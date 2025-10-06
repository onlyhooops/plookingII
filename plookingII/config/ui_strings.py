#!/usr/bin/env python3
"""
UI文案管理模块

统一管理所有用户可见的文案字符串，支持国际化和集中维护。
替代硬编码字符串，便于翻译和文案统一。

Author: PlookingII Team
"""

class UIStrings:
    """UI文案管理器"""

    # 应用程序基础信息
    APP_INFO = {
        "name": "PlookingII",
        "about": "关于",
        "version_label": "版本：",
        "developer_label": "开发者：",
        "copyright_prefix": "©",
    }

    # 菜单文案
    MENU = {
        # 应用程序菜单
        "app_menu_title": "PlookingII",
        "about": "关于",
        "hide": "隐藏",
        "minimize": "最小化",
        "quit": "退出程序",

        # 文件菜单
        "file_menu": "文件",
        "open_folder": "打开文件夹…",
        "recent_files": "打开最近",

        # 编辑菜单
        "edit_menu": "编辑",
        "undo_selection": "撤销精选",
        "copy_path": "复制图片路径",
        "rotate_right": "向右旋转90°",
        "rotate_left": "向左旋转90°",

        # 前往菜单
        "go_menu": "前往",
        "jump_folder": "跳转文件夹",
        "goto_selection": "转到精选文件夹",
        "show_in_finder": "在Finder中显示",

        # 显示菜单
        "view_menu": "显示",
        "toggle_theme": "切换深浅模式",

        # 工具菜单
        "tools_menu": "工具",
        "clear_history": "清除历史记录",
        "reverse_folder_order": "文件夹倒序浏览",

        # 帮助菜单
        "help_menu": "帮助",
        "shortcuts": "快捷键",
    }

    # 对话框按钮
    BUTTONS = {
        "ok": "确定",
        "cancel": "取消",
        "continue": "继续",
        "open": "打开",
        "clear_records": "清空记录",
        "restore": "恢复",
        "restart": "重新开始",
        "clear_history": "清除历史",
        "jump": "跳转",
        "view_help": "查看帮助",
    }

    # 快捷键说明
    SHORTCUTS_HELP = {
        "title": "快捷键",
        "left_right_arrows": "← / → 切换图片",
        "down_arrow": "↓ 移动到精选文件夹",
        "esc_key": "Esc 退出当前文件夹",
        "space_drag": "空格键 拖拽查看",
        
        "cmd_o": "⌘ O 打开文件夹",
        "cmd_z": "⌘ Z 撤销精选操作",
        "cmd_r": "⌘ R 在Finder中显示",
        
        "cmd_right": "⌘ → 跳过当前文件夹",
        "cmd_left": "⌘ ← 撤回跳过",
        
        "cmd_opt_r": "⌘ ⌥ R 向右旋转90°",
        "cmd_opt_l": "⌘ ⌥ L 向左旋转90°",
    }

    # 关于对话框内容
    ABOUT_DIALOG = {
        "description": "为macOS设计的原生图片浏览器",
        "subtitle": "快速浏览与筛选本地高分辨率照片",
        "privacy": "本地运行 不联网 不留缓存",
    }

    # 状态消息
    STATUS_MESSAGES = {
        "no_images": "无图片 0/0",
        "no_folders": "0/0",
        "task_completed": "任务完成",
        "all_folders_viewed": "所有图片文件夹已浏览完毕！",
        "no_current_image": "无当前图片，无法定位。",
        "selection_folder_not_exist": "精选文件夹不存在。",
        "no_directory_selected": "未选择图片目录，无法跳转。",
        "no_directory_for_selection": "未选择图片目录，无法打开精选文件夹。",
        "folder_opened": "已打开文件夹: {}",
        "folder_skipped": "已跳过文件夹: {}",
        "switched_to_sibling": "已切换到同级文件夹: {}",
        "switched_to_previous_sibling": "已切换到上一个同级文件夹: {}",
        "all_folders_completed": "{} 下的所有文件夹已浏览完毕！",
        "no_folders_to_skip": "无可跳过的文件夹",
        "no_undo_operations": "无可撤销的跳过操作",
        "folder_not_exist_undo": "跳过的文件夹已不存在，无法撤销",
        "undo_skip_returned": "已撤销跳过，返回到: {}",
        "no_undo_selection": "无可撤销的精选操作",
        "selection_undone": "已撤销精选操作",
        "undo_failed": "撤销失败: {}",
        "cannot_undo_file_missing": "无法撤销，目标文件不存在",
        "rotating_right": "正在向右旋转90°...",
        "rotating_left": "正在向左旋转90°...",
        "rotation_completed": "{}旋转90°完成",
        "rotation_failed": "旋转操作失败",
        "rotation_error": "旋转失败: {}",
        "no_rotatable_image": "没有可旋转的图像",
        "image_file_not_exist": "图像文件不存在",
        "clear_recent_success": "已清空最近打开记录",
        "folder_order_switched": "已切换文件夹浏览顺序：{}",
        "order_ascending": "升序",
        "order_descending": "降序",
        "drag_release_hint": "松开鼠标打开文件夹: {}",
        "path_copied": "已复制图片路径",
        "no_image_to_copy": "无当前图片，无法复制路径",
        "quartz_only_mode": "当前为Quartz-only模式，已禁用VIPS",
        "progressive_disabled": "渐进式已禁用（兼容旧API）",
    }

    # 错误消息
    ERROR_MESSAGES = {
        "open_folder_failed": "打开文件夹失败",
        "rotation_operation_failed": "旋转操作异常",
        "keyboard_event_failed": "键盘事件处理失败: {}",
        "zoom_slider_failed": "缩放滑块处理失败: {}",
        "navigation_failed": "导航操作执行失败: {}",
        "status_clear_failed": "状态消息清除失败: {}",
        "ui_update_failed": "UI更新失败: {}",
        "theme_switch_failed": "主题切换失败: {}",
        "about_dialog_failed": "显示关于对话框失败: {}",
        "shortcuts_dialog_failed": "显示快捷键说明失败: {}",
        "recent_menu_failed": "显示最近文件菜单失败: {}",
        "menu_build_failed": "构建菜单失败: {}",
        "drag_validation_failed": "拖拽验证失败: {}",
        "drag_enter_failed": "拖拽进入处理异常: {}",
        "drag_update_failed": "拖拽更新处理失败: {}",
        "drag_exit_failed": "拖拽退出处理失败: {}",
        "drag_operation_failed": "拖拽操作执行失败: {}",
        "folder_access_denied": "无法访问文件夹",
        "unsupported_folder": "拖拽的文件夹中未找到支持的图片文件",
    }

    # 历史记录对话框
    HISTORY_DIALOG = {
        "title": "发现历史记录",
        "info_template": (
            "发现上次浏览记录：\n"
            "• 文件夹进度：第 {} 个，共 {} 个\n"
            "• 图片进度：第 {} 张\n"
            "• 是否恢复上次的浏览位置？"
        ),
        "restore": "恢复",
        "restart": "重新开始",
        "clear_history": "清除历史",
    }

    # 跳转文件夹对话框
    JUMP_FOLDER_DIALOG = {
        "title": "跳转文件夹",
        "instruction": "请选择要跳转的图片文件夹：",
        "jump": "跳转",
        "cancel": "取消",
    }

    # 最近文件对话框
    RECENT_FILES_DIALOG = {
        "title": "最近打开文件",
        "open": "打开",
        "clear_records": "清空记录",
        "cancel": "取消",
    }

class UIStringManager:
    """UI文案管理器"""

    def __init__(self):
        """初始化文案管理器"""
        self._strings = {}
        self._load_default_strings()

    def _load_default_strings(self):
        """加载默认文案"""
        self._strings.update({
            "app_info": UIStrings.APP_INFO,
            "menu": UIStrings.MENU,
            "buttons": UIStrings.BUTTONS,
            "shortcuts_help": UIStrings.SHORTCUTS_HELP,
            "about_dialog": UIStrings.ABOUT_DIALOG,
            "status_messages": UIStrings.STATUS_MESSAGES,
            "error_messages": UIStrings.ERROR_MESSAGES,
            "history_dialog": UIStrings.HISTORY_DIALOG,
            "jump_folder_dialog": UIStrings.JUMP_FOLDER_DIALOG,
            "recent_files_dialog": UIStrings.RECENT_FILES_DIALOG,
        })

    def get(self, category: str, key: str, default: str = "") -> str:
        """获取文案字符串

        Args:
            category: 文案分类 (如 'menu', 'buttons', 'status_messages')
            key: 文案键名
            default: 默认值

        Returns:
            str: 文案字符串
        """
        try:
            return self._strings.get(category, {}).get(key, default)
        except Exception:
            return default

    def get_formatted(self, category: str, key: str, *args, **kwargs) -> str:
        """获取格式化文案字符串

        Args:
            category: 文案分类
            key: 文案键名
            *args: 格式化参数
            **kwargs: 格式化关键字参数

        Returns:
            str: 格式化后的文案字符串
        """
        try:
            template = self.get(category, key)
            if template:
                return template.format(*args, **kwargs)
            return ""
        except Exception:
            return ""

    def get_shortcuts_help_text(self) -> str:
        """获取完整的快捷键帮助文本

        Returns:
            str: 格式化的快捷键帮助文本
        """
        shortcuts = self._strings.get("shortcuts_help", {})

        sections = [
            shortcuts.get("left_right_arrows", ""),
            shortcuts.get("down_arrow", ""),
            shortcuts.get("esc_key", ""),
            shortcuts.get("space_drag", ""),
            "",
            shortcuts.get("cmd_o", ""),
            shortcuts.get("cmd_z", ""),
            shortcuts.get("cmd_r", ""),
            "",
            shortcuts.get("cmd_right", ""),
            shortcuts.get("cmd_left", ""),
            "",
            shortcuts.get("cmd_opt_r", ""),
            shortcuts.get("cmd_opt_l", ""),
        ]

        return "\n".join(section for section in sections if section)

    def get_about_dialog_text(self, version: str, author: str, copyright_text: str) -> str:
        """获取关于对话框文本

        Args:
            version: 版本号
            author: 开发者
            copyright_text: 版权信息

        Returns:
            str: 格式化的关于对话框文本
        """
        about = self._strings.get("about_dialog", {})

        sections = [
            f"V {version}",
            "",
            about.get("description", ""),
            "",
            about.get("subtitle", ""),
            "",
            about.get("privacy", ""),
            "",
            copyright_text,
        ]

        return "\n".join(section for section in sections if section)

# 全局文案管理器实例
_ui_string_manager = None

def get_ui_string_manager() -> UIStringManager:
    """获取全局UI文案管理器实例"""
    global _ui_string_manager
    if _ui_string_manager is None:
        _ui_string_manager = UIStringManager()
    return _ui_string_manager

def get_ui_string(category: str, key: str, default: str = "") -> str:
    """便捷函数：获取UI文案字符串

    Args:
        category: 文案分类
        key: 文案键名
        default: 默认值

    Returns:
        str: 文案字符串
    """
    return get_ui_string_manager().get(category, key, default)

def get_formatted_ui_string(category: str, key: str, *args, **kwargs) -> str:
    """便捷函数：获取格式化UI文案字符串

    Args:
        category: 文案分类
        key: 文案键名
        *args: 格式化参数
        **kwargs: 格式化关键字参数

    Returns:
        str: 格式化后的文案字符串
    """
    return get_ui_string_manager().get_formatted(category, key, *args, **kwargs)
