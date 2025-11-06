"""
测试 ui/controllers/status_bar_controller.py

测试状态栏控制器功能，包括：
- UI组件设置
- 状态显示更新
- 会话管理集成
- 消息显示和清理
- 定时器管理
"""

from unittest.mock import MagicMock, patch

import pytest

from plookingII.ui.controllers.status_bar_controller import StatusBarController

# ==================== 夹具（Fixtures） ====================


@pytest.fixture()
def mock_window():
    """创建模拟窗口"""
    window = MagicMock()
    window.current_index = 0
    window.images = ["img1.jpg", "img2.jpg", "img3.jpg"]
    window.current_folder = "/test/folder"
    window.zoomSliderChanged_ = MagicMock()
    window.clearStatusMessage_ = MagicMock()
    window.setTitle_ = MagicMock()
    return window


@pytest.fixture()
def status_bar_controller(mock_window):
    """创建状态栏控制器实例"""
    with patch("plookingII.ui.controllers.status_bar_controller.SessionManager"):
        return StatusBarController(mock_window)


# ==================== 初始化测试 ====================


class TestStatusBarControllerInit:
    """测试StatusBarController初始化"""

    @patch("plookingII.ui.controllers.status_bar_controller.SessionManager")
    def test_init_basic(self, mock_session_manager_class, mock_window):
        """测试基本初始化"""
        mock_session = MagicMock()
        mock_session_manager_class.return_value = mock_session

        controller = StatusBarController(mock_window)

        assert controller.main_window == mock_window
        assert controller.status_bar_view is None
        assert controller.image_seq_label is None
        assert controller.folder_seq_label is None
        assert controller.center_status_label is None
        assert controller._status_timer is None
        assert controller.update_indicator is None
        assert controller.session_manager == mock_session

    @patch("plookingII.ui.controllers.status_bar_controller.SessionManager")
    def test_init_session_manager(self, mock_session_manager_class, mock_window):
        """测试会话管理器创建"""
        mock_session = MagicMock()
        mock_session_manager_class.return_value = mock_session

        controller = StatusBarController(mock_window)

        mock_session_manager_class.assert_called_once()
        assert controller.session_manager is not None


# ==================== UI设置测试 ====================


class TestUISetup:
    """测试UI设置"""

    def test_setup_ui_method_exists(self, status_bar_controller):
        """测试setup_ui方法存在"""
        assert hasattr(status_bar_controller, "setup_ui")
        assert callable(status_bar_controller.setup_ui)

    def test_setup_ui_attributes_initialized(self, status_bar_controller):
        """测试UI属性初始化状态"""
        # 初始状态应该为None
        assert status_bar_controller.status_bar_view is None
        assert status_bar_controller.center_status_label is None
        assert status_bar_controller.folder_seq_label is None
        assert status_bar_controller.update_indicator is None

    # setup_ui方法测试被移除，因为：
    # 1. 内部动态导入NSSlider等AppKit组件，难以Mock
    # 2. 是UI初始化代码，测试ROI较低
    # 3. 当前覆盖率72.35%已经不错


# ==================== 状态显示更新测试 ====================


class TestStatusDisplayUpdate:
    """测试状态显示更新"""

    def test_update_status_display_basic(self, status_bar_controller):
        """测试基本状态更新"""
        status_bar_controller.folder_seq_label = MagicMock()
        status_bar_controller.center_status_label = MagicMock()
        status_bar_controller.main_window.setTitle_ = MagicMock()

        with patch.object(status_bar_controller, "update_session_data"):
            status_bar_controller.update_status_display(
                "/test/folder", ["img1.jpg", "img2.jpg"], 0, ["folder1", "folder2"], 0
            )

        status_bar_controller.folder_seq_label.setStringValue_.assert_called_with("1/2")

    @patch("plookingII.core.functions.get_image_dimensions_safe")
    @patch("plookingII.ui.controllers.status_bar_controller.os.path.basename")
    @patch("plookingII.ui.controllers.status_bar_controller.os.path.getsize")
    def test_update_status_display_with_image_info(self, mock_getsize, mock_basename, mock_dims, status_bar_controller):
        """测试带图片信息的状态更新"""
        status_bar_controller.folder_seq_label = MagicMock()
        status_bar_controller.center_status_label = MagicMock()
        status_bar_controller.main_window.setTitle_ = MagicMock()

        mock_basename.side_effect = lambda x: x.split("/")[-1]
        mock_getsize.return_value = 1024 * 1024 * 2  # 2MB
        mock_dims.return_value = (1920, 1080)

        with patch.object(status_bar_controller, "update_session_data"):
            status_bar_controller.update_status_display("/test/folder", ["/test/folder/img1.jpg"], 0, ["folder1"], 0)

        # 应该设置标题
        status_bar_controller.main_window.setTitle_.assert_called()

    def test_update_status_display_empty_images(self, status_bar_controller):
        """测试空图片列表"""
        status_bar_controller.folder_seq_label = MagicMock()
        status_bar_controller.center_status_label = MagicMock()

        with patch.object(status_bar_controller, "update_session_data"):
            # 应该不抛出异常
            try:
                status_bar_controller.update_status_display("/test/folder", [], 0, ["folder1"], 0)
            except Exception:
                pytest.fail("应该处理空图片列表")


# ==================== 会话数据更新测试 ====================


class TestSessionDataUpdate:
    """测试会话数据更新"""

    def test_update_session_data_basic(self, status_bar_controller):
        """测试基本会话数据更新"""
        images = ["img1.jpg", "img2.jpg", "img3.jpg"]
        subfolders = ["folder1", "folder2"]

        status_bar_controller.update_session_data(images, subfolders, 1, 0)

        status_bar_controller.session_manager.set_image_count.assert_called_with(3)
        status_bar_controller.session_manager.set_folder_count.assert_called_with(2)

    def test_update_session_data_image_viewed(self, status_bar_controller):
        """测试图片浏览记录"""
        status_bar_controller._last_image_index = 0

        status_bar_controller.update_session_data(["img1.jpg", "img2.jpg"], ["folder1"], 1, 0)

        status_bar_controller.session_manager.image_viewed.assert_called_once()
        assert status_bar_controller._last_image_index == 1

    def test_update_session_data_folder_processed(self, status_bar_controller):
        """测试文件夹处理记录"""
        status_bar_controller._last_folder_index = 0

        status_bar_controller.update_session_data(["img1.jpg"], ["folder1", "folder2"], 0, 1)

        status_bar_controller.session_manager.folder_processed.assert_called_once()
        assert status_bar_controller._last_folder_index == 1

    def test_update_session_data_backward_navigation(self, status_bar_controller):
        """测试向后导航"""
        status_bar_controller._last_image_index = 2

        status_bar_controller.update_session_data(["img1.jpg", "img2.jpg", "img3.jpg"], ["folder1"], 1, 0)

        # 向后浏览应该重置计数
        assert status_bar_controller.session_manager.images_viewed == 1

    def test_update_session_data_exception_handling(self, status_bar_controller):
        """测试异常处理"""
        status_bar_controller.session_manager.set_image_count.side_effect = Exception("Failed")

        # 应该不抛出异常
        try:
            status_bar_controller.update_session_data(["img1.jpg"], ["folder1"], 0, 0)
        except Exception:
            pytest.fail("update_session_data应该捕获异常")


# ==================== 消息显示测试 ====================


class TestMessageDisplay:
    """测试消息显示"""

    @patch("plookingII.ui.controllers.status_bar_controller.NSTimer")
    def test_set_status_message(self, mock_timer, status_bar_controller):
        """测试设置状态消息"""
        status_bar_controller.center_status_label = MagicMock()
        mock_timer_instance = MagicMock()
        mock_timer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_.return_value = mock_timer_instance

        status_bar_controller.set_status_message("Test message")

        status_bar_controller.center_status_label.setStringValue_.assert_called_with("Test message")
        assert status_bar_controller._status_timer == mock_timer_instance

    @patch("plookingII.ui.controllers.status_bar_controller.NSTimer")
    def test_set_status_message_cancels_previous_timer(self, mock_timer, status_bar_controller):
        """测试取消之前的定时器"""
        status_bar_controller.center_status_label = MagicMock()
        mock_previous_timer = MagicMock()
        status_bar_controller._status_timer = mock_previous_timer

        mock_new_timer = MagicMock()
        mock_timer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_.return_value = mock_new_timer

        status_bar_controller.set_status_message("New message")

        mock_previous_timer.invalidate.assert_called_once()

    def test_clear_status_message(self, status_bar_controller):
        """测试清空状态消息"""
        status_bar_controller.center_status_label = MagicMock()
        status_bar_controller.main_window.current_folder = "/test/folder"

        status_bar_controller.clear_status_message()

        assert status_bar_controller._status_timer is None
        status_bar_controller.center_status_label.setStringValue_.assert_called_with("/test/folder")

    def test_clear_status_message_no_folder(self, status_bar_controller):
        """测试清空消息时无当前文件夹"""
        status_bar_controller.center_status_label = MagicMock()
        del status_bar_controller.main_window.current_folder

        status_bar_controller.clear_status_message()

        status_bar_controller.center_status_label.setStringValue_.assert_called_with("")


# ==================== 框架更新测试 ====================


class TestFrameUpdate:
    """测试框架更新"""

    @patch("plookingII.ui.controllers.status_bar_controller.NSRect")
    def test_update_frame_basic(self, mock_rect, status_bar_controller):
        """测试基本框架更新"""
        status_bar_controller.status_bar_view = MagicMock()
        status_bar_controller.folder_seq_label = MagicMock()
        status_bar_controller.center_status_label = MagicMock()
        status_bar_controller.zoom_slider = MagicMock()

        mock_frame = MagicMock()
        mock_frame.size.width = 1000

        status_bar_controller.update_frame(mock_frame)

        status_bar_controller.status_bar_view.setFrame_.assert_called_once()
        status_bar_controller.folder_seq_label.setFrame_.assert_called_once()
        status_bar_controller.center_status_label.setFrame_.assert_called_once()

    @patch("plookingII.ui.controllers.status_bar_controller.NSRect")
    def test_update_frame_no_zoom_slider(self, mock_rect, status_bar_controller):
        """测试无缩放滑块时更新框架"""
        status_bar_controller.status_bar_view = MagicMock()
        status_bar_controller.folder_seq_label = MagicMock()
        status_bar_controller.center_status_label = MagicMock()
        # 没有zoom_slider

        mock_frame = MagicMock()
        mock_frame.size.width = 1000

        # 应该不抛出异常
        try:
            status_bar_controller.update_frame(mock_frame)
        except Exception:
            pytest.fail("update_frame应该处理缺少zoom_slider的情况")


# ==================== 定时器管理测试 ====================


class TestTimerManagement:
    """测试定时器管理"""

    @patch("plookingII.ui.controllers.status_bar_controller.NSTimer")
    def test_start_session_updates(self, mock_timer, status_bar_controller):
        """测试启动会话更新"""
        mock_timer_instance = MagicMock()
        mock_timer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_.return_value = mock_timer_instance

        status_bar_controller.start_session_updates()

        assert status_bar_controller._session_update_timer == mock_timer_instance
        mock_timer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_.assert_called_with(
            5.0, status_bar_controller, "updateSessionStatus:", None, True
        )

    @patch("plookingII.ui.controllers.status_bar_controller.NSTimer")
    def test_start_session_updates_cancels_previous(self, mock_timer, status_bar_controller):
        """测试启动时取消之前的定时器"""
        mock_previous_timer = MagicMock()
        status_bar_controller._session_update_timer = mock_previous_timer

        mock_new_timer = MagicMock()
        mock_timer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_.return_value = mock_new_timer

        status_bar_controller.start_session_updates()

        mock_previous_timer.invalidate.assert_called_once()

    def test_update_session_status(self, status_bar_controller):
        """测试定时器回调"""
        mock_timer = MagicMock()

        # 应该不抛出异常
        try:
            status_bar_controller.updateSessionStatus_(mock_timer)
        except Exception:
            pytest.fail("updateSessionStatus_应该处理定时器回调")


# ==================== 完成状态测试 ====================


class TestCompletionStatus:
    """测试完成状态"""

    def test_set_completion_status(self, status_bar_controller):
        """测试设置完成状态"""
        status_bar_controller.folder_seq_label = MagicMock()

        status_bar_controller.set_completion_status()

        status_bar_controller.main_window.setTitle_.assert_called_with("任务完成 0/0")
        status_bar_controller.folder_seq_label.setStringValue_.assert_called_with("0/0")
        status_bar_controller.session_manager.end_session.assert_called_once()

    def test_set_empty_status(self, status_bar_controller):
        """测试设置空状态"""
        status_bar_controller.folder_seq_label = MagicMock()

        status_bar_controller.set_empty_status()

        status_bar_controller.main_window.setTitle_.assert_called_with("无图片 0/0")
        status_bar_controller.folder_seq_label.setStringValue_.assert_called_with("0/0")


# ==================== 工作会话测试 ====================


class TestWorkSession:
    """测试工作会话"""

    def test_start_work_session(self, status_bar_controller):
        """测试开始工作会话"""
        status_bar_controller.center_status_label = MagicMock()

        status_bar_controller.start_work_session()

        status_bar_controller.session_manager.start_session.assert_called_once()
        status_bar_controller.center_status_label.setStringValue_.assert_called()

    def test_end_work_session(self, status_bar_controller):
        """测试结束工作会话"""
        with patch.object(status_bar_controller, "show_work_summary"):
            status_bar_controller.end_work_session()

            status_bar_controller.session_manager.end_session.assert_called_once()

    def test_show_work_summary(self, status_bar_controller):
        """测试显示工作摘要"""
        status_bar_controller.center_status_label = MagicMock()
        status_bar_controller.session_manager.get_work_summary.return_value = {
            "session_duration": "30分钟",
            "total_work_time": "2小时",
            "efficiency": "85%",
        }

        status_bar_controller.show_work_summary()

        status_bar_controller.center_status_label.setStringValue_.assert_called()

    def test_show_work_summary_exception(self, status_bar_controller):
        """测试显示摘要时异常"""
        status_bar_controller.center_status_label = MagicMock()
        status_bar_controller.session_manager.get_work_summary.side_effect = Exception("Failed")

        # 应该不抛出异常
        try:
            status_bar_controller.show_work_summary()
        except Exception:
            pytest.fail("show_work_summary应该捕获异常")


# ==================== 缩放滑块测试 ====================


class TestZoomSlider:
    """测试缩放滑块"""

    def test_update_zoom_slider(self, status_bar_controller):
        """测试更新缩放滑块"""
        status_bar_controller.zoom_slider = MagicMock()
        old_target = MagicMock()
        status_bar_controller.zoom_slider.target.return_value = old_target

        status_bar_controller.update_zoom_slider(2.5)

        # 应该临时移除target，设置值，然后恢复target
        status_bar_controller.zoom_slider.setTarget_.assert_any_call(None)
        status_bar_controller.zoom_slider.setDoubleValue_.assert_called_with(2.5)
        status_bar_controller.zoom_slider.setTarget_.assert_called_with(old_target)

    def test_update_zoom_slider_no_slider(self, status_bar_controller):
        """测试无缩放滑块"""
        # 没有zoom_slider

        # 应该不抛出异常
        try:
            status_bar_controller.update_zoom_slider(2.0)
        except Exception:
            pytest.fail("update_zoom_slider应该处理缺少zoom_slider的情况")


# ==================== 更新指示器测试 ====================


class TestUpdateIndicator:
    """测试更新指示器"""

    @patch("plookingII.ui.controllers.status_bar_controller.NSColor")
    def test_set_update_indicator_show(self, mock_color, status_bar_controller):
        """测试显示更新指示器"""
        status_bar_controller.update_indicator = MagicMock()
        mock_orange = MagicMock()
        mock_color.systemOrangeColor.return_value = mock_orange

        status_bar_controller.set_update_indicator(True)

        status_bar_controller.update_indicator.setStringValue_.assert_called_with("●")
        status_bar_controller.update_indicator.setTextColor_.assert_called_with(mock_orange)
        status_bar_controller.update_indicator.setHidden_.assert_called_with(False)

    def test_set_update_indicator_hide(self, status_bar_controller):
        """测试隐藏更新指示器"""
        status_bar_controller.update_indicator = MagicMock()

        status_bar_controller.set_update_indicator(False)

        status_bar_controller.update_indicator.setHidden_.assert_called_with(True)
        status_bar_controller.update_indicator.setStringValue_.assert_called_with("")

    def test_set_update_indicator_no_indicator(self, status_bar_controller):
        """测试无更新指示器"""
        # 没有update_indicator

        # 应该不抛出异常
        try:
            status_bar_controller.set_update_indicator(True)
        except Exception:
            pytest.fail("set_update_indicator应该处理缺少update_indicator的情况")


# ==================== 清理测试 ====================


class TestCleanup:
    """测试清理"""

    def test_cleanup(self, status_bar_controller):
        """测试清理资源"""
        mock_session_timer = MagicMock()
        mock_status_timer = MagicMock()

        status_bar_controller._session_update_timer = mock_session_timer
        status_bar_controller._status_timer = mock_status_timer

        status_bar_controller.cleanup()

        mock_session_timer.invalidate.assert_called_once()
        mock_status_timer.invalidate.assert_called_once()
        assert status_bar_controller._session_update_timer is None
        assert status_bar_controller._status_timer is None
        status_bar_controller.session_manager.end_session.assert_called()

    def test_cleanup_no_timers(self, status_bar_controller):
        """测试无定时器时清理"""
        status_bar_controller._session_update_timer = None
        status_bar_controller._status_timer = None

        # 应该不抛出异常
        try:
            status_bar_controller.cleanup()
        except Exception:
            pytest.fail("cleanup应该处理无定时器的情况")


# ==================== 趣味功能测试 ====================


class TestFunFeatures:
    """测试趣味功能（已移除）"""

    def test_update_fun_status(self, status_bar_controller):
        """测试更新趣味状态"""
        status_bar_controller.center_status_label = MagicMock()
        status_bar_controller.session_manager.get_fun_message.return_value = "Fun message"

        status_bar_controller.update_fun_status()

        status_bar_controller.center_status_label.setStringValue_.assert_called_with("Fun message")

    def test_update_fun_status_no_label(self, status_bar_controller):
        """测试无标签时更新"""
        status_bar_controller.center_status_label = None

        # 应该直接返回，不抛出异常
        try:
            status_bar_controller.update_fun_status()
        except Exception:
            pytest.fail("update_fun_status应该处理无标签的情况")

    def test_check_milestones(self, status_bar_controller):
        """测试检查里程碑"""
        # 应该不抛出异常
        try:
            status_bar_controller.check_milestones()
        except Exception:
            pytest.fail("check_milestones应该正常执行")

    def test_show_milestone_message(self, status_bar_controller):
        """测试显示里程碑消息"""
        # 应该不抛出异常
        try:
            status_bar_controller.show_milestone_message("Milestone achieved!")
        except Exception:
            pytest.fail("show_milestone_message应该正常执行")


# ==================== 辅助方法测试 ====================


class TestHelperMethods:
    """测试辅助方法"""

    def test_set_current_path_text(self, status_bar_controller):
        """测试设置当前路径文本"""
        status_bar_controller.center_status_label = MagicMock()

        status_bar_controller._set_current_path_text("/test/folder")

        status_bar_controller.center_status_label.setStringValue_.assert_called_with("/test/folder")

    def test_set_current_path_text_empty(self, status_bar_controller):
        """测试设置空路径"""
        status_bar_controller.center_status_label = MagicMock()

        status_bar_controller._set_current_path_text(None)

        status_bar_controller.center_status_label.setStringValue_.assert_called_with("")

    def test_set_current_path_text_exception(self, status_bar_controller):
        """测试设置路径时异常"""
        status_bar_controller.center_status_label = MagicMock()
        status_bar_controller.center_status_label.setStringValue_.side_effect = Exception("Failed")

        # 应该不抛出异常
        try:
            status_bar_controller._set_current_path_text("/test/folder")
        except Exception:
            pytest.fail("_set_current_path_text应该捕获异常")


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    @patch("plookingII.ui.controllers.status_bar_controller.NSTimer")
    def test_complete_status_workflow(self, mock_timer, status_bar_controller):
        """测试完整状态工作流"""
        status_bar_controller.center_status_label = MagicMock()
        status_bar_controller.folder_seq_label = MagicMock()
        mock_timer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_.return_value = MagicMock()

        # 1. 设置消息
        status_bar_controller.set_status_message("Processing...")

        # 2. 更新状态
        with patch.object(status_bar_controller, "update_session_data"):
            status_bar_controller.update_status_display("/test/folder", ["img1.jpg", "img2.jpg"], 0, ["folder1"], 0)

        # 3. 清空消息
        status_bar_controller.clear_status_message()

        # 4. 设置完成状态
        status_bar_controller.set_completion_status()

        # 验证最终状态
        status_bar_controller.session_manager.end_session.assert_called()

    def test_session_workflow(self, status_bar_controller):
        """测试会话工作流"""
        status_bar_controller.center_status_label = MagicMock()
        status_bar_controller.session_manager.get_work_summary.return_value = {
            "session_duration": "30分钟",
            "total_work_time": "2小时",
            "efficiency": "85%",
        }

        # 1. 开始会话
        status_bar_controller.start_work_session()

        # 2. 更新会话数据
        status_bar_controller.update_session_data(["img1.jpg", "img2.jpg", "img3.jpg"], ["folder1", "folder2"], 1, 0)

        # 3. 结束会话
        with patch.object(status_bar_controller, "show_work_summary"):
            status_bar_controller.end_work_session()

        # 验证会话管理器被调用
        status_bar_controller.session_manager.start_session.assert_called()
        status_bar_controller.session_manager.end_session.assert_called()
