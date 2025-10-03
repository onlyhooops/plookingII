"""
缓存系统适配器

提供向后兼容的适配器，使旧代码可以无缝迁移到新的统一缓存系统。

Author: PlookingII Team
Version: 3.0.0
"""

import logging
from typing import Any

from ...config.constants import APP_NAME, MAX_CACHE_SIZE
from .config import CacheConfig
from .unified_cache import UnifiedCache, get_unified_cache

logger = logging.getLogger(APP_NAME)


class AdvancedImageCacheAdapter:
    """AdvancedImageCache 的适配器

    提供与旧版 AdvancedImageCache 兼容的接口，但内部使用新的 UnifiedCache。
    这是一个适配器模式实现，使现有代码无需修改即可使用新缓存系统。

    迁移指南：
        旧代码:
            from plookingII.core.cache import AdvancedImageCache
            cache = AdvancedImageCache(max_size=100)
            cache.get(key, prefer_preview=False)
            cache.put(key, value, size_mb=10)

        新代码（推荐）:
            from plookingII.core.cache import UnifiedCache, CacheConfig
            config = CacheConfig(active_cache_size=100)
            cache = UnifiedCache(config)
            cache.get(key)
            cache.put(key, value, size=10)
    """

    def __init__(self, max_size=MAX_CACHE_SIZE):
        """初始化适配器

        Args:
            max_size: 最大缓存图片数量（映射到 active_cache_size）
        """
        logger.info(f"Using AdvancedImageCacheAdapter (compatibility mode), max_size={max_size}")

        # 创建配置
        config = CacheConfig(
            active_cache_size=max_size,
            nearby_cache_size=max(20, max_size // 3),  # 预加载缓存约为主缓存的1/3
            preload_count=5,
        )

        # 使用全局统一缓存
        self._cache = get_unified_cache(config)

        # 向后兼容属性
        self.max_size = max_size
        self.cache_hits = 0
        self.cache_misses = 0

    def get(self, key: str, prefer_preview: bool = False,
            target_size: tuple[int, int] | None = None) -> Any | None:
        """获取缓存项（兼容旧接口）

        Args:
            key: 缓存键
            prefer_preview: 已废弃，保留仅为兼容
            target_size: 已废弃，保留仅为兼容

        Returns:
            缓存的值，如果不存在则返回 None
        """
        result = self._cache.get(key, default=None)

        # 更新统计（向后兼容）
        if result is not None:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

        return result

    def put(self, key: str, value: Any, size_mb: float = 0,
            target_key: str | None = None,
            cache_type: str = "main") -> bool:
        """存储缓存项（兼容旧接口）

        Args:
            key: 缓存键
            value: 缓存值
            size_mb: 数据大小（MB）
            target_key: 已废弃，保留仅为兼容
            cache_type: 缓存类型 ('main', 'preview', 'preload', 'progressive')
                       映射: main/preview -> active, preload/progressive -> nearby

        Returns:
            bool: 是否成功存储
        """
        # 根据 cache_type 决定是否是预加载缓存
        is_nearby = cache_type in ("preload", "progressive")

        return self._cache.put(key, value, size=size_mb, is_nearby=is_nearby)

    def remove(self, key: str) -> bool:
        """移除缓存项（兼容旧接口）"""
        return self._cache.remove(key)

    def clear(self) -> None:
        """清空缓存（兼容旧接口）"""
        self._cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息（兼容旧接口）

        Returns:
            Dict: 统计信息字典，格式与旧版兼容
        """
        stats = self._cache.get_stats()

        # 转换为旧格式
        return {
            "size": stats["total_items"],
            "max_size": self.max_size,
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "hit_rate": (self.cache_hits / (self.cache_hits + self.cache_misses) * 100)
                       if (self.cache_hits + self.cache_misses) > 0 else 0.0,
            "current_memory_mb": stats["current_memory_mb"],
            "max_memory_mb": stats["max_memory_mb"],
            "memory_usage_pct": stats["memory_usage_pct"],
            # 新增的详细信息
            "active_cache_size": stats["active_cache_size"],
            "nearby_cache_size": stats["nearby_cache_size"],
        }

    def get_memory_stats(self) -> dict[str, float]:
        """获取内存统计（兼容旧接口）"""
        stats = self._cache.get_stats()
        return {
            "current_mb": stats["current_memory_mb"],
            "max_mb": stats["max_memory_mb"],
            "usage_pct": stats["memory_usage_pct"],
        }

    def get_file_size_mb(self, path: str) -> float:
        """获取文件大小（兼容方法）

        Args:
            path: 文件路径

        Returns:
            float: 文件大小（MB）
        """
        import os
        try:
            size_bytes = os.path.getsize(path)
            return size_bytes / (1024 * 1024)
        except Exception:
            return 0.0

    # 向后兼容的属性
    @property
    def main_cache(self):
        """模拟旧的 main_cache 属性"""
        return _CacheLayerAdapter(self._cache, is_nearby=False)

    @property
    def preview_cache(self):
        """模拟旧的 preview_cache 属性"""
        return _CacheLayerAdapter(self._cache, is_nearby=False)

    @property
    def preload_cache(self):
        """模拟旧的 preload_cache 属性"""
        return _CacheLayerAdapter(self._cache, is_nearby=True)

    @property
    def progressive_cache(self):
        """模拟旧的 progressive_cache 属性"""
        return _CacheLayerAdapter(self._cache, is_nearby=True)


class _CacheLayerAdapter:
    """缓存层适配器（内部使用）"""

    def __init__(self, cache: UnifiedCache, is_nearby: bool):
        self._cache = cache
        self._is_nearby = is_nearby

    def get(self, key: str):
        return self._cache.get(key)

    def put(self, key: str, value: Any, size_mb: float = 0):
        return self._cache.put(key, value, size=size_mb, is_nearby=self._is_nearby)

    def remove(self, key: str):
        return self._cache.remove(key)

    def clear(self):
        # 清空整个缓存（注意：这会影响所有层）
        self._cache.clear()

    def get_stats(self):
        return self._cache.get_stats()


class UnifiedCacheManagerAdapter:
    """UnifiedCacheManager 的适配器

    提供与旧版 UnifiedCacheManager 兼容的接口。
    """

    def __init__(self,
                 hot_cache_size: int = 100,
                 cold_cache_size: int = 500,
                 max_memory_mb: float = 2048,
                 cleanup_threshold: float = 0.8):
        """初始化适配器

        Args:
            hot_cache_size: 热缓存大小（映射到 active_cache_size）
            cold_cache_size: 冷缓存大小（映射到 nearby_cache_size）
            max_memory_mb: 最大内存使用（MB）
            cleanup_threshold: 清理阈值（已废弃）
        """
        logger.info("Using UnifiedCacheManagerAdapter (compatibility mode)")

        # 创建配置
        config = CacheConfig(
            max_memory_mb=max_memory_mb,
            active_cache_size=hot_cache_size,
            nearby_cache_size=cold_cache_size,
            cleanup_threshold=cleanup_threshold,
        )

        # 使用全局统一缓存
        self._cache = get_unified_cache(config)

        # 向后兼容属性
        self.hot_cache_size = hot_cache_size
        self.cold_cache_size = cold_cache_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024

    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存项"""
        return self._cache.get(key, default=default)

    def put(self, key: str, value: Any, size: int = 0, priority: int = 1,
            pixels_mp: float = 0.0, image_category: str = "normal") -> bool:
        """存储缓存项

        Note: pixels_mp 和 image_category 参数已废弃（过度设计）
        """
        size_mb = size / (1024 * 1024) if size > 0 else 0
        return self._cache.put(key, value, size=size_mb, priority=priority)

    def remove(self, key: str) -> bool:
        """移除缓存项"""
        return self._cache.remove(key)

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return self._cache.get_stats()


# 向后兼容的导出
# 使旧代码可以直接使用: from plookingII.core.cache import AdvancedImageCache
AdvancedImageCache = AdvancedImageCacheAdapter
UnifiedCacheManager = UnifiedCacheManagerAdapter

