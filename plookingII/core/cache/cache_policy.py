"""
缓存淘汰策略

支持多种缓存淘汰算法：
- LRU (Least Recently Used): 最近最少使用
- LFU (Least Frequently Used): 最不经常使用
- ARC (Adaptive Replacement Cache): 自适应替换缓存

Author: PlookingII Team
Version: 2.0.0
"""

import time
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict


class CachePolicy(ABC):
    """缓存淘汰策略基类"""

    @abstractmethod
    def on_access(self, key: str) -> None:
        """缓存项被访问时调用

        Args:
            key: 缓存键
        """

    @abstractmethod
    def on_put(self, key: str, size: float) -> None:
        """缓存项被存储时调用

        Args:
            key: 缓存键
            size: 数据大小（MB）
        """

    @abstractmethod
    def on_remove(self, key: str) -> None:
        """缓存项被移除时调用

        Args:
            key: 缓存键
        """

    @abstractmethod
    def select_eviction_candidate(self, keys: list[str]) -> str | None:
        """选择一个要淘汰的缓存项

        Args:
            keys: 候选键列表

        Returns:
            要淘汰的键，如果没有则返回 None
        """


class LRUPolicy(CachePolicy):
    """LRU (Least Recently Used) 淘汰策略

    淘汰最近最少使用的项。使用访问时间戳记录。
    """

    def __init__(self):
        self._access_order: OrderedDict[str, float] = OrderedDict()

    def on_access(self, key: str) -> None:
        """记录访问时间并更新顺序"""
        self._access_order[key] = time.time()
        self._access_order.move_to_end(key)

    def on_put(self, key: str, size: float) -> None:
        """新项存储时记录"""
        self._access_order[key] = time.time()
        self._access_order.move_to_end(key)

    def on_remove(self, key: str) -> None:
        """移除时清理记录"""
        self._access_order.pop(key, None)

    def select_eviction_candidate(self, keys: list[str]) -> str | None:
        """选择最久未使用的项"""
        if not self._access_order:
            return keys[0] if keys else None

        # 返回最旧的项（OrderedDict 的第一个）
        return next(iter(self._access_order))


class LFUPolicy(CachePolicy):
    """LFU (Least Frequently Used) 淘汰策略

    淘汰访问频率最低的项。
    """

    def __init__(self):
        self._access_count: dict[str, int] = defaultdict(int)

    def on_access(self, key: str) -> None:
        """增加访问计数"""
        self._access_count[key] += 1

    def on_put(self, key: str, size: float) -> None:
        """新项存储时初始化计数"""
        self._access_count[key] = 1

    def on_remove(self, key: str) -> None:
        """移除时清理计数"""
        self._access_count.pop(key, None)

    def select_eviction_candidate(self, keys: list[str]) -> str | None:
        """选择访问频率最低的项"""
        if not keys:
            return None

        # 找到访问次数最少的键
        min_key = min(keys, key=lambda k: self._access_count.get(k, 0))
        return min_key


class ARCPolicy(CachePolicy):
    """ARC (Adaptive Replacement Cache) 淘汰策略

    自适应策略，结合 LRU 和 LFU 的优点。
    维护两个列表：
    - T1: 最近访问一次的项（LRU）
    - T2: 最近访问多次的项（LFU）

    动态调整两个列表的大小以适应访问模式。
    """

    def __init__(self, capacity: int = 1000):
        self._capacity = capacity
        self._p = 0  # T1 的目标大小

        # T1: 最近访问一次
        self._t1: OrderedDict[str, float] = OrderedDict()

        # T2: 最近访问多次
        self._t2: OrderedDict[str, float] = OrderedDict()

        # B1: T1 的历史（已淘汰）
        self._b1: OrderedDict[str, float] = OrderedDict()

        # B2: T2 的历史（已淘汰）
        self._b2: OrderedDict[str, float] = OrderedDict()

        # 访问计数
        self._access_count: dict[str, int] = defaultdict(int)

    def on_access(self, key: str) -> None:
        """处理访问事件"""
        self._access_count[key] += 1
        current_time = time.time()

        # 如果在 T1 中，移到 T2
        if key in self._t1:
            self._t1.pop(key)
            self._t2[key] = current_time
            self._t2.move_to_end(key)

        # 如果在 T2 中，更新位置
        elif key in self._t2:
            self._t2[key] = current_time
            self._t2.move_to_end(key)

        # 如果在 B1 中（历史命中）
        elif key in self._b1:
            # 增加 p（T1 目标大小）
            self._p = min(self._capacity, self._p + max(1, len(self._b2) // len(self._b1)))
            self._b1.pop(key)
            self._t2[key] = current_time

        # 如果在 B2 中（历史命中）
        elif key in self._b2:
            # 减少 p（T1 目标大小）
            self._p = max(0, self._p - max(1, len(self._b1) // len(self._b2)))
            self._b2.pop(key)
            self._t2[key] = current_time

        # 新项（首次访问）
        else:
            self._t1[key] = current_time

    def on_put(self, key: str, size: float) -> None:
        """新项存储"""
        self._access_count[key] = 1
        self._t1[key] = time.time()

    def on_remove(self, key: str) -> None:
        """移除项"""
        self._t1.pop(key, None)
        self._t2.pop(key, None)
        self._b1.pop(key, None)
        self._b2.pop(key, None)
        self._access_count.pop(key, None)

    def select_eviction_candidate(self, keys: list[str]) -> str | None:
        """选择淘汰候选"""
        # 优先从 T1 淘汰（如果 T1 大小超过目标）
        if len(self._t1) > self._p and self._t1:
            key = next(iter(self._t1))
            # 移到 B1（历史记录）
            self._b1[key] = self._t1.pop(key)
            return key

        # 否则从 T2 淘汰
        if self._t2:
            key = next(iter(self._t2))
            # 移到 B2（历史记录）
            self._b2[key] = self._t2.pop(key)
            return key

        # 如果都为空，从 T1 淘汰
        if self._t1:
            key = next(iter(self._t1))
            self._t1.pop(key)
            return key

        return None


# 策略工厂
def create_policy(policy_name: str = "lru") -> CachePolicy:
    """创建缓存策略

    Args:
        policy_name: 策略名称 ('lru', 'lfu', 'arc')

    Returns:
        CachePolicy: 缓存策略实例
    """
    policy_name = policy_name.lower()

    if policy_name == "lru":
        return LRUPolicy()
    if policy_name == "lfu":
        return LFUPolicy()
    if policy_name == "arc":
        return ARCPolicy()
    # 默认使用 LRU
    return LRUPolicy()
