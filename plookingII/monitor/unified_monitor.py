#!/usr/bin/env python3
"""
统一监控器模块

整合所有监控功能，提供统一的监控接口，简化架构复杂度。

主要功能：
- 内存使用监控
- 性能指标收集
- 系统资源监控
- 遥测数据管理

Author: PlookingII Team
Version: 1.0.0
"""

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

from ..config.constants import APP_NAME

logger = logging.getLogger(APP_NAME)

# 尝试导入可选依赖
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: float
    memory_usage_mb: float
    cpu_usage_percent: float
    operation_name: str
    duration_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryStatus:
    """内存状态数据类"""
    used_mb: float
    available_mb: float
    pressure_level: str  # 'low', 'medium', 'high', 'critical'
    cache_usage_mb: float
    recommendations: list[str] = field(default_factory=list)


class UnifiedMonitor:
    """统一监控器

    整合内存监控、性能监控、系统监控等功能。
    """

    def __init__(self, max_history: int = 1000):
        """初始化统一监控器

        Args:
            max_history: 最大历史记录数
        """
        self.max_history = max_history
        self.performance_history: deque = deque(maxlen=max_history)
        self.memory_history: deque = deque(maxlen=max_history)

        # 监控状态
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # 内存阈值配置
        self.memory_thresholds = {
            "cleanup": 0.8,      # 80%时开始清理
            "warning": 0.85,     # 85%时警告
            "critical": 0.95     # 95%时紧急清理
        }

        # 性能统计
        self.stats = {
            "total_operations": 0,
            "avg_response_time": 0.0,
            "memory_cleanups": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }

        logger.info("统一监控器已初始化")

    def start_monitoring(self, interval: float = 5.0):
        """启动监控

        Args:
            interval: 监控间隔（秒）
        """
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.stop_event.clear()

        def monitoring_loop():
            """监控循环"""
            while not self.stop_event.wait(interval):
                try:
                    self._collect_system_metrics()
                except Exception as e:
                    logger.error(f"系统监控失败: {e}")

        self.monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"统一监控已启动，间隔{interval}秒")

    def stop_monitoring(self):
        """停止监控"""
        if self.is_monitoring:
            self.stop_event.set()
            if self.monitor_thread:
                self.monitor_thread.join(timeout=2.0)
            self.is_monitoring = False
            logger.info("统一监控已停止")

    def record_operation(self, operation_name: str, duration_ms: float, **metadata):
        """记录操作性能

        Args:
            operation_name: 操作名称
            duration_ms: 持续时间（毫秒）
            **metadata: 额外的元数据
        """
        try:
            memory_info = self.get_memory_status()

            metric = PerformanceMetrics(
                timestamp=time.time(),
                memory_usage_mb=memory_info.used_mb,
                cpu_usage_percent=self._get_cpu_usage(),
                operation_name=operation_name,
                duration_ms=duration_ms,
                metadata=metadata
            )

            self.performance_history.append(metric)

            # 更新统计信息
            self.stats["total_operations"] += 1
            self._update_avg_response_time(duration_ms)

            # 检查是否需要记录慢操作
            if duration_ms > 1000:  # 超过1秒的操作
                logger.warning(f"慢操作检测: {operation_name} 耗时 {duration_ms:.2f}ms")

        except Exception as e:
            logger.error(f"记录操作性能失败: {e}")

    def get_memory_status(self) -> MemoryStatus:
        """获取内存状态

        Returns:
            MemoryStatus: 内存状态信息
        """
        try:
            if HAS_PSUTIL:
                # 使用psutil获取精确信息
                memory = psutil.virtual_memory()
                used_mb = (memory.total - memory.available) / (1024 ** 2)
                available_mb = memory.available / (1024 ** 2)
                usage_percent = memory.percent / 100.0
            else:
                # 使用系统命令备选方案
                import subprocess
                subprocess.run(["vm_stat"], check=False, capture_output=True, text=True)
                # 简化的内存估算
                used_mb = 512.0  # 估算值
                available_mb = 1024.0  # 估算值
                usage_percent = 0.5

            # 确定压力级别
            if usage_percent > self.memory_thresholds["critical"]:
                pressure_level = "critical"
                recommendations = ["立即清理缓存", "关闭不必要功能"]
            elif usage_percent > self.memory_thresholds["warning"]:
                pressure_level = "high"
                recommendations = ["清理预览缓存", "减少预加载"]
            elif usage_percent > self.memory_thresholds["cleanup"]:
                pressure_level = "medium"
                recommendations = ["渐进式缓存清理"]
            else:
                pressure_level = "low"
                recommendations = []

            return MemoryStatus(
                used_mb=used_mb,
                available_mb=available_mb,
                pressure_level=pressure_level,
                cache_usage_mb=self._estimate_cache_usage(),
                recommendations=recommendations
            )

        except Exception as e:
            logger.error(f"获取内存状态失败: {e}")
            # 返回默认状态
            return MemoryStatus(
                used_mb=0.0,
                available_mb=1024.0,
                pressure_level="unknown",
                cache_usage_mb=0.0,
                recommendations=["监控数据不可用"]
            )

    def is_memory_pressure(self) -> bool:
        """检查是否存在内存压力

        Returns:
            bool: 是否存在内存压力
        """
        memory_status = self.get_memory_status()
        return memory_status.pressure_level in ["high", "critical"]

    def get_performance_summary(self) -> dict[str, Any]:
        """获取性能摘要

        Returns:
            Dict: 性能摘要数据
        """
        if not self.performance_history:
            return {"status": "no_data"}

        recent_metrics = list(self.performance_history)[-100:]  # 最近100个操作

        durations = [m.duration_ms for m in recent_metrics]
        memory_usage = [m.memory_usage_mb for m in recent_metrics]

        return {
            "total_operations": self.stats["total_operations"],
            "avg_response_time": self.stats["avg_response_time"],
            "recent_avg_duration": sum(durations) / len(durations),
            "recent_max_duration": max(durations),
            "recent_min_duration": min(durations),
            "avg_memory_usage": sum(memory_usage) / len(memory_usage),
            "memory_status": self.get_memory_status(),
            "cache_stats": {
                "hits": self.stats["cache_hits"],
                "misses": self.stats["cache_misses"],
                "hit_rate": self._calculate_hit_rate()
            }
        }

    def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            memory_status = self.get_memory_status()

            # 记录到历史
            self.memory_history.append({
                "timestamp": time.time(),
                "used_mb": memory_status.used_mb,
                "pressure_level": memory_status.pressure_level
            })

            # 检查是否需要自动清理
            if memory_status.pressure_level in ["high", "critical"]:
                logger.warning(f"内存压力{memory_status.pressure_level}，建议: {memory_status.recommendations}")

        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")

    def _get_cpu_usage(self) -> float:
        """获取CPU使用率"""
        try:
            if HAS_PSUTIL:
                return psutil.cpu_percent(interval=None)
            return 0.0  # 无法获取时返回0
        except Exception:
            return 0.0

    def _estimate_cache_usage(self) -> float:
        """估算缓存使用量"""
        # 这里可以集成实际的缓存监控
        return 128.0  # 估算值

    def _update_avg_response_time(self, duration_ms: float):
        """更新平均响应时间"""
        total_ops = self.stats["total_operations"]
        current_avg = self.stats["avg_response_time"]

        # 增量平均值计算
        self.stats["avg_response_time"] = (current_avg * (total_ops - 1) + duration_ms) / total_ops

    def _calculate_hit_rate(self) -> float:
        """计算缓存命中率"""
        total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
        if total_requests == 0:
            return 0.0
        return self.stats["cache_hits"] / total_requests

    def record_cache_hit(self):
        """记录缓存命中"""
        self.stats["cache_hits"] += 1

    def record_cache_miss(self):
        """记录缓存未命中"""
        self.stats["cache_misses"] += 1

    def force_cleanup(self):
        """强制内存清理"""
        try:
            import gc
            gc.collect()
            self.stats["memory_cleanups"] += 1
            logger.info("执行强制内存清理")
        except Exception as e:
            logger.error(f"强制内存清理失败: {e}")

    def get_dashboard_data(self) -> dict[str, Any]:
        """获取监控面板数据

        Returns:
            Dict: 完整的监控数据
        """
        return {
            "performance": self.get_performance_summary(),
            "memory": self.get_memory_status().__dict__,
            "system": {
                "monitoring": self.is_monitoring,
                "uptime": time.time() - getattr(self, "_start_time", time.time()),
                "has_psutil": HAS_PSUTIL
            },
            "statistics": self.stats.copy()
        }


# 全局统一监控器实例
_unified_monitor = None

def get_unified_monitor() -> UnifiedMonitor:
    """获取全局统一监控器实例"""
    global _unified_monitor
    if _unified_monitor is None:
        _unified_monitor = UnifiedMonitor()
        _unified_monitor._start_time = time.time()
    return _unified_monitor


# 便捷的性能监控装饰器
def monitor_performance(operation_name: str):
    """性能监控装饰器

    Args:
        operation_name: 操作名称
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                get_unified_monitor().record_operation(operation_name, duration_ms, success=True)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                get_unified_monitor().record_operation(operation_name, duration_ms, success=False, error=str(e))
                raise
        return wrapper
    return decorator
