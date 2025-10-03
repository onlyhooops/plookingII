"""
缓存监控和统计

提供缓存性能监控、统计信息收集和报告生成功能。

Author: PlookingII Team
Version: 2.0.0
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheStats:
    """缓存统计信息"""

    # 命中统计
    hot_hits: int = 0
    cold_hits: int = 0
    unified_hits: int = 0
    misses: int = 0

    # 操作统计
    puts: int = 0
    removes: int = 0
    evictions: int = 0
    clears: int = 0

    # 大小统计
    total_put_size_mb: float = 0.0

    # 时间统计
    start_time: float = field(default_factory=time.time)

    def record_hit(self, cache_type: str = "unified") -> None:
        """记录缓存命中

        Args:
            cache_type: 缓存类型 ('hot', 'cold', 'unified')
        """
        if cache_type == "hot":
            self.hot_hits += 1
        elif cache_type == "cold":
            self.cold_hits += 1
        else:
            self.unified_hits += 1

    def record_miss(self) -> None:
        """记录缓存未命中"""
        self.misses += 1

    def record_put(self, size: float) -> None:
        """记录缓存存储

        Args:
            size: 数据大小（MB）
        """
        self.puts += 1
        self.total_put_size_mb += size

    def record_remove(self) -> None:
        """记录缓存移除"""
        self.removes += 1

    def record_eviction(self) -> None:
        """记录缓存淘汰"""
        self.evictions += 1

    def record_clear(self) -> None:
        """记录缓存清空"""
        self.clears += 1

    @property
    def total_hits(self) -> int:
        """总命中数"""
        return self.hot_hits + self.cold_hits + self.unified_hits

    @property
    def total_accesses(self) -> int:
        """总访问数"""
        return self.total_hits + self.misses

    @property
    def hit_rate(self) -> float:
        """命中率（0.0-1.0）"""
        if self.total_accesses == 0:
            return 0.0
        return self.total_hits / self.total_accesses

    @property
    def miss_rate(self) -> float:
        """未命中率（0.0-1.0）"""
        return 1.0 - self.hit_rate

    @property
    def uptime_seconds(self) -> float:
        """运行时间（秒）"""
        return time.time() - self.start_time

    def to_dict(self) -> dict[str, Any]:
        """转换为字典

        Returns:
            Dict: 统计信息字典
        """
        return {
            "hits": {
                "hot": self.hot_hits,
                "cold": self.cold_hits,
                "unified": self.unified_hits,
                "total": self.total_hits,
            },
            "misses": self.misses,
            "total_accesses": self.total_accesses,
            "hit_rate": round(self.hit_rate * 100, 2),
            "miss_rate": round(self.miss_rate * 100, 2),
            "operations": {
                "puts": self.puts,
                "removes": self.removes,
                "evictions": self.evictions,
                "clears": self.clears,
            },
            "total_put_size_mb": round(self.total_put_size_mb, 2),
            "uptime_seconds": round(self.uptime_seconds, 2),
        }

    def __repr__(self) -> str:
        return (
            f"CacheStats(hits={self.total_hits}, misses={self.misses}, "
            f"hit_rate={self.hit_rate:.2%}, uptime={self.uptime_seconds:.1f}s)"
        )


class CacheMonitor:
    """缓存监控器

    提供实时监控和历史数据记录功能。
    """

    def __init__(self, history_size: int = 1000):
        """初始化监控器

        Args:
            history_size: 历史记录容量
        """
        self._history_size = history_size
        self._history: deque = deque(maxlen=history_size)
        self._lock = threading.Lock()

        self._stats = CacheStats()

    def record_event(self, event_type: str, **data) -> None:
        """记录事件

        Args:
            event_type: 事件类型 ('hit', 'miss', 'put', 'eviction')
            **data: 事件数据
        """
        with self._lock:
            event = {
                "type": event_type,
                "timestamp": time.time(),
                **data
            }
            self._history.append(event)

    def get_recent_events(self, count: int = 100) -> list[dict[str, Any]]:
        """获取最近的事件

        Args:
            count: 事件数量

        Returns:
            List[Dict]: 事件列表
        """
        with self._lock:
            return list(self._history)[-count:]

    def get_stats_summary(self) -> dict[str, Any]:
        """获取统计摘要

        Returns:
            Dict: 统计摘要
        """
        with self._lock:
            # 从历史记录计算统计
            hits = sum(1 for e in self._history if e["type"] == "hit")
            misses = sum(1 for e in self._history if e["type"] == "miss")
            puts = sum(1 for e in self._history if e["type"] == "put")
            evictions = sum(1 for e in self._history if e["type"] == "eviction")

            total_accesses = hits + misses
            hit_rate = (hits / total_accesses * 100) if total_accesses > 0 else 0

            return {
                "recent_events": len(self._history),
                "recent_hits": hits,
                "recent_misses": misses,
                "recent_puts": puts,
                "recent_evictions": evictions,
                "recent_hit_rate": round(hit_rate, 2),
            }

    def clear_history(self) -> None:
        """清空历史记录"""
        with self._lock:
            self._history.clear()
