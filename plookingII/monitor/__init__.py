"""
性能监控模块

提供PlookingII应用程序的性能监控功能，包括内存监控、性能统计和系统健康检查。

v2.0.0 统一监控系统（推荐）：
- 引入 UnifiedMonitorV2 - 可配置监控级别
- 整合所有监控功能到单一接口
- 提供性能监控装饰器
- 完全向后兼容旧监控系统

主要组件：
    - UnifiedMonitorV2: 统一监控器 V2（推荐）
    - MonitoringLevel: 监控级别枚举（minimal/standard/detailed）
    - 适配器：向后兼容旧监控系统

使用示例：
    from plookingII.monitor import get_unified_monitor, MonitoringLevel

    # 获取监控器实例（默认 standard 级别）
    monitor = get_unified_monitor(level=MonitoringLevel.STANDARD)

    # 记录操作
    monitor.record_operation("load_image", duration_ms=150, cache_hit=True)

    # 获取统计
    stats = monitor.get_stats()
    memory = monitor.get_memory_status()

Author: PlookingII Team
Version: 2.0.0
"""

# 统一监控器 V2（推荐使用）
try:
    from .unified import (
        LightweightPerformanceMonitorAdapter,
        MemoryStatus,
        PerformanceMetrics,
        SimplifiedMemoryMonitorAdapter,
        get_unified_monitor,
        monitor_performance,
    )
    _UNIFIED_V2_AVAILABLE = True
except ImportError:
    # 回退到旧版本
    _UNIFIED_V2_AVAILABLE = False
    from .unified_monitor import (
        MemoryStatus,
        PerformanceMetrics,
        get_unified_monitor,
        monitor_performance,
    )

# 旧监控模块已迁移到统一监控器
# lightweight_performance.py 和 simplified_performance.py 已清理
# 所有功能现在通过适配器提供，自动路由到 UnifiedMonitorV2

# 向后兼容的全局函数
def get_health_status():
    """获取系统健康状态 - 兼容函数"""
    monitor = get_unified_monitor()
    stats = monitor.get_stats()
    memory = monitor.get_memory_status()
    return {
        "is_healthy": memory.pressure_level not in ["high", "critical"],
        "memory_pressure": memory.pressure_level,
        "cache_hit_rate": stats.cache_hit_rate,
    }

def get_performance_monitor():
    """获取性能监控器 - 兼容函数"""
    return get_unified_monitor()

def get_simple_stats():
    """获取简单统计 - 兼容函数"""
    monitor = get_unified_monitor()
    return monitor.get_stats()

def is_system_healthy():
    """系统是否健康 - 兼容函数"""
    status = get_health_status()
    return status["is_healthy"]

def record_load_time(duration_ms, cache_hit=False):
    """记录加载时间 - 兼容函数"""
    monitor = get_unified_monitor()
    monitor.record_operation("load", duration_ms=duration_ms, cache_hit=cache_hit)

def record_memory(memory_mb):
    """记录内存使用 - 兼容函数"""
    # 统一监控器自动跟踪内存，此函数保留用于兼容性

# 向后兼容的函数别名
def get_current_memory_mb():
    """获取当前内存使用量（MB）- 兼容函数"""
    monitor = get_unified_monitor()
    return monitor.get_memory_usage()

def check_memory_pressure():
    """检查内存压力 - 兼容函数"""
    monitor = get_unified_monitor()
    return monitor.is_memory_pressure()

def should_cleanup_memory():
    """是否应该清理内存 - 兼容函数"""
    return check_memory_pressure()

def get_memory_display_info():
    """获取内存显示信息 - 兼容函数"""
    monitor = get_unified_monitor()
    memory_mb = monitor.get_memory_usage()
    return f"内存: {memory_mb:.1f}MB"

def get_memory_monitor():
    """获取内存监控器 - 兼容函数"""
    return get_unified_monitor()

class MemoryUtils:
    """内存工具类 - 兼容类"""
    @staticmethod
    def get_current_memory_mb():
        return get_current_memory_mb()

    @staticmethod
    def check_memory_pressure():
        return check_memory_pressure()

class SimplifiedMemoryMonitor:
    """简化内存监控器 - 兼容类"""
    def __init__(self):
        self._monitor = get_unified_monitor()

    def get_memory_usage(self):
        memory_status = self._monitor.get_memory_status()
        return memory_status.used_mb

    def is_memory_pressure(self):
        return self._monitor.is_memory_pressure()

    def get_memory_info(self):
        """获取内存信息 - 兼容方法"""
        memory_status = self._monitor.get_memory_status()

        return {
            "used_mb": memory_status.used_mb,
            "available_mb": memory_status.available_mb,
            "pressure": memory_status.pressure_level in ["high", "critical"],
            "recommendations": memory_status.recommendations
        }

    def is_preload_memory_high(self):
        """检查预加载内存是否过高 - 兼容方法"""
        memory_status = self._monitor.get_memory_status()
        # 如果可用内存少于512MB，认为预加载内存过高
        return memory_status.available_mb < 512

    def is_main_memory_high(self):
        """检查主内存是否过高 - 兼容方法"""
        memory_status = self._monitor.get_memory_status()
        return memory_status.pressure_level in ["high", "critical"]

    def is_memory_high(self):
        """检查内存是否过高 - 兼容方法"""
        memory_status = self._monitor.get_memory_status()
        return memory_status.pressure_level in ["high", "critical"]

    def force_garbage_collection(self):
        """强制垃圾回收 - 兼容方法"""
        import gc
        gc.collect()

    def update_preload_memory_usage(self, usage_mb):
        """更新预加载内存使用量 - 兼容方法"""
        # 在简化版本中，我们只是记录这个值，不做特殊处理
        self._preload_memory_usage = getattr(self, "_preload_memory_usage", 0.0)
        self._preload_memory_usage = usage_mb

# 向后兼容的别名
if _UNIFIED_V2_AVAILABLE:
    # 使用适配器提供向后兼容
    ImagePerformanceMonitor = LightweightPerformanceMonitorAdapter
    PerformanceMonitor = LightweightPerformanceMonitorAdapter
    MemoryMonitor = SimplifiedMemoryMonitorAdapter
else:
    # 回退到旧实现
    ImagePerformanceMonitor = LightweightPerformanceMonitor
    PerformanceMonitor = LightweightPerformanceMonitor
    MemoryMonitor = SimplifiedMemoryMonitor

__all__ = [
    # 统一监控器 V2（推荐）
    "get_unified_monitor",
    "monitor_performance",
    "PerformanceMetrics",
    "MemoryStatus",

    # 兼容类（已通过适配器实现）
    "SimplifiedMemoryMonitor",
    "MemoryUtils",

    # 全局函数
    "get_performance_monitor",
    "get_memory_monitor",
    "record_load_time",
    "record_memory",
    "get_health_status",
    "get_simple_stats",
    "is_system_healthy",
    "get_current_memory_mb",
    "check_memory_pressure",
    "should_cleanup_memory",
    "get_memory_display_info",

    # 向后兼容别名
    "ImagePerformanceMonitor",
    "PerformanceMonitor",
    "MemoryMonitor",
]

# 动态添加新监控器到 __all__
if _UNIFIED_V2_AVAILABLE:
    __all__.extend([
        "LightweightMonitorAdapter",
        "LightweightPerformanceMonitorAdapter",
        "MonitoringLevel",
        "SimplifiedMemoryMonitorAdapter",
        "UnifiedMonitorV2",
    ])
else:
    __all__.append("UnifiedMonitor")
