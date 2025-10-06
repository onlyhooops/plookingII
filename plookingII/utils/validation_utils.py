"""
验证工具模块

统一的验证和检查工具，消除各模块中重复的验证逻辑。

主要功能：
    - 文件夹路径验证
    - 参数验证和检查
    - 业务规则验证
    - 安全性检查

Author: PlookingII Team
"""

import logging
import os

from plookingII.config.constants import APP_NAME
from plookingII.utils.path_utils import PathUtils

logger = logging.getLogger(APP_NAME)

class ValidationUtils:
    """验证工具类"""

    @staticmethod
    def validate_folder_path(folder_path: str, check_permissions: bool = True) -> bool:
        """验证文件夹路径是否有效

        Args:
            folder_path: 文件夹路径
            check_permissions: 是否检查权限

        Returns:
            bool: 路径是否有效
        """
        try:
            if not folder_path or not isinstance(folder_path, str):
                return False

            # 检查路径是否存在
            if not os.path.exists(folder_path):
                return False

            # 检查是否为文件夹
            if not os.path.isdir(folder_path):
                return False

            # 检查权限
            if check_permissions:
                if not os.access(folder_path, os.R_OK):
                    return False

            return True

        except Exception:
            return False

    @staticmethod
    def validate_recent_folder_path(folder_path: str) -> bool:
        """验证最近文件夹路径是否有效（包含业务规则）

        Args:
            folder_path: 文件夹路径

        Returns:
            bool: 路径是否有效
        """
        try:
            # 基础路径验证
            if not ValidationUtils.validate_folder_path(folder_path):
                return False

            # 排除精选文件夹（以"精选"结尾的文件夹不应该作为根文件夹）
            folder_name = os.path.basename(folder_path.rstrip(os.sep))
            if folder_name.endswith(" 精选") or folder_name == "精选":
                return False

            # 检查路径中是否包含可能导致问题的特殊字符
            problematic_chars = ["#", "?", "%", "&"]
            if any(char in folder_path for char in problematic_chars):
                # 记录但不完全拒绝，可能是合法的文件夹名
                logger.debug("文件夹路径包含特殊字符: %s", folder_path)

            return True

        except Exception:
            return False

    @staticmethod
    def validate_parameter(param, param_name: str, expected_type=None, allow_none: bool = False) -> bool:
        """验证参数是否有效

        Args:
            param: 参数值
            param_name: 参数名称
            expected_type: 期望的类型
            allow_none: 是否允许None值

        Returns:
            bool: 参数是否有效
        """
        try:
            # 检查None值
            if param is None:
                if allow_none:
                    return True
                logger.debug("参数 %s 不能为None", param_name)
                return False

            # 检查类型
            if expected_type is not None:
                if not isinstance(param, expected_type):
                    logger.debug("参数 %s 类型错误，期望 %s，实际 %s",
                               param_name, expected_type.__name__, type(param).__name__)
                    return False

            # 字符串特殊检查
            if isinstance(param, str):
                if not param.strip():  # 空字符串或只有空白字符
                    logger.debug("参数 %s 不能为空字符串", param_name)
                    return False

            return True

        except Exception as e:
            logger.debug("参数验证失败: %s, 错误: %s", param_name, e)
            return False

    @staticmethod
    def validate_path_list(paths: list[str], check_existence: bool = True) -> list[str]:
        """验证路径列表，返回有效的路径

        Args:
            paths: 路径列表
            check_existence: 是否检查路径存在性

        Returns:
            List[str]: 有效的路径列表
        """
        valid_paths = []

        try:
            if not paths or not isinstance(paths, list):
                return valid_paths

            for path in paths:
                if not isinstance(path, str):
                    continue

                if check_existence:
                    if PathUtils.is_valid_path(path):
                        valid_paths.append(path)
                # 只检查格式，不检查存在性
                elif path and path.strip():
                    valid_paths.append(path)

        except Exception as e:
            logger.debug("路径列表验证失败: %s", e)

        return valid_paths

    @staticmethod
    def is_safe_path(path: str, base_path: str | None = None) -> bool:
        """检查路径是否安全（防止路径遍历攻击）

        Args:
            path: 要检查的路径
            base_path: 基础路径（可选）

        Returns:
            bool: 路径是否安全
        """
        try:
            if not path or not isinstance(path, str):
                return False

            # 规范化路径
            normalized_path = PathUtils.canonicalize_path(path)

            # 检查是否包含危险的路径组件
            dangerous_components = ["..", "./", "~/", "/etc/", "/usr/", "/var/"]
            for component in dangerous_components:
                if component in normalized_path:
                    logger.warning("检测到危险路径组件: %s in %s", component, path)
                    return False

            # 如果提供了基础路径，检查是否在允许的范围内
            if base_path:
                normalized_base = PathUtils.canonicalize_path(base_path)
                if not normalized_path.startswith(normalized_base):
                    logger.warning("路径超出允许范围: %s not in %s", path, base_path)
                    return False

            return True

        except Exception as e:
            logger.debug("路径安全检查失败: %s, 错误: %s", path, e)
            return False

    @staticmethod
    def validate_config_value(value, config_name: str, valid_values: list | None = None) -> bool:
        """验证配置值是否有效

        Args:
            value: 配置值
            config_name: 配置名称
            valid_values: 有效值列表（可选）

        Returns:
            bool: 配置值是否有效
        """
        try:
            if value is None:
                logger.debug("配置值 %s 不能为None", config_name)
                return False

            # 检查是否在有效值列表中
            if valid_values is not None:
                if value not in valid_values:
                    logger.debug("配置值 %s 无效，有效值: %s", config_name, valid_values)
                    return False

            return True

        except Exception as e:
            logger.debug("配置值验证失败: %s, 错误: %s", config_name, e)
            return False
