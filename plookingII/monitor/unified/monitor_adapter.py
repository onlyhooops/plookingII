"""
监控系统适配器

为旧的监控系统提供向后兼容的适配器接口。

适配以下旧系统：
- LightweightPerformanceMonitor
- SimplifiedMemoryMonitor
- LightweightMonitor
"""

from typing import Any

from .unified_monitor_v2 import MonitoringLevel, get_unified_monitor


class LightweightPerformanceMonitorAdapter:
    """LightweightPerformanceMonitor 适配器

    适配 plookingII/monitor/lightweight_performance.py::LightweightPerformanceMonitor
    """

    def __init__(self, history_size: int = 100):
        """初始化适配器

        Args:
            history_size: 历史记录大小（传递给底层监控器）
        """
        self._monitor = get_unified_monitor(
            level=MonitoringLevel.STANDARD,
            max_history=history_size
        )
        self.history_size = history_size

    def record_load_operation(
        self,
        load_time: float,
        cache_hit: bool = False,
        error: bool = False
    ):
        """记录加载操作

        Args:
            load_time: 加载时间（秒）
            cache_hit: 是否缓存命中
            error: 是否发生错误
        """
        self._monitor.record_operation(
            operation_name="load_operation",
            duration_ms=load_time * 1000,  # 转换为毫秒
            cache_hit=cache_hit,
            success=not error,
            error_msg="Operation failed" if error else None
        )

    def record_memory_usage(self, memory_mb: float):
        """记录内存使用

        Args:
            memory_mb: 内存使用量（MB）
        """
        # UnifiedMonitorV2 自动收集内存，这里只是兼容接口

    def get_performance_summary(self) -> dict[str, Any]:
        """获取性能摘要"""
        summary = self._monitor.get_performance_summary()
        stats = self._monitor.get_stats()

        # 转换为旧格式
        return {
            "summary": {
                "runtime_minutes": stats["uptime_seconds"] / 60,
                "total_operations": summary["total_operations"],
                "avg_load_time_ms": summary["avg_duration_ms"],
                "cache_hit_rate": summary["cache_hit_rate"],
                "error_rate": summary["error_rate"],
                "current_memory_mb": self._monitor.get_memory_usage()
            },
            "detailed": {
                "cache_hits": stats["cache_hits"],
                "cache_misses": stats["cache_misses"],
                "errors": stats["error_count"],
                "last_load_time_ms": summary.get("max_duration_ms", 0.0),
                "total_load_time": stats["total_duration_ms"] / 1000,  # 转换为秒
                "last_update": stats["last_update"]
            }
        }

    def get_health_status(self) -> str:
        """获取系统健康状态

        Returns:
            健康状态: 'good', 'warning', 'critical'
        """
        summary = self._monitor.get_performance_summary()

        # 检查错误率
        if summary["error_rate"] > 0.1:
            return "critical"

        # 检查平均加载时间
        if summary["avg_duration_ms"] > 2000:
            return "warning"

        # 检查缓存命中率
        if summary["cache_hit_rate"] < 0.5 and summary["total_operations"] > 10:
            return "warning"

        # 检查内存使用
        if self._monitor.is_memory_pressure():
            return "warning"

        return "good"

    def get_optimization_suggestions(self) -> list[str]:
        """获取优化建议"""
        return self._monitor._get_performance_recommendations()

    def reset_statistics(self):
        """重置统计信息"""
        self._monitor.reset_stats()

    def get_simple_stats(self) -> dict[str, Any]:
        """获取简化的统计信息"""
        summary = self._monitor.get_performance_summary()

        return {
            "operations": summary["total_operations"],
            "avg_time_ms": round(summary["avg_duration_ms"], 1),
            "cache_hit_rate": round(summary["cache_hit_rate"], 2),
            "memory_mb": round(self._monitor.get_memory_usage(), 1),
            "health": self.get_health_status(),
            "runtime_min": round(summary["uptime_seconds"] / 60, 1)
        }

    def is_performing_well(self) -> bool:
        """检查系统是否运行良好"""
        return self.get_health_status() == "good"


class SimplifiedMemoryMonitorAdapter:
    """SimplifiedMemoryMonitor 适配器

    适配 plookingII/monitor/__init__.py::SimplifiedMemoryMonitor
    """

    def __init__(self):
        """初始化适配器"""
        self._monitor = get_unified_monitor()
        self._preload_memory_usage = 0.0

    def get_memory_usage(self) -> float:
        """获取内存使用量（MB）"""
        return self._monitor.get_memory_usage()

    def is_memory_pressure(self) -> bool:
        """检查是否存在内存压力"""
        return self._monitor.is_memory_pressure()

    def get_memory_info(self) -> dict[str, Any]:
        """获取内存信息"""
        memory_status = self._monitor.get_memory_status()

        return {
            "used_mb": memory_status.used_mb,
            "available_mb": memory_status.available_mb,
            "pressure": memory_status.pressure_level in ["high", "critical"],
            "recommendations": memory_status.recommendations
        }

    def is_preload_memory_high(self) -> bool:
        """检查预加载内存是否过高"""
        memory_status = self._monitor.get_memory_status()
        return memory_status.available_mb < 512

    def is_main_memory_high(self) -> bool:
        """检查主内存是否过高"""
        memory_status = self._monitor.get_memory_status()
        return memory_status.pressure_level in ["high", "critical"]

    def is_memory_high(self) -> bool:
        """检查内存是否过高"""
        memory_status = self._monitor.get_memory_status()
        return memory_status.pressure_level in ["high", "critical"]

    def force_garbage_collection(self):
        """强制垃圾回收"""
        self._monitor.force_cleanup()

    def update_preload_memory_usage(self, usage_mb: float):
        """更新预加载内存使用量

        Args:
            usage_mb: 预加载内存使用量（MB）
        """
        self._preload_memory_usage = usage_mb


class LightweightMonitorAdapter:
    """LightweightMonitor 适配器

    适配 plookingII/core/lightweight_monitor.py::LightweightMonitor
    """

    def __init__(self):
        """初始化适配器"""
        self._monitor = get_unified_monitor(level=MonitoringLevel.MINIMAL)

    def record_load(self, load_time: float, cache_hit: bool = False):
        """记录加载操作

        Args:
            load_time: 加载时间（秒）
            cache_hit: 是否缓存命中
        """
        self._monitor.record_operation(
            operation_name="load",
            duration_ms=load_time * 1000,
            cache_hit=cache_hit
        )

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        summary = self._monitor.get_performance_summary()

        # 处理无数据情况
        if summary.get("status") == "no_data":
            return {
                "total_loads": 0,
                "avg_load_time": 0.0,
                "cache_hit_rate": 0.0,
                "memory_mb": self._monitor.get_memory_usage()
            }

        return {
            "total_loads": summary["total_operations"],
            "avg_load_time": summary["avg_duration_ms"] / 1000,  # 转换为秒
            "cache_hit_rate": summary["cache_hit_rate"],
            "memory_mb": self._monitor.get_memory_usage()
        }

    def reset(self):
        """重置统计"""
        self._monitor.reset_stats()


# ==================== 工厂函数 ====================

def create_monitor_adapter(monitor_type: str, **kwargs):
    """创建监控适配器的工厂函数

    Args:
        monitor_type: 监控器类型
            - "lightweight_performance"
            - "simplified_memory"
            - "lightweight"
        **kwargs: 传递给适配器的参数

    Returns:
        相应的适配器实例
    """
    adapters = {
        "lightweight_performance": LightweightPerformanceMonitorAdapter,
        "simplified_memory": SimplifiedMemoryMonitorAdapter,
        "lightweight": LightweightMonitorAdapter,
    }

    adapter_class = adapters.get(monitor_type)
    if adapter_class is None:
        raise ValueError(
            f"Unknown monitor type: {monitor_type}. "
            f"Available types: {list(adapters.keys())}"
        )

    return adapter_class(**kwargs)
