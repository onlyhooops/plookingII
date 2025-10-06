"""
BackgroundTaskManager - 后台任务管理服务

负责统一管理应用的后台任务调度和生命周期：
- 后台任务调度和执行
- 任务线程管理
- 应用退出时的任务清理
- 异步验证任务管理

从 MainWindow 和 SystemController 中提取，遵循单一职责原则。
"""

import concurrent.futures
import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from ..config.constants import APP_NAME

logger = logging.getLogger(APP_NAME)


class BackgroundTaskManager:
    """
    后台任务管理服务

    负责处理：
    1. 后台任务调度和执行
    2. 线程池管理
    3. 任务生命周期管理
    4. 应用退出时的清理
    """

    def __init__(self, window):
        """
        初始化后台任务管理器

        Args:
            window: 主窗口实例
        """
        self.window = window
        self._shutting_down = False
        self._task_lock = threading.Lock()

        # 线程池管理
        self._executor = None
        self._max_workers = 4

        # 活跃任务跟踪
        self._active_tasks: dict[str, concurrent.futures.Future] = {}
        self._task_callbacks: dict[str, Callable] = {}

        # 初始化线程池
        self._init_executor()

    def _init_executor(self):
        """初始化线程池执行器"""
        try:
            self._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=self._max_workers, thread_name_prefix="BackgroundTask"
            )
            logger.debug(f"后台任务线程池初始化完成，最大工作线程数: {self._max_workers}")
        except Exception as e:
            logger.error(f"初始化后台任务线程池失败: {e}")

    # ==================== 任务调度管理 ====================

    def schedule_background_tasks(self):
        """
        调度后台任务

        启动必要的后台任务，如图片预加载、缓存清理等。
        """
        if self._shutting_down:
            return

        try:
            # 委托给ImageLoaderService处理图片相关的后台任务
            if hasattr(self.window, "image_loader_service"):
                self.window.image_loader_service.schedule_background_tasks()

            # 启动其他后台任务
            self._schedule_maintenance_tasks()

        except Exception as e:
            logger.warning(f"调度后台任务失败: {e}")

    def _schedule_maintenance_tasks(self):
        """调度维护性后台任务"""
        try:
            # 定期清理过期的任务记录 - 在测试环境中使用较短延迟
            delay = 0.1 if hasattr(self.window, "_is_testing") else 30.0
            self.submit_task("cleanup_expired_tasks", self._cleanup_expired_tasks, delay=delay)
        except Exception as e:
            logger.debug(f"调度维护任务失败: {e}")

    def submit_task(
        self, task_id: str, task_func: Callable, *args, delay: float = 0.0, callback: Callable | None = None, **kwargs
    ):
        """
        提交后台任务

        Args:
            task_id: 任务唯一标识符
            task_func: 任务函数
            *args: 任务函数参数
            delay: 延迟执行时间（秒）
            callback: 任务完成回调函数
            **kwargs: 任务函数关键字参数

        Returns:
            Future: 任务Future对象，如果提交失败则返回None
        """
        if self._shutting_down or not self._executor:
            return None

        try:
            # 包装任务函数以支持延迟执行
            def delayed_task():
                if delay > 0:
                    time.sleep(delay)
                if self._shutting_down:
                    return None
                return task_func(*args, **kwargs)

            # 先检查是否有需要取消的任务（在锁内）
            old_future_to_cancel = None
            with self._task_lock:
                if task_id in self._active_tasks:
                    old_future = self._active_tasks[task_id]
                    if not old_future.done():
                        old_future_to_cancel = old_future

            # 在锁外取消旧任务，避免死锁
            if old_future_to_cancel:
                old_future_to_cancel.cancel()

            # 在锁内注册新任务
            with self._task_lock:
                # 提交任务
                future = self._executor.submit(delayed_task)
                self._active_tasks[task_id] = future

                if callback:
                    self._task_callbacks[task_id] = callback

            # 在锁外添加完成回调，避免死锁
            future.add_done_callback(lambda f: self._on_task_completed(task_id, f))

            logger.debug(f"后台任务已提交: {task_id}")
            return future

        except Exception as e:
            logger.warning(f"提交后台任务失败 [{task_id}]: {e}")
            return None

    def _on_task_completed(self, task_id: str, future: concurrent.futures.Future):
        """任务完成回调处理"""
        try:
            with self._task_lock:
                # 清理任务记录
                self._active_tasks.pop(task_id, None)
                callback = self._task_callbacks.pop(task_id, None)

            # 执行用户回调（在锁外执行，避免死锁）
            if callback and not self._shutting_down:
                try:
                    # 注意：这里不要调用future.result()，因为这可能导致死锁
                    # 让用户回调自己决定是否需要获取结果
                    callback(future)
                except Exception as e:
                    logger.debug(f"任务回调执行失败 [{task_id}]: {e}")

            logger.debug(f"后台任务完成: {task_id}")

        except Exception as e:
            logger.debug(f"任务完成处理失败 [{task_id}]: {e}")

    # ==================== 异步验证任务 ====================

    def start_async_validation(self, validation_func: Callable, *args, **kwargs):
        """
        启动异步验证任务

        Args:
            validation_func: 验证函数
            *args: 验证函数参数
            **kwargs: 验证函数关键字参数

        Returns:
            Future: 验证任务Future对象
        """
        return self.submit_task("async_validation", validation_func, *args, **kwargs)

    def async_validate(self, data: Any, validator: Callable) -> bool:
        """
        异步验证数据

        Args:
            data: 待验证的数据
            validator: 验证器函数

        Returns:
            bool: 验证结果
        """
        try:
            if self._shutting_down:
                return False

            return validator(data)
        except Exception as e:
            logger.debug(f"异步验证失败: {e}")
            return False

    def cancel_async_validation(self):
        """取消异步验证任务"""
        try:
            with self._task_lock:
                validation_future = self._active_tasks.get("async_validation")
                if validation_future and not validation_future.done():
                    validation_future.cancel()
                    logger.debug("异步验证任务已取消")
        except Exception as e:
            logger.debug(f"取消异步验证失败: {e}")

    # ==================== 任务管理 ====================

    def cancel_task(self, task_id: str) -> bool:
        """
        取消指定任务

        Args:
            task_id: 任务标识符

        Returns:
            bool: 取消成功返回True
        """
        try:
            with self._task_lock:
                future = self._active_tasks.get(task_id)
                if future and not future.done():
                    result = future.cancel()
                    if result:
                        self._active_tasks.pop(task_id, None)
                        self._task_callbacks.pop(task_id, None)
                        logger.debug(f"任务已取消: {task_id}")
                    return result
        except Exception as e:
            logger.debug(f"取消任务失败 [{task_id}]: {e}")
        return False

    def get_active_task_count(self) -> int:
        """获取活跃任务数量"""
        try:
            with self._task_lock:
                return len([f for f in self._active_tasks.values() if not f.done()])
        except Exception:
            return 0

    def get_active_task_ids(self) -> list[str]:
        """获取活跃任务ID列表"""
        try:
            with self._task_lock:
                return [tid for tid, f in self._active_tasks.items() if not f.done()]
        except Exception:
            return []

    def get_task_status(self, task_id: str) -> str:
        """
        获取任务状态

        Args:
            task_id: 任务标识符

        Returns:
            str: 任务状态 - "running"/"pending"/"completed"/"cancelled"/"not_found"
        """
        try:
            with self._task_lock:
                future = self._active_tasks.get(task_id)
                if not future:
                    return "not_found"
                if future.done():
                    if future.cancelled():
                        return "cancelled"
                    return "completed"
                return "running"  # 简化处理，不区分running和pending
        except Exception:
            return "not_found"

    # ==================== 维护任务 ====================

    def _cleanup_expired_tasks(self):
        """清理过期的任务记录"""
        try:
            with self._task_lock:
                completed_tasks = [tid for tid, future in self._active_tasks.items() if future.done()]

                for task_id in completed_tasks:
                    self._active_tasks.pop(task_id, None)
                    self._task_callbacks.pop(task_id, None)

                if completed_tasks:
                    logger.debug(f"清理了 {len(completed_tasks)} 个已完成的任务记录")

        except Exception as e:
            logger.debug(f"清理过期任务失败: {e}")

    # ==================== 生命周期管理 ====================

    def shutdown_background_tasks(self):
        """
        关闭所有后台任务

        应用退出前调用，确保所有后台任务正确停止。
        """
        logger.debug("开始关闭后台任务...")

        try:
            # 设置关闭标志
            self._shutting_down = True

            # 获取所有需要取消的任务（在锁内）
            tasks_to_cancel = []
            with self._task_lock:
                for task_id, future in list(self._active_tasks.items()):
                    if not future.done():
                        tasks_to_cancel.append((task_id, future))

            # 在锁外取消任务，避免死锁
            for task_id, future in tasks_to_cancel:
                future.cancel()
                logger.debug(f"取消任务: {task_id}")

            # 关闭线程池 (注意: shutdown不接受timeout参数)
            if self._executor:
                self._executor.shutdown(wait=False)  # 不等待，避免死锁
                logger.debug("后台任务线程池已关闭")

            # 清理资源
            with self._task_lock:
                self._active_tasks.clear()
                self._task_callbacks.clear()

            logger.debug("后台任务管理器关闭完成")

        except Exception as e:
            logger.warning(f"关闭后台任务失败: {e}")

    def cleanup(self):
        """清理后台任务管理器资源"""
        self.shutdown_background_tasks()

    def shutdown(self):
        """关闭任务管理器的别名方法"""
        self.shutdown_background_tasks()

    # ==================== 状态查询 ====================

    def is_shutting_down(self) -> bool:
        """检查是否正在关闭"""
        return self._shutting_down

    def get_status_info(self) -> dict[str, Any]:
        """
        获取后台任务管理器状态信息

        Returns:
            Dict: 状态信息字典
        """
        try:
            with self._task_lock:
                active_count = len([f for f in self._active_tasks.values() if not f.done()])
                total_count = len(self._active_tasks)

                return {
                    "shutting_down": self._shutting_down,
                    "active_tasks": active_count,
                    "total_tasks": total_count,
                    "max_workers": self._max_workers,
                    "executor_alive": self._executor is not None and not self._executor._shutdown,
                }
        except Exception as e:
            logger.debug(f"获取状态信息失败: {e}")
            return {"error": str(e)}
