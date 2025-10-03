"""
图像内存池管理模块

提供高效的内存池管理，减少内存分配/释放开销，提高内存使用效率。
支持按大小分组的对象池和智能内存回收。

主要功能：
    - 按大小分组的内存池
    - 智能内存回收机制
    - 内存使用量监控
    - 线程安全的内存管理

Author: PlookingII Team
Version: 1.0.0
"""

import logging
import threading
from collections import defaultdict

from ..config.constants import APP_NAME

# 使用标准库 logging/threading，避免重复导入

logger = logging.getLogger(APP_NAME)


class ImageMemoryPool:
    """图像内存池管理器"""

    def __init__(self, max_memory_mb: float = 1000):
        """初始化内存池

        Args:
            max_memory_mb: 最大内存使用量（MB）
        """
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.allocated_bytes = 0
        self.pools = defaultdict(list)  # 按大小分组的对象池
        self.lock = threading.RLock()

        # 统计信息
        self.total_allocations = 0
        self.total_deallocations = 0
        self.cache_hits = 0
        self.cache_misses = 0

        # 预定义的大小类别（2的幂次）
        self.size_categories = (
            [1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576]
        )

    def get_buffer(self, size_bytes: int) -> bytearray | None:
        """从池中获取指定大小的缓冲区

        Args:
            size_bytes: 需要的缓冲区大小（字节）

        Returns:
            bytearray: 缓冲区对象，如果无法分配则返回None
        """
        with self.lock:
            try:
                # 查找合适大小的池
                pool_size = self._find_best_pool_size(size_bytes)

                if self.pools.get(pool_size):
                    # 从池中获取缓冲区
                    buffer = self.pools[pool_size].pop()
                    self.allocated_bytes += size_bytes
                    self.total_allocations += 1
                    self.cache_hits += 1

                    # 截取到需要的大小
                    return buffer[:size_bytes]
                # 池中没有可用缓冲区，创建新的
                if self.allocated_bytes + pool_size <= self.max_memory_bytes:
                    buffer = bytearray(pool_size)
                    self.allocated_bytes += pool_size
                    self.total_allocations += 1
                    self.cache_misses += 1
                    return buffer[:size_bytes]
                # 内存不足，尝试清理一些池
                if self._cleanup_pools():
                    return self.get_buffer(size_bytes)  # 递归重试
                return None

            except Exception as e:
                logger.error(f"Failed to get buffer: {e}")
                return None

    def return_buffer(self, buffer: bytearray, original_size: int):
        """将缓冲区返回到池中

        Args:
            buffer: 要返回的缓冲区
            original_size: 原始分配的大小
        """
        with self.lock:
            try:
                if not buffer:
                    return

                # 找到合适的池大小
                pool_size = self._find_best_pool_size(original_size)

                # 确保缓冲区大小正确
                if len(buffer) < pool_size:
                    buffer.extend(b"\x00" * (pool_size - len(buffer)))
                elif len(buffer) > pool_size:
                    buffer = buffer[:pool_size]

                # 检查内存限制
                if self.allocated_bytes + pool_size <= self.max_memory_bytes:
                    self.pools[pool_size].append(buffer)
                    self.allocated_bytes += pool_size
                    self.total_deallocations += 1
                else:
                    # 内存不足，直接丢弃
                    self.total_deallocations += 1

            except Exception as e:
                logger.error(f"Failed to return buffer: {e}")

    def _find_best_pool_size(self, size_bytes: int) -> int:
        """找到最适合的池大小

        Args:
            size_bytes: 需要的字节数

        Returns:
            int: 最适合的池大小
        """
        # 找到第一个大于等于需要大小的预定义大小
        for category_size in self.size_categories:
            if category_size >= size_bytes:
                return category_size

        # 如果没有找到合适的预定义大小，使用下一个2的幂次
        return self._next_power_of_two(size_bytes)

    def _next_power_of_two(self, n: int) -> int:
        """计算大于等于n的下一个2的幂次"""
        if n <= 0:
            return 1
        return 1 << (n - 1).bit_length()

    def _cleanup_pools(self) -> bool:
        """清理一些池以释放内存

        Returns:
            bool: 是否成功清理了内存
        """
        try:
            # 清理最大的池
            for size in sorted(self.pools.keys(), reverse=True):
                if self.pools[size]:
                    # 清理一半的缓冲区
                    half_count = len(self.pools[size]) // 2
                    for _ in range(half_count):
                        if self.pools[size]:
                            self.pools[size].pop()
                            self.allocated_bytes -= size

                    if self.allocated_bytes < self.max_memory_bytes * 0.8:
                        return True

            return False
        except Exception as e:
            logger.error(f"Failed to cleanup pools: {e}")
            return False

    def clear_all(self):
        """清空所有池"""
        with self.lock:
            self.pools.clear()
            self.allocated_bytes = 0

    def get_memory_usage(self) -> dict:
        """获取内存使用情况

        Returns:
            dict: 内存使用统计信息
        """
        with self.lock:
            total_pools = sum(len(pool) for pool in self.pools.values())
            return {
                "allocated_mb": self.allocated_bytes / (1024 * 1024),
                "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
                "usage_ratio": self.allocated_bytes / self.max_memory_bytes,
                "total_pools": total_pools,
                "pool_sizes": {size: len(pool) for size, pool in self.pools.items()},
                "total_allocations": self.total_allocations,
                "total_deallocations": self.total_deallocations,
                "cache_hit_rate": self.cache_hits / max(1, self.cache_hits + self.cache_misses)
            }

    def optimize_pools(self):
        """优化池的使用"""
        with self.lock:
            # 移除空的池
            empty_sizes = [size for size, pool in self.pools.items() if not pool]
            for size in empty_sizes:
                del self.pools[size]

            # 合并小的池到大的池
            sorted_sizes = sorted(self.pools.keys())
            for i in range(len(sorted_sizes) - 1):
                small_size = sorted_sizes[i]
                large_size = sorted_sizes[i + 1]

                if (len(self.pools[small_size]) > 10 and
                    len(self.pools[large_size]) < 5):
                    # 将小池的缓冲区合并到大池
                    small_pool = self.pools[small_size]
                    large_pool = self.pools[large_size]

                    # 每个大缓冲区可以容纳多个小缓冲区
                    ratio = large_size // small_size
                    for _ in range(min(len(small_pool) // ratio, 5)):
                        if len(small_pool) >= ratio:
                            # 合并ratio个小缓冲区为一个大缓冲区
                            merged_buffer = bytearray()
                            for _ in range(ratio):
                                if small_pool:
                                    merged_buffer.extend(small_pool.pop())

                            if len(merged_buffer) == large_size:
                                large_pool.append(merged_buffer)
                                self.allocated_bytes += large_size - small_size * ratio
