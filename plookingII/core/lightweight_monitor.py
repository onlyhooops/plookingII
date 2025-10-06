#!/usr/bin/env python3
"""
轻量级监控系统

提供轻量级的性能监控功能，只监控关键指标。

主要特性：
- 关键指标监控
- 低开销设计
- 实时统计
- 性能报告
- 线程安全

Author: PlookingII Team
"""

import threading
import time
from collections import deque
from typing import Any

from ..config.constants import APP_NAME
from ..imports import logging

logger = logging.getLogger(APP_NAME)

class LightweightMonitor:
    """轻量级监控系统

    只监控关键性能指标，减少监控开销。
    """

    def __init__(self, max_history: int = 100):
        """初始化轻量级监控系统

        Args:
            max_history: 最大历史记录数量
        """
        self.max_history = max_history
        self.lock = threading.RLock()

        # 关键指标
        self.metrics = {
            "cache_hit_rate": 0.0,           # 缓存命中率
            "avg_load_time": 0.0,            # 平均加载时间
            "memory_usage_mb": 0.0,          # 内存使用量（MB）
            "total_requests": 0,             # 总请求数
            "error_count": 0,                # 错误数量
            "last_update_time": 0.0          # 最后更新时间
        }

        # 历史记录
        self.history = {
            "load_times": deque(maxlen=max_history),
            "memory_usage": deque(maxlen=max_history),
            "cache_hit_rates": deque(maxlen=max_history)
        }

        # 计数器
        self.counters = {
            "cache_hits": 0,
            "cache_misses": 0,
            "successful_loads": 0,
            "failed_loads": 0
        }

        logger.info("Lightweight monitor initialized")

    def record_cache_hit(self):
        """记录缓存命中"""
        with self.lock:
            self.counters["cache_hits"] += 1
            self._update_cache_hit_rate()

    def record_cache_miss(self):
        """记录缓存未命中"""
        with self.lock:
            self.counters["cache_misses"] += 1
            self._update_cache_hit_rate()

    def record_load_time(self, load_time: float, success: bool = True):
        """记录加载时间

        Args:
            load_time: 加载时间（秒）
            success: 是否成功
        """
        with self.lock:
            self.history["load_times"].append(load_time)
            self._update_avg_load_time()

            if success:
                self.counters["successful_loads"] += 1
            else:
                self.counters["failed_loads"] += 1
                self.metrics["error_count"] += 1

    def record_memory_usage(self, memory_mb: float):
        """记录内存使用量

        Args:
            memory_mb: 内存使用量（MB）
        """
        with self.lock:
            self.metrics["memory_usage_mb"] = memory_mb
            self.history["memory_usage"].append(memory_mb)

    def record_request(self):
        """记录请求"""
        with self.lock:
            self.metrics["total_requests"] += 1

    def _update_cache_hit_rate(self):
        """更新缓存命中率"""
        total_requests = self.counters["cache_hits"] + self.counters["cache_misses"]
        if total_requests > 0:
            self.metrics["cache_hit_rate"] = self.counters["cache_hits"] / total_requests
            self.history["cache_hit_rates"].append(self.metrics["cache_hit_rate"])

    def _update_avg_load_time(self):
        """更新平均加载时间"""
        if self.history["load_times"]:
            self.metrics["avg_load_time"] = sum(self.history["load_times"]) / len(self.history["load_times"])

    def get_metrics(self) -> dict[str, Any]:
        """获取当前指标

        Returns:
            指标字典
        """
        with self.lock:
            self.metrics["last_update_time"] = time.time()
            return self.metrics.copy()

    def get_history(self) -> dict[str, list]:
        """获取历史记录

        Returns:
            历史记录字典
        """
        with self.lock:
            return {
                "load_times": list(self.history["load_times"]),
                "memory_usage": list(self.history["memory_usage"]),
                "cache_hit_rates": list(self.history["cache_hit_rates"])
            }

    def get_summary(self) -> dict[str, Any]:
        """获取性能摘要

        Returns:
            性能摘要字典
        """
        with self.lock:
            total_loads = self.counters["successful_loads"] + self.counters["failed_loads"]
            success_rate = 0.0
            if total_loads > 0:
                success_rate = self.counters["successful_loads"] / total_loads

            return {
                "cache_hit_rate": self.metrics["cache_hit_rate"],
                "avg_load_time": self.metrics["avg_load_time"],
                "memory_usage_mb": self.metrics["memory_usage_mb"],
                "total_requests": self.metrics["total_requests"],
                "success_rate": success_rate,
                "error_count": self.metrics["error_count"],
                "total_loads": total_loads,
                "last_update_time": self.metrics["last_update_time"]
            }

    def reset(self):
        """重置监控数据"""
        with self.lock:
            self.metrics = {
                "cache_hit_rate": 0.0,
                "avg_load_time": 0.0,
                "memory_usage_mb": 0.0,
                "total_requests": 0,
                "error_count": 0,
                "last_update_time": 0.0
            }

            for history_list in self.history.values():
                history_list.clear()

            for key in list(self.counters.keys()):
                self.counters[key] = 0

            logger.info("Monitor data reset")

    def get_performance_report(self) -> str:
        """获取性能报告

        Returns:
            性能报告字符串
        """
        summary = self.get_summary()

        report = f"""
PlookingII Performance Report
============================
Cache Hit Rate: {summary['cache_hit_rate']:.2%}
Average Load Time: {summary['avg_load_time']:.3f}s
Memory Usage: {summary['memory_usage_mb']:.1f}MB
Total Requests: {summary['total_requests']}
Success Rate: {summary['success_rate']:.2%}
Error Count: {summary['error_count']}
Total Loads: {summary['total_loads']}
Last Update: {time.ctime(summary['last_update_time'])}
        """.strip()

        return report

    def is_performance_good(self) -> bool:
        """检查性能是否良好

        Returns:
            性能是否良好
        """
        summary = self.get_summary()

        # 性能标准
        good_cache_hit_rate = summary["cache_hit_rate"] >= 0.7
        good_load_time = summary["avg_load_time"] <= 2.0
        good_success_rate = summary["success_rate"] >= 0.95

        return good_cache_hit_rate and good_load_time and good_success_rate

    def get_recommendations(self) -> list:
        """获取性能优化建议

        Returns:
            建议列表
        """
        recommendations = []
        summary = self.get_summary()

        # 缓存命中率建议
        if summary["cache_hit_rate"] < 0.7:
            recommendations.append("缓存命中率较低，建议增加缓存大小或优化缓存策略")

        # 加载时间建议
        if summary["avg_load_time"] > 2.0:
            recommendations.append("平均加载时间较长，建议优化图像处理流程或使用更快的加载方法")

        # 成功率建议
        if summary["success_rate"] < 0.95:
            recommendations.append("成功率较低，建议检查错误日志并优化错误处理")

        # 内存使用建议
        if summary["memory_usage_mb"] > 1000:
            recommendations.append("内存使用量较高，建议优化内存管理或减少缓存大小")

        return recommendations

class PerformanceTracker:
    """性能跟踪器"""

    def __init__(self, monitor: LightweightMonitor):
        """初始化性能跟踪器

        Args:
            monitor: 监控系统
        """
        self.monitor = monitor
        self.start_time = None
        self.operation_name = None

    def __enter__(self):
        """进入上下文"""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if self.start_time:
            duration = time.time() - self.start_time
            success = exc_type is None
            self.monitor.record_load_time(duration, success)

    def set_operation_name(self, name: str):
        """设置操作名称

        Args:
            name: 操作名称
        """
        self.operation_name = name

# 全局监控实例
lightweight_monitor = LightweightMonitor()

def get_monitor() -> LightweightMonitor:
    """获取全局监控实例

    Returns:
        监控实例
    """
    return lightweight_monitor

def track_performance(operation_name: str = None):
    """性能跟踪装饰器

    Args:
        operation_name: 操作名称

    Returns:
        装饰器函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with PerformanceTracker(lightweight_monitor) as tracker:
                if operation_name:
                    tracker.set_operation_name(operation_name)
                return func(*args, **kwargs)
        return wrapper
    return decorator
