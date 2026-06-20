"""
PlookingII 版本号管理模块

这是项目中版本号的**唯一真源（Single Source of Truth）**。

版本号管理规则：
1. 所有版本号信息都从这个文件导入
2. 发布新版本时，只需要修改这个文件中的 __version__
3. 遵循语义化版本规范（Semantic Versioning 2.0.0）
   格式：MAJOR.MINOR.PATCH
   - MAJOR: 不兼容的API变更
   - MINOR: 向后兼容的功能新增
   - PATCH: 向后兼容的问题修复

使用示例：
    from plookingII.__version__ import __version__
    print(f"PlookingII v{__version__}")

Author: PlookingII Team
Date: 2025-10-06
"""

# 🎯 唯一版本号定义 - 发布新版本时只需修改这里
__version__ = "1.8.0"

# 版本号别名（向后兼容）
VERSION = __version__
APP_VERSION = __version__

# 版本信息
VERSION_INFO = tuple(int(x) for x in __version__.split("."))
MAJOR, MINOR, PATCH = VERSION_INFO

# 版本描述
VERSION_DESCRIPTION = "Core Algorithm & Resource Optimization"

# 发布日期
RELEASE_DATE = "2025-04-25"


def get_version() -> str:
    """获取版本号字符串

    Returns:
        str: 版本号，例如 "1.7.0"
    """
    return __version__


def get_version_info() -> tuple[int, int, int]:
    """获取版本号元组

    Returns:
        tuple: (major, minor, patch)
    """
    return VERSION_INFO


def get_full_version() -> str:
    """获取完整版本信息

    Returns:
        str: 完整版本描述，例如 "PlookingII v1.7.0 (Architecture Refinement)"
    """
    return f"PlookingII v{__version__} ({VERSION_DESCRIPTION})"


# 导出符号
__all__ = [
    "APP_VERSION",
    "MAJOR",
    "MINOR",
    "PATCH",
    "RELEASE_DATE",
    "VERSION",
    "VERSION_DESCRIPTION",
    "VERSION_INFO",
    "__version__",
    "get_full_version",
    "get_version",
    "get_version_info",
]
