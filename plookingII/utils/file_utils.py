"""
文件操作工具模块

统一的文件和文件夹操作工具，消除各模块中重复的文件处理逻辑。

主要功能：
    - 文件夹图片检测
    - 文件遍历和过滤
    - 文件类型检查
    - 安全的文件操作

Author: PlookingII Team
"""

import logging
import os

from plookingII.config.constants import APP_NAME, SUPPORTED_IMAGE_EXTS
from plookingII.core.error_handling import FolderValidationError

logger = logging.getLogger(APP_NAME)


class FileUtils:
    """文件操作工具类"""

    @staticmethod
    def is_image_file(filename: str) -> bool:
        """检查文件是否为支持的图片格式

        Args:
            filename: 文件名或路径

        Returns:
            bool: 是否为支持的图片文件
        """
        try:
            return filename.lower().endswith(SUPPORTED_IMAGE_EXTS)
        except Exception:
            return False

    @staticmethod
    def list_files_safe(folder_path: str) -> list[str]:
        """安全地列出文件夹中的文件

        Args:
            folder_path: 文件夹路径

        Returns:
            List[str]: 文件名列表，失败时返回空列表
        """
        try:
            return os.listdir(folder_path)
        except Exception as e:
            logger.debug("无法列出文件夹内容: %s, 错误: %s", folder_path, e)
            return []

    @staticmethod
    def folder_contains_images(folder_path: str, recursive_depth: int = 1) -> bool:
        """检查文件夹是否包含支持的图片文件

        Args:
            folder_path: 文件夹路径
            recursive_depth: 递归检查深度（0=仅当前文件夹，1=检查一层子文件夹）

        Returns:
            bool: 是否包含图片文件

        Raises:
            FolderValidationError: 文件夹访问失败
        """
        try:
            # 检查文件夹本身是否包含图片
            files = FileUtils.list_files_safe(folder_path)
            for filename in files:
                if FileUtils.is_image_file(filename):
                    return True

            # 递归检查子文件夹
            if recursive_depth > 0:
                for item in files:
                    item_path = os.path.join(folder_path, item)
                    if os.path.isdir(item_path):
                        try:
                            sub_files = FileUtils.list_files_safe(item_path)
                            for sub_filename in sub_files:
                                if FileUtils.is_image_file(sub_filename):
                                    return True
                        except Exception:
                            # 子文件夹访问失败，继续检查其他子文件夹
                            continue

            return False

        except Exception as e:
            logger.debug("检查文件夹图片失败: %s, 错误: %s", folder_path, e)
            raise FolderValidationError("无法访问文件夹", folder_path=folder_path) from e

    @staticmethod
    def get_image_files(folder_path: str, recursive: bool = False) -> list[str]:
        """获取文件夹中的所有图片文件

        Args:
            folder_path: 文件夹路径
            recursive: 是否递归搜索子文件夹

        Returns:
            List[str]: 图片文件路径列表
        """
        image_files = []

        try:
            files = FileUtils.list_files_safe(folder_path)

            # 检查当前文件夹中的图片
            for filename in files:
                if FileUtils.is_image_file(filename):
                    image_files.append(os.path.join(folder_path, filename))

            # 递归检查子文件夹
            if recursive:
                for item in files:
                    item_path = os.path.join(folder_path, item)
                    if os.path.isdir(item_path):
                        try:
                            sub_images = FileUtils.get_image_files(item_path, recursive=True)
                            image_files.extend(sub_images)
                        except Exception:
                            # 子文件夹访问失败，继续检查其他子文件夹
                            continue

        except Exception as e:
            logger.debug("获取图片文件失败: %s, 错误: %s", folder_path, e)

        return image_files

    @staticmethod
    def count_image_files(folder_path: str, recursive: bool = False) -> int:
        """统计文件夹中的图片文件数量

        Args:
            folder_path: 文件夹路径
            recursive: 是否递归统计子文件夹

        Returns:
            int: 图片文件数量
        """
        try:
            return len(FileUtils.get_image_files(folder_path, recursive=recursive))
        except Exception:
            return 0

    @staticmethod
    def get_folder_info(folder_path: str) -> tuple[int, int, bool]:
        """获取文件夹信息

        Args:
            folder_path: 文件夹路径

        Returns:
            Tuple[int, int, bool]: (总文件数, 图片文件数, 是否包含子文件夹)
        """
        total_files = 0
        image_files = 0
        has_subfolders = False

        try:
            files = FileUtils.list_files_safe(folder_path)

            for item in files:
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    total_files += 1
                    if FileUtils.is_image_file(item):
                        image_files += 1
                elif os.path.isdir(item_path):
                    has_subfolders = True

        except Exception as e:
            logger.debug("获取文件夹信息失败: %s, 错误: %s", folder_path, e)

        return total_files, image_files, has_subfolders

    @staticmethod
    def is_empty_folder(folder_path: str) -> bool:
        """检查文件夹是否为空

        Args:
            folder_path: 文件夹路径

        Returns:
            bool: 文件夹是否为空
        """
        try:
            files = FileUtils.list_files_safe(folder_path)
            return len(files) == 0
        except Exception:
            return True  # 访问失败视为空文件夹
