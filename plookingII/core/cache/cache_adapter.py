"""
缓存适配器 - 向后兼容层

为旧代码提供兼容接口，允许渐进式迁移到统一缓存系统。

适配器列表：
- AdvancedImageCacheAdapter: 适配 AdvancedImageCache
- BidirectionalCachePoolAdapter: 适配 BidirectionalCachePool
- NetworkCacheAdapter: 适配 NetworkCache

Author: PlookingII Team
Version: 2.0.0
"""

import logging
from typing import Any

from ...config.constants import APP_NAME
from .unified_cache import get_unified_cache

logger = logging.getLogger(APP_NAME)


class AdvancedImageCacheAdapter:
    """AdvancedImageCache 兼容适配器

    适配旧的 AdvancedImageCache 接口到新的 UnifiedCache。

    使用示例：
        >>> cache = AdvancedImageCacheAdapter()
        >>> cache.put(path, image)
        >>> image = cache.get(path)
    """

    def __init__(self, max_size: int = 100):
        """初始化适配器

        Args:
            max_size: 最大缓存项数（兼容参数）
        """
        self._unified = get_unified_cache()
        self._max_size = max_size

        logger.debug("AdvancedImageCacheAdapter initialized (delegating to UnifiedCache)")

    def get(self, path: str, target_size: tuple[int, int] | None = None) -> Any:
        """获取缓存图像

        Args:
            path: 图像路径
            target_size: 目标尺寸（兼容参数，暂不使用）

        Returns:
            缓存的图像，如果不存在则返回 None
        """
        # 构造缓存键（包含 target_size 信息）
        cache_key = self._make_cache_key(path, target_size)
        return self._unified.get(cache_key)

    def put(self, path: str, image: Any, size: float = 0, target_size: tuple[int, int] | None = None) -> bool:
        """存储图像到缓存

        Args:
            path: 图像路径
            image: 图像对象
            size: 图像大小（MB）
            target_size: 目标尺寸（兼容参数）

        Returns:
            bool: 是否成功存储
        """
        cache_key = self._make_cache_key(path, target_size)
        return self._unified.put(cache_key, image, size=size)

    def remove(self, path: str, target_size: tuple[int, int] | None = None) -> bool:
        """移除缓存项

        Args:
            path: 图像路径
            target_size: 目标尺寸

        Returns:
            bool: 是否成功移除
        """
        cache_key = self._make_cache_key(path, target_size)
        return self._unified.remove(cache_key)

    def clear(self) -> None:
        """清空缓存"""
        self._unified.clear()

    def put_new(self, path: str, image: Any, size: float = 0, target_size: tuple[int, int] | None = None) -> bool:
        """存储新图像到缓存（别名方法，兼容旧接口）

        Args:
            path: 图像路径
            image: 图像对象
            size: 图像大小（MB）
            target_size: 目标尺寸（兼容参数）

        Returns:
            bool: 是否成功存储
        """
        # put_new 与 put 行为相同，提供兼容性
        return self.put(path, image, size=size, target_size=target_size)

    def clear_all(self) -> None:
        """清空所有缓存（别名方法，兼容旧接口）"""
        self.clear()

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计

        Returns:
            Dict: 统计信息
        """
        stats = self._unified.get_stats()

        # 适配旧的统计格式
        return {
            "cache_hits": stats["hits"]["total"],
            "cache_misses": stats["misses"],
            "cache_size": stats["total_items"],
            "memory_usage_mb": stats["current_memory_mb"],
            "hit_rate": stats["hit_rate"],
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

    def _make_cache_key(self, path: str, target_size: tuple[int, int] | None = None) -> str:
        """构造缓存键

        Args:
            path: 图像路径
            target_size: 目标尺寸

        Returns:
            str: 缓存键
        """
        if target_size:
            return f"{path}:{target_size[0]}x{target_size[1]}"
        return path


class BidirectionalCachePoolAdapter:
    """BidirectionalCachePool 兼容适配器

    适配旧的 BidirectionalCachePool 接口到新的 UnifiedCache。
    """

    def __init__(
        self,
        preload_count: int = 5,
        keep_previous: int = 3,
        image_processor: Any = None,
        memory_monitor: Any = None,
        advanced_cache: Any = None,
    ):
        """初始化适配器

        Args:
            preload_count: 预加载数量
            keep_previous: 保留之前的数量
            image_processor: 图像处理器（兼容参数）
            memory_monitor: 内存监控器（兼容参数）
            advanced_cache: 高级缓存（兼容参数）
        """
        self._unified = get_unified_cache()
        self._preload_count = preload_count
        self._keep_previous = keep_previous

        logger.debug("BidirectionalCachePoolAdapter initialized")

    def get_sync(self, key: str) -> Any:
        """同步获取缓存项

        Args:
            key: 缓存键

        Returns:
            缓存值
        """
        return self._unified.get(key)

    def put_sync(self, key: str, value: Any, size: float = 0) -> bool:
        """同步存储缓存项

        Args:
            key: 缓存键
            value: 缓存值
            size: 数据大小（MB）

        Returns:
            bool: 是否成功
        """
        return self._unified.put(key, value, size=size)

    def set_current_image_sync(self, key: str, path: str) -> None:
        """设置当前图像（兼容方法）

        Args:
            key: 缓存键
            path: 图像路径
        """
        # 记录当前图像，但不做特殊处理
        logger.debug(f"set_current_image_sync: {path}")

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            Dict: 统计信息
        """
        stats = self._unified.get_stats()

        return {
            "preload_hits": stats["hits"]["hot"],
            "cache_misses": stats["misses"],
            "total_size": stats["total_items"],
        }


class NetworkCacheAdapter:
    """NetworkCache 兼容适配器

    适配旧的 NetworkCache 接口到新的 UnifiedCache。
    """

    def __init__(self, max_size: int = 100, ttl: int = 3600):
        """初始化适配器

        Args:
            max_size: 最大缓存项数
            ttl: 缓存过期时间（秒）
        """
        self._unified = get_unified_cache()
        self._max_size = max_size
        self._ttl = ttl

        logger.debug("NetworkCacheAdapter initialized")

    def get(self, url: str) -> Any:
        """获取网络资源缓存

        Args:
            url: 资源URL

        Returns:
            缓存的资源
        """
        return self._unified.get(url)

    def put(self, url: str, data: Any, size: float = 0) -> bool:
        """存储网络资源到缓存

        Args:
            url: 资源URL
            data: 资源数据
            size: 数据大小（MB）

        Returns:
            bool: 是否成功
        """
        return self._unified.put(url, data, size=size)

    def clear(self) -> None:
        """清空缓存"""
        self._unified.clear()

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            Dict: 统计信息
        """
        return self._unified.get_stats()


# 工厂函数：创建适配器实例
def create_cache_adapter(cache_type: str = "advanced_image", **kwargs) -> Any:
    """创建缓存适配器

    Args:
        cache_type: 缓存类型 ('advanced_image', 'bidirectional', 'network')
        **kwargs: 传递给适配器的参数

    Returns:
        缓存适配器实例
    """
    cache_type = cache_type.lower()

    if cache_type == "advanced_image":
        return AdvancedImageCacheAdapter(**kwargs)
    if cache_type == "bidirectional":
        return BidirectionalCachePoolAdapter(**kwargs)
    if cache_type == "network":
        return NetworkCacheAdapter(**kwargs)
    raise ValueError(f"Unknown cache type: {cache_type}")
