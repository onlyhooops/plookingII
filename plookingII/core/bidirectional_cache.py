"""
双向缓存池模块

提供PlookingII应用程序的智能双向图像缓存管理功能。
实现基于用户浏览行为的智能预加载策略，提供流畅的图像浏览体验。

主要功能：
    - 向前预加载：基于优先级队列异步加载后续图像
    - 向后保留：保留最近浏览过的图像以支持快速回退
    - 智能内存管理：与AdvancedImageCache协同，避免内存溢出
    - 自适应策略：根据用户浏览速度和方向调整预加载窗口
    - 异步处理：内置事件循环线程，支持任务取消和优先级调度

核心组件：
    - BidirectionalCachePool: 主要的双向缓存池类
    - 预加载策略引擎
    - 内存监控集成
    - 异步任务调度器

技术特点：
    - 双向缓存机制：向前预加载 + 向后保留
    - 智能预加载：基于用户行为分析优化预加载策略
    - 内存协同：与AdvancedImageCache协同管理内存
    - 异步处理：非阻塞的预加载和缓存管理
    - 自适应优化：根据使用模式动态调整缓存策略

使用方式：
    from plookingII.core.bidirectional_cache import BidirectionalCachePool


Author: PlookingII Team
Version: 1.0.0
"""

from typing import Any

from ..config.constants import APP_NAME
from ..imports import logging, threading, time
from ..monitor import get_unified_monitor
from .cache import AdvancedImageCache
from .image_processing import HybridImageProcessor
from .preload_manager import PreloadManager

# from ..config.manager import get_config  # Not used directly

logger = logging.getLogger(APP_NAME)


class BidirectionalCachePool:
    """以当前图片为中心的双向智能缓存池。

    实现基于用户浏览行为的智能预加载策略，提供流畅的图像浏览体验。
    采用双向缓存机制：向前预加载即将浏览的图像，向后保留最近浏览的图像。

    核心特性：
    - 向前预加载（future_cache）：基于优先级队列异步加载后续图像
    - 向后保留（past_cache）：保留最近浏览过的图像以支持快速回退
    - 智能内存管理：与AdvancedImageCache协同，避免内存溢出
    - 自适应策略：根据用户浏览速度和方向调整预加载窗口
    - 异步处理：内置事件循环线程，支持任务取消和优先级调度

    协作组件：
    - AdvancedImageCache: 统一的图像缓存管理
    - HybridImageProcessor: 图像处理和格式转换
    - MemoryMonitor: 系统内存监控和阈值管理
    """

    def __init__(
        self,
        preload_count: int = 5,
        keep_previous: int = 3,
        image_processor: HybridImageProcessor | None = None,
        memory_monitor: object | None = None,
        advanced_cache: AdvancedImageCache | None = None,
    ):
        """初始化双向缓存池。

        Args:
            preload_count: 向前预加载的图像数量，默认5张
            keep_previous: 向后保留的图像数量，默认3张
            image_processor: 图像处理器实例，用于图像加载和转换
            memory_monitor: 内存监控器实例，用于内存使用监控
            advanced_cache: 高级缓存实例，用于统一的图像缓存管理

        Note:
            - 所有组件都支持依赖注入，未提供时使用默认实例
            - 自动建立组件间的协作关系
            - 启动独立的异步事件循环线程
        """
        import threading
        from collections import OrderedDict


        # 缓存窗口配置
        self.preload_count = preload_count      # 向前预加载数量
        self.keep_previous = keep_previous      # 向后保留数量

        # 核心组件初始化（支持依赖注入）
        self.image_processor = image_processor or HybridImageProcessor()
        self.memory_monitor = memory_monitor or get_unified_monitor()
        self.image_cache = advanced_cache or AdvancedImageCache()

        # 建立缓存与内存监控器的协作关系
        try:
            self.image_cache.memory_monitor = self.memory_monitor
        except Exception:
            logger.debug("Failed to set image_cache.memory_monitor", exc_info=True)

        # 双向缓存结构（仅存储键，图像对象由AdvancedImageCache统一管理）
        self.future_cache = OrderedDict()      # 向前预加载缓存：key -> True
        self.past_cache = OrderedDict()        # 向后保留缓存：key -> True

        # 当前状态
        self.current_image_key: str | None = None    # 当前显示的图像键
        self.sequence: list[str] = []                   # 图像序列列表
        self._index_map: dict[str, int] = {}            # 键到索引的映射

        # 线程同步与任务管理（线程队列模型）
        self._lock = threading.RLock()          # 可重入锁，保护共享状态
        self._generation = 0                    # 任务代次，用于取消过时的预加载任务
        try:
            import concurrent.futures as _cf


            self._executor = _cf.ThreadPoolExecutor(max_workers=2, thread_name_prefix="BidiPool")
        except Exception:
            self._executor = None

        # 内存管理配置
        self.max_preload_memory_mb = 800       # 预加载内存阈值（MB）

        # 预加载管理器
        self.preload_manager = PreloadManager(self, memory_monitor)

        # 用户导航行为分析
        self._last_index: int | None = None     # 上次访问的图像索引
        self._last_set_ts: float = 0.0             # 上次设置时间戳
        self._nav_speed_ips: float = 0.0           # 导航速度（图像/秒）
        self._nav_direction: str = "forward"       # 导航方向：forward/backward/idle
        self._last_dwell_s: float = 0.0            # 上次停留时间（秒）

        # 线程队列模型无需事件循环

    # ---------- 基础结构 ----------
    def _ensure_event_loop_thread(self):
        """兼容保留：线程队列模型下不再需要事件循环。"""
        return

    def set_sequence(self, sequence: list[str]):
        """设置图像序列并重建索引映射。

        更新缓存池管理的图像序列，重新构建键到索引的映射关系。
        清空向前预加载缓存，但保留向后缓存以维持浏览历史。

        Args:
            sequence: 图像键的有序列表，None时设置为空列表

        Note:
            - 线程安全：在锁保护下执行
            - 重建索引映射以支持快速位置查找
            - 清空future_cache，由下次set_current_image触发重新计算
            - 保留past_cache，避免切换序列时丢失浏览历史
        """
        with self._lock:
            self.sequence = sequence or []
            # 重建键到索引的映射，用于快速位置查找
            self._index_map = {k: i for i, k in enumerate(self.sequence)}

            # 清空向前预加载缓存（将由下次set_current_image重新计算）
            self.future_cache.clear()

            # 保留向后缓存，避免序列切换时丢失已浏览的历史

    def clear(self):
        """清空双向缓存池的所有状态。

        清除所有缓存引用和当前状态，但不直接操作AdvancedImageCache，
        由上层UI组件的清理策略统一处理底层缓存。

        Note:
            - 线程安全：在锁保护下执行
            - 仅清空缓存池的引用，不影响底层图像缓存
            - 重置当前图像状态
        """
        with self._lock:
            self.future_cache.clear()       # 清空向前预加载缓存
            self.past_cache.clear()         # 清空向后保留缓存
            self.current_image_key = None   # 重置当前图像键
            # 注意：不直接清空AdvancedImageCache，由UI的清理策略统一处理

    def shutdown(self):
        """关闭双向缓存池并清理资源。

        停止所有正在进行的预加载任务，关闭事件循环线程，
        确保资源得到正确释放。

        Note:
            - 增加任务代次以取消所有进行中的预加载任务
            - 安全地停止事件循环
            - 异常处理：确保关闭过程中的错误不会影响程序稳定性
        """
        try:
            with self._lock:
                self._generation += 1
            if getattr(self, "_executor", None):
                self._executor.shutdown(wait=False, cancel_futures=True)
            # 关闭预加载管理器
            if hasattr(self, "preload_manager"):
                self.preload_manager.shutdown()
        except Exception:
            logger.exception("Error during BidirectionalCachePool shutdown")

    def clear_image_cache(self, image_path: str) -> bool:
        """清理与指定图像路径相关的缓存引用与底层缓存。

        Args:
            image_path: 图像文件路径（或作为键使用的标识）

        Returns:
            bool: 是否成功执行清理
        """
        try:
            # 先移除引用，再清理底层缓存
            with self._lock:
                # 从前向/后向缓存移除
                if image_path in self.future_cache:
                    self.future_cache.pop(image_path, None)
                if image_path in self.past_cache:
                    self.past_cache.pop(image_path, None)

                # 清理当前键与索引映射
                if self.current_image_key == image_path:
                    self.current_image_key = None
                self._index_map.pop(image_path, None)

            # 清理底层 AdvancedImageCache
            cache = getattr(self, "image_cache", None)
            if cache is not None:
                if hasattr(cache, "remove") and callable(cache.remove):
                    cache.remove(image_path)
                elif hasattr(cache, "remove_from_cache") and callable(cache.remove_from_cache):
                    cache.remove_from_cache(image_path)
            return True
        except Exception:
            logger.debug("clear_image_cache failed", exc_info=True)
            return False

    # ---------- 公开方法 ----------
    def get_image(self, image_key: str):
        """获取指定键的图像。

        直接委托给底层的AdvancedImageCache进行图像获取，
        利用其多级缓存和智能管理机制。

        Args:
            image_key: 图像键

        Returns:
            图像对象，如果未找到则返回None

        Note:
            - 委托模式：利用AdvancedImageCache的完整功能
            - 支持多级缓存查找（主缓存、预览缓存、预加载缓存）
        """
        return self.image_cache.get(image_key)

    def set_current_image_sync(self, image_key: str, image_path: str, image_data=None):
        """同步方式设置当前图像（线程安全）。

        为同步环境提供的接口，内部将任务提交到异步事件循环执行。
        自动管理任务代次和任务取消，确保只有最新的预加载任务在执行。

        Args:
            image_key: 图像键
            image_path: 图像文件路径
            image_data: 可选的预加载图像数据

        Note:
            - 线程安全：可从任意线程调用
            - 任务管理：自动取消过时的预加载任务
            - 异步执行：实际处理在事件循环线程中进行
        """
        with self._lock:
            self._generation += 1
            gen = self._generation
        # 在线程池中提交任务
        def _task():
            try:
                self._set_current_image_task(image_key, image_path, image_data, gen)
            except Exception:
                logger.debug("_set_current_image_task failed", exc_info=True)
        if getattr(self, "_executor", None):
            self._executor.submit(_task)
        else:
            threading.Thread(target=_task, daemon=True).start()
        return gen

    def _set_current_image_task(self, image_key: str, image_path: str, image_data, gen: int) -> None:
        prev_key = None
        with self._lock:
            prev_key = self.current_image_key
            self.current_image_key = image_key
            cur_idx = self._index_map.get(image_key, -1)
            now = time.time()
            if self._last_index is not None and cur_idx >= 0:
                dt = max(1e-3, now - (self._last_set_ts or now))
                di = abs(cur_idx - self._last_index)
                self._nav_speed_ips = min(30.0, di / dt)
                if cur_idx > self._last_index:
                    self._nav_direction = "forward"
                elif cur_idx < self._last_index:
                    self._nav_direction = "backward"
                else:
                    self._nav_direction = "idle"
                self._last_dwell_s = dt
            self._last_index = cur_idx
            self._last_set_ts = now
            if prev_key and prev_key != image_key:
                self._add_to_past_cache(prev_key)
                self._clean_old_past_cache()
        # 启动同步预加载流程（在线程中）
        self._preload_images_sync(image_key, gen)

    async def set_current_image(self, image_key: str, image_path: str, image_data=None):
        """异步设置当前图像并触发智能预加载。

        核心功能：
        - 将前一张图像加入past_cache，维护浏览历史
        - 基于当前位置和导航模式计算预加载窗口
        - 启动异步预加载任务，支持内存敏感调整
        - 更新导航度量（速度、方向、停留时间）

        Args:
            image_key: 当前图像键
            image_path: 图像文件路径
            image_data: 可选的预加载图像数据

        Note:
            - 异步执行：在事件循环线程中运行
            - 导航分析：根据用户浏览行为动态调整预加载策略
            - 内存管理：根据可用内存调整预加载数量
        """
        import time


        prev_key = None
        with self._lock:
            prev_key = self.current_image_key
            self.current_image_key = image_key

            # 更新导航度量：分析用户浏览行为
            cur_idx = self._index_map.get(image_key, -1)
            now = time.time()

            if self._last_index is not None and cur_idx >= 0:
                # 计算时间间隔和位置变化
                dt = max(1e-3, now - (self._last_set_ts or now))
                di = abs(cur_idx - self._last_index)

                # 计算导航速度（图片/秒），限制最大值避免异常
                self._nav_speed_ips = min(30.0, di / dt)

                # 确定导航方向
                if cur_idx > self._last_index:
                    self._nav_direction = "forward"    # 向前浏览
                elif cur_idx < self._last_index:
                    self._nav_direction = "backward"   # 向后浏览
                else:
                    self._nav_direction = "idle"       # 停留在当前位置

                # 记录停留时间
                self._last_dwell_s = dt

            # 更新导航状态
            self._last_index = cur_idx
            self._last_set_ts = now

            # 将前一张图像加入历史缓存
            if prev_key and prev_key != image_key:
                self._add_to_past_cache(prev_key)
                self._clean_old_past_cache()

            # 获取当前任务代次
            gen = self._generation

        # 启动异步预加载任务
        # 兼容保留：转为同步线程模型后，此接口不再使用
        # 简化预加载逻辑 - 移除复杂的异步预加载
        try:
            self._simple_preload(image_key, gen)
        except Exception:
            pass

    def _simple_preload(self, image_key: str, gen: int):
        """简化的预加载逻辑"""
        # 基本的同步预加载实现

    # ---------- 内部逻辑 ----------
    def _compute_preload_window(self, cur_index: int) -> tuple[list[int], list[int]]:
        """计算预加载窗口（精简分支，等价逻辑）。"""
        mem_info = self.memory_monitor.get_memory_info() if self.memory_monitor else {"available_mb": 1000}
        available = mem_info.get("available_mb", 1000) or 1000
        speed = self._nav_speed_ips
        direction = self._nav_direction or "forward"

        # 前向基础窗口：基于可用内存分三挡
        if available > 1500:
            base = max(1, self.preload_count)
        elif available >= 800:
            base = min(self.preload_count, 5)
        else:
            base = min(self.preload_count, 3 if available >= 500 else 2)

        # 速度调整：合并为线性截断
        if speed >= 8.0:
            forward = max(1, min(3, base - 2))
        elif speed >= 4.0:
            forward = max(1, min(4, base - 1))
        elif speed <= 1.0:
            forward = min(base + 2, base + 1)
        else:
            forward = base

        # 后向窗口：默认至多3，回看时+1但不超过keep_previous
        backward = min(self.keep_previous, 3 + (1 if direction == "backward" else 0))

        # 生成索引
        n = len(self.sequence)
        fwd = list(range(cur_index + 1, min(n, cur_index + 1 + forward)))
        back = list(range(max(0, cur_index - backward), cur_index))
        return fwd, back[::-1]

    def _preload_images_sync(self, current_key: str, generation: int):
        """异步预加载图像的核心逻辑 - 使用PreloadManager重构版本

        ✨ 重构说明: 原212行复杂函数已拆分为专门的PreloadManager类
        这个方法现在只负责协调调用，具体逻辑在preload_manager模块中。

        Args:
            current_key: 当前图像键
            generation: 任务代次，用于验证任务有效性
        """
        # 获取当前状态快照（线程安全）
        with self._lock:
            sequence = list(self.sequence)
            index_map = dict(self._index_map)
            nav_speed = self._nav_speed_ips
            nav_direction = self._nav_direction

        # 使用PreloadManager执行预加载
        stats = self.preload_manager.preload_images(
            current_key=current_key,
            generation=generation,
            sequence=sequence,
            index_map=index_map,
            nav_speed_ips=nav_speed,
            nav_direction=nav_direction,
            cancel_check_callback=self._should_cancel_generation
        )

        # 记录统计信息（仅在有加载或调试模式下）
        if stats.get("completed", 0) > 0 or logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"预加载完成: {stats}")

    def _add_to_past_cache(self, image_key: str):
        """将图像键添加到历史缓存。

        维护用户浏览历史的有序记录，支持快速回看。
        使用OrderedDict确保按访问顺序排列。

        Args:
            image_key: 要添加的图像键

        Note:
            - 线程安全：在锁保护下执行
            - 自动移动到末尾，保持最近访问顺序
            - 异常处理：避免单个操作影响整体功能
        """
        try:
            with self._lock:
                self.past_cache[image_key] = True
                # 移动到末尾，保持最近访问的顺序
                self.past_cache.move_to_end(image_key)
        except Exception:
            logger.debug("Failed to add %s to past_cache", image_key, exc_info=True)

    def _clean_old_past_cache(self):
        """清理过期的历史缓存记录。

        移除超出keep_previous限制的最旧历史记录，
        保持历史缓存在合理大小范围内。

        Note:
            - 线程安全：在锁保护下执行
            - FIFO策略：移除最旧的记录（last=False）
            - 异常处理：确保清理失败不影响其他功能
        """
        try:
            with self._lock:
                # 移除超出限制的最旧记录
                while len(self.past_cache) > self.keep_previous:
                    self.past_cache.popitem(last=False)  # 移除最旧的项
        except Exception:
            logger.debug("Failed to clean old past cache", exc_info=True)

    def reset_generation(self):
        """重置任务代次，取消所有进行中的预加载任务。

        通过增加代次使所有正在执行的预加载任务失效，
        用于快速响应用户操作变化。

        Note:
            - 线程安全：在锁保护下执行
            - 立即生效：所有旧任务将在下次检查时自动停止
        """
        with self._lock:
            self._generation += 1

    def set_preload_window(self, preload_count: int = None, keep_previous: int = None):
        """动态调整预加载窗口大小。

        允许运行时调整预加载策略，适应不同的使用场景和性能需求。

        Args:
            preload_count: 向前预加载的图像数量，None表示不修改
            keep_previous: 保留的历史图像数量，None表示不修改

        Note:
            - 线程安全：在锁保护下执行
            - 选择性更新：只更新非None的参数
            - 立即生效：下次预加载时使用新配置
        """
        with self._lock:
            if preload_count is not None:
                self.preload_count = preload_count
            if keep_previous is not None:
                self.keep_previous = keep_previous

    def get_stats(self) -> dict[str, Any]:
        """获取双向缓存池的统计信息。

        提供缓存池状态的详细统计数据，用于性能监控和调试分析。

        Returns:
            Dict[str, Any]: 包含以下统计信息的字典：
            - sequence_length: 图像序列总长度
            - current_key: 当前显示的图像键
            - future_size: 向前预加载缓存的项目数量
            - past_size: 向后历史缓存的项目数量
            - generation: 当前任务代次（用于任务有效性验证）

        Note:
            - 线程安全：在锁保护下读取所有统计数据
            - 实时数据：反映调用时刻的准确状态
            - 用于性能分析和缓存策略优化
        """
        with self._lock:
            stats = {
                "sequence_length": len(self.sequence),
                "current_key": self.current_image_key,
                "future_size": len(self.future_cache),
                "past_size": len(self.past_cache),
                "generation": self._generation,
            }
        return stats
