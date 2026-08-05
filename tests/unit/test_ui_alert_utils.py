"""
测试 ui/utils/alert_utils.py

覆盖：激活置前、sheet 优先展示、模态回退。
"""

from unittest.mock import MagicMock, patch

from plookingII.ui.utils.alert_utils import activate_app_and_front, present_alert_sheet, run_modal


class TestAlertUtils:
    @patch("plookingII.ui.utils.alert_utils.NSApplication")
    def test_activate_app_and_front(self, mock_app):
        """激活应用并把窗口置前、恢复最小化"""
        window = MagicMock()
        window.isMiniaturized.return_value = True

        activate_app_and_front(window)

        mock_app.sharedApplication.return_value.activateIgnoringOtherApps_.assert_called_once_with(True)
        window.makeKeyAndOrderFront_.assert_called_once_with(None)
        window.orderFrontRegardless.assert_called_once()
        window.deminiaturize_.assert_called_once_with(None)

    @patch("plookingII.ui.utils.alert_utils.NSApplication")
    def test_present_alert_sheet_success(self, mock_app):
        """有窗口时以 sheet 展示并返回 True"""
        alert = MagicMock()
        window = MagicMock()

        assert present_alert_sheet(alert, window) is True
        alert.beginSheetModalForWindow_completionHandler_.assert_called_once()

    @patch("plookingII.ui.utils.alert_utils.NSApplication")
    def test_present_alert_sheet_falls_back_on_exception(self, mock_app):
        """sheet 展示异常时返回 False 供调用方回退"""
        alert = MagicMock()
        alert.beginSheetModalForWindow_completionHandler_.side_effect = Exception("sheet failed")

        assert present_alert_sheet(alert, MagicMock()) is False

    @patch("plookingII.ui.utils.alert_utils.NSApplication")
    def test_present_alert_sheet_without_window(self, mock_app):
        """无窗口时不使用 sheet，返回 False"""
        assert present_alert_sheet(MagicMock(), None) is False

    @patch("plookingII.ui.utils.alert_utils.NSApplication")
    def test_run_modal_returns_result(self, mock_app):
        """模态弹窗返回按钮结果"""
        alert = MagicMock()
        alert.runModal.return_value = 1001
        assert run_modal(alert, MagicMock()) == 1001

    @patch("plookingII.ui.utils.alert_utils.NSApplication")
    def test_run_modal_exception_returns_zero(self, mock_app):
        """模态异常时返回 0"""
        alert = MagicMock()
        alert.runModal.side_effect = Exception("modal failed")
        assert run_modal(alert, None) == 0
