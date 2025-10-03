"""
PlookingII 工具模块

提供应用程序通用的工具函数和辅助类，消除代码重复，提高代码复用性。

主要模块：
    - path_utils: 路径处理和规范化工具
    - file_utils: 文件和文件夹操作工具  
    - validation_utils: 验证和检查工具
    - error_utils: 错误处理辅助工具

Author: PlookingII Team
Version: 1.0.0
"""

from .error_utils import ErrorCollector, handle_exceptions, safe_execute
from .file_utils import FileUtils
from .path_utils import PathUtils
from .validation_utils import ValidationUtils

__all__ = [
    "ErrorCollector",
    "FileUtils",
    "PathUtils",
    "ValidationUtils",
    "handle_exceptions",
    "safe_execute"
]
