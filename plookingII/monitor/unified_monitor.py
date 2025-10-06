"""
统一监控器 - 简化整合版

整合 V1 和 V2 的功能，提供轻量、高效的监控能力。

核心功能：
- 性能指标收集
- 内存状态监控
- 自动压力检测
- 统计数据输出

简化改进：
- 移除过度复杂的配置层级
- 优化数据结构减少开销
- 简化API提高易用性
- 保持向后兼容

Author: PlookingII Team
Date: 2025-10-06 (整合简化)
"""

import logging
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from enum import Enum
from functools import wraps
from typing import Any

from ..config.constants import APP_NAME

logger = logging.getLogger(APP_NAME)

# 尝试导入可选依赖
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False


class MonitoringLevel(Enum):
    """监控级别"""

    MINIMAL = "minimal"  # 最小监控：仅关键指标
    STANDARD = "standard"  # 标准监控：平衡性能和详细度（默认）
    DETAILED = "detailed"  # 详细监控：完整指标和历史


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""

    timestamp: float
    operation_name: str
    duration_ms: float
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    cache_hit: bool | None = None
    success: bool = True
    error_msg: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class MemoryStatus:
    """内存状态数据类"""

    used_mb: float
    available_mb: float
    total_mb: float
    percent: float
    pressure_level: str  # 'low', 'medium', 'high', 'critical'
    cache_usage_mb: float = 0.0
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class UnifiedMonitor:
    """统一监控器（整合简化版）

    整合所有监控功能，提供轻量且功能完整的监控能力。
    """

    def __init__(
        self,
        level: MonitoringLevel = MonitoringLevel.STANDARD,
        max_history: int = 500,
        enable_auto_monitoring: bool = False,
    ):
        """初始化统一监控器

        Args:
            level: 监控级别
            max_history: 最大历史记录数
            enable_auto_monitoring: 是否启用自动后台监控
        """
        self.level = level
        self.max_history = max_history

        # 根据监控级别调整历史大小
        if level == MonitoringLevel.MINIMAL:
            self.max_history = min(max_history, 100)
        elif level == MonitoringLevel.DETAILED:
            self.max_history = max(max_history, 1000)

        # 历史数据
        self.performance_history: deque = deque(maxlen=self.max_history)
        self.memory_history: deque = deque(maxlen=self.max_history)

        # 监控状态
        self.is_monitoring = False
        self.monitor_thread: threading.Thread | None = None
        self.stop_event = threading.Event()

        # 内存阈值配置
        self.memory_thresholds = {"cleanup": 0.80, "warning": 0.85, "critical": 0.95}

        # 统计数据
        self.stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "avg_response_time": 0.0,
            "total_response_time": 0.0,
            "memory_cleanups": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        # 线程锁
        self._lock = threading.RLock()

        # 启动自动监控
        if enable_auto_monitoring and HAS_PSUTIL:
            self.start_monitoring()

        logger.info(f"统一监控器已初始化 - 级别: {level.value}, 历史: {self.max_history}")

    def record_operation(
        self,
        operation_name: str,
        duration_ms: float,
        success: bool = True,
        cache_hit: bool | None = None,
        memory_mb: float = 0.0,
        **metadata,
    ) -> None:
        """记录操作指标

        Args:
            operation_name: 操作名称
            duration_ms: 持续时间（毫秒）
            success: 是否成功
            cache_hit: 是否缓存命中
            memory_mb: 内存使用（MB）
            **metadata: 额外元数据
        """
        with self._lock:
            # 创建指标
            metric = PerformanceMetrics(
                timestamp=time.time(),
                operation_name=operation_name,
                duration_ms=duration_ms,
                memory_usage_mb=memory_mb,
                cache_hit=cache_hit,
                success=success,
                metadata=metadata,
            )

            # 记录到历史
            if self.level != MonitoringLevel.MINIMAL:
                self.performance_history.append(metric)

            # 更新统计
            self.stats["total_operations"] += 1
            if success:
                self.stats["successful_operations"] += 1
            else:
                self.stats["failed_operations"] += 1

            self.stats["total_response_time"] += duration_ms
            self.stats["avg_response_time"] = self.stats["total_response_time"] / self.stats["total_operations"]

            # 更新缓存统计
            if cache_hit is not None:
                if cache_hit:
                    self.stats["cache_hits"] += 1
                else:
                    self.stats["cache_misses"] += 1

    def get_memory_status(self) -> MemoryStatus:
        """获取当前内存状态"""
        if not HAS_PSUTIL:
            return MemoryStatus(
                used_mb=0.0,
                available_mb=0.0,
                total_mb=0.0,
                percent=0.0,
                pressure_level="unknown",
                recommendations=["psutil 未安装，无法监控内存"],
            )

        try:
            mem = psutil.virtual_memory()
            used_mb = mem.used / 1024 / 1024
            available_mb = mem.available / 1024 / 1024
            total_mb = mem.total / 1024 / 1024
            percent = mem.percent

            # 判断压力级别
            pressure_level = self._get_pressure_level(percent)

            # 生成建议
            recommendations = self._generate_recommendations(pressure_level, percent)

            status = MemoryStatus(
                used_mb=used_mb,
                available_mb=available_mb,
                total_mb=total_mb,
                percent=percent,
                pressure_level=pressure_level,
                recommendations=recommendations,
            )

            # 记录到历史
            if self.level == MonitoringLevel.DETAILED:
                with self._lock:
                    self.memory_history.append(status)

            return status

        except Exception as e:
            logger.error(f"获取内存状态失败: {e}")
            return MemoryStatus(
                used_mb=0.0,
                available_mb=0.0,
                total_mb=0.0,
                percent=0.0,
                pressure_level="error",
                recommendations=[f"获取内存状态失败: {e}"],
            )

    def _get_pressure_level(self, percent: float) -> str:
        """根据内存使用率判断压力级别"""
        if percent < 70:
            return "low"
        if percent < self.memory_thresholds["cleanup"] * 100:
            return "medium"
        if percent < self.memory_thresholds["critical"] * 100:
            return "high"
        return "critical"

    def _generate_recommendations(self, pressure_level: str, percent: float) -> list[str]:
        """生成内存优化建议"""
        recommendations = []

        if pressure_level == "critical":
            recommendations.append("⚠️ 内存压力极高，建议立即清理缓存")
            recommendations.append("考虑关闭其他应用程序")
        elif pressure_level == "high":
            recommendations.append("内存压力较高，建议清理缓存")
        elif pressure_level == "medium":
            recommendations.append("内存使用正常，注意监控")

        return recommendations

    def start_monitoring(self, interval: float = 5.0) -> None:
        """启动后台监控

        Args:
            interval: 监控间隔（秒）
        """
        if self.is_monitoring or not HAS_PSUTIL:
            return

        self.is_monitoring = True
        self.stop_event.clear()

        def monitor_loop():
            while not self.stop_event.is_set():
                try:
                    # 获取内存状态
                    self.get_memory_status()

                    # 检查是否需要清理
                    status = self.get_memory_status()
                    if status.percent > self.memory_thresholds["cleanup"] * 100:
                        self.stats["memory_cleanups"] += 1
                        logger.warning(f"内存压力: {status.pressure_level} ({status.percent:.1f}%), 建议清理缓存")

                except Exception as e:
                    logger.error(f"监控循环错误: {e}")

                # 等待间隔
                self.stop_event.wait(interval)

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"后台监控已启动，间隔: {interval}秒")

    def stop_monitoring(self) -> None:
        """停止后台监控"""
        if not self.is_monitoring:
            return

        self.stop_event.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)

        self.is_monitoring = False
        logger.info("后台监控已停止")

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            stats = dict(self.stats)

            # 添加缓存命中率
            total_cache_ops = stats["cache_hits"] + stats["cache_misses"]
            if total_cache_ops > 0:
                stats["cache_hit_ratio"] = stats["cache_hits"] / total_cache_ops
            else:
                stats["cache_hit_ratio"] = 0.0

            # 添加成功率
            if stats["total_operations"] > 0:
                stats["success_rate"] = stats["successful_operations"] / stats["total_operations"]
            else:
                stats["success_rate"] = 0.0

            return stats

    def get_recent_operations(self, count: int = 10) -> list[PerformanceMetrics]:
        """获取最近的操作记录"""
        with self._lock:
            history_list = list(self.performance_history)
            return history_list[-count:] if len(history_list) >= count else history_list

    def clear_history(self) -> None:
        """清除历史数据"""
        with self._lock:
            self.performance_history.clear()
            self.memory_history.clear()
        logger.info("监控历史已清除")

    def reset_stats(self) -> None:
        """重置统计数据"""
        with self._lock:
            self.stats = {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "avg_response_time": 0.0,
                "total_response_time": 0.0,
                "memory_cleanups": 0,
                "cache_hits": 0,
                "cache_misses": 0,
            }
        logger.info("监控统计已重置")


# 全局单例
_global_monitor: UnifiedMonitor | None = None
_monitor_lock = threading.Lock()


def get_unified_monitor(level: MonitoringLevel = MonitoringLevel.STANDARD, **kwargs) -> UnifiedMonitor:
    """获取全局统一监控器实例

    Args:
        level: 监控级别
        **kwargs: 传递给 UnifiedMonitor 的额外参数

    Returns:
        全局监控器实例
    """
    global _global_monitor

    with _monitor_lock:
        if _global_monitor is None:
            _global_monitor = UnifiedMonitor(level=level, **kwargs)
            logger.info(f"全局监控器已创建 - 级别: {level.value}")

        return _global_monitor


def reset_unified_monitor() -> None:
    """重置全局监控器"""
    global _global_monitor

    with _monitor_lock:
        if _global_monitor is not None:
            _global_monitor.stop_monitoring()
            _global_monitor = None
            logger.info("全局监控器已重置")


def monitor_performance(operation_name: str):
    """性能监控装饰器

    使用示例:
        @monitor_performance('load_image')
        def load_image(path):
            ...

    Args:
        operation_name: 操作名称
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            result = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                monitor = get_unified_monitor()
                monitor.record_operation(operation_name, duration_ms, success=success)

        return wrapper

    return decorator
