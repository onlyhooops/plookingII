"""
测试 core/threading.py

测试优化的线程池执行器功能，包括：
- _PatchedThreadPoolExecutor初始化
- 自适应线程数量计算
- CPU核心数检测
- 线程池资源管理
- ThreadPoolExecutor兼容性
"""

from unittest.mock import MagicMock, Mock, patch
import os
import time

import pytest

from plookingII.core.threading import _PatchedThreadPoolExecutor


# ==================== 初始化测试 ====================


class TestPatchedThreadPoolExecutorInit:
    """测试_PatchedThreadPoolExecutor初始化"""

    def test_init_with_explicit_max_workers(self):
        """测试显式指定max_workers"""
        executor = _PatchedThreadPoolExecutor(max_workers=10)
        
        # 验证max_workers被正确设置
        assert executor._max_workers == 10
        
        executor.shutdown(wait=False)

    def test_init_without_max_workers(self):
        """测试不指定max_workers（自动计算）"""
        with patch('plookingII.core.threading.os.cpu_count') as mock_cpu_count:
            mock_cpu_count.return_value = 4
            
            executor = _PatchedThreadPoolExecutor()
            
            # 应该计算为 4 * 4 = 16
            assert executor._max_workers == 16
            
            executor.shutdown(wait=False)

    def test_init_with_none_max_workers(self):
        """测试显式传入None作为max_workers"""
        with patch('plookingII.core.threading.os.cpu_count') as mock_cpu_count:
            mock_cpu_count.return_value = 8
            
            executor = _PatchedThreadPoolExecutor(max_workers=None)
            
            # 应该计算为 8 * 4 = 32
            assert executor._max_workers == 32
            
            executor.shutdown(wait=False)

    def test_init_with_args_and_kwargs(self):
        """测试传入额外的args和kwargs"""
        executor = _PatchedThreadPoolExecutor(
            max_workers=5,
            thread_name_prefix="test_thread"
        )
        
        assert executor._max_workers == 5
        
        executor.shutdown(wait=False)


# ==================== CPU核心数计算测试 ====================


class TestCPUCountCalculation:
    """测试CPU核心数计算逻辑"""

    def test_cpu_count_calculation_4_cores(self):
        """测试4核CPU的计算"""
        with patch('plookingII.core.threading.os.cpu_count') as mock_cpu_count:
            mock_cpu_count.return_value = 4
            
            executor = _PatchedThreadPoolExecutor()
            
            # 4 * 4 = 16
            assert executor._max_workers == 16
            
            executor.shutdown(wait=False)

    def test_cpu_count_calculation_8_cores(self):
        """测试8核CPU的计算"""
        with patch('plookingII.core.threading.os.cpu_count') as mock_cpu_count:
            mock_cpu_count.return_value = 8
            
            executor = _PatchedThreadPoolExecutor()
            
            # 8 * 4 = 32
            assert executor._max_workers == 32
            
            executor.shutdown(wait=False)

    def test_cpu_count_calculation_16_cores(self):
        """测试16核CPU的计算（达到上限）"""
        with patch('plookingII.core.threading.os.cpu_count') as mock_cpu_count:
            mock_cpu_count.return_value = 16
            
            executor = _PatchedThreadPoolExecutor()
            
            # 16 * 4 = 64 (不超过上限)
            assert executor._max_workers == 64
            
            executor.shutdown(wait=False)

    def test_cpu_count_calculation_32_cores(self):
        """测试32核CPU的计算（超过上限）"""
        with patch('plookingII.core.threading.os.cpu_count') as mock_cpu_count:
            mock_cpu_count.return_value = 32
            
            executor = _PatchedThreadPoolExecutor()
            
            # 32 * 4 = 128, 但应该限制在 64
            assert executor._max_workers == 64
            
            executor.shutdown(wait=False)

    def test_cpu_count_calculation_1_core(self):
        """测试1核CPU的计算"""
        with patch('plookingII.core.threading.os.cpu_count') as mock_cpu_count:
            mock_cpu_count.return_value = 1
            
            executor = _PatchedThreadPoolExecutor()
            
            # 1 * 4 = 4
            assert executor._max_workers == 4
            
            executor.shutdown(wait=False)

    def test_cpu_count_returns_none(self):
        """测试cpu_count返回None的情况"""
        with patch('plookingII.core.threading.os.cpu_count') as mock_cpu_count:
            mock_cpu_count.return_value = None
            
            executor = _PatchedThreadPoolExecutor()
            
            # 应该回退到 1 * 4 = 4
            assert executor._max_workers == 4
            
            executor.shutdown(wait=False)


# ==================== 线程池功能测试 ====================


class TestThreadPoolFunctionality:
    """测试线程池基本功能"""

    def test_submit_task(self):
        """测试提交任务"""
        executor = _PatchedThreadPoolExecutor(max_workers=2)
        
        def test_func(x):
            return x * 2
        
        future = executor.submit(test_func, 5)
        result = future.result(timeout=1)
        
        assert result == 10
        
        executor.shutdown(wait=True)

    def test_submit_multiple_tasks(self):
        """测试提交多个任务"""
        executor = _PatchedThreadPoolExecutor(max_workers=4)
        
        def test_func(x):
            return x ** 2
        
        futures = [executor.submit(test_func, i) for i in range(10)]
        results = [f.result(timeout=1) for f in futures]
        
        assert results == [i ** 2 for i in range(10)]
        
        executor.shutdown(wait=True)

    def test_map_functionality(self):
        """测试map功能"""
        executor = _PatchedThreadPoolExecutor(max_workers=2)
        
        def test_func(x):
            return x + 1
        
        results = list(executor.map(test_func, range(5)))
        
        assert results == [1, 2, 3, 4, 5]
        
        executor.shutdown(wait=True)

    def test_shutdown(self):
        """测试关闭线程池"""
        executor = _PatchedThreadPoolExecutor(max_workers=2)
        
        def test_func():
            time.sleep(0.1)
            return True
        
        future = executor.submit(test_func)
        executor.shutdown(wait=True)
        
        # 关闭后任务应该已完成
        assert future.done()

    def test_context_manager(self):
        """测试上下文管理器"""
        with _PatchedThreadPoolExecutor(max_workers=2) as executor:
            def test_func(x):
                return x * 3
            
            future = executor.submit(test_func, 7)
            result = future.result(timeout=1)
            
            assert result == 21
        
        # 退出上下文后线程池应该已关闭
        # （无需额外验证，如果有问题会抛出异常）


# ==================== 边缘情况测试 ====================


class TestEdgeCases:
    """测试边缘情况"""

    def test_zero_max_workers(self):
        """测试max_workers为0（虽然不推荐）"""
        # ThreadPoolExecutor可能会处理这种情况，我们只验证不崩溃
        try:
            executor = _PatchedThreadPoolExecutor(max_workers=0)
            executor.shutdown(wait=False)
        except ValueError:
            # 如果抛出ValueError是预期的
            pass

    def test_negative_max_workers(self):
        """测试max_workers为负数"""
        # 应该被ThreadPoolExecutor拒绝
        with pytest.raises(ValueError):
            executor = _PatchedThreadPoolExecutor(max_workers=-1)

    def test_very_large_max_workers(self):
        """测试非常大的max_workers"""
        executor = _PatchedThreadPoolExecutor(max_workers=1000)
        
        assert executor._max_workers == 1000
        
        executor.shutdown(wait=False)

    def test_task_exception_handling(self):
        """测试任务异常处理"""
        executor = _PatchedThreadPoolExecutor(max_workers=2)
        
        def error_func():
            raise ValueError("Test error")
        
        future = executor.submit(error_func)
        
        # 应该可以捕获异常
        with pytest.raises(ValueError, match="Test error"):
            future.result(timeout=1)
        
        executor.shutdown(wait=True)


# ==================== 性能和并发测试 ====================


class TestPerformanceAndConcurrency:
    """测试性能和并发"""

    def test_concurrent_execution(self):
        """测试并发执行"""
        executor = _PatchedThreadPoolExecutor(max_workers=4)
        
        start_times = {}
        
        def test_func(task_id):
            start_times[task_id] = time.time()
            time.sleep(0.1)
            return task_id
        
        futures = [executor.submit(test_func, i) for i in range(8)]
        results = [f.result(timeout=2) for f in futures]
        
        # 验证所有任务都完成
        assert len(results) == 8
        assert set(results) == set(range(8))
        
        executor.shutdown(wait=True)

    def test_multiple_executors(self):
        """测试创建多个执行器"""
        executor1 = _PatchedThreadPoolExecutor(max_workers=2)
        executor2 = _PatchedThreadPoolExecutor(max_workers=3)
        
        def test_func(x):
            return x
        
        future1 = executor1.submit(test_func, 1)
        future2 = executor2.submit(test_func, 2)
        
        assert future1.result(timeout=1) == 1
        assert future2.result(timeout=1) == 2
        
        executor1.shutdown(wait=True)
        executor2.shutdown(wait=True)


# ==================== 兼容性测试 ====================


class TestCompatibility:
    """测试与ThreadPoolExecutor的兼容性"""

    def test_inheritance(self):
        """测试继承关系"""
        from concurrent.futures import ThreadPoolExecutor
        
        executor = _PatchedThreadPoolExecutor(max_workers=2)
        
        # 应该是ThreadPoolExecutor的实例
        assert isinstance(executor, ThreadPoolExecutor)
        
        executor.shutdown(wait=False)

    def test_all_standard_methods(self):
        """测试所有标准方法都可用"""
        executor = _PatchedThreadPoolExecutor(max_workers=2)
        
        # 验证标准方法存在
        assert hasattr(executor, 'submit')
        assert hasattr(executor, 'map')
        assert hasattr(executor, 'shutdown')
        assert callable(executor.submit)
        assert callable(executor.map)
        assert callable(executor.shutdown)
        
        executor.shutdown(wait=False)


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    def test_real_world_scenario(self):
        """测试真实场景：模拟图像加载任务"""
        executor = _PatchedThreadPoolExecutor(max_workers=4)
        
        def load_image(image_id):
            # 模拟I/O操作
            time.sleep(0.05)
            return f"image_{image_id}_data"
        
        # 提交10个图像加载任务
        futures = [executor.submit(load_image, i) for i in range(10)]
        
        # 等待所有任务完成
        results = [f.result(timeout=2) for f in futures]
        
        # 验证所有图像都被"加载"
        assert len(results) == 10
        assert all("image_" in r and "_data" in r for r in results)
        
        executor.shutdown(wait=True)

    def test_mixed_task_types(self):
        """测试混合任务类型"""
        executor = _PatchedThreadPoolExecutor(max_workers=4)
        
        def cpu_task(x):
            return sum(range(x))
        
        def io_task(x):
            time.sleep(0.01)
            return x * 2
        
        # 混合CPU和I/O任务
        futures = []
        futures.extend([executor.submit(cpu_task, 100) for _ in range(5)])
        futures.extend([executor.submit(io_task, i) for i in range(5)])
        
        results = [f.result(timeout=2) for f in futures]
        
        assert len(results) == 10
        
        executor.shutdown(wait=True)

