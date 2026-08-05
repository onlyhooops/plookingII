"""
测试 core/bounded_executor.py

覆盖：有界队列淘汰最旧任务、任务完成后移除跟踪、shutdown 透传。
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from plookingII.core.bounded_executor import BoundedExecutor


class TestBoundedExecutor:
    def test_submit_and_pending_count(self):
        """提交任务后被跟踪，执行完成后移除"""
        start = threading.Event()

        def slow_task():
            start.wait(2)
            return 42

        with ThreadPoolExecutor(max_workers=1) as pool:
            bounded = BoundedExecutor(pool, max_queued=8)
            future = bounded.submit(slow_task)
            assert bounded.pending_count() == 1
            start.set()
            assert future.result(timeout=3) == 42
            deadline = time.time() + 3
            while time.time() < deadline and bounded.pending_count() != 0:
                time.sleep(0.01)
            assert bounded.pending_count() == 0

    def test_queue_full_evicts_oldest(self):
        """队列满时提交新任务会淘汰最旧的未开始任务"""
        start = threading.Event()

        def slow_task():
            start.wait(2)
            return "slow"

        with ThreadPoolExecutor(max_workers=1) as pool:
            bounded = BoundedExecutor(pool, max_queued=1)
            first = bounded.submit(slow_task)  # 占用唯一工作线程
            time.sleep(0.05)
            second = bounded.submit(lambda: 1)  # 排队（淘汰正在运行的 first，取消失败）
            third = bounded.submit(lambda: 2)  # 队列满 → 淘汰可取消的 second
            start.set()
            first.result(timeout=3)
            third.result(timeout=3)
            assert second.cancelled()
            assert bounded.pending_count() <= 1

    def test_shutdown_passthrough(self):
        """shutdown 透传到底层线程池"""
        pool = ThreadPoolExecutor(max_workers=1)
        bounded = BoundedExecutor(pool, max_queued=4)
        bounded.shutdown(wait=False)
        assert pool._shutdown
