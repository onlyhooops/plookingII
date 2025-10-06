"""
HistoryManager - 历史记录和进度管理服务

负责统一管理应用的历史记录和进度保存功能：
- 任务历史记录验证
- 历史恢复对话框管理
- 进度保存和恢复
- 异步进度保存

从 MainWindow 和 SystemController 中提取，遵循单一职责原则。
"""

import logging
import threading
import time
from typing import Any

from ..config.constants import APP_NAME
from ..core.history import TaskHistoryManager

logger = logging.getLogger(APP_NAME)

class HistoryManager:
    """
    历史记录和进度管理服务

    负责处理：
    1. 历史记录验证和校验
    2. 历史恢复对话框管理
    3. 进度数据的保存和恢复
    4. 异步进度保存机制
    """

    def __init__(self, window):
        """
        初始化历史管理器

        Args:
            window: 主窗口实例
        """
        self.window = window
        self._save_lock = threading.Lock()
        self._last_save_time = 0
        self._pending_save_data = None
        self._save_throttle_interval = 2.0  # 节流间隔（秒）

    # ==================== 历史记录验证 ====================

    def validate_history(self, history_data: dict[str, Any]) -> bool:
        """
        校验历史记录数据的有效性

        Args:
            history_data: 历史记录数据字典

        Returns:
            bool: 校验结果，True表示有效
        """
        try:
            if not history_data or not isinstance(history_data, dict):
                return False

            # 委托给folder_manager进行具体验证
            if (hasattr(self.window, "folder_manager") and
                self.window.folder_manager and
                hasattr(self.window.folder_manager, "_validate_task_history")):
                return self.window.folder_manager._validate_task_history(history_data)

            return False
        except Exception as e:
            logger.warning(f"校验历史记录失败: {e}")
            return False

    def validate_task_history(self, history_data: dict[str, Any]) -> bool:
        """
        校验任务历史记录（方法名别名）

        Args:
            history_data: 历史记录数据字典

        Returns:
            bool: 校验结果，True表示有效
        """
        return self.validate_history(history_data)

    # ==================== 历史恢复对话框 ====================

    def show_history_restore_dialog(self, history_data: dict[str, Any]) -> None:
        """
        显示历史恢复对话框

        向用户展示历史记录恢复选项，让用户选择是否恢复之前的浏览进度。

        Args:
            history_data: 历史记录数据字典
        """
        try:
            if not history_data:
                return

            # 委托给folder_manager处理具体的对话框显示
            if (hasattr(self.window, "folder_manager") and
                self.window.folder_manager and
                hasattr(self.window.folder_manager, "_show_task_history_restore_dialog")):
                self.window.folder_manager._show_task_history_restore_dialog(history_data)
        except Exception as e:
            logger.warning(f"显示历史恢复对话框失败: {e}")

    def show_task_history_restore_dialog(self, history_data: dict[str, Any]) -> None:
        """
        显示任务历史恢复对话框（方法名别名）

        Args:
            history_data: 历史记录数据字典
        """
        self.show_history_restore_dialog(history_data)

    # ==================== 进度保存管理 ====================

    def save_task_progress(self) -> None:
        """
        保存任务进度（异步节流版本）

        使用节流机制避免频繁保存，提高性能。
        """
        try:
            current_time = time.time()

            # 准备保存数据
            if hasattr(self.window, "subfolders") and hasattr(self.window, "current_subfolder_index"):
                save_data = {
                    "subfolders": getattr(self.window, "subfolders", []),
                    "current_subfolder_index": getattr(self.window, "current_subfolder_index", 0),
                    "current_index": getattr(self.window, "current_index", 0),
                    "timestamp": current_time
                }

                with self._save_lock:
                    self._pending_save_data = save_data

                    # 节流：如果距离上次保存时间太短，延迟保存
                    if current_time - self._last_save_time >= self._save_throttle_interval:
                        self._async_save_progress()
                        self._last_save_time = current_time

        except Exception as e:
            logger.warning(f"保存任务进度失败: {e}")

    def save_task_progress_immediate(self) -> None:
        """
        立即保存任务进度（同步版本）

        用于重要操作，确保数据立即写入。
        """
        try:
            if (hasattr(self.window, "folder_manager") and
                self.window.folder_manager and
                hasattr(self.window.folder_manager, "_save_task_progress_immediate")):
                self.window.folder_manager._save_task_progress_immediate()
        except Exception as e:
            logger.warning(f"立即保存任务进度失败: {e}")

    def async_save_progress(self) -> None:
        """
        异步保存进度数据

        在后台线程中执行保存操作，避免阻塞UI。
        """
        try:
            if (hasattr(self.window, "folder_manager") and
                self.window.folder_manager and
                hasattr(self.window.folder_manager, "_async_save_progress")):
                self.window.folder_manager._async_save_progress()
        except Exception as e:
            logger.warning(f"异步保存进度失败: {e}")

    def _async_save_progress(self) -> None:
        """
        内部异步保存实现

        在后台线程中执行实际的保存操作。
        """
        if not self._pending_save_data:
            return

        def save_worker():
            try:
                with self._save_lock:
                    save_data = self._pending_save_data
                    if not save_data:
                        return

                    # 获取TaskHistoryManager实例
                    task_history_manager = None
                    if (hasattr(self.window, "folder_manager") and
                        self.window.folder_manager and
                        hasattr(self.window.folder_manager, "task_history_manager")):
                        task_history_manager = self.window.folder_manager.task_history_manager

                    if task_history_manager:
                        task_history_manager.save_task_progress(save_data)
                        logger.debug("异步保存进度完成")

                    # 清除待保存数据
                    self._pending_save_data = None

            except Exception as e:
                logger.warning(f"异步保存进度工作线程失败: {e}")

        # 在后台线程中执行保存
        threading.Thread(target=save_worker, daemon=True).start()

    # ==================== 工具方法 ====================

    def get_task_history_manager(self) -> TaskHistoryManager | None:
        """
        获取任务历史管理器实例

        Returns:
            TaskHistoryManager: 任务历史管理器实例，如果不存在则返回None
        """
        try:
            if (hasattr(self.window, "folder_manager") and
                self.window.folder_manager and
                hasattr(self.window.folder_manager, "task_history_manager")):
                return self.window.folder_manager.task_history_manager
        except Exception as e:
            logger.debug(f"获取任务历史管理器失败: {e}")
        return None

    def is_history_available(self) -> bool:
        """
        检查历史记录功能是否可用

        Returns:
            bool: True表示历史记录功能可用
        """
        return self.get_task_history_manager() is not None

    def cleanup(self) -> None:
        """
        清理历史管理器资源

        在应用退出时调用，确保所有待保存的数据都被保存。
        """
        try:
            # 立即保存所有待保存的数据
            if self._pending_save_data:
                self.save_task_progress_immediate()

            logger.debug("历史管理器清理完成")
        except Exception as e:
            logger.warning(f"历史管理器清理失败: {e}")
