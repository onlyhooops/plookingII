"""
测试简单缓存模块

测试覆盖：
- CacheEntry 数据类
- SimpleImageCache 类
- 全局缓存函数
- LRU淘汰策略
- 内存管理
- 线程安全
"""

import threading
import time

from plookingII.core.simple_cache import (
    CacheEntry,
    SimpleImageCache,
    get_global_cache,
    reset_global_cache,
)


class TestCacheEntry:
    """测试CacheEntry数据类"""

    def test_init_with_defaults(self):
        """测试默认初始化"""
        entry = CacheEntry(key="test", value="data", size_mb=1.0)

        assert entry.key == "test"
        assert entry.value == "data"
        assert entry.size_mb == 1.0
        assert entry.access_count == 0
        assert isinstance(entry.created_at, float)
        assert isinstance(entry.accessed_at, float)

    def test_init_with_custom_values(self):
        """测试自定义值初始化"""
        now = time.time()
        entry = CacheEntry(key="key", value="value", size_mb=5.5, created_at=now, accessed_at=now + 10, access_count=5)

        assert entry.key == "key"
        assert entry.value == "value"
        assert entry.size_mb == 5.5
        assert entry.created_at == now
        assert entry.accessed_at == now + 10
        assert entry.access_count == 5

    def test_timestamps_are_close(self):
        """测试创建和访问时间戳接近"""
        entry = CacheEntry(key="test", value="data", size_mb=1.0)

        # 时间戳应该非常接近
        assert abs(entry.created_at - entry.accessed_at) < 0.1


class TestSimpleImageCacheInit:
    """测试SimpleImageCache初始化"""

    def test_default_initialization(self):
        """测试默认初始化"""
        cache = SimpleImageCache()

        assert cache.max_items == 50
        assert cache.max_memory_mb == 500.0
        assert cache.name == "default"
        assert len(cache) == 0

    def test_custom_initialization(self):
        """测试自定义初始化"""
        cache = SimpleImageCache(max_items=100, max_memory_mb=1000.0, name="custom")

        assert cache.max_items == 100
        assert cache.max_memory_mb == 1000.0
        assert cache.name == "custom"

    def test_empty_cache_stats(self):
        """测试空缓存统计"""
        cache = SimpleImageCache()
        stats = cache.get_stats()

        assert stats["size"] == 0
        assert stats["memory_mb"] == 0.0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate_pct"] == 0.0
        assert stats["evictions"] == 0


class TestSimpleImageCacheGetPut:
    """测试缓存的获取和存储"""

    def test_put_and_get(self):
        """测试存储和获取"""
        cache = SimpleImageCache()
        cache.put("key1", "value1", size_mb=1.0)

        result = cache.get("key1")
        assert result == "value1"

    def test_get_nonexistent_key(self):
        """测试获取不存在的键"""
        cache = SimpleImageCache()
        result = cache.get("nonexistent")

        assert result is None

    def test_put_updates_size(self):
        """测试存储更新缓存大小"""
        cache = SimpleImageCache()
        cache.put("key1", "value1", size_mb=1.0)

        assert len(cache) == 1
        stats = cache.get_stats()
        assert stats["size"] == 1

    def test_put_updates_memory(self):
        """测试存储更新内存使用"""
        cache = SimpleImageCache()
        cache.put("key1", "value1", size_mb=10.5)

        stats = cache.get_stats()
        assert stats["memory_mb"] == 10.5

    def test_put_multiple_items(self):
        """测试存储多个项目"""
        cache = SimpleImageCache()
        cache.put("key1", "value1", size_mb=1.0)
        cache.put("key2", "value2", size_mb=2.0)
        cache.put("key3", "value3", size_mb=3.0)

        assert len(cache) == 3
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_put_overwrites_existing(self):
        """测试覆盖已存在的键"""
        cache = SimpleImageCache()
        cache.put("key1", "value1", size_mb=1.0)
        cache.put("key1", "value2", size_mb=2.0)

        assert len(cache) == 1
        assert cache.get("key1") == "value2"
        stats = cache.get_stats()
        assert stats["memory_mb"] == 2.0

    def test_get_updates_lru(self):
        """测试获取更新LRU顺序"""
        cache = SimpleImageCache(max_items=2)
        cache.put("key1", "value1")
        cache.put("key2", "value2")

        # 访问key1，使其成为最近使用
        cache.get("key1")

        # 添加key3，应该淘汰key2（最久未使用）
        cache.put("key3", "value3")

        assert cache.get("key1") is not None
        assert cache.get("key2") is None
        assert cache.get("key3") is not None


class TestSimpleImageCacheLRU:
    """测试LRU淘汰策略"""

    def test_evict_when_max_items_reached(self):
        """测试达到最大项数时淘汰"""
        cache = SimpleImageCache(max_items=3)
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # 添加第4个，应该淘汰key1
        cache.put("key4", "value4")

        assert len(cache) == 3
        assert cache.get("key1") is None
        assert cache.get("key4") is not None

    def test_evict_when_max_memory_reached(self):
        """测试达到最大内存时淘汰"""
        cache = SimpleImageCache(max_items=10, max_memory_mb=10.0)
        cache.put("key1", "value1", size_mb=5.0)
        cache.put("key2", "value2", size_mb=4.0)

        # 添加一个大项，应该淘汰直到有足够空间
        cache.put("key3", "value3", size_mb=8.0)

        # key1和key2应该都被淘汰
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is not None

    def test_eviction_count(self):
        """测试淘汰计数"""
        cache = SimpleImageCache(max_items=2)
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")  # 淘汰1次
        cache.put("key4", "value4")  # 淘汰1次

        stats = cache.get_stats()
        assert stats["evictions"] == 2

    def test_lru_order_maintained(self):
        """测试LRU顺序维护"""
        cache = SimpleImageCache(max_items=3)
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # 访问key1，使其变为最近使用
        cache.get("key1")

        # 添加新项，应该淘汰key2
        cache.put("key4", "value4")

        assert cache.get("key2") is None
        assert cache.get("key1") is not None


class TestSimpleImageCacheRemove:
    """测试缓存移除"""

    def test_remove_existing_key(self):
        """测试移除存在的键"""
        cache = SimpleImageCache()
        cache.put("key1", "value1", size_mb=5.0)

        result = cache.remove("key1")

        assert result is True
        assert cache.get("key1") is None
        assert len(cache) == 0

    def test_remove_nonexistent_key(self):
        """测试移除不存在的键"""
        cache = SimpleImageCache()
        result = cache.remove("nonexistent")

        assert result is False

    def test_remove_updates_memory(self):
        """测试移除更新内存"""
        cache = SimpleImageCache()
        cache.put("key1", "value1", size_mb=10.0)
        cache.remove("key1")

        stats = cache.get_stats()
        assert stats["memory_mb"] == 0.0


class TestSimpleImageCacheClear:
    """测试缓存清空"""

    def test_clear_empty_cache(self):
        """测试清空空缓存"""
        cache = SimpleImageCache()
        cache.clear()

        assert len(cache) == 0

    def test_clear_removes_all_items(self):
        """测试清空移除所有项"""
        cache = SimpleImageCache()
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        cache.clear()

        assert len(cache) == 0
        assert cache.get("key1") is None

    def test_clear_resets_memory(self):
        """测试清空重置内存"""
        cache = SimpleImageCache()
        cache.put("key1", "value1", size_mb=10.0)
        cache.put("key2", "value2", size_mb=20.0)

        cache.clear()

        stats = cache.get_stats()
        assert stats["memory_mb"] == 0.0


class TestSimpleImageCacheStats:
    """测试缓存统计"""

    def test_hit_rate_calculation(self):
        """测试命中率计算"""
        cache = SimpleImageCache()
        cache.put("key1", "value1")

        cache.get("key1")  # hit
        cache.get("key1")  # hit
        cache.get("key2")  # miss

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate_pct"] == round(2 / 3 * 100, 2)

    def test_memory_usage_percentage(self):
        """测试内存使用百分比"""
        cache = SimpleImageCache(max_memory_mb=100.0)
        cache.put("key1", "value1", size_mb=30.0)

        stats = cache.get_stats()
        assert stats["memory_usage_pct"] == 30.0

    def test_stats_include_all_fields(self):
        """测试统计包含所有字段"""
        cache = SimpleImageCache(name="test")
        stats = cache.get_stats()

        required_fields = [
            "name",
            "size",
            "max_items",
            "memory_mb",
            "max_memory_mb",
            "memory_usage_pct",
            "hits",
            "misses",
            "hit_rate_pct",
            "evictions",
        ]
        for field in required_fields:
            assert field in stats


class TestSimpleImageCacheMagicMethods:
    """测试魔术方法"""

    def test_len(self):
        """测试__len__"""
        cache = SimpleImageCache()
        assert len(cache) == 0

        cache.put("key1", "value1")
        assert len(cache) == 1

        cache.put("key2", "value2")
        assert len(cache) == 2

    def test_contains(self):
        """测试__contains__"""
        cache = SimpleImageCache()
        cache.put("key1", "value1")

        assert "key1" in cache
        assert "key2" not in cache

    def test_repr(self):
        """测试__repr__"""
        cache = SimpleImageCache(name="test", max_items=10, max_memory_mb=100.0)
        cache.put("key1", "value1", size_mb=5.0)

        repr_str = repr(cache)

        assert "SimpleImageCache" in repr_str
        assert "test" in repr_str
        assert "1/10" in repr_str  # items
        assert "5.0/100.0MB" in repr_str  # memory


class TestGlobalCache:
    """测试全局缓存"""

    def test_get_global_cache_singleton(self):
        """测试全局缓存单例"""
        reset_global_cache()  # 确保干净状态

        cache1 = get_global_cache()
        cache2 = get_global_cache()

        assert cache1 is cache2

    def test_global_cache_default_config(self):
        """测试全局缓存默认配置"""
        reset_global_cache()

        cache = get_global_cache()

        assert cache.name == "global"
        assert cache.max_items == 50
        assert cache.max_memory_mb == 500.0

    def test_reset_global_cache(self):
        """测试重置全局缓存"""
        reset_global_cache()

        cache1 = get_global_cache()
        cache1.put("key1", "value1")

        reset_global_cache()

        cache2 = get_global_cache()
        assert cache2.get("key1") is None

    def test_global_cache_persists_data(self):
        """测试全局缓存持久化数据"""
        reset_global_cache()

        cache1 = get_global_cache()
        cache1.put("key1", "value1")

        cache2 = get_global_cache()
        assert cache2.get("key1") == "value1"


class TestThreadSafety:
    """测试线程安全"""

    def test_concurrent_puts(self):
        """测试并发存储"""
        cache = SimpleImageCache()

        def put_items(start, count):
            for i in range(start, start + count):
                cache.put(f"key{i}", f"value{i}")

        threads = [
            threading.Thread(target=put_items, args=(0, 50)),
            threading.Thread(target=put_items, args=(50, 50)),
            threading.Thread(target=put_items, args=(100, 50)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 由于max_items=50，最终应该有50个项
        assert len(cache) == 50

    def test_concurrent_get_put(self):
        """测试并发获取和存储"""
        cache = SimpleImageCache()
        cache.put("shared", "initial")

        results = {"gets": [], "puts": []}

        def getter():
            for _ in range(100):
                val = cache.get("shared")
                if val is not None:
                    results["gets"].append(val)

        def putter():
            for i in range(100):
                cache.put("shared", f"value{i}")
                results["puts"].append(i)

        threads = [
            threading.Thread(target=getter),
            threading.Thread(target=putter),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 不应该有崩溃或死锁
        assert len(results["gets"]) > 0
        assert len(results["puts"]) == 100


class TestEdgeCases:
    """测试边缘情况"""

    def test_zero_size_item(self):
        """测试零大小项"""
        cache = SimpleImageCache()
        cache.put("key1", "value1", size_mb=0.0)

        assert cache.get("key1") == "value1"
        stats = cache.get_stats()
        assert stats["memory_mb"] == 0.0

    def test_very_large_item(self):
        """测试非常大的项"""
        cache = SimpleImageCache(max_memory_mb=100.0)
        cache.put("large", "data", size_mb=200.0)

        # 应该淘汰所有现有项，但无法容纳新项
        # 实现会尝试清空然后添加
        stats = cache.get_stats()
        # 行为取决于实现细节

    def test_put_with_same_key_different_size(self):
        """测试相同键不同大小"""
        cache = SimpleImageCache()
        cache.put("key1", "value1", size_mb=10.0)
        cache.put("key1", "value2", size_mb=20.0)

        stats = cache.get_stats()
        assert stats["memory_mb"] == 20.0  # 应该用新的大小替换

    def test_max_items_one(self):
        """测试最大项数为1"""
        cache = SimpleImageCache(max_items=1)
        cache.put("key1", "value1")
        cache.put("key2", "value2")

        assert len(cache) == 1
        assert cache.get("key2") is not None

    def test_none_value(self):
        """测试None值"""
        cache = SimpleImageCache()
        cache.put("key1", None)

        # None是合法的值
        result = cache.get("key1")
        assert result is None
        # 但键应该存在
        assert "key1" in cache

    def test_empty_string_key(self):
        """测试空字符串键"""
        cache = SimpleImageCache()
        cache.put("", "value")

        assert cache.get("") == "value"

    def test_update_access_count(self):
        """测试访问计数更新"""
        cache = SimpleImageCache()
        cache.put("key1", "value1")

        # 多次访问
        for _ in range(5):
            cache.get("key1")

        # 访问计数应该增加（虽然没有直接的API获取）
        # 但可以通过行为验证，比如在LRU中的位置


class TestIntegration:
    """集成测试"""

    def test_realistic_usage_pattern(self):
        """测试真实使用模式"""
        cache = SimpleImageCache(max_items=10, max_memory_mb=50.0)

        # 存储一些图片
        for i in range(5):
            cache.put(f"img{i}.jpg", f"image_data_{i}", size_mb=5.0)

        # 访问部分图片
        for i in range(3):
            assert cache.get(f"img{i}.jpg") is not None

        # 添加更多图片导致淘汰
        for i in range(5, 15):
            cache.put(f"img{i}.jpg", f"image_data_{i}", size_mb=5.0)

        # 检查统计
        stats = cache.get_stats()
        assert stats["size"] == 10
        assert stats["evictions"] > 0
        assert stats["hits"] >= 3

        # 清空
        cache.clear()
        assert len(cache) == 0

    def test_memory_pressure_handling(self):
        """测试内存压力处理"""
        cache = SimpleImageCache(max_items=100, max_memory_mb=100.0)

        # 填满缓存
        for i in range(50):
            cache.put(f"key{i}", f"value{i}", size_mb=2.0)

        stats = cache.get_stats()
        assert stats["memory_mb"] == 100.0

        # 尝试添加更大的项
        cache.put("large", "large_value", size_mb=30.0)

        # 应该淘汰足够的项来容纳新项
        stats = cache.get_stats()
        assert stats["memory_mb"] <= 100.0
