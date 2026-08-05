"""
PlookingII 核心模块

提供图像浏览应用的核心功能，包括：
- 图像处理和优化算法
- 缓存管理系统
- 远程文件支持 (SMB)
- 错误处理和日志系统

主要组件：
    - image_processing: 图像处理和加载策略
    - simple_cache: 统一缓存系统
    - optimized_loading_strategies: 优化加载策略
    - remote_file_manager: 远程文件管理 (v1.4.0+)
    - smb_optimizer: SMB网络优化 (v1.4.0+)
    - network_cache: 网络缓存管理 (v1.4.0+)
    - error_handling: 统一错误处理
    - enhanced_logging: 增强日志系统 (v1.4.0+)

Author: PlookingII Team
"""

# 图像处理核心
from .image_processing import HybridImageProcessor
from .optimized_loading_strategies import OptimizedLoadingStrategyFactory

# 缓存系统 - 使用简化的统一缓存（v2.0+）
from .simple_cache import (
    AdvancedImageCache,
    BidirectionalCachePool,
    SimpleImageCache,
    get_global_cache,
)

_UNIFIED_CACHE_AVAILABLE = True

# 性能和监控
from .error_handling import ErrorHandler, error_context, error_handler

__all__ = [
    "AdvancedImageCache",
    "BidirectionalCachePool",
    "ErrorHandler",
    # 图像处理核心
    "HybridImageProcessor",
    "OptimizedLoadingStrategyFactory",
    "error_context",
    "error_handler",
]
