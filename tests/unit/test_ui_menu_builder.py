"""
测试 ui/menu_builder.py

覆盖：各菜单构建器输出与主菜单组装。
"""

from unittest.mock import MagicMock, patch

import pytest

from plookingII.ui.menu_builder import (
    AppMenuBuilder,
    FileMenuBuilder,
    MenuBuilder,
    ToolsMenuBuilder,
)


@pytest.fixture
def window():
    win = MagicMock()
    win.recent_menu_item = None
    win.reverse_folder_order_menu_item = None
    win.folder_manager = MagicMock()
    win.folder_manager.reverse_folder_order = False
    return win


class TestMenuBuilders:
    @patch("plookingII.ui.menu_builder.NSMenuItem")
    @patch("plookingII.ui.menu_builder.NSMenu")
    @patch("plookingII.ui.menu_builder.get_ui_string")
    def test_app_menu_builder(self, mock_ui, mock_menu, mock_item, window):
        """应用菜单包含关于/隐藏/最小化/退出"""
        mock_ui.side_effect = lambda *args, **kwargs: args[-1]
        # 让 initWithTitle_... 返回与 init() 相同的对象，便于断言 setTarget_
        mock_item.alloc.return_value.initWithTitle_action_keyEquivalent_.return_value = (
            mock_item.alloc.return_value.init.return_value
        )
        builder = AppMenuBuilder(MagicMock(), window)

        item = builder.build_app_menu()

        assert item.setSubmenu_.called
        assert mock_item.alloc.return_value.init.return_value.setTarget_.call_count >= 4

    @patch("plookingII.ui.menu_builder.NSMenuItem")
    @patch("plookingII.ui.menu_builder.NSMenu")
    @patch("plookingII.ui.menu_builder.get_ui_string")
    def test_file_menu_builder_saves_recent_item(self, mock_ui, mock_menu, mock_item, window):
        """文件菜单保存最近打开子菜单引用"""
        mock_ui.side_effect = lambda *args, **kwargs: args[-1]
        builder = FileMenuBuilder(window)

        builder.build_file_menu()

        assert window.recent_menu_item is not None

    @patch("plookingII.ui.menu_builder.NSMenuItem")
    @patch("plookingII.ui.menu_builder.NSMenu")
    @patch("plookingII.ui.menu_builder.get_ui_string")
    def test_tools_menu_builder_sets_reverse_state(self, mock_ui, mock_menu, mock_item, window):
        """工具菜单保存倒序浏览菜单项并同步初始状态"""
        mock_ui.side_effect = lambda *args, **kwargs: args[-1]
        builder = ToolsMenuBuilder(window)

        builder.build_tools_menu()

        assert window.reverse_folder_order_menu_item is not None
        window.reverse_folder_order_menu_item.setState_.assert_called()

    @patch("plookingII.ui.menu_builder.NSMenuItem")
    @patch("plookingII.ui.menu_builder.NSMenu")
    @patch("plookingII.ui.menu_builder.get_ui_string")
    def test_build_menu_assembles_all_sections(self, mock_ui, mock_menu, mock_item, window):
        """主菜单组装 7 个一级菜单"""
        mock_ui.side_effect = lambda *args, **kwargs: args[-1]
        builder = MenuBuilder(MagicMock(), window)

        menu = builder.build_menu()

        assert menu is mock_menu.alloc.return_value.init.return_value
        assert menu.addItem_.call_count == 7
        assert window.recent_menu_item is not None

    @patch("plookingII.ui.menu_builder.NSMenuItem")
    @patch("plookingII.ui.menu_builder.NSMenu")
    @patch("plookingII.ui.menu_builder.get_ui_string")
    def test_build_menu_failure_returns_fallback_menu(self, mock_ui, mock_menu, mock_item, window):
        """构建失败时返回空菜单兜底"""
        mock_ui.side_effect = lambda *args, **kwargs: args[-1]
        mock_menu.alloc.return_value.init.return_value.addItem_.side_effect = Exception("menu failed")
        builder = MenuBuilder(MagicMock(), window)

        menu = builder.build_menu()

        assert menu is not None
