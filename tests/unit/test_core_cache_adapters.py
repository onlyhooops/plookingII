"""
测试 core/cache/adapters.py

测试缓存适配器功能
"""

from unittest.mock import MagicMock, Mock, patch
import pytest

from plookingII.core.cache.adapters import (
    AdvancedImageCacheAdapter,
    UnifiedCacheManagerAdapter,
    _CacheLayerAdapter
)


# ==================== AdvancedImageCacheAdapter 测试 ====================


class TestAdvancedImageCacheAdapterInit:
    """测试AdvancedImageCacheAdapter初始化"""

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_init_default(self, mock_get_cache):
        """测试默认初始化"""
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        
        assert adapter._cache == mock_cache
        mock_get_cache.assert_called_once()

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_init_with_max_size(self, mock_get_cache):
        """测试指定max_size初始化"""
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter(max_size=200)
        
        assert adapter.max_size == 200


class TestAdvancedImageCacheAdapterGet:
    """测试AdvancedImageCacheAdapter的get方法"""

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_get_basic(self, mock_get_cache):
        """测试基本get操作"""
        mock_cache = MagicMock()
        mock_cache.get.return_value = "value"
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        result = adapter.get("key")
        
        mock_cache.get.assert_called_once()

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_get_with_target_size(self, mock_get_cache):
        """测试带target_size的get"""
        mock_cache = MagicMock()
        mock_cache.get.return_value = "value"
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        result = adapter.get("key", target_size=(100, 100))
        
        mock_cache.get.assert_called()


class TestAdvancedImageCacheAdapterPut:
    """测试AdvancedImageCacheAdapter的put方法"""

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_put_basic(self, mock_get_cache):
        """测试基本put操作"""
        mock_cache = MagicMock()
        mock_cache.put.return_value = True
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        result = adapter.put("key", "value")
        
        assert result is True
        mock_cache.put.assert_called_once()

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_put_with_size(self, mock_get_cache):
        """测试带size的put"""
        mock_cache = MagicMock()
        mock_cache.put.return_value = True
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        result = adapter.put("key", "value", size_mb=5.0)
        
        assert result is True
        mock_cache.put.assert_called()


class TestAdvancedImageCacheAdapterRemove:
    """测试AdvancedImageCacheAdapter的remove方法"""

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_remove_success(self, mock_get_cache):
        """测试成功移除"""
        mock_cache = MagicMock()
        mock_cache.remove.return_value = True
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        result = adapter.remove("key")
        
        assert result is True
        mock_cache.remove.assert_called_once_with("key")

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_remove_not_found(self, mock_get_cache):
        """测试移除不存在的键"""
        mock_cache = MagicMock()
        mock_cache.remove.return_value = False
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        result = adapter.remove("nonexistent")
        
        assert result is False


class TestAdvancedImageCacheAdapterClear:
    """测试AdvancedImageCacheAdapter的clear方法"""

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_clear(self, mock_get_cache):
        """测试clear方法"""
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        adapter.clear()
        
        mock_cache.clear.assert_called_once()

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_clear_all(self, mock_get_cache):
        """测试clear_all方法"""
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        adapter.clear_all()
        
        mock_cache.clear.assert_called_once()


class TestAdvancedImageCacheAdapterPutNew:
    """测试AdvancedImageCacheAdapter的put_new方法"""

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_put_new(self, mock_get_cache):
        """测试put_new方法"""
        mock_cache = MagicMock()
        mock_cache.put.return_value = True
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        result = adapter.put_new("key", "value")
        
        assert result is True
        mock_cache.put.assert_called_once()


class TestAdvancedImageCacheAdapterStats:
    """测试AdvancedImageCacheAdapter的统计方法"""

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_get_stats(self, mock_get_cache):
        """测试get_stats方法"""
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = {
            "total_items": 10,
            "current_memory_mb": 50.0,
            "max_memory_mb": 100.0,
            "memory_usage_pct": 50.0,
            "active_cache_size": 20,
            "nearby_cache_size": 10
        }
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        stats = adapter.get_stats()
        
        assert isinstance(stats, dict)
        assert "size" in stats
        assert "hits" in stats
        mock_cache.get_stats.assert_called_once()

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_get_memory_stats(self, mock_get_cache):
        """测试get_memory_stats方法"""
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = {
            "current_memory_mb": 50.0,
            "max_memory_mb": 100.0,
            "memory_usage_pct": 50.0,
            "total_items": 10,
            "active_cache_size": 20,
            "nearby_cache_size": 10
        }
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        stats = adapter.get_memory_stats()
        
        assert isinstance(stats, dict)
        assert "current_mb" in stats
        assert "max_mb" in stats
        assert "usage_pct" in stats


class TestAdvancedImageCacheAdapterFileSize:
    """测试AdvancedImageCacheAdapter的文件大小方法"""

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    @patch('os.path.getsize')
    @patch('os.path.exists')
    def test_get_file_size_mb_success(self, mock_exists, mock_getsize, mock_get_cache):
        """测试成功获取文件大小"""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024 * 5  # 5MB
        mock_get_cache.return_value = MagicMock()
        
        adapter = AdvancedImageCacheAdapter()
        size = adapter.get_file_size_mb("/test/file.jpg")
        
        assert size == 5.0

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_get_file_size_mb_not_exists(self, mock_get_cache):
        """测试文件不存在"""
        mock_get_cache.return_value = MagicMock()
        
        adapter = AdvancedImageCacheAdapter()
        # 使用不存在的路径，应该返回0.0
        size = adapter.get_file_size_mb("/nonexistent/path/that/does/not/exist.jpg")
        
        assert size == 0.0


class TestAdvancedImageCacheAdapterProperties:
    """测试AdvancedImageCacheAdapter的属性"""

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_main_cache_property(self, mock_get_cache):
        """测试main_cache属性"""
        mock_cache = MagicMock()
        mock_cache.active = MagicMock()
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        cache = adapter.main_cache
        
        assert cache is not None

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_preview_cache_property(self, mock_get_cache):
        """测试preview_cache属性"""
        mock_cache = MagicMock()
        mock_cache.active = MagicMock()
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        cache = adapter.preview_cache
        
        assert cache is not None

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_preload_cache_property(self, mock_get_cache):
        """测试preload_cache属性"""
        mock_cache = MagicMock()
        mock_cache.nearby = MagicMock()
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        cache = adapter.preload_cache
        
        assert cache is not None

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_progressive_cache_property(self, mock_get_cache):
        """测试progressive_cache属性"""
        mock_cache = MagicMock()
        mock_cache.nearby = MagicMock()
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        cache = adapter.progressive_cache
        
        assert cache is not None


# ==================== _CacheLayerAdapter 测试 ====================


class TestCacheLayerAdapter:
    """测试_CacheLayerAdapter"""

    def test_init(self):
        """测试初始化"""
        mock_cache = MagicMock()
        adapter = _CacheLayerAdapter(mock_cache, is_nearby=False)
        
        assert adapter._cache == mock_cache
        assert adapter._is_nearby is False

    def test_get(self):
        """测试get方法"""
        mock_cache = MagicMock()
        mock_cache.get.return_value = "value"
        adapter = _CacheLayerAdapter(mock_cache, is_nearby=False)
        
        result = adapter.get("key")
        
        mock_cache.get.assert_called_once()

    def test_put(self):
        """测试put方法"""
        mock_cache = MagicMock()
        adapter = _CacheLayerAdapter(mock_cache, is_nearby=False)
        
        adapter.put("key", "value")
        
        mock_cache.put.assert_called_once()

    def test_remove(self):
        """测试remove方法"""
        mock_cache = MagicMock()
        adapter = _CacheLayerAdapter(mock_cache, is_nearby=False)
        
        adapter.remove("key")
        
        mock_cache.remove.assert_called_once_with("key")

    def test_clear(self):
        """测试clear方法"""
        mock_cache = MagicMock()
        adapter = _CacheLayerAdapter(mock_cache, is_nearby=False)
        
        adapter.clear()
        
        mock_cache.clear.assert_called_once()

    def test_get_stats(self):
        """测试get_stats方法"""
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = {"size": 10}
        adapter = _CacheLayerAdapter(mock_cache, is_nearby=False)
        
        stats = adapter.get_stats()
        
        assert isinstance(stats, dict)
        mock_cache.get_stats.assert_called_once()


# ==================== UnifiedCacheManagerAdapter 测试 ====================


class TestUnifiedCacheManagerAdapterInit:
    """测试UnifiedCacheManagerAdapter初始化"""

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_init_default(self, mock_get_cache):
        """测试默认初始化"""
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache
        
        adapter = UnifiedCacheManagerAdapter()
        
        assert adapter._cache == mock_cache


class TestUnifiedCacheManagerAdapterMethods:
    """测试UnifiedCacheManagerAdapter方法"""

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_get(self, mock_get_cache):
        """测试get方法"""
        mock_cache = MagicMock()
        mock_cache.get.return_value = "value"
        mock_get_cache.return_value = mock_cache
        
        adapter = UnifiedCacheManagerAdapter()
        result = adapter.get("key")
        
        mock_cache.get.assert_called_once()

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_get_with_default(self, mock_get_cache):
        """测试带默认值的get"""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache
        
        adapter = UnifiedCacheManagerAdapter()
        result = adapter.get("key", default="default_value")
        
        # 即使cache返回None，也会调用get
        mock_cache.get.assert_called()

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_put(self, mock_get_cache):
        """测试put方法"""
        mock_cache = MagicMock()
        mock_cache.put.return_value = True
        mock_get_cache.return_value = mock_cache
        
        adapter = UnifiedCacheManagerAdapter()
        result = adapter.put("key", "value")
        
        assert result is True
        mock_cache.put.assert_called_once()

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_put_with_options(self, mock_get_cache):
        """测试带选项的put"""
        mock_cache = MagicMock()
        mock_cache.put.return_value = True
        mock_get_cache.return_value = mock_cache
        
        adapter = UnifiedCacheManagerAdapter()
        result = adapter.put("key", "value", size=100, priority=2)
        
        assert result is True
        mock_cache.put.assert_called()

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_remove(self, mock_get_cache):
        """测试remove方法"""
        mock_cache = MagicMock()
        mock_cache.remove.return_value = True
        mock_get_cache.return_value = mock_cache
        
        adapter = UnifiedCacheManagerAdapter()
        result = adapter.remove("key")
        
        assert result is True
        mock_cache.remove.assert_called_once_with("key")

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_clear(self, mock_get_cache):
        """测试clear方法"""
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache
        
        adapter = UnifiedCacheManagerAdapter()
        adapter.clear()
        
        mock_cache.clear.assert_called_once()

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_get_stats(self, mock_get_cache):
        """测试get_stats方法"""
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = {"hits": 10, "misses": 2}
        mock_get_cache.return_value = mock_cache
        
        adapter = UnifiedCacheManagerAdapter()
        stats = adapter.get_stats()
        
        assert isinstance(stats, dict)
        mock_cache.get_stats.assert_called_once()


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_advanced_adapter_workflow(self, mock_get_cache):
        """测试AdvancedImageCacheAdapter完整工作流"""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_cache.put.return_value = True
        mock_cache.remove.return_value = True
        mock_cache.get_stats.return_value = {
            "total_items": 5,
            "current_memory_mb": 50.0,
            "max_memory_mb": 100.0,
            "memory_usage_pct": 50.0,
            "active_cache_size": 20,
            "nearby_cache_size": 10
        }
        mock_get_cache.return_value = mock_cache
        
        adapter = AdvancedImageCacheAdapter()
        
        # 1. Put
        adapter.put("key1", "value1")
        
        # 2. Get
        adapter.get("key1")
        
        # 3. Stats
        stats = adapter.get_stats()
        assert isinstance(stats, dict)
        
        # 4. Remove
        adapter.remove("key1")
        
        # 5. Clear
        adapter.clear()

    @patch('plookingII.core.cache.adapters.get_unified_cache')
    def test_unified_manager_workflow(self, mock_get_cache):
        """测试UnifiedCacheManagerAdapter完整工作流"""
        mock_cache = MagicMock()
        mock_cache.get.return_value = "value"
        mock_cache.put.return_value = True
        mock_cache.get_stats.return_value = {"total": 10}
        mock_get_cache.return_value = mock_cache
        
        adapter = UnifiedCacheManagerAdapter()
        
        # 1. Put
        adapter.put("key1", "value1", size=100)
        
        # 2. Get
        result = adapter.get("key1")
        assert result is not None
        
        # 3. Stats
        stats = adapter.get_stats()
        assert isinstance(stats, dict)
        
        # 4. Clear
        adapter.clear()

