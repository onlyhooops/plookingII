"""
路径处理工具模块

统一的路径规范化、验证和处理工具，消除各模块中重复的路径处理逻辑。

主要功能：
    - 路径规范化和标准化
    - 符号链接处理
    - Unicode路径规范化
    - 路径验证和检查

Author: PlookingII Team
"""

import logging
import os

try:
    import unicodedata as _ud
except Exception:
    _ud = None

from ..config.constants import APP_NAME

logger = logging.getLogger(APP_NAME)

class PathUtils:
    """路径处理工具类"""

    @staticmethod
    def normalize_path_basic(path: str) -> str:
        """执行基础路径规范化操作

        Args:
            path: 原始文件路径

        Returns:
            str: 基础规范化后的路径
        """
        if not path:
            return path
        path = os.path.expanduser(path)
        path = os.path.normpath(path)
        return path

    @staticmethod
    def resolve_symlinks_safe(path: str) -> str:
        """安全地解析符号链接

        Args:
            path: 文件路径

        Returns:
            str: 解析后的路径，失败时返回原路径
        """
        try:
            # 尝试解析符号链接，但不强制要求成功
            resolved = os.path.realpath(path)
            # 验证解析后的路径确实存在
            if os.path.exists(resolved):
                return resolved
            logger.debug("符号链接解析后路径不存在，使用原路径: %s -> %s", path, resolved)
            return path
        except Exception:
            logger.debug("符号链接解析失败，使用原路径: %s", path, exc_info=True)
            return path

    @staticmethod
    def normalize_unicode_safe(path: str) -> str:
        """安全的Unicode路径规范化

        Args:
            path: 文件路径

        Returns:
            str: Unicode规范化后的路径
        """
        if not _ud or not path:
            return path

        try:
            # 使用NFC规范化，确保相同字符的不同Unicode表示统一
            normalized = _ud.normalize("NFC", path)
            return normalized
        except Exception:
            logger.debug("Unicode路径规范化失败，使用原路径: %s", path, exc_info=True)
            return path

    @staticmethod
    def canonicalize_path(path: str, resolve_symlinks: bool = True) -> str:
        """标准化文件路径，确保在macOS上的稳定哈希和相等性比较

        处理符号链接、Unicode规范化和路径格式统一，避免同一路径的不同表示
        导致哈希不一致或比较失败的问题。

        Args:
            path: 原始文件路径
            resolve_symlinks: 是否解析符号链接

        Returns:
            str: 标准化后的绝对路径

        Note:
            - 展开用户目录（~）
            - 规范化路径分隔符和移除尾随组件
            - 可选解析符号链接到真实路径
            - 确保返回绝对路径
            - Unicode NFC规范化，避免视觉相同路径的字节差异
            - 异常安全：任何步骤失败都返回可用路径
        """
        try:
            # 基础路径规范化
            path = PathUtils.normalize_path_basic(path)

            # 可选的符号链接解析
            if resolve_symlinks:
                path = PathUtils.resolve_symlinks_safe(path)

            # 确保绝对路径
            path = os.path.abspath(path)

            # Unicode规范化
            path = PathUtils.normalize_unicode_safe(path)

            return path
        except Exception:
            logger.debug("路径标准化失败，返回原始输入: %s", path, exc_info=True)
            return path

    @staticmethod
    def normalize_folder_path(folder_path: str, resolve_symlinks: bool = False) -> str:
        """规范化文件夹路径

        Args:
            folder_path: 原始文件夹路径
            resolve_symlinks: 是否解析符号链接（默认False避免路径变化）

        Returns:
            str: 规范化后的路径
        """
        try:
            if resolve_symlinks:
                # 使用完整的路径规范化
                return PathUtils.canonicalize_path(folder_path, resolve_symlinks=True)
            # 简化处理：只移除末尾斜杠，不解析符号链接避免路径变化
            normalized = folder_path.rstrip(os.sep)
            return normalized
        except Exception:
            # 规范化失败时返回原路径
            logger.debug("文件夹路径规范化失败: %s", folder_path, exc_info=True)
            return folder_path

    @staticmethod
    def is_valid_path(path: str) -> bool:
        """检查路径是否有效

        Args:
            path: 文件或文件夹路径

        Returns:
            bool: 路径是否有效
        """
        try:
            if not path or not isinstance(path, str):
                return False

            # 检查路径是否存在
            return os.path.exists(path)
        except Exception:
            return False

    @staticmethod
    def is_valid_folder(folder_path: str) -> bool:
        """检查文件夹路径是否有效

        Args:
            folder_path: 文件夹路径

        Returns:
            bool: 文件夹路径是否有效
        """
        try:
            if not PathUtils.is_valid_path(folder_path):
                return False

            # 检查是否为文件夹
            return os.path.isdir(folder_path)
        except Exception:
            return False
