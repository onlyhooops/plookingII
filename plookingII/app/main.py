from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyRegular,
    NSMenu,
    NSMenuItem,
    NSObject,
    NSScreen,
)

from ..config.constants import APP_NAME
from ..core.error_handling import ErrorCategory, error_context
from ..core.functions import build_menu
from ..imports import logging, objc
from ..ui.window import MainWindow


class AppDelegate(NSObject):
    def init(self):
        self = objc.super(AppDelegate, self).init()  # type: ignore
        if self:
            self.main_window = None
        return self

    def applicationDidFinishLaunching_(self, notification):
        """应用启动完成后的回调 - 创建主窗口并构建菜单"""
        app = NSApplication.sharedApplication()
        # v1.0.0: Quartz-only架构，移除VIPS依赖
        # 创建主窗口
        self.main_window = MainWindow.alloc().init()
        # 构建菜单
        build_menu(app, self.main_window)

        # 确保窗口在正确的显示器上显示
        try:
            # 获取主显示器的屏幕信息
            screen = NSScreen.mainScreen()
            if screen:
                # 将窗口移动到主显示器的中心
                screen_frame = screen.frame()
                window_frame = self.main_window.frame()
                new_x = screen_frame.origin.x + (screen_frame.size.width - window_frame.size.width) / 2
                new_y = screen_frame.origin.y + (screen_frame.size.height - window_frame.size.height) / 2
                self.main_window.setFrameOrigin_((new_x, new_y))
        except Exception:
            pass

        # 显示主窗口并激活应用
        self.main_window.makeKeyAndOrderFront_(None)

        # 确保窗口在最前面
        self.main_window.orderFrontRegardless()

        try:
            app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        except Exception:
            pass
        app.activateIgnoringOtherApps_(True)

        # 强制重绘窗口
        self.main_window.display()

    def applicationShouldHandleReopen_hasVisibleWindows_(self, app, flag):
        # Dock图标点击时，如果主窗口被关闭，则重新显示
        if self.main_window:
            self.main_window.makeKeyAndOrderFront_(None)
            self.main_window.orderFrontRegardless()
        return True

    def applicationDockMenu_(self, sender):
        """提供 Dock 菜单：打开文件夹、最近打开"""
        try:
            # 强制清理无效的最近文件夹记录
            if self.main_window and hasattr(self.main_window, "folder_manager"):
                try:
                    manager = self.main_window.folder_manager.recent_folders_manager
                    cleaned = manager.cleanup_invalid_entries()
                    if cleaned > 0:
                        logging.info(f"Dock菜单构建时清理了 {cleaned} 个无效记录")
                except Exception:
                    pass

            menu = NSMenu.alloc().initWithTitle_("DockMenu")
            # 打开文件夹
            openItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("选择文件夹…", "openFolder:", "")
            if self.main_window:
                openItem.setTarget_(self.main_window)
            menu.addItem_(openItem)
            menu.addItem_(NSMenuItem.separatorItem())

            # 最近打开 - 使用经过验证的最近文件夹列表
            if self.main_window and hasattr(self.main_window, "buildRecentMenu_"):
                recent_submenu = self.main_window.buildRecentMenu_(None)
                recentItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("最近打开", "", "")
                recentItem.setSubmenu_(recent_submenu)
                menu.addItem_(recentItem)

            return menu

        except Exception as e:
            logging.warning(f"构建dock菜单失败: {e}")
            # 返回基础菜单
            menu = NSMenu.alloc().initWithTitle_("DockMenu")
            openItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("选择文件夹…", "openFolder:", "")
            if self.main_window:
                openItem.setTarget_(self.main_window)
            menu.addItem_(openItem)
            return menu

    def applicationShouldTerminate_(self, sender):
        # 程序退出前保存历史记录并停止后台任务
        if self.main_window:
            try:
                if hasattr(self.main_window, "shutdown_background_tasks"):
                    self.main_window.shutdown_background_tasks()
            except Exception:
                pass
            self.main_window._save_task_progress_immediate()

        # 开发环境下自动清理 macOS 最近文档记录
        try:
            from ..utils.macos_cleanup import MacOSCleanupManager

            MacOSCleanupManager.auto_cleanup_if_dev()
        except Exception:
            pass

        return True


def main():
    """主应用入口函数"""
    with error_context("app_main", category=ErrorCategory.UI):
        try:
            # 创建应用实例
            app = NSApplication.sharedApplication()

            # 设置应用代理
            app_delegate = AppDelegate.alloc().init()
            app.setDelegate_(app_delegate)

            # 启动应用
            app.run()
        except Exception:
            logging.getLogger(APP_NAME).critical("App main loop failed", exc_info=True)
            raise


if __name__ == "__main__":
    main()
