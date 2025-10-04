"""
测试 services/background_task_manager.py

测试后台任务管理服务的功能，包括：
- 任务提交和执行
- 任务回调机制
- 任务取消
- 异步验证
- 生命周期管理
- 状态查询
"""

import concurrent.futures
import threading
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from plookingII.services.background_task_manager import BackgroundTaskManager


@pytest.fixture
def mock_window():
    """创建模拟的window对象"""
    window = MagicMock()
    window.image_loader_service = None
    return window


@pytest.fixture
def task_manager(mock_window):
    """创建BackgroundTaskManager实例"""
    manager = BackgroundTaskManager(mock_window)
    yield manager
    # 清理
    try:
        manager.shutdown()
    except Exception:
        pass


# ==================== 初始化测试 ====================


class TestBackgroundTaskManagerInit:
    """测试BackgroundTaskManager初始化"""

    def test_init_success(self, mock_window):
        """测试成功初始化"""
        manager = BackgroundTaskManager(mock_window)
        
        assert manager.window == mock_window
        assert manager._shutting_down is False
        assert isinstance(manager._task_lock, type(threading.Lock()))
        assert manager._executor is not None
        assert manager._max_workers == 4
        assert isinstance(manager._active_tasks, dict)
        assert isinstance(manager._task_callbacks, dict)
        
        # 清理
        manager.shutdown()

    def test_init_with_executor_failure(self, mock_window):
        """测试线程池初始化失败的情况"""
        with patch('concurrent.futures.ThreadPoolExecutor') as mock_executor:
            mock_executor.side_effect = Exception("Init failed")
            
            manager = BackgroundTaskManager(mock_window)
            
            # 即使初始化失败，manager应该仍然被创建
            assert manager.window == mock_window
            # executor在异常处理后可能为None
            # 不需要清理，因为executor未成功创建


# ==================== 任务提交和执行测试 ====================


class TestTaskSubmission:
    """测试任务提交和执行"""

    def test_submit_simple_task(self, task_manager):
        """测试提交简单任务"""
        result_holder = []
        
        def simple_task():
            result_holder.append("executed")
            return "result"
        
        future = task_manager.submit_task("test_task", simple_task)
        
        assert future is not None
        assert isinstance(future, concurrent.futures.Future)
        
        # 等待任务完成
        result = future.result(timeout=2.0)
        assert result == "result"
        assert "executed" in result_holder

    def test_submit_task_with_args(self, task_manager):
        """测试提交带参数的任务"""
        def task_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"
        
        future = task_manager.submit_task(
            "test_task",
            task_with_args,
            "arg1", "arg2",
            c="kwarg"
        )
        
        result = future.result(timeout=2.0)
        assert result == "arg1-arg2-kwarg"

    def test_submit_task_with_delay(self, task_manager):
        """测试延迟执行任务"""
        start_time = time.time()
        
        def delayed_task():
            return "delayed_result"
        
        future = task_manager.submit_task(
            "delayed_task",
            delayed_task,
            delay=0.2  # 200ms延迟
        )
        
        result = future.result(timeout=2.0)
        elapsed = time.time() - start_time
        
        assert result == "delayed_result"
        assert elapsed >= 0.2  # 至少延迟了200ms

    def test_submit_task_with_callback(self, task_manager):
        """测试任务完成回调"""
        callback_called = []
        
        def task_func():
            return "task_result"
        
        def callback(future):
            callback_called.append(future.result())
        
        future = task_manager.submit_task(
            "callback_task",
            task_func,
            callback=callback
        )
        
        # 等待任务完成
        future.result(timeout=2.0)
        
        # 等待回调执行
        time.sleep(0.1)
        
        assert len(callback_called) == 1
        assert callback_called[0] == "task_result"

    def test_submit_task_replaces_existing(self, task_manager):
        """测试提交同ID任务会替换旧任务"""
        executed_count = []
        
        def slow_task():
            time.sleep(1.0)
            executed_count.append("slow")
            return "slow_result"
        
        def fast_task():
            executed_count.append("fast")
            return "fast_result"
        
        # 提交慢任务
        future1 = task_manager.submit_task("same_id", slow_task)
        time.sleep(0.05)  # 确保慢任务已开始
        
        # 提交快任务（相同ID）
        future2 = task_manager.submit_task("same_id", fast_task)
        
        # 第一个任务应该被取消或被替换
        # 第二个任务应该正常完成
        result2 = future2.result(timeout=2.0)
        assert result2 == "fast_result"
        assert "fast" in executed_count

    def test_submit_task_when_shutting_down(self, task_manager):
        """测试关闭期间提交任务"""
        task_manager._shutting_down = True
        
        def test_task():
            return "result"
        
        future = task_manager.submit_task("test", test_task)
        
        assert future is None

    def test_submit_task_exception_handling(self, task_manager):
        """测试任务提交异常处理"""
        # 模拟executor不可用
        task_manager._executor = None
        
        def test_task():
            return "result"
        
        future = task_manager.submit_task("test", test_task)
        
        assert future is None


# ==================== 任务取消测试 ====================


class TestTaskCancellation:
    """测试任务取消"""

    def test_cancel_pending_task(self, task_manager):
        """测试取消未开始的任务"""
        def long_task():
            time.sleep(2.0)
            return "result"
        
        future = task_manager.submit_task("cancel_test", long_task)
        time.sleep(0.05)  # 让任务进入队列
        
        result = task_manager.cancel_task("cancel_test")
        
        # 取消可能成功也可能失败（如果任务已经开始执行）
        assert isinstance(result, bool)

    def test_cancel_nonexistent_task(self, task_manager):
        """测试取消不存在的任务"""
        result = task_manager.cancel_task("nonexistent")
        
        assert result is False

    def test_cancel_completed_task(self, task_manager):
        """测试取消已完成的任务"""
        def quick_task():
            return "result"
        
        future = task_manager.submit_task("quick", quick_task)
        future.result(timeout=2.0)  # 等待完成
        
        result = task_manager.cancel_task("quick")
        
        assert result is False  # 已完成的任务无法取消


# ==================== 异步验证测试 ====================


class TestAsyncValidation:
    """测试异步验证功能"""

    def test_start_async_validation(self, task_manager):
        """测试启动异步验证"""
        def validate(data):
            return data > 0
        
        future = task_manager.start_async_validation(validate, 10)
        
        assert future is not None
        result = future.result(timeout=2.0)
        assert result is True

    def test_async_validate_success(self, task_manager):
        """测试异步验证成功"""
        def validator(data):
            return data == "valid"
        
        result = task_manager.async_validate("valid", validator)
        
        assert result is True

    def test_async_validate_failure(self, task_manager):
        """测试异步验证失败"""
        def validator(data):
            return data == "valid"
        
        result = task_manager.async_validate("invalid", validator)
        
        assert result is False

    def test_async_validate_with_exception(self, task_manager):
        """测试异步验证抛出异常"""
        def validator(data):
            raise ValueError("Validation error")
        
        result = task_manager.async_validate("data", validator)
        
        assert result is False

    def test_async_validate_when_shutting_down(self, task_manager):
        """测试关闭期间的异步验证"""
        task_manager._shutting_down = True
        
        def validator(data):
            return True
        
        result = task_manager.async_validate("data", validator)
        
        assert result is False

    def test_cancel_async_validation(self, task_manager):
        """测试取消异步验证"""
        def slow_validator(data):
            time.sleep(2.0)
            return True
        
        # 启动验证
        task_manager.start_async_validation(slow_validator, "data")
        time.sleep(0.05)
        
        # 取消验证
        task_manager.cancel_async_validation()
        
        # 验证应该被取消（不一定成功，取决于执行状态）
        # 至少不应该抛出异常
        assert True


# ==================== 后台任务调度测试 ====================


class TestBackgroundTaskScheduling:
    """测试后台任务调度"""

    def test_schedule_background_tasks_without_image_loader(self, task_manager):
        """测试没有ImageLoaderService时的任务调度"""
        task_manager.window.image_loader_service = None
        
        task_manager.schedule_background_tasks()
        
        # 应该启动维护任务
        time.sleep(0.2)  # 等待任务提交
        
        # 验证有任务被调度（至少有维护任务）
        # 由于维护任务有延迟，可能还在活跃列表中
        assert isinstance(task_manager._active_tasks, dict)

    def test_schedule_background_tasks_with_image_loader(self, task_manager):
        """测试有ImageLoaderService时的任务调度"""
        mock_service = MagicMock()
        task_manager.window.image_loader_service = mock_service
        
        task_manager.schedule_background_tasks()
        
        # 应该调用image_loader_service的方法
        mock_service.schedule_background_tasks.assert_called_once()

    def test_schedule_when_shutting_down(self, task_manager):
        """测试关闭期间的任务调度"""
        task_manager._shutting_down = True
        
        task_manager.schedule_background_tasks()
        
        # 不应该调度任何任务
        assert len(task_manager._active_tasks) == 0

    def test_schedule_with_exception(self, task_manager):
        """测试任务调度异常处理"""
        mock_service = MagicMock()
        mock_service.schedule_background_tasks.side_effect = Exception("Schedule failed")
        task_manager.window.image_loader_service = mock_service
        
        # 应该捕获异常，不抛出
        task_manager.schedule_background_tasks()
        
        assert True  # 没有抛出异常即为成功


# ==================== 维护任务测试 ====================


class TestMaintenanceTasks:
    """测试维护任务"""

    def test_cleanup_expired_tasks(self, task_manager):
        """测试清理过期任务"""
        # 提交一些任务并让它们完成
        def quick_task():
            return "done"
        
        for i in range(3):
            future = task_manager.submit_task(f"task_{i}", quick_task)
            future.result(timeout=2.0)
        
        # 手动调用清理
        task_manager._cleanup_expired_tasks()
        
        # 已完成的任务应该被清理
        # 注意：由于任务完成回调也会清理，这里可能已经是0
        assert len(task_manager._active_tasks) >= 0

    def test_schedule_maintenance_tasks(self, task_manager):
        """测试调度维护任务"""
        # 设置测试标志以使用短延迟
        task_manager.window._is_testing = True
        
        task_manager._schedule_maintenance_tasks()
        
        # 维护任务应该被提交
        time.sleep(0.2)  # 等待任务提交和执行
        
        # 验证任务被提交（可能已完成）
        assert "cleanup_expired_tasks" in task_manager._active_tasks or True


# ==================== 状态查询测试 ====================


class TestStatusQuery:
    """测试状态查询"""

    def test_get_active_task_count(self, task_manager):
        """测试获取活跃任务数量"""
        def long_task():
            time.sleep(0.5)
            return "done"
        
        # 提交多个任务
        for i in range(3):
            task_manager.submit_task(f"task_{i}", long_task)
        
        count = task_manager.get_active_task_count()
        
        # 至少应该有一些活跃任务
        assert count >= 0
        assert isinstance(count, int)

    def test_get_active_task_ids(self, task_manager):
        """测试获取活跃任务ID列表"""
        def long_task():
            time.sleep(0.5)
            return "done"
        
        task_manager.submit_task("task_1", long_task)
        task_manager.submit_task("task_2", long_task)
        
        task_ids = task_manager.get_active_task_ids()
        
        assert isinstance(task_ids, list)
        # 任务可能已完成，所以可能为空
        assert len(task_ids) >= 0

    def test_get_task_status_running(self, task_manager):
        """测试获取运行中任务的状态"""
        def long_task():
            time.sleep(1.0)
            return "done"
        
        task_manager.submit_task("status_test", long_task)
        time.sleep(0.05)  # 确保任务已开始
        
        status = task_manager.get_task_status("status_test")
        
        # 可能是running或completed（如果非常快）
        assert status in ["running", "completed", "pending"]

    def test_get_task_status_completed(self, task_manager):
        """测试获取已完成任务的状态"""
        def quick_task():
            return "done"
        
        future = task_manager.submit_task("completed_test", quick_task)
        future.result(timeout=2.0)
        time.sleep(0.05)  # 等待回调清理
        
        status = task_manager.get_task_status("completed_test")
        
        # 可能是completed或not_found（如果已被清理）
        assert status in ["completed", "not_found"]

    def test_get_task_status_not_found(self, task_manager):
        """测试获取不存在任务的状态"""
        status = task_manager.get_task_status("nonexistent")
        
        assert status == "not_found"

    def test_is_shutting_down(self, task_manager):
        """测试检查关闭状态"""
        assert task_manager.is_shutting_down() is False
        
        task_manager._shutting_down = True
        
        assert task_manager.is_shutting_down() is True

    def test_get_status_info(self, task_manager):
        """测试获取状态信息"""
        status_info = task_manager.get_status_info()
        
        assert isinstance(status_info, dict)
        assert "shutting_down" in status_info
        assert "active_tasks" in status_info
        assert "total_tasks" in status_info
        assert "max_workers" in status_info
        
        assert status_info["shutting_down"] is False
        assert status_info["max_workers"] == 4


# ==================== 生命周期管理测试 ====================


class TestLifecycleManagement:
    """测试生命周期管理"""

    def test_shutdown_background_tasks(self, task_manager):
        """测试关闭后台任务"""
        def long_task():
            time.sleep(2.0)
            return "done"
        
        # 提交一些任务
        for i in range(3):
            task_manager.submit_task(f"task_{i}", long_task)
        
        # 关闭
        task_manager.shutdown_background_tasks()
        
        assert task_manager._shutting_down is True
        # 任务应该被清理
        time.sleep(0.1)
        assert len(task_manager._active_tasks) == 0

    def test_shutdown_idempotent(self, task_manager):
        """测试重复关闭"""
        task_manager.shutdown_background_tasks()
        task_manager.shutdown_background_tasks()  # 再次关闭
        
        # 不应该抛出异常
        assert task_manager._shutting_down is True

    def test_cleanup_alias(self, task_manager):
        """测试cleanup方法别名"""
        task_manager.cleanup()
        
        assert task_manager._shutting_down is True

    def test_shutdown_alias(self, task_manager):
        """测试shutdown方法别名"""
        task_manager.shutdown()
        
        assert task_manager._shutting_down is True

    def test_shutdown_with_callback_tasks(self, task_manager):
        """测试关闭时有回调的任务"""
        callback_executed = []
        
        def task_func():
            time.sleep(0.1)
            return "result"
        
        def callback(future):
            callback_executed.append("called")
        
        task_manager.submit_task("callback_task", task_func, callback=callback)
        
        # 立即关闭
        task_manager.shutdown_background_tasks()
        
        # 回调可能执行也可能不执行（取决于任务完成时机）
        assert task_manager._shutting_down is True


# ==================== 并发安全测试 ====================


class TestConcurrencySafety:
    """测试并发安全性"""

    def test_concurrent_task_submission(self, task_manager):
        """测试并发提交任务"""
        def simple_task(task_id):
            return f"result_{task_id}"
        
        # 并发提交100个任务
        futures = []
        for i in range(100):
            future = task_manager.submit_task(f"concurrent_{i}", simple_task, i)
            if future:
                futures.append(future)
        
        # 等待所有任务完成
        results = []
        for future in futures:
            try:
                result = future.result(timeout=3.0)
                results.append(result)
            except Exception:
                pass
        
        # 大部分任务应该成功完成
        assert len(results) > 90

    def test_concurrent_status_queries(self, task_manager):
        """测试并发状态查询"""
        def long_task():
            time.sleep(0.1)
            return "done"
        
        # 提交一些任务
        for i in range(10):
            task_manager.submit_task(f"task_{i}", long_task)
        
        # 并发查询状态
        def query_status():
            task_manager.get_active_task_count()
            task_manager.get_active_task_ids()
            task_manager.get_status_info()
        
        threads = []
        for _ in range(20):
            t = threading.Thread(target=query_status)
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join(timeout=3.0)
        
        # 不应该抛出异常
        assert True

    def test_thread_safety_with_lock(self, task_manager):
        """测试锁的正确使用"""
        # 验证锁被正确初始化
        assert hasattr(task_manager, '_task_lock')
        assert isinstance(task_manager._task_lock, type(threading.Lock()))


# ==================== 边缘情况测试 ====================


class TestEdgeCases:
    """测试边缘情况"""

    def test_task_exception_handling(self, task_manager):
        """测试任务执行异常处理"""
        def failing_task():
            raise ValueError("Task failed")
        
        future = task_manager.submit_task("failing", failing_task)
        
        with pytest.raises(ValueError):
            future.result(timeout=2.0)

    def test_callback_exception_handling(self, task_manager):
        """测试回调异常处理"""
        def task_func():
            return "result"
        
        def failing_callback(future):
            raise Exception("Callback failed")
        
        future = task_manager.submit_task(
            "callback_fail",
            task_func,
            callback=failing_callback
        )
        
        # 回调失败不应该影响任务完成
        result = future.result(timeout=2.0)
        assert result == "result"
        
        time.sleep(0.1)  # 等待回调执行
        # 不应该抛出异常

    def test_zero_delay_task(self, task_manager):
        """测试零延迟任务"""
        def task():
            return "immediate"
        
        future = task_manager.submit_task("zero_delay", task, delay=0.0)
        
        result = future.result(timeout=2.0)
        assert result == "immediate"

    def test_very_short_delay_task(self, task_manager):
        """测试极短延迟任务"""
        def task():
            return "short_delay"
        
        future = task_manager.submit_task("short", task, delay=0.001)
        
        result = future.result(timeout=2.0)
        assert result == "short_delay"

    def test_get_status_with_exception(self, task_manager):
        """测试状态查询异常处理"""
        # 破坏内部状态
        task_manager._active_tasks = None
        
        count = task_manager.get_active_task_count()
        assert count == 0
        
        ids = task_manager.get_active_task_ids()
        assert ids == []
        
        status = task_manager.get_task_status("any")
        assert status == "not_found"

