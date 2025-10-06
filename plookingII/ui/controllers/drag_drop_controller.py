"""
拖拽控制器

负责处理窗口的拖拽功能，包括：
- 拖拽进入/离开/更新事件
- 文件夹验证（同步/异步）
- 拖拽反馈和视觉效果
"""

import logging
import os
import threading

from AppKit import (
    NSDragOperationCopy,
    NSDragOperationNone,
    NSFilenamesPboardType,
)

from ...config.constants import APP_NAME, SUPPORTED_IMAGE_EXTS
from ...core.error_handling import DragDropError, FolderValidationError
from ...utils.file_utils import FileUtils
from ..utils.user_feedback import show_error

logger = logging.getLogger(APP_NAME)


class DragDropController:
    """
    拖拽控制器

    负责处理窗口的拖拽接收功能，包括验证、反馈和执行。

    Attributes:
        window: 主窗口引用
        _drag_validation_cache: 文件夹验证缓存
        _drag_validation_timer: 异步验证定时器
        _last_drag_path: 上次拖拽的路径
    """

    def __init__(self, window):
        """
        初始化拖拽控制器

        Args:
            window: 主窗口实例
        """
        self.window = window
        self._drag_validation_cache: dict[str, bool] = {}
        self._drag_validation_timer: threading.Timer | None = None
        self._last_drag_path: str | None = None
        logger.debug("拖拽控制器已初始化")

    def setup(self):
        """
        设置拖拽接收功能

        启用窗口的拖拽接收功能，支持用户拖拽文件夹到窗口进行照片浏览。
        """
        try:
            # 注册接受的拖拽类型
            self.window.registerForDraggedTypes_([NSFilenamesPboardType])
            logger.debug("拖拽接收功能已启用")
        except Exception as e:
            logger.warning(f"设置拖拽接收功能失败: {e}")

    def dragging_entered(self, sender):
        """
        拖拽进入窗口时的处理（优化版本）

        使用缓存和异步验证来避免UI卡顿。

        Args:
            sender: 拖拽信息对象

        Returns:
            NSDragOperation: 拖拽操作类型
        """
        try:
            # 获取拖拽的文件路径
            pasteboard = sender.draggingPasteboard()
            filenames = pasteboard.propertyListForType_(NSFilenamesPboardType)

            if not filenames or len(filenames) == 0:
                return NSDragOperationNone

            # 快速检查第一个有效的文件夹
            for filename in filenames:
                if os.path.isdir(filename):
                    self._last_drag_path = filename

                    # 检查缓存
                    if filename in self._drag_validation_cache:
                        cached_result = self._drag_validation_cache[filename]
                        if cached_result:
                            self._show_drag_feedback(filename)
                            return NSDragOperationCopy
                        return NSDragOperationNone

                    # 快速预检查：只检查文件夹根目录的前几个文件
                    if self._quick_folder_check(filename):
                        self._drag_validation_cache[filename] = True
                        self._show_drag_feedback(filename)

                        # 启动异步深度验证
                        self._start_async_validation(filename)
                        return NSDragOperationCopy
                    # 启动异步验证，但先返回None
                    self._start_async_validation(filename)
                    return NSDragOperationNone

            return NSDragOperationNone

        except DragDropError as e:
            logger.warning(f"拖拽验证失败: {e}")
            return NSDragOperationNone
        except Exception as e:
            logger.error(f"拖拽进入处理异常: {e}")
            return NSDragOperationNone

    def dragging_updated(self, sender):
        """
        拖拽在窗口内移动时的处理（优化版本）

        避免重复验证，直接使用缓存结果。

        Args:
            sender: 拖拽信息对象

        Returns:
            NSDragOperation: 拖拽操作类型
        """
        try:
            # 如果有上次的拖拽路径，直接使用缓存结果
            if self._last_drag_path and self._last_drag_path in self._drag_validation_cache:
                return NSDragOperationCopy if self._drag_validation_cache[self._last_drag_path] else NSDragOperationNone

            # 否则进行轻量级检查
            pasteboard = sender.draggingPasteboard()
            filenames = pasteboard.propertyListForType_(NSFilenamesPboardType)

            if filenames and len(filenames) > 0:
                for filename in filenames:
                    if os.path.isdir(filename):
                        if filename == self._last_drag_path:
                            # 路径相同，等待异步验证结果
                            return (
                                NSDragOperationCopy
                                if self._drag_validation_cache.get(filename, False)
                                else NSDragOperationNone
                            )
                        # 路径变化，重新验证
                        return self.dragging_entered(sender)

            return NSDragOperationNone

        except Exception as e:
            logger.warning(f"拖拽更新处理失败: {e}")
            return NSDragOperationNone

    def dragging_exited(self, sender):
        """
        拖拽离开窗口时的处理（优化版本）

        清除视觉反馈和异步验证任务。

        Args:
            sender: 拖拽信息对象
        """
        try:
            # 清除拖拽高亮效果
            if hasattr(self.window, "image_view") and self.window.image_view:
                if hasattr(self.window.image_view, "setDragHighlight_"):
                    self.window.image_view.setDragHighlight_(False)

            # 清除状态消息
            if hasattr(self.window, "status_bar_controller") and self.window.status_bar_controller:
                self.window.status_bar_controller.clear_status_message()

            # 取消异步验证
            self._cancel_async_validation()

            # 清除当前拖拽路径
            self._last_drag_path = None

        except Exception as e:
            logger.warning(f"拖拽退出处理失败: {e}")

    def perform_drag_operation(self, sender):
        """
        执行拖拽操作

        当用户松开鼠标完成拖拽时调用，处理拖拽的文件夹并开始照片浏览。

        Args:
            sender: 拖拽信息对象

        Returns:
            bool: 操作是否成功
        """
        try:
            # 获取拖拽的文件路径
            pasteboard = sender.draggingPasteboard()
            filenames = pasteboard.propertyListForType_(NSFilenamesPboardType)

            if not filenames or len(filenames) == 0:
                return False

            # 查找第一个有效的图片文件夹
            valid_folder = None
            for filename in filenames:
                if os.path.isdir(filename) and self._folder_contains_images(filename):
                    valid_folder = filename
                    break

            if not valid_folder:
                # 清除拖拽高亮效果
                self._clear_drag_highlight()

                # 使用友好的错误提示
                error = DragDropError("拖拽的文件夹中未找到支持的图片文件")
                show_error(error, "拖拽文件夹验证")
                return False

            logger.info(f"通过拖拽打开文件夹: {valid_folder}")

            # 保存当前任务进度
            self.window.folder_manager._save_task_progress_immediate()

            # 保存到最近打开记录
            self.window.operation_manager._save_last_dir(valid_folder)
            self.window.folder_manager.add_recent_folder(valid_folder)

            # 更新最近菜单（如果window有这个方法）
            if hasattr(self.window, "updateRecentMenu_"):
                self.window.updateRecentMenu_()

            # 加载文件夹图片
            self.window.folder_manager.load_images_from_root(valid_folder)

            # 清除拖拽高亮效果
            self._clear_drag_highlight()

            # 显示成功消息
            folder_name = os.path.basename(valid_folder)
            self.window.status_bar_controller.set_status_message(f"已打开文件夹: {folder_name}")

            return True

        except Exception as e:
            # 清除拖拽高亮效果
            self._clear_drag_highlight()

            # 使用友好的错误提示
            if isinstance(e, (DragDropError, FolderValidationError)):
                show_error(e, "拖拽操作")
            else:
                error = DragDropError(f"拖拽操作失败: {e!s}")
                show_error(error, "拖拽操作")

            logger.error(f"拖拽操作执行失败: {e}")
            return False

    def _clear_drag_highlight(self):
        """清除拖拽高亮效果"""
        if hasattr(self.window, "image_view") and self.window.image_view:
            if hasattr(self.window.image_view, "setDragHighlight_"):
                self.window.image_view.setDragHighlight_(False)

    def _folder_contains_images(self, folder_path: str) -> bool:
        """
        检查文件夹是否包含支持的图片文件

        Args:
            folder_path: 文件夹路径

        Returns:
            bool: 是否包含图片文件

        Raises:
            FolderValidationError: 文件夹访问失败
        """
        return FileUtils.folder_contains_images(folder_path, recursive_depth=1)

    def _quick_folder_check(self, folder_path: str) -> bool:
        """
        快速检查文件夹（仅检查前几个文件）

        Args:
            folder_path: 文件夹路径

        Returns:
            bool: 是否可能包含图片
        """
        try:
            # 快速检查：只检查前10个文件
            count = 0
            for filename in os.listdir(folder_path):
                if filename.lower().endswith(SUPPORTED_IMAGE_EXTS):
                    return True

                count += 1
                if count >= 10:
                    break

            return False

        except Exception as e:
            logger.debug(f"快速文件夹检查失败: {e}")
            return False

    def _show_drag_feedback(self, folder_path: str):
        """
        显示拖拽反馈

        Args:
            folder_path: 文件夹路径
        """
        try:
            # 设置拖拽高亮效果
            if hasattr(self.window, "image_view") and self.window.image_view:
                if hasattr(self.window.image_view, "setDragHighlight_"):
                    self.window.image_view.setDragHighlight_(True)

            # 显示状态消息
            folder_name = os.path.basename(folder_path)
            if hasattr(self.window, "status_bar_controller") and self.window.status_bar_controller:
                self.window.status_bar_controller.set_status_message(f"准备打开: {folder_name}")

        except Exception as e:
            logger.debug(f"显示拖拽反馈失败: {e}")

    def _start_async_validation(self, folder_path: str):
        """
        启动异步文件夹验证

        Args:
            folder_path: 文件夹路径
        """
        # 取消之前的验证
        self._cancel_async_validation()

        def async_validate():
            """异步验证文件夹"""
            try:
                result = self._folder_contains_images(folder_path)
                self._drag_validation_cache[folder_path] = result

                if not result:
                    logger.debug(f"异步验证失败: {folder_path}")

            except Exception as e:
                logger.debug(f"异步验证异常: {e}")
                self._drag_validation_cache[folder_path] = False

        # 启动异步验证
        self._drag_validation_timer = threading.Timer(0.1, async_validate)
        self._drag_validation_timer.daemon = True
        self._drag_validation_timer.start()

    def _cancel_async_validation(self):
        """取消异步验证"""
        if self._drag_validation_timer and self._drag_validation_timer.is_alive():
            self._drag_validation_timer.cancel()
            self._drag_validation_timer = None

    def shutdown(self):
        """关闭控制器，清理资源"""
        self._cancel_async_validation()
        self._drag_validation_cache.clear()
        logger.debug("拖拽控制器已关闭")
