"""
菜单构建器 - 专门处理macOS应用程序菜单的创建和管理

该模块负责构建完整的macOS原生菜单系统，包括：
- 应用程序菜单（关于、隐藏、退出等）
- 文件菜单（打开文件夹、最近打开等）
- 编辑菜单（撤销、复制等）
- 转到菜单（导航相关）
- 视图菜单（显示选项）
- 工具菜单（功能工具）
- 帮助菜单（帮助和快捷键）
"""

from AppKit import NSEventModifierFlagCommand, NSEventModifierFlagOption, NSMenu, NSMenuItem

from ..config.constants import APP_NAME
from ..config.ui_strings import get_ui_string
from ..imports import logging

logger = logging.getLogger(APP_NAME)


class AppMenuBuilder:
    """应用程序菜单构建器"""

    def __init__(self, app, window):
        self.app = app
        self.window = window

    def build_app_menu(self) -> NSMenuItem:
        """构建应用程序菜单

        Returns:
            NSMenuItem: 应用程序菜单项
        """
        app_menu_item = NSMenuItem.alloc().init()
        app_menu = NSMenu.alloc().initWithTitle_("PlookingII")

        # 关于菜单项
        about_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            get_ui_string("menu", "about", "关于"), "showAbout:", ""
        )
        about_item.setTarget_(self.window)
        app_menu.addItem_(about_item)

        # 隐藏菜单项
        hide_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            get_ui_string("menu", "hide", "隐藏"), "hide:", "h"
        )
        hide_item.setKeyEquivalentModifierMask_(NSEventModifierFlagCommand)
        hide_item.setTarget_(self.app)
        app_menu.addItem_(hide_item)

        # 最小化菜单项
        minimize_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            get_ui_string("menu", "minimize", "最小化"), "performMiniaturize:", "m"
        )
        minimize_item.setKeyEquivalentModifierMask_(NSEventModifierFlagCommand)
        minimize_item.setTarget_(self.window)
        app_menu.addItem_(minimize_item)

        # 退出菜单项
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            get_ui_string("menu", "quit", "退出程序"), "terminate:", "q"
        )
        quit_item.setKeyEquivalentModifierMask_(NSEventModifierFlagCommand)
        quit_item.setTarget_(self.app)
        app_menu.addItem_(quit_item)

        app_menu_item.setSubmenu_(app_menu)
        return app_menu_item


class FileMenuBuilder:
    """文件菜单构建器"""

    def __init__(self, window):
        self.window = window

    def build_file_menu(self) -> NSMenuItem:
        """构建文件菜单

        Returns:
            NSMenuItem: 文件菜单项
        """
        file_menu_item = NSMenuItem.alloc().init()
        file_menu = NSMenu.alloc().initWithTitle_("文件")

        # 打开文件夹菜单项
        open_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            get_ui_string("menu", "open_folder", "打开文件夹…"), "openFolder:", "o"
        )
        open_item.setKeyEquivalentModifierMask_(NSEventModifierFlagCommand)
        open_item.setTarget_(self.window)
        file_menu.addItem_(open_item)

        # 最近打开文件菜单项
        recent_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("打开最近", "", "")
        recent_menu = NSMenu.alloc().initWithTitle_("打开最近")
        recent_menu_item.setSubmenu_(recent_menu)
        file_menu.addItem_(recent_menu_item)

        # 保存引用供后续更新
        self.window.recent_menu_item = recent_menu_item

        file_menu_item.setSubmenu_(file_menu)
        return file_menu_item


class EditMenuBuilder:
    """编辑菜单构建器"""

    def __init__(self, window):
        self.window = window

    def build_edit_menu(self) -> NSMenuItem:
        """构建编辑菜单

        Returns:
            NSMenuItem: 编辑菜单项
        """
        edit_menu_item = NSMenuItem.alloc().init()
        edit_menu = NSMenu.alloc().initWithTitle_("编辑")

        # 禁用菜单的自动验证，防止系统自动修改菜单项
        try:
            edit_menu.setAutoenablesItems_(False)
        except Exception:
            pass

        # 撤销菜单项（术语统一：精选）
        # 使用自定义 action 避免系统自动覆盖为 "Undo"
        undo_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            get_ui_string("menu", "undo_selection", "撤销精选"), "undoSelection:", "z"
        )
        undo_item.setKeyEquivalentModifierMask_(NSEventModifierFlagCommand)
        undo_item.setTarget_(self.window)
        undo_item.setEnabled_(True)
        edit_menu.addItem_(undo_item)

        edit_menu.addItem_(NSMenuItem.separatorItem())

        # 复制菜单项
        copy_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            get_ui_string("menu", "copy_path", "复制图片路径"), "copy:", "c"
        )
        copy_item.setKeyEquivalentModifierMask_(NSEventModifierFlagCommand)
        copy_item.setTarget_(self.window)
        copy_item.setEnabled_(True)
        edit_menu.addItem_(copy_item)

        edit_menu.addItem_(NSMenuItem.separatorItem())

        # 向右旋转90°菜单项 (原来在编辑菜单中)
        rotate_right_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            get_ui_string("menu", "rotate_right", "向右旋转90°"), "rotateImageClockwise:", "r"
        )
        rotate_right_item.setKeyEquivalentModifierMask_(NSEventModifierFlagCommand | NSEventModifierFlagOption)
        rotate_right_item.setTarget_(self.window)
        rotate_right_item.setEnabled_(True)
        edit_menu.addItem_(rotate_right_item)

        # 向左旋转90°菜单项 (原来在编辑菜单中)
        rotate_left_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            get_ui_string("menu", "rotate_left", "向左旋转90°"), "rotateImageCounterclockwise:", "l"
        )
        rotate_left_item.setKeyEquivalentModifierMask_(NSEventModifierFlagCommand | NSEventModifierFlagOption)
        rotate_left_item.setTarget_(self.window)
        rotate_left_item.setEnabled_(True)
        edit_menu.addItem_(rotate_left_item)

        edit_menu_item.setSubmenu_(edit_menu)
        return edit_menu_item


class GoMenuBuilder:
    """转到菜单构建器"""

    def __init__(self, window):
        self.window = window

    def build_go_menu(self) -> NSMenuItem:
        """构建转到菜单

        Returns:
            NSMenuItem: 转到菜单项
        """
        go_menu_item = NSMenuItem.alloc().init()
        go_menu = NSMenu.alloc().initWithTitle_("前往")  # 原来的菜单标题

        # 跳转文件夹菜单项 (原来的标题)
        jump_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("跳转文件夹", "jumpToFolder:", "")
        jump_item.setTarget_(self.window)
        go_menu.addItem_(jump_item)

        # 跳转到保留文件夹菜单项
        keep_folder_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "转到精选文件夹", "gotoKeepFolder:", ""
        )
        keep_folder_item.setTarget_(self.window)
        go_menu.addItem_(keep_folder_item)

        # 跳转到文件菜单项
        goto_file_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("跳转到文件", "gotoFile:", "g")
        goto_file_item.setKeyEquivalentModifierMask_(NSEventModifierFlagCommand)
        goto_file_item.setTarget_(self.window)
        go_menu.addItem_(goto_file_item)

        # 在Finder中显示菜单项 (原来在转到菜单中)
        show_finder_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "在Finder中显示", "showInFinder:", "r"
        )
        show_finder_item.setKeyEquivalentModifierMask_(NSEventModifierFlagCommand)
        show_finder_item.setTarget_(self.window)
        go_menu.addItem_(show_finder_item)

        go_menu_item.setSubmenu_(go_menu)
        return go_menu_item


class ViewMenuBuilder:
    """视图菜单构建器"""

    def __init__(self, window):
        self.window = window

    def build_view_menu(self) -> NSMenuItem:
        """构建视图菜单

        Returns:
            NSMenuItem: 视图菜单项
        """
        view_menu_item = NSMenuItem.alloc().init()
        view_menu = NSMenu.alloc().initWithTitle_("显示")  # 原来的菜单标题

        # 切换深浅模式菜单项 (原来在视图菜单中)
        theme_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("切换深浅模式", "toggleTheme:", "")
        theme_item.setTarget_(self.window)
        view_menu.addItem_(theme_item)

        view_menu_item.setSubmenu_(view_menu)
        return view_menu_item


class ToolsMenuBuilder:
    """工具菜单构建器"""

    def __init__(self, window):
        self.window = window

    def build_tools_menu(self) -> NSMenuItem:
        """构建工具菜单

        Returns:
            NSMenuItem: 工具菜单项
        """
        tools_menu_item = NSMenuItem.alloc().init()
        tools_menu = NSMenu.alloc().initWithTitle_("工具")

        # 清除历史记录菜单项 (原来的名称)
        clear_cache_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("清除历史记录", "clearCache:", "")
        clear_cache_item.setTarget_(self.window)
        tools_menu.addItem_(clear_cache_item)

        # 文件夹倒序浏览菜单项 (原来在工具菜单中)
        reverse_order_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "文件夹倒序浏览", "reverseFolderOrder:", ""
        )
        reverse_order_item.setTarget_(self.window)
        # 设置初始状态
        reverse_order_item.setState_(1 if getattr(self.window, "reverse_folder_order", False) else 0)
        tools_menu.addItem_(reverse_order_item)

        # 保存引用供后续更新
        self.window.reverse_folder_order_menu_item = reverse_order_item
        # 修正初始勾选依据为 FolderManager 的状态
        try:
            fm = getattr(self.window, "folder_manager", None)
            state = 1 if (fm and getattr(fm, "reverse_folder_order", False)) else 0
            reverse_order_item.setState_(state)
        except Exception:
            logger.debug("Initialize reverse order state failed", exc_info=True)

        tools_menu_item.setSubmenu_(tools_menu)
        return tools_menu_item


class HelpMenuBuilder:
    """帮助菜单构建器"""

    def __init__(self, window):
        self.window = window

    def build_help_menu(self) -> NSMenuItem:
        """构建帮助菜单

        Returns:
            NSMenuItem: 帮助菜单项
        """
        help_menu_item = NSMenuItem.alloc().init()
        help_menu = NSMenu.alloc().initWithTitle_("帮助")

        # 快捷键菜单项
        shortcuts_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            get_ui_string("menu", "shortcuts", "快捷键"), "showShortcuts:", ""
        )
        shortcuts_item.setTarget_(self.window)
        help_menu.addItem_(shortcuts_item)

        help_menu_item.setSubmenu_(help_menu)
        return help_menu_item


class MenuBuilder:
    """主菜单构建器 - 负责整个菜单系统的协调和构建"""

    def __init__(self, app, window):
        self.app = app
        self.window = window

        # 初始化各个菜单构建器
        self.app_menu_builder = AppMenuBuilder(app, window)
        self.file_menu_builder = FileMenuBuilder(window)
        self.edit_menu_builder = EditMenuBuilder(window)
        self.go_menu_builder = GoMenuBuilder(window)
        self.view_menu_builder = ViewMenuBuilder(window)
        self.tools_menu_builder = ToolsMenuBuilder(window)
        self.help_menu_builder = HelpMenuBuilder(window)

    def build_menu(self) -> NSMenu:
        """构建完整的应用程序菜单

        ✨ 重构说明: 原150行复杂函数已拆分为专门的菜单构建器类
        这个方法现在只负责协调各个菜单构建器，具体逻辑在各自的构建器中。

        Returns:
            NSMenu: 构建完成的主菜单
        """
        try:
            main_menu = NSMenu.alloc().init()

            # 构建各个菜单
            app_menu_item = self.app_menu_builder.build_app_menu()
            file_menu_item = self.file_menu_builder.build_file_menu()
            edit_menu_item = self.edit_menu_builder.build_edit_menu()
            go_menu_item = self.go_menu_builder.build_go_menu()
            view_menu_item = self.view_menu_builder.build_view_menu()
            tools_menu_item = self.tools_menu_builder.build_tools_menu()
            help_menu_item = self.help_menu_builder.build_help_menu()

            # 添加到主菜单
            main_menu.addItem_(app_menu_item)
            main_menu.addItem_(file_menu_item)
            main_menu.addItem_(edit_menu_item)
            main_menu.addItem_(go_menu_item)
            main_menu.addItem_(view_menu_item)
            main_menu.addItem_(tools_menu_item)
            main_menu.addItem_(help_menu_item)

            return main_menu

        except Exception as e:
            logger.error("构建菜单失败: %s", e)
            # 返回一个基本菜单作为回退
            fallback_menu = NSMenu.alloc().init()
            return fallback_menu
