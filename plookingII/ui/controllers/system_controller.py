"""
SystemController - 系统级功能控制器

负责处理系统级功能和状态管理：
- 主题切换和外观管理
- 系统通知处理
- 菜单状态更新
- 应用程序生命周期管理

注意：历史记录和进度保存功能已迁移到 HistoryManager 服务。
从 MainWindow 中提取，遵循单一职责原则。
"""

import logging

from AppKit import (
    NSAppearance,
    NSAppearanceNameAqua,
    NSAppearanceNameDarkAqua,
    NSApplication,
    NSDistributedNotificationCenter,
)

from ...config.constants import APP_NAME

logger = logging.getLogger(APP_NAME)


class SystemController:
    """
    系统级功能控制器

    负责处理：
    1. 主题和外观管理
    2. 系统通知处理
    3. 菜单状态更新
    4. 应用程序生命周期管理

    注意：历史记录和进度保存功能已迁移到 HistoryManager 服务。
    """

    def __init__(self, window):
        """
        初始化系统控制器

        Args:
            window: 主窗口实例
        """
        self.window = window
        self._shutting_down = False

        # 注册系统主题变化通知
        self._setup_system_notifications()

    def _setup_system_notifications(self):
        """设置系统通知监听"""
        try:
            # 监听系统外观变化
            notification_center = NSDistributedNotificationCenter.defaultCenter()
            notification_center.addObserver_selector_name_object_(
                self.window, "systemThemeChanged:", "AppleInterfaceThemeChangedNotification", None
            )
        except Exception as e:
            logger.debug("设置系统通知失败: %s", e)

    # ==================== 主题和外观管理 ====================

    def handle_system_theme_changed(self, notification):
        """
        系统主题变化处理

        当系统主题发生变化时，自动跟随系统主题并刷新UI。

        Args:
            notification: 系统通知对象
        """
        try:
            app = NSApplication.sharedApplication()
            cur_appearance = app.appearance()
            if cur_appearance and cur_appearance.name() == NSAppearanceNameDarkAqua:
                app.setAppearance_(NSAppearance.appearanceNamed_(NSAppearanceNameAqua))
            else:
                app.setAppearance_(NSAppearance.appearanceNamed_(NSAppearanceNameDarkAqua))

            # 刷新UI
            if self.window.contentView():
                self.window.contentView().setNeedsDisplay_(True)
        except Exception as e:
            logger.warning("系统主题变化处理失败: %s", e)

    def toggle_theme(self, sender):
        """
        手动切换主题

        在浅色和深色主题之间切换，提供用户手动控制主题的能力。

        Args:
            sender: 菜单项对象
        """
        try:
            app = NSApplication.sharedApplication()
            cur_appearance = app.appearance()
            if cur_appearance and cur_appearance.name() == NSAppearanceNameDarkAqua:
                app.setAppearance_(NSAppearance.appearanceNamed_(NSAppearanceNameAqua))
            else:
                app.setAppearance_(NSAppearance.appearanceNamed_(NSAppearanceNameDarkAqua))
        except Exception as e:
            logger.warning("主题切换失败: %s", e)

    # ==================== 历史记录和状态管理 ====================
    # 注意：历史记录相关方法已迁移到 HistoryManager 服务

    # ==================== 菜单状态管理 ====================

    def reverse_folder_order(self, sender):
        """
        切换文件夹倒序浏览功能

        在升序和降序之间切换文件夹浏览顺序，并重新加载当前根目录。
        """
        try:
            self.window.folder_manager.set_reverse_folder_order(not self.window.folder_manager.reverse_folder_order)
            # 重新加载当前根目录（保持当前路径）
            if self.window.root_folder:
                self.window.folder_manager.load_images_from_root(self.window.root_folder)
            # 更新菜单勾选状态
            self.update_reverse_folder_order_menu()
            if hasattr(self.window, "status_bar_controller") and self.window.status_bar_controller:
                self.window.status_bar_controller.set_status_message(
                    "已切换文件夹浏览顺序：{}".format(
                        "降序" if self.window.folder_manager.reverse_folder_order else "升序"
                    )
                )
        except Exception as e:
            logger.error("切换文件夹浏览顺序失败: %s", e)

    def update_reverse_folder_order_menu(self, sender=None):
        """
        更新倒序菜单项的勾选状态

        根据当前的文件夹浏览顺序更新菜单项的勾选状态。
        """
        try:
            if hasattr(self.window, "reverse_folder_order_menu_item") and (self.window.reverse_folder_order_menu_item):
                self.window.reverse_folder_order_menu_item.setState_(
                    1 if self.window.folder_manager.reverse_folder_order else 0
                )
        except Exception as e:
            logger.warning("更新倒序菜单状态失败: %s", e)

    # ==================== 应用程序生命周期管理 ====================
    # 注意：后台任务管理已迁移到 BackgroundTaskManager 服务

    def cleanup(self):
        """清理系统控制器资源"""
        try:
            # 移除系统通知监听
            notification_center = NSDistributedNotificationCenter.defaultCenter()
            notification_center.removeObserver_(self.window)

            # 清理控制器和管理器
            if hasattr(self.window, "navigation_controller"):
                self.window.navigation_controller.cleanup()
            if hasattr(self.window, "image_manager"):
                self.window.image_manager.cleanup()
            if hasattr(self.window, "image_update_manager"):
                self.window.image_update_manager.cleanup()

        except Exception as e:
            logger.debug("清理系统控制器失败: %s", e)
