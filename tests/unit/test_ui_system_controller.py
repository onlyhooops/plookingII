"""
测试 ui/controllers/system_controller.py

测试系统功能控制器，包括：
- 初始化和通知设置
- 主题切换（自动和手动）
- 文件夹顺序管理
- 菜单状态更新
- 清理和资源释放
"""

from unittest.mock import MagicMock, Mock, patch, call

import pytest

from plookingII.ui.controllers.system_controller import SystemController


@pytest.fixture
def mock_window():
    """创建模拟的主窗口"""
    window = MagicMock()
    window.folder_manager = MagicMock()
    window.folder_manager.reverse_folder_order = False
    window.status_bar_controller = MagicMock()
    window.root_folder = "/test/folder"
    window.reverse_folder_order_menu_item = MagicMock()
    window.navigation_controller = MagicMock()
    window.image_manager = MagicMock()
    window.image_update_manager = MagicMock()
    window.contentView = MagicMock()
    return window


@pytest.fixture
def system_controller(mock_window):
    """创建SystemController实例"""
    with patch('plookingII.ui.controllers.system_controller.NSDistributedNotificationCenter'):
        controller = SystemController(mock_window)
        return controller


# ==================== 初始化测试 ====================


class TestSystemControllerInit:
    """测试SystemController初始化"""

    def test_init_basic(self, mock_window):
        """测试基本初始化"""
        with patch('plookingII.ui.controllers.system_controller.NSDistributedNotificationCenter'):
            controller = SystemController(mock_window)
            
            assert controller.window == mock_window
            assert controller._shutting_down is False

    def test_init_sets_up_notifications(self, mock_window):
        """测试初始化设置系统通知"""
        with patch('plookingII.ui.controllers.system_controller.NSDistributedNotificationCenter') as mock_center_class:
            mock_center = MagicMock()
            mock_center_class.defaultCenter.return_value = mock_center
            
            controller = SystemController(mock_window)
            
            # 验证添加了通知监听
            assert mock_center.addObserver_selector_name_object_.called

    def test_init_notification_setup_failure(self, mock_window):
        """测试通知设置失败"""
        with patch('plookingII.ui.controllers.system_controller.NSDistributedNotificationCenter') as mock_center_class:
            mock_center_class.defaultCenter.side_effect = Exception("Notification setup failed")
            
            # 不应该抛出异常
            controller = SystemController(mock_window)
            assert controller.window == mock_window


# ==================== 系统通知设置测试 ====================


class TestSystemNotifications:
    """测试系统通知设置"""

    def test_setup_system_notifications_success(self, mock_window):
        """测试成功设置系统通知"""
        with patch('plookingII.ui.controllers.system_controller.NSDistributedNotificationCenter') as mock_center_class:
            mock_center = MagicMock()
            mock_center_class.defaultCenter.return_value = mock_center
            
            controller = SystemController(mock_window)
            controller._setup_system_notifications()
            
            # 验证监听器被添加
            assert mock_center.addObserver_selector_name_object_.call_count >= 1

    def test_setup_system_notifications_exception(self, mock_window):
        """测试通知设置异常处理"""
        with patch('plookingII.ui.controllers.system_controller.NSDistributedNotificationCenter') as mock_center_class:
            mock_center = MagicMock()
            mock_center.addObserver_selector_name_object_.side_effect = Exception("Setup failed")
            mock_center_class.defaultCenter.return_value = mock_center
            
            # 不应该抛出异常
            controller = SystemController(mock_window)


# ==================== 主题切换测试 ====================


class TestThemeManagement:
    """测试主题管理"""

    def test_handle_system_theme_changed_to_light(self, system_controller):
        """测试系统主题变化到浅色"""
        with patch('plookingII.ui.controllers.system_controller.NSApplication') as mock_app_class:
            with patch('plookingII.ui.controllers.system_controller.NSAppearance') as mock_appearance_class:
                with patch('plookingII.ui.controllers.system_controller.NSAppearanceNameDarkAqua', 'DarkAqua'):
                    with patch('plookingII.ui.controllers.system_controller.NSAppearanceNameAqua', 'Aqua'):
                        mock_app = MagicMock()
                        mock_appearance = MagicMock()
                        mock_appearance.name.return_value = 'DarkAqua'
                        mock_app.appearance.return_value = mock_appearance
                        mock_app_class.sharedApplication.return_value = mock_app
                        
                        system_controller.handle_system_theme_changed(None)
                        
                        # 验证设置了浅色主题
                        assert mock_app.setAppearance_.called

    def test_handle_system_theme_changed_to_dark(self, system_controller):
        """测试系统主题变化到深色"""
        with patch('plookingII.ui.controllers.system_controller.NSApplication') as mock_app_class:
            with patch('plookingII.ui.controllers.system_controller.NSAppearance'):
                with patch('plookingII.ui.controllers.system_controller.NSAppearanceNameDarkAqua', 'DarkAqua'):
                    with patch('plookingII.ui.controllers.system_controller.NSAppearanceNameAqua', 'Aqua'):
                        mock_app = MagicMock()
                        mock_appearance = MagicMock()
                        mock_appearance.name.return_value = 'Aqua'
                        mock_app.appearance.return_value = mock_appearance
                        mock_app_class.sharedApplication.return_value = mock_app
                        
                        system_controller.handle_system_theme_changed(None)
                        
                        # 验证设置了深色主题
                        assert mock_app.setAppearance_.called

    def test_handle_system_theme_changed_refresh_ui(self, system_controller, mock_window):
        """测试主题变化刷新UI"""
        with patch('plookingII.ui.controllers.system_controller.NSApplication') as mock_app_class:
            with patch('plookingII.ui.controllers.system_controller.NSAppearance'):
                mock_app = MagicMock()
                mock_appearance = MagicMock()
                mock_app.appearance.return_value = mock_appearance
                mock_app_class.sharedApplication.return_value = mock_app
                
                mock_content_view = MagicMock()
                mock_window.contentView.return_value = mock_content_view
                
                system_controller.handle_system_theme_changed(None)
                
                # 验证刷新了UI
                mock_content_view.setNeedsDisplay_.assert_called_with(True)

    def test_handle_system_theme_changed_exception(self, system_controller):
        """测试主题变化异常处理"""
        with patch('plookingII.ui.controllers.system_controller.NSApplication') as mock_app_class:
            mock_app_class.sharedApplication.side_effect = Exception("Theme change failed")
            
            # 不应该抛出异常
            system_controller.handle_system_theme_changed(None)

    def test_toggle_theme_from_dark_to_light(self, system_controller):
        """测试从深色切换到浅色"""
        with patch('plookingII.ui.controllers.system_controller.NSApplication') as mock_app_class:
            with patch('plookingII.ui.controllers.system_controller.NSAppearance') as mock_appearance_class:
                with patch('plookingII.ui.controllers.system_controller.NSAppearanceNameDarkAqua', 'DarkAqua'):
                    with patch('plookingII.ui.controllers.system_controller.NSAppearanceNameAqua', 'Aqua'):
                        mock_app = MagicMock()
                        mock_appearance = MagicMock()
                        mock_appearance.name.return_value = 'DarkAqua'
                        mock_app.appearance.return_value = mock_appearance
                        mock_app_class.sharedApplication.return_value = mock_app
                        
                        system_controller.toggle_theme(None)
                        
                        # 验证切换了主题
                        assert mock_app.setAppearance_.called

    def test_toggle_theme_from_light_to_dark(self, system_controller):
        """测试从浅色切换到深色"""
        with patch('plookingII.ui.controllers.system_controller.NSApplication') as mock_app_class:
            with patch('plookingII.ui.controllers.system_controller.NSAppearance'):
                with patch('plookingII.ui.controllers.system_controller.NSAppearanceNameDarkAqua', 'DarkAqua'):
                    with patch('plookingII.ui.controllers.system_controller.NSAppearanceNameAqua', 'Aqua'):
                        mock_app = MagicMock()
                        mock_appearance = MagicMock()
                        mock_appearance.name.return_value = 'Aqua'
                        mock_app.appearance.return_value = mock_appearance
                        mock_app_class.sharedApplication.return_value = mock_app
                        
                        system_controller.toggle_theme(None)
                        
                        assert mock_app.setAppearance_.called

    def test_toggle_theme_exception(self, system_controller):
        """测试主题切换异常处理"""
        with patch('plookingII.ui.controllers.system_controller.NSApplication') as mock_app_class:
            mock_app_class.sharedApplication.side_effect = Exception("Toggle failed")
            
            # 不应该抛出异常
            system_controller.toggle_theme(None)


# ==================== 文件夹顺序管理测试 ====================


class TestFolderOrderManagement:
    """测试文件夹顺序管理"""

    def test_reverse_folder_order_from_false_to_true(self, system_controller, mock_window):
        """测试从升序切换到降序"""
        mock_window.folder_manager.reverse_folder_order = False
        
        system_controller.reverse_folder_order(None)
        
        # 验证设置了reverse_folder_order
        mock_window.folder_manager.set_reverse_folder_order.assert_called_with(True)
        # 验证重新加载了root folder
        mock_window.folder_manager.load_images_from_root.assert_called_with("/test/folder")

    def test_reverse_folder_order_from_true_to_false(self, system_controller, mock_window):
        """测试从降序切换到升序"""
        mock_window.folder_manager.reverse_folder_order = True
        
        system_controller.reverse_folder_order(None)
        
        mock_window.folder_manager.set_reverse_folder_order.assert_called_with(False)

    def test_reverse_folder_order_updates_status(self, system_controller, mock_window):
        """测试切换顺序更新状态消息"""
        mock_window.folder_manager.reverse_folder_order = False
        
        system_controller.reverse_folder_order(None)
        
        # 验证更新了状态消息
        assert mock_window.status_bar_controller.set_status_message.called

    def test_reverse_folder_order_no_root_folder(self, system_controller, mock_window):
        """测试没有root_folder时"""
        mock_window.root_folder = None
        
        system_controller.reverse_folder_order(None)
        
        # 不应该调用load_images_from_root
        mock_window.folder_manager.load_images_from_root.assert_not_called()

    def test_reverse_folder_order_no_status_bar(self, system_controller, mock_window):
        """测试没有status_bar_controller"""
        del mock_window.status_bar_controller
        
        # 不应该抛出异常
        system_controller.reverse_folder_order(None)

    def test_reverse_folder_order_exception(self, system_controller, mock_window):
        """测试切换顺序异常处理"""
        mock_window.folder_manager.set_reverse_folder_order.side_effect = Exception("Set failed")
        
        # 不应该抛出异常
        system_controller.reverse_folder_order(None)

    def test_update_reverse_folder_order_menu_checked(self, system_controller, mock_window):
        """测试更新菜单为勾选状态"""
        mock_window.folder_manager.reverse_folder_order = True
        
        system_controller.update_reverse_folder_order_menu()
        
        mock_window.reverse_folder_order_menu_item.setState_.assert_called_with(1)

    def test_update_reverse_folder_order_menu_unchecked(self, system_controller, mock_window):
        """测试更新菜单为未勾选状态"""
        mock_window.folder_manager.reverse_folder_order = False
        
        system_controller.update_reverse_folder_order_menu()
        
        mock_window.reverse_folder_order_menu_item.setState_.assert_called_with(0)

    def test_update_reverse_folder_order_menu_no_menu_item(self, system_controller, mock_window):
        """测试没有菜单项"""
        del mock_window.reverse_folder_order_menu_item
        
        # 不应该抛出异常
        system_controller.update_reverse_folder_order_menu()

    def test_update_reverse_folder_order_menu_exception(self, system_controller, mock_window):
        """测试更新菜单异常处理"""
        mock_window.reverse_folder_order_menu_item.setState_.side_effect = Exception("Set state failed")
        
        # 不应该抛出异常
        system_controller.update_reverse_folder_order_menu()


# ==================== 清理测试 ====================


class TestCleanup:
    """测试清理功能"""

    def test_cleanup_removes_observer(self, system_controller):
        """测试清理移除通知监听"""
        with patch('plookingII.ui.controllers.system_controller.NSDistributedNotificationCenter') as mock_center_class:
            mock_center = MagicMock()
            mock_center_class.defaultCenter.return_value = mock_center
            
            system_controller.cleanup()
            
            mock_center.removeObserver_.assert_called_with(system_controller.window)

    def test_cleanup_cleans_controllers(self, system_controller, mock_window):
        """测试清理控制器"""
        system_controller.cleanup()
        
        # 验证清理了各个控制器
        mock_window.navigation_controller.cleanup.assert_called_once()
        mock_window.image_manager.cleanup.assert_called_once()
        mock_window.image_update_manager.cleanup.assert_called_once()

    def test_cleanup_no_navigation_controller(self, system_controller, mock_window):
        """测试没有navigation_controller"""
        del mock_window.navigation_controller
        
        # 不应该抛出异常
        system_controller.cleanup()

    def test_cleanup_no_image_manager(self, system_controller, mock_window):
        """测试没有image_manager"""
        del mock_window.image_manager
        
        # 不应该抛出异常
        system_controller.cleanup()

    def test_cleanup_exception_handling(self, system_controller):
        """测试清理异常处理"""
        with patch('plookingII.ui.controllers.system_controller.NSDistributedNotificationCenter') as mock_center_class:
            mock_center_class.defaultCenter.side_effect = Exception("Cleanup failed")
            
            # 不应该抛出异常
            system_controller.cleanup()


# ==================== 边缘情况测试 ====================


class TestEdgeCases:
    """测试边缘情况"""

    def test_multiple_theme_toggles(self, system_controller):
        """测试多次主题切换"""
        with patch('plookingII.ui.controllers.system_controller.NSApplication') as mock_app_class:
            with patch('plookingII.ui.controllers.system_controller.NSAppearance'):
                mock_app = MagicMock()
                mock_appearance = MagicMock()
                mock_app.appearance.return_value = mock_appearance
                mock_app_class.sharedApplication.return_value = mock_app
                
                for _ in range(10):
                    system_controller.toggle_theme(None)
                
                # 应该调用10次
                assert mock_app.setAppearance_.call_count >= 10

    def test_rapid_folder_order_changes(self, system_controller, mock_window):
        """测试快速切换文件夹顺序"""
        for _ in range(5):
            system_controller.reverse_folder_order(None)
        
        # 应该调用5次
        assert mock_window.folder_manager.set_reverse_folder_order.call_count == 5

    def test_cleanup_multiple_times(self, system_controller, mock_window):
        """测试多次清理"""
        system_controller.cleanup()
        system_controller.cleanup()
        
        # 不应该抛出异常

    def test_window_without_content_view(self, system_controller, mock_window):
        """测试window没有contentView"""
        mock_window.contentView.return_value = None
        
        with patch('plookingII.ui.controllers.system_controller.NSApplication') as mock_app_class:
            with patch('plookingII.ui.controllers.system_controller.NSAppearance'):
                mock_app = MagicMock()
                mock_app_class.sharedApplication.return_value = mock_app
                
                # 不应该抛出异常
                system_controller.handle_system_theme_changed(None)

    def test_appearance_returns_none(self, system_controller):
        """测试appearance返回None"""
        with patch('plookingII.ui.controllers.system_controller.NSApplication') as mock_app_class:
            with patch('plookingII.ui.controllers.system_controller.NSAppearance'):
                mock_app = MagicMock()
                mock_app.appearance.return_value = None
                mock_app_class.sharedApplication.return_value = mock_app
                
                # 不应该抛出异常
                system_controller.toggle_theme(None)


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    def test_complete_theme_workflow(self, mock_window):
        """测试完整主题工作流"""
        with patch('plookingII.ui.controllers.system_controller.NSDistributedNotificationCenter'):
            with patch('plookingII.ui.controllers.system_controller.NSApplication') as mock_app_class:
                with patch('plookingII.ui.controllers.system_controller.NSAppearance'):
                    mock_app = MagicMock()
                    mock_app_class.sharedApplication.return_value = mock_app
                    
                    controller = SystemController(mock_window)
                    
                    # 系统主题变化
                    controller.handle_system_theme_changed(None)
                    
                    # 手动切换主题
                    controller.toggle_theme(None)
                    
                    # 验证至少调用了两次
                    assert mock_app.setAppearance_.call_count >= 2

    def test_complete_folder_order_workflow(self, mock_window):
        """测试完整文件夹顺序工作流"""
        with patch('plookingII.ui.controllers.system_controller.NSDistributedNotificationCenter'):
            controller = SystemController(mock_window)
            
            # 切换到降序
            controller.reverse_folder_order(None)
            
            # 更新菜单
            controller.update_reverse_folder_order_menu()
            
            # 再切换回升序
            controller.reverse_folder_order(None)
            
            # 验证调用
            assert mock_window.folder_manager.set_reverse_folder_order.call_count == 2

    def test_full_lifecycle(self, mock_window):
        """测试完整生命周期"""
        with patch('plookingII.ui.controllers.system_controller.NSDistributedNotificationCenter'):
            with patch('plookingII.ui.controllers.system_controller.NSApplication'):
                with patch('plookingII.ui.controllers.system_controller.NSAppearance'):
                    controller = SystemController(mock_window)
                    
                    # 使用各种功能
                    controller.toggle_theme(None)
                    controller.reverse_folder_order(None)
                    controller.update_reverse_folder_order_menu()
                    
                    # 清理
                    controller.cleanup()
                    
                    # 验证清理被调用
                    assert mock_window.navigation_controller.cleanup.called

