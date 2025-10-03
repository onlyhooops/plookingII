"""
PlookingII 统一监控系统 v2.0

整合所有监控功能为单一、可配置的监控架构。

主要特性：
- 📊 统一的性能指标收集
- 💾 内存监控和压力检测
- 📈 实时监控和历史数据
- 🔌 可插拔的监控级别（minimal/standard/detailed）
- 🔄 向后兼容旧监控系统

替代以下旧系统：
- monitor/lightweight_performance.py (LightweightPerformanceMonitor)
- monitor/simplified_performance.py (SimplifiedPerformanceMonitor)
- core/lightweight_monitor.py (LightweightMonitor)
- 部分 core/smart_memory_manager.py (MemoryMonitor)

使用示例：
    from plookingII.monitor.unified import get_unified_monitor

    monitor = get_unified_monitor(level="standard")
    monitor.record_operation("image_load", duration_ms=150)
    stats = monitor.get_stats()

Author: PlookingII Team
Version: 2.0.0
"""

from .monitor_adapter import (
    LightweightMonitorAdapter,
    LightweightPerformanceMonitorAdapter,
    SimplifiedMemoryMonitorAdapter,
)
from .unified_monitor_v2 import (
    MemoryStatus,
    MonitoringLevel,
    PerformanceMetrics,
    UnifiedMonitorV2,
    get_unified_monitor,
    monitor_performance,
)

__all__ = [
    # 核心监控器
    "UnifiedMonitorV2",
    "MonitoringLevel",
    "PerformanceMetrics",
    "MemoryStatus",
    "get_unified_monitor",
    "monitor_performance",

    # 兼容适配器
    "LightweightPerformanceMonitorAdapter",
    "SimplifiedMemoryMonitorAdapter",
    "LightweightMonitorAdapter",
]
