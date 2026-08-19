"""
解码子进程池管理（内存根治方案主进程侧）

配合 decode_worker.py：主进程通过子进程池执行图像解码，解码内存
（全分辨率实测 ~242MB/张）全部隔离在子进程，子进程周期重启回收。

设计：
- 池大小：固定 N 个子进程，每个持有一条 Pipe
- 任务分发：轮询空闲子进程（简单 FIFO），阻塞等待结果
- 周期重启：子进程累计解码 MAX_TASKS_PER_WORKER 次后重启，确保
  autorelease pool 随进程销毁彻底释放
- 临时文件清理：主进程拿到结果文件后，使用完毕后删除
- 降级：multiprocessing 不可用（如受限环境）时回退主进程直接解码

用法:
    from ..core.decode_pool import DecodePool

    pool = DecodePool(max_workers=2, max_tasks_per_worker=50)
    file_path = pool.decode(path, target_size=(1920, 1280))  # 返回临时文件路径
    # ... 使用 file_path 显示 ...
    pool.cleanup_file(file_path)
    pool.shutdown()
"""

import logging
import multiprocessing as mp
import os
import tempfile
import threading

logger = logging.getLogger("plookingII.decode_pool")

# 每个子进程最多解码次数：达到后重启（保证解码内存彻底回收）
_DEFAULT_MAX_TASKS_PER_WORKER = 50


def _spawn_worker_entry(conn, work_dir: str) -> None:
    """模块级子进程入口（spawn 要求 target 可 pickle 的顶层函数）

    避免传递绑定方法（含锁等不可 pickle 状态）。
    """
    from .decode_worker import worker_entry

    worker_entry(conn, work_dir)


class _WorkerSlot:
    """单个子进程槽位：持有进程 + Pipe + 任务计数"""

    __slots__ = ("active", "conn", "process", "tasks_done")

    def __init__(self, process, conn):
        self.process = process
        self.conn = conn
        self.tasks_done = 0
        self.active = False


class DecodePool:
    """解码子进程池（内存隔离 + 周期重启）"""

    def __init__(
        self,
        max_workers: int = 2,
        max_tasks_per_worker: int = _DEFAULT_MAX_TASKS_PER_WORKER,
        work_dir: str | None = None,
    ):
        """
        Args:
            max_workers: 子进程数（并发解码）
            max_tasks_per_worker: 每个子进程重启前累计解码次数
            work_dir: 临时文件输出目录，None 使用系统临时目录
        """
        self._max_workers = max(1, max_workers)
        self._max_tasks = max(1, max_tasks_per_worker)
        self._work_dir = work_dir or os.path.join(tempfile.gettempdir(), "plookingII-decode")
        self._lock = threading.RLock()
        self._slots: list[_WorkerSlot] = []
        self._round_robin = 0
        self._shutdown_flag = False
        self._spawn_ctx = None

        try:
            self._spawn_ctx = mp.get_context("spawn")
            # 预启动子进程（延迟到首次 decode 也行，但预启动降低首图延迟）
            self._ensure_workers()
        except Exception:
            logger.warning("解码子进程池初始化失败，将回退主进程直接解码", exc_info=True)
            self._spawn_ctx = None
            self._slots = []

    # ------------------------------------------------------------------
    # 子进程生命周期
    # ------------------------------------------------------------------
    def _ensure_workers(self) -> None:
        """确保子进程池就绪（启动缺失的槽位）"""
        if self._spawn_ctx is None:
            return
        with self._lock:
            for _ in range(self._max_workers - len(self._slots)):
                self._start_worker()

    def _start_worker(self) -> None:
        """启动一个子进程槽位"""
        try:
            parent_conn, child_conn = mp.Pipe(duplex=True)
            process = self._spawn_ctx.Process(
                target=_spawn_worker_entry,
                args=(child_conn, self._work_dir),
                daemon=True,
            )
            process.start()
            # 子进程端连接在父进程侧关闭，避免泄漏
            child_conn.close()
            self._slots.append(_WorkerSlot(process, parent_conn))
            logger.debug("解码子进程已启动 pid=%s", process.pid)
        except Exception:
            logger.exception("启动解码子进程失败")

    def _restart_worker(self, slot: _WorkerSlot) -> None:
        """重启一个子进程（终止旧进程，启动新进程）"""
        with self._lock:
            try:
                slot.conn.close()
            except Exception:
                pass
            try:
                slot.process.terminate()
                slot.process.join(timeout=3.0)
            except Exception:
                pass
            self._slots.remove(slot)
            self._start_worker()

    # ------------------------------------------------------------------
    # 解码接口
    # ------------------------------------------------------------------
    def decode(self, path: str, target_size: tuple[int, int] | None = None) -> str | None:
        """通过子进程解码图片，返回临时文件路径（失败返回 None）

        Args:
            path: 源图片路径
            target_size: 目标尺寸 (w, h)；None 表示全分辨率

        Returns:
            解码后临时文件路径（主进程显示用），失败返回 None
        """
        if self._shutdown_flag:
            return None

        # 回退路径：无子进程池时主进程直接解码
        if self._spawn_ctx is None or not self._slots:
            try:
                from .decode_worker import _decode_to_file

                return _decode_to_file(path, target_size, self._work_dir)
            except Exception:
                logger.exception("主进程回退解码失败 %s", path)
                return None

        # 轮询选择空闲槽位（FIFO 轮转）
        slot = None
        with self._lock:
            if not self._slots:
                self._ensure_workers()
            if not self._slots:
                return None
            self._round_robin = (self._round_robin + 1) % len(self._slots)
            slot = self._slots[self._round_robin]

        if slot is None:
            return None

        try:
            slot.conn.send((path, target_size))
            result = slot.conn.recv()  # 阻塞等待解码结果
            slot.tasks_done += 1
            # 达到上限重启（确保解码内存随进程销毁回收）
            if slot.tasks_done >= self._max_tasks:
                self._restart_worker(slot)
            return result if isinstance(result, str) else None
        except (EOFError, OSError):
            # 子进程异常退出：重启并重试一次
            logger.warning("解码子进程异常，重启重试: %s", path)
            self._restart_worker(slot)
            return self.decode(path, target_size)

    @staticmethod
    def cleanup_file(file_path: str | None) -> None:
        """删除解码临时文件（显示使用完毕后调用）"""
        if not file_path:
            return
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except OSError:
            logger.debug("临时文件清理失败: %s", file_path)

    def shutdown(self) -> None:
        """关闭子进程池（应用退出时调用）"""
        self._shutdown_flag = True
        with self._lock:
            for slot in self._slots:
                try:
                    slot.conn.send(None)  # 终止信号
                    slot.process.join(timeout=2.0)
                except Exception:
                    pass
                try:
                    slot.conn.close()
                except Exception:
                    pass
            self._slots = []

    def get_stats(self) -> dict:
        """导出池状态（调试/监控）"""
        with self._lock:
            return {
                "workers": len(self._slots),
                "tasks_per_worker": [s.tasks_done for s in self._slots],
                "max_tasks": self._max_tasks,
                "work_dir": self._work_dir,
            }


# 全局单例（应用生命周期内复用）
_global_pool: DecodePool | None = None
_pool_lock = threading.Lock()


def get_decode_pool() -> DecodePool:
    """获取全局解码子进程池单例"""
    global _global_pool  # noqa: PLW0603
    with _pool_lock:
        if _global_pool is None:
            _global_pool = DecodePool()
        return _global_pool


def shutdown_decode_pool() -> None:
    """关闭全局解码子进程池（应用退出时调用）"""
    global _global_pool  # noqa: PLW0603
    with _pool_lock:
        pool = _global_pool
        _global_pool = None
    if pool is not None:
        pool.shutdown()


def reset_decode_pool() -> None:
    """重置全局单例（主要用于测试）"""
    global _global_pool  # noqa: PLW0603
    with _pool_lock:
        _global_pool = None


__all__ = ["DecodePool", "get_decode_pool", "reset_decode_pool", "shutdown_decode_pool"]
