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


class TestImageManagerNoncriticalSubmit:
    """测试 ImageManager._submit_noncritical 的有界丢弃语义（P2-2）"""

    def test_submit_noncritical_drops_when_queue_full(self):
        """关键池队列满时，非关键任务被丢弃（返回 None）"""
        from unittest.mock import MagicMock, patch

        from plookingII.ui.managers.image_manager import ImageManager

        manager = ImageManager.__new__(ImageManager)
        manager._KEY_EXECUTOR_MAX_QUEUED = 2

        mock_queue = MagicMock()
        mock_queue.qsize.return_value = 2  # 队列已满
        mock_executor = MagicMock()
        mock_executor._work_queue = mock_queue
        manager._executor = mock_executor

        result = manager._submit_noncritical(lambda: 1)

        assert result is None
        mock_executor.submit.assert_not_called()

    def test_submit_noncritical_submits_when_queue_has_space(self):
        """队列未满时非关键任务正常提交"""
        from unittest.mock import MagicMock

        from plookingII.ui.managers.image_manager import ImageManager

        manager = ImageManager.__new__(ImageManager)
        manager._KEY_EXECUTOR_MAX_QUEUED = 8

        mock_queue = MagicMock()
        mock_queue.qsize.return_value = 3
        mock_executor = MagicMock()
        mock_executor._work_queue = mock_queue
        future = MagicMock()
        mock_executor.submit.return_value = future
        manager._executor = mock_executor

        result = manager._submit_noncritical(lambda: 1)

        assert result is future
        mock_executor.submit.assert_called_once()
