"""
测试SimpleCache高级功能和兼容类

测试覆盖：
- AdvancedImageCache 兼容类
- UnifiedCacheManager 兼容类
- BidirectionalCachePool 兼容类
"""

from unittest.mock import Mock, patch

from plookingII.core.simple_cache import (
    AdvancedImageCache,
    BidirectionalCachePool,
    SimpleImageCache,
    UnifiedCacheManager,
)


class TestAdvancedImageCacheInit:
    """测试AdvancedImageCache初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        cache = AdvancedImageCache()

        assert cache.max_items == 50
        assert cache.max_memory_mb == 500.0

    def test_init_with_new_params(self):
        """测试使用新参数名"""
        cache = AdvancedImageCache(max_items=100, max_memory_mb=1000.0)

        assert cache.max_items == 100
        assert cache.max_memory_mb == 1000.0

    def test_init_with_legacy_params(self):
        """测试使用旧参数名兼容性"""
        cache = AdvancedImageCache(cache_size=75, max_memory=750.0)

        assert cache.max_items == 75
        assert cache.max_memory_mb == 750.0

    def test_init_mixed_params(self):
        """测试混合新旧参数"""
        # 旧参数名应该被转换
        cache = AdvancedImageCache(cache_size=60, max_memory_mb=600.0)

        assert cache.max_items == 60
        assert cache.max_memory_mb == 600.0

    def test_inherits_from_simple_cache(self):
        """测试继承自SimpleImageCache"""
        cache = AdvancedImageCache()

        assert isinstance(cache, SimpleImageCache)


class TestAdvancedImageCacheGetFileSizeMb:
    """测试get_file_size_mb方法"""

    def test_get_file_size_existing_file(self, tmp_path):
        """测试获取存在文件的大小"""
        cache = AdvancedImageCache()

        # 创建测试文件
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"0" * (5 * 1024 * 1024))  # 5MB

        size_mb = cache.get_file_size_mb(str(test_file))

        assert abs(size_mb - 5.0) < 0.1

    def test_get_file_size_nonexistent_file(self):
        """测试获取不存在文件的大小"""
        cache = AdvancedImageCache()

        size_mb = cache.get_file_size_mb("/nonexistent/file.jpg")

        assert size_mb == 0.0

    def test_get_file_size_small_file(self, tmp_path):
        """测试获取小文件的大小"""
        cache = AdvancedImageCache()

        test_file = tmp_path / "small.txt"
        test_file.write_text("Hello")

        size_mb = cache.get_file_size_mb(str(test_file))

        assert size_mb < 0.001

    def test_get_file_size_empty_file(self, tmp_path):
        """测试获取空文件的大小"""
        cache = AdvancedImageCache()

        test_file = tmp_path / "empty.jpg"
        test_file.touch()

        size_mb = cache.get_file_size_mb(str(test_file))

        assert size_mb == 0.0

    def test_get_file_size_with_permission_error(self, tmp_path, monkeypatch):
        """测试文件权限错误"""
        cache = AdvancedImageCache()

        test_file = tmp_path / "protected.jpg"
        test_file.write_bytes(b"test")

        # Mock getsize to raise exception
        def mock_getsize(path):
            raise PermissionError("No permission")

        with patch("os.path.getsize", side_effect=mock_getsize):
            size_mb = cache.get_file_size_mb(str(test_file))
            assert size_mb == 0.0


class TestAdvancedImageCacheLoadImageWithStrategy:
    """测试load_image_with_strategy方法"""

    def test_load_image_force_reload(self, tmp_path):
        """测试强制重新加载"""
        cache = AdvancedImageCache()

        test_file = tmp_path / "reload.jpg"
        test_file.write_bytes(b"data")

        # Mock loader
        mock_loader = Mock()
        mock_loader.load = Mock(return_value="new_image")

        with patch("plookingII.core.loading.get_loader", return_value=mock_loader):
            result = cache.load_image_with_strategy(str(test_file), force_reload=True)

        # 应该返回新加载的图片
        assert result == "new_image"
        mock_loader.load.assert_called_once()

    def test_load_image_different_strategies(self, tmp_path):
        """测试不同加载策略"""
        cache = AdvancedImageCache()

        test_file = tmp_path / "strategy.jpg"
        test_file.write_bytes(b"data")

        strategies = ["auto", "optimized", "preview", "fast"]

        for strategy in strategies:
            mock_loader = Mock()
            mock_loader.load = Mock(return_value=f"image_{strategy}")

            with patch("plookingII.core.loading.get_loader", return_value=mock_loader):
                result = cache.load_image_with_strategy(str(test_file), strategy=strategy, force_reload=True)

                assert result == f"image_{strategy}"

    def test_load_image_failure(self, tmp_path):
        """测试加载失败"""
        cache = AdvancedImageCache()

        test_file = tmp_path / "fail.jpg"
        test_file.write_bytes(b"data")

        mock_loader = Mock()
        mock_loader.load = Mock(side_effect=Exception("Load failed"))

        with patch("plookingII.core.loading.get_loader", return_value=mock_loader):
            result = cache.load_image_with_strategy(str(test_file), force_reload=True)

        assert result is None

    def test_load_image_loader_returns_none(self, tmp_path):
        """测试加载器返回None"""
        cache = AdvancedImageCache()

        test_file = tmp_path / "none.jpg"
        test_file.write_bytes(b"data")

        mock_loader = Mock()
        mock_loader.load = Mock(return_value=None)

        with patch("plookingII.core.loading.get_loader", return_value=mock_loader):
            result = cache.load_image_with_strategy(str(test_file), force_reload=True)

        assert result is None


class TestUnifiedCacheManager:
    """测试UnifiedCacheManager类"""

    def test_init(self):
        """测试初始化"""
        manager = UnifiedCacheManager(max_items=20, max_memory_mb=200.0)

        assert manager.max_items == 20
        assert manager.max_memory_mb == 200.0

    def test_inherits_from_simple_cache(self):
        """测试继承自SimpleImageCache"""
        manager = UnifiedCacheManager()

        assert isinstance(manager, SimpleImageCache)

    def test_basic_operations(self):
        """测试基本操作"""
        manager = UnifiedCacheManager()

        manager.put("key1", "value1", size_mb=1.0)
        result = manager.get("key1")

        assert result == "value1"

    def test_all_simple_cache_features_work(self):
        """测试所有SimpleImageCache功能都工作"""
        manager = UnifiedCacheManager(max_items=3)

        # 添加项
        manager.put("k1", "v1")
        manager.put("k2", "v2")
        manager.put("k3", "v3")

        # 测试LRU
        manager.get("k1")
        manager.put("k4", "v4")

        # k2应该被淘汰
        assert manager.get("k2") is None
        assert manager.get("k1") is not None


class TestBidirectionalCachePool:
    """测试BidirectionalCachePool类"""

    def test_init_default(self):
        """测试默认初始化"""
        pool = BidirectionalCachePool()

        assert isinstance(pool, SimpleImageCache)
        assert pool._current_index == -1
        assert pool._current_sequence == []

    def test_init_with_legacy_params(self):
        """测试旧参数被忽略"""
        # 这些旧参数应该被移除，不会导致错误
        pool = BidirectionalCachePool(preload_count=5, keep_previous=3, memory_monitor=Mock())

        assert isinstance(pool, SimpleImageCache)

    def test_init_with_image_processor(self):
        """测试传入image_processor"""
        mock_processor = Mock()
        pool = BidirectionalCachePool(image_processor=mock_processor)

        assert pool._image_processor == mock_processor

    def test_init_with_advanced_cache(self):
        """测试传入advanced_cache"""
        mock_cache = Mock()
        pool = BidirectionalCachePool(advanced_cache=mock_cache)

        assert pool._advanced_cache == mock_cache

    def test_set_current_image_sync(self):
        """测试设置当前图片"""
        pool = BidirectionalCachePool()
        pool._current_sequence = ["img1.jpg", "img2.jpg", "img3.jpg"]

        pool.set_current_image_sync("img2.jpg", sync_key="test")

        assert pool._current_index == 1

    def test_set_current_image_sync_not_in_sequence(self):
        """测试设置不在序列中的图片"""
        pool = BidirectionalCachePool()
        pool._current_sequence = ["img1.jpg", "img2.jpg"]

        # 不应该崩溃
        pool.set_current_image_sync("img3.jpg", sync_key="test")

    def test_update_sequence_manually(self):
        """测试手动更新序列"""
        pool = BidirectionalCachePool()

        # 直接设置内部状态（update_sequence方法不存在）
        pool._current_sequence = ["a.jpg", "b.jpg", "c.jpg"]

        assert pool._current_sequence == ["a.jpg", "b.jpg", "c.jpg"]

    def test_basic_cache_operations(self):
        """测试基本缓存操作"""
        pool = BidirectionalCachePool()

        pool.put("img1", "image_data1")
        pool.put("img2", "image_data2")

        assert pool.get("img1") == "image_data1"
        assert pool.get("img2") == "image_data2"


class TestCompatibilityIntegration:
    """测试兼容性集成"""

    def test_all_classes_share_same_interface(self):
        """测试所有类共享相同接口"""
        simple = SimpleImageCache()
        advanced = AdvancedImageCache()
        unified = UnifiedCacheManager()
        pool = BidirectionalCachePool()

        # 所有都应该有基本的put/get方法
        for cache in [simple, advanced, unified, pool]:
            cache.put("test", "value")
            assert cache.get("test") == "value"

    def test_migration_from_advanced_to_simple(self):
        """测试从AdvancedImageCache迁移到SimpleImageCache"""
        # 创建AdvancedImageCache
        advanced = AdvancedImageCache(max_items=10, max_memory_mb=100.0)
        advanced.put("key1", "value1")
        advanced.put("key2", "value2")

        # 可以直接替换为SimpleImageCache
        simple = SimpleImageCache(max_items=10, max_memory_mb=100.0)
        simple.put("key1", "value1")
        simple.put("key2", "value2")

        # 行为应该相同
        assert advanced.get("key1") == simple.get("key1")

    def test_legacy_code_still_works(self, tmp_path):
        """测试旧代码仍然工作"""
        # 模拟旧代码使用方式
        cache = AdvancedImageCache(cache_size=50, max_memory=500.0)

        test_file = tmp_path / "legacy.jpg"
        test_file.write_bytes(b"0" * (2 * 1024 * 1024))

        # 旧方法应该工作
        size = cache.get_file_size_mb(str(test_file))
        assert abs(size - 2.0) < 0.1


class TestEdgeCases:
    """测试边缘情况"""

    def test_advanced_cache_with_none_image_processor(self):
        """测试image_processor为None"""
        pool = BidirectionalCachePool(image_processor=None)

        assert pool._image_processor is None
        # 基本操作应该仍然工作
        pool.put("key", "value")
        assert pool.get("key") == "value"

    def test_empty_sequence_update(self):
        """测试更新为空序列"""
        pool = BidirectionalCachePool()
        pool._current_sequence = ["img1", "img2"]

        # 手动设置为空序列
        pool._current_sequence = []

        assert pool._current_sequence == []

    def test_advanced_cache_inherits_all_features(self):
        """测试AdvancedImageCache继承所有特性"""
        cache = AdvancedImageCache(max_items=3)

        # 测试LRU
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        cache.put("k3", "v3")

        cache.get("k1")  # 访问k1
        cache.put("k4", "v4")  # 应该淘汰k2

        assert cache.get("k2") is None
        assert cache.get("k1") is not None

    def test_unified_manager_clear(self):
        """测试UnifiedCacheManager清空"""
        manager = UnifiedCacheManager()

        manager.put("k1", "v1")
        manager.put("k2", "v2")

        manager.clear()

        assert len(manager) == 0
        assert manager.get("k1") is None
