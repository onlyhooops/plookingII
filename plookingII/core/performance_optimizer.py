#!/usr/bin/env python3
"""
性能优化器

集中管理所有性能优化策略，提供极致的图片加载和UI响应性能。

主要特性：
- CGImage零拷贝渲染优化
- 智能预加载与缓存策略
- 高频操作防抖与节流
- 内存管理与自动清理
- 性能监控与自适应调优

Author: PlookingII Team
"""

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from ..config.constants import APP_NAME
from ..config.manager import Config

logger = logging.getLogger(APP_NAME)


class CGImageOptimizer:
    """CGImage零拷贝渲染优化器

    提供极致的图片加载性能，避免不必要的内存拷贝和格式转换。
    """

    def __init__(self):
        """初始化CGImage优化器"""
        self._cgimage_cache = {}  # CGImage对象缓存
        self._cache_lock = threading.RLock()
        self._max_cache_size = 10  # 只缓存最近的10张CGImage
        self._access_order = deque(maxlen=10)

        # 性能统计
        self.stats = {"cgimage_hits": 0, "cgimage_creates": 0, "zero_copy_renders": 0, "total_render_time": 0.0}

    def get_cgimage(self, image_path: str, create_func: Callable | None = None) -> Any | None:
        """获取CGImage对象，优先从缓存获取

        Args:
            image_path: 图片路径
            create_func: 创建CGImage的函数

        Returns:
            CGImage对象或None
        """
        with self._cache_lock:
            # 检查缓存
            if image_path in self._cgimage_cache:
                self.stats["cgimage_hits"] += 1
                self._access_order.append(image_path)
                return self._cgimage_cache[image_path]

            # 创建新的CGImage
            if create_func:
                try:
                    cgimage = create_func(image_path)
                    if cgimage:
                        self._cache_cgimage(image_path, cgimage)
                        self.stats["cgimage_creates"] += 1
                        return cgimage
                except Exception:
                    logger.warning("Failed to create CGImage for %s: {e}", image_path)

            return None

    def _cache_cgimage(self, image_path: str, cgimage: Any):
        """缓存CGImage对象

        Args:
            image_path: 图片路径
            cgimage: CGImage对象
        """
        # 如果缓存已满，移除最旧的项
        if len(self._cgimage_cache) >= self._max_cache_size and self._access_order:
            oldest = self._access_order.popleft()
            self._cgimage_cache.pop(oldest, None)

        self._cgimage_cache[image_path] = cgimage
        self._access_order.append(image_path)

    def clear_cache(self):
        """清空CGImage缓存"""
        with self._cache_lock:
            self._cgimage_cache.clear()
            self._access_order.clear()

    def record_render(self, render_time: float):
        """记录渲染时间

        Args:
            render_time: 渲染耗时（秒）
        """
        self.stats["zero_copy_renders"] += 1
        self.stats["total_render_time"] += render_time

    def get_stats(self) -> dict:
        """获取性能统计信息

        Returns:
            统计信息字典
        """
        total_ops = self.stats["cgimage_hits"] + self.stats["cgimage_creates"]
        hit_rate = (self.stats["cgimage_hits"] / total_ops * 100) if total_ops > 0 else 0.0
        avg_render_time = (
            self.stats["total_render_time"] / self.stats["zero_copy_renders"]
            if self.stats["zero_copy_renders"] > 0
            else 0.0
        )

        return {
            **self.stats,
            "cache_size": len(self._cgimage_cache),
            "hit_rate": hit_rate,
            "avg_render_time_ms": avg_render_time * 1000,
        }


class NavigationOptimizer:
    """导航操作优化器

    提供极致的按键响应性能，确保UI更新与按键同步。
    """

    def __init__(self):
        """初始化导航优化器"""
        self._last_navigation_time = 0.0
        self._navigation_velocity = 0.0  # 导航速度（图片/秒）
        self._velocity_history = deque(maxlen=5)  # 速度历史记录

        # 自适应防抖参数
        self._min_debounce_ms = 5  # 最小防抖时间：5ms
        self._max_debounce_ms = 20  # 最大防抖时间：20ms
        self._current_debounce_ms = 15  # 当前防抖时间

        # 性能统计
        self.stats = {"total_navigations": 0, "avg_response_time_ms": 0.0, "max_velocity": 0.0}

    def calculate_optimal_debounce(self, current_time: float) -> float:
        """计算最优防抖时间

        根据用户的导航速度自适应调整防抖时间。
        快速浏览时降低防抖，慢速浏览时提高防抖。

        Args:
            current_time: 当前时间戳

        Returns:
            最优防抖时间（秒）
        """
        # 计算导航速度
        if self._last_navigation_time > 0:
            time_delta = current_time - self._last_navigation_time
            if time_delta > 0:
                velocity = 1.0 / time_delta  # 图片/秒
                self._velocity_history.append(velocity)

                # 计算平均速度
                avg_velocity = sum(self._velocity_history) / len(self._velocity_history)
                self._navigation_velocity = avg_velocity

                # 更新最大速度统计
                self.stats["max_velocity"] = max(self.stats["max_velocity"], avg_velocity)

                # 自适应调整防抖时间
                # 速度越快，防抖越短
                if avg_velocity > 5.0:  # 非常快速浏览（>5图片/秒）
                    self._current_debounce_ms = self._min_debounce_ms
                elif avg_velocity > 2.0:  # 快速浏览（2-5图片/秒）
                    self._current_debounce_ms = 10
                else:  # 正常浏览（<2图片/秒）
                    self._current_debounce_ms = self._max_debounce_ms

        self._last_navigation_time = current_time
        self.stats["total_navigations"] += 1

        return self._current_debounce_ms / 1000.0  # 转换为秒

    def should_skip_intermediate_frames(self) -> bool:
        """判断是否应跳过中间帧

        在高速浏览时，跳过中间帧可以显著提升响应性。

        Returns:
            是否跳过中间帧
        """
        return self._navigation_velocity > 3.0  # 速度>3图片/秒时跳帧

    def get_stats(self) -> dict:
        """获取性能统计信息

        Returns:
            统计信息字典
        """
        return {
            **self.stats,
            "current_velocity": self._navigation_velocity,
            "current_debounce_ms": self._current_debounce_ms,
        }


class PreloadOptimizer:
    """预加载优化器

    智能预测用户浏览方向，提前加载图片。
    """

    def __init__(self):
        """初始化预加载优化器"""
        self._navigation_direction = 0  # 1:向前, -1:向后, 0:未知
        self._direction_history = deque(maxlen=10)

        # 预加载配置
        self._forward_preload_count = 3  # 向前预加载3张
        self._backward_preload_count = 1  # 向后预加载1张

        # 性能统计
        self.stats = {"preload_hits": 0, "preload_misses": 0, "total_preloaded": 0}

    def update_direction(self, from_index: int, to_index: int):
        """更新导航方向

        Args:
            from_index: 起始索引
            to_index: 目标索引
        """
        if to_index > from_index:
            direction = 1  # 向前
        elif to_index < from_index:
            direction = -1  # 向后
        else:
            direction = 0  # 未移动

        self._direction_history.append(direction)

        # 计算主导方向
        if len(self._direction_history) >= 3:
            forward_count = sum(1 for d in self._direction_history if d == 1)
            backward_count = sum(1 for d in self._direction_history if d == -1)

            if forward_count > backward_count:
                self._navigation_direction = 1
            elif backward_count > forward_count:
                self._navigation_direction = -1
            else:
                self._navigation_direction = 0

    def get_preload_indices(self, current_index: int, total_count: int) -> list:
        """获取应该预加载的图片索引列表

        Args:
            current_index: 当前图片索引
            total_count: 图片总数

        Returns:
            预加载索引列表
        """
        indices = []

        # 根据导航方向调整预加载策略
        if self._navigation_direction >= 0:  # 向前或未知
            # 向前预加载更多
            forward = min(self._forward_preload_count, total_count - current_index - 1)
            backward = min(1, current_index)
        else:  # 向后
            # 向后预加载更多
            forward = min(1, total_count - current_index - 1)
            backward = min(self._backward_preload_count, current_index)

        # 添加向前的索引
        for i in range(1, forward + 1):
            idx = current_index + i
            if 0 <= idx < total_count:
                indices.append(idx)

        # 添加向后的索引
        for i in range(1, backward + 1):
            idx = current_index - i
            if 0 <= idx < total_count:
                indices.append(idx)

        return indices

    def record_preload_hit(self):
        """记录预加载命中"""
        self.stats["preload_hits"] += 1

    def record_preload_miss(self):
        """记录预加载未命中"""
        self.stats["preload_misses"] += 1

    def get_stats(self) -> dict:
        """获取性能统计信息

        Returns:
            统计信息字典
        """
        total = self.stats["preload_hits"] + self.stats["preload_misses"]
        hit_rate = (self.stats["preload_hits"] / total * 100) if total > 0 else 0.0

        return {**self.stats, "direction": self._navigation_direction, "hit_rate": hit_rate}


class MemoryOptimizer:
    """内存优化器

    智能管理内存使用，防止内存溢出。
    """

    def __init__(self, max_memory_mb: float = 2048.0):
        """初始化内存优化器

        Args:
            max_memory_mb: 最大内存限制（MB）
        """
        self._max_memory_bytes = max_memory_mb * 1024 * 1024
        self._current_memory_bytes = 0.0
        self._memory_lock = threading.RLock()

        # 清理阈值
        self._cleanup_threshold = 0.85  # 85%时触发清理
        self._target_threshold = 0.70  # 清理到70%

        # 性能统计
        self.stats = {"cleanup_count": 0, "total_freed_mb": 0.0, "peak_memory_mb": 0.0}

    def allocate(self, size_bytes: float) -> bool:
        """分配内存

        Args:
            size_bytes: 需要分配的内存大小（字节）

        Returns:
            是否分配成功
        """
        with self._memory_lock:
            if self._current_memory_bytes + size_bytes > self._max_memory_bytes:
                return False

            self._current_memory_bytes += size_bytes

            # 更新峰值记录
            current_mb = self._current_memory_bytes / 1024 / 1024
            self.stats["peak_memory_mb"] = max(self.stats["peak_memory_mb"], current_mb)

            return True

    def free(self, size_bytes: float):
        """释放内存

        Args:
            size_bytes: 释放的内存大小（字节）
        """
        with self._memory_lock:
            self._current_memory_bytes = max(0, self._current_memory_bytes - size_bytes)

    def should_cleanup(self) -> bool:
        """判断是否应该清理内存

        Returns:
            是否应该清理
        """
        usage_ratio = self._current_memory_bytes / self._max_memory_bytes
        return usage_ratio >= self._cleanup_threshold

    def get_target_free_bytes(self) -> float:
        """获取需要释放的内存量

        Returns:
            需要释放的字节数
        """
        target_bytes = self._max_memory_bytes * self._target_threshold
        return max(0, self._current_memory_bytes - target_bytes)

    def record_cleanup(self, freed_bytes: float):
        """记录清理操作

        Args:
            freed_bytes: 释放的字节数
        """
        self.stats["cleanup_count"] += 1
        self.stats["total_freed_mb"] += freed_bytes / 1024 / 1024

    def get_stats(self) -> dict:
        """获取内存统计信息

        Returns:
            统计信息字典
        """
        return {
            **self.stats,
            "current_memory_mb": self._current_memory_bytes / 1024 / 1024,
            "max_memory_mb": self._max_memory_bytes / 1024 / 1024,
            "usage_percent": (self._current_memory_bytes / self._max_memory_bytes * 100),
        }


class PerformanceOptimizer:
    """性能优化器总控

    集成所有性能优化组件，提供统一的优化接口。
    """

    def __init__(self):
        """初始化性能优化器"""
        # 获取配置
        perf_config = Config.get_performance_config()

        # 初始化各个优化器
        self.cgimage_optimizer = CGImageOptimizer()
        self.navigation_optimizer = NavigationOptimizer()
        self.preload_optimizer = PreloadOptimizer()

        max_memory_mb = perf_config.get("max_memory_mb", 2048.0)
        self.memory_optimizer = MemoryOptimizer(max_memory_mb)

        logger.info("PerformanceOptimizer initialized with all sub-optimizers")

    def optimize_image_loading(self, image_path: str, create_func: Callable) -> Any | None:
        """优化图片加载

        Args:
            image_path: 图片路径
            create_func: 创建CGImage的函数

        Returns:
            CGImage对象或None
        """
        return self.cgimage_optimizer.get_cgimage(image_path, create_func)

    def optimize_navigation(self, from_index: int, to_index: int, total_count: int) -> dict:
        """优化导航操作

        Args:
            from_index: 起始索引
            to_index: 目标索引
            total_count: 总图片数

        Returns:
            优化建议字典
        """
        current_time = time.time()

        # 计算最优防抖时间
        optimal_debounce = self.navigation_optimizer.calculate_optimal_debounce(current_time)

        # 更新预加载方向
        self.preload_optimizer.update_direction(from_index, to_index)

        # 获取预加载索引
        preload_indices = self.preload_optimizer.get_preload_indices(to_index, total_count)

        # 判断是否跳帧
        skip_frames = self.navigation_optimizer.should_skip_intermediate_frames()

        return {
            "optimal_debounce_sec": optimal_debounce,
            "preload_indices": preload_indices,
            "skip_intermediate_frames": skip_frames,
            "navigation_velocity": self.navigation_optimizer._navigation_velocity,
        }

    def check_memory_and_cleanup(self, cleanup_callback: Callable | None = None) -> bool:
        """检查内存并清理

        Args:
            cleanup_callback: 清理回调函数

        Returns:
            是否执行了清理
        """
        if self.memory_optimizer.should_cleanup():
            target_free_bytes = self.memory_optimizer.get_target_free_bytes()

            if cleanup_callback:
                try:
                    freed_bytes = cleanup_callback(target_free_bytes)
                    self.memory_optimizer.record_cleanup(freed_bytes)
                    return True
                except Exception as e:
                    logger.warning("Cleanup callback failed: %s", e)

            # 清理CGImage缓存
            self.cgimage_optimizer.clear_cache()
            return True

        return False

    def get_all_stats(self) -> dict:
        """获取所有性能统计信息

        Returns:
            汇总的统计信息字典
        """
        return {
            "cgimage": self.cgimage_optimizer.get_stats(),
            "navigation": self.navigation_optimizer.get_stats(),
            "preload": self.preload_optimizer.get_stats(),
            "memory": self.memory_optimizer.get_stats(),
        }


# 全局性能优化器实例
_global_optimizer = None
_optimizer_lock = threading.Lock()


def get_performance_optimizer() -> PerformanceOptimizer:
    """获取全局性能优化器实例

    Returns:
        性能优化器实例
    """
    global _global_optimizer  # noqa: PLW0603  # 单例模式的合理使用

    with _optimizer_lock:
        if _global_optimizer is None:
            _global_optimizer = PerformanceOptimizer()
        return _global_optimizer


def reset_performance_optimizer():
    """重置全局性能优化器（主要用于测试）"""
    global _global_optimizer  # noqa: PLW0603  # 单例模式的合理使用

    with _optimizer_lock:
        _global_optimizer = None


__all__ = [
    "CGImageOptimizer",
    "MemoryOptimizer",
    "NavigationOptimizer",
    "PerformanceOptimizer",
    "PreloadOptimizer",
    "get_performance_optimizer",
    "reset_performance_optimizer",
]
