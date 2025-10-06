#!/usr/bin/env python3
"""
图片更新状态管理器

负责监听当前显示图片的文件系统变化，并在图片被外部编辑时提供更新提示。

主要功能：
- 监听当前图片文件的修改、删除等事件
- 提供图片更新状态的视觉反馈
- 支持自动重新加载更新的图片
- 防抖机制避免频繁更新

Author: PlookingII Team
"""

import logging
import time
from collections.abc import Callable

from ...config.constants import APP_NAME
from ...core.file_watcher import FileChangeEvent, FileChangeType, FileWatcher
from ..utils.user_feedback import show_info, show_warning

logger = logging.getLogger(APP_NAME)


class ImageUpdateManager:
    """图片更新状态管理器

    监听当前图片文件的变化，提供更新提示和重载功能。
    """

    def __init__(self, main_window):
        """初始化图片更新管理器

        Args:
            main_window: MainWindow实例
        """
        self.main_window = main_window
        self.file_watcher = FileWatcher(strategy="auto")
        self.current_image_path: str | None = None
        self.update_pending = False
        self.last_update_time = 0
        self.debounce_delay = 1.0  # 防抖延迟（秒）

        # 设置文件变化回调
        self.file_watcher.add_callback(self._on_file_changed)

        # 更新状态回调
        self.update_callbacks: list[Callable[[str, bool], None]] = []

        logger.info("图片更新管理器已初始化")

    def add_update_callback(self, callback: Callable[[str, bool], None]):
        """添加更新状态回调

        Args:
            callback: 回调函数，接收 (image_path, has_update) 参数
        """
        if callback not in self.update_callbacks:
            self.update_callbacks.append(callback)

    def remove_update_callback(self, callback: Callable[[str, bool], None]):
        """移除更新状态回调"""
        if callback in self.update_callbacks:
            self.update_callbacks.remove(callback)

    def set_current_image(self, image_path: str):
        """设置当前监听的图片

        Args:
            image_path: 图片文件路径
        """
        try:
            # 停止监听之前的图片
            if self.current_image_path:
                self.file_watcher.unwatch_file(self.current_image_path)

            # 重置状态
            self.update_pending = False
            self.last_update_time = 0
            self.current_image_path = image_path

            # 开始监听新图片
            if image_path:
                self.file_watcher.watch_file(image_path)
                logger.debug(f"开始监听图片文件: {image_path}")

                # 通知状态回调
                self._notify_update_callbacks(image_path, False)

        except Exception as e:
            logger.error(f"设置当前监听图片失败: {e}")

    def clear_current_image(self):
        """清除当前监听的图片"""
        self.set_current_image(None)

    def _on_file_changed(self, event: FileChangeEvent):
        """处理文件变化事件

        Args:
            event: 文件变化事件
        """
        try:
            if event.file_path != self.current_image_path:
                return

            current_time = time.time()

            # 防抖处理
            if current_time - self.last_update_time < self.debounce_delay:
                return

            self.last_update_time = current_time

            if event.change_type == FileChangeType.MODIFIED:
                self._handle_file_modified(event)
            elif event.change_type == FileChangeType.DELETED:
                self._handle_file_deleted(event)
            elif event.change_type == FileChangeType.MOVED:
                self._handle_file_moved(event)

        except Exception as e:
            logger.error(f"处理文件变化事件失败: {e}")

    def _handle_file_modified(self, event: FileChangeEvent):
        """处理文件修改事件

        Args:
            event: 文件变化事件
        """
        logger.info(f"检测到图片文件被修改: {event.file_path}")

        # 标记为有更新
        self.update_pending = True

        # 通知状态回调
        self._notify_update_callbacks(event.file_path, True)

        # 显示更新提示（在主线程中执行）
        def show_update_notification():
            try:
                import os

                filename = os.path.basename(event.file_path)
                should_reload = show_warning(
                    "图片已更新", f'检测到图片 "{filename}" 已被外部程序修改。\n\n是否重新加载图片？'
                )

                if should_reload:
                    self.reload_current_image()

            except Exception as e:
                logger.error(f"显示更新通知失败: {e}")

        # 在主线程中显示通知
        self._schedule_main_thread(show_update_notification)

    def _handle_file_deleted(self, event: FileChangeEvent):
        """处理文件删除事件

        Args:
            event: 文件变化事件
        """
        logger.warning(f"检测到图片文件被删除: {event.file_path}")

        # 清除监听
        self.clear_current_image()

        # 显示删除通知
        def show_delete_notification():
            try:
                import os

                filename = os.path.basename(event.file_path)
                show_info("图片已删除", f'图片 "{filename}" 已被删除。')

                # 尝试导航到下一张图片
                if hasattr(self.main_window, "navigation_controller"):
                    self.main_window.navigation_controller._handle_navigation_key("right")

            except Exception as e:
                logger.error(f"显示删除通知失败: {e}")

        self._schedule_main_thread(show_delete_notification)

    def _handle_file_moved(self, event: FileChangeEvent):
        """处理文件移动事件

        Args:
            event: 文件变化事件
        """
        logger.info(f"检测到图片文件被移动: {event.old_path} -> {event.file_path}")

        # 更新监听路径
        self.current_image_path = event.file_path

        # 显示移动通知
        def show_move_notification():
            try:
                import os

                old_name = os.path.basename(event.old_path) if event.old_path else "未知"
                new_name = os.path.basename(event.file_path)
                show_info("图片已移动", f'图片已从 "{old_name}" 移动到 "{new_name}"。')

            except Exception as e:
                logger.error(f"显示移动通知失败: {e}")

        self._schedule_main_thread(show_move_notification)

    def reload_current_image(self):
        """重新加载当前图片"""
        try:
            if not self.current_image_path or not self.update_pending:
                return

            # 重置更新状态
            self.update_pending = False

            # 通知状态回调
            self._notify_update_callbacks(self.current_image_path, False)

            # 重新加载图片
            if hasattr(self.main_window, "image_manager"):
                # 清除相关缓存
                if hasattr(self.main_window.image_manager, "image_cache"):
                    try:
                        cache = self.main_window.image_manager.image_cache
                        if hasattr(cache, "remove"):
                            cache.remove(self.current_image_path)
                        elif hasattr(cache, "clear_image"):
                            cache.clear_image(self.current_image_path)
                    except Exception as e:
                        logger.debug(f"清除图片缓存失败: {e}")

                # 清除双向缓存池
                if hasattr(self.main_window.image_manager, "bidi_pool"):
                    try:
                        self.main_window.image_manager.bidi_pool.clear_image_cache(self.current_image_path)
                    except Exception as e:
                        logger.debug(f"清除双向缓存失败: {e}")

                # 重新显示当前图片
                self.main_window.image_manager.show_current_image()

                logger.info(f"已重新加载图片: {self.current_image_path}")

                # 显示成功消息
                def show_reload_success():
                    import os

                    filename = os.path.basename(self.current_image_path)
                    if hasattr(self.main_window, "status_bar_controller"):
                        self.main_window.status_bar_controller.set_status_message(f"已重新加载: {filename}")

                self._schedule_main_thread(show_reload_success)

        except Exception as e:
            logger.error(f"重新加载图片失败: {e}")

            def show_reload_error():
                show_info("重新加载失败", f"重新加载图片时发生错误: {e!s}")

            self._schedule_main_thread(show_reload_error)

    def _notify_update_callbacks(self, image_path: str, has_update: bool):
        """通知更新状态回调

        Args:
            image_path: 图片路径
            has_update: 是否有更新
        """
        for callback in self.update_callbacks:
            try:
                callback(image_path, has_update)
            except Exception as e:
                logger.error(f"更新状态回调执行失败: {e}")

    def _schedule_main_thread(self, func: Callable):
        """在主线程中执行函数

        Args:
            func: 要执行的函数
        """
        try:
            # 使用NSThread在主线程中执行
            from Foundation import NSThread

            if NSThread.isMainThread():
                func()
            else:
                NSThread.detachNewThreadSelector_toTarget_withObject_(
                    "performSelectorOnMainThread:withObject:waitUntilDone:",
                    self,
                    {"selector": func, "object": None, "wait": False},
                )
        except Exception:
            # 回退到直接执行
            func()

    def get_update_status(self) -> bool:
        """获取当前更新状态

        Returns:
            bool: 是否有待处理的更新
        """
        return self.update_pending

    def force_check_update(self):
        """强制检查当前图片的更新状态"""
        if not self.current_image_path:
            return

        try:
            import os

            if not os.path.exists(self.current_image_path):
                # 文件不存在，触发删除事件
                from ...core.file_watcher import FileChangeEvent, FileChangeType

                event = FileChangeEvent(
                    file_path=self.current_image_path, change_type=FileChangeType.DELETED, timestamp=time.time()
                )
                self._handle_file_deleted(event)

        except Exception as e:
            logger.error(f"强制检查更新失败: {e}")

    def cleanup(self):
        """清理资源"""
        try:
            self.file_watcher.stop()
            self.current_image_path = None
            self.update_pending = False
            self.update_callbacks.clear()
            logger.info("图片更新管理器已清理")
        except Exception as e:
            logger.error(f"清理图片更新管理器失败: {e}")
