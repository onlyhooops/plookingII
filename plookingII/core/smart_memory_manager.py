#!/usr/bin/env python3
"""
智能内存管理器

提供智能的内存管理功能，包括：
- 自适应内存清理
- 内存压力监控
- 重复计算避免
- 内存泄漏检测

Author: PlookingII Team
"""

import gc
import threading
import time
from collections.abc import Callable
from typing import Any

import psutil

from ..config.constants import APP_NAME
from ..imports import logging

logger = logging.getLogger(APP_NAME)

class SmartMemoryManager:
    """智能内存管理器"""

    def __init__(self, memory_limit_mb: float = 2000, cleanup_threshold: float = 0.8):
        """初始化智能内存管理器

        Args:
            memory_limit_mb: 内存限制（MB）
            cleanup_threshold: 清理阈值（0.0-1.0）
        """
        self.memory_limit_mb = memory_limit_mb
        self.cleanup_threshold = cleanup_threshold
        self.lock = threading.RLock()

        # 计算缓存（避免重复计算）
        self.computation_cache = {}
        self.cache_max_size = 1000

        # 内存监控
        self.memory_history = []
        self.max_history_size = 100

        # 清理策略
        self.cleanup_strategies = {
            "gentle": self._gentle_cleanup,
            "moderate": self._moderate_cleanup,
            "aggressive": self._aggressive_cleanup
        }

        # 统计信息
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "cleanups_performed": 0,
            "memory_freed_mb": 0.0,
            "last_cleanup_time": 0
        }

        logger.info(f"Smart memory manager initialized: limit={memory_limit_mb}MB, threshold={cleanup_threshold}")

    def get_memory_usage_mb(self) -> float:
        """获取当前内存使用量（MB）"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024)
        except Exception as e:
            logger.warning(f"Failed to get memory usage: {e}")
            return 0.0

    def get_memory_pressure(self) -> float:
        """获取内存压力（0.0-1.0）"""
        current_usage = self.get_memory_usage_mb()
        pressure = current_usage / self.memory_limit_mb
        return min(pressure, 1.0)

    def is_memory_pressure_high(self) -> bool:
        """检查是否内存压力过高"""
        return self.get_memory_pressure() > self.cleanup_threshold

    def cached_computation(self, key: str, compute_func: Callable, *args, **kwargs) -> Any:
        """带缓存的计算

        Args:
            key: 缓存键
            compute_func: 计算函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            计算结果
        """
        with self.lock:
            # 检查缓存
            if key in self.computation_cache:
                self.stats["cache_hits"] += 1
                return self.computation_cache[key]

            # 执行计算
            try:
                result = compute_func(*args, **kwargs)

                # 缓存结果
                if len(self.computation_cache) < self.cache_max_size:
                    self.computation_cache[key] = result
                else:
                    # 缓存已满，清理一些旧项
                    self._cleanup_cache()
                    if len(self.computation_cache) < self.cache_max_size:
                        self.computation_cache[key] = result

                self.stats["cache_misses"] += 1
                return result

            except Exception as e:
                logger.error(f"Computation failed for key {key}: {e}")
                raise

    def get_file_size_mb(self, file_path: str) -> float:
        """获取文件大小（MB），带缓存"""
        def _compute_file_size():
            import os

            try:
                return os.path.getsize(file_path) / (1024 * 1024)
            except OSError:
                return 0.0

        return self.cached_computation(f"file_size:{file_path}", _compute_file_size)

    def get_image_dimensions(self, file_path: str) -> tuple | None:
        """获取图像尺寸，带缓存"""
        def _compute_dimensions():
            try:
                from .functions import get_image_dimensions_safe
                return get_image_dimensions_safe(file_path)
            except Exception:
                return None

        return self.cached_computation(f"image_dimensions:{file_path}", _compute_dimensions)

    def adaptive_cleanup(self) -> str:
        """自适应内存清理

        Returns:
            执行的清理策略名称
        """
        with self.lock:
            pressure = self.get_memory_pressure()

            if pressure < 0.6:
                # 内存压力低，不清理
                return "none"
            if pressure < 0.8:
                # 内存压力中等，温和清理
                strategy = "gentle"
            elif pressure < 0.95:
                # 内存压力高，适度清理
                strategy = "moderate"
            else:
                # 内存压力极高，激进清理
                strategy = "aggressive"

            # 执行清理
            if strategy in self.cleanup_strategies:
                self.cleanup_strategies[strategy]()
                self.stats["cleanups_performed"] += 1
                self.stats["last_cleanup_time"] = time.time()
                logger.info(f"Performed {strategy} memory cleanup")
                return strategy

            return "none"

    def _gentle_cleanup(self):
        """温和清理"""
        # 清理计算缓存
        if len(self.computation_cache) > self.cache_max_size // 2:
            self._cleanup_cache()

        # 执行垃圾回收
        gc.collect()

    def _moderate_cleanup(self):
        """适度清理"""
        # 清理计算缓存
        self._cleanup_cache()

        # 清理内存历史
        if len(self.memory_history) > self.max_history_size // 2:
            self.memory_history = self.memory_history[-self.max_history_size // 2:]

        # 执行垃圾回收
        gc.collect()

    def _aggressive_cleanup(self):
        """激进清理"""
        # 清空计算缓存
        self.computation_cache.clear()

        # 清空内存历史
        self.memory_history.clear()

        # 多次垃圾回收
        for _ in range(3):
            gc.collect()

        # 记录清理的内存
        self.stats["memory_freed_mb"] += self.get_memory_usage_mb()

    def _cleanup_cache(self):
        """清理计算缓存"""
        if not self.computation_cache:
            return

        # 保留最近使用的一半
        keep_count = len(self.computation_cache) // 2
        items_to_remove = list(self.computation_cache.keys())[:-keep_count]

        for key in items_to_remove:
            del self.computation_cache[key]

    def monitor_memory(self):
        """监控内存使用情况"""
        current_usage = self.get_memory_usage_mb()
        pressure = self.get_memory_pressure()

        # 记录内存历史
        self.memory_history.append({
            "timestamp": time.time(),
            "usage_mb": current_usage,
            "pressure": pressure
        })

        # 限制历史记录大小
        if len(self.memory_history) > self.max_history_size:
            self.memory_history = self.memory_history[-self.max_history_size:]

        # 检查是否需要清理
        if self.is_memory_pressure_high():
            self.adaptive_cleanup()

    def get_stats(self) -> dict[str, Any]:
        """获取内存管理统计信息

        Returns:
            统计信息字典
        """
        with self.lock:
            current_usage = self.get_memory_usage_mb()
            pressure = self.get_memory_pressure()

            cache_hit_rate = 0.0
            total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
            if total_requests > 0:
                cache_hit_rate = self.stats["cache_hits"] / total_requests

            return {
                "current_usage_mb": current_usage,
                "memory_limit_mb": self.memory_limit_mb,
                "memory_pressure": pressure,
                "cache_size": len(self.computation_cache),
                "cache_hit_rate": cache_hit_rate,
                "cache_hits": self.stats["cache_hits"],
                "cache_misses": self.stats["cache_misses"],
                "cleanups_performed": self.stats["cleanups_performed"],
                "memory_freed_mb": self.stats["memory_freed_mb"],
                "last_cleanup_time": self.stats["last_cleanup_time"]
            }

    def _estimate_image_size(self, image: Any) -> float:
        """估算图像的内存大小

        Args:
            image: 图像对象

        Returns:
            float: 估算的内存大小（MB）
        """
        try:
            if image is None:
                return 0.0

            # 如果是NSImage对象，尝试获取实际尺寸
            if hasattr(image, "size"):
                size = image.size()
                width = size.width
                height = size.height
                # 假设32位RGBA（4字节每像素）
                bytes_estimate = width * height * 4
                return bytes_estimate / (1024 * 1024)  # 转换为MB

            # 如果是其他类型的图像，使用系统大小估算
            import sys
            return sys.getsizeof(image) / (1024 * 1024)

        except Exception as e:
            logger.error(f"Failed to estimate image size: {e}")
            return 1.0  # 默认返回1MB

    def force_cleanup(self):
        """强制清理所有缓存"""
        with self.lock:
            self.computation_cache.clear()
            self.memory_history.clear()

            # 多次垃圾回收
            for _ in range(3):
                gc.collect()

            logger.info("Forced memory cleanup completed")

    def set_memory_limit(self, limit_mb: float):
        """设置内存限制

        Args:
            limit_mb: 新的内存限制（MB）
        """
        with self.lock:
            self.memory_limit_mb = limit_mb
            logger.info(f"Memory limit updated to {limit_mb}MB")

    def set_cleanup_threshold(self, threshold: float):
        """设置清理阈值

        Args:
            threshold: 新的清理阈值（0.0-1.0）
        """
        with self.lock:
            self.cleanup_threshold = max(0.0, min(1.0, threshold))
            logger.info(f"Cleanup threshold updated to {self.cleanup_threshold}")

class MemoryMonitor:
    """智能内存监控器（专用于SmartMemoryManager）"""

    def __init__(self, memory_manager: SmartMemoryManager, interval: float = 30.0):
        """初始化内存监控器

        Args:
            memory_manager: 内存管理器
            interval: 监控间隔（秒）
        """
        self.memory_manager = memory_manager
        self.interval = interval
        self.monitoring = False
        self.monitor_thread = None
        self.lock = threading.Lock()

    def start_monitoring(self):
        """开始监控"""
        with self.lock:
            if not self.monitoring:
                self.monitoring = True
                self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                self.monitor_thread.start()
                logger.info("Memory monitoring started")

    def stop_monitoring(self):
        """停止监控"""
        with self.lock:
            if self.monitoring:
                self.monitoring = False
                if self.monitor_thread:
                    self.monitor_thread.join(timeout=1.0)
                logger.info("Memory monitoring stopped")

    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                self.memory_manager.monitor_memory()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                time.sleep(self.interval)
