#!/usr/bin/env python3
"""
统一缓存管理器

整合所有缓存系统为单一、高效的缓存管理接口。
替代多个重复的缓存实现，简化架构并提升性能。

主要特性：
- 统一的缓存接口
- 自适应缓存策略
- 智能内存管理
- LRU淘汰机制
- 性能监控集成

Author: PlookingII Team
Version: 1.0.0
"""

import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from ..config.constants import APP_NAME
from ..imports import logging

logger = logging.getLogger(APP_NAME)


class UnifiedCacheEntry:
    """统一缓存项"""

    def __init__(self, key: str, value: Any, size: int = 0, priority: int = 1):
        self.key = key
        self.value = value
        self.size = size  # 内存大小估算(bytes)
        self.priority = priority  # 优先级(1-10, 10最高)
        self.access_time = time.time()
        self.access_count = 1
        self.created_time = time.time()

    def update_access(self):
        """更新访问信息"""
        self.access_time = time.time()
        self.access_count += 1

    def get_score(self) -> float:
        """计算缓存项得分(用于LRU+优先级排序)"""
        age = time.time() - self.access_time
        return (self.priority * 10 + self.access_count) / (age + 1)


class PixelAwareCacheEntry(UnifiedCacheEntry):
    """像素感知的缓存项

    扩展UnifiedCacheEntry以支持基于像素数的智能缓存策略。
    特别针对超大像素图片进行优化。
    """

    def __init__(self, key: str, value: Any, size: int = 0, priority: int = 1,
                 pixels_mp: float = 0.0, image_category: str = "normal"):
        super().__init__(key, value, size, priority)
        self.pixels_mp = pixels_mp  # 百万像素数
        self.image_category = image_category  # 图片类别: ultra_high_pixel, high_pixel, large_file, normal
        self.memory_priority = image_category in ("ultra_high_pixel", "high_pixel")

    def get_pixel_aware_score(self) -> float:
        """计算像素感知的缓存得分"""
        base_score = self.get_score()

        # 根据像素数和图片类别调整得分
        if self.image_category == "ultra_high_pixel":
            # 超大像素图片：降低得分，优先淘汰
            pixel_penalty = min(self.pixels_mp / 100.0, 10.0)  # 最高10倍惩罚
            return base_score / (1 + pixel_penalty)
        if self.image_category == "high_pixel":
            # 高像素图片：中等惩罚
            pixel_penalty = min(self.pixels_mp / 200.0, 5.0)  # 最高5倍惩罚
            return base_score / (1 + pixel_penalty)
        # 普通图片：无惩罚
        return base_score

    def should_force_evict(self, memory_pressure_ratio: float) -> bool:
        """判断是否应强制淘汰此项"""
        if self.image_category == "ultra_high_pixel":
            # 内存压力大于50%时，强制淘汰超大图片
            return memory_pressure_ratio > 0.5
        if self.image_category == "high_pixel":
            # 内存压力大于75%时，强制淘汰高像素图片
            return memory_pressure_ratio > 0.75
        return False


class UnifiedCacheManager:
    """统一缓存管理器

    整合热缓存、冷缓存和预加载缓存为单一管理器。
    提供智能的缓存策略和自动内存管理。
    """

    def __init__(self,
                 hot_cache_size: int = 100,
                 cold_cache_size: int = 500,
                 max_memory_mb: float = 2048,
                 cleanup_threshold: float = 0.8):
        """初始化统一缓存管理器

        Args:
            hot_cache_size: 热缓存最大项数
            cold_cache_size: 冷缓存最大项数
            max_memory_mb: 最大内存使用(MB)
            cleanup_threshold: 清理阈值(0.0-1.0)
        """
        self.hot_cache_size = hot_cache_size
        self.cold_cache_size = cold_cache_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cleanup_threshold = cleanup_threshold

        # 缓存存储
        self.hot_cache = OrderedDict()  # 热缓存(最近访问)
        self.cold_cache = OrderedDict()  # 冷缓存(历史数据)

        # 统计信息
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "memory_bytes": 0,
            "last_cleanup": time.time()
        }

        # 线程安全
        self.lock = threading.RLock()

        # 清理回调
        self.cleanup_callbacks = []

        # 像素感知配置
        self.pixel_based_optimization = True
        self.ultra_high_pixel_threshold_mp = 150.0
        self.high_pixel_threshold_mp = 50.0
        self.max_ultra_high_pixel_instances = 1
        self.ultra_high_pixel_memory_budget_mb = 2000

        logger.info(
            "UnifiedCacheManager initialized: hot=%s, cold=%s, memory=%sMB",
            hot_cache_size,
            cold_cache_size,
            max_memory_mb,
        )

    def get(self, key: str) -> Any | None:
        """获取缓存项"""
        with self.lock:
            # 首先检查热缓存
            if key in self.hot_cache:
                entry = self.hot_cache[key]
                entry.update_access()
                # 移到末尾(最近使用)
                self.hot_cache.move_to_end(key)
                self.stats["hits"] += 1
                return entry.value

            # 检查冷缓存
            if key in self.cold_cache:
                entry = self.cold_cache.pop(key)
                # 对低优先级项目（历史残留或并发情况下进入冷缓存）视为未命中
                if getattr(entry, "priority", 1) < 3:
                    self.stats["misses"] += 1
                    return None
                entry.update_access()
                # 提升到热缓存
                self._add_to_hot_cache(key, entry)
                self.stats["hits"] += 1
                return entry.value

            self.stats["misses"] += 1
            return None

    def put(self, key: str, value: Any, size: int = 0, priority: int = 1) -> bool:
        """添加缓存项"""
        with self.lock:
            entry = UnifiedCacheEntry(key, value, size, priority)

            # 检查是否需要清理
            self._check_and_cleanup()

            # 添加到热缓存
            success = self._add_to_hot_cache(key, entry)

            if success:
                self.stats["memory_bytes"] += size
                logger.debug(f"Cache put: {key}, size={size}, priority={priority}")

            return success

    def _add_to_hot_cache(self, key: str, entry: UnifiedCacheEntry) -> bool:
        """添加到热缓存"""
        # 如果键已存在，更新
        if key in self.hot_cache:
            old_entry = self.hot_cache[key]
            self.stats["memory_bytes"] -= old_entry.size

        self.hot_cache[key] = entry
        self.hot_cache.move_to_end(key)

        # 检查大小限制
        while len(self.hot_cache) > self.hot_cache_size:
            self._evict_from_hot_cache()

        return True

    def _evict_from_hot_cache(self):
        """从热缓存中驱逐项目"""
        if not self.hot_cache:
            return

        # 获取最老的项目
        key, entry = self.hot_cache.popitem(last=False)

        # 根据优先级决定是否移到冷缓存
        if entry.priority >= 3:  # 高优先级项目移到冷缓存
            self._add_to_cold_cache(key, entry)
        else:
            # 低优先级项目直接删除
            self.stats["memory_bytes"] -= entry.size
            self.stats["evictions"] += 1
            logger.debug(f"Cache eviction: {key}")

    def _add_to_cold_cache(self, key: str, entry: UnifiedCacheEntry):
        """添加到冷缓存"""
        if key in self.cold_cache:
            old_entry = self.cold_cache[key]
            self.stats["memory_bytes"] -= old_entry.size

        self.cold_cache[key] = entry
        self.cold_cache.move_to_end(key)

        # 检查大小限制
        while len(self.cold_cache) > self.cold_cache_size:
            key, old_entry = self.cold_cache.popitem(last=False)
            self.stats["memory_bytes"] -= old_entry.size
            self.stats["evictions"] += 1

    def _check_and_cleanup(self):
        """检查并清理缓存"""
        current_memory = self.stats["memory_bytes"]
        threshold_memory = self.max_memory_bytes * self.cleanup_threshold

        if current_memory > threshold_memory:
            self._cleanup_by_memory()

    def _cleanup_by_memory(self):
        """基于内存使用进行清理"""
        target_memory = self.max_memory_bytes * 0.6  # 清理到60%

        # 首先清理冷缓存中的低优先级项目
        items_to_remove = []
        for key, entry in self.cold_cache.items():
            if entry.priority < 3:
                items_to_remove.append(key)

        for key in items_to_remove:
            if self.stats["memory_bytes"] <= target_memory:
                break
            entry = self.cold_cache.pop(key, None)
            if entry:
                self.stats["memory_bytes"] -= entry.size
                self.stats["evictions"] += 1

        # 如果还不够，清理最老的项目
        while (self.stats["memory_bytes"] > target_memory and
               (self.cold_cache or self.hot_cache)):
            if self.cold_cache:
                key, entry = self.cold_cache.popitem(last=False)
            else:
                key, entry = self.hot_cache.popitem(last=False)

            self.stats["memory_bytes"] -= entry.size
            self.stats["evictions"] += 1

        self.stats["last_cleanup"] = time.time()
        logger.info(f"Cache cleanup completed, memory: {self.stats['memory_bytes']/1024/1024:.1f}MB")

        # 调用清理回调
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.warning(f"Cleanup callback failed: {e}")

    def remove(self, key: str) -> bool:
        """移除缓存项"""
        with self.lock:
            removed = False

            if key in self.hot_cache:
                entry = self.hot_cache.pop(key)
                self.stats["memory_bytes"] -= entry.size
                removed = True

            if key in self.cold_cache:
                entry = self.cold_cache.pop(key)
                self.stats["memory_bytes"] -= entry.size
                removed = True

            return removed

    def clear(self):
        """清空所有缓存"""
        with self.lock:
            self.hot_cache.clear()
            self.cold_cache.clear()
            self.stats["memory_bytes"] = 0
            self.stats["evictions"] = 0
            logger.info("All caches cleared")

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total_items = len(self.hot_cache) + len(self.cold_cache)
            hit_rate = 0.0
            if self.stats["hits"] + self.stats["misses"] > 0:
                hit_rate = self.stats["hits"] / (self.stats["hits"] + self.stats["misses"])

            return {
                "total_items": total_items,
                "hot_cache_items": len(self.hot_cache),
                "cold_cache_items": len(self.cold_cache),
                "memory_mb": self.stats["memory_bytes"] / 1024 / 1024,
                "hit_rate": hit_rate,
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "evictions": self.stats["evictions"],
                "last_cleanup": self.stats["last_cleanup"]
            }

    def add_cleanup_callback(self, callback: Callable[[], None]):
        """添加清理回调函数"""
        self.cleanup_callbacks.append(callback)

    def preload(self, keys_and_loaders: list) -> int:
        """批量预加载数据

        Args:
            keys_and_loaders: [(key, loader_func, priority), ...]

        Returns:
            成功预加载的数量
        """
        loaded_count = 0

        for item in keys_and_loaders:
            if len(item) >= 2:
                key = item[0]
                loader = item[1]
                priority = item[2] if len(item) > 2 else 1

                # 检查是否已缓存
                if self.get(key) is not None:
                    continue

                try:
                    value = loader()
                    if value is not None:
                        # 估算大小(简单实现)
                        size = self._estimate_size(value)
                        if self.put(key, value, size, priority):
                            loaded_count += 1
                except Exception as e:
                    logger.warning(f"Preload failed for {key}: {e}")

        return loaded_count

    def _estimate_size(self, value: Any) -> int:
        """估算对象大小"""
        try:
            # 这是一个简单的大小估算
            if hasattr(value, "__sizeof__"):
                return value.__sizeof__()
            return 1024  # 默认1KB
        except Exception:
            return 1024

    def put_image_with_pixels(self, key: str, image: Any, pixels_mp: float = 0.0,
                             estimated_size_mb: float = 0.0, priority: int = 1) -> bool:
        """存储带像素数信息的图像

        Args:
            key: 缓存键
            image: 图像对象
            pixels_mp: 百万像素数
            estimated_size_mb: 估算的内存大小(MB)
            priority: 优先级

        Returns:
            bool: 是否成功存储
        """
        if not self.pixel_based_optimization:
            # 未启用像素感知，使用传统方法
            size_bytes = int(estimated_size_mb * 1024 * 1024) if estimated_size_mb > 0 else self._estimate_size(image)
            return self.put(key, image, size_bytes, priority)

        # 确定图片类别
        if pixels_mp >= self.ultra_high_pixel_threshold_mp:
            image_category = "ultra_high_pixel"
        elif pixels_mp >= self.high_pixel_threshold_mp:
            image_category = "high_pixel"
        else:
            image_category = "normal"

        # 检查超大像素图片的缓存限制
        if image_category == "ultra_high_pixel":
            current_ultra_count = self._count_ultra_high_pixel_images()
            if current_ultra_count >= self.max_ultra_high_pixel_instances:
                # 替换现有的超大像素图片
                self._evict_ultra_high_pixel_images()

        size_bytes = int(estimated_size_mb * 1024 * 1024) if estimated_size_mb > 0 else self._estimate_size(image)

        with self.lock:
            # 创建像素感知的缓存项
            entry = PixelAwareCacheEntry(
                key=key,
                value=image,
                size=size_bytes,
                priority=priority,
                pixels_mp=pixels_mp,
                image_category=image_category
            )

            # 检查内存预算
            if not self._check_memory_budget(entry):
                return False

            # 存储到热缓存
            self.hot_cache[key] = entry
            self.stats["memory_bytes"] += size_bytes

            # 超出大小限制时清理
            if len(self.hot_cache) > self.hot_cache_size:
                self._pixel_aware_cleanup()

            return True

    def _count_ultra_high_pixel_images(self) -> int:
        """统计当前缓存中超大像素图片的数量"""
        count = 0
        for entry in self.hot_cache.values():
            if isinstance(entry, PixelAwareCacheEntry) and entry.image_category == "ultra_high_pixel":
                count += 1
        for entry in self.cold_cache.values():
            if isinstance(entry, PixelAwareCacheEntry) and entry.image_category == "ultra_high_pixel":
                count += 1
        return count

    def _evict_ultra_high_pixel_images(self):
        """淘汰所有超大像素图片"""
        with self.lock:
            # 从热缓存中移除
            keys_to_remove = []
            for key, entry in self.hot_cache.items():
                if isinstance(entry, PixelAwareCacheEntry) and entry.image_category == "ultra_high_pixel":
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                entry = self.hot_cache.pop(key)
                self.stats["memory_bytes"] -= entry.size
                self.stats["evictions"] += 1

            # 从冷缓存中移除
            keys_to_remove = []
            for key, entry in self.cold_cache.items():
                if isinstance(entry, PixelAwareCacheEntry) and entry.image_category == "ultra_high_pixel":
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                entry = self.cold_cache.pop(key)
                self.stats["memory_bytes"] -= entry.size
                self.stats["evictions"] += 1

    def _check_memory_budget(self, entry: PixelAwareCacheEntry) -> bool:
        """检查内存预算是否允许添加此项"""
        if entry.image_category == "ultra_high_pixel":
            # 超大像素图片有专门的内存预算
            ultra_budget_bytes = self.ultra_high_pixel_memory_budget_mb * 1024 * 1024
            return entry.size <= ultra_budget_bytes
        # 普通图片检查总内存预算
        return (self.stats["memory_bytes"] + entry.size) <= self.max_memory_bytes

    def _pixel_aware_cleanup(self):
        """基于像素数的智能清理"""
        if not self.pixel_based_optimization:
            # 未启用像素感知，使用传统清理
            self._cleanup_old_entries()
            return

        with self.lock:
            # 计算内存压力比率
            memory_pressure_ratio = self.stats["memory_bytes"] / self.max_memory_bytes

            # 收集所有缓存项并计算得分
            all_entries = []

            for entry in self.hot_cache.values():
                if isinstance(entry, PixelAwareCacheEntry):
                    # 检查是否应强制淘汰
                    if entry.should_force_evict(memory_pressure_ratio):
                        all_entries.append((entry, -1000))  # 强制淘汰得分
                    else:
                        all_entries.append((entry, entry.get_pixel_aware_score()))
                else:
                    all_entries.append((entry, entry.get_score()))

            # 按得分排序，得分越低越先淘汰
            all_entries.sort(key=lambda x: x[1])

            # 淘汰最低得分的项，直到满足内存要求
            target_memory = self.max_memory_bytes * self.cleanup_threshold

            for entry, score in all_entries:
                if self.stats["memory_bytes"] <= target_memory:
                    break

                # 从缓存中移除
                if entry.key in self.hot_cache:
                    del self.hot_cache[entry.key]
                elif entry.key in self.cold_cache:
                    del self.cold_cache[entry.key]

                self.stats["memory_bytes"] -= entry.size
                self.stats["evictions"] += 1


# 全局统一缓存管理器实例
_unified_cache_manager = None
_cache_lock = threading.Lock()


def get_unified_cache_manager(**kwargs) -> UnifiedCacheManager:
    """获取全局统一缓存管理器实例"""
    global _unified_cache_manager

    with _cache_lock:
        if _unified_cache_manager is None:
            _unified_cache_manager = UnifiedCacheManager(**kwargs)
        return _unified_cache_manager


def reset_unified_cache_manager():
    """重置全局缓存管理器(主要用于测试)"""
    global _unified_cache_manager

    with _cache_lock:
        if _unified_cache_manager:
            _unified_cache_manager.clear()
        _unified_cache_manager = None


# 兼容性接口 - 提供与旧缓存系统兼容的接口


class CacheCompatibilityAdapter:
    """缓存兼容性适配器

    为旧的缓存接口提供兼容性支持，便于渐进式迁移。
    """

    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager

    def get_image(self, key: str) -> Any | None:
        """获取图像(兼容旧接口)"""
        return self.cache_manager.get(key)

    def cache_image(self, key: str, image: Any, priority: int = 1) -> bool:
        """缓存图像(兼容旧接口)"""
        size = self.cache_manager._estimate_size(image)
        return self.cache_manager.put(key, image, size, priority)

    def cache_image_with_pixels(self, key: str, image: Any, pixels_mp: float = 0.0,
                               estimated_size_mb: float = 0.0, priority: int = 1) -> bool:
        """缓存带像素数信息的图像(新接口)"""
        return self.cache_manager.put_image_with_pixels(key, image, pixels_mp, estimated_size_mb, priority)

    def clear_cache(self):
        """清空缓存(兼容旧接口)"""
        self.cache_manager.clear()

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计(兼容旧接口)"""
        return self.cache_manager.get_stats()


# 导出主要接口
__all__ = [
    "CacheCompatibilityAdapter",
    "PixelAwareCacheEntry",
    "UnifiedCacheEntry",
    "UnifiedCacheManager",
    "get_unified_cache_manager",
    "reset_unified_cache_manager"
]
