"""
监控模块 - 统一接口

提供简洁、高效的监控API。

核心功能：
- 性能指标收集
- 内存状态监控
- 统计数据输出
- 遥测功能

使用示例:
    from plookingII.monitor import get_unified_monitor

    monitor = get_unified_monitor()
    monitor.record_operation('load_image', duration_ms=125.5)

    # 或使用装饰器
    @monitor_performance('my_operation')
    def my_function():
        ...

Author: PlookingII Team
Date: 2025-10-06 (简化整合)
"""

from .telemetry import is_telemetry_enabled, record_event
from .unified_monitor import (
    MemoryStatus,
    MonitoringLevel,
    PerformanceMetrics,
    UnifiedMonitor,
    get_unified_monitor,
    monitor_performance,
    reset_unified_monitor,
)

__all__ = [
    # 核心类
    "UnifiedMonitor",
    "PerformanceMetrics",
    "MemoryStatus",
    "MonitoringLevel",
    # 工厂函数
    "get_unified_monitor",
    "reset_unified_monitor",
    # 装饰器
    "monitor_performance",
    # 遥测
    "record_event",
    "is_telemetry_enabled",
    # 便捷函数
    "record_operation",
    "get_memory_status",
    "get_stats",
    "get_recent_operations",
]

# === 便捷函数（向后兼容）===


def record_operation(operation_name: str, duration_ms: float, success: bool = True, **kwargs) -> None:
    """记录操作（便捷函数）

    Args:
        operation_name: 操作名称
        duration_ms: 持续时间（毫秒）
        success: 是否成功
        **kwargs: 额外参数
    """
    monitor = get_unified_monitor()
    monitor.record_operation(operation_name, duration_ms, success=success, **kwargs)


def get_memory_status() -> MemoryStatus:
    """获取内存状态（便捷函数）"""
    monitor = get_unified_monitor()
    return monitor.get_memory_status()


def get_stats() -> dict:
    """获取统计信息（便捷函数）"""
    monitor = get_unified_monitor()
    return monitor.get_stats()


def get_recent_operations(count: int = 10) -> list[PerformanceMetrics]:
    """获取最近操作（便捷函数）"""
    monitor = get_unified_monitor()
    return monitor.get_recent_operations(count)


# === 兼容性别名（向后兼容旧代码）===

# 兼容旧的函数名
get_performance_monitor = get_unified_monitor
get_memory_monitor = get_unified_monitor


def get_simple_stats() -> dict:
    """获取简单统计（兼容接口）"""
    return get_stats()


def record_load_time(duration_ms: float, cache_hit: bool = False) -> None:
    """记录加载时间（兼容接口）"""
    record_operation("load", duration_ms, cache_hit=cache_hit)


def record_memory(memory_mb: float) -> None:
    """记录内存使用（兼容接口）"""
    # 现代API中，内存通过 get_memory_status() 自动获取


def get_current_memory_mb() -> float:
    """获取当前内存使用（兼容接口）"""
    status = get_memory_status()
    return status.used_mb


def check_memory_pressure() -> str:
    """检查内存压力（兼容接口）"""
    status = get_memory_status()
    return status.pressure_level


def should_cleanup_memory() -> bool:
    """是否应该清理内存（兼容接口）"""
    status = get_memory_status()
    return status.pressure_level in ("high", "critical")


def get_health_status() -> dict:
    """获取健康状态（兼容接口）"""
    stats = get_stats()
    memory = get_memory_status()

    return {
        "healthy": memory.pressure_level not in ("critical",),
        "memory_pressure": memory.pressure_level,
        "total_operations": stats.get("total_operations", 0),
        "success_rate": stats.get("success_rate", 0.0),
    }


def is_system_healthy() -> bool:
    """系统是否健康（兼容接口）"""
    health = get_health_status()
    return health["healthy"]


def get_memory_display_info() -> dict:
    """获取内存显示信息（兼容接口）"""
    status = get_memory_status()
    return {
        "used_mb": status.used_mb,
        "available_mb": status.available_mb,
        "percent": status.percent,
        "pressure": status.pressure_level,
        "recommendations": status.recommendations,
    }
