"""
统一缓存系统测试

测试重构后的2层缓存架构。

Author: PlookingII Team
Version: 3.0.0
"""

import pytest
import time
from plookingII.core.cache import (
    UnifiedCache,
    CacheConfig,
    CacheEntry,
    get_unified_cache,
    reset_unified_cache,
)


class TestCacheConfig:
    """测试缓存配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = CacheConfig.default()
        assert config.max_memory_mb == 2048.0
        assert config.active_cache_size == 50
        assert config.nearby_cache_size == 30
        assert config.preload_count == 5
        assert config.eviction_policy == "lru"

    def test_lightweight_config(self):
        """测试轻量级配置"""
        config = CacheConfig.lightweight()
        assert config.max_memory_mb == 512.0
        assert config.active_cache_size == 20
        assert config.nearby_cache_size == 10

    def test_performance_config(self):
        """测试高性能配置"""
        config = CacheConfig.performance()
        assert config.max_memory_mb == 4096.0
        assert config.active_cache_size == 100
        assert config.nearby_cache_size == 50

    def test_total_cache_size(self):
        """测试总缓存大小计算"""
        config = CacheConfig(active_cache_size=30, nearby_cache_size=20)
        assert config.total_cache_size == 50

    def test_config_validation(self):
        """测试配置验证"""
        # 测试无效的内存配置
        with pytest.raises(ValueError):
            CacheConfig(max_memory_mb=-1)

        # 测试无效的清理阈值
        with pytest.raises(ValueError):
            CacheConfig(cleanup_threshold=1.5)

        # 测试无效的淘汰策略
        with pytest.raises(ValueError):
            CacheConfig(eviction_policy="invalid")


class TestCacheEntry:
    """测试缓存条目"""

    def test_cache_entry_creation(self):
        """测试缓存条目创建"""
        entry = CacheEntry(value="test", size=10.5, priority=5)
        assert entry.value == "test"
        assert entry.size == 10.5
        assert entry.priority == 5
        assert entry.access_count == 0
        assert entry.creation_time > 0
        assert entry.last_access_time > 0

    def test_cache_entry_auto_init(self):
        """测试缓存条目自动初始化时间戳"""
        entry = CacheEntry(value="test", size=1.0)
        assert entry.creation_time == entry.last_access_time


class TestUnifiedCache:
    """测试统一缓存"""

    def setup_method(self):
        """每个测试前重置缓存"""
        reset_unified_cache()

    def test_cache_initialization(self):
        """测试缓存初始化"""
        config = CacheConfig(
            active_cache_size=10,
            nearby_cache_size=5,
            max_memory_mb=100
        )
        cache = UnifiedCache(config)
        
        stats = cache.get_stats()
        assert stats['active_cache_size'] == 0
        assert stats['nearby_cache_size'] == 0
        assert stats['total_items'] == 0
        assert stats['current_memory_mb'] == 0

    def test_put_and_get_active_cache(self):
        """测试存储和获取（Active Cache）"""
        cache = UnifiedCache()
        
        # 存储到 Active Cache
        success = cache.put('key1', 'value1', size=1.0, is_nearby=False)
        assert success is True
        
        # 获取
        value = cache.get('key1')
        assert value == 'value1'
        
        # 统计
        stats = cache.get_stats()
        assert stats['active_cache_size'] == 1
        assert stats['nearby_cache_size'] == 0

    def test_put_and_get_nearby_cache(self):
        """测试存储和获取（Nearby Cache）"""
        cache = UnifiedCache()
        
        # 存储到 Nearby Cache
        success = cache.put('key1', 'value1', size=1.0, is_nearby=True)
        assert success is True
        
        # 获取（应该被晋升到Active Cache）
        value = cache.get('key1')
        assert value == 'value1'
        
        # 统计（晋升后应该在Active Cache中）
        stats = cache.get_stats()
        assert stats['active_cache_size'] == 1
        assert stats['nearby_cache_size'] == 0

    def test_cache_miss(self):
        """测试缓存未命中"""
        cache = UnifiedCache()
        value = cache.get('nonexistent', default='default_value')
        assert value == 'default_value'

    def test_cache_remove(self):
        """测试移除缓存项"""
        cache = UnifiedCache()
        cache.put('key1', 'value1', size=1.0)
        
        # 确认存在
        assert cache.get('key1') == 'value1'
        
        # 移除
        removed = cache.remove('key1')
        assert removed is True
        
        # 确认已移除
        assert cache.get('key1') is None

    def test_cache_clear(self):
        """测试清空缓存"""
        cache = UnifiedCache()
        cache.put('key1', 'value1', size=1.0)
        cache.put('key2', 'value2', size=1.0, is_nearby=True)
        
        cache.clear()
        
        stats = cache.get_stats()
        assert stats['total_items'] == 0
        assert stats['current_memory_mb'] == 0

    def test_lru_eviction_active_cache(self):
        """测试LRU淘汰（Active Cache）"""
        config = CacheConfig(active_cache_size=3, nearby_cache_size=2)
        cache = UnifiedCache(config)
        
        # 填充缓存
        cache.put('key1', 'value1', size=1.0)
        cache.put('key2', 'value2', size=1.0)
        cache.put('key3', 'value3', size=1.0)
        
        # 添加第4个（应该触发降级到Nearby Cache）
        cache.put('key4', 'value4', size=1.0)
        
        stats = cache.get_stats()
        assert stats['active_cache_size'] == 3
        assert stats['nearby_cache_size'] == 1

    def test_memory_limit_eviction(self):
        """测试内存限制淘汰"""
        config = CacheConfig(max_memory_mb=10.0)  # 10MB限制
        cache = UnifiedCache(config)
        
        # 添加大文件
        cache.put('file1', 'data1', size=4.0)
        cache.put('file2', 'data2', size=4.0)
        cache.put('file3', 'data3', size=4.0)  # 应触发淘汰
        
        stats = cache.get_stats()
        assert stats['current_memory_mb'] <= 10.0
        # file1应该被淘汰了
        assert cache.get('file1') is None

    def test_file_size_limit(self):
        """测试文件大小限制"""
        config = CacheConfig(max_file_size_mb=100.0)
        cache = UnifiedCache(config)
        
        # 尝试添加超大文件
        success = cache.put('huge_file', 'data', size=500.0)
        assert success is False

    def test_promotion_from_nearby_to_active(self):
        """测试从Nearby晋升到Active"""
        cache = UnifiedCache()
        
        # 添加到Nearby Cache
        cache.put('key1', 'value1', size=1.0, is_nearby=True)
        stats = cache.get_stats()
        assert stats['nearby_cache_size'] == 1
        
        # 访问（应该晋升）
        value = cache.get('key1')
        assert value == 'value1'
        
        stats = cache.get_stats()
        assert stats['active_cache_size'] == 1
        assert stats['nearby_cache_size'] == 0

    def test_thread_safety_config(self):
        """测试线程安全配置"""
        config_safe = CacheConfig(thread_safe=True)
        cache_safe = UnifiedCache(config_safe)
        assert cache_safe._lock is not None
        
        config_unsafe = CacheConfig(thread_safe=False)
        cache_unsafe = UnifiedCache(config_unsafe)
        assert cache_unsafe._lock is None


class TestGlobalCache:
    """测试全局缓存单例"""

    def setup_method(self):
        """每个测试前重置"""
        reset_unified_cache()

    def test_global_cache_singleton(self):
        """测试全局缓存单例模式"""
        config = CacheConfig.default()
        cache1 = get_unified_cache(config)
        cache2 = get_unified_cache()  # 应返回同一实例
        
        assert cache1 is cache2

    def test_global_cache_reset(self):
        """测试全局缓存重置"""
        cache1 = get_unified_cache()
        cache1.put('key1', 'value1', size=1.0)
        
        reset_unified_cache()
        
        cache2 = get_unified_cache()
        # 应该是新实例
        assert cache2.get('key1') is None


class TestCacheStatistics:
    """测试缓存统计信息"""

    def setup_method(self):
        """每个测试前重置"""
        reset_unified_cache()

    def test_stats_structure(self):
        """测试统计信息结构"""
        cache = UnifiedCache()
        stats = cache.get_stats()
        
        # 检查必要的字段
        assert 'active_cache_size' in stats
        assert 'nearby_cache_size' in stats
        assert 'total_items' in stats
        assert 'current_memory_mb' in stats
        assert 'max_memory_mb' in stats
        assert 'memory_usage_pct' in stats

    def test_memory_usage_percentage(self):
        """测试内存使用百分比计算"""
        config = CacheConfig(max_memory_mb=100.0)
        cache = UnifiedCache(config)
        
        cache.put('key1', 'value1', size=50.0)
        stats = cache.get_stats()
        
        assert stats['current_memory_mb'] == 50.0
        assert stats['memory_usage_pct'] == 50.0


class TestPerformance:
    """性能测试"""

    def setup_method(self):
        """每个测试前重置"""
        reset_unified_cache()

    def test_large_cache_performance(self):
        """测试大缓存性能"""
        config = CacheConfig(active_cache_size=1000, nearby_cache_size=500)
        cache = UnifiedCache(config)

        # 添加1000个项
        start_time = time.time()
        for i in range(1000):
            cache.put(f'key{i}', f'value{i}', size=0.1)
        put_time = time.time() - start_time

        # 获取1000个项
        start_time = time.time()
        for i in range(1000):
            cache.get(f'key{i}')
        get_time = time.time() - start_time

        # 性能断言（应该很快）
        assert put_time < 1.0  # 1秒内完成
        assert get_time < 0.5  # 0.5秒内完成

    def test_lru_access_order(self):
        """测试LRU访问顺序"""
        config = CacheConfig(active_cache_size=3)
        cache = UnifiedCache(config)
        
        # 添加3个项
        cache.put('key1', 'value1', size=1.0)
        cache.put('key2', 'value2', size=1.0)
        cache.put('key3', 'value3', size=1.0)
        
        # 访问key1（更新访问时间）
        cache.get('key1')
        
        # 添加key4（key2应该被淘汰，因为key1刚被访问）
        cache.put('key4', 'value4', size=1.0)
        
        # key1和key3应该还在Active Cache，key2被降级
        assert cache.get('key1') == 'value1'
        assert cache.get('key3') == 'value3'
        assert cache.get('key4') == 'value4'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
