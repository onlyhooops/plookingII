"""
加载统计

提供简洁的加载统计功能，避免复杂的统计逻辑。

Author: PlookingII Team
Date: 2025-10-06
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class LoadingStats:
    """加载统计信息"""

    total_requests: int = 0
    successful_loads: int = 0
    failed_loads: int = 0
    total_time: float = 0.0

    # 分类统计
    nsimage_loads: int = 0
    quartz_loads: int = 0
    memory_map_loads: int = 0
    fast_loads: int = 0

    def record_success(self, method: str, duration: float) -> None:
        """记录成功加载

        Args:
            method: 加载方法 ('nsimage', 'quartz', 'memory_map', 'fast')
            duration: 加载耗时（秒）
        """
        self.total_requests += 1
        self.successful_loads += 1
        self.total_time += duration

        if method == "nsimage":
            self.nsimage_loads += 1
        elif method == "quartz":
            self.quartz_loads += 1
        elif method == "memory_map":
            self.memory_map_loads += 1
        elif method == "fast":
            self.fast_loads += 1

    def record_failure(self) -> None:
        """记录失败加载"""
        self.total_requests += 1
        self.failed_loads += 1

    def get_stats(self) -> dict[str, Any]:
        """获取统计字典"""
        avg_time = self.total_time / self.total_requests if self.total_requests > 0 else 0.0

        return {
            "total_requests": self.total_requests,
            "successful_loads": self.successful_loads,
            "failed_loads": self.failed_loads,
            "total_time": self.total_time,
            "avg_time": avg_time,
            "nsimage_loads": self.nsimage_loads,
            "quartz_loads": self.quartz_loads,
            "memory_map_loads": self.memory_map_loads,
            "fast_loads": self.fast_loads,
            # 兼容旧字段名
            "total_loads": self.total_requests,
        }

    def reset(self) -> None:
        """重置统计"""
        self.total_requests = 0
        self.successful_loads = 0
        self.failed_loads = 0
        self.total_time = 0.0
        self.nsimage_loads = 0
        self.quartz_loads = 0
        self.memory_map_loads = 0
        self.fast_loads = 0

    def __str__(self) -> str:
        """字符串表示"""
        stats = self.get_stats()
        return (
            f"LoadingStats(requests={stats['total_requests']}, "
            f"success={stats['successful_loads']}, "
            f"failed={stats['failed_loads']}, "
            f"avg_time={stats['avg_time']:.3f}s)"
        )

