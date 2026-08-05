"""
业务管理器模块

提供PlookingII应用程序的核心业务逻辑管理器类，负责处理图像、文件夹、操作等核心业务逻辑。
这些管理器类实现了应用程序的主要功能，与UI控制器分离，确保业务逻辑的可复用性和可测试性。

主要管理器：
    - ImageManager: 图像管理，负责图像加载、缓存、处理策略等
    - FolderManager: 文件夹管理，负责文件夹扫描、导航、历史记录等
    - OperationManager: 操作管理，负责文件操作、历史记录、缓存清理等

设计原则：
    - 单一职责：每个管理器只负责一个特定的业务领域
    - 依赖注入：通过构造函数注入依赖，便于测试和配置
    - 错误处理：统一的异常处理和错误恢复机制
    - 性能优化：智能缓存、异步处理、内存管理等优化策略

Author: PlookingII Team
"""

import logging

from .folder_manager import FolderManager
from .operation_manager import OperationManager

logger = logging.getLogger("PlookingII")

# 导入核心管理器
from .image_manager import ImageManager
from .image_update_manager import ImageUpdateManager

__all__ = [
    "FolderManager",
    "ImageManager",
    "ImageUpdateManager",
    "OperationManager",
]
