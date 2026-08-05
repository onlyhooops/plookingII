"""
测试 ui/utils/user_feedback.py

覆盖：错误消息映射、恢复建议、弹窗展示与便捷函数。
"""

from unittest.mock import patch

import pytest

from plookingII.core.error_handling import (
    DragDropError,
    ErrorSeverity,
    ImageProcessingError,
    PlookingIIError,
)
from plookingII.ui.utils.user_feedback import UserFeedbackManager, show_info, show_warning


@pytest.fixture
def manager():
    return UserFeedbackManager()


class TestUserFeedbackManager:
    @pytest.fixture(autouse=True)
    def _no_real_activation(self):
        """避免测试期间真实激活应用（抢焦点）"""
        with patch("plookingII.ui.utils.alert_utils.NSApplication"):
            yield

    def test_user_friendly_message_mapping(self, manager):
        """自定义错误与系统错误的友好文案映射"""
        assert manager._get_user_friendly_message(DragDropError("x")) == "拖拽操作遇到问题"
        assert manager._get_user_friendly_message(FileNotFoundError("x")) == "找不到指定的文件或文件夹"
        assert manager._get_user_friendly_message(PermissionError("x")) == "没有权限访问该文件或文件夹"
        assert manager._get_user_friendly_message(OSError("x")) == "系统操作失败"
        assert manager._get_user_friendly_message(ValueError("x")) == "数据格式错误"
        assert manager._get_user_friendly_message(TypeError("x")) == "操作参数错误"
        assert manager._get_user_friendly_message(Exception("x")) == "发生了未知错误"

    def test_recovery_suggestion_mapping(self, manager):
        """恢复建议映射"""
        assert manager._get_recovery_suggestion(DragDropError("x")) == "请尝试重新拖拽文件夹，或使用菜单选择文件夹"
        assert manager._get_recovery_suggestion(FileNotFoundError("x")) == "请检查文件路径和访问权限"
        assert manager._get_recovery_suggestion(OSError("x")) == "请重试操作，或联系技术支持"
        assert manager._get_recovery_suggestion(Exception("x")) == "请尝试重启应用程序，或联系技术支持"

    def test_alert_style_by_severity(self, manager):
        """按错误严重度选择弹窗样式"""
        critical = PlookingIIError("x", severity=ErrorSeverity.CRITICAL)
        high = PlookingIIError("x", severity=ErrorSeverity.HIGH)
        low = PlookingIIError("x", severity=ErrorSeverity.LOW)
        assert manager._get_alert_style(critical) == 2
        # 不同 AppKit 版本常量取值可能不同（0/1），只断言为合法整型
        assert manager._get_alert_style(high) in (0, 1)
        assert manager._get_alert_style(low) in (0, 1)
        assert isinstance(manager._get_alert_style(OSError("x")), int)

    def test_detailed_help_texts(self, manager):
        """详细帮助文案包含对应模块提示"""
        assert manager._get_detailed_help(ImageProcessingError("x")).startswith("图片处理帮助")
        assert manager._get_detailed_help(Exception("x")) == "请联系技术支持获取帮助"

    @patch("plookingII.ui.utils.user_feedback.NSAlert")
    @patch("plookingII.ui.utils.user_feedback.get_ui_string")
    def test_show_error_dialog(self, mock_ui, mock_alert, manager):
        """错误弹窗展示并处理确认按钮"""
        mock_alert.alloc.return_value.init.return_value = mock_alert
        mock_ui.side_effect = lambda *args, **kwargs: args[-1]
        mock_alert.runModal.return_value = 1000

        manager.show_error_dialog(DragDropError("x"), "拖拽")

        mock_alert.setMessageText_.assert_called_with("拖拽操作遇到问题")
        mock_alert.runModal.assert_called_once()

    @patch("plookingII.ui.utils.user_feedback.NSAlert")
    @patch("plookingII.ui.utils.user_feedback.get_ui_string")
    def test_show_error_dialog_help_button(self, mock_ui, mock_alert, manager):
        """点击帮助按钮时展示详细帮助"""
        mock_alert.alloc.return_value.init.return_value = mock_alert
        mock_ui.side_effect = lambda *args, **kwargs: args[-1]
        mock_alert.runModal.return_value = 1001

        with patch.object(manager, "_show_help_dialog") as help_dialog:
            manager.show_error_dialog(ImageProcessingError("x"), "处理")

        help_dialog.assert_called_once()

    @patch("plookingII.ui.utils.user_feedback.NSAlert")
    @patch("plookingII.ui.utils.user_feedback.get_ui_string")
    def test_show_error_dialog_exception_falls_back(self, mock_ui, mock_alert, manager):
        """弹窗异常时回退到简单错误提示"""
        mock_alert.alloc.side_effect = Exception("NSAlert failed")
        mock_ui.side_effect = lambda *args, **kwargs: args[-1]

        with patch.object(manager, "_show_simple_error") as simple:
            manager.show_error_dialog(DragDropError("x"))

        simple.assert_called_once()

    @patch("plookingII.ui.utils.user_feedback.NSAlert")
    def test_show_warning_message_confirmation(self, mock_alert, manager):
        """警告弹窗返回用户确认结果"""
        mock_alert.alloc.return_value.init.return_value = mock_alert
        mock_alert.runModal.return_value = 1000
        assert manager.show_warning_message("标题", "内容") is True

        mock_alert.runModal.return_value = 1001
        assert manager.show_warning_message("标题", "内容") is False

    @patch("plookingII.ui.utils.user_feedback.NSAlert")
    def test_show_info_message(self, mock_alert, manager):
        """信息弹窗正常展示"""
        mock_alert.alloc.return_value.init.return_value = mock_alert
        manager.show_info_message("标题", "内容")
        mock_alert.runModal.assert_called_once()

    @patch("plookingII.ui.utils.user_feedback.NSAlert")
    def test_show_simple_error(self, mock_alert, manager):
        """简单错误回退弹窗"""
        mock_alert.alloc.return_value.init.return_value = mock_alert
        manager._show_simple_error("出错了")
        mock_alert.setMessageText_.assert_called_with("错误")

    @patch("plookingII.ui.utils.user_feedback.NSAlert")
    def test_module_level_show_warning(self, mock_alert):
        """模块级便捷函数可用"""
        mock_alert.alloc.return_value.init.return_value = mock_alert
        mock_alert.runModal.return_value = 1000
        assert show_warning("标题", "内容") is True

    @patch("plookingII.ui.utils.user_feedback.NSAlert")
    def test_module_level_show_info(self, mock_alert):
        """模块级信息提示可用"""
        mock_alert.alloc.return_value.init.return_value = mock_alert
        show_info("标题", "内容")
        mock_alert.runModal.assert_called_once()
