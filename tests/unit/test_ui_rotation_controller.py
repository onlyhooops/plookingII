"""
测试 ui/controllers/rotation_controller.py

测试图片旋转控制器的功能，包括：
- 初始化
- 顺时针旋转（各种场景）
- 逆时针旋转（各种场景）
- 状态消息设置
- 错误处理
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from plookingII.ui.controllers.rotation_controller import RotationController


@pytest.fixture
def mock_window():
    """创建模拟的主窗口"""
    window = MagicMock()
    window.operation_manager = MagicMock()
    window.status_bar_controller = MagicMock()
    window.images = ["image1.jpg", "image2.jpg", "image3.jpg"]
    window.current_index = 0
    return window


@pytest.fixture
def rotation_controller(mock_window):
    """创建RotationController实例"""
    return RotationController(mock_window)


# ==================== 初始化测试 ====================


class TestRotationControllerInit:
    """测试RotationController初始化"""

    def test_init_basic(self, mock_window):
        """测试基本初始化"""
        controller = RotationController(mock_window)
        
        assert controller.window == mock_window

    def test_init_with_real_window(self):
        """测试使用真实窗口对象初始化"""
        window = MagicMock()
        controller = RotationController(window)
        
        assert controller.window is window


# ==================== 顺时针旋转测试 ====================


class TestRotateClockwise:
    """测试顺时针旋转"""

    def test_rotate_clockwise_success(self, rotation_controller, mock_window):
        """测试成功顺时针旋转"""
        rotation_controller.rotate_clockwise()
        
        # 验证调用了operation_manager的rotate_current_image方法
        mock_window.operation_manager.rotate_current_image.assert_called_once_with("clockwise")

    def test_rotate_clockwise_no_operation_manager(self, rotation_controller, mock_window):
        """测试operation_manager未初始化"""
        del mock_window.operation_manager
        
        rotation_controller.rotate_clockwise()
        
        # 不应该抛出异常

    def test_rotate_clockwise_operation_manager_none(self, rotation_controller, mock_window):
        """测试operation_manager为None"""
        mock_window.operation_manager = None
        
        rotation_controller.rotate_clockwise()
        
        # 不应该抛出异常

    def test_rotate_clockwise_no_images(self, rotation_controller, mock_window):
        """测试没有图像列表"""
        del mock_window.images
        
        rotation_controller.rotate_clockwise()
        
        # 应该调用设置状态消息
        mock_window.status_bar_controller.set_status_message.assert_called_with("没有可旋转的图像")

    def test_rotate_clockwise_empty_images(self, rotation_controller, mock_window):
        """测试空图像列表"""
        mock_window.images = []
        
        rotation_controller.rotate_clockwise()
        
        # 应该调用设置状态消息
        mock_window.status_bar_controller.set_status_message.assert_called_with("没有可旋转的图像")

    def test_rotate_clockwise_index_out_of_range(self, rotation_controller, mock_window):
        """测试当前索引超出范围"""
        mock_window.current_index = 10  # 超出images列表长度
        
        rotation_controller.rotate_clockwise()
        
        # 应该调用设置状态消息
        mock_window.status_bar_controller.set_status_message.assert_called_with("没有可旋转的图像")

    def test_rotate_clockwise_with_valid_image(self, rotation_controller, mock_window):
        """测试旋转有效图像"""
        mock_window.current_index = 1
        
        rotation_controller.rotate_clockwise()
        
        # 验证使用正确的方向参数
        mock_window.operation_manager.rotate_current_image.assert_called_with("clockwise")

    def test_rotate_clockwise_exception_handling(self, rotation_controller, mock_window):
        """测试旋转异常处理"""
        mock_window.operation_manager.rotate_current_image.side_effect = Exception("Rotation failed")
        
        rotation_controller.rotate_clockwise()
        
        # 应该调用设置状态消息
        mock_window.status_bar_controller.set_status_message.assert_called_with("旋转操作失败")


# ==================== 逆时针旋转测试 ====================


class TestRotateCounterclockwise:
    """测试逆时针旋转"""

    def test_rotate_counterclockwise_success(self, rotation_controller, mock_window):
        """测试成功逆时针旋转"""
        rotation_controller.rotate_counterclockwise()
        
        # 验证调用了operation_manager的rotate_current_image方法
        mock_window.operation_manager.rotate_current_image.assert_called_once_with("counterclockwise")

    def test_rotate_counterclockwise_no_operation_manager(self, rotation_controller, mock_window):
        """测试operation_manager未初始化"""
        del mock_window.operation_manager
        
        rotation_controller.rotate_counterclockwise()
        
        # 不应该抛出异常

    def test_rotate_counterclockwise_operation_manager_none(self, rotation_controller, mock_window):
        """测试operation_manager为None"""
        mock_window.operation_manager = None
        
        rotation_controller.rotate_counterclockwise()
        
        # 不应该抛出异常

    def test_rotate_counterclockwise_no_images(self, rotation_controller, mock_window):
        """测试没有图像列表"""
        del mock_window.images
        
        rotation_controller.rotate_counterclockwise()
        
        # 应该调用设置状态消息
        mock_window.status_bar_controller.set_status_message.assert_called_with("没有可旋转的图像")

    def test_rotate_counterclockwise_empty_images(self, rotation_controller, mock_window):
        """测试空图像列表"""
        mock_window.images = []
        
        rotation_controller.rotate_counterclockwise()
        
        # 应该调用设置状态消息
        mock_window.status_bar_controller.set_status_message.assert_called_with("没有可旋转的图像")

    def test_rotate_counterclockwise_index_out_of_range(self, rotation_controller, mock_window):
        """测试当前索引超出范围"""
        mock_window.current_index = 10  # 超出images列表长度
        
        rotation_controller.rotate_counterclockwise()
        
        # 应该调用设置状态消息
        mock_window.status_bar_controller.set_status_message.assert_called_with("没有可旋转的图像")

    def test_rotate_counterclockwise_with_valid_image(self, rotation_controller, mock_window):
        """测试旋转有效图像"""
        mock_window.current_index = 2
        
        rotation_controller.rotate_counterclockwise()
        
        # 验证使用正确的方向参数
        mock_window.operation_manager.rotate_current_image.assert_called_with("counterclockwise")

    def test_rotate_counterclockwise_exception_handling(self, rotation_controller, mock_window):
        """测试旋转异常处理"""
        mock_window.operation_manager.rotate_current_image.side_effect = Exception("Rotation failed")
        
        rotation_controller.rotate_counterclockwise()
        
        # 应该调用设置状态消息
        mock_window.status_bar_controller.set_status_message.assert_called_with("旋转操作失败")


# ==================== 状态消息设置测试 ====================


class TestSetStatusMessage:
    """测试设置状态消息"""

    def test_set_status_message_success(self, rotation_controller, mock_window):
        """测试成功设置状态消息"""
        rotation_controller._set_status_message("测试消息")
        
        mock_window.status_bar_controller.set_status_message.assert_called_once_with("测试消息")

    def test_set_status_message_no_status_bar(self, rotation_controller, mock_window):
        """测试没有status_bar_controller"""
        del mock_window.status_bar_controller
        
        # 不应该抛出异常
        rotation_controller._set_status_message("测试消息")

    def test_set_status_message_status_bar_none(self, rotation_controller, mock_window):
        """测试status_bar_controller为None"""
        mock_window.status_bar_controller = None
        
        # 不应该抛出异常
        rotation_controller._set_status_message("测试消息")

    def test_set_status_message_exception_handling(self, rotation_controller, mock_window):
        """测试设置消息异常处理"""
        mock_window.status_bar_controller.set_status_message.side_effect = Exception("Status bar error")
        
        # 不应该抛出异常
        rotation_controller._set_status_message("测试消息")

    def test_set_status_message_empty_string(self, rotation_controller, mock_window):
        """测试空字符串消息"""
        rotation_controller._set_status_message("")
        
        mock_window.status_bar_controller.set_status_message.assert_called_once_with("")

    def test_set_status_message_long_string(self, rotation_controller, mock_window):
        """测试超长字符串消息"""
        long_message = "A" * 1000
        rotation_controller._set_status_message(long_message)
        
        mock_window.status_bar_controller.set_status_message.assert_called_once_with(long_message)


# ==================== 边缘情况测试 ====================


class TestEdgeCases:
    """测试边缘情况"""

    def test_rotate_with_negative_index(self, rotation_controller, mock_window):
        """测试负索引"""
        mock_window.current_index = -1
        
        # 负索引在Python中有效，但应该小于列表长度
        rotation_controller.rotate_clockwise()
        
        # 应该成功调用（Python支持负索引）
        assert mock_window.operation_manager.rotate_current_image.called

    def test_rotate_with_zero_index(self, rotation_controller, mock_window):
        """测试索引为0"""
        mock_window.current_index = 0
        
        rotation_controller.rotate_clockwise()
        
        mock_window.operation_manager.rotate_current_image.assert_called_with("clockwise")

    def test_rotate_last_image(self, rotation_controller, mock_window):
        """测试旋转最后一张图片"""
        mock_window.current_index = len(mock_window.images) - 1
        
        rotation_controller.rotate_clockwise()
        
        mock_window.operation_manager.rotate_current_image.assert_called_with("clockwise")

    def test_rotate_both_directions_sequentially(self, rotation_controller, mock_window):
        """测试连续不同方向旋转"""
        rotation_controller.rotate_clockwise()
        rotation_controller.rotate_counterclockwise()
        
        # 验证两次调用
        assert mock_window.operation_manager.rotate_current_image.call_count == 2

    def test_rotate_multiple_times_same_direction(self, rotation_controller, mock_window):
        """测试多次同方向旋转"""
        for _ in range(5):
            rotation_controller.rotate_clockwise()
        
        assert mock_window.operation_manager.rotate_current_image.call_count == 5

    def test_window_images_modified_during_rotation(self, rotation_controller, mock_window):
        """测试旋转过程中图像列表被修改"""
        def modify_images(*args):
            mock_window.images = []
        
        mock_window.operation_manager.rotate_current_image.side_effect = modify_images
        
        # 不应该抛出异常
        rotation_controller.rotate_clockwise()

    def test_window_has_images_attr_false(self, rotation_controller, mock_window):
        """测试window有images属性但值为False"""
        mock_window.images = False
        
        rotation_controller.rotate_clockwise()
        
        # 应该调用设置状态消息
        mock_window.status_bar_controller.set_status_message.assert_called()

    def test_window_has_images_attr_none(self, rotation_controller, mock_window):
        """测试window有images属性但值为None"""
        mock_window.images = None
        
        rotation_controller.rotate_clockwise()
        
        # 应该调用设置状态消息
        mock_window.status_bar_controller.set_status_message.assert_called()


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    def test_complete_rotation_workflow(self, rotation_controller, mock_window):
        """测试完整旋转工作流"""
        # 旋转第一张
        rotation_controller.rotate_clockwise()
        
        # 切换到第二张
        mock_window.current_index = 1
        rotation_controller.rotate_counterclockwise()
        
        # 切换到第三张
        mock_window.current_index = 2
        rotation_controller.rotate_clockwise()
        
        # 验证所有调用
        assert mock_window.operation_manager.rotate_current_image.call_count == 3

    def test_error_recovery_workflow(self, rotation_controller, mock_window):
        """测试错误恢复工作流"""
        # 第一次旋转失败
        mock_window.operation_manager.rotate_current_image.side_effect = Exception("First fail")
        rotation_controller.rotate_clockwise()
        
        # 第二次旋转成功
        mock_window.operation_manager.rotate_current_image.side_effect = None
        rotation_controller.rotate_clockwise()
        
        # 验证两次都调用了
        assert mock_window.operation_manager.rotate_current_image.call_count == 2

    def test_rotation_without_status_bar(self, mock_window):
        """测试没有status_bar的完整流程"""
        del mock_window.status_bar_controller
        controller = RotationController(mock_window)
        
        # 成功旋转
        controller.rotate_clockwise()
        mock_window.operation_manager.rotate_current_image.assert_called()
        
        # 失败旋转（没有图像）
        mock_window.images = []
        controller.rotate_counterclockwise()
        
        # 不应该抛出异常

    def test_rotation_with_various_image_counts(self, mock_window):
        """测试不同数量的图像列表"""
        controller = RotationController(mock_window)
        
        # 1张图像
        mock_window.images = ["img1.jpg"]
        mock_window.current_index = 0
        controller.rotate_clockwise()
        
        # 10张图像
        mock_window.images = [f"img{i}.jpg" for i in range(10)]
        mock_window.current_index = 5
        controller.rotate_counterclockwise()
        
        # 100张图像
        mock_window.images = [f"img{i}.jpg" for i in range(100)]
        mock_window.current_index = 50
        controller.rotate_clockwise()
        
        # 所有调用都应该成功
        assert mock_window.operation_manager.rotate_current_image.call_count == 3


# ==================== 并发测试 ====================


class TestConcurrency:
    """测试并发场景（虽然controller本身不是线程安全的）"""

    def test_rapid_rotation_calls(self, rotation_controller, mock_window):
        """测试快速连续调用"""
        for _ in range(100):
            rotation_controller.rotate_clockwise()
        
        assert mock_window.operation_manager.rotate_current_image.call_count == 100

    def test_alternating_rotations(self, rotation_controller, mock_window):
        """测试交替旋转"""
        for _ in range(50):
            rotation_controller.rotate_clockwise()
            rotation_controller.rotate_counterclockwise()
        
        assert mock_window.operation_manager.rotate_current_image.call_count == 100

