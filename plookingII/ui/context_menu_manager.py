"""
上下文菜单管理器 - 专门处理右键菜单的复杂逻辑

该模块负责处理系统级"打开方式"菜单的创建和管理，包括：
- 应用程序发现和过滤
- 菜单项创建和图标设置
- 浏览器应用程序过滤
- 菜单事件处理
"""

import os

import objc
from AppKit import NSMenu, NSMenuItem, NSWorkspace
from Foundation import NSURL

from ..config.constants import APP_NAME
from ..imports import logging

logger = logging.getLogger(APP_NAME)

class AppInfo:
    """应用程序信息封装"""

    def __init__(self, url: NSURL, name: str, path: str, is_default: bool = False):
        self.url = url
        self.name = name
        self.path = path
        self.is_default = is_default
        self.icon = None

class BrowserFilter:
    """浏览器应用程序过滤器"""

    # 浏览器关键词列表
    BROWSER_KEYWORDS = [
        "浏览器", "Browser", "Safari", "Chrome", "Firefox", "Edge",
        "Opera", "Brave", "Vivaldi", "Arc", "115浏览器"
    ]

    @classmethod
    def is_browser_app(cls, app_path: str) -> bool:
        """检查应用程序是否为浏览器

        Args:
            app_path: 应用程序路径

        Returns:
            bool: 如果是浏览器应用返回True
        """
        if not app_path:
            return False

        app_name = os.path.basename(app_path)

        # 检查应用名称是否包含浏览器关键词
        for keyword in cls.BROWSER_KEYWORDS:
            if keyword.lower() in app_name.lower():
                return True

        return False

class AppDiscovery:
    """应用程序发现器"""

    def __init__(self, workspace: NSWorkspace):
        self.workspace = workspace
        self.browser_filter = BrowserFilter()

    def get_apps_for_file(self, file_path: str) -> list[AppInfo]:
        """获取可以打开指定文件的应用程序列表

        Args:
            file_path: 文件路径

        Returns:
            List[AppInfo]: 应用程序信息列表
        """
        try:
            file_url = NSURL.fileURLWithPath_(file_path)
            apps_urls = self.workspace.URLsForApplicationsToOpenURL_(file_url)
            default_app_url = self.workspace.URLForApplicationToOpenURL_(file_url)

            if not apps_urls:
                return []

            apps = []
            added_paths = set()

            # 处理默认应用程序
            if default_app_url:
                default_path = default_app_url.path()
                if not self.browser_filter.is_browser_app(default_path):
                    app_name = os.path.basename(default_path).replace(".app", "")
                    apps.append(AppInfo(default_app_url, app_name, default_path, is_default=True))
                    added_paths.add(default_path)

            # 处理其他应用程序
            for app_url in apps_urls:
                app_path = app_url.path()
                if app_path not in added_paths:
                    if not self.browser_filter.is_browser_app(app_path):
                        app_name = os.path.basename(app_path).replace(".app", "")
                        apps.append(AppInfo(app_url, app_name, app_path))
                        added_paths.add(app_path)

            return apps

        except Exception as e:
            logger.warning(f"获取应用程序列表失败: {e}")
            return []

class MenuItemBuilder:
    """菜单项构建器"""

    def __init__(self, workspace: NSWorkspace, target_view):
        self.workspace = workspace
        self.target_view = target_view

    def create_title_item(self, file_path: str) -> NSMenuItem:
        """创建标题菜单项

        Args:
            file_path: 文件路径

        Returns:
            NSMenuItem: 标题菜单项
        """
        title_item = NSMenuItem.alloc().init()
        title_item.setTitle_("打开方式...")
        title_item.setEnabled_(False)  # 作为标题，不可点击

        # 设置文件图标
        try:
            file_icon = self.workspace.iconForFile_(file_path)
            if file_icon:
                file_icon.setSize_((16, 16))
                title_item.setImage_(file_icon)
        except Exception:
            pass  # 图标设置失败不影响功能

        return title_item

    def create_app_item(self, app_info: AppInfo) -> NSMenuItem:
        """创建应用程序菜单项

        Args:
            app_info: 应用程序信息

        Returns:
            NSMenuItem: 应用程序菜单项
        """
        menu_item = NSMenuItem.alloc().init()

        # 设置标题
        title = f"{app_info.name} (默认)" if app_info.is_default else app_info.name
        menu_item.setTitle_(title)

        # 设置目标和动作
        menu_item.setTarget_(self.target_view)
        if app_info.is_default:
            menu_item.setAction_(objc.selector(self.target_view.openWithDefaultApp_, signature=b"v@:@"))
        else:
            menu_item.setAction_(objc.selector(self.target_view.openWithApp_, signature=b"v@:@"))

        menu_item.setRepresentedObject_(app_info.url)
        menu_item.setEnabled_(True)

        # 设置应用程序图标
        try:
            app_icon = self.workspace.iconForFile_(app_info.path)
            if app_icon:
                app_icon.setSize_((16, 16))
                menu_item.setImage_(app_icon)
        except Exception as e:
            logger.debug(f"{app_info.name} 图标设置失败: {e}")

        return menu_item

    def create_other_item(self) -> NSMenuItem:
        """创建"其他..."菜单项

        Returns:
            NSMenuItem: "其他..."菜单项
        """
        other_item = NSMenuItem.alloc().init()
        other_item.setTitle_("其他...")
        other_item.setTarget_(self.target_view)
        other_item.setAction_(objc.selector(self.target_view.openWithOtherApp_, signature=b"v@:@"))
        other_item.setEnabled_(True)

        # 设置文件夹图标
        try:
            folder_icon = self.workspace.iconForFileType_("public.folder")
            if folder_icon:
                folder_icon.setSize_((16, 16))
                other_item.setImage_(folder_icon)
        except Exception:
            pass

        return other_item

    def create_filtered_notice_item(self) -> NSMenuItem:
        """创建过滤提示菜单项

        Returns:
            NSMenuItem: 过滤提示菜单项
        """
        notice_item = NSMenuItem.alloc().init()
        notice_item.setTitle_("(已过滤浏览器应用程序)")
        notice_item.setEnabled_(False)
        return notice_item

class ContextMenuManager:
    """上下文菜单管理器 - 负责整个右键菜单的创建和管理"""

    def __init__(self, target_view):
        self.target_view = target_view
        self.workspace = NSWorkspace.sharedWorkspace()
        self.app_discovery = AppDiscovery(self.workspace)
        self.menu_builder = MenuItemBuilder(self.workspace, target_view)

    def show_open_with_menu(self, event, file_path: str) -> bool:
        """显示"打开方式"菜单

        Args:
            event: 鼠标事件对象
            file_path: 要打开的文件路径

        Returns:
            bool: 成功显示菜单返回True
        """
        try:
            if not file_path or not os.path.exists(file_path):
                logger.warning("文件路径无效或文件不存在")
                return False

            # 获取可用应用程序
            apps = self.app_discovery.get_apps_for_file(file_path)

            # 创建菜单
            menu = self._create_menu(apps, file_path)
            if not menu:
                return False

            # 显示菜单
            location = event.locationInWindow()
            menu.popUpMenuPositioningItem_atLocation_inView_(
                None, location, self.target_view
            )

            return True

        except Exception as e:
            logger.error(f"显示右键菜单失败: {e}")
            return False

    def _create_menu(self, apps: list[AppInfo], file_path: str) -> NSMenu | None:
        """创建菜单

        Args:
            apps: 应用程序列表
            file_path: 文件路径

        Returns:
            Optional[NSMenu]: 创建的菜单，失败时返回None
        """
        if not apps:
            return None

        menu = NSMenu.alloc().init()
        menu.setAutoenablesItems_(False)

        # 添加标题
        title_item = self.menu_builder.create_title_item(file_path)
        menu.addItem_(title_item)
        menu.addItem_(NSMenuItem.separatorItem())

        # 添加应用程序菜单项
        added_count = 0
        max_apps = 8  # 限制显示数量

        for app_info in apps:
            if added_count >= max_apps:
                break

            app_item = self.menu_builder.create_app_item(app_info)
            menu.addItem_(app_item)
            added_count += 1

        # 如果没有可用应用程序，显示过滤提示
        if added_count == 0:
            notice_item = self.menu_builder.create_filtered_notice_item()
            menu.addItem_(notice_item)
        else:
            # 添加分隔线和"其他..."选项
            menu.addItem_(NSMenuItem.separatorItem())
            other_item = self.menu_builder.create_other_item()
            menu.addItem_(other_item)

        return menu
