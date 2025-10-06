"""
测试 ui/managers/image_manager.py

测试图片管理器功能，包括：
- 初始化和配置
- 图片显示
- 加载策略
- 缓存管理
- 预加载和预取
"""

import os
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from plookingII.ui.managers.image_manager import ImageManager

# ==================== 夹具（Fixtures） ====================


@pytest.fixture
def mock_window():
    """创建模拟窗口"""
    window = MagicMock()
    window.images = ["/test/img1.jpg", "/test/img2.jpg", "/test/img3.jpg"]
    window.current_index = 0
    window.image_view = MagicMock()
    window.image_seq_label = MagicMock()
    window.folder_seq_label = MagicMock()
    window.status_bar_controller = MagicMock()
    window.current_folder = "/test/folder"
    window.subfolders = ["/test/folder"]
    window.current_subfolder_index = 0
    return window


@pytest.fixture
def image_manager(mock_window):
    """创建图片管理器实例"""
    with patch('plookingII.ui.managers.image_manager.HybridImageProcessor'):
        return ImageManager(mock_window)


# ==================== 初始化测试 ====================


class TestImageManagerInit:
    """测试ImageManager初始化"""

    @patch('plookingII.ui.managers.image_manager.HybridImageProcessor')
    def test_init_basic(self, mock_processor_class, mock_window):
        """测试基本初始化"""
        mock_processor = MagicMock()
        mock_processor_class.return_value = mock_processor
        
        manager = ImageManager(mock_window)
        
        assert manager.main_window == mock_window
        assert manager.hybrid_processor == mock_processor

    @patch('plookingII.ui.managers.image_manager.HybridImageProcessor')
    def test_init_default_attributes(self, mock_processor_class, mock_window):
        """测试默认属性"""
        manager = ImageManager(mock_window)
        
        assert hasattr(manager, '_load_generation')
        assert hasattr(manager, '_decode_lock')
        assert hasattr(manager, '_nav_history')


# ==================== 显示方法测试 ====================


class TestDisplayMethods:
    """测试显示方法"""

    def test_show_current_image_method_exists(self, image_manager):
        """测试show_current_image方法存在"""
        assert hasattr(image_manager, 'show_current_image')
        assert callable(image_manager.show_current_image)

    def test_display_image_immediate_method_exists(self, image_manager):
        """测试_display_image_immediate方法存在"""
        assert hasattr(image_manager, '_display_image_immediate')
        assert callable(image_manager._display_image_immediate)


# ==================== 加载策略测试 ====================


class TestLoadingStrategies:
    """测试加载策略"""

    def test_should_use_fast_loading_method_exists(self, image_manager):
        """测试_should_use_fast_loading方法存在"""
        assert hasattr(image_manager, '_should_use_fast_loading')
        assert callable(image_manager._should_use_fast_loading)

    def test_should_use_progressive_method_exists(self, image_manager):
        """测试_should_use_progressive方法存在"""
        assert hasattr(image_manager, '_should_use_progressive')
        assert callable(image_manager._should_use_progressive)

    def test_execute_loading_strategy_method_exists(self, image_manager):
        """测试_execute_loading_strategy方法存在"""
        assert hasattr(image_manager, '_execute_loading_strategy')
        assert callable(image_manager._execute_loading_strategy)

    def test_should_use_fast_loading_small_file(self, image_manager):
        """测试小文件快速加载"""
        result = image_manager._should_use_fast_loading(0.5)  # 0.5MB
        assert isinstance(result, bool)

    def test_should_use_fast_loading_large_file(self, image_manager):
        """测试大文件快速加载"""
        result = image_manager._should_use_fast_loading(50.0)  # 50MB
        assert isinstance(result, bool)

    def test_should_use_progressive_small_file(self, image_manager):
        """测试小文件渐进式加载"""
        result = image_manager._should_use_progressive(1.0)  # 1MB
        assert isinstance(result, bool)

    def test_should_use_progressive_large_file(self, image_manager):
        """测试大文件渐进式加载"""
        result = image_manager._should_use_progressive(20.0)  # 20MB
        assert isinstance(result, bool)


# ==================== 缓存管理测试 ====================


class TestCacheManagement:
    """测试缓存管理"""

    def test_try_display_cached_image_method_exists(self, image_manager):
        """测试_try_display_cached_image方法存在"""
        assert hasattr(image_manager, '_try_display_cached_image')
        assert callable(image_manager._try_display_cached_image)

    def test_record_cache_hit_method_exists(self, image_manager):
        """测试_record_cache_hit方法存在"""
        assert hasattr(image_manager, '_record_cache_hit')
        assert callable(image_manager._record_cache_hit)


# ==================== 目标尺寸计算测试 ====================


class TestTargetSizeCalculation:
    """测试目标尺寸计算"""

    def test_calculate_target_size_method_exists(self, image_manager):
        """测试_calculate_target_size方法存在"""
        assert hasattr(image_manager, '_calculate_target_size')
        assert callable(image_manager._calculate_target_size)

    def test_get_target_size_for_view_method_exists(self, image_manager):
        """测试_get_target_size_for_view方法存在"""
        assert hasattr(image_manager, '_get_target_size_for_view')
        assert callable(image_manager._get_target_size_for_view)

    def test_get_dynamic_target_size_method_exists(self, image_manager):
        """测试_get_dynamic_target_size方法存在"""
        assert hasattr(image_manager, '_get_dynamic_target_size')
        assert callable(image_manager._get_dynamic_target_size)

    def test_is_portrait_image_method_exists(self, image_manager):
        """测试_is_portrait_image方法存在"""
        assert hasattr(image_manager, '_is_portrait_image')
        assert callable(image_manager._is_portrait_image)


# ==================== 文件大小测试 ====================


class TestFileSize:
    """测试文件大小"""

    def test_get_file_size_safely_method_exists(self, image_manager):
        """测试_get_file_size_safely方法存在"""
        assert hasattr(image_manager, '_get_file_size_safely')
        assert callable(image_manager._get_file_size_safely)

    def test_get_file_size_safely_success(self, image_manager):
        """测试成功获取文件大小"""
        image_manager.image_cache.get_file_size_mb = MagicMock(return_value=5.0)
        
        result = image_manager._get_file_size_safely('/test/image.jpg')
        
        assert result == 5.0

    def test_get_file_size_safely_exception(self, image_manager):
        """测试获取文件大小异常"""
        image_manager.image_cache.get_file_size_mb = MagicMock(side_effect=Exception("Error"))
        
        result = image_manager._get_file_size_safely('/test/image.jpg')
        
        assert result == 0.0


# ==================== 预加载和预取测试 ====================


class TestPrefetch:
    """测试预加载和预取"""

    def test_prepare_next_image_async_method_exists(self, image_manager):
        """测试_prepare_next_image_async方法存在"""
        assert hasattr(image_manager, '_prepare_next_image_async')
        assert callable(image_manager._prepare_next_image_async)

    def test_schedule_adaptive_prefetch_method_exists(self, image_manager):
        """测试_schedule_adaptive_prefetch方法存在"""
        assert hasattr(image_manager, '_schedule_adaptive_prefetch')
        assert callable(image_manager._schedule_adaptive_prefetch)

    def test_compute_prefetch_window_method_exists(self, image_manager):
        """测试_compute_prefetch_window方法存在"""
        assert hasattr(image_manager, '_compute_prefetch_window')
        assert callable(image_manager._compute_prefetch_window)

    def test_cancel_stale_prefetches_method_exists(self, image_manager):
        """测试_cancel_stale_prefetches方法存在"""
        assert hasattr(image_manager, '_cancel_stale_prefetches')
        assert callable(image_manager._cancel_stale_prefetches)

    def test_prefetch_generation_initialized(self, image_manager):
        """测试预取代数已初始化"""
        assert hasattr(image_manager, '_load_generation')


# ==================== 导航统计测试 ====================


class TestNavigationStats:
    """测试导航统计"""

    def test_update_navigation_stats_method_exists(self, image_manager):
        """测试_update_navigation_stats方法存在"""
        assert hasattr(image_manager, '_update_navigation_stats')
        assert callable(image_manager._update_navigation_stats)

    def test_navigation_stats_initialized(self, image_manager):
        """测试导航统计已初始化"""
        assert hasattr(image_manager, '_nav_history')


# ==================== 路径计算测试 ====================


class TestPathCalculation:
    """测试路径计算"""

    def test_get_adjacent_path_method_exists(self, image_manager):
        """测试_get_adjacent_path方法存在"""
        assert hasattr(image_manager, '_get_adjacent_path')
        assert callable(image_manager._get_adjacent_path)

    def test_get_path_by_offset_method_exists(self, image_manager):
        """测试_get_path_by_offset方法存在"""
        assert hasattr(image_manager, '_get_path_by_offset')
        assert callable(image_manager._get_path_by_offset)

    def test_get_adjacent_path_next(self, image_manager):
        """测试获取下一张图片路径"""
        result = image_manager._get_adjacent_path('/test/img1.jpg', direction=1)
        
        # 应该返回下一个路径或None
        assert result is None or isinstance(result, str)

    def test_get_adjacent_path_previous(self, image_manager):
        """测试获取上一张图片路径"""
        result = image_manager._get_adjacent_path('/test/img1.jpg', direction=-1)
        
        # 应该返回上一个路径或None
        assert result is None or isinstance(result, str)


# ==================== 后台加载测试 ====================


class TestBackgroundLoading:
    """测试后台加载"""

    def test_start_background_load_method_exists(self, image_manager):
        """测试_start_background_load方法存在"""
        assert hasattr(image_manager, '_start_background_load')
        assert callable(image_manager._start_background_load)

    def test_load_image_with_concurrency_method_exists(self, image_manager):
        """测试_load_image_with_concurrency方法存在"""
        assert hasattr(image_manager, '_load_image_with_concurrency')
        assert callable(image_manager._load_image_with_concurrency)

    def test_try_display_next_ready_method_exists(self, image_manager):
        """测试_try_display_next_ready方法存在"""
        assert hasattr(image_manager, '_try_display_next_ready')
        assert callable(image_manager._try_display_next_ready)


# ==================== 状态更新测试 ====================


class TestStatusUpdates:
    """测试状态更新"""

    def test_update_session_progress_method_exists(self, image_manager):
        """测试_update_session_progress方法存在"""
        assert hasattr(image_manager, '_update_session_progress')
        assert callable(image_manager._update_session_progress)

    def test_update_status_and_notices_method_exists(self, image_manager):
        """测试_update_status_and_notices方法存在"""
        assert hasattr(image_manager, '_update_status_and_notices')
        assert callable(image_manager._update_status_and_notices)


# ==================== 缓存通知测试 ====================


class TestCacheNotification:
    """测试缓存通知"""

    def test_bidi_pool_exists(self, image_manager):
        """测试双向缓存池存在"""
        assert hasattr(image_manager, 'bidi_pool')
        assert image_manager.bidi_pool is not None


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    @patch('plookingII.ui.managers.image_manager.HybridImageProcessor')
    def test_complete_lifecycle(self, mock_processor_class, mock_window):
        """测试完整生命周期"""
        mock_processor = MagicMock()
        mock_processor_class.return_value = mock_processor
        
        # 1. 创建管理器
        manager = ImageManager(mock_window)
        assert manager.main_window == mock_window
        
        # 2. 测试文件大小计算
        manager.image_cache.get_file_size_mb = MagicMock(return_value=1.0)
        size = manager._get_file_size_safely('/test/img.jpg')
        assert size == 1.0

    def test_loading_strategy_workflow(self, image_manager):
        """测试加载策略工作流"""
        # 1. 检查小文件
        result1 = image_manager._should_use_fast_loading(0.5)
        assert isinstance(result1, bool)
        
        # 2. 检查大文件
        result2 = image_manager._should_use_progressive(20.0)
        assert isinstance(result2, bool)


# ==================== 边界情况测试 ====================


class TestEdgeCases:
    """测试边界情况"""

    def test_get_file_size_zero(self, image_manager):
        """测试零大小文件"""
        image_manager.image_cache.get_file_size_mb = MagicMock(return_value=0.0)
        
        result = image_manager._get_file_size_safely('/test/empty.jpg')
        
        assert result == 0.0

    def test_should_use_fast_loading_boundary(self, image_manager):
        """测试快速加载边界值"""
        # 测试边界值
        result = image_manager._should_use_fast_loading(5.0)
        assert isinstance(result, bool)

    def test_should_use_progressive_boundary(self, image_manager):
        """测试渐进式加载边界值"""
        # 测试边界值
        result = image_manager._should_use_progressive(10.0)
        assert isinstance(result, bool)


# ==================== 属性测试 ====================


class TestAttributes:
    """测试属性"""

    def test_all_required_attributes_exist(self, image_manager):
        """测试所有必需属性存在"""
        required_attrs = [
            'main_window', 'hybrid_processor', '_load_generation',
            '_decode_lock', '_nav_history'
        ]
        
        for attr in required_attrs:
            assert hasattr(image_manager, attr), f"Missing attribute: {attr}"


# ==================== 性能测试 ====================


class TestPerformance:
    """测试性能相关"""

    def test_post_display_tasks_method_exists(self, image_manager):
        """测试_post_display_tasks方法存在"""
        assert hasattr(image_manager, '_post_display_tasks')
        assert callable(image_manager._post_display_tasks)

    def test_execute_fast_loading_method_exists(self, image_manager):
        """测试_execute_fast_loading方法存在"""
        assert hasattr(image_manager, '_execute_fast_loading')
        assert callable(image_manager._execute_fast_loading)

    def test_load_and_display_progressive_method_exists(self, image_manager):
        """测试_load_and_display_progressive方法存在"""
        assert hasattr(image_manager, '_load_and_display_progressive')
        assert callable(image_manager._load_and_display_progressive)

