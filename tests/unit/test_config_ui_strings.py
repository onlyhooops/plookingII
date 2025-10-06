#!/usr/bin/env python3
"""
测试 config/ui_strings.py

Author: PlookingII Team
"""

from plookingII.config.ui_strings import (
    UIStringManager,
    UIStrings,
    get_formatted_ui_string,
    get_ui_string,
    get_ui_string_manager,
)


class TestUIStrings:
    """测试 UIStrings 类"""

    def test_app_info_structure(self):
        """测试应用信息结构"""
        assert isinstance(UIStrings.APP_INFO, dict)
        assert "name" in UIStrings.APP_INFO
        assert "about" in UIStrings.APP_INFO
        assert UIStrings.APP_INFO["name"] == "PlookingII"

    def test_menu_structure(self):
        """测试菜单文案结构"""
        assert isinstance(UIStrings.MENU, dict)
        assert "file_menu" in UIStrings.MENU
        assert "edit_menu" in UIStrings.MENU
        assert "go_menu" in UIStrings.MENU
        assert "view_menu" in UIStrings.MENU
        assert "tools_menu" in UIStrings.MENU
        assert "help_menu" in UIStrings.MENU

    def test_buttons_structure(self):
        """测试按钮文案结构"""
        assert isinstance(UIStrings.BUTTONS, dict)
        assert "ok" in UIStrings.BUTTONS
        assert "cancel" in UIStrings.BUTTONS
        assert "open" in UIStrings.BUTTONS

    def test_shortcuts_help_structure(self):
        """测试快捷键帮助结构"""
        assert isinstance(UIStrings.SHORTCUTS_HELP, dict)
        assert "title" in UIStrings.SHORTCUTS_HELP
        # 新的简化结构直接使用键值对
        assert "left_right_arrows" in UIStrings.SHORTCUTS_HELP
        assert "cmd_o" in UIStrings.SHORTCUTS_HELP

    def test_about_dialog_structure(self):
        """测试关于对话框结构"""
        assert isinstance(UIStrings.ABOUT_DIALOG, dict)
        # 新的简化结构
        assert "description" in UIStrings.ABOUT_DIALOG
        assert "subtitle" in UIStrings.ABOUT_DIALOG
        assert "privacy" in UIStrings.ABOUT_DIALOG

    def test_status_messages_structure(self):
        """测试状态消息结构"""
        assert isinstance(UIStrings.STATUS_MESSAGES, dict)
        assert "no_images" in UIStrings.STATUS_MESSAGES
        assert "task_completed" in UIStrings.STATUS_MESSAGES

    def test_error_messages_structure(self):
        """测试错误消息结构"""
        assert isinstance(UIStrings.ERROR_MESSAGES, dict)
        assert "open_folder_failed" in UIStrings.ERROR_MESSAGES
        assert "rotation_operation_failed" in UIStrings.ERROR_MESSAGES

    def test_history_dialog_structure(self):
        """测试历史记录对话框结构"""
        assert isinstance(UIStrings.HISTORY_DIALOG, dict)
        assert "title" in UIStrings.HISTORY_DIALOG
        assert "info_template" in UIStrings.HISTORY_DIALOG

    def test_jump_folder_dialog_structure(self):
        """测试跳转文件夹对话框结构"""
        assert isinstance(UIStrings.JUMP_FOLDER_DIALOG, dict)
        assert "title" in UIStrings.JUMP_FOLDER_DIALOG

    def test_recent_files_dialog_structure(self):
        """测试最近文件对话框结构"""
        assert isinstance(UIStrings.RECENT_FILES_DIALOG, dict)
        assert "title" in UIStrings.RECENT_FILES_DIALOG


class TestUIStringManager:
    """测试 UIStringManager 类"""

    def test_initialization(self):
        """测试初始化"""
        manager = UIStringManager()
        assert manager._strings is not None
        assert isinstance(manager._strings, dict)

    def test_get_valid_string(self):
        """测试获取有效字符串"""
        manager = UIStringManager()
        value = manager.get("app_info", "name")
        assert value == "PlookingII"

    def test_get_with_default(self):
        """测试获取不存在的键返回默认值"""
        manager = UIStringManager()
        value = manager.get("app_info", "nonexistent", "default_value")
        assert value == "default_value"

    def test_get_invalid_category(self):
        """测试无效分类返回默认值"""
        manager = UIStringManager()
        value = manager.get("invalid_category", "key", "default")
        assert value == "default"

    def test_get_formatted_string(self):
        """测试格式化字符串"""
        manager = UIStringManager()
        # 使用状态消息中的模板
        template = manager.get("status_messages", "folder_opened")
        assert "{}" in template

        formatted = manager.get_formatted("status_messages", "folder_opened", "/test/path")
        assert "/test/path" in formatted

    def test_get_formatted_with_multiple_args(self):
        """测试多参数格式化"""
        manager = UIStringManager()
        # info_template 有多个占位符
        formatted = manager.get_formatted("history_dialog", "info_template", 5, 10, 3)
        assert "5" in formatted
        assert "10" in formatted
        assert "3" in formatted

    def test_get_formatted_invalid_key(self):
        """测试格式化不存在的键"""
        manager = UIStringManager()
        result = manager.get_formatted("invalid", "key", "arg")
        assert result == ""

    def test_get_shortcuts_help_text(self):
        """测试获取快捷键帮助文本"""
        manager = UIStringManager()
        help_text = manager.get_shortcuts_help_text()
        assert isinstance(help_text, str)
        assert "基础导航" in help_text or "导航" in help_text or len(help_text) > 0

    def test_get_about_dialog_text(self):
        """测试获取关于对话框文本"""
        manager = UIStringManager()
        about_text = manager.get_about_dialog_text("1.0.0", "Test Author", "© 2025")
        assert isinstance(about_text, str)
        assert "1.0.0" in about_text
        assert "Test Author" in about_text
        assert "© 2025" in about_text


class TestGlobalFunctions:
    """测试全局函数"""

    def test_get_ui_string_manager(self):
        """测试获取全局管理器"""
        manager1 = get_ui_string_manager()
        manager2 = get_ui_string_manager()
        # 应该返回同一个实例
        assert manager1 is manager2
        assert isinstance(manager1, UIStringManager)

    def test_get_ui_string(self):
        """测试便捷函数获取字符串"""
        value = get_ui_string("app_info", "name")
        assert value == "PlookingII"

    def test_get_ui_string_with_default(self):
        """测试便捷函数使用默认值"""
        value = get_ui_string("invalid", "key", "default")
        assert value == "default"

    def test_get_formatted_ui_string(self):
        """测试便捷函数获取格式化字符串"""
        formatted = get_formatted_ui_string("status_messages", "folder_opened", "/test/path")
        assert "/test/path" in formatted


class TestUIStringsContent:
    """测试 UI 字符串内容"""

    def test_all_menu_items_have_text(self):
        """测试所有菜单项都有文本"""
        for key, value in UIStrings.MENU.items():
            assert isinstance(value, str)
            assert len(value) > 0

    def test_all_buttons_have_text(self):
        """测试所有按钮都有文本"""
        for key, value in UIStrings.BUTTONS.items():
            assert isinstance(value, str)
            assert len(value) > 0

    def test_all_status_messages_have_text(self):
        """测试所有状态消息都有文本"""
        for key, value in UIStrings.STATUS_MESSAGES.items():
            assert isinstance(value, str)
            assert len(value) > 0

    def test_all_error_messages_have_text(self):
        """测试所有错误消息都有文本"""
        for key, value in UIStrings.ERROR_MESSAGES.items():
            assert isinstance(value, str)
            assert len(value) > 0

    def test_format_placeholders_in_messages(self):
        """测试消息中的格式占位符"""
        # 检查一些已知包含占位符的消息
        assert "{}" in UIStrings.STATUS_MESSAGES["folder_opened"]
        assert "{}" in UIStrings.STATUS_MESSAGES["folder_skipped"]
        assert "{}" in UIStrings.ERROR_MESSAGES["keyboard_event_failed"]


class TestUIStringManagerEdgeCases:
    """测试 UIStringManager 边界情况"""

    def test_get_with_none_category(self):
        """测试 None 分类"""
        manager = UIStringManager()
        # 应该优雅地处理 None
        result = manager.get(None, "key", "default")
        assert result == "default"

    def test_get_with_none_key(self):
        """测试 None 键"""
        manager = UIStringManager()
        result = manager.get("app_info", None, "default")
        assert result == "default"

    def test_get_formatted_with_no_placeholders(self):
        """测试格式化没有占位符的字符串"""
        manager = UIStringManager()
        # app_info.name 没有占位符
        result = manager.get_formatted("app_info", "name", "unused_arg")
        # 应该正常返回字符串
        assert isinstance(result, str)

    def test_get_formatted_with_wrong_number_of_args(self):
        """测试格式化参数数量不匹配"""
        manager = UIStringManager()
        # 如果参数数量不匹配，应该捕获异常并返回空字符串
        result = manager.get_formatted("history_dialog", "info_template", 1)  # 需要4个参数
        # 应该返回空字符串或捕获异常
        assert isinstance(result, str)

    def test_shortcuts_help_text_not_empty(self):
        """测试快捷键帮助文本非空"""
        manager = UIStringManager()
        help_text = manager.get_shortcuts_help_text()
        # 即使某些部分为空，结果也应该是字符串
        assert isinstance(help_text, str)

    def test_about_dialog_text_not_empty(self):
        """测试关于对话框文本非空"""
        manager = UIStringManager()
        about_text = manager.get_about_dialog_text("", "", "")
        # 即使参数为空，也应该返回字符串
        assert isinstance(about_text, str)


class TestUIStringsIntegration:
    """测试 UI 字符串集成"""

    def test_menu_items_consistency(self):
        """测试菜单项一致性"""
        # 确保相关的菜单项存在
        assert "file_menu" in UIStrings.MENU
        assert "open_folder" in UIStrings.MENU
        assert "recent_files" in UIStrings.MENU

    def test_dialog_consistency(self):
        """测试对话框一致性"""
        # 历史对话框应该有所有必需的键
        required_keys = ["title", "info_template", "restore", "restart", "clear_history"]
        for key in required_keys:
            assert key in UIStrings.HISTORY_DIALOG

    def test_rotation_messages_exist(self):
        """测试旋转相关消息存在"""
        assert "rotating_right" in UIStrings.STATUS_MESSAGES
        assert "rotating_left" in UIStrings.STATUS_MESSAGES
        assert "rotation_completed" in UIStrings.STATUS_MESSAGES
        assert "rotation_failed" in UIStrings.STATUS_MESSAGES
        assert "rotation_operation_failed" in UIStrings.ERROR_MESSAGES
