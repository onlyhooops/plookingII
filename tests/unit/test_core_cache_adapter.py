"""
测试 core/cache/cache_adapter.py

测试缓存适配器功能，包括：
- AdvancedImageCacheAdapter
- BidirectionalCachePoolAdapter
- NetworkCacheAdapter
- create_cache_adapter工厂函数
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from plookingII.core.cache.cache_adapter import (
    AdvancedImageCacheAdapter,
    BidirectionalCachePoolAdapter,
    NetworkCacheAdapter,
    create_cache_adapter,
)


@pytest.fixture
def mock_unified_cache():
    """创建模拟的统一缓存"""
    cache = MagicMock()
    cache.get.return_value = None
    cache.put.return_value = True
    cache.remove.return_value = True
    cache.clear.return_value = None
    cache.get_stats.return_value = {
        "hits": {"total": 10, "hot": 5, "warm": 3, "cold": 2},
        "misses": 2,
        "total_items": 10,
        "current_memory_mb": 50.0,
        "hit_rate": 0.83,
    }
    return cache


# ==================== AdvancedImageCacheAdapter 测试 ====================


class TestAdvancedImageCacheAdapter:
    """测试AdvancedImageCacheAdapter"""

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_init(self, mock_get_cache, mock_unified_cache):
        """测试初始化"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = AdvancedImageCacheAdapter(max_size=200)
        
        assert adapter._max_size == 200
        assert adapter._unified == mock_unified_cache

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_get_without_target_size(self, mock_get_cache, mock_unified_cache):
        """测试无目标尺寸的get"""
        mock_get_cache.return_value = mock_unified_cache
        mock_unified_cache.get.return_value = "image_data"
        
        adapter = AdvancedImageCacheAdapter()
        result = adapter.get("/path/to/image.jpg")
        
        assert result == "image_data"
        mock_unified_cache.get.assert_called_with("/path/to/image.jpg")

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_get_with_target_size(self, mock_get_cache, mock_unified_cache):
        """测试带目标尺寸的get"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = AdvancedImageCacheAdapter()
        adapter.get("/path/to/image.jpg", target_size=(800, 600))
        
        mock_unified_cache.get.assert_called_with("/path/to/image.jpg:800x600")

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_put_without_target_size(self, mock_get_cache, mock_unified_cache):
        """测试无目标尺寸的put"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = AdvancedImageCacheAdapter()
        result = adapter.put("/path/to/image.jpg", "image_data", size=2.5)
        
        assert result is True
        mock_unified_cache.put.assert_called_with("/path/to/image.jpg", "image_data", size=2.5)

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_put_with_target_size(self, mock_get_cache, mock_unified_cache):
        """测试带目标尺寸的put"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = AdvancedImageCacheAdapter()
        result = adapter.put("/path/to/image.jpg", "image_data", size=2.5, target_size=(1024, 768))
        
        assert result is True
        mock_unified_cache.put.assert_called_with("/path/to/image.jpg:1024x768", "image_data", size=2.5)

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_remove(self, mock_get_cache, mock_unified_cache):
        """测试remove"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = AdvancedImageCacheAdapter()
        result = adapter.remove("/path/to/image.jpg")
        
        assert result is True
        mock_unified_cache.remove.assert_called_with("/path/to/image.jpg")

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_clear(self, mock_get_cache, mock_unified_cache):
        """测试clear"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = AdvancedImageCacheAdapter()
        adapter.clear()
        
        mock_unified_cache.clear.assert_called_once()

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_put_new(self, mock_get_cache, mock_unified_cache):
        """测试put_new别名方法"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = AdvancedImageCacheAdapter()
        result = adapter.put_new("/path/to/image.jpg", "image_data", size=1.5, target_size=(640, 480))
        
        assert result is True
        mock_unified_cache.put.assert_called_with("/path/to/image.jpg:640x480", "image_data", size=1.5)

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_clear_all(self, mock_get_cache, mock_unified_cache):
        """测试clear_all别名方法"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = AdvancedImageCacheAdapter()
        adapter.clear_all()
        
        mock_unified_cache.clear.assert_called_once()

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_get_stats(self, mock_get_cache, mock_unified_cache):
        """测试get_stats"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = AdvancedImageCacheAdapter()
        stats = adapter.get_stats()
        
        assert stats["cache_hits"] == 10
        assert stats["cache_misses"] == 2
        assert stats["cache_size"] == 10
        assert stats["memory_usage_mb"] == 50.0
        assert stats["hit_rate"] == 0.83

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_get_file_size_mb(self, mock_get_cache, mock_unified_cache):
        """测试get_file_size_mb"""
        import tempfile
        import os
        
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = AdvancedImageCacheAdapter()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"x" * (1024 * 1024 * 2))  # 2MB
            temp_path = f.name
        
        try:
            size_mb = adapter.get_file_size_mb(temp_path)
            assert 1.9 < size_mb < 2.1  # 大约2MB
        finally:
            os.unlink(temp_path)

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_get_file_size_mb_nonexistent(self, mock_get_cache, mock_unified_cache):
        """测试不存在文件的get_file_size_mb"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = AdvancedImageCacheAdapter()
        size_mb = adapter.get_file_size_mb("/nonexistent/path.jpg")
        
        assert size_mb == 0.0

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_make_cache_key_without_size(self, mock_get_cache, mock_unified_cache):
        """测试_make_cache_key无尺寸"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = AdvancedImageCacheAdapter()
        key = adapter._make_cache_key("/path/to/image.jpg")
        
        assert key == "/path/to/image.jpg"

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_make_cache_key_with_size(self, mock_get_cache, mock_unified_cache):
        """测试_make_cache_key有尺寸"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = AdvancedImageCacheAdapter()
        key = adapter._make_cache_key("/path/to/image.jpg", target_size=(1920, 1080))
        
        assert key == "/path/to/image.jpg:1920x1080"


# ==================== BidirectionalCachePoolAdapter 测试 ====================


class TestBidirectionalCachePoolAdapter:
    """测试BidirectionalCachePoolAdapter"""

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_init(self, mock_get_cache, mock_unified_cache):
        """测试初始化"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = BidirectionalCachePoolAdapter(
            preload_count=10,
            keep_previous=5
        )
        
        assert adapter._preload_count == 10
        assert adapter._keep_previous == 5
        assert adapter._unified == mock_unified_cache

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_get_sync(self, mock_get_cache, mock_unified_cache):
        """测试get_sync"""
        mock_get_cache.return_value = mock_unified_cache
        mock_unified_cache.get.return_value = "cached_value"
        
        adapter = BidirectionalCachePoolAdapter()
        result = adapter.get_sync("test_key")
        
        assert result == "cached_value"
        mock_unified_cache.get.assert_called_with("test_key")

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_put_sync(self, mock_get_cache, mock_unified_cache):
        """测试put_sync"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = BidirectionalCachePoolAdapter()
        result = adapter.put_sync("test_key", "test_value", size=1.5)
        
        assert result is True
        mock_unified_cache.put.assert_called_with("test_key", "test_value", size=1.5)

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_set_current_image_sync(self, mock_get_cache, mock_unified_cache):
        """测试set_current_image_sync"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = BidirectionalCachePoolAdapter()
        # 不应该抛出异常
        adapter.set_current_image_sync("key1", "/path/to/image.jpg")

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_get_stats(self, mock_get_cache, mock_unified_cache):
        """测试get_stats"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = BidirectionalCachePoolAdapter()
        stats = adapter.get_stats()
        
        assert stats["preload_hits"] == 5
        assert stats["cache_misses"] == 2
        assert stats["total_size"] == 10


# ==================== NetworkCacheAdapter 测试 ====================


class TestNetworkCacheAdapter:
    """测试NetworkCacheAdapter"""

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_init(self, mock_get_cache, mock_unified_cache):
        """测试初始化"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = NetworkCacheAdapter(max_size=50, ttl=7200)
        
        assert adapter._max_size == 50
        assert adapter._ttl == 7200
        assert adapter._unified == mock_unified_cache

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_get(self, mock_get_cache, mock_unified_cache):
        """测试get"""
        mock_get_cache.return_value = mock_unified_cache
        mock_unified_cache.get.return_value = "network_data"
        
        adapter = NetworkCacheAdapter()
        result = adapter.get("https://example.com/resource")
        
        assert result == "network_data"
        mock_unified_cache.get.assert_called_with("https://example.com/resource")

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_put(self, mock_get_cache, mock_unified_cache):
        """测试put"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = NetworkCacheAdapter()
        result = adapter.put("https://example.com/resource", "data", size=0.5)
        
        assert result is True
        mock_unified_cache.put.assert_called_with("https://example.com/resource", "data", size=0.5)

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_clear(self, mock_get_cache, mock_unified_cache):
        """测试clear"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = NetworkCacheAdapter()
        adapter.clear()
        
        mock_unified_cache.clear.assert_called_once()

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_get_stats(self, mock_get_cache, mock_unified_cache):
        """测试get_stats"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = NetworkCacheAdapter()
        stats = adapter.get_stats()
        
        # 返回原始统计信息
        assert stats["hits"]["total"] == 10
        assert stats["misses"] == 2


# ==================== create_cache_adapter 工厂函数测试 ====================


class TestCreateCacheAdapter:
    """测试create_cache_adapter工厂函数"""

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_create_advanced_image(self, mock_get_cache, mock_unified_cache):
        """测试创建AdvancedImageCacheAdapter"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = create_cache_adapter("advanced_image", max_size=150)
        
        assert isinstance(adapter, AdvancedImageCacheAdapter)
        assert adapter._max_size == 150

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_create_bidirectional(self, mock_get_cache, mock_unified_cache):
        """测试创建BidirectionalCachePoolAdapter"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = create_cache_adapter("bidirectional", preload_count=8)
        
        assert isinstance(adapter, BidirectionalCachePoolAdapter)
        assert adapter._preload_count == 8

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_create_network(self, mock_get_cache, mock_unified_cache):
        """测试创建NetworkCacheAdapter"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = create_cache_adapter("network", max_size=60, ttl=3600)
        
        assert isinstance(adapter, NetworkCacheAdapter)
        assert adapter._max_size == 60
        assert adapter._ttl == 3600

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_create_unknown_type(self, mock_get_cache, mock_unified_cache):
        """测试创建未知类型"""
        mock_get_cache.return_value = mock_unified_cache
        
        with pytest.raises(ValueError, match="Unknown cache type"):
            create_cache_adapter("unknown_type")

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_create_case_insensitive(self, mock_get_cache, mock_unified_cache):
        """测试大小写不敏感"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter1 = create_cache_adapter("ADVANCED_IMAGE")
        adapter2 = create_cache_adapter("Advanced_Image")
        adapter3 = create_cache_adapter("aDvAnCeD_iMaGe")
        
        assert isinstance(adapter1, AdvancedImageCacheAdapter)
        assert isinstance(adapter2, AdvancedImageCacheAdapter)
        assert isinstance(adapter3, AdvancedImageCacheAdapter)


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_advanced_image_workflow(self, mock_get_cache, mock_unified_cache):
        """测试AdvancedImageCacheAdapter完整工作流"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter = AdvancedImageCacheAdapter(max_size=100)
        
        # 存储
        adapter.put("/image1.jpg", "data1", size=1.0)
        adapter.put("/image2.jpg", "data2", size=2.0, target_size=(800, 600))
        
        # 获取
        adapter.get("/image1.jpg")
        adapter.get("/image2.jpg", target_size=(800, 600))
        
        # 统计
        stats = adapter.get_stats()
        assert "cache_hits" in stats
        
        # 清空
        adapter.clear()

    @patch('plookingII.core.cache.cache_adapter.get_unified_cache')
    def test_all_adapters_coexist(self, mock_get_cache, mock_unified_cache):
        """测试所有适配器可以同时存在"""
        mock_get_cache.return_value = mock_unified_cache
        
        adapter1 = create_cache_adapter("advanced_image")
        adapter2 = create_cache_adapter("bidirectional")
        adapter3 = create_cache_adapter("network")
        
        assert isinstance(adapter1, AdvancedImageCacheAdapter)
        assert isinstance(adapter2, BidirectionalCachePoolAdapter)
        assert isinstance(adapter3, NetworkCacheAdapter)

