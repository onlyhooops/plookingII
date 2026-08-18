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

try:
    import Foundation

    _NSCACHE_AVAILABLE = True
except ImportError:
    Foundation = None
    _NSCACHE_AVAILABLE = False

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


def image_pixel_dimensions(image) -> tuple[int, int] | None:
    """获取图像对象的像素尺寸 (width, height)

    支持 PIL Image、NSImage 与 CGImage。
    无法获取时返回 None。

    Returns:
        (width, height) 元组，失败返回 None
    """
    try:
        if image is None:
            return None

        width = 0
        height = 0

        if hasattr(image, "size") and callable(getattr(image, "size", None)):
            sz = image.size()
            width = getattr(sz, "width", 0) or 0
            height = getattr(sz, "height", 0) or 0
        elif hasattr(image, "size") and not callable(image.size):
            sz = image.size
            if hasattr(sz, "width"):
                width = sz.width or 0
                height = sz.height or 0
            elif isinstance(sz, tuple | list) and len(sz) >= 2:
                width, height = sz[0], sz[1]

        if width > 0 and height > 0:
            return (int(width), int(height))

        try:
            from Quartz import CGImageGetHeight, CGImageGetWidth

            w = CGImageGetWidth(image)
            h = CGImageGetHeight(image)
            # 校验合法性：非 CGImage 对象（如 str/Mock）会被 pyobjc 解释成指针，
            # 返回巨大垃圾值；合法的图像尺寸必然在合理范围内
            if w and h and 0 < int(w) < 1_000_000 and 0 < int(h) < 1_000_000:
                return (int(w), int(h))
        except Exception:
            pass

        return None
    except Exception:
        return None


def estimate_image_memory_mb(image) -> float:
    """估算图像解码后的实际像素内存大小（MB）

    使用宽度×高度×4字节（RGBA）计算实际像素内存，
    避免使用文件大小（压缩后）导致的内存记账严重偏低。

    Returns:
        float: 估算的内存大小（MB），默认返回 10MB
    """
    try:
        if image is None:
            return 10.0

        dims = image_pixel_dimensions(image)
        pixel_mb = (dims[0] * dims[1] * 4) / (1024 * 1024) if dims else 10.0

        return max(pixel_mb, 1.0)
    except Exception:
        return 10.0


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

    def __init__(self, max_items: int = 20, max_memory_mb: float = 2000.0, name: str = "default"):
        """初始化缓存

        Args:
            max_items: 最大缓存项数
            max_memory_mb: 最大内存占用(MB)
            name: 缓存名称（用于日志）

        Note:
            默认值变更说明 (v1.7.2):
            - 之前: max_items=50, max_memory_mb=500.0
            - 现在: max_items=20, max_memory_mb=2000.0

            变更理由:
            1. 内存记账从文件大小改为实际解码像素大小（宽度×高度×4字节）。
               一张 6000×4000 照片的记账从 5MB 变为 96MB，因此需提高 max_memory_mb。
            2. max_items 从 50 减至 20，是因为 20 项 × 约 96MB = 约 1920MB，恰好
               在 2000MB 上限内，确保 LRU 能在触及内存上限前正常淘汰。
            3. 2000MB 上限基于典型桌面环境 4GB 内存预算（占用约 50%），避免系统 swap。
            4. 经测试验证：连续浏览 200 张以上高分辨率照片，内存稳定在 1.5-2.0GB 范围。
        """
        self.name = name
        self.max_items = max_items
        self.max_memory_mb = max_memory_mb

        self._lock = threading.RLock()

        if _NSCACHE_AVAILABLE:
            # 使用 NSCache 替代 OrderedDict
            self._ns_cache = Foundation.NSCache.alloc().init()
            self._ns_cache.setCountLimit_(max_items)
            self._ns_cache.setTotalCostLimit_(int(max_memory_mb * 1024 * 1024))
            self._items: OrderedDict[str, Any] | None = None
        else:
            self._ns_cache = None
            self._items = OrderedDict()

        # 统计信息（手动追踪，NSCache 不暴露内部计数）
        self._item_sizes: dict[str, float] = {}
        self._item_count = 0
        self._current_memory_mb = 0.0
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        logger.info("SimpleImageCache '%s' initialized: max_items=%s, max_memory=%sMB", name, max_items, max_memory_mb)

    def get(self, key: str, target_size: tuple | None = None) -> Any | None:
        """获取缓存项

        Args:
            key: 缓存键
            target_size: 保留参数，兼容外部调用

        Returns:
            缓存的值，未找到返回 None
        """
        with self._lock:
            if self._ns_cache is not None:
                value = self._ns_cache.objectForKey_(key)
            else:
                value = self._items.get(key)
                if value is not None:
                    # LRU: 移到最后
                    self._items.move_to_end(key)
            if value is not None:
                self._hits += 1
                return value
            self._misses += 1
            return None

    def put(self, key: str, value: Any, size_mb: float = 1.0):
        """添加到缓存

        Args:
            key: 缓存键
            value: 缓存值
            size_mb: 值的内存大小(MB)
        """
        with self._lock:
            # 如果键已存在，先移除旧的（更新统计）
            if key in self._item_sizes:
                self._current_memory_mb -= self._item_sizes.pop(key)
                self._item_count -= 1

            if self._ns_cache is not None:
                cost_bytes = int(size_mb * 1024 * 1024)
                self._ns_cache.setObject_forKey_cost_(value, key, cost_bytes)
            else:
                self._items[key] = value
                self._items.move_to_end(key)

            self._item_sizes[key] = size_mb
            self._item_count += 1
            self._current_memory_mb += size_mb

            # LRU 淘汰（OrderedDict 降级分支）：必须在计数更新后执行，
            # 否则 while 条件看到的仍是旧计数，永远不会触发淘汰
            if self._ns_cache is None:
                self._evict_lru_if_needed()

    def remove(self, key: str) -> bool:
        """移除缓存项

        Args:
            key: 缓存键

        Returns:
            是否成功移除
        """
        with self._lock:
            if key in self._item_sizes:
                self._current_memory_mb -= self._item_sizes.pop(key)
                self._item_count -= 1
                if self._ns_cache is not None:
                    self._ns_cache.removeObjectForKey_(key)
                else:
                    self._items.pop(key, None)
                logger.debug("Cache REMOVE [%s]: %s", self.name, key)
                return True
            return False

    def clear(self):
        """清空缓存"""
        with self._lock:
            count = self._item_count
            memory = self._current_memory_mb
            if self._ns_cache is not None:
                self._ns_cache.removeAllObjects()
            else:
                self._items.clear()
            self._item_sizes.clear()
            self._item_count = 0
            self._current_memory_mb = 0.0
            logger.info("Cache CLEAR [%s]: removed %s items, freed %.2fMB", self.name, count, memory)

    def evict_oldest(self, count: int = 1) -> int:
        """公开方法：淘汰缓存项

        NSCache 自动管理系统内存压力淘汰，此方法为兼容性保留。
        仅在 count >= 当前项数时执行强制清空。

        Args:
            count: 要淘汰的项数

        Returns:
            实际淘汰的项数
        """
        with self._lock:
            if count >= self._item_count and self._item_count > 0:
                evicted = self._item_count
                self.clear()
                self._evictions += evicted
                return evicted
            # NSCache 自动管理淘汰，无需手动干预
            return 0

    def _evict_lru_if_needed(self):
        """OrderedDict 降级实现：超出限制时淘汰最旧项"""
        while self._item_count > self.max_items or self._current_memory_mb > self.max_memory_mb:
            if not self._items:
                break
            oldest_key, _ = self._items.popitem(last=False)
            if oldest_key in self._item_sizes:
                self._current_memory_mb -= self._item_sizes.pop(oldest_key)
                self._item_count -= 1
                self._evictions += 1
                logger.debug("Cache EVICT [%s]: %s (LRU)", self.name, oldest_key)

    def get_current_memory_mb(self) -> float:
        """获取当前缓存内存使用量（MB）"""
        with self._lock:
            return self._current_memory_mb

    def reconcile(self) -> int:
        """对账 NSCache 实际持有对象与内部记账，修正自动驱逐导致的漂移

        NSCache 在系统内存压力或成本上限触发时会自动驱逐对象，
        此时内部 _item_sizes/_item_count/_current_memory_mb 不会同步更新，
        会导致内存清理阈值判断失真。定期调用（如内存检查周期）可恢复准确性。

        Returns:
            本次修正（剔除）的条目数
        """
        with self._lock:
            if self._ns_cache is None or not self._item_sizes:
                return 0
            stale = [k for k in list(self._item_sizes) if self._ns_cache.objectForKey_(k) is None]
            for k in stale:
                self._current_memory_mb -= self._item_sizes.pop(k)
                self._item_count -= 1
                self._evictions += 1
            if stale:
                logger.debug(
                    "Cache RECONCILE [%s]: removed %d stale entries, memory %.1fMB",
                    self.name,
                    len(stale),
                    self._current_memory_mb,
                )
            return len(stale)

    def get_stats(self) -> dict:
        """获取缓存统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            # 先对账，确保内存/条目统计反映 NSCache 实际状态
            self.reconcile()

            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0

            return {
                "name": self.name,
                "size": self._item_count,
                "max_items": self.max_items,
                "memory_mb": round(self._current_memory_mb, 2),
                "max_memory_mb": self.max_memory_mb,
                "memory_usage_pct": round((self._current_memory_mb / self.max_memory_mb * 100), 2)
                if self.max_memory_mb > 0
                else 0.0,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_pct": round(hit_rate, 2),
                "evictions": self._evictions,
            }

    def __len__(self) -> int:
        """返回缓存项数量"""
        return self._item_count

    def __contains__(self, key: str) -> bool:
        """检查键是否存在"""
        return key in self._item_sizes

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
                _global_cache = SimpleImageCache(max_items=20, max_memory_mb=2000.0, name="global")

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

            # 加载图片（解码产生的 ObjC 中间对象由局部自动释放池回收，
            # 防止 PyObjC 桥接下解码内存随全局 pool 永久残留——见
            # docs/reports/memory-analysis-2026-08-18.md）
            from ..core.autorelease import objc_autorelease_pool

            with objc_autorelease_pool():
                image = loader.load(image_path, target_size=target_size)

            if image is not None:
                size_mb = self._estimate_image_memory(image)
                self.put(image_path, image, size_mb=size_mb)
                logger.debug("Loaded and cached %s using %s (estimated %.1fMB)", image_path, strategy, size_mb)

            return image

        except Exception as e:
            logger.exception("Failed to load image %s: %s", image_path, e)
            return None

    def get_file_size_mb(self, file_path: str) -> float:
        """获取文件大小（MB）

        委托给带缓存的全局文件信息加载器（5s TTL），
        避免导航热路径上的重复磁盘 I/O（尤其网络盘/外置盘）。

        Args:
            file_path: 文件路径

        Returns:
            文件大小（MB），失败返回0.0
        """
        try:
            from .file_info_batch_loader import get_file_info_loader

            return get_file_info_loader().get_file_size_mb(file_path, use_cache=True)
        except Exception as e:
            logger.debug("Failed to get file size via loader for %s: %s", file_path, e)
            try:
                import os

                if os.path.exists(file_path):
                    size_bytes = os.path.getsize(file_path)
                    return size_bytes / (1024 * 1024)
            except Exception:
                pass
            return 0.0

    @staticmethod
    def _estimate_image_memory(image) -> float:
        """估算图像解码后的实际像素内存大小（MB）
        委托到模块级函数
        """
        return estimate_image_memory_mb(image)


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
        # path -> index 映射：避免每次导航都做 O(n) list.index()
        # （大文件夹场景每次按键会带来主线程毫秒级字符串比较）
        self._path_to_index: dict[str, int] = {}

        logger.debug("Using BidirectionalCachePool (compatibility mode)")

    def set_current_image_sync(self, image_path: str, sync_key: str) -> None:
        """设置当前图片（兼容方法，O(1) 索引查找）"""
        try:
            if image_path in self._path_to_index:
                self._current_index = self._path_to_index[image_path]
            elif image_path in self._current_sequence:
                # 防御性回退：正常应命中缓存，这里避免重复 O(n)
                self._current_index = self._current_sequence.index(image_path)
                self._path_to_index[image_path] = self._current_index
        except Exception:
            pass

    def set_preload_window(self, preload_count: int = 5) -> None:
        """设置预加载窗口（兼容方法，简化实现）"""
        # 简化：不做实际预加载，只记录设置

    def set_sequence(self, images: list) -> None:
        """设置图片序列（兼容方法）"""
        self._current_sequence = images if images else []
        self._path_to_index = {}
        if images:
            self._path_to_index = {p: i for i, p in enumerate(images)}
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
    "estimate_image_memory_mb",
    "get_global_cache",
    "image_pixel_dimensions",
    "reset_global_cache",
]
