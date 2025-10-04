"""
测试 ui/controllers/navigation_controller.py

测试导航控制器功能，包括：
- 键盘事件处理
- 防抖动机制
- 导航队列处理
- 旋转操作
- 递归防护
"""

from unittest.mock import MagicMock, Mock, patch, call
import time
import threading

import pytest

from plookingII.ui.controllers.navigation_controller import NavigationController


# ==================== 夹具（Fixtures） ====================


@pytest.fixture
def mock_window():
    """创建模拟窗口"""
    window = MagicMock()
    window.current_index = 0
    window.images = ["img1.jpg", "img2.jpg", "img3.jpg"]
    window.operation_manager = MagicMock()
    window.folder_manager = MagicMock()
    window._show_current_image_optimized = MagicMock()
    window._update_status_display_immediate = MagicMock()
    window._last_keep_action = None
    window.rotate_image_clockwise = MagicMock()
    window.rotate_image_counterclockwise = MagicMock()
    return window


@pytest.fixture
def navigation_controller(mock_window):
    """创建导航控制器实例"""
    return NavigationController(mock_window)


# ==================== 初始化测试 ====================


class TestNavigationControllerInit:
    """测试NavigationController初始化"""

    def test_init_basic(self, mock_window):
        """测试基本初始化"""
        controller = NavigationController(mock_window)
        
        assert controller.main_window == mock_window
        assert controller._state == controller._state_idle
        assert controller._key_debounce_delay == 0.015
        assert controller._is_navigating is False
        assert controller._processing_key_event is False
        assert controller._recursion_depth == 0
        assert controller._queued_steps == 0

    def test_init_with_performance_optimizer(self, mock_window):
        """测试带性能优化器的初始化"""
        with patch('plookingII.ui.controllers.navigation_controller.get_performance_optimizer') as mock_get:
            mock_optimizer = MagicMock()
            mock_get.return_value = mock_optimizer
            
            controller = NavigationController(mock_window)
            
            assert controller._perf_optimizer == mock_optimizer

    def test_init_performance_optimizer_failure(self, mock_window):
        """测试性能优化器初始化失败"""
        with patch('plookingII.ui.controllers.navigation_controller.get_performance_optimizer') as mock_get:
            mock_get.side_effect = Exception("Optimizer failed")
            
            controller = NavigationController(mock_window)
            
            assert controller._perf_optimizer is None


# ==================== 键盘事件处理测试 ====================


class TestKeyboardEventHandling:
    """测试键盘事件处理"""

    def test_handle_key_event_none(self, navigation_controller):
        """测试空事件对象"""
        result = navigation_controller.handle_key_event(None)
        
        assert result is False

    def test_handle_left_arrow_key(self, navigation_controller):
        """测试左方向键"""
        mock_event = MagicMock()
        mock_event.characters.return_value = "\uf702"
        mock_event.modifierFlags.return_value = 0
        
        with patch.object(navigation_controller, '_handle_navigation_key') as mock_handle:
            result = navigation_controller.handle_key_event(mock_event)
            
            assert result is True
            mock_handle.assert_called_once_with("left")

    def test_handle_right_arrow_key(self, navigation_controller):
        """测试右方向键"""
        mock_event = MagicMock()
        mock_event.characters.return_value = "\uf703"
        mock_event.modifierFlags.return_value = 0
        
        with patch.object(navigation_controller, '_handle_navigation_key') as mock_handle:
            result = navigation_controller.handle_key_event(mock_event)
            
            assert result is True
            mock_handle.assert_called_once_with("right")

    def test_handle_down_arrow_key(self, navigation_controller):
        """测试下方向键（保留图片）"""
        mock_event = MagicMock()
        mock_event.characters.return_value = "\uf701"
        mock_event.modifierFlags.return_value = 0
        
        result = navigation_controller.handle_key_event(mock_event)
        
        assert result is True
        navigation_controller.main_window.operation_manager.keep_current_image.assert_called_once()

    def test_handle_up_arrow_key(self, navigation_controller):
        """测试上方向键（预留功能）"""
        mock_event = MagicMock()
        mock_event.characters.return_value = "\uf700"
        mock_event.modifierFlags.return_value = 0
        
        result = navigation_controller.handle_key_event(mock_event)
        
        assert result is True

    def test_handle_esc_key(self, navigation_controller):
        """测试ESC键"""
        mock_event = MagicMock()
        mock_event.characters.return_value = ""
        mock_event.keyCode.return_value = 53
        mock_event.modifierFlags.return_value = 0
        
        result = navigation_controller.handle_key_event(mock_event)
        
        assert result is True
        navigation_controller.main_window.operation_manager.exit_current_folder.assert_called_once()

    @patch('plookingII.ui.controllers.navigation_controller.NSEventModifierFlagCommand', 1048576)
    def test_handle_command_z(self, navigation_controller):
        """测试Command+Z（撤销）"""
        mock_event = MagicMock()
        mock_event.characters.return_value = "z"
        mock_event.modifierFlags.return_value = 1048576
        
        result = navigation_controller.handle_key_event(mock_event)
        
        assert result is True
        navigation_controller.main_window.operation_manager.undo_keep_action.assert_called_once()

    @patch('plookingII.ui.controllers.navigation_controller.NSEventModifierFlagCommand', 1048576)
    def test_handle_command_right_arrow(self, navigation_controller):
        """测试Command+右方向键（跳过文件夹）"""
        mock_event = MagicMock()
        mock_event.characters.return_value = "\uf703"
        mock_event.modifierFlags.return_value = 1048576
        
        result = navigation_controller.handle_key_event(mock_event)
        
        assert result is True
        navigation_controller.main_window.folder_manager.skip_current_folder.assert_called_once()

    @patch('plookingII.ui.controllers.navigation_controller.NSEventModifierFlagCommand', 1048576)
    def test_handle_command_left_arrow(self, navigation_controller):
        """测试Command+左方向键（撤销跳过）"""
        mock_event = MagicMock()
        mock_event.characters.return_value = "\uf702"
        mock_event.modifierFlags.return_value = 1048576
        
        result = navigation_controller.handle_key_event(mock_event)
        
        assert result is True
        navigation_controller.main_window.folder_manager.undo_skip_folder.assert_called_once()

    @patch('plookingII.ui.controllers.navigation_controller.NSEventModifierFlagCommand', 1048576)
    @patch('plookingII.ui.controllers.navigation_controller.NSEventModifierFlagOption', 524288)
    def test_handle_command_option_r(self, navigation_controller):
        """测试Command+Option+R（右旋转）"""
        mock_event = MagicMock()
        mock_event.characters.return_value = "r"
        mock_event.modifierFlags.return_value = 1048576 | 524288
        
        with patch.object(navigation_controller, '_execute_rotation_safely') as mock_rotate:
            result = navigation_controller.handle_key_event(mock_event)
            
            assert result is True
            mock_rotate.assert_called_once_with("clockwise")

    @patch('plookingII.ui.controllers.navigation_controller.NSEventModifierFlagCommand', 1048576)
    @patch('plookingII.ui.controllers.navigation_controller.NSEventModifierFlagOption', 524288)
    def test_handle_command_option_l(self, navigation_controller):
        """测试Command+Option+L（左旋转）"""
        mock_event = MagicMock()
        mock_event.characters.return_value = "l"
        mock_event.modifierFlags.return_value = 1048576 | 524288
        
        with patch.object(navigation_controller, '_execute_rotation_safely') as mock_rotate:
            result = navigation_controller.handle_key_event(mock_event)
            
            assert result is True
            mock_rotate.assert_called_once_with("counterclockwise")

    def test_handle_unknown_key(self, navigation_controller):
        """测试未知按键"""
        mock_event = MagicMock()
        mock_event.characters.return_value = "a"
        mock_event.modifierFlags.return_value = 0
        
        result = navigation_controller.handle_key_event(mock_event)
        
        assert result is False


# ==================== 递归防护测试 ====================


class TestRecursionProtection:
    """测试递归防护"""

    def test_recursion_protection_basic(self, navigation_controller):
        """测试基本递归防护"""
        navigation_controller._processing_key_event = True
        
        mock_event = MagicMock()
        result = navigation_controller.handle_key_event(mock_event)
        
        assert result is False
        assert navigation_controller._recursion_depth == 1

    def test_recursion_depth_limit(self, navigation_controller):
        """测试递归深度限制"""
        navigation_controller._processing_key_event = True
        navigation_controller._recursion_depth = 3
        
        mock_event = MagicMock()
        result = navigation_controller.handle_key_event(mock_event)
        
        assert result is False
        assert navigation_controller._recursion_depth == 0  # 强制重置

    def test_recursion_reset_after_processing(self, navigation_controller):
        """测试处理后递归标志重置"""
        mock_event = MagicMock()
        mock_event.characters.return_value = "\uf700"
        mock_event.modifierFlags.return_value = 0
        
        navigation_controller.handle_key_event(mock_event)
        
        assert navigation_controller._processing_key_event is False
        assert navigation_controller._recursion_depth == 0


# ==================== 旋转操作测试 ====================


class TestRotationOperations:
    """测试旋转操作"""

    @patch('plookingII.ui.controllers.navigation_controller.threading.Thread')
    def test_execute_rotation_clockwise(self, mock_thread_class, navigation_controller):
        """测试顺时针旋转"""
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread
        
        navigation_controller._execute_rotation_safely("clockwise")
        
        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()

    @patch('plookingII.ui.controllers.navigation_controller.threading.Thread')
    def test_execute_rotation_counterclockwise(self, mock_thread_class, navigation_controller):
        """测试逆时针旋转"""
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread
        
        navigation_controller._execute_rotation_safely("counterclockwise")
        
        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()

    def test_execute_rotation_exception_handling(self, navigation_controller):
        """测试旋转异常处理"""
        with patch('plookingII.ui.controllers.navigation_controller.threading.Thread') as mock_thread_class:
            mock_thread_class.side_effect = Exception("Thread failed")
            
            # 应该不抛出异常
            try:
                navigation_controller._execute_rotation_safely("clockwise")
            except Exception:
                pytest.fail("_execute_rotation_safely应该捕获异常")


# ==================== 导航防抖测试 ====================


class TestNavigationDebounce:
    """测试导航防抖"""

    @patch('plookingII.ui.controllers.navigation_controller.NSTimer')
    @patch('plookingII.ui.controllers.navigation_controller.time.time')
    def test_handle_navigation_key_basic(self, mock_time, mock_timer, navigation_controller):
        """测试基本导航防抖"""
        mock_time.return_value = 1000.0
        mock_timer_instance = MagicMock()
        mock_timer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_.return_value = mock_timer_instance
        
        navigation_controller._handle_navigation_key("right")
        
        assert navigation_controller._pending_navigation == "right"
        assert navigation_controller._last_key_time == 1000.0
        mock_timer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_.assert_called_once()

    @patch('plookingII.ui.controllers.navigation_controller.NSTimer')
    @patch('plookingII.ui.controllers.navigation_controller.time.time')
    def test_handle_navigation_key_cancel_previous(self, mock_time, mock_timer, navigation_controller):
        """测试取消之前的定时器"""
        mock_time.return_value = 1000.0
        mock_previous_timer = MagicMock()
        navigation_controller._key_debounce_timer = mock_previous_timer
        
        mock_timer_instance = MagicMock()
        mock_timer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_.return_value = mock_timer_instance
        
        navigation_controller._handle_navigation_key("right")
        
        mock_previous_timer.invalidate.assert_called_once()

    @patch('plookingII.ui.controllers.navigation_controller.NSTimer')
    @patch('plookingII.ui.controllers.navigation_controller.time.time')
    def test_handle_navigation_while_navigating(self, mock_time, mock_timer, navigation_controller):
        """测试导航中累积步进"""
        navigation_controller._is_navigating = True
        navigation_controller._queued_steps = 0
        
        navigation_controller._handle_navigation_key("right")
        
        assert navigation_controller._queued_steps == 1
        mock_timer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_.assert_not_called()

    def test_handle_navigation_queue_accumulation(self, navigation_controller):
        """测试队列累积"""
        navigation_controller._is_navigating = True
        
        navigation_controller._handle_navigation_key("right")
        navigation_controller._handle_navigation_key("right")
        navigation_controller._handle_navigation_key("left")
        
        assert navigation_controller._queued_steps == 1  # 2 - 1


# ==================== 导航执行测试 ====================


class TestNavigationExecution:
    """测试导航执行"""

    def test_execute_pending_navigation_no_pending(self, navigation_controller):
        """测试无待处理导航"""
        navigation_controller._pending_navigation = None
        
        navigation_controller.execute_pending_navigation()
        
        navigation_controller.main_window._show_current_image_optimized.assert_not_called()

    def test_execute_pending_navigation_right(self, navigation_controller):
        """测试向右导航"""
        navigation_controller._pending_navigation = "right"
        navigation_controller.main_window.current_index = 0
        
        navigation_controller.execute_pending_navigation()
        
        assert navigation_controller.main_window.current_index == 1
        navigation_controller.main_window._show_current_image_optimized.assert_called()

    def test_execute_pending_navigation_left(self, navigation_controller):
        """测试向左导航"""
        navigation_controller._pending_navigation = "left"
        navigation_controller.main_window.current_index = 2
        
        navigation_controller.execute_pending_navigation()
        
        assert navigation_controller.main_window.current_index == 1
        navigation_controller.main_window._show_current_image_optimized.assert_called()

    def test_execute_pending_navigation_left_boundary(self, navigation_controller):
        """测试左边界跳转"""
        navigation_controller._pending_navigation = "left"
        navigation_controller.main_window.current_index = 0
        
        navigation_controller.execute_pending_navigation()
        
        navigation_controller.main_window.folder_manager.jump_to_previous_folder.assert_called_once()

    def test_execute_pending_navigation_right_boundary(self, navigation_controller):
        """测试右边界跳转"""
        navigation_controller._pending_navigation = "right"
        navigation_controller.main_window.current_index = 2
        
        navigation_controller.execute_pending_navigation()
        
        navigation_controller.main_window.folder_manager.jump_to_next_folder.assert_called_once()

    def test_execute_pending_navigation_with_queue(self, navigation_controller):
        """测试带队列的导航"""
        navigation_controller._pending_navigation = "right"
        navigation_controller._queued_steps = 2
        navigation_controller.main_window.current_index = 0
        
        navigation_controller.execute_pending_navigation()
        
        # 1 (right) + 2 (queued) = 3, 但列表只有3个元素，应该跳到下一个文件夹
        navigation_controller.main_window.folder_manager.jump_to_next_folder.assert_called_once()

    def test_execute_pending_navigation_jump_prev(self, navigation_controller):
        """测试跳转到上一个文件夹"""
        navigation_controller._pending_navigation = "jump_prev"
        
        navigation_controller.execute_pending_navigation()
        
        navigation_controller.main_window.folder_manager.jump_to_previous_folder.assert_called_once()

    def test_execute_pending_navigation_jump_next(self, navigation_controller):
        """测试跳转到下一个文件夹"""
        navigation_controller._pending_navigation = "jump_next"
        
        navigation_controller.execute_pending_navigation()
        
        navigation_controller.main_window.folder_manager.jump_to_next_folder.assert_called_once()


# ==================== 状态管理测试 ====================


class TestStateManagement:
    """测试状态管理"""

    def test_initial_state_idle(self, navigation_controller):
        """测试初始状态为空闲"""
        assert navigation_controller._state == navigation_controller._state_idle

    @patch('plookingII.ui.controllers.navigation_controller.NSTimer')
    def test_state_debouncing(self, mock_timer, navigation_controller):
        """测试防抖状态"""
        mock_timer_instance = MagicMock()
        mock_timer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_.return_value = mock_timer_instance
        
        navigation_controller._handle_navigation_key("right")
        
        assert navigation_controller._state == navigation_controller._state_debouncing

    def test_state_navigating(self, navigation_controller):
        """测试导航状态"""
        navigation_controller._pending_navigation = "right"
        
        navigation_controller.execute_pending_navigation()
        
        # 执行后应该回到idle状态
        assert navigation_controller._state == navigation_controller._state_idle


# ==================== 配置和清理测试 ====================


class TestConfigurationAndCleanup:
    """测试配置和清理"""

    def test_set_debounce_delay(self, navigation_controller):
        """测试设置防抖延迟"""
        navigation_controller.set_debounce_delay(0.05)
        
        assert navigation_controller._key_debounce_delay == 0.05

    def test_set_debounce_delay_minimum(self, navigation_controller):
        """测试最小防抖延迟"""
        navigation_controller.set_debounce_delay(0.001)
        
        assert navigation_controller._key_debounce_delay == 0.01

    def test_cleanup(self, navigation_controller):
        """测试清理"""
        mock_timer = MagicMock()
        navigation_controller._key_debounce_timer = mock_timer
        
        navigation_controller.cleanup()
        
        mock_timer.invalidate.assert_called_once()
        assert navigation_controller._key_debounce_timer is None

    def test_cleanup_no_timer(self, navigation_controller):
        """测试无定时器时清理"""
        navigation_controller._key_debounce_timer = None
        
        # 应该不抛出异常
        try:
            navigation_controller.cleanup()
        except Exception:
            pytest.fail("cleanup应该处理无定时器的情况")


# ==================== 边界情况测试 ====================


class TestEdgeCases:
    """测试边界情况"""

    def test_handle_event_exception(self, navigation_controller):
        """测试事件处理异常"""
        mock_event = MagicMock()
        mock_event.characters.side_effect = Exception("Event failed")
        
        result = navigation_controller.handle_key_event(mock_event)
        
        assert result is False

    def test_execute_navigation_no_images(self, navigation_controller):
        """测试无图片时导航"""
        navigation_controller._pending_navigation = "right"
        navigation_controller.main_window.images = []
        
        # 应该不抛出异常
        try:
            navigation_controller.execute_pending_navigation()
        except Exception:
            pytest.fail("execute_pending_navigation应该处理无图片的情况")

    def test_handle_navigation_missing_operation_manager(self, navigation_controller):
        """测试缺少operation_manager时处理"""
        del navigation_controller.main_window.operation_manager
        navigation_controller.main_window.keep_current_image = MagicMock()
        
        mock_event = MagicMock()
        mock_event.characters.return_value = "\uf701"
        mock_event.modifierFlags.return_value = 0
        
        result = navigation_controller.handle_key_event(mock_event)
        
        assert result is True
        navigation_controller.main_window.keep_current_image.assert_called_once()


# ==================== 性能优化器集成测试 ====================


class TestPerformanceOptimizerIntegration:
    """测试性能优化器集成"""

    @patch('plookingII.ui.controllers.navigation_controller.NSTimer')
    @patch('plookingII.ui.controllers.navigation_controller.time.time')
    def test_adaptive_debounce_with_optimizer(self, mock_time, mock_timer, mock_window):
        """测试使用优化器的自适应防抖"""
        mock_time.return_value = 1000.0
        mock_timer_instance = MagicMock()
        mock_timer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_.return_value = mock_timer_instance
        
        with patch('plookingII.ui.controllers.navigation_controller.get_performance_optimizer') as mock_get:
            mock_optimizer = MagicMock()
            mock_optimizer.optimize_navigation.return_value = {"optimal_debounce_sec": 0.01, "navigation_velocity": 10}
            mock_get.return_value = mock_optimizer
            
            controller = NavigationController(mock_window)
            controller._last_index = 0
            controller._handle_navigation_key("right")
            
            # 应该调用优化器
            mock_optimizer.optimize_navigation.assert_called()

    @patch('plookingII.ui.controllers.navigation_controller.NSTimer')
    @patch('plookingII.ui.controllers.navigation_controller.time.time')
    def test_adaptive_debounce_optimizer_failure(self, mock_time, mock_timer, mock_window):
        """测试优化器失败时的回退"""
        mock_time.return_value = 1000.0
        mock_timer_instance = MagicMock()
        mock_timer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_.return_value = mock_timer_instance
        
        with patch('plookingII.ui.controllers.navigation_controller.get_performance_optimizer') as mock_get:
            mock_optimizer = MagicMock()
            mock_optimizer.optimize_navigation.side_effect = Exception("Optimizer failed")
            mock_get.return_value = mock_optimizer
            
            controller = NavigationController(mock_window)
            controller._last_index = 0
            
            # 应该不抛出异常，回退到原有逻辑
            try:
                controller._handle_navigation_key("right")
            except Exception:
                pytest.fail("应该处理优化器异常")


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    @patch('plookingII.ui.controllers.navigation_controller.NSTimer')
    @patch('plookingII.ui.controllers.navigation_controller.time.time')
    def test_complete_navigation_workflow(self, mock_time, mock_timer, navigation_controller):
        """测试完整导航工作流"""
        mock_time.return_value = 1000.0
        mock_timer_instance = MagicMock()
        mock_timer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_.return_value = mock_timer_instance
        
        # 1. 按右键
        mock_event = MagicMock()
        mock_event.characters.return_value = "\uf703"
        mock_event.modifierFlags.return_value = 0
        
        result = navigation_controller.handle_key_event(mock_event)
        assert result is True
        
        # 2. 执行待处理的导航
        navigation_controller._pending_navigation = "right"
        navigation_controller.execute_pending_navigation()
        
        # 3. 验证索引变化
        assert navigation_controller.main_window.current_index == 1

    def test_rapid_key_presses(self, navigation_controller):
        """测试快速按键"""
        navigation_controller._is_navigating = True
        
        # 快速按右键3次
        navigation_controller._handle_navigation_key("right")
        navigation_controller._handle_navigation_key("right")
        navigation_controller._handle_navigation_key("right")
        
        # 队列应该累积3步
        assert navigation_controller._queued_steps == 3

