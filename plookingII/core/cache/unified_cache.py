"""
统一缓存核心实现（重构版）

简化的2层缓存架构：
- Active Cache: 当前活跃图片（正在查看或刚看过的）
- Nearby Cache: 相邻图片预加载（提前加载的图片）

特性：
- LRU淘汰策略（简单高效）
- 内存大小限制管理
- 线程安全的并发访问
- 统计信息收集
- 智能预加载支持

Author: PlookingII Team
Version: 3.0.0 (Refactored)
"""

import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from ...config.constants import APP_NAME
from .cache_monitor import CacheStats
from .cache_policy import CachePolicy, LRUPolicy
from .config import CacheConfig

logger = logging.getLogger(APP_NAME)


@dataclass
class CacheEntry:
    """缓存条目数据类"""
    value: Any
    size: float  # MB
    priority: int = 1
    access_count: int = 0
    last_access_time: float = 0.0
    creation_time: float = 0.0

    def __post_init__(self):
        if self.creation_time == 0.0:
            self.creation_time = time.time()
        if self.last_access_time == 0.0:
            self.last_access_time = self.creation_time


class UnifiedCache:
    """统一缓存实现（重构版 - 2层架构）

    简化的2层缓存系统：
    - Active Cache: 存储当前正在查看或刚查看过的图片
    - Nearby Cache: 存储预加载的相邻图片

    特性：
    - 简单的LRU淘汰策略
    - 内存限制和智能淘汰
    - 线程安全访问
    - 详细的统计信息

    示例：
        >>> config = CacheConfig.default()
        >>> cache = UnifiedCache(config)
        >>> cache.put('key1', value1, size=10.5)
        >>> value = cache.get('key1')
        >>> stats = cache.get_stats()
    """

    def __init__(
        self,
        config: CacheConfig | None = None,
        policy: CachePolicy | None = None,
    ):
        """初始化统一缓存

        Args:
            config: 缓存配置，如果为None则使用默认配置
            policy: 缓存淘汰策略（默认LRU，推荐使用默认）
        """
        # 使用配置
        self._config = config or CacheConfig.default()

        # 2层缓存存储（简化架构）
        self._active_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._nearby_cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # 淘汰策略（仅使用LRU，已被证明足够高效）
        self._policy = policy or LRUPolicy()

        # 线程安全
        self._lock = threading.RLock() if self._config.thread_safe else None

        # 统计信息
        self._stats = CacheStats() if self._config.enable_stats else None

        # 当前内存使用
        self._current_memory_mb = 0.0

        # 清理计时器
        self._last_cleanup = time.time()

        logger.info(
            f"UnifiedCache initialized: {self._config}"
        )

    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存项

        Args:
            key: 缓存键
            default: 未找到时的默认值

        Returns:
            缓存的值，如果不存在则返回 default
        """
        def _do_get():
            # Active Cache查找
            if key in self._active_cache:
                entry = self._active_cache[key]
                entry.access_count += 1
                entry.last_access_time = time.time()

                # 移到末尾（LRU）
                self._active_cache.move_to_end(key)

                if self._stats:
                    self._stats.record_hit("active")
                self._policy.on_access(key)

                if self._config.debug_logging:
                    logger.debug(f"Cache HIT (active): {key}")
                return entry.value

            # Nearby Cache查找
            if key in self._nearby_cache:
                entry = self._nearby_cache[key]
                entry.access_count += 1
                entry.last_access_time = time.time()

                if self._stats:
                    self._stats.record_hit("nearby")
                self._policy.on_access(key)

                # 晋升到 Active Cache（因为用户现在正在查看它）
                self._promote_to_active(key)

                if self._config.debug_logging:
                    logger.debug(f"Cache HIT (nearby, promoted): {key}")
                return entry.value

            # 缓存未命中
            if self._stats:
                self._stats.record_miss()
            if self._config.debug_logging:
                logger.debug(f"Cache MISS: {key}")
            return default

        # 线程安全
        if self._lock:
            with self._lock:
                return _do_get()
        else:
            return _do_get()

    def put(self, key: str, value: Any, size: float = 0, priority: int = 1,
            is_nearby: bool = False) -> bool:
        """存储缓存项

        Args:
            key: 缓存键
            value: 缓存值
            size: 数据大小（MB）
            priority: 优先级（1-10，越高越重要）
            is_nearby: 是否是预加载的相邻图片（True则存到nearby cache）

        Returns:
            bool: 是否成功存储
        """
        def _do_put():
            # 检查文件大小限制
            if size > self._config.max_file_size_mb:
                logger.warning(f"File too large to cache: {key}, size={size}MB")
                return False

            # 确保有足够空间
            if not self._ensure_space(size):
                logger.warning(f"Failed to ensure space for key: {key}, size={size}MB")
                return False

            # 创建缓存条目
            entry = CacheEntry(
                value=value,
                size=size,
                priority=priority,
                access_count=1,
                last_access_time=time.time(),
            )

            # 根据is_nearby决定存储位置
            if is_nearby:
                # 存储到 Nearby Cache
                self._nearby_cache[key] = entry
                self._nearby_cache.move_to_end(key)

                # 检查 Nearby Cache 大小
                if len(self._nearby_cache) > self._config.nearby_cache_size:
                    self._evict_from_nearby()
            else:
                # 存储到 Active Cache
                self._active_cache[key] = entry
                self._active_cache.move_to_end(key)

                # 检查 Active Cache 大小
                if len(self._active_cache) > self._config.active_cache_size:
                    self._demote_to_nearby()

            # 更新内存使用
            self._current_memory_mb += size

            # 通知策略
            self._policy.on_put(key, size)

            # 更新统计
            if self._stats:
                self._stats.record_put(size)

            if self._config.debug_logging:
                cache_type = "nearby" if is_nearby else "active"
                logger.debug(f"Cache PUT ({cache_type}): {key}, size={size}MB, total={self._current_memory_mb:.1f}MB")
            return True

        # 线程安全
        if self._lock:
            with self._lock:
                return _do_put()
        else:
            return _do_put()

    def remove(self, key: str) -> bool:
        """移除缓存项

        Args:
            key: 缓存键

        Returns:
            bool: 是否成功移除
        """
        def _do_remove():
            removed = False
            freed_size = 0.0

            # 从 Active Cache 移除
            if key in self._active_cache:
                entry = self._active_cache.pop(key)
                freed_size = entry.size
                removed = True

            # 从 Nearby Cache 移除
            if key in self._nearby_cache:
                entry = self._nearby_cache.pop(key)
                freed_size = entry.size
                removed = True

            if removed:
                self._current_memory_mb -= freed_size
                if self._stats:
                    self._stats.record_eviction()
                self._policy.on_remove(key)
                if self._config.debug_logging:
                    logger.debug(f"Cache REMOVE: {key}, freed={freed_size}MB")

            return removed

        # 线程安全
        if self._lock:
            with self._lock:
                return _do_remove()
        else:
            return _do_remove()

    def clear(self) -> None:
        """清空所有缓存"""
        def _do_clear():
            self._active_cache.clear()
            self._nearby_cache.clear()
            self._current_memory_mb = 0.0
            if self._stats:
                self._stats.record_clear()
            logger.info("Cache cleared")

        # 线程安全
        if self._lock:
            with self._lock:
                _do_clear()
        else:
            _do_clear()

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计信息

        Returns:
            Dict: 包含命中率、内存使用等统计信息
        """
        def _do_get_stats():
            stats = {}
            if self._stats:
                stats.update(self._stats.to_dict())

            stats.update({
                "active_cache_size": len(self._active_cache),
                "nearby_cache_size": len(self._nearby_cache),
                "total_items": self._get_total_items(),
                "current_memory_mb": round(self._current_memory_mb, 2),
                "max_memory_mb": self._config.max_memory_mb,
                "memory_usage_pct": round(
                    (self._current_memory_mb / self._config.max_memory_mb * 100), 2
                ) if self._config.max_memory_mb > 0 else 0,
            })
            return stats

        # 线程安全
        if self._lock:
            with self._lock:
                return _do_get_stats()
        else:
            return _do_get_stats()

    def _ensure_space(self, required_size: float) -> bool:
        """确保有足够的空间

        Args:
            required_size: 需要的空间（MB）

        Returns:
            bool: 是否成功确保空间
        """
        # 检查是否超过内存限制
        max_iterations = self._get_total_items() + 10  # 防止无限循环
        iterations = 0

        while self._current_memory_mb + required_size > self._config.max_memory_mb:
            iterations += 1
            if iterations > max_iterations:
                logger.error("Too many eviction iterations, stopping")
                return False

            # 尝试淘汰缓存项
            if not self._evict_one():
                # 无法淘汰更多项
                return False

        return True

    def _evict_one(self) -> bool:
        """淘汰一个缓存项（LRU策略）

        Returns:
            bool: 是否成功淘汰
        """
        # 优先从 Nearby Cache 淘汰（LRU）
        if self._nearby_cache:
            key = next(iter(self._nearby_cache))
            self.remove(key)
            if self._config.debug_logging:
                logger.debug(f"Evicted from nearby: {key}")
            return True

        # 从 Active Cache 淘汰（LRU）
        if self._active_cache:
            key = next(iter(self._active_cache))
            self.remove(key)
            if self._config.debug_logging:
                logger.debug(f"Evicted from active: {key}")
            return True

        return False

    def _evict_from_nearby(self) -> None:
        """从 Nearby Cache 淘汰最旧的项"""
        if not self._nearby_cache:
            return

        # 获取最旧的项（LRU）
        key = next(iter(self._nearby_cache))
        self.remove(key)
        if self._config.debug_logging:
            logger.debug(f"Evicted from nearby (size limit): {key}")

    def _promote_to_active(self, key: str) -> None:
        """将 Nearby Cache 项晋升到 Active Cache

        Args:
            key: 缓存键
        """
        if key not in self._nearby_cache:
            return

        entry = self._nearby_cache.pop(key)
        self._active_cache[key] = entry
        self._active_cache.move_to_end(key)

        # 检查 Active Cache 大小
        if len(self._active_cache) > self._config.active_cache_size:
            self._demote_to_nearby()

        if self._config.debug_logging:
            logger.debug(f"Promoted to active: {key}")

    def _demote_to_nearby(self) -> None:
        """将最旧的 Active Cache 项降级到 Nearby Cache"""
        if not self._active_cache:
            return

        # 获取最旧的项（LRU）
        key, entry = self._active_cache.popitem(last=False)
        self._nearby_cache[key] = entry
        self._nearby_cache.move_to_end(key)

        # 检查 Nearby Cache 大小
        if len(self._nearby_cache) > self._config.nearby_cache_size:
            # 淘汰最旧的 Nearby Cache 项
            self._evict_from_nearby()

        if self._config.debug_logging:
            logger.debug(f"Demoted to nearby: {key}")

    def _get_total_items(self) -> int:
        """获取总缓存项数"""
        return len(self._active_cache) + len(self._nearby_cache)

    def __repr__(self) -> str:
        return (
            f"UnifiedCache(active={len(self._active_cache)}, "
            f"nearby={len(self._nearby_cache)}, "
            f"memory={self._current_memory_mb:.1f}MB/{self._config.max_memory_mb}MB)"
        )


# 全局单例
_unified_cache: UnifiedCache | None = None
_cache_lock = threading.Lock()


def get_unified_cache(config: CacheConfig | None = None) -> UnifiedCache:
    """获取全局统一缓存实例（单例模式）

    Args:
        config: 缓存配置，仅在首次创建时使用

    Returns:
        UnifiedCache: 全局缓存实例

    Example:
        >>> config = CacheConfig.performance()
        >>> cache = get_unified_cache(config)
        >>> # 后续调用会返回同一实例
        >>> cache2 = get_unified_cache()  # 返回同一个实例
    """
    global _unified_cache

    if _unified_cache is None:
        with _cache_lock:
            if _unified_cache is None:
                _unified_cache = UnifiedCache(config=config)
                logger.info("Global UnifiedCache instance created")

    return _unified_cache


def reset_unified_cache() -> None:
    """重置全局缓存实例（主要用于测试）"""
    global _unified_cache

    with _cache_lock:
        if _unified_cache is not None:
            _unified_cache.clear()
            _unified_cache = None
            logger.info("Global UnifiedCache instance reset")
