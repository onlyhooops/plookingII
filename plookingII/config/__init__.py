"""
配置模块

提供PlookingII应用程序的配置管理功能，包括常量定义、配置文件和配置验证。
这个模块集中管理应用程序的所有配置项，确保配置的一致性和可维护性。

主要组件：
    - constants.py: 核心常量定义，包括应用程序信息、支持格式、内存阈值等
    - image_processing_config.py: 图像处理配置，包括EXIF处理策略、性能优化选项等
    - manager.py: 统一配置管理器（v1.4.0新增，推荐使用）

配置特点：
    - 统一管理：通过ConfigManager统一管理所有配置项
    - 类型安全：使用类型注解和验证器确保配置值正确性
    - 环境变量：支持通过环境变量覆盖默认配置
    - 热更新：支持运行时配置变更和观察者模式
    - 文档完整：每个配置项都有详细的说明和用途描述

使用方式：
    from plookingII.config.constants import *
    from plookingII.config.image_processing_config import *

    或

    from plookingII.config import constants, image_processing_config

Author: PlookingII Team
"""

from .constants import (
                        APP_NAME,
                        AUTHOR,
                        COPYRIGHT,
                        IMAGE_PROCESSING_CONFIG,
                        MAX_CACHE_SIZE,
                        MEMORY_THRESHOLD_MB,
                        SUPPORTED_IMAGE_EXTS,
                        VERSION,
)
from .image_processing_config import (
                        CACHE_CONFIG,
                        EXIF_PROCESSING_CONFIG,
                        IMAGE_LOADING_OPTIMIZATIONS,
                        PERFORMANCE_MONITORING,
                        PIL_FALLBACK_CONFIG,
                        QUARTZ_CONFIG,
)
from .manager import Config, ConfigManager, ConfigSchema, ConfigType, get_config, get_config_manager, set_config

__all__ = [
    # 统一配置管理器（推荐）
    "ConfigManager",
    "ConfigType",
    "ConfigSchema",
    "get_config_manager",
    "get_config",
    "set_config",
    "Config",
    # 从constants.py导出的常量
    "APP_NAME",
    "VERSION",
    "AUTHOR",
    "COPYRIGHT",
    "SUPPORTED_IMAGE_EXTS",
    "MAX_CACHE_SIZE",
    "MEMORY_THRESHOLD_MB",
    "IMAGE_PROCESSING_CONFIG",
    # 从image_processing_config.py导出的配置
    "EXIF_PROCESSING_CONFIG",
    "IMAGE_LOADING_OPTIMIZATIONS",
    "QUARTZ_CONFIG",
    "PIL_FALLBACK_CONFIG",
    "CACHE_CONFIG",
    "PERFORMANCE_MONITORING",
]
