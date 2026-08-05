"""
有界任务执行器

包装 ThreadPoolExecutor，为后台预取类任务提供“有界排队 + 淘汰最旧”语义：
快速连续导航产生的过期预取任务不再无限积压，队列满时优先取消最旧的
未开始任务，防止内存与线程资源被陈旧任务耗尽。
"""

import threading
from collections import deque
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any


class BoundedExecutor:
    """有界执行器：队列满时淘汰最旧未开始任务"""

    def __init__(self, executor: ThreadPoolExecutor, max_queued: int = 8):
        self._executor = executor
        self._max_queued = max(1, max_queued)
        self._queued: deque[Future] = deque(maxlen=self._max_queued)
        # RLock：任务瞬时完成时 add_done_callback 会在 submit 所在线程同步触发，
        # _discard 需要与 submit 持锁期间重入（否则自锁死锁）
        self._lock = threading.RLock()

    def submit(self, fn: Callable, *args: Any, **kwargs: Any) -> Future:
        """提交任务；队列满时取消最旧的未开始任务"""
        with self._lock:
            while len(self._queued) >= self._max_queued:
                oldest = self._queued.popleft()
                oldest.cancel()  # 已开始执行的任务无法取消，仅移除跟踪

            future = self._executor.submit(fn, *args, **kwargs)
            self._queued.append(future)
            future.add_done_callback(self._discard)
            return future

    def _discard(self, future: Future) -> None:
        """任务结束后从跟踪队列移除"""
        with self._lock:
            try:
                self._queued.remove(future)
            except ValueError:
                pass

    def shutdown(self, wait: bool = False) -> None:
        """关闭底层执行器"""
        self._executor.shutdown(wait=wait)

    def pending_count(self) -> int:
        """当前排队中的任务数"""
        with self._lock:
            return len(self._queued)
