"""
简化统一缓存 - 单一实现

将所有缓存功能合并到一个简洁的实现中，替代当前复杂的多层缓存系统。

设计原则：
- 简单优于复杂：使用标准库 OrderedDict 实现 LRU
- 性能优先：减少抽象层开销
- 易于维护：代码清晰，注释完整
- 线程安全：使用简单的锁机制

Author: PlookingII Team
"""

import contextlib
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    value: Any
    size_mb: float  # 内存大小(MB)
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0


class SimpleImageCache:
    """简化的图片缓存实现

    特性：
    - LRU 淘汰策略
    - 内存大小限制
    - 线程安全
    - 简单的统计

    示例：
        cache = SimpleImageCache(max_items=50, max_memory_mb=500)
        cache.put('img1.jpg', image_data, size_mb=10.5)
        image = cache.get('img1.jpg')
    """

    def __init__(self, max_items: int = 50, max_memory_mb: float = 500.0, name: str = "default"):
        """初始化缓存

        Args:
            max_items: 最大缓存项数
            max_memory_mb: 最大内存占用(MB)
            name: 缓存名称（用于日志）
        """
        self.name = name
        self.max_items = max_items
        self.max_memory_mb = max_memory_mb

        # 使用 OrderedDict 实现 LRU
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

        # 统计信息
        self._current_memory_mb = 0.0
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        logger.info("SimpleImageCache '%s' initialized: max_items=%s, max_memory=%sMB", name, max_items, max_memory_mb)

    def get(self, key: str) -> Any | None:
        """获取缓存项

        Args:
            key: 缓存键

        Returns:
            缓存的值，未找到返回 None
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                # 更新访问信息
                entry.accessed_at = time.time()
                entry.access_count += 1
                # 移到末尾（LRU：最近使用）
                self._cache.move_to_end(key)

                self._hits += 1
                logger.debug("Cache HIT [%s]: %s", self.name, key)
                return entry.value
            self._misses += 1
            logger.debug("Cache MISS [%s]: %s", self.name, key)
            return None

    def put(self, key: str, value: Any, size_mb: float = 1.0):
        """添加到缓存

        Args:
            key: 缓存键
            value: 缓存值
            size_mb: 值的内存大小(MB)
        """
        with self._lock:
            # 如果键已存在，先移除旧的
            if key in self._cache:
                old_entry = self._cache[key]
                self._current_memory_mb -= old_entry.size_mb
                del self._cache[key]

            # 检查是否需要淘汰
            while len(self._cache) >= self.max_items or (self._current_memory_mb + size_mb) > self.max_memory_mb:
                if not self._cache:
                    break
                self._evict_lru()

            # 添加新条目
            entry = CacheEntry(key=key, value=value, size_mb=size_mb)
            self._cache[key] = entry
            self._current_memory_mb += size_mb

            logger.debug(
                "Cache PUT [%s]: %s (size=%.2fMB, total=%.2fMB)", self.name, key, size_mb, self._current_memory_mb
            )

    def remove(self, key: str) -> bool:
        """移除缓存项

        Args:
            key: 缓存键

        Returns:
            是否成功移除
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                self._current_memory_mb -= entry.size_mb
                del self._cache[key]
                logger.debug("Cache REMOVE [%s]: %s", self.name, key)
                return True
            return False

    def clear(self):
        """清空缓存"""
        with self._lock:
            count = len(self._cache)
            memory = self._current_memory_mb
            self._cache.clear()
            self._current_memory_mb = 0.0
            logger.info("Cache CLEAR [%s]: removed %s items, freed %.2fMB", self.name, count, memory)

    def _evict_lru(self):
        """淘汰最久未使用的项（LRU）"""
        if not self._cache:
            return

        # OrderedDict: 第一项是最久未使用的
        key, entry = self._cache.popitem(last=False)
        self._current_memory_mb -= entry.size_mb
        self._evictions += 1

        logger.debug("Cache EVICT [%s]: %s (freed %.2fMB)", self.name, key, entry.size_mb)

    def get_stats(self) -> dict:
        """获取缓存统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0

            return {
                "name": self.name,
                "size": len(self._cache),
                "max_items": self.max_items,
                "memory_mb": round(self._current_memory_mb, 2),
                "max_memory_mb": self.max_memory_mb,
                "memory_usage_pct": round((self._current_memory_mb / self.max_memory_mb * 100), 2),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_pct": round(hit_rate, 2),
                "evictions": self._evictions,
            }

    def __len__(self) -> int:
        """返回缓存项数量"""
        return len(self._cache)

    def __contains__(self, key: str) -> bool:
        """检查键是否存在"""
        return key in self._cache

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"SimpleImageCache(name='{self.name}', "
            f"items={stats['size']}/{stats['max_items']}, "
            f"memory={stats['memory_mb']}/{stats['max_memory_mb']}MB, "
            f"hit_rate={stats['hit_rate_pct']:.1f}%)"
        )


# 全局缓存实例（单例模式）
_global_cache: SimpleImageCache | None = None
_global_cache_lock = threading.Lock()


def get_global_cache() -> SimpleImageCache:
    """获取全局缓存实例（单例）

    Returns:
        全局缓存实例
    """
    global _global_cache  # noqa: PLW0603  # 单例模式的合理使用

    if _global_cache is None:
        with _global_cache_lock:
            if _global_cache is None:
                _global_cache = SimpleImageCache(max_items=50, max_memory_mb=500.0, name="global")

    return _global_cache


def reset_global_cache():
    """重置全局缓存（主要用于测试）"""
    global _global_cache  # noqa: PLW0603  # 单例模式的合理使用

    with _global_cache_lock:
        if _global_cache is not None:
            _global_cache.clear()
        _global_cache = None


# 向后兼容的别名
class AdvancedImageCache(SimpleImageCache):
    """向后兼容：旧的 AdvancedImageCache 接口

    提供旧的 AdvancedImageCache API，包括图片加载和文件大小查询。
    """

    def __init__(self, *args, **kwargs):
        # 兼容旧的参数名
        if "cache_size" in kwargs:
            kwargs["max_items"] = kwargs.pop("cache_size")
        if "max_memory" in kwargs:
            kwargs["max_memory_mb"] = kwargs.pop("max_memory")

        super().__init__(*args, **kwargs)
        logger.debug("Using AdvancedImageCache (compatibility mode)")

    def load_image_with_strategy(
        self, image_path: str, strategy: str = "auto", target_size: tuple | None = None, force_reload: bool = False
    ) -> Any:
        """使用指定策略加载图片（兼容方法）

        Args:
            image_path: 图片路径
            strategy: 加载策略 ('auto', 'optimized', 'preview', 'fast')
            target_size: 目标尺寸
            force_reload: 是否强制重新加载

        Returns:
            加载的图片对象，失败返回None
        """
        try:
            # 如果不强制重载，先尝试从缓存获取
            if not force_reload:
                cached = self.get(image_path, target_size=target_size)
                if cached is not None:
                    logger.debug("Cache hit for %s", image_path)
                    return cached

            # 使用加载器加载图片
            from ..core.loading import get_loader

            loader = get_loader(strategy)

            # 加载图片
            image = loader.load(image_path, target_size=target_size)

            if image is not None:
                # 估算图片大小（简化）
                size_mb = 5.0  # 默认估算值
                try:
                    import os

                    file_size = os.path.getsize(image_path)
                    size_mb = file_size / (1024 * 1024)
                except Exception:
                    pass

                # 存入缓存
                self.put(image_path, image, size_mb=size_mb)
                logger.debug("Loaded and cached %s using %s", image_path, strategy)

            return image

        except Exception as e:
            logger.exception("Failed to load image %s: %s", image_path, e)
            return None

    def get_file_size_mb(self, file_path: str) -> float:
        """获取文件大小（MB）

        Args:
            file_path: 文件路径

        Returns:
            文件大小（MB），失败返回0.0
        """
        try:
            import os

            if os.path.exists(file_path):
                size_bytes = os.path.getsize(file_path)
                return size_bytes / (1024 * 1024)
        except Exception as e:
            logger.debug("Failed to get file size for %s: %s", file_path, e)
        return 0.0


class UnifiedCacheManager(SimpleImageCache):
    """向后兼容：旧的 UnifiedCacheManager 接口"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.debug("Using UnifiedCacheManager (compatibility mode)")


class BidirectionalCachePool(SimpleImageCache):
    """向后兼容：旧的 BidirectionalCachePool 接口

    提供旧的 BidirectionalCachePool API，但内部使用 SimpleImageCache。
    某些高级功能（如预加载）被简化或禁用。
    """

    def __init__(self, *args, **kwargs):
        # 保存需要的参数
        self._image_processor = kwargs.pop("image_processor", None)
        self._advanced_cache = kwargs.pop("advanced_cache", None)

        # 移除旧的不兼容参数
        kwargs.pop("preload_count", None)
        kwargs.pop("keep_previous", None)
        kwargs.pop("memory_monitor", None)

        super().__init__(*args, **kwargs)

        # 内部状态
        self._current_sequence = []
        self._current_index = -1

        logger.debug("Using BidirectionalCachePool (compatibility mode)")

    def set_current_image_sync(self, image_path: str, sync_key: str) -> None:
        """设置当前图片（兼容方法）"""
        try:
            if image_path in self._current_sequence:
                self._current_index = self._current_sequence.index(image_path)
        except Exception:
            pass

    def set_preload_window(self, preload_count: int = 5) -> None:
        """设置预加载窗口（兼容方法，简化实现）"""
        # 简化：不做实际预加载，只记录设置

    def set_sequence(self, images: list) -> None:
        """设置图片序列（兼容方法）"""
        self._current_sequence = images if images else []
        self._current_index = 0 if images else -1

    def shutdown(self) -> None:
        """关闭缓存池（兼容方法）"""
        with contextlib.suppress(Exception):
            self.clear()


__all__ = [
    # 向后兼容
    "AdvancedImageCache",
    "BidirectionalCachePool",
    "CacheEntry",
    "SimpleImageCache",
    "UnifiedCacheManager",
    "get_global_cache",
    "reset_global_cache",
]
