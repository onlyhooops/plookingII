"""
菜单控制器

负责处理应用程序的菜单相关操作：
- 最近文件菜单构建和更新
- 关于对话框
- 快捷键说明对话框
- 最近文件打开和清空
"""

import logging
import os

from AppKit import (
    NSAlert,
    NSMenu,
    NSMenuItem,
    NSTimer,
    NSWorkspace,
)

from ...config.constants import APP_NAME, AUTHOR, COPYRIGHT, VERSION
from ...config.ui_strings import get_ui_string_manager
from ...imports import logging, os
from ...utils.file_utils import FileUtils

logger = logging.getLogger(APP_NAME)

class MenuController:
    """
    菜单控制器

    管理应用程序的菜单系统，包括：
    1. 最近文件菜单的构建和更新
    2. 对话框（关于、快捷键）
    3. 最近文件操作（打开、清空）

    Attributes:
        window: MainWindow 窗口实例
    """

    def __init__(self, window):
        """
        初始化菜单控制器

        Args:
            window: MainWindow 窗口实例
        """
        self.window = window
        logger.debug("MenuController 初始化完成")

    # ==================== 对话框方法 ====================

    def show_about(self, sender):
        """
        显示关于对话框

        展示应用程序的基本信息，包括版本、开发者、版权等。

        Args:
            sender: 菜单项对象
        """
        try:
            ui_strings = get_ui_string_manager()

            alert = NSAlert.alloc().init()
            alert.setMessageText_(APP_NAME)

            # 使用统一文案管理器获取关于对话框内容
            about_text = ui_strings.get_about_dialog_text(VERSION, AUTHOR, COPYRIGHT)
            alert.setInformativeText_(about_text)

            # 使用统一按钮文案
            alert.addButtonWithTitle_(ui_strings.get("buttons", "ok", "确定"))

            # 优先使用sheet模式，失败时回退到modal模式
            try:
                alert.beginSheetModalForWindow_completionHandler_(self.window, lambda resp: None)
            except Exception:
                alert.runModal()
        except Exception as e:
            logger.warning(f"显示关于对话框失败: {e}")

    def show_shortcuts(self, sender):
        """
        显示快捷键说明

        展示应用程序支持的所有快捷键操作说明。

        Args:
            sender: 菜单项对象
        """
        try:
            ui_strings = get_ui_string_manager()

            alert = NSAlert.alloc().init()
            alert.setMessageText_(ui_strings.get('shortcuts_help', 'title', '快捷键'))

            # 使用统一文案管理器获取快捷键帮助内容
            shortcuts_text = ui_strings.get_shortcuts_help_text()
            alert.setInformativeText_(shortcuts_text)

            # 使用统一按钮文案
            alert.addButtonWithTitle_(ui_strings.get("buttons", "ok", "确定"))

            # 优先使用sheet模式，失败时回退到modal模式
            try:
                alert.beginSheetModalForWindow_completionHandler_(self.window, lambda resp: None)
            except Exception:
                alert.runModal()
        except Exception as e:
            logger.warning(f"显示快捷键说明失败: {e}")

    # ==================== 最近文件菜单构建 ====================

    def build_recent_menu(self, sender):
        """
        构建最近文件菜单

        创建包含最近打开文件列表的菜单，支持快速访问和清空操作。

        Args:
            sender: 菜单项对象

        Returns:
            NSMenu: 构建的菜单对象
        """
        try:
            menu = NSMenu.alloc().initWithTitle_("最近打开文件")
            # 清空操作
            clearItem = (
                NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("清空最近记录", "clearRecentFiles:", "")
            )
            clearItem.setTarget_(self.window)
            menu.addItem_(clearItem)
            menu.addItem_(NSMenuItem.separatorItem())
            # 文件项
            current_path = self.window.root_folder if hasattr(self.window, "root_folder") else None
            recent_list = self.window.folder_manager.get_recent_folders()
            logger.debug(f"构建最近文件菜单，获取到 {len(recent_list)} 个路径")

            for path in recent_list:
                logger.debug(f"处理最近文件夹路径: {path}")

                # 双重验证：确保路径有效且是文件夹
                if not os.path.exists(path) or not os.path.isdir(path):
                    logger.debug(f"跳过无效路径: {path}")
                    continue

                # 排除精选文件夹
                folder_name = os.path.basename(path.rstrip(os.sep))
                if folder_name.endswith(" 精选") or folder_name == "精选":
                    logger.debug(f"跳过精选文件夹: {path}")
                    continue

                name = os.path.basename(path)
                item = (
                    NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(name, "openRecentFile:", "")
                )
                item.setTarget_(self.window)
                item.setRepresentedObject_(path)
                item.setToolTip_(path)

                try:
                    icon = NSWorkspace.sharedWorkspace().iconForFile_(path)
                    icon.setSize_((16, 16))
                    item.setImage_(icon)
                except Exception:
                    # 图标获取失败时跳过设置，使用默认图标
                    pass

                if current_path and path == current_path:
                    item.setState_(1)
                menu.addItem_(item)
            return menu
        except Exception as e:
            logger.warning(f"构建最近文件菜单失败: {e}")
            return NSMenu.alloc().initWithTitle_("最近打开文件")

    def update_recent_menu(self, sender=None):
        """
        动态更新最近打开文件夹菜单

        当最近文件列表发生变化时，重新构建菜单内容。

        Args:
            sender: 菜单项对象（可选）
        """
        try:
            if hasattr(self.window, "recent_menu_item") and self.window.recent_menu_item:
                # 重新构建菜单内容
                new_menu = self.build_recent_menu(None)
                self.window.recent_menu_item.setSubmenu_(new_menu)
        except Exception as e:
            logger.warning(f"更新最近文件菜单失败: {e}")

    def initialize_recent_menu(self, timer):
        """
        初始化最近打开文件夹菜单（定时器回调）

        确保菜单已经创建完成后再初始化内容，如果菜单还未创建则延迟重试。

        Args:
            timer: 定时器对象
        """
        try:
            # 确保菜单已经创建完成后再初始化内容
            if hasattr(self.window, "recent_menu_item") and self.window.recent_menu_item:
                self.update_recent_menu()
            else:
                # 如果菜单还未创建，再次延迟
                NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                    0.1, self.window, "initializeRecentMenu:", None, False
                )
        except Exception as e:
            logger.warning(f"初始化最近文件菜单失败: {e}")

    # ==================== 最近文件操作 ====================

    def show_recent_files(self, sender):
        """
        显示最近打开文件夹菜单

        动态构建并显示最近打开的文件夹列表。

        Args:
            sender: 菜单项对象
        """
        try:
            # 已移除手动打开菜单逻辑，系统会自动处理
            # 但保留清空操作的快捷方式
            if hasattr(sender, "title") and sender.title() == "清空最近记录":
                self.clear_recent_files(sender)
        except Exception as e:
            logger.warning(f"显示最近文件菜单失败: {e}")

    def open_recent_file(self, sender):
        """
        打开最近文件

        从最近文件菜单中打开选中的文件夹。

        Args:
            sender: 菜单项对象
        """
        try:
            path = sender.representedObject()
            if path:
                # 验证路径是否为有效的文件夹
                if not os.path.exists(path):
                    logger.warning(f"最近文件夹路径不存在: {path}")
                    self.window.status_bar_controller.set_status_message(f"文件夹不存在: {os.path.basename(path)}")
                    return

                if not os.path.isdir(path):
                    logger.warning(f"最近路径不是文件夹: {path}")
                    self.window.status_bar_controller.set_status_message(f"路径不是文件夹: {os.path.basename(path)}")
                    return

                # 验证文件夹是否包含图片（使用拖拽控制器的方法）
                if not self._folder_contains_images(path):
                    logger.warning(f"最近文件夹不包含支持的图片: {path}")
                    self.window.status_bar_controller.set_status_message(f"文件夹不包含图片: {os.path.basename(path)}")
                    return

                self.window.operation_manager._save_last_dir(path)
                # 重新添加到最近记录（会更新时间戳）
                self.window.folder_manager.add_recent_folder(path)
                self.update_recent_menu()
                self.window.folder_manager.load_images_from_root(path)
        except Exception as e:
            logger.warning(f"打开最近文件失败: {e}")
            self.window.status_bar_controller.set_status_message(f"打开文件夹失败: {e!s}")

    def clear_recent_files(self, sender):
        """
        清空最近文件记录

        清除所有最近打开的文件记录。

        Args:
            sender: 菜单项对象
        """
        try:
            self.window.folder_manager.clear_recent_folders()
            self.update_recent_menu()
            self.window.status_bar_controller.set_status_message("已清空最近打开记录")
        except Exception as e:
            logger.warning(f"清空最近文件记录失败: {e}")

    # ==================== 辅助方法 ====================

    def _folder_contains_images(self, folder_path: str) -> bool:
        """
        检查文件夹是否包含支持的图片文件

        Args:
            folder_path: 文件夹路径

        Returns:
            bool: 是否包含图片文件
        """
        try:
            return FileUtils.folder_contains_images(folder_path, recursive_depth=1)
        except Exception:
            return False

