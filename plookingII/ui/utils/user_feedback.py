#!/usr/bin/env python3
"""
用户反馈工具模块

提供友好的用户错误提示和反馈机制，将技术错误转换为用户可理解的提示。
"""

import logging

from AppKit import NSAlert, NSAlertStyle

from ...config.constants import APP_NAME
from ...config.ui_strings import get_ui_string
from ...core.error_handling import (
    ConfigurationError,
    DragDropError,
    ErrorSeverity,
    FileSystemError,
    FolderValidationError,
    ImageProcessingError,
    MemoryError,
    PlookingIIError,
)

logger = logging.getLogger(APP_NAME)


class UserFeedbackManager:
    """用户反馈管理器

    负责将技术错误转换为用户友好的提示信息。
    """

    def __init__(self):
        """初始化用户反馈管理器"""
        self._error_messages = self._init_error_messages()
        self._recovery_suggestions = self._init_recovery_suggestions()

    def _init_error_messages(self) -> dict[type, str]:
        """初始化错误消息映射"""
        return {
            DragDropError: "拖拽操作遇到问题",
            FolderValidationError: "文件夹验证失败",
            ImageProcessingError: "图片处理出现错误",
            FileSystemError: "文件系统访问失败",
            MemoryError: "内存使用异常",
            ConfigurationError: "配置设置有误",
        }

    def _init_recovery_suggestions(self) -> dict[type, str]:
        """初始化恢复建议映射"""
        return {
            DragDropError: "请尝试重新拖拽文件夹，或使用菜单选择文件夹",
            FolderValidationError: "请检查文件夹权限，或选择其他包含图片的文件夹",
            ImageProcessingError: "请检查图片文件是否损坏，或尝试其他图片",
            FileSystemError: "请检查文件夹是否存在，以及是否有访问权限",
            MemoryError: "请关闭其他应用程序释放内存，或重启应用程序",
            ConfigurationError: "请检查应用程序设置，或重置为默认配置",
        }

    def show_error_dialog(self, error: Exception, context: str = "") -> None:
        """显示用户友好的错误对话框

        Args:
            error: 异常对象
            context: 错误上下文信息
        """
        try:
            # 获取用户友好的错误信息
            user_message = self._get_user_friendly_message(error)
            recovery_suggestion = self._get_recovery_suggestion(error)

            # 创建错误对话框
            alert = NSAlert.alloc().init()
            alert.setMessageText_(user_message)

            # 构建详细信息
            detail_info = []
            if context:
                detail_info.append(f"操作: {context}")

            if recovery_suggestion:
                detail_info.append(f"建议: {recovery_suggestion}")

            # 如果是PlookingII自定义错误，添加详细信息
            if isinstance(error, PlookingIIError) and hasattr(error, "metadata") and error.metadata:
                if "folder_path" in error.metadata:
                    detail_info.append(f"文件夹: {error.metadata['folder_path']}")

            if detail_info:
                alert.setInformativeText_("\n".join(detail_info))

            # 设置错误级别对应的图标
            alert_style = self._get_alert_style(error)
            alert.setAlertStyle_(alert_style)

            # 添加按钮
            alert.addButtonWithTitle_(get_ui_string("buttons", "ok", "确定"))
            if recovery_suggestion:
                alert.addButtonWithTitle_(get_ui_string("buttons", "view_help", "查看帮助"))

            # 显示对话框
            response = alert.runModal()

            # 如果用户点击帮助，显示详细帮助
            if response == 1001:  # 第二个按钮
                self._show_help_dialog(error)

        except Exception as e:
            logger.exception("显示错误对话框失败: %s", e)
            # 回退到简单的错误提示
            self._show_simple_error(str(error))

    def _get_user_friendly_message(self, error: Exception) -> str:
        """获取用户友好的错误消息

        Args:
            error: 异常对象

        Returns:
            str: 用户友好的错误消息
        """
        error_type = type(error)

        # 检查是否有预定义的用户消息
        if error_type in self._error_messages:
            return self._error_messages[error_type]

        # 检查是否是PlookingII自定义错误
        if isinstance(error, PlookingIIError):
            return str(error)

        # 常见系统错误的友好提示
        if isinstance(error, FileNotFoundError):
            return "找不到指定的文件或文件夹"
        if isinstance(error, PermissionError):
            return "没有权限访问该文件或文件夹"
        if isinstance(error, OSError):
            return "系统操作失败"
        if isinstance(error, ValueError):
            return "数据格式错误"
        if isinstance(error, TypeError):
            return "操作参数错误"
        return "发生了未知错误"

    def _get_recovery_suggestion(self, error: Exception) -> str | None:
        """获取恢复建议

        Args:
            error: 异常对象

        Returns:
            Optional[str]: 恢复建议
        """
        error_type = type(error)

        if error_type in self._recovery_suggestions:
            return self._recovery_suggestions[error_type]

        # 系统错误的通用建议
        if isinstance(error, FileNotFoundError | PermissionError):
            return "请检查文件路径和访问权限"
        if isinstance(error, OSError):
            return "请重试操作，或联系技术支持"
        return "请尝试重启应用程序，或联系技术支持"

    def _get_alert_style(self, error: Exception) -> int:
        """获取对话框样式

        Args:
            error: 异常对象

        Returns:
            int: NSAlertStyle值
        """
        if isinstance(error, PlookingIIError):
            try:
                # 兼容不同AppKit版本或测试环境缺失常量的情况
                critical = getattr(NSAlertStyle, "NSCriticalAlertStyle", 2)
                warning = getattr(NSAlertStyle, "NSWarningAlertStyle", 1)
                info = getattr(NSAlertStyle, "NSInformationalAlertStyle", 0)
            except Exception:
                critical, warning, info = 2, 1, 0

            if error.severity == ErrorSeverity.CRITICAL:
                return critical
            if error.severity == ErrorSeverity.HIGH:
                return warning
            return info
        return NSAlertStyle.NSWarningAlertStyle

    def _show_help_dialog(self, error: Exception):
        """显示详细帮助对话框

        Args:
            error: 异常对象
        """
        try:
            alert = NSAlert.alloc().init()
            alert.setMessageText_("错误帮助信息")

            help_text = self._get_detailed_help(error)
            alert.setInformativeText_(help_text)
            alert.addButtonWithTitle_("确定")
            alert.runModal()

        except Exception as e:
            logger.exception("显示帮助对话框失败: %s", e)

    def _get_detailed_help(self, error: Exception) -> str:
        """获取详细帮助信息

        Args:
            error: 异常对象

        Returns:
            str: 详细帮助信息
        """
        error_type = type(error)

        help_texts = {
            DragDropError: (
                "拖拽功能帮助:\n\n"
                "1. 确保拖拽的是包含图片的文件夹\n"
                "2. 支持的图片格式: JPG、JPEG、PNG\n"
                "3. 检查文件夹访问权限\n"
                "4. 尝试使用菜单 '文件' → '打开文件夹' 作为替代方案"
            ),
            FolderValidationError: (
                "文件夹验证帮助:\n\n"
                "1. 检查文件夹是否包含图片文件\n"
                "2. 确认您有访问该文件夹的权限\n"
                "3. 尝试选择父级文件夹\n"
                "4. 检查文件夹是否在网络驱动器上"
            ),
            ImageProcessingError: (
                "图片处理帮助:\n\n"
                "1. 检查图片文件是否损坏\n"
                "2. 确认图片格式被支持 (JPG/JPEG/PNG)\n"
                "3. 检查磁盘空间是否充足\n"
                "4. 尝试重新启动应用程序"
            ),
        }

        return help_texts.get(error_type, "请联系技术支持获取帮助")

    def _show_simple_error(self, message: str):
        """显示简单错误提示（回退方案）

        Args:
            message: 错误消息
        """
        try:
            alert = NSAlert.alloc().init()
            alert.setMessageText_("错误")
            alert.setInformativeText_(message)
            alert.addButtonWithTitle_("确定")
            alert.runModal()
        except Exception:
            # 最后的回退：只记录日志
            logger.exception("无法显示错误对话框: %s", message)

    def show_info_message(self, title: str, message: str):
        """显示信息提示

        Args:
            title: 标题
            message: 消息内容
        """
        try:
            alert = NSAlert.alloc().init()
            alert.setMessageText_(title)
            alert.setInformativeText_(message)
            alert.setAlertStyle_(NSAlertStyle.NSInformationalAlertStyle)
            alert.addButtonWithTitle_("确定")
            alert.runModal()
        except Exception as e:
            logger.exception("显示信息对话框失败: %s", e)

    def show_warning_message(self, title: str, message: str) -> bool:
        """显示警告提示

        Args:
            title: 标题
            message: 消息内容

        Returns:
            bool: 用户是否确认继续
        """
        try:
            alert = NSAlert.alloc().init()
            alert.setMessageText_(title)
            alert.setInformativeText_(message)
            alert.setAlertStyle_(NSAlertStyle.NSWarningAlertStyle)
            alert.addButtonWithTitle_("继续")
            alert.addButtonWithTitle_("取消")

            response = alert.runModal()
            return response == 1000  # 第一个按钮 (继续)

        except Exception as e:
            logger.exception("显示警告对话框失败: %s", e)
            return False


# 全局用户反馈管理器实例
user_feedback_manager = UserFeedbackManager()


def show_error(error: Exception, context: str = ""):
    """显示错误提示的便捷函数

    Args:
        error: 异常对象
        context: 错误上下文
    """
    user_feedback_manager.show_error_dialog(error, context)


def show_info(title: str, message: str):
    """显示信息提示的便捷函数

    Args:
        title: 标题
        message: 消息
    """
    user_feedback_manager.show_info_message(title, message)


def show_warning(title: str, message: str) -> bool:
    """显示警告提示的便捷函数

    Args:
        title: 标题
        message: 消息

    Returns:
        bool: 用户确认结果
    """
    return user_feedback_manager.show_warning_message(title, message)
