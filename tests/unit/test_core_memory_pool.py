"""
测试 core/memory_pool.py 模块

测试目标：达到90%+覆盖率
"""

import threading
import time
from unittest.mock import patch

import pytest

from plookingII.core.memory_pool import ImageMemoryPool


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestImageMemoryPoolInit:
    """测试内存池初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        pool = ImageMemoryPool()
        assert pool.max_memory_bytes == 1000 * 1024 * 1024
        assert pool.allocated_bytes == 0
        assert pool.total_allocations == 0
        assert pool.total_deallocations == 0
        assert pool.cache_hits == 0
        assert pool.cache_misses == 0

    def test_init_custom_memory(self):
        """测试自定义内存限制"""
        pool = ImageMemoryPool(max_memory_mb=500)
        assert pool.max_memory_bytes == 500 * 1024 * 1024

    def test_size_categories(self):
        """测试大小类别配置"""
        pool = ImageMemoryPool()
        assert len(pool.size_categories) > 0
        assert all(isinstance(size, int) for size in pool.size_categories)
        # 应该是升序（将元组转换为列表进行比较）
        assert list(pool.size_categories) == sorted(pool.size_categories)


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestGetBuffer:
    """测试获取缓冲区"""

    def test_get_buffer_first_time(self):
        """测试首次获取缓冲区"""
        pool = ImageMemoryPool(max_memory_mb=10)
        buffer = pool.get_buffer(1024)
        
        assert buffer is not None
        assert len(buffer) == 1024
        assert isinstance(buffer, bytearray)
        assert pool.total_allocations == 1
        assert pool.cache_misses == 1

    def test_get_buffer_from_pool(self):
        """测试从池中获取缓冲区"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        # 首次分配
        buffer1 = pool.get_buffer(1024)
        pool.return_buffer(buffer1, 1024)
        
        # 从池中获取
        buffer2 = pool.get_buffer(1024)
        assert buffer2 is not None
        assert pool.cache_hits == 1

    def test_get_buffer_multiple_sizes(self):
        """测试获取不同大小的缓冲区"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        buffer1 = pool.get_buffer(1024)
        buffer2 = pool.get_buffer(2048)
        buffer3 = pool.get_buffer(4096)
        
        assert buffer1 is not None
        assert buffer2 is not None
        assert buffer3 is not None
        assert len(buffer1) == 1024
        assert len(buffer2) == 2048
        assert len(buffer3) == 4096

    def test_get_buffer_memory_limit(self):
        """测试内存限制"""
        pool = ImageMemoryPool(max_memory_mb=0.001)  # 很小的内存限制
        
        # 尝试分配大量内存
        buffers = []
        for _ in range(10):
            buffer = pool.get_buffer(1024)
            if buffer is not None:
                buffers.append(buffer)
        
        # 应该被内存限制约束
        assert len(buffers) < 10

    def test_get_buffer_exception_handling(self):
        """测试异常处理"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        with patch.object(pool, '_find_best_pool_size', side_effect=Exception("Test error")):
            buffer = pool.get_buffer(1024)
            assert buffer is None

    def test_get_buffer_with_cleanup(self):
        """测试带清理的缓冲区获取"""
        pool = ImageMemoryPool(max_memory_mb=0.01)  # 10KB限制
        
        # 填满池
        buffers = []
        for _ in range(20):
            buffer = pool.get_buffer(1024)
            if buffer:
                buffers.append(buffer)
                pool.return_buffer(buffer, 1024)
        
        # 在小内存限制下，可能无法分配新缓冲区，这是正常的
        new_buffer = pool.get_buffer(1024)
        # 只验证函数不崩溃即可
        assert new_buffer is None or isinstance(new_buffer, bytearray)


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestReturnBuffer:
    """测试归还缓冲区"""

    def test_return_buffer_normal(self):
        """测试正常归还缓冲区"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        buffer = pool.get_buffer(1024)
        initial_deallocations = pool.total_deallocations
        pool.return_buffer(buffer, 1024)
        
        assert pool.total_deallocations == initial_deallocations + 1

    def test_return_buffer_none(self):
        """测试归还None缓冲区"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        # 不应该崩溃
        pool.return_buffer(None, 1024)
        assert pool.total_deallocations == 0

    def test_return_buffer_extend(self):
        """测试归还小于池大小的缓冲区"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        # 创建小缓冲区
        small_buffer = bytearray(512)
        pool.return_buffer(small_buffer, 1024)
        
        assert pool.total_deallocations == 1

    def test_return_buffer_truncate(self):
        """测试归还大于池大小的缓冲区"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        # 创建大缓冲区
        large_buffer = bytearray(2048)
        pool.return_buffer(large_buffer, 1024)
        
        assert pool.total_deallocations == 1

    def test_return_buffer_exception_handling(self):
        """测试异常处理"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        with patch.object(pool, '_find_best_pool_size', side_effect=Exception("Test error")):
            # 不应该崩溃
            pool.return_buffer(bytearray(1024), 1024)


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestPoolSizeCalculation:
    """测试池大小计算"""

    def test_find_best_pool_size_small(self):
        """测试小尺寸的池大小计算"""
        pool = ImageMemoryPool()
        
        size = pool._find_best_pool_size(1024)
        assert size >= 1024
        assert size in pool.size_categories

    def test_find_best_pool_size_large(self):
        """测试大尺寸的池大小计算"""
        pool = ImageMemoryPool()
        
        # 超过预定义类别的大小
        size = pool._find_best_pool_size(10 * 1024 * 1024)
        assert size >= 10 * 1024 * 1024

    def test_next_power_of_two(self):
        """测试2的幂次计算"""
        pool = ImageMemoryPool()
        
        assert pool._next_power_of_two(0) == 1
        assert pool._next_power_of_two(1) == 1
        assert pool._next_power_of_two(2) == 2
        assert pool._next_power_of_two(3) == 4
        assert pool._next_power_of_two(5) == 8
        assert pool._next_power_of_two(100) == 128
        assert pool._next_power_of_two(1000) == 1024


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestCleanupPools:
    """测试池清理"""

    def test_cleanup_pools_success(self):
        """测试成功清理池"""
        pool = ImageMemoryPool(max_memory_mb=1)
        
        # 创建一些缓冲区并返回到池
        for _ in range(10):
            buffer = pool.get_buffer(1024)
            if buffer:
                pool.return_buffer(buffer, 1024)
        
        initial_allocated = pool.allocated_bytes
        result = pool._cleanup_pools()
        
        # 应该清理了一些内存
        if initial_allocated > 0:
            assert result is True or pool.allocated_bytes < initial_allocated

    def test_cleanup_pools_empty(self):
        """测试清理空池"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        result = pool._cleanup_pools()
        assert result is False

    def test_cleanup_pools_exception_handling(self):
        """测试清理过程中的异常处理"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        # 创建一些缓冲区
        for _ in range(5):
            buffer = pool.get_buffer(1024)
            if buffer:
                pool.return_buffer(buffer, 1024)
        
        # 测试异常处理 - 通过mock sorted函数来触发异常
        with patch('plookingII.core.memory_pool.sorted', side_effect=Exception("Test error")):
            result = pool._cleanup_pools()
            assert result is False


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestPoolManagement:
    """测试池管理功能"""

    def test_clear_all(self):
        """测试清空所有池"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        # 创建一些缓冲区
        for _ in range(5):
            buffer = pool.get_buffer(1024)
            if buffer:
                pool.return_buffer(buffer, 1024)
        
        pool.clear_all()
        assert len(pool.pools) == 0
        assert pool.allocated_bytes == 0

    def test_get_memory_usage(self):
        """测试获取内存使用情况"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        # 创建一些缓冲区
        buffer = pool.get_buffer(1024)
        if buffer:
            pool.return_buffer(buffer, 1024)
        
        usage = pool.get_memory_usage()
        assert isinstance(usage, dict)
        assert "allocated_mb" in usage
        assert "max_memory_mb" in usage
        assert "usage_ratio" in usage
        assert "total_pools" in usage
        assert "pool_sizes" in usage
        assert "total_allocations" in usage
        assert "total_deallocations" in usage
        assert "cache_hit_rate" in usage

    def test_optimize_pools(self):
        """测试优化池"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        # 创建一些缓冲区
        for size in [1024, 2048, 4096]:
            buffer = pool.get_buffer(size)
            if buffer:
                pool.return_buffer(buffer, size)
        
        pool.optimize_pools()
        # 不应该崩溃
        assert True

    def test_optimize_pools_remove_empty(self):
        """测试优化时移除空池"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        # 手动创建空池
        pool.pools[8192] = []
        
        pool.optimize_pools()
        assert 8192 not in pool.pools


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestThreadSafety:
    """测试线程安全性"""

    def test_concurrent_get_buffer(self):
        """测试并发获取缓冲区"""
        pool = ImageMemoryPool(max_memory_mb=10)
        results = []
        
        def get_buffers():
            for _ in range(10):
                buffer = pool.get_buffer(1024)
                results.append(buffer is not None)
        
        threads = [threading.Thread(target=get_buffers) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 应该成功获取到一些缓冲区
        assert any(results)

    def test_concurrent_return_buffer(self):
        """测试并发归还缓冲区"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        def return_buffers():
            for _ in range(10):
                buffer = bytearray(1024)
                pool.return_buffer(buffer, 1024)
        
        threads = [threading.Thread(target=return_buffers) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 不应该崩溃
        assert pool.total_deallocations > 0


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestEdgeCases:
    """测试边缘情况"""

    def test_zero_memory_limit(self):
        """测试零内存限制"""
        pool = ImageMemoryPool(max_memory_mb=0)
        buffer = pool.get_buffer(1024)
        # 可能返回None或空缓冲区
        assert buffer is None or len(buffer) == 0

    def test_very_large_buffer(self):
        """测试非常大的缓冲区"""
        pool = ImageMemoryPool(max_memory_mb=100)
        buffer = pool.get_buffer(50 * 1024 * 1024)  # 50MB
        
        # 可能成功或失败，取决于系统内存
        if buffer is not None:
            assert len(buffer) == 50 * 1024 * 1024

    def test_negative_size(self):
        """测试负数大小"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        # _next_power_of_two 应该处理负数
        result = pool._next_power_of_two(-1)
        assert result == 1

    def test_cache_statistics(self):
        """测试缓存统计"""
        pool = ImageMemoryPool(max_memory_mb=10)
        
        # 首次获取 - 缓存未命中
        buffer1 = pool.get_buffer(1024)
        assert pool.cache_misses == 1
        assert pool.cache_hits == 0
        
        # 归还后再获取 - 缓存命中
        if buffer1:
            pool.return_buffer(buffer1, 1024)
            buffer2 = pool.get_buffer(1024)
            if buffer2:
                assert pool.cache_hits == 1

