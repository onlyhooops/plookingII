#!/usr/bin/env python3
"""
统一缓存接口

为所有缓存系统提供统一的接口定义，确保缓存系统的一致性和可互换性。

Author: PlookingII Team
Version: 1.4.0
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class CacheType(Enum):
    """缓存类型枚举"""
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    HYBRID = "hybrid"


class CacheStrategy(Enum):
    """缓存策略枚举"""
    LRU = "lru"           # 最近最少使用
    LFU = "lfu"           # 最少使用频率
    FIFO = "fifo"         # 先进先出
    SIZE_BASED = "size"   # 基于大小
    PRIORITY = "priority"  # 基于优先级


class CacheInterface(ABC):
    """缓存系统统一接口"""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """获取缓存项

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在返回None
        """

    @abstractmethod
    def set(self, key: str, value: Any, **kwargs) -> bool:
        """设置缓存项

        Args:
            key: 缓存键
            value: 缓存值
            **kwargs: 额外参数（如ttl, priority等）

        Returns:
            是否设置成功
        """

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存项

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """

    @abstractmethod
    def clear(self) -> bool:
        """清空所有缓存

        Returns:
            是否清空成功
        """

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查缓存项是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在
        """

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计信息

        Returns:
            包含统计信息的字典
        """

    @abstractmethod
    def get_size(self) -> int:
        """获取缓存大小（项目数量）

        Returns:
            缓存项目数量
        """

    @abstractmethod
    def get_memory_usage(self) -> int:
        """获取内存使用量（字节）

        Returns:
            内存使用量
        """

    def get_hit_rate(self) -> float:
        """获取缓存命中率

        Returns:
            命中率（0.0-1.0）
        """
        stats = self.get_stats()
        hits = stats.get("hits", 0)
        total = hits + stats.get("misses", 0)
        return hits / total if total > 0 else 0.0


class CacheManagerInterface(ABC):
    """缓存管理器接口"""

    @abstractmethod
    def get_cache(self, cache_name: str) -> CacheInterface | None:
        """获取指定的缓存实例

        Args:
            cache_name: 缓存名称

        Returns:
            缓存实例，如果不存在返回None
        """

    @abstractmethod
    def register_cache(self, cache_name: str, cache: CacheInterface) -> bool:
        """注册缓存实例

        Args:
            cache_name: 缓存名称
            cache: 缓存实例

        Returns:
            是否注册成功
        """

    @abstractmethod
    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """获取所有缓存的统计信息

        Returns:
            包含所有缓存统计信息的字典
        """

    @abstractmethod
    def cleanup_all(self) -> bool:
        """清理所有缓存

        Returns:
            是否清理成功
        """


class ImageCacheInterface(CacheInterface):
    """图像缓存专用接口"""

    @abstractmethod
    def cache_image(self, file_path: str, image_data: Any, **kwargs) -> bool:
        """缓存图像数据

        Args:
            file_path: 图像文件路径
            image_data: 图像数据
            **kwargs: 额外参数（如size, format等）

        Returns:
            是否缓存成功
        """

    @abstractmethod
    def get_image(self, file_path: str) -> Any | None:
        """获取图像数据

        Args:
            file_path: 图像文件路径

        Returns:
            图像数据，如果不存在返回None
        """

    @abstractmethod
    def preload_images(self, file_paths: list[str]) -> int:
        """预加载图像

        Args:
            file_paths: 图像文件路径列表

        Returns:
            成功预加载的数量
        """


class NetworkCacheInterface(CacheInterface):
    """网络缓存专用接口"""

    @abstractmethod
    def cache_remote_file(self, remote_path: str, local_path: str, **kwargs) -> bool:
        """缓存远程文件

        Args:
            remote_path: 远程文件路径
            local_path: 本地缓存路径
            **kwargs: 额外参数（如ttl等）

        Returns:
            是否缓存成功
        """

    @abstractmethod
    def get_cached_file(self, remote_path: str) -> str | None:
        """获取缓存的远程文件本地路径

        Args:
            remote_path: 远程文件路径

        Returns:
            本地文件路径，如果不存在返回None
        """

    @abstractmethod
    def is_file_cached(self, remote_path: str) -> bool:
        """检查远程文件是否已缓存

        Args:
            remote_path: 远程文件路径

        Returns:
            是否已缓存
        """

    @abstractmethod
    def cleanup_expired(self) -> int:
        """清理过期的缓存文件

        Returns:
            清理的文件数量
        """
