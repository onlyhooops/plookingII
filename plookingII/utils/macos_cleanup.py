"""
macOS 系统级清理工具

用于清理 macOS 系统中与应用相关的缓存和记录，
特别是 Dock 菜单中显示的最近打开项目。
"""

import logging
import os
import subprocess
from pathlib import Path

from ..config.constants import APP_NAME

logger = logging.getLogger(APP_NAME)


class MacOSCleanupManager:
    """macOS 系统级清理管理器"""

    @staticmethod
    def clear_recent_documents():
        """清除 macOS 系统的最近文档记录

        这会清除：
        1. NSDocumentController 记录
        2. 系统的"最近项目"列表
        3. Dock 菜单中显示的最近打开项目

        Returns:
            bool: 清理是否成功
        """
        try:
            # 方法1: 清除 NSRecentDocumentRecords
            try:
                from Foundation import NSUserDefaults

                defaults = NSUserDefaults.standardUserDefaults()
                defaults.removeObjectForKey_("NSRecentDocumentRecords")
                defaults.synchronize()
                logger.info("已清除 NSRecentDocumentRecords")
            except Exception as e:
                logger.debug(f"清除 NSRecentDocumentRecords 失败: {e}")

            # 方法2: 使用 AppleScript 清除最近项目
            applescript = """
            tell application "System Events"
                tell appearance preferences
                    set recent documents limit to 0
                    set recent applications limit to 0
                    set recent servers limit to 0
                end tell
            end tell

            tell application "System Events"
                tell appearance preferences
                    set recent documents limit to 10
                    set recent applications limit to 10
                    set recent servers limit to 10
                end tell
            end tell
            """

            try:
                subprocess.run(["osascript", "-e", applescript], check=False, capture_output=True, timeout=5)
                logger.info("已通过 AppleScript 重置最近项目")
            except Exception as e:
                logger.debug(f"AppleScript 清理失败: {e}")

            # 方法3: 清除 Dock 持久化数据
            try:
                home = Path.home()
                recent_dirs = [
                    home / "Library" / "Preferences" / "com.apple.recentitems.plist",
                ]

                for recent_file in recent_dirs:
                    if recent_file.exists():
                        try:
                            # 使用 defaults 命令清除
                            subprocess.run(
                                ["defaults", "delete", "com.apple.recentitems"],
                                check=False,
                                capture_output=True,
                                timeout=5,
                            )
                            logger.info(f"已清除 {recent_file.name}")
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"清除持久化数据失败: {e}")

            return True

        except Exception as e:
            logger.warning(f"清除 macOS 最近文档失败: {e}")
            return False

    @staticmethod
    def clear_app_recent_documents():
        """仅清除当前应用的最近文档记录

        Returns:
            bool: 清理是否成功
        """
        try:
            from Foundation import NSDocumentController

            # 清除 NSDocumentController 的最近文档
            doc_controller = NSDocumentController.sharedDocumentController()
            doc_controller.clearRecentDocuments_(None)

            logger.info(f"已清除 {APP_NAME} 的最近文档记录")
            return True

        except Exception as e:
            logger.debug(f"清除应用最近文档失败: {e}")
            return False

    @staticmethod
    def is_development_environment() -> bool:
        """检测是否在开发环境中运行

        开发环境特征：
        1. 从源码目录运行（存在 .git 目录）
        2. 设置了开发环境变量
        3. 在虚拟环境中运行

        Returns:
            bool: 是否为开发环境
        """
        # 检查环境变量
        if os.environ.get("PLOOKINGII_DEV") == "1":
            return True

        # 检查是否在虚拟环境中
        if hasattr(os.sys, "real_prefix") or (hasattr(os.sys, "base_prefix") and os.sys.base_prefix != os.sys.prefix):
            return True

        # 检查是否存在 .git 目录（从源码运行）
        try:
            current_dir = Path(__file__).resolve().parent
            project_root = current_dir.parent.parent
            if (project_root / ".git").exists():
                return True
        except Exception:
            pass

        return False

    @staticmethod
    def auto_cleanup_if_dev():
        """如果在开发环境中，自动清理最近记录

        Returns:
            bool: 是否执行了清理
        """
        if MacOSCleanupManager.is_development_environment():
            logger.info("检测到开发环境，自动清理 macOS 最近文档记录")
            MacOSCleanupManager.clear_recent_documents()
            MacOSCleanupManager.clear_app_recent_documents()
            return True
        return False


def clear_macos_recent_items():
    """清理 macOS 最近项目（便捷函数）"""
    manager = MacOSCleanupManager()
    manager.clear_recent_documents()
    manager.clear_app_recent_documents()
