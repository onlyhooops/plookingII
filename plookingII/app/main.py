import contextlib
import os

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


def _dump_menu_diagnostics(app, main_window):
    """临时诊断：导出主菜单各项的 action 分发状态，用于排查打包后菜单失效问题"""
    try:
        menu = app.mainMenu()
        logging.warning(
            "[MENU-DEBUG] mainMenu=%s, main_window=%s (%s) isActive=%s keyWindow=%s mainWindow=%s",
            menu,
            main_window,
            type(main_window).__name__,
            bool(app.isActive()) if hasattr(app, "isActive") else "?",
            app.keyWindow(),
            app.mainWindow(),
        )
        if menu is None:
            logging.warning("[MENU-DEBUG] mainMenu 为 None！")
            return
        for item in menu.itemArray():
            submenu = item.submenu()
            if submenu is None:
                continue
            for sub in submenu.itemArray():
                action = sub.action()
                if not action:
                    continue
                target = sub.target()
                responds = None
                if target is not None:
                    with contextlib.suppress(Exception):
                        responds = bool(target.respondsToSelector_(action))
                logging.warning(
                    "[MENU-DEBUG] %s | %s | action=%s target=%s isMainWindow=%s responds=%s enabled=%s",
                    submenu.title(),
                    sub.title(),
                    action,
                    type(target).__name__ if target is not None else None,
                    target is main_window,
                    responds,
                    bool(sub.isEnabled()),
                )
    except Exception:
        logging.exception("[MENU-DEBUG] 诊断失败")


class _MenuFlowSimulator(NSObject):
    """临时诊断：模拟「关闭窗口 -> Dock 唤起」流程，检测菜单 action 分发是否仍有效"""

    def initWithApp_window_(self, app, win):
        self = objc.super(_MenuFlowSimulator, self).init()  # type: ignore
        if self:
            self.app = app
            self.win = win
            self.stage = 0
        return self

    def tick_(self, timer):
        from AppKit import NSTimer

        self.stage += 1
        try:
            if self.stage == 1:
                logging.warning("[FLOW-DEBUG] t+3s: isActive=%s 即将 performClose", bool(self.app.isActive()))
                self.win.performClose_(None)
                logging.warning(
                    "[FLOW-DEBUG] performClose 完成: isVisible=%s windows=%s",
                    bool(self.win.isVisible()),
                    [type(w).__name__ for w in self.app.windows()],
                )
            elif self.stage == 2:
                logging.warning("[FLOW-DEBUG] t+6s: 测试 sendAction 分发（窗口已隐藏）")
                sent = self.app.sendAction_to_from_("copy:", self.win, None)
                logging.warning("[FLOW-DEBUG] sendAction copy: -> %s", bool(sent))
                logging.warning("[FLOW-DEBUG] 模拟 Dock 唤起（调用 reopen 处理器）")
                delegate = self.app.delegate()
                delegate.applicationShouldHandleReopen_hasVisibleWindows_(self.app, False)
                logging.warning(
                    "[FLOW-DEBUG] reopen 完成: isVisible=%s isActive=%s",
                    bool(self.win.isVisible()),
                    bool(self.app.isActive()),
                )
            elif self.stage == 3:
                logging.warning("[FLOW-DEBUG] t+9s: 唤起后再次检测菜单状态")
                _dump_menu_diagnostics(self.app, self.win)
                sent = self.app.sendAction_to_from_("copy:", self.win, None)
                logging.warning("[FLOW-DEBUG] 唤起后 sendAction copy: -> %s", bool(sent))
                timer.invalidate()
            else:
                timer.invalidate()
                return
            if self.stage < 3:
                NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                    3.0, self, "tick:", None, False
                )
        except Exception:
            logging.exception("[FLOW-DEBUG] 模拟流程失败")
            timer.invalidate()


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

        with contextlib.suppress(Exception):
            app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        app.activateIgnoringOtherApps_(True)

        # 强制重绘窗口
        self.main_window.display()

        # 临时诊断：导出菜单分发状态（仅 PLOOKINGII_MENU_DEBUG=1 时启用）
        if os.environ.get("PLOOKINGII_MENU_DEBUG"):
            _dump_menu_diagnostics(app, self.main_window)
            from AppKit import NSTimer as _NSTimer

            self._menu_flow_simulator = _MenuFlowSimulator.alloc().initWithApp_window_(app, self.main_window)
            _NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                3.0, self._menu_flow_simulator, "tick:", None, False
            )

    def applicationShouldHandleReopen_hasVisibleWindows_(self, app, flag):
        """Dock 图标点击时重新显示主窗口

        处理三种场景：
        1. 窗口被最小化（Miniaturized）—— 使用 deminiaturize_ 恢复
        2. 窗口被隐藏（Hidden/OrderedOut）—— 使用 makeKeyAndOrderFront_ 显示
        3. 窗口在屏幕外或因其他原因不可见 —— 强制前置

        防御：若窗口引用已失效（极端情况下被系统销毁），重建窗口与菜单，
        确保 Dock 唤起与菜单栏始终可用。
        """
        try:
            if self.main_window is None:
                self.main_window = MainWindow.alloc().init()
                build_menu(app, self.main_window)

            if self.main_window.isMiniaturized():
                self.main_window.deminiaturize_(None)
            self.main_window.makeKeyAndOrderFront_(None)
            self.main_window.orderFrontRegardless()

            # 激活应用，确保菜单栏恢复响应
            with contextlib.suppress(Exception):
                app.activateIgnoringOtherApps_(True)
        except Exception:
            logging.exception("Dock 重新唤起窗口失败")
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
        # 程序退出前完整清理所有资源
        if self.main_window:
            try:
                # 1) 清理系统级别控制器（移除 NSNotification observer 等）
                if hasattr(self.main_window, "system_controller") and self.main_window.system_controller:
                    self.main_window.system_controller.cleanup()

                # 2) 清理图像管理器（定时器、线程池、HOT3 锁定）
                if hasattr(self.main_window, "image_manager") and self.main_window.image_manager:
                    self.main_window.image_manager.shutdown()

                # 3) 清理导航控制器（防抖定时器）
                if hasattr(self.main_window, "navigation_controller") and self.main_window.navigation_controller:
                    self.main_window.navigation_controller.cleanup()

                # 4) 清理图片更新管理器
                if hasattr(self.main_window, "image_update_manager") and self.main_window.image_update_manager:
                    self.main_window.image_update_manager.cleanup()

                # 5) 停止后台任务管理
                if hasattr(self.main_window, "shutdown_background_tasks"):
                    self.main_window.shutdown_background_tasks()

                # 6) 清理状态栏控制器
                if hasattr(self.main_window, "status_bar_controller") and self.main_window.status_bar_controller:
                    self.main_window.status_bar_controller.cleanup()
            except Exception:
                pass
            self.main_window._save_task_progress_immediate()

        # 7) 关闭全局单例的线程池
        try:
            from ..core.smb_optimizer import get_smb_optimizer

            optimizer = get_smb_optimizer()
            if optimizer and hasattr(optimizer, "shutdown"):
                optimizer.shutdown()
        except Exception:
            pass
        try:
            from ..core.remote_file_manager import get_remote_file_manager

            rfm = get_remote_file_manager()
            if rfm and hasattr(rfm, "shutdown"):
                rfm.shutdown()
        except Exception:
            pass

        # 开发环境下自动清理 macOS 最近文档记录
        try:
            from ..utils.macos_cleanup import MacOSCleanupManager

            MacOSCleanupManager.auto_cleanup_if_dev()
        except Exception:
            pass

        # 8) 输出性能监测会话报告（轻量跟踪器，退出前落盘供后续分析）
        try:
            from ..monitor import shutdown_perf_tracker

            shutdown_perf_tracker()
        except Exception:
            pass

        # 9) 关闭解码子进程池（回收子进程解码内存）
        try:
            from ..core.decode_pool import shutdown_decode_pool

            shutdown_decode_pool()
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
