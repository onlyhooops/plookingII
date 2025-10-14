"""
RotationController - 图片旋转控制器

负责处理图片旋转功能：
- 顺时针旋转（向右旋转90°）
- 逆时针旋转（向左旋转90°）
- 旋转状态验证和错误处理

从 MainWindow 中提取，遵循单一职责原则。
"""

import logging

from ...config.constants import APP_NAME

logger = logging.getLogger(APP_NAME)


class RotationController:
    """
    图片旋转控制器

    负责处理：
    1. 顺时针旋转（向右旋转90°）
    2. 逆时针旋转（向左旋转90°）
    3. 旋转前的状态验证
    4. 旋转操作的错误处理
    """

    def __init__(self, window):
        """
        初始化旋转控制器

        Args:
            window: 主窗口实例
        """
        self.window = window
        logger.debug("RotationController 初始化完成")

    def rotate_clockwise(self):
        """
        向右旋转90°

        执行顺时针旋转操作，包括状态验证和错误处理。
        """
        try:
            logger.debug("开始执行向右旋转操作")

            # 检查必要的组件是否已初始化
            if not hasattr(self.window, "operation_manager") or not self.window.operation_manager:
                logger.warning("操作管理器未初始化，无法执行旋转操作")
                return

            if not hasattr(self.window, "images") or not self.window.images:
                logger.debug("没有图像列表，无法执行旋转操作")
                self._set_status_message("没有可旋转的图像")
                return

            if self.window.current_index >= len(self.window.images):
                logger.debug("当前索引%s超出图像列表长度{len(self.window.images)}", self.window.current_index)
                self._set_status_message("没有可旋转的图像")
                return

            logger.debug("准备旋转图像: %s", self.window.images[self.window.current_index])
            self.window.operation_manager.rotate_current_image("clockwise")
            logger.debug("向右旋转操作已启动")
        except Exception as e:
            logger.exception("向右旋转失败: %s", e)
            self._set_status_message("旋转操作失败")

    def rotate_counterclockwise(self):
        """
        向左旋转90°

        执行逆时针旋转操作，包括状态验证和错误处理。
        """
        try:
            logger.debug("开始执行向左旋转操作")

            # 检查必要的组件是否已初始化
            if not hasattr(self.window, "operation_manager") or not self.window.operation_manager:
                logger.warning("操作管理器未初始化，无法执行旋转操作")
                return

            if not hasattr(self.window, "images") or not self.window.images:
                logger.debug("没有图像列表，无法执行旋转操作")
                self._set_status_message("没有可旋转的图像")
                return

            if self.window.current_index >= len(self.window.images):
                logger.debug("当前索引%s超出图像列表长度{len(self.window.images)}", self.window.current_index)
                self._set_status_message("没有可旋转的图像")
                return

            logger.debug("准备旋转图像: %s", self.window.images[self.window.current_index])
            self.window.operation_manager.rotate_current_image("counterclockwise")
            logger.debug("向左旋转操作已启动")
        except Exception as e:
            logger.exception("向左旋转失败: %s", e)
            self._set_status_message("旋转操作失败")

    def _set_status_message(self, message: str):
        """
        设置状态消息的辅助方法

        Args:
            message: 要显示的状态消息
        """
        try:
            if hasattr(self.window, "status_bar_controller") and self.window.status_bar_controller:
                self.window.status_bar_controller.set_status_message(message)
        except Exception as e:
            logger.debug("设置状态消息失败: %s", e)
