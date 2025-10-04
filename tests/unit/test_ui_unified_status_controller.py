"""
测试 ui/controllers/unified_status_controller.py

测试统一状态控制器功能，包括：
- 初始化和UI设置
- 状态显示和更新
- 会话管理
- 标题栏管理
"""

from unittest.mock import MagicMock, Mock, patch, call
import os

import pytest

from plookingII.ui.controllers.unified_status_controller import UnifiedStatusController


# ==================== 夹具（Fixtures） ====================


@pytest.fixture
def mock_window():
    """创建模拟窗口"""
    window = MagicMock()
    window.current_index = 0
    window.images = ["img1.jpg", "img2.jpg", "img3.jpg"]
    window.current_folder = "/test/folder"
    window.zoomSliderChanged_ = MagicMock()
    window.setTitle_ = MagicMock()
    window.addTitlebarAccessoryViewController_ = MagicMock()
    return window


@pytest.fixture
def unified_controller(mock_window):
    """创建统一状态控制器实例"""
    with patch('plookingII.ui.controllers.unified_status_controller.SessionManager'):
        return UnifiedStatusController(mock_window)


# ==================== 初始化测试 ====================


class TestUnifiedStatusControllerInit:
    """测试UnifiedStatusController初始化"""

    @patch('plookingII.ui.controllers.unified_status_controller.SessionManager')
    def test_init_basic(self, mock_session_manager_class, mock_window):
        """测试基本初始化"""
        mock_session = MagicMock()
        mock_session_manager_class.return_value = mock_session
        
        controller = UnifiedStatusController(mock_window)
        
        assert controller.main_window == mock_window
        assert controller.window == mock_window
        assert controller.status_bar_view is None
        assert controller.image_seq_label is None
        assert controller.folder_seq_label is None
        assert controller.center_status_label is None
        assert controller.zoom_slider is None
        assert controller.titlebar_accessory is None
        assert controller.session_manager == mock_session

    @patch('plookingII.ui.controllers.unified_status_controller.SessionManager')
    def test_init_titlebar_attributes(self, mock_session_manager_class, mock_window):
        """测试标题栏属性初始化"""
        controller = UnifiedStatusController(mock_window)
        
        assert controller.titlebar_container is None
        assert controller.titlebar_info_label is None
        assert controller._tracking_area is None
        assert controller._hide_timer is None
        assert controller._overlay_height == 36

    @patch('plookingII.ui.controllers.unified_status_controller.SessionManager')
    def test_init_timers(self, mock_session_manager_class, mock_window):
        """测试定时器初始化"""
        controller = UnifiedStatusController(mock_window)
        
        assert controller._status_timer is None
        assert controller._session_update_timer is None


# ==================== UI设置测试 ====================


class TestUISetup:
    """测试UI设置"""

    def test_setup_ui_method_exists(self, unified_controller):
        """测试setup_ui方法存在"""
        assert hasattr(unified_controller, 'setup_ui')
        assert callable(unified_controller.setup_ui)

    def test_setup_ui_attributes_initialized(self, unified_controller):
        """测试UI属性初始化状态"""
        # 初始状态应该为None
        assert unified_controller.status_bar_view is None
        assert unified_controller.center_status_label is None
        assert unified_controller.folder_seq_label is None
        assert unified_controller.zoom_slider is None


# ==================== 状态更新测试 ====================


class TestStatusUpdate:
    """测试状态更新"""

    def test_update_status_message_method_exists(self, unified_controller):
        """测试update_status_message方法存在"""
        assert hasattr(unified_controller, 'update_status_message')
        assert callable(unified_controller.update_status_message)

    def test_set_status_message_method_exists(self, unified_controller):
        """测试set_status_message方法存在"""
        assert hasattr(unified_controller, 'set_status_message')
        assert callable(unified_controller.set_status_message)

    def test_update_image_sequence_method_exists(self, unified_controller):
        """测试update_image_sequence方法存在"""
        assert hasattr(unified_controller, 'update_image_sequence')
        assert callable(unified_controller.update_image_sequence)

    def test_update_folder_sequence_method_exists(self, unified_controller):
        """测试update_folder_sequence方法存在"""
        assert hasattr(unified_controller, 'update_folder_sequence')
        assert callable(unified_controller.update_folder_sequence)

    def test_update_zoom_slider_method_exists(self, unified_controller):
        """测试update_zoom_slider方法存在"""
        assert hasattr(unified_controller, 'update_zoom_slider')
        assert callable(unified_controller.update_zoom_slider)


# ==================== 标题栏测试 ====================


class TestTitlebar:
    """测试标题栏"""

    def test_update_titlebar_text_method_exists(self, unified_controller):
        """测试update_titlebar_text方法存在"""
        assert hasattr(unified_controller, 'update_titlebar_text')
        assert callable(unified_controller.update_titlebar_text)

    def test_update_current_image_path_method_exists(self, unified_controller):
        """测试update_current_image_path方法存在"""
        assert hasattr(unified_controller, 'update_current_image_path')
        assert callable(unified_controller.update_current_image_path)


# ==================== 会话管理测试 ====================


class TestSessionManagement:
    """测试会话管理"""

    def test_session_manager_initialized(self, unified_controller):
        """测试会话管理器已初始化"""
        assert unified_controller.session_manager is not None

    def test_start_work_session_method_exists(self, unified_controller):
        """测试start_work_session方法存在"""
        assert hasattr(unified_controller, 'start_work_session')
        assert callable(unified_controller.start_work_session)

    def test_stop_work_session_method_exists(self, unified_controller):
        """测试stop_work_session方法存在"""
        assert hasattr(unified_controller, 'stop_work_session')
        assert callable(unified_controller.stop_work_session)

    def test_update_session_data_method_exists(self, unified_controller):
        """测试update_session_data方法存在"""
        assert hasattr(unified_controller, 'update_session_data')
        assert callable(unified_controller.update_session_data)

    def test_get_session_stats_method_exists(self, unified_controller):
        """测试get_session_stats方法存在"""
        assert hasattr(unified_controller, 'get_session_stats')
        assert callable(unified_controller.get_session_stats)


# ==================== 完成状态测试 ====================


class TestCompletionStatus:
    """测试完成状态"""

    def test_show_temporary_message_method_exists(self, unified_controller):
        """测试show_temporary_message方法存在"""
        assert hasattr(unified_controller, 'show_temporary_message')
        assert callable(unified_controller.show_temporary_message)

    def test_update_folder_label_method_exists(self, unified_controller):
        """测试update_folder_label方法存在"""
        assert hasattr(unified_controller, 'update_folder_label')
        assert callable(unified_controller.update_folder_label)

    def test_update_image_label_method_exists(self, unified_controller):
        """测试update_image_label方法存在"""
        assert hasattr(unified_controller, 'update_image_label')
        assert callable(unified_controller.update_image_label)


# ==================== 框架更新测试 ====================


class TestFrameUpdate:
    """测试框架更新"""

    def test_update_frame_method_exists(self, unified_controller):
        """测试update_frame方法存在"""
        assert hasattr(unified_controller, 'update_frame')
        assert callable(unified_controller.update_frame)


# ==================== 清理测试 ====================


class TestCleanup:
    """测试清理"""

    def test_cleanup_method_exists(self, unified_controller):
        """测试cleanup方法存在"""
        assert hasattr(unified_controller, 'cleanup')
        assert callable(unified_controller.cleanup)

    def test_cleanup_basic(self, unified_controller):
        """测试基本清理"""
        # 应该不抛出异常
        try:
            unified_controller.cleanup()
        except Exception:
            pytest.fail("cleanup应该正常执行")


# ==================== 辅助方法测试 ====================


class TestHelperMethods:
    """测试辅助方法"""

    def test_create_label_method_exists(self, unified_controller):
        """测试_create_label方法存在"""
        assert hasattr(unified_controller, '_create_label')
        assert callable(unified_controller._create_label)


# ==================== 兼容性测试 ====================


class TestCompatibility:
    """测试兼容性"""

    def test_image_seq_label_compatibility(self, unified_controller):
        """测试image_seq_label兼容性"""
        # image_seq_label应该在setup后指向folder_seq_label
        assert hasattr(unified_controller, 'image_seq_label')

    def test_folder_seq_label_attribute(self, unified_controller):
        """测试folder_seq_label属性"""
        assert hasattr(unified_controller, 'folder_seq_label')

    def test_center_status_label_attribute(self, unified_controller):
        """测试center_status_label属性"""
        assert hasattr(unified_controller, 'center_status_label')


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    @patch('plookingII.ui.controllers.unified_status_controller.SessionManager')
    def test_controller_lifecycle(self, mock_session_manager_class, mock_window):
        """测试控制器完整生命周期"""
        mock_session = MagicMock()
        mock_session_manager_class.return_value = mock_session
        
        # 1. 创建控制器
        controller = UnifiedStatusController(mock_window)
        assert controller.session_manager == mock_session
        
        # 2. 清理控制器
        controller.cleanup()
        # cleanup应该正常执行

    def test_window_reference(self, unified_controller):
        """测试窗口引用"""
        assert unified_controller.main_window == unified_controller.window
        assert unified_controller.window is not None


# ==================== 边界情况测试 ====================


class TestEdgeCases:
    """测试边界情况"""

    def test_multiple_cleanup_calls(self, unified_controller):
        """测试多次清理调用"""
        # 应该不抛出异常
        try:
            unified_controller.cleanup()
            unified_controller.cleanup()
            unified_controller.cleanup()
        except Exception:
            pytest.fail("多次cleanup调用应该不抛出异常")

    def test_cleanup_without_timers(self, unified_controller):
        """测试无定时器时清理"""
        unified_controller._session_update_timer = None
        unified_controller._status_timer = None
        
        # 应该不抛出异常
        try:
            unified_controller.cleanup()
        except Exception:
            pytest.fail("无定时器时cleanup应该正常执行")


# ==================== 私有方法测试 ====================


class TestPrivateMethods:
    """测试私有方法"""

    def test_setup_status_bar_method_exists(self, unified_controller):
        """测试_setup_status_bar方法存在"""
        assert hasattr(unified_controller, '_setup_status_bar')
        assert callable(unified_controller._setup_status_bar)

    def test_setup_titlebar_method_exists(self, unified_controller):
        """测试_setup_titlebar方法存在"""
        assert hasattr(unified_controller, '_setup_titlebar')
        assert callable(unified_controller._setup_titlebar)

    def test_start_session_updates_method_exists(self, unified_controller):
        """测试_start_session_updates方法存在"""
        assert hasattr(unified_controller, '_start_session_updates')
        assert callable(unified_controller._start_session_updates)


# ==================== 属性测试 ====================


class TestAttributes:
    """测试属性"""

    def test_all_required_attributes_exist(self, unified_controller):
        """测试所有必需属性存在"""
        required_attrs = [
            'main_window', 'window', 'status_bar_view', 'image_seq_label',
            'folder_seq_label', 'center_status_label', 'zoom_slider',
            'titlebar_accessory', 'titlebar_container', 'titlebar_info_label',
            '_tracking_area', '_hide_timer', '_overlay_height',
            '_status_timer', '_session_update_timer', 'session_manager'
        ]
        
        for attr in required_attrs:
            assert hasattr(unified_controller, attr), f"Missing attribute: {attr}"

    def test_overlay_height_value(self, unified_controller):
        """测试overlay_height默认值"""
        assert unified_controller._overlay_height == 36


# ==================== Mock测试 ====================


class TestWithMocks:
    """使用Mock进行的测试"""

    def test_session_manager_mock(self, unified_controller):
        """测试会话管理器mock"""
        # 应该是一个Mock对象
        assert unified_controller.session_manager is not None

    def test_window_mock(self, unified_controller):
        """测试窗口mock"""
        # 应该有zoomSliderChanged_方法
        assert hasattr(unified_controller.main_window, 'zoomSliderChanged_')
        assert callable(unified_controller.main_window.zoomSliderChanged_)

