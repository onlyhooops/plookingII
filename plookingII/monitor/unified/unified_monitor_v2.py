"""
统一监控器 V2.0

整合所有监控功能，提供可配置的监控级别和全面的性能分析。

核心改进：
- 可配置监控级别（minimal/standard/detailed）
- 统一的指标收集接口
- 智能内存压力检测
- 自动性能优化建议
- 线程安全的统计数据
"""

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from enum import Enum
from functools import wraps
from typing import Any

from ...config.constants import APP_NAME

logger = logging.getLogger(APP_NAME)

# 尝试导入可选依赖
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False


class MonitoringLevel(Enum):
    """监控级别枚举"""
    MINIMAL = "minimal"      # 最小监控：仅关键指标
    STANDARD = "standard"    # 标准监控：平衡性能和详细度（默认）
    DETAILED = "detailed"    # 详细监控：完整指标和历史


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


class UnifiedMonitorV2:
    """统一监控器 V2.0

    整合所有监控功能，提供灵活的监控级别配置。
    """

    def __init__(
        self,
        level: MonitoringLevel = MonitoringLevel.STANDARD,
        max_history: int = 1000,
        enable_auto_monitoring: bool = False,
        monitoring_interval: float = 5.0
    ):
        """初始化统一监控器

        Args:
            level: 监控级别
            max_history: 最大历史记录数
            enable_auto_monitoring: 是否启用自动监控
            monitoring_interval: 自动监控间隔（秒）
        """
        self.level = level
        self.max_history = max_history
        self.monitoring_interval = monitoring_interval

        # 根据监控级别调整历史大小
        if level == MonitoringLevel.MINIMAL:
            self.max_history = min(100, max_history)
        elif level == MonitoringLevel.STANDARD:
            self.max_history = min(500, max_history)
        # DETAILED 使用完整 max_history

        # 线程安全锁
        self._lock = threading.RLock()

        # 历史数据
        self.performance_history: deque = deque(maxlen=self.max_history)
        self.memory_history: deque = deque(maxlen=self.max_history // 10)  # 内存历史较少

        # 监控状态
        self.is_monitoring = False
        self.monitor_thread: threading.Thread | None = None
        self.stop_event = threading.Event()

        # 内存阈值配置
        self.memory_thresholds = {
            "cleanup": 0.75,    # 75%时开始清理
            "warning": 0.85,    # 85%时警告
            "critical": 0.95    # 95%时紧急清理
        }

        # 统计数据
        self.stats = {
            # 操作统计
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,

            # 时间统计
            "total_duration_ms": 0.0,
            "avg_duration_ms": 0.0,
            "min_duration_ms": float("inf"),
            "max_duration_ms": 0.0,

            # 缓存统计
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_hit_rate": 0.0,

            # 内存统计
            "memory_cleanups": 0,
            "peak_memory_mb": 0.0,
            "avg_memory_mb": 0.0,

            # 错误统计
            "error_count": 0,
            "error_rate": 0.0,

            # 启动时间
            "start_time": time.time(),
            "last_update": time.time(),
        }

        # 操作类型计数器
        self.operation_counts: dict[str, int] = {}
        self.operation_durations: dict[str, list[float]] = {}

        logger.info(f"统一监控器 V2 已初始化 (级别: {level.value}, 历史: {self.max_history})")

        # 自动启动监控
        if enable_auto_monitoring:
            self.start_monitoring(monitoring_interval)

    def start_monitoring(self, interval: float | None = None):
        """启动自动监控

        Args:
            interval: 监控间隔（秒），None 则使用初始化时的值
        """
        if self.is_monitoring:
            logger.warning("监控已在运行中")
            return

        if interval is not None:
            self.monitoring_interval = interval

        self.is_monitoring = True
        self.stop_event.clear()

        def monitoring_loop():
            """监控循环"""
            while not self.stop_event.wait(self.monitoring_interval):
                try:
                    self._collect_system_metrics()
                except Exception as e:
                    logger.error(f"系统监控失败: {e}", exc_info=True)

        self.monitor_thread = threading.Thread(
            target=monitoring_loop,
            daemon=True,
            name="UnifiedMonitorV2-Thread"
        )
        self.monitor_thread.start()
        logger.info(f"统一监控已启动，间隔 {self.monitoring_interval}秒")

    def stop_monitoring(self):
        """停止自动监控"""
        if not self.is_monitoring:
            return

        self.stop_event.set()
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)

        self.is_monitoring = False
        logger.info("统一监控已停止")

    def record_operation(
        self,
        operation_name: str,
        duration_ms: float,
        cache_hit: bool | None = None,
        success: bool = True,
        error_msg: str | None = None,
        **metadata
    ):
        """记录操作性能

        Args:
            operation_name: 操作名称
            duration_ms: 持续时间（毫秒）
            cache_hit: 是否缓存命中（None表示不记录缓存）
            success: 操作是否成功
            error_msg: 错误消息（如果失败）
            **metadata: 额外的元数据
        """
        with self._lock:
            # 获取当前系统状态
            memory_info = self._get_memory_info()
            cpu_usage = self._get_cpu_usage() if self.level == MonitoringLevel.DETAILED else 0.0

            # 创建性能指标
            metric = PerformanceMetrics(
                timestamp=time.time(),
                operation_name=operation_name,
                duration_ms=duration_ms,
                memory_usage_mb=memory_info["used_mb"],
                cpu_usage_percent=cpu_usage,
                cache_hit=cache_hit,
                success=success,
                error_msg=error_msg,
                metadata=metadata
            )

            # 根据监控级别决定是否记录历史
            if self.level in [MonitoringLevel.STANDARD, MonitoringLevel.DETAILED]:
                self.performance_history.append(metric)

            # 更新统计信息
            self._update_stats(metric)

            # 检查慢操作
            if duration_ms > 1000 and self.level != MonitoringLevel.MINIMAL:
                logger.warning(
                    f"慢操作检测: {operation_name} 耗时 {duration_ms:.2f}ms"
                )

    def record_cache_hit(self):
        """记录缓存命中"""
        with self._lock:
            self.stats["cache_hits"] += 1
            self._update_cache_hit_rate()

    def record_cache_miss(self):
        """记录缓存未命中"""
        with self._lock:
            self.stats["cache_misses"] += 1
            self._update_cache_hit_rate()

    def get_memory_status(self) -> MemoryStatus:
        """获取内存状态

        Returns:
            MemoryStatus: 内存状态信息
        """
        try:
            memory_info = self._get_memory_info()
            used_mb = memory_info["used_mb"]
            available_mb = memory_info["available_mb"]
            total_mb = memory_info["total_mb"]
            percent = memory_info["percent"]

            # 确定压力级别和建议
            if percent > self.memory_thresholds["critical"]:
                pressure_level = "critical"
                recommendations = [
                    "立即清理缓存",
                    "关闭不必要功能",
                    "考虑重启应用"
                ]
            elif percent > self.memory_thresholds["warning"]:
                pressure_level = "high"
                recommendations = [
                    "清理预览缓存",
                    "减少预加载图像数量",
                    "关闭部分后台任务"
                ]
            elif percent > self.memory_thresholds["cleanup"]:
                pressure_level = "medium"
                recommendations = [
                    "渐进式缓存清理",
                    "考虑减少缓存大小"
                ]
            else:
                pressure_level = "low"
                recommendations = []

            return MemoryStatus(
                used_mb=used_mb,
                available_mb=available_mb,
                total_mb=total_mb,
                percent=percent,
                pressure_level=pressure_level,
                cache_usage_mb=self._estimate_cache_usage(),
                recommendations=recommendations
            )

        except Exception as e:
            logger.error(f"获取内存状态失败: {e}")
            return MemoryStatus(
                used_mb=0.0,
                available_mb=1024.0,
                total_mb=2048.0,
                percent=0.0,
                pressure_level="unknown",
                cache_usage_mb=0.0,
                recommendations=["监控数据不可用"]
            )

    def is_memory_pressure(self) -> bool:
        """检查是否存在内存压力"""
        memory_status = self.get_memory_status()
        return memory_status.pressure_level in ["high", "critical"]

    def get_stats(self) -> dict[str, Any]:
        """获取完整统计信息"""
        with self._lock:
            stats = self.stats.copy()

            # 添加运行时间
            stats["uptime_seconds"] = time.time() - stats["start_time"]

            # 添加内存状态
            stats["memory_status"] = self.get_memory_status().to_dict()

            # 添加操作统计（如果是详细模式）
            if self.level == MonitoringLevel.DETAILED:
                stats["operation_counts"] = self.operation_counts.copy()
                stats["top_operations"] = self._get_top_operations()

            # 添加性能建议
            stats["recommendations"] = self._get_performance_recommendations()

            return stats

    def get_performance_summary(self) -> dict[str, Any]:
        """获取性能摘要"""
        with self._lock:
            # 如果没有历史数据，使用统计数据
            if not self.performance_history:
                # 在 MINIMAL 级别或没有操作时，使用 stats 数据
                return {
                    "total_operations": self.stats["total_operations"],
                    "successful_operations": self.stats["successful_operations"],
                    "failed_operations": self.stats["failed_operations"],
                    "avg_duration_ms": self.stats["avg_duration_ms"],
                    "min_duration_ms": self.stats["min_duration_ms"] if self.stats["min_duration_ms"] != float("inf") else 0.0,
                    "max_duration_ms": self.stats["max_duration_ms"],
                    "avg_memory_mb": self.get_memory_usage(),
                    "cache_hit_rate": self.stats["cache_hit_rate"],
                    "error_rate": self.stats["error_rate"],
                    "uptime_seconds": time.time() - self.stats["start_time"],
                }

            # 使用历史数据计算最近的性能
            recent_count = min(100, len(self.performance_history))
            recent_metrics = list(self.performance_history)[-recent_count:]

            durations = [m.duration_ms for m in recent_metrics]
            memory_usage = [m.memory_usage_mb for m in recent_metrics]
            successful = sum(1 for m in recent_metrics if m.success)

            return {
                "total_operations": self.stats["total_operations"],
                "successful_operations": successful,
                "failed_operations": recent_count - successful,
                "avg_duration_ms": sum(durations) / len(durations),
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
                "avg_memory_mb": sum(memory_usage) / len(memory_usage),
                "cache_hit_rate": self.stats["cache_hit_rate"],
                "error_rate": self.stats["error_rate"],
                "uptime_seconds": time.time() - self.stats["start_time"],
            }

    def get_memory_usage(self) -> float:
        """获取当前内存使用量（MB）- 兼容方法"""
        return self.get_memory_status().used_mb

    def force_cleanup(self):
        """强制内存清理"""
        try:
            import gc
            gc.collect()
            with self._lock:
                self.stats["memory_cleanups"] += 1
            logger.info("执行强制内存清理")
        except Exception as e:
            logger.error(f"强制内存清理失败: {e}")

    def reset_stats(self):
        """重置统计数据"""
        with self._lock:
            self.stats.update({
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "total_duration_ms": 0.0,
                "avg_duration_ms": 0.0,
                "min_duration_ms": float("inf"),
                "max_duration_ms": 0.0,
                "cache_hits": 0,
                "cache_misses": 0,
                "cache_hit_rate": 0.0,
                "error_count": 0,
                "error_rate": 0.0,
                "start_time": time.time(),
            })
            self.operation_counts.clear()
            self.operation_durations.clear()
            self.performance_history.clear()
            self.memory_history.clear()
            logger.info("监控统计已重置")

    def get_dashboard_data(self) -> dict[str, Any]:
        """获取监控面板数据"""
        return {
            "performance": self.get_performance_summary(),
            "memory": self.get_memory_status().to_dict(),
            "system": {
                "monitoring": self.is_monitoring,
                "level": self.level.value,
                "uptime": time.time() - self.stats["start_time"],
                "has_psutil": HAS_PSUTIL
            },
            "statistics": self.stats.copy(),
            "recommendations": self._get_performance_recommendations()
        }

    # ==================== 私有方法 ====================

    def _update_stats(self, metric: PerformanceMetrics):
        """更新统计信息"""
        # 基本计数
        self.stats["total_operations"] += 1
        if metric.success:
            self.stats["successful_operations"] += 1
        else:
            self.stats["failed_operations"] += 1
            self.stats["error_count"] += 1

        # 时间统计
        self.stats["total_duration_ms"] += metric.duration_ms
        self.stats["avg_duration_ms"] = (
            self.stats["total_duration_ms"] / self.stats["total_operations"]
        )
        self.stats["min_duration_ms"] = min(
            self.stats["min_duration_ms"],
            metric.duration_ms
        )
        self.stats["max_duration_ms"] = max(
            self.stats["max_duration_ms"],
            metric.duration_ms
        )

        # 内存统计
        self.stats["peak_memory_mb"] = max(
            self.stats["peak_memory_mb"],
            metric.memory_usage_mb
        )

        # 缓存统计
        if metric.cache_hit is not None:
            if metric.cache_hit:
                self.stats["cache_hits"] += 1
            else:
                self.stats["cache_misses"] += 1
            self._update_cache_hit_rate()

        # 错误率
        self.stats["error_rate"] = (
            self.stats["error_count"] / self.stats["total_operations"]
        )

        # 操作类型统计（详细模式）
        if self.level == MonitoringLevel.DETAILED:
            self.operation_counts[metric.operation_name] = (
                self.operation_counts.get(metric.operation_name, 0) + 1
            )
            if metric.operation_name not in self.operation_durations:
                self.operation_durations[metric.operation_name] = []
            self.operation_durations[metric.operation_name].append(
                metric.duration_ms
            )

        self.stats["last_update"] = time.time()

    def _update_cache_hit_rate(self):
        """更新缓存命中率"""
        total = self.stats["cache_hits"] + self.stats["cache_misses"]
        if total > 0:
            self.stats["cache_hit_rate"] = self.stats["cache_hits"] / total
        else:
            self.stats["cache_hit_rate"] = 0.0

    def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            memory_status = self.get_memory_status()

            # 记录到历史
            self.memory_history.append({
                "timestamp": time.time(),
                "used_mb": memory_status.used_mb,
                "percent": memory_status.percent,
                "pressure_level": memory_status.pressure_level
            })

            # 检查内存压力
            if memory_status.pressure_level in ["high", "critical"]:
                logger.warning(
                    f"内存压力 {memory_status.pressure_level}: "
                    f"{memory_status.used_mb:.1f}MB / {memory_status.total_mb:.1f}MB "
                    f"({memory_status.percent:.1f}%)"
                )
                for rec in memory_status.recommendations:
                    logger.warning(f"  建议: {rec}")

        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")

    def _get_memory_info(self) -> dict[str, float]:
        """获取内存信息"""
        try:
            if HAS_PSUTIL:
                memory = psutil.virtual_memory()
                return {
                    "used_mb": (memory.total - memory.available) / (1024 ** 2),
                    "available_mb": memory.available / (1024 ** 2),
                    "total_mb": memory.total / (1024 ** 2),
                    "percent": memory.percent,
                }
            # 回退到估算
            return {
                "used_mb": 512.0,
                "available_mb": 1024.0,
                "total_mb": 2048.0,
                "percent": 25.0,
            }
        except Exception:
            return {
                "used_mb": 0.0,
                "available_mb": 1024.0,
                "total_mb": 2048.0,
                "percent": 0.0,
            }

    def _get_cpu_usage(self) -> float:
        """获取CPU使用率"""
        try:
            if HAS_PSUTIL:
                return psutil.cpu_percent(interval=None)
            return 0.0
        except Exception:
            return 0.0

    def _estimate_cache_usage(self) -> float:
        """估算缓存使用量"""
        try:
            # 集成实际的缓存监控

            # 尝试获取缓存管理器实例
            cache_manager = getattr(self, "_cache_manager", None)
            if cache_manager and hasattr(cache_manager, "get_cache_stats"):
                stats = cache_manager.get_cache_stats()
                if stats and "memory_usage_mb" in stats:
                    return float(stats["memory_usage_mb"])

            # 备用方案：估算缓存使用量
            # 基于当前监控的操作数量和平均大小估算
            if hasattr(self, "operation_stats") and self.operation_stats:
                # 假设每个操作平均占用1MB缓存
                active_operations = len([op for op in self.operation_stats.values()
                                       if op.get("last_access", 0) > 0])
                return float(active_operations * 1.0)  # MB

            # 默认估算值
            return 64.0

        except Exception as e:
            # 记录错误但不影响监控功能
            import logging
            logging.debug(f"缓存使用量估算失败: {e}")
            return 128.0

    def _get_top_operations(self, top_n: int = 5) -> list[dict[str, Any]]:
        """获取最频繁的操作"""
        sorted_ops = sorted(
            self.operation_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

        result = []
        for op_name, count in sorted_ops:
            durations = self.operation_durations.get(op_name, [])
            avg_duration = sum(durations) / len(durations) if durations else 0.0
            result.append({
                "operation": op_name,
                "count": count,
                "avg_duration_ms": avg_duration
            })

        return result

    def _get_performance_recommendations(self) -> list[str]:
        """获取性能优化建议"""
        recommendations = []

        # 检查平均响应时间
        if self.stats["avg_duration_ms"] > 1000:
            recommendations.append(
                f"平均响应时间较长 ({self.stats['avg_duration_ms']:.1f}ms)，"
                "建议优化加载流程"
            )

        # 检查缓存命中率
        if self.stats["cache_hit_rate"] < 0.7 and self.stats["total_operations"] > 10:
            recommendations.append(
                f"缓存命中率较低 ({self.stats['cache_hit_rate']:.1%})，"
                "建议调整缓存策略或增加缓存容量"
            )

        # 检查错误率
        if self.stats["error_rate"] > 0.05:
            recommendations.append(
                f"错误率较高 ({self.stats['error_rate']:.1%})，"
                "建议检查错误日志和异常处理"
            )

        # 检查内存
        memory_status = self.get_memory_status()
        if memory_status.pressure_level in ["high", "critical"]:
            recommendations.extend(memory_status.recommendations)

        return recommendations


# ==================== 全局单例 ====================

_unified_monitor_instance: UnifiedMonitorV2 | None = None
_monitor_lock = threading.Lock()


def get_unified_monitor(
    level: MonitoringLevel = MonitoringLevel.STANDARD,
    **kwargs
) -> UnifiedMonitorV2:
    """获取全局统一监控器实例

    Args:
        level: 监控级别
        **kwargs: 传递给 UnifiedMonitorV2 的其他参数

    Returns:
        UnifiedMonitorV2: 全局监控器实例
    """
    global _unified_monitor_instance

    with _monitor_lock:
        if _unified_monitor_instance is None:
            _unified_monitor_instance = UnifiedMonitorV2(level=level, **kwargs)
        return _unified_monitor_instance


def reset_unified_monitor():
    """重置全局监控器实例（主要用于测试）"""
    global _unified_monitor_instance

    with _monitor_lock:
        if _unified_monitor_instance is not None:
            _unified_monitor_instance.stop_monitoring()
        _unified_monitor_instance = None


# ==================== 装饰器 ====================

def monitor_performance(operation_name: str):
    """性能监控装饰器

    Args:
        operation_name: 操作名称

    使用示例:
        @monitor_performance("load_image")
        def load_image(path):
            # ... 加载逻辑
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_msg = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                get_unified_monitor().record_operation(
                    operation_name=operation_name,
                    duration_ms=duration_ms,
                    success=success,
                    error_msg=error_msg
                )

        return wrapper
    return decorator
