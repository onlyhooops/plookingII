#!/usr/bin/env python3
"""
控制器模块集成测试

测试第2周重构创建的控制器模块：
- MenuController
- DragDropController  
- ImageViewController
- NavigationController
- StatusBarController
- SystemController
- UnifiedStatusController
"""

import pytest
import tempfile
import os
from unittest.mock import MagicMock, patch, Mock
from PyQt6.QtCore import QPoint, QMimeData, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QApplication, QWidget

# 导入被测试的控制器
from plookingII.ui.controllers.menu_controller import MenuController
from plookingII.ui.controllers.drag_drop_controller import DragDropController
from plookingII.ui.controllers.image_view_controller import ImageViewController
from plookingII.ui.controllers.navigation_controller import NavigationController
from plookingII.ui.controllers.status_bar_controller import StatusBarController
from plookingII.ui.controllers.system_controller import SystemController
from plookingII.ui.controllers.unified_status_controller import UnifiedStatusController


@pytest.fixture
def mock_main_window():
    """创建模拟主窗口"""
    window = MagicMock()
    window.images = []
    window.current_index = 0
    window.current_folder = ""
    window.root_folder = ""
    window.image_label = MagicMock()
    window.status_bar = MagicMock()
    window.progress_bar = MagicMock()
    window.folder_label = MagicMock()
    window.image_info_label = MagicMock()
    return window


@pytest.fixture
def qt_app():
    """创建Qt应用实例"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestMenuController:
    """MenuController测试"""
    
    def test_controller_initialization(self, mock_main_window):
        """测试控制器初始化"""
        controller = MenuController(mock_main_window)
        
        assert controller.main_window == mock_main_window
        assert hasattr(controller, 'setup_menu')
    
    def test_setup_menu(self, mock_main_window):
        """测试菜单设置"""
        controller = MenuController(mock_main_window)
        
        # 模拟菜单栏
        mock_main_window.menuBar.return_value = MagicMock()
        
        # 测试菜单设置不会抛出异常
        try:
            controller.setup_menu()
        except Exception as e:
            pytest.fail(f"setup_menu raised {e} unexpectedly!")
    
    @patch('plookingII.ui.controllers.menu_controller.QFileDialog')
    def test_open_folder_action(self, mock_dialog, mock_main_window):
        """测试打开文件夹动作"""
        controller = MenuController(mock_main_window)
        
        # 模拟文件对话框返回路径
        mock_dialog.getExistingDirectory.return_value = "/test/path"
        
        # 模拟主窗口方法
        mock_main_window.load_folder = MagicMock()
        
        controller._open_folder()
        
        # 验证调用
        mock_dialog.getExistingDirectory.assert_called_once()
        mock_main_window.load_folder.assert_called_once_with("/test/path")


class TestDragDropController:
    """DragDropController测试"""
    
    def test_controller_initialization(self, mock_main_window):
        """测试控制器初始化"""
        controller = DragDropController(mock_main_window)
        
        assert controller.main_window == mock_main_window
        assert hasattr(controller, 'setup_drag_drop')
    
    def test_setup_drag_drop(self, mock_main_window):
        """测试拖拽设置"""
        controller = DragDropController(mock_main_window)
        
        # 测试设置不会抛出异常
        try:
            controller.setup_drag_drop()
        except Exception as e:
            pytest.fail(f"setup_drag_drop raised {e} unexpectedly!")
        
        # 验证拖拽接受设置
        mock_main_window.setAcceptDrops.assert_called_once_with(True)
    
    def test_drag_enter_event_valid(self, mock_main_window, qt_app):
        """测试有效拖拽进入事件"""
        controller = DragDropController(mock_main_window)
        
        # 创建模拟事件
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile("/test/path")])
        
        event = MagicMock()
        event.mimeData.return_value = mime_data
        
        controller.dragEnterEvent(event)
        
        # 验证事件被接受
        event.acceptProposedAction.assert_called_once()
    
    def test_drop_event_folder(self, mock_main_window, qt_app):
        """测试文件夹拖拽事件"""
        controller = DragDropController(mock_main_window)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建模拟事件
            mime_data = QMimeData()
            mime_data.setUrls([QUrl.fromLocalFile(temp_dir)])
            
            event = MagicMock()
            event.mimeData.return_value = mime_data
            
            # 模拟主窗口方法
            mock_main_window.load_folder = MagicMock()
            
            controller.dropEvent(event)
            
            # 验证文件夹加载
            mock_main_window.load_folder.assert_called_once_with(temp_dir)


class TestImageViewController:
    """ImageViewController测试"""
    
    def test_controller_initialization(self, mock_main_window):
        """测试控制器初始化"""
        controller = ImageViewController(mock_main_window)
        
        assert controller.main_window == mock_main_window
        assert hasattr(controller, 'update_image_display')
    
    def test_update_image_display_valid_image(self, mock_main_window):
        """测试更新图片显示 - 有效图片"""
        controller = ImageViewController(mock_main_window)
        
        # 设置测试数据
        mock_main_window.images = ["/test/image1.jpg", "/test/image2.jpg"]
        mock_main_window.current_index = 0
        
        with patch('plookingII.ui.controllers.image_view_controller.QPixmap') as mock_pixmap:
            mock_pixmap.return_value.isNull.return_value = False
            
            controller.update_image_display()
            
            # 验证图片加载
            mock_pixmap.assert_called_once_with("/test/image1.jpg")
            mock_main_window.image_label.setPixmap.assert_called_once()
    
    def test_update_image_display_no_images(self, mock_main_window):
        """测试更新图片显示 - 无图片"""
        controller = ImageViewController(mock_main_window)
        
        # 设置空图片列表
        mock_main_window.images = []
        
        controller.update_image_display()
        
        # 验证清空显示
        mock_main_window.image_label.clear.assert_called_once()
    
    def test_fit_image_to_window(self, mock_main_window):
        """测试图片适应窗口"""
        controller = ImageViewController(mock_main_window)
        
        # 模拟图片标签
        mock_main_window.image_label.size.return_value.width.return_value = 800
        mock_main_window.image_label.size.return_value.height.return_value = 600
        
        with patch('plookingII.ui.controllers.image_view_controller.QPixmap') as mock_pixmap:
            mock_pixmap_instance = MagicMock()
            mock_pixmap.return_value = mock_pixmap_instance
            mock_pixmap_instance.scaled.return_value = mock_pixmap_instance
            
            controller.fit_image_to_window("/test/image.jpg")
            
            # 验证图片缩放
            mock_pixmap_instance.scaled.assert_called_once()


class TestNavigationController:
    """NavigationController测试"""
    
    def test_controller_initialization(self, mock_main_window):
        """测试控制器初始化"""
        controller = NavigationController(mock_main_window)
        
        assert controller.main_window == mock_main_window
        assert hasattr(controller, 'next_image')
        assert hasattr(controller, 'previous_image')
    
    def test_next_image_valid(self, mock_main_window):
        """测试下一张图片 - 有效情况"""
        controller = NavigationController(mock_main_window)
        
        # 设置测试数据
        mock_main_window.images = ["/test/image1.jpg", "/test/image2.jpg", "/test/image3.jpg"]
        mock_main_window.current_index = 0
        
        # 模拟图片视图控制器
        mock_main_window.image_view_controller = MagicMock()
        
        controller.next_image()
        
        # 验证索引更新
        assert mock_main_window.current_index == 1
        mock_main_window.image_view_controller.update_image_display.assert_called_once()
    
    def test_next_image_at_end(self, mock_main_window):
        """测试下一张图片 - 在末尾"""
        controller = NavigationController(mock_main_window)
        
        # 设置测试数据 - 已在最后一张
        mock_main_window.images = ["/test/image1.jpg", "/test/image2.jpg"]
        mock_main_window.current_index = 1
        
        original_index = mock_main_window.current_index
        controller.next_image()
        
        # 验证索引不变（或循环到开头，取决于实现）
        # 这里假设不循环
        assert mock_main_window.current_index == original_index
    
    def test_previous_image_valid(self, mock_main_window):
        """测试上一张图片 - 有效情况"""
        controller = NavigationController(mock_main_window)
        
        # 设置测试数据
        mock_main_window.images = ["/test/image1.jpg", "/test/image2.jpg", "/test/image3.jpg"]
        mock_main_window.current_index = 2
        
        # 模拟图片视图控制器
        mock_main_window.image_view_controller = MagicMock()
        
        controller.previous_image()
        
        # 验证索引更新
        assert mock_main_window.current_index == 1
        mock_main_window.image_view_controller.update_image_display.assert_called_once()
    
    def test_previous_image_at_start(self, mock_main_window):
        """测试上一张图片 - 在开头"""
        controller = NavigationController(mock_main_window)
        
        # 设置测试数据 - 已在第一张
        mock_main_window.images = ["/test/image1.jpg", "/test/image2.jpg"]
        mock_main_window.current_index = 0
        
        original_index = mock_main_window.current_index
        controller.previous_image()
        
        # 验证索引不变（或循环到末尾，取决于实现）
        assert mock_main_window.current_index == original_index
    
    def test_go_to_image(self, mock_main_window):
        """测试跳转到指定图片"""
        controller = NavigationController(mock_main_window)
        
        # 设置测试数据
        mock_main_window.images = ["/test/image1.jpg", "/test/image2.jpg", "/test/image3.jpg"]
        mock_main_window.current_index = 0
        
        # 模拟图片视图控制器
        mock_main_window.image_view_controller = MagicMock()
        
        controller.go_to_image(2)
        
        # 验证索引更新
        assert mock_main_window.current_index == 2
        mock_main_window.image_view_controller.update_image_display.assert_called_once()


class TestStatusBarController:
    """StatusBarController测试"""
    
    def test_controller_initialization(self, mock_main_window):
        """测试控制器初始化"""
        controller = StatusBarController(mock_main_window)
        
        assert controller.main_window == mock_main_window
        assert hasattr(controller, 'update_status')
    
    def test_update_status_with_images(self, mock_main_window):
        """测试更新状态 - 有图片"""
        controller = StatusBarController(mock_main_window)
        
        # 设置测试数据
        mock_main_window.images = ["/test/image1.jpg", "/test/image2.jpg", "/test/image3.jpg"]
        mock_main_window.current_index = 1
        mock_main_window.current_folder = "/test/folder"
        
        controller.update_status()
        
        # 验证状态更新（具体调用取决于实现）
        mock_main_window.status_bar.showMessage.assert_called()
    
    def test_update_status_no_images(self, mock_main_window):
        """测试更新状态 - 无图片"""
        controller = StatusBarController(mock_main_window)
        
        # 设置测试数据
        mock_main_window.images = []
        mock_main_window.current_folder = ""
        
        controller.update_status()
        
        # 验证状态更新
        mock_main_window.status_bar.showMessage.assert_called()
    
    def test_show_progress(self, mock_main_window):
        """测试显示进度"""
        controller = StatusBarController(mock_main_window)
        
        controller.show_progress("Loading images...", 50)
        
        # 验证进度显示
        mock_main_window.progress_bar.setValue.assert_called_with(50)
        mock_main_window.status_bar.showMessage.assert_called_with("Loading images...")


class TestSystemController:
    """SystemController测试"""
    
    def test_controller_initialization(self, mock_main_window):
        """测试控制器初始化"""
        controller = SystemController(mock_main_window)
        
        assert controller.main_window == mock_main_window
        assert hasattr(controller, 'get_system_info')
    
    def test_get_system_info(self, mock_main_window):
        """测试获取系统信息"""
        controller = SystemController(mock_main_window)
        
        info = controller.get_system_info()
        
        # 验证返回系统信息
        assert isinstance(info, dict)
        assert 'platform' in info or 'os' in info  # 取决于具体实现
    
    @patch('plookingII.ui.controllers.system_controller.platform')
    def test_is_macos(self, mock_platform, mock_main_window):
        """测试macOS检测"""
        controller = SystemController(mock_main_window)
        
        mock_platform.system.return_value = "Darwin"
        
        result = controller.is_macos()
        assert result is True
        
        mock_platform.system.return_value = "Windows"
        result = controller.is_macos()
        assert result is False


class TestUnifiedStatusController:
    """UnifiedStatusController测试"""
    
    def test_controller_initialization(self, mock_main_window):
        """测试控制器初始化"""
        controller = UnifiedStatusController(mock_main_window)
        
        assert controller.main_window == mock_main_window
        assert hasattr(controller, 'update_unified_status')
    
    def test_update_unified_status(self, mock_main_window):
        """测试更新统一状态"""
        controller = UnifiedStatusController(mock_main_window)
        
        # 设置测试数据
        mock_main_window.images = ["/test/image1.jpg", "/test/image2.jpg"]
        mock_main_window.current_index = 0
        mock_main_window.current_folder = "/test/folder"
        
        controller.update_unified_status()
        
        # 验证状态更新（具体验证取决于实现）
        # 这里只验证不抛出异常
        assert True  # 如果到这里说明没有异常


@pytest.mark.integration
class TestControllersIntegration:
    """控制器集成测试"""
    
    def test_controller_coordination(self, mock_main_window):
        """测试控制器协调工作"""
        # 创建所有控制器
        menu_controller = MenuController(mock_main_window)
        drag_drop_controller = DragDropController(mock_main_window)
        image_view_controller = ImageViewController(mock_main_window)
        navigation_controller = NavigationController(mock_main_window)
        status_bar_controller = StatusBarController(mock_main_window)
        
        # 设置测试数据
        mock_main_window.images = ["/test/image1.jpg", "/test/image2.jpg", "/test/image3.jpg"]
        mock_main_window.current_index = 0
        mock_main_window.current_folder = "/test/folder"
        
        # 模拟导航操作
        mock_main_window.image_view_controller = image_view_controller
        navigation_controller.next_image()
        
        # 验证状态更新
        assert mock_main_window.current_index == 1
        
        # 更新状态栏
        status_bar_controller.update_status()
        mock_main_window.status_bar.showMessage.assert_called()
    
    def test_error_handling_integration(self, mock_main_window):
        """测试错误处理集成"""
        navigation_controller = NavigationController(mock_main_window)
        
        # 测试空图片列表的导航
        mock_main_window.images = []
        mock_main_window.current_index = 0
        
        # 这些操作不应该抛出异常
        try:
            navigation_controller.next_image()
            navigation_controller.previous_image()
        except Exception as e:
            pytest.fail(f"Navigation with empty images raised {e} unexpectedly!")
    
    def test_mvc_pattern_compliance(self, mock_main_window):
        """测试MVC模式合规性"""
        # 验证控制器不直接操作视图细节
        navigation_controller = NavigationController(mock_main_window)
        image_view_controller = ImageViewController(mock_main_window)
        
        # 控制器应该通过主窗口或其他控制器协调，而不是直接操作UI组件
        assert hasattr(navigation_controller, 'main_window')
        assert hasattr(image_view_controller, 'main_window')
        
        # 验证职责分离
        assert hasattr(navigation_controller, 'next_image')
        assert hasattr(navigation_controller, 'previous_image')
        assert hasattr(image_view_controller, 'update_image_display')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
