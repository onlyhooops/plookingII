"""
测试 ui/controllers/menu_controller.py

测试菜单控制器功能，包括：
- 对话框（关于、快捷键）
- 最近文件菜单构建和更新
- 最近文件操作（打开、清空）
"""

from unittest.mock import MagicMock, Mock, patch, call
import os

import pytest

from plookingII.ui.controllers.menu_controller import MenuController


# ==================== 夹具（Fixtures） ====================


@pytest.fixture
def mock_window():
    """创建模拟窗口"""
    window = MagicMock()
    window.root_folder = "/test/folder"
    window.folder_manager = MagicMock()
    window.operation_manager = MagicMock()
    window.status_bar_controller = MagicMock()
    window.recent_menu_item = MagicMock()
    return window


@pytest.fixture
def menu_controller(mock_window):
    """创建菜单控制器实例"""
    return MenuController(mock_window)


# ==================== 初始化测试 ====================


class TestMenuControllerInit:
    """测试MenuController初始化"""

    def test_init_basic(self, mock_window):
        """测试基本初始化"""
        controller = MenuController(mock_window)
        
        assert controller.window == mock_window

    def test_init_with_none(self):
        """测试None窗口初始化"""
        controller = MenuController(None)
        
        assert controller.window is None


# ==================== 对话框测试 ====================


class TestDialogs:
    """测试对话框显示"""

    @patch('plookingII.ui.controllers.menu_controller.NSAlert')
    @patch('plookingII.ui.controllers.menu_controller.get_ui_string_manager')
    def test_show_about_basic(self, mock_ui_strings, mock_ns_alert, menu_controller):
        """测试显示关于对话框"""
        # 设置模拟对象
        mock_alert = MagicMock()
        mock_ns_alert.alloc.return_value.init.return_value = mock_alert
        
        mock_ui_manager = MagicMock()
        mock_ui_manager.get_about_dialog_text.return_value = "Version 1.0\nAuthor: Test\nCopyright 2024"
        mock_ui_manager.get.return_value = "确定"
        mock_ui_strings.return_value = mock_ui_manager
        
        # 调用方法
        menu_controller.show_about(None)
        
        # 验证
        mock_alert.setMessageText_.assert_called()
        mock_alert.setInformativeText_.assert_called_once()
        mock_alert.addButtonWithTitle_.assert_called_once_with("确定")

    @patch('plookingII.ui.controllers.menu_controller.NSAlert')
    @patch('plookingII.ui.controllers.menu_controller.get_ui_string_manager')
    def test_show_about_sheet_mode(self, mock_ui_strings, mock_ns_alert, menu_controller):
        """测试关于对话框使用sheet模式"""
        mock_alert = MagicMock()
        mock_ns_alert.alloc.return_value.init.return_value = mock_alert
        
        mock_ui_manager = MagicMock()
        mock_ui_manager.get_about_dialog_text.return_value = "About text"
        mock_ui_manager.get.return_value = "OK"
        mock_ui_strings.return_value = mock_ui_manager
        
        # 调用方法
        menu_controller.show_about(None)
        
        # 验证优先使用sheet模式
        mock_alert.beginSheetModalForWindow_completionHandler_.assert_called_once()

    @patch('plookingII.ui.controllers.menu_controller.NSAlert')
    @patch('plookingII.ui.controllers.menu_controller.get_ui_string_manager')
    def test_show_about_fallback_modal(self, mock_ui_strings, mock_ns_alert, menu_controller):
        """测试关于对话框回退到modal模式"""
        mock_alert = MagicMock()
        mock_alert.beginSheetModalForWindow_completionHandler_.side_effect = Exception("Sheet failed")
        mock_ns_alert.alloc.return_value.init.return_value = mock_alert
        
        mock_ui_manager = MagicMock()
        mock_ui_manager.get_about_dialog_text.return_value = "About text"
        mock_ui_manager.get.return_value = "OK"
        mock_ui_strings.return_value = mock_ui_manager
        
        # 调用方法
        menu_controller.show_about(None)
        
        # 验证回退到runModal
        mock_alert.runModal.assert_called_once()

    @patch('plookingII.ui.controllers.menu_controller.NSAlert')
    @patch('plookingII.ui.controllers.menu_controller.get_ui_string_manager')
    def test_show_shortcuts_basic(self, mock_ui_strings, mock_ns_alert, menu_controller):
        """测试显示快捷键对话框"""
        mock_alert = MagicMock()
        mock_ns_alert.alloc.return_value.init.return_value = mock_alert
        
        mock_ui_manager = MagicMock()
        mock_ui_manager.get_shortcuts_help_text.return_value = "Shortcuts help"
        mock_ui_manager.get.return_value = "确定"
        mock_ui_strings.return_value = mock_ui_manager
        
        # 调用方法
        menu_controller.show_shortcuts(None)
        
        # 验证
        mock_alert.setMessageText_.assert_called()
        mock_alert.setInformativeText_.assert_called_once()
        mock_alert.addButtonWithTitle_.assert_called_once_with("确定")

    @patch('plookingII.ui.controllers.menu_controller.NSAlert')
    @patch('plookingII.ui.controllers.menu_controller.get_ui_string_manager')
    def test_show_shortcuts_exception(self, mock_ui_strings, mock_ns_alert, menu_controller):
        """测试快捷键对话框异常处理"""
        mock_ns_alert.alloc.side_effect = Exception("NSAlert failed")
        mock_ui_strings.return_value = MagicMock()
        
        # 应该不抛出异常
        try:
            menu_controller.show_shortcuts(None)
        except Exception:
            pytest.fail("show_shortcuts应该捕获异常")


# ==================== 最近文件菜单构建测试 ====================


class TestBuildRecentMenu:
    """测试最近文件菜单构建"""

    @patch('plookingII.ui.controllers.menu_controller.NSMenuItem')
    @patch('plookingII.ui.controllers.menu_controller.NSMenu')
    @patch('plookingII.ui.controllers.menu_controller.os.path.exists')
    @patch('plookingII.ui.controllers.menu_controller.os.path.isdir')
    def test_build_recent_menu_basic(self, mock_isdir, mock_exists, mock_ns_menu, 
                                     mock_ns_menu_item, menu_controller):
        """测试基本菜单构建"""
        # 设置模拟
        mock_menu = MagicMock()
        mock_ns_menu.alloc.return_value.initWithTitle_.return_value = mock_menu
        
        mock_menu_item = MagicMock()
        mock_ns_menu_item.alloc.return_value.initWithTitle_action_keyEquivalent_.return_value = mock_menu_item
        mock_ns_menu_item.separatorItem.return_value = MagicMock()
        
        mock_exists.return_value = True
        mock_isdir.return_value = True
        
        menu_controller.window.folder_manager.get_recent_folders.return_value = [
            "/test/folder1",
            "/test/folder2"
        ]
        
        # 调用
        result = menu_controller.build_recent_menu(None)
        
        # 验证
        assert result == mock_menu
        assert mock_menu.addItem_.call_count >= 2  # 至少添加了清空和分隔符

    @patch('plookingII.ui.controllers.menu_controller.NSMenuItem')
    @patch('plookingII.ui.controllers.menu_controller.NSMenu')
    def test_build_recent_menu_empty_list(self, mock_ns_menu, mock_ns_menu_item, menu_controller):
        """测试空列表"""
        mock_menu = MagicMock()
        mock_ns_menu.alloc.return_value.initWithTitle_.return_value = mock_menu
        
        menu_controller.window.folder_manager.get_recent_folders.return_value = []
        
        result = menu_controller.build_recent_menu(None)
        
        assert result == mock_menu

    @patch('plookingII.ui.controllers.menu_controller.NSWorkspace')
    @patch('plookingII.ui.controllers.menu_controller.NSMenuItem')
    @patch('plookingII.ui.controllers.menu_controller.NSMenu')
    @patch('plookingII.ui.controllers.menu_controller.os.path.exists')
    @patch('plookingII.ui.controllers.menu_controller.os.path.isdir')
    @patch('plookingII.ui.controllers.menu_controller.os.path.basename')
    def test_build_recent_menu_with_icons(self, mock_basename, mock_isdir, mock_exists, 
                                          mock_ns_menu, mock_ns_menu_item, mock_workspace, 
                                          menu_controller):
        """测试带图标的菜单构建"""
        mock_menu = MagicMock()
        mock_ns_menu.alloc.return_value.initWithTitle_.return_value = mock_menu
        
        mock_menu_item = MagicMock()
        mock_ns_menu_item.alloc.return_value.initWithTitle_action_keyEquivalent_.return_value = mock_menu_item
        mock_ns_menu_item.separatorItem.return_value = MagicMock()
        
        mock_icon = MagicMock()
        mock_workspace.sharedWorkspace.return_value.iconForFile_.return_value = mock_icon
        
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_basename.side_effect = lambda x: x.split('/')[-1]
        
        menu_controller.window.folder_manager.get_recent_folders.return_value = ["/test/folder1"]
        
        result = menu_controller.build_recent_menu(None)
        
        # 验证图标设置
        mock_icon.setSize_.assert_called()

    @patch('plookingII.ui.controllers.menu_controller.NSMenuItem')
    @patch('plookingII.ui.controllers.menu_controller.NSMenu')
    @patch('plookingII.ui.controllers.menu_controller.os.path.exists')
    @patch('plookingII.ui.controllers.menu_controller.os.path.isdir')
    @patch('plookingII.ui.controllers.menu_controller.os.path.basename')
    def test_build_recent_menu_skip_invalid_paths(self, mock_basename, mock_isdir, mock_exists,
                                                   mock_ns_menu, mock_ns_menu_item, menu_controller):
        """测试跳过无效路径"""
        mock_menu = MagicMock()
        mock_ns_menu.alloc.return_value.initWithTitle_.return_value = mock_menu
        mock_ns_menu_item.alloc.return_value.initWithTitle_action_keyEquivalent_.return_value = MagicMock()
        mock_ns_menu_item.separatorItem.return_value = MagicMock()
        
        # 第一个路径不存在，第二个不是目录
        mock_exists.side_effect = [False, True]
        mock_isdir.side_effect = [False]
        mock_basename.return_value = "folder"
        
        menu_controller.window.folder_manager.get_recent_folders.return_value = [
            "/nonexistent/path",
            "/not/a/directory"
        ]
        
        result = menu_controller.build_recent_menu(None)
        
        # 只应该添加清空项和分隔符，没有文件项
        assert result == mock_menu

    @patch('plookingII.ui.controllers.menu_controller.NSMenuItem')
    @patch('plookingII.ui.controllers.menu_controller.NSMenu')
    @patch('plookingII.ui.controllers.menu_controller.os.path.exists')
    @patch('plookingII.ui.controllers.menu_controller.os.path.isdir')
    @patch('plookingII.ui.controllers.menu_controller.os.path.basename')
    def test_build_recent_menu_skip_selection_folders(self, mock_basename, mock_isdir, mock_exists,
                                                      mock_ns_menu, mock_ns_menu_item, menu_controller):
        """测试跳过精选文件夹"""
        mock_menu = MagicMock()
        mock_ns_menu.alloc.return_value.initWithTitle_.return_value = mock_menu
        mock_ns_menu_item.alloc.return_value.initWithTitle_action_keyEquivalent_.return_value = MagicMock()
        mock_ns_menu_item.separatorItem.return_value = MagicMock()
        
        mock_exists.return_value = True
        mock_isdir.return_value = True
        # 使用lambda返回路径的最后部分
        mock_basename.side_effect = lambda x: x.split('/')[-1].rstrip(os.sep)
        
        menu_controller.window.folder_manager.get_recent_folders.return_value = [
            "/test/测试 精选",
            "/test/精选",
            "/test/正常文件夹"
        ]
        
        result = menu_controller.build_recent_menu(None)
        
        # 只应该添加一个正常文件夹项
        assert result == mock_menu

    @patch('plookingII.ui.controllers.menu_controller.NSMenu')
    def test_build_recent_menu_exception(self, mock_ns_menu, menu_controller):
        """测试异常处理"""
        mock_ns_menu.alloc.return_value.initWithTitle_.side_effect = [
            Exception("Build failed"),
            MagicMock()  # 第二次调用（异常处理的fallback）
        ]
        
        result = menu_controller.build_recent_menu(None)
        
        # 应该返回空菜单
        assert result is not None


# ==================== 菜单更新测试 ====================


class TestUpdateRecentMenu:
    """测试菜单更新"""

    @patch.object(MenuController, 'build_recent_menu')
    def test_update_recent_menu_success(self, mock_build, menu_controller):
        """测试成功更新菜单"""
        mock_new_menu = MagicMock()
        mock_build.return_value = mock_new_menu
        
        menu_controller.update_recent_menu()
        
        menu_controller.window.recent_menu_item.setSubmenu_.assert_called_once_with(mock_new_menu)

    def test_update_recent_menu_no_menu_item(self, menu_controller):
        """测试没有menu_item时不更新"""
        del menu_controller.window.recent_menu_item
        
        # 应该不抛出异常
        try:
            menu_controller.update_recent_menu()
        except Exception:
            pytest.fail("update_recent_menu应该处理missing attribute")

    @patch.object(MenuController, 'build_recent_menu')
    def test_update_recent_menu_exception(self, mock_build, menu_controller):
        """测试更新异常"""
        mock_build.side_effect = Exception("Build failed")
        
        # 应该不抛出异常
        try:
            menu_controller.update_recent_menu()
        except Exception:
            pytest.fail("update_recent_menu应该捕获异常")


# ==================== 初始化菜单测试 ====================


class TestInitializeRecentMenu:
    """测试初始化最近菜单"""

    @patch.object(MenuController, 'update_recent_menu')
    def test_initialize_recent_menu_success(self, mock_update, menu_controller):
        """测试成功初始化"""
        mock_timer = MagicMock()
        
        menu_controller.initialize_recent_menu(mock_timer)
        
        mock_update.assert_called_once()

    @patch('plookingII.ui.controllers.menu_controller.NSTimer')
    @patch.object(MenuController, 'update_recent_menu')
    def test_initialize_recent_menu_retry(self, mock_update, mock_ns_timer, menu_controller):
        """测试延迟重试"""
        menu_controller.window.recent_menu_item = None
        mock_timer = MagicMock()
        
        menu_controller.initialize_recent_menu(mock_timer)
        
        # 应该调度延迟重试
        mock_ns_timer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_.assert_called_once()

    @patch.object(MenuController, 'update_recent_menu')
    def test_initialize_recent_menu_exception(self, mock_update, menu_controller):
        """测试异常处理"""
        mock_update.side_effect = Exception("Update failed")
        mock_timer = MagicMock()
        
        # 应该不抛出异常
        try:
            menu_controller.initialize_recent_menu(mock_timer)
        except Exception:
            pytest.fail("initialize_recent_menu应该捕获异常")


# ==================== 最近文件操作测试 ====================


class TestRecentFileOperations:
    """测试最近文件操作"""

    @patch.object(MenuController, 'clear_recent_files')
    def test_show_recent_files_clear(self, mock_clear, menu_controller):
        """测试通过show_recent_files清空"""
        mock_sender = MagicMock()
        mock_sender.title.return_value = "清空最近记录"
        
        menu_controller.show_recent_files(mock_sender)
        
        mock_clear.assert_called_once_with(mock_sender)

    def test_show_recent_files_no_action(self, menu_controller):
        """测试没有操作"""
        mock_sender = MagicMock()
        mock_sender.title.return_value = "其他"
        
        # 应该不抛出异常
        try:
            menu_controller.show_recent_files(mock_sender)
        except Exception:
            pytest.fail("show_recent_files应该处理其他标题")

    @patch('plookingII.ui.controllers.menu_controller.os.path.exists')
    @patch('plookingII.ui.controllers.menu_controller.os.path.isdir')
    @patch.object(MenuController, '_folder_contains_images')
    @patch.object(MenuController, 'update_recent_menu')
    def test_open_recent_file_success(self, mock_update, mock_contains, mock_isdir, 
                                      mock_exists, menu_controller):
        """测试成功打开最近文件"""
        mock_sender = MagicMock()
        mock_sender.representedObject.return_value = "/test/folder"
        
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_contains.return_value = True
        
        menu_controller.open_recent_file(mock_sender)
        
        menu_controller.window.operation_manager._save_last_dir.assert_called_once_with("/test/folder")
        menu_controller.window.folder_manager.add_recent_folder.assert_called_once_with("/test/folder")
        menu_controller.window.folder_manager.load_images_from_root.assert_called_once_with("/test/folder")
        mock_update.assert_called_once()

    @patch('plookingII.ui.controllers.menu_controller.os.path.exists')
    @patch('plookingII.ui.controllers.menu_controller.os.path.basename')
    def test_open_recent_file_not_exists(self, mock_basename, mock_exists, menu_controller):
        """测试路径不存在"""
        mock_sender = MagicMock()
        mock_sender.representedObject.return_value = "/nonexistent/folder"
        
        mock_exists.return_value = False
        mock_basename.return_value = "folder"
        
        menu_controller.open_recent_file(mock_sender)
        
        menu_controller.window.status_bar_controller.set_status_message.assert_called_once()

    @patch('plookingII.ui.controllers.menu_controller.os.path.exists')
    @patch('plookingII.ui.controllers.menu_controller.os.path.isdir')
    @patch('plookingII.ui.controllers.menu_controller.os.path.basename')
    def test_open_recent_file_not_dir(self, mock_basename, mock_isdir, mock_exists, menu_controller):
        """测试路径不是文件夹"""
        mock_sender = MagicMock()
        mock_sender.representedObject.return_value = "/test/file.txt"
        
        mock_exists.return_value = True
        mock_isdir.return_value = False
        mock_basename.return_value = "file.txt"
        
        menu_controller.open_recent_file(mock_sender)
        
        menu_controller.window.status_bar_controller.set_status_message.assert_called_once()

    @patch('plookingII.ui.controllers.menu_controller.os.path.exists')
    @patch('plookingII.ui.controllers.menu_controller.os.path.isdir')
    @patch('plookingII.ui.controllers.menu_controller.os.path.basename')
    @patch.object(MenuController, '_folder_contains_images')
    def test_open_recent_file_no_images(self, mock_contains, mock_basename, mock_isdir, 
                                       mock_exists, menu_controller):
        """测试文件夹不包含图片"""
        mock_sender = MagicMock()
        mock_sender.representedObject.return_value = "/test/empty"
        
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_contains.return_value = False
        mock_basename.return_value = "empty"
        
        menu_controller.open_recent_file(mock_sender)
        
        menu_controller.window.status_bar_controller.set_status_message.assert_called_once()

    def test_open_recent_file_exception(self, menu_controller):
        """测试异常处理"""
        mock_sender = MagicMock()
        mock_sender.representedObject.side_effect = Exception("Failed")
        
        # 应该不抛出异常
        try:
            menu_controller.open_recent_file(mock_sender)
        except Exception:
            pytest.fail("open_recent_file应该捕获异常")

    @patch.object(MenuController, 'update_recent_menu')
    def test_clear_recent_files_success(self, mock_update, menu_controller):
        """测试成功清空"""
        menu_controller.clear_recent_files(None)
        
        menu_controller.window.folder_manager.clear_recent_folders.assert_called_once()
        mock_update.assert_called_once()
        menu_controller.window.status_bar_controller.set_status_message.assert_called_once()

    @patch.object(MenuController, 'update_recent_menu')
    def test_clear_recent_files_exception(self, mock_update, menu_controller):
        """测试清空异常"""
        menu_controller.window.folder_manager.clear_recent_folders.side_effect = Exception("Clear failed")
        
        # 应该不抛出异常
        try:
            menu_controller.clear_recent_files(None)
        except Exception:
            pytest.fail("clear_recent_files应该捕获异常")


# ==================== 辅助方法测试 ====================


class TestHelperMethods:
    """测试辅助方法"""

    @patch('plookingII.ui.controllers.menu_controller.FileUtils')
    def test_folder_contains_images_true(self, mock_file_utils, menu_controller):
        """测试文件夹包含图片"""
        mock_file_utils.folder_contains_images.return_value = True
        
        result = menu_controller._folder_contains_images("/test/folder")
        
        assert result is True
        mock_file_utils.folder_contains_images.assert_called_once_with("/test/folder", recursive_depth=1)

    @patch('plookingII.ui.controllers.menu_controller.FileUtils')
    def test_folder_contains_images_false(self, mock_file_utils, menu_controller):
        """测试文件夹不包含图片"""
        mock_file_utils.folder_contains_images.return_value = False
        
        result = menu_controller._folder_contains_images("/test/empty")
        
        assert result is False

    @patch('plookingII.ui.controllers.menu_controller.FileUtils')
    def test_folder_contains_images_exception(self, mock_file_utils, menu_controller):
        """测试异常返回False"""
        mock_file_utils.folder_contains_images.side_effect = Exception("Check failed")
        
        result = menu_controller._folder_contains_images("/test/folder")
        
        assert result is False


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    @patch('plookingII.ui.controllers.menu_controller.NSAlert')
    @patch('plookingII.ui.controllers.menu_controller.get_ui_string_manager')
    def test_dialog_workflow(self, mock_ui_strings, mock_ns_alert, menu_controller):
        """测试对话框完整工作流"""
        mock_alert = MagicMock()
        mock_ns_alert.alloc.return_value.init.return_value = mock_alert
        
        mock_ui_manager = MagicMock()
        mock_ui_manager.get_about_dialog_text.return_value = "About"
        mock_ui_manager.get_shortcuts_help_text.return_value = "Shortcuts"
        mock_ui_manager.get.return_value = "确定"
        mock_ui_strings.return_value = mock_ui_manager
        
        # 显示两个对话框
        menu_controller.show_about(None)
        menu_controller.show_shortcuts(None)
        
        # 验证两次对话框创建
        assert mock_ns_alert.alloc.return_value.init.call_count == 2

    @patch('plookingII.ui.controllers.menu_controller.NSMenuItem')
    @patch('plookingII.ui.controllers.menu_controller.NSMenu')
    @patch('plookingII.ui.controllers.menu_controller.os.path.exists')
    @patch('plookingII.ui.controllers.menu_controller.os.path.isdir')
    @patch.object(MenuController, '_folder_contains_images')
    @patch.object(MenuController, 'update_recent_menu')
    def test_menu_build_and_open(self, mock_update, mock_contains, mock_isdir, 
                                 mock_exists, mock_ns_menu, mock_ns_menu_item, 
                                 menu_controller):
        """测试菜单构建和打开工作流"""
        mock_menu = MagicMock()
        mock_ns_menu.alloc.return_value.initWithTitle_.return_value = mock_menu
        
        mock_item = MagicMock()
        mock_ns_menu_item.alloc.return_value.initWithTitle_action_keyEquivalent_.return_value = mock_item
        mock_ns_menu_item.separatorItem.return_value = MagicMock()
        
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_contains.return_value = True
        
        menu_controller.window.folder_manager.get_recent_folders.return_value = ["/test/folder"]
        
        # 构建菜单
        menu = menu_controller.build_recent_menu(None)
        assert menu is not None
        
        # 模拟打开
        mock_sender = MagicMock()
        mock_sender.representedObject.return_value = "/test/folder"
        menu_controller.open_recent_file(mock_sender)
        
        # 验证调用
        menu_controller.window.folder_manager.load_images_from_root.assert_called_once()

