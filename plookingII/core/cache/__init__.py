"""
统一缓存系统（重构版 V3.0）

简化的2层缓存架构：
- Active Cache: 当前活跃图片
- Nearby Cache: 预加载的相邻图片

主要改进：
- 合并4个重复的缓存管理器为1个
- 简化4层缓存为2层（active + nearby）
- 统一缓存配置（CacheConfig）
- 向后兼容适配器（无需修改现有代码）

主要组件：
- UnifiedCache: 统一缓存核心实现（重构版）
- CacheConfig: 统一缓存配置
- CachePolicy: 缓存淘汰策略（推荐使用LRU）
- CacheAdapter: 向后兼容适配器
- CacheMonitor: 缓存监控和统计

Author: PlookingII Team
Version: 3.0.0 (Refactored)
Date: 2025-10-02
"""

from .adapters import (
    AdvancedImageCacheAdapter,
    UnifiedCacheManagerAdapter,
)
from .cache_monitor import CacheMonitor, CacheStats
from .cache_policy import ARCPolicy, CachePolicy, LFUPolicy, LRUPolicy
from .config import CacheConfig
from .unified_cache import CacheEntry, UnifiedCache, get_unified_cache, reset_unified_cache

# 向后兼容别名（让旧代码无缝工作）
AdvancedImageCache = AdvancedImageCacheAdapter
UnifiedCacheManager = UnifiedCacheManagerAdapter

__all__ = [
    # 核心类
    "UnifiedCache",
    "get_unified_cache",
    "reset_unified_cache",
    "CacheEntry",

    # 配置类
    "CacheConfig",

    # 策略类
    "CachePolicy",
    "LRUPolicy",
    "LFUPolicy",
    "ARCPolicy",

    # 适配器（向后兼容）
    "AdvancedImageCacheAdapter",
    "UnifiedCacheManagerAdapter",

    # 向后兼容别名
    "AdvancedImageCache",
    "UnifiedCacheManager",

    # 监控类
    "CacheStats",
    "CacheMonitor",
]

__version__ = "3.0.0"
