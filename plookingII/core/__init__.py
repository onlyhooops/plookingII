"""
PlookingII 核心模块

提供图像浏览应用的核心功能，包括：
- 图像处理和优化算法
- 缓存管理系统
- 远程文件支持 (SMB)
- 预加载和性能优化
- 错误处理和日志系统

主要组件：
    - image_processing: 图像处理和加载策略
    - cache: 多层缓存系统
    - bidirectional_cache: 双向缓存池
    - optimized_loading_strategies: 优化加载策略
    - remote_file_manager: 远程文件管理 (v1.4.0+)
    - smb_optimizer: SMB网络优化 (v1.4.0+)
    - network_cache: 网络缓存管理 (v1.4.0+)
    - preload_manager: 预加载管理器
    - error_handling: 统一错误处理
    - enhanced_logging: 增强日志系统 (v1.4.0+)

Author: PlookingII Team
Version: 1.4.0
"""

# 图像处理核心
from .image_processing import HybridImageProcessor
from .optimized_loading_strategies import OptimizedLoadingStrategyFactory

# 缓存系统 - 优先使用统一缓存
try:
    # 尝试导入新的统一缓存系统（v2.0+）
    from .cache import (
        AdvancedImageCacheAdapter,
        BidirectionalCachePoolAdapter,
    )
    # 为向后兼容，创建别名
    AdvancedImageCache = AdvancedImageCacheAdapter
    BidirectionalCachePool = BidirectionalCachePoolAdapter
    _UNIFIED_CACHE_AVAILABLE = True
except ImportError:
    # 回退到旧的缓存系统
    from .bidirectional_cache import BidirectionalCachePool
    from .cache import AdvancedImageCache
    _UNIFIED_CACHE_AVAILABLE = False

# 性能和监控
from .error_handling import ErrorHandler, error_context, error_handler
from .preload_manager import PreloadManager

# 远程文件支持 (v1.4.0新增) - 按需导入避免语法错误
try:
    _REMOTE_MODULES_AVAILABLE = True
except (ImportError, SyntaxError):
    _REMOTE_MODULES_AVAILABLE = False

# 延迟初始化支持
from .lazy_initialization import lazy_init, profile_startup, startup_profiler

__all__ = [
    # 图像处理核心
    "HybridImageProcessor",
    "AdvancedImageCache",
    "BidirectionalCachePool",
    "OptimizedLoadingStrategyFactory",

    # 远程文件支持 (v1.4.0) - 按模块可用性导出

    # 性能和监控
    "PreloadManager",
    "ErrorHandler",
    "error_handler",
    "error_context",

    # 延迟初始化
    "lazy_init",
    "startup_profiler",
    "profile_startup",
]

# 动态添加远程模块到__all__
if _REMOTE_MODULES_AVAILABLE:
    __all__.extend([
        "NetworkCache",
        "RemoteFileDetector",
        "RemoteFileManager",
        "SMBOptimizer",
    ])
