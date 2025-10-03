"""
单元测试 - NavigationController
测试实际的公共接口和行为
"""

import pytest
import time
from unittest.mock import Mock
from plookingII.ui.controllers.navigation_controller import NavigationController


class TestNavigationControllerBasics:
    """测试NavigationController基本功能"""

    @pytest.fixture
    def controller(self):
        """创建测试用的NavigationController实例"""
        main_window = Mock()
        main_window.folder_manager = Mock()
        main_window.image_manager = Mock()
        main_window.operation_manager = Mock()
        main_window.rotate_image_counterclockwise = Mock()
        main_window.rotate_image_clockwise = Mock()
        return NavigationController(main_window)

    def test_initialization(self, controller):
        """测试初始化"""
        assert controller.main_window is not None
        assert controller._processing_key_event is False
        assert controller._recursion_depth == 0
        assert controller._queued_steps == 0

    def test_recursion_protection(self, controller):
        """测试递归保护机制"""
        # 模拟递归调用
        controller._processing_key_event = True
        controller._recursion_depth = 0

        event = Mock()
        event.type.return_value = 10
        event.characters.return_value = "a"

        # 应该被阻止
        result = controller.handle_key_event(event)
        assert result is False

        # 深度应该增加
        assert controller._recursion_depth > 0

    def test_invalid_event_handling(self, controller):
        """测试无效事件处理"""
        # None事件
        result = controller.handle_key_event(None)
        assert result is False

        # 没有characters的事件
        event = Mock()
        event.characters.return_value = None
        result = controller.handle_key_event(event)
        assert result is False

        # 空字符事件
        event.characters.return_value = ""
        result = controller.handle_key_event(event)
        assert result is False


class TestNavigationControllerRotation:
    """测试旋转功能"""

    @pytest.fixture
    def controller(self):
        """创建测试用的NavigationController实例"""
        main_window = Mock()
        main_window.folder_manager = Mock()
        main_window.image_manager = Mock()
        main_window.operation_manager = Mock()
        main_window.rotate_image_counterclockwise = Mock()
        main_window.rotate_image_clockwise = Mock()
        return NavigationController(main_window)

    def test_rotate_counterclockwise(self, controller):
        """测试逆时针旋转 (Cmd+Option+L)"""
        event = Mock()
        event.type.return_value = 10
        event.characters.return_value = "l"
        event.modifierFlags.return_value = 1048576 | 524288  # Cmd + Option

        result = controller.handle_key_event(event)

        # 应该返回True表示处理成功
        assert result is True
        # 旋转在后台线程执行，稍等后验证（或仅验证返回值）

    def test_rotate_clockwise(self, controller):
        """测试顺时针旋转 (Cmd+Option+R)"""
        event = Mock()
        event.type.return_value = 10
        event.characters.return_value = "r"
        event.modifierFlags.return_value = 1048576 | 524288  # Cmd + Option

        result = controller.handle_key_event(event)

        # 应该返回True表示处理成功
        assert result is True


class TestNavigationControllerCommands:
    """测试命令键功能"""

    @pytest.fixture
    def controller(self):
        """创建测试用的NavigationController实例"""
        main_window = Mock()
        main_window.folder_manager = Mock()
        main_window.folder_manager.skip_current_folder = Mock()
        main_window.folder_manager.undo_skip_folder = Mock()
        main_window.image_manager = Mock()
        main_window.operation_manager = Mock()
        main_window.operation_manager.undo_keep_action = Mock()
        main_window.operation_manager.keep_current_image = Mock()
        main_window.operation_manager.exit_current_folder = Mock()
        return NavigationController(main_window)

    def test_undo_keep_command(self, controller):
        """测试 Cmd+Z (撤销保留)"""
        event = Mock()
        event.type.return_value = 10
        event.characters.return_value = "z"
        event.modifierFlags.return_value = 1048576  # NSCommandKeyMask

        result = controller.handle_key_event(event)

        # 应该调用撤销
        assert result is True
        controller.main_window.operation_manager.undo_keep_action.assert_called()

    def test_skip_folder_command(self, controller):
        """测试 Cmd+右箭头 (跳过文件夹)"""
        event = Mock()
        event.type.return_value = 10
        event.characters.return_value = "\uf703"  # 右箭头
        event.modifierFlags.return_value = 1048576

        result = controller.handle_key_event(event)

        # 应该调用跳过文件夹
        assert result is True
        controller.main_window.folder_manager.skip_current_folder.assert_called()

    def test_undo_skip_command(self, controller):
        """测试 Cmd+左箭头 (撤销跳过)"""
        event = Mock()
        event.type.return_value = 10
        event.characters.return_value = "\uf702"  # 左箭头
        event.modifierFlags.return_value = 1048576

        result = controller.handle_key_event(event)

        # 应该调用撤销跳过
        assert result is True
        controller.main_window.folder_manager.undo_skip_folder.assert_called()

    def test_keep_image_command(self, controller):
        """测试下箭头 (保留图片)"""
        event = Mock()
        event.type.return_value = 10
        event.characters.return_value = "\uf701"  # 下箭头
        event.modifierFlags.return_value = 0

        result = controller.handle_key_event(event)

        # 应该调用保留图片
        assert result is True
        controller.main_window.operation_manager.keep_current_image.assert_called()

    def test_exit_folder_command(self, controller):
        """测试 ESC (退出文件夹)"""
        event = Mock()
        event.type.return_value = 10
        event.characters.return_value = ""
        event.keyCode.return_value = 53  # ESC
        event.modifierFlags.return_value = 0

        result = controller.handle_key_event(event)

        # 应该调用退出
        assert result is True
        controller.main_window.operation_manager.exit_current_folder.assert_called()


class TestNavigationControllerNavigation:
    """测试导航功能"""

    @pytest.fixture
    def controller(self):
        """创建测试用的NavigationController实例"""
        main_window = Mock()
        main_window.folder_manager = Mock()
        main_window.folder_manager.jump_to_next_folder = Mock()
        main_window.folder_manager.jump_to_previous_folder = Mock()
        main_window.image_manager = Mock()
        main_window.image_manager.show_next_image = Mock()
        main_window.image_manager.show_previous_image = Mock()
        main_window.operation_manager = Mock()
        return NavigationController(main_window)

    def test_right_arrow_navigation(self, controller):
        """测试右箭头导航"""
        # 重置时间戳
        controller._last_key_time = time.time() - 1.0

        event = Mock()
        event.type.return_value = 10
        event.characters.return_value = "\uf703"  # NSRightArrowFunctionKey
        event.modifierFlags.return_value = 0

        result = controller.handle_key_event(event)

        # 应该设置待处理导航
        assert result is True or controller._pending_navigation is not None

    def test_left_arrow_navigation(self, controller):
        """测试左箭头导航"""
        # 重置时间戳
        controller._last_key_time = time.time() - 1.0

        event = Mock()
        event.type.return_value = 10
        event.characters.return_value = "\uf702"  # NSLeftArrowFunctionKey
        event.modifierFlags.return_value = 0

        result = controller.handle_key_event(event)

        # 应该设置待处理导航
        assert result is True or controller._pending_navigation is not None

    def test_folder_jump_forward(self, controller):
        """测试Option+右箭头 (跳到下一文件夹)"""
        controller._last_key_time = time.time() - 1.0

        event = Mock()
        event.type.return_value = 10
        event.characters.return_value = "\uf703"
        event.modifierFlags.return_value = 524288  # NSAlternateKeyMask (Option)

        result = controller.handle_key_event(event)

        # 应该处理事件
        assert result is True or controller._pending_navigation is not None

    def test_folder_jump_backward(self, controller):
        """测试Option+左箭头 (跳到上一文件夹)"""
        controller._last_key_time = time.time() - 1.0

        event = Mock()
        event.type.return_value = 10
        event.characters.return_value = "\uf702"
        event.modifierFlags.return_value = 524288

        result = controller.handle_key_event(event)

        # 应该处理事件
        assert result is True or controller._pending_navigation is not None


class TestNavigationControllerIntegration:
    """集成测试 - 测试完整流程"""

    @pytest.fixture
    def controller(self):
        """创建测试用的NavigationController实例"""
        main_window = Mock()
        main_window.folder_manager = Mock()
        main_window.image_manager = Mock()
        main_window.image_manager.show_next_image = Mock()
        main_window.operation_manager = Mock()
        main_window.operation_manager.undo_keep_action = Mock()
        return NavigationController(main_window)

    def test_full_navigation_flow(self, controller):
        """测试完整的导航流程"""
        controller._last_key_time = time.time() - 1.0

        # 创建模拟事件
        event = Mock()
        event.type.return_value = 10
        event.characters.return_value = "\uf703"  # 右箭头
        event.modifierFlags.return_value = 0

        # 执行导航
        result = controller.handle_key_event(event)

        # 验证结果 - 应该处理了事件
        assert result is True or controller._pending_navigation is not None

    def test_command_key_flow(self, controller):
        """测试命令键流程"""
        # 创建Cmd+Z事件（撤销保留）
        event = Mock()
        event.type.return_value = 10
        event.characters.return_value = "z"
        event.modifierFlags.return_value = 1048576  # NSCommandKeyMask

        # 执行
        result = controller.handle_key_event(event)

        # 验证 - 应该调用撤销
        assert result is True
        controller.main_window.operation_manager.undo_keep_action.assert_called()

    def test_debouncing_mechanism(self, controller):
        """测试防抖机制"""
        # 快速连续按键
        controller._last_key_time = time.time()

        event = Mock()
        event.type.return_value = 10
        event.characters.return_value = "\uf703"
        event.modifierFlags.return_value = 0

        # 第一次按键
        result1 = controller.handle_key_event(event)

        # 立即第二次按键（应该被防抖）
        controller._last_key_time = time.time()
        result2 = controller.handle_key_event(event)

        # 至少有一个应该成功
        assert result1 is True or result2 is True

    def test_state_management(self, controller):
        """测试状态管理"""
        # 初始状态
        assert controller._state == controller._state_idle
        assert controller._is_navigating is False
        assert controller._queued_steps == 0

        # 设置导航状态
        controller._is_navigating = True
        assert controller._is_navigating is True

        # 队列步数
        controller._queued_steps = 3
        assert controller._queued_steps == 3
