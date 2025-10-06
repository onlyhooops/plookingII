# Phase 3: 监控系统整合 + 废弃代码清理

## 📊 当前状况分析

### 监控系统 (1,718 行)

```
plookingII/monitor/
├── __init__.py                      (230行) - 过多包装函数
├── telemetry.py                     (62行)  - 遥测功能
├── unified_monitor.py               (366行) - V1 版本 ⚠️ 重复
└── unified/
    ├── __init__.py                  (56行)
    ├── unified_monitor_v2.py        (733行) - V2 版本 ⚠️ 重复
    └── monitor_adapter.py           (271行) - 适配器层
```

**重复问题**：
- `unified_monitor.py` 和 `unified_monitor_v2.py` **功能重复**
- 相同的类：`PerformanceMetrics`, `MemoryStatus`, `UnifiedMonitor`
- 相同的函数：`get_unified_monitor()`, `monitor_performance()`

### 废弃代码（旧缓存系统）

```
plookingII/core/cache/                (已被 simple_cache.py 替代)
├── __init__.py                      (1.6K)
├── adapters.py                      (9.0K)  ✗ 废弃
├── cache_adapter.py                 (8.4K)  ✗ 废弃
├── cache_monitor.py                 (5.5K)  ✗ 废弃
├── cache_policy.py                  (6.6K)  ✗ 废弃
├── config.py                        (4.3K)  ✗ 废弃
└── unified_cache.py                 (14K)   ✗ 废弃
```

**清理目标**：移除整个 `core/cache/` 目录（约48KB）

## 🎯 整合策略

### 方案：简化统一监控

**保留**：
- `unified_monitor_v2.py` 作为核心（最完善）
- `telemetry.py`（独立功能）

**移除**：
- `unified_monitor.py`（V1，重复）
- `monitor_adapter.py`（过度抽象）
- 简化 `__init__.py`（移除冗余包装）

**新结构**：
```
plookingII/monitor/
├── __init__.py              (~80行)  - 简洁接口
├── telemetry.py             (62行)   - 遥测功能
└── unified_monitor.py       (~400行) - 整合后的监控器
```

## 📐 详细设计

### 1. 简化的监控器 (`unified_monitor.py`)

基于 V2，但简化：
- 移除过度复杂的配置
- 保留核心监控功能
- 简化内存压力检测
- 优化性能开销

```python
"""
统一监控器 - 简化版

提供轻量、高效的监控功能。

核心功能：
- 性能指标收集
- 内存状态监控
- 自动压力检测
- 统计数据输出
"""

from dataclasses import dataclass
from typing import Any
import threading
import time

@dataclass
class Metrics:
    """统一的指标数据"""
    timestamp: float
    operation: str
    duration_ms: float
    memory_mb: float = 0.0
    success: bool = True
    metadata: dict = None

class Monitor:
    """简化的统一监控器"""
    
    def __init__(self, max_history: int = 500):
        self.max_history = max_history
        self.metrics_history = []
        self.stats = {
            'total_ops': 0,
            'avg_time': 0.0,
            'memory_cleanups': 0,
        }
        self._lock = threading.RLock()
    
    def record(self, operation: str, duration_ms: float, 
               memory_mb: float = 0.0, success: bool = True):
        """记录指标"""
        with self._lock:
            metric = Metrics(
                timestamp=time.time(),
                operation=operation,
                duration_ms=duration_ms,
                memory_mb=memory_mb,
                success=success
            )
            self.metrics_history.append(metric)
            if len(self.metrics_history) > self.max_history:
                self.metrics_history.pop(0)
            
            # 更新统计
            self.stats['total_ops'] += 1
    
    def get_memory_status(self) -> dict:
        """获取内存状态"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                'used_mb': mem.used / 1024 / 1024,
                'available_mb': mem.available / 1024 / 1024,
                'percent': mem.percent,
                'pressure': self._get_pressure_level(mem.percent)
            }
        except ImportError:
            return {'pressure': 'unknown'}
    
    def _get_pressure_level(self, percent: float) -> str:
        """获取压力级别"""
        if percent < 70:
            return 'low'
        elif percent < 85:
            return 'medium'
        elif percent < 95:
            return 'high'
        else:
            return 'critical'
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            return dict(self.stats)

# 全局实例
_monitor = None
_lock = threading.Lock()

def get_monitor() -> Monitor:
    """获取全局监控器实例"""
    global _monitor
    with _lock:
        if _monitor is None:
            _monitor = Monitor()
        return _monitor
```

### 2. 简化的 `__init__.py`

```python
"""
监控模块 - 统一接口

提供简洁的监控API。

使用示例:
    from plookingII.monitor import get_monitor
    
    monitor = get_monitor()
    monitor.record('load_image', duration_ms=125.5)
"""

from .unified_monitor import Monitor, get_monitor, Metrics
from .telemetry import record_event, is_telemetry_enabled

__all__ = [
    'Monitor',
    'get_monitor',
    'Metrics',
    'record_event',
    'is_telemetry_enabled',
]

# 向后兼容的便捷函数
def record_operation(name: str, duration_ms: float, **kwargs):
    """记录操作（兼容接口）"""
    monitor = get_monitor()
    monitor.record(name, duration_ms, **kwargs)

def get_memory_status() -> dict:
    """获取内存状态（兼容接口）"""
    monitor = get_monitor()
    return monitor.get_memory_status()

def get_stats() -> dict:
    """获取统计信息（兼容接口）"""
    monitor = get_monitor()
    return monitor.get_stats()
```

## 📊 预期成果

### 代码量对比

| 文件 | 旧版本 | 新版本 | 改善 |
|------|--------|--------|------|
| **监控系统** | | | |
| __init__.py | 230 行 | ~80 行 | ↓150 行 |
| unified_monitor.py | 366 行 | ~400 行 | 整合V1+V2 |
| unified_monitor_v2.py | 733 行 | ✗ 移除 | -733 行 |
| monitor_adapter.py | 271 行 | ✗ 移除 | -271 行 |
| unified/__init__.py | 56 行 | ✗ 移除 | -56 行 |
| telemetry.py | 62 行 | 62 行 | 保持 |
| **小计** | **1,718 行** | **~542 行** | **↓68.5%** |

### 废弃代码清理

| 目录/文件 | 大小 | 状态 |
|-----------|------|------|
| core/cache/__init__.py | 1.6K | ✗ 移除 |
| core/cache/adapters.py | 9.0K | ✗ 移除 |
| core/cache/cache_adapter.py | 8.4K | ✗ 移除 |
| core/cache/cache_monitor.py | 5.5K | ✗ 移除 |
| core/cache/cache_policy.py | 6.6K | ✗ 移除 |
| core/cache/config.py | 4.3K | ✗ 移除 |
| core/cache/unified_cache.py | 14K | ✗ 移除 |
| **总计** | **~48K** | **完全移除** |

### 总改善

| 指标 | 改善 |
|------|------|
| 监控代码减少 | 1,176 行 (68.5%) |
| 废弃代码清理 | ~48K (7个文件) |
| 总减少 | 1,176+ 行 |
| 文件减少 | 11 个 |

## 🚀 实施计划

### Step 1: 创建简化的监控器 (1-2小时)

1. 基于 `unified_monitor_v2.py` 创建简化版
2. 移除过度复杂的功能
3. 保留核心监控能力

### Step 2: 简化公共接口 (30分钟)

1. 简化 `__init__.py`
2. 移除冗余包装函数
3. 提供向后兼容接口

### Step 3: 清理废弃代码 (15分钟)

1. 移除 `core/cache/` 目录
2. 检查是否有导入依赖
3. 更新相关导入

### Step 4: 移除重复文件 (15分钟)

1. 删除 `unified_monitor.py` (V1)
2. 删除 `monitor_adapter.py`
3. 删除 `unified/` 目录

### Step 5: 测试验证 (30分钟)

1. 运行现有测试
2. 验证监控功能
3. 检查向后兼容性

## ⚠️ 风险控制

### 1. 向后兼容性

**风险**: 破坏现有监控代码

**缓解**:
- 保留关键API
- 提供兼容函数
- 渐进式废弃

### 2. 功能丢失

**风险**: 移除仍在使用的功能

**缓解**:
- 检查所有导入
- 保留核心功能
- 文档记录变更

### 3. 依赖问题

**风险**: 旧缓存代码可能被引用

**缓解**:
- 全局搜索导入
- 确认无引用后删除
- 保留兼容说明

## 📝 检查清单

### 清理前检查

- [ ] 搜索 `from plookingII.core.cache` 导入
- [ ] 搜索 `import plookingII.core.cache` 导入
- [ ] 确认 simple_cache.py 完全替代
- [ ] 搜索 `unified_monitor.py` 导入
- [ ] 搜索 `monitor_adapter` 导入

### 清理后验证

- [ ] 运行所有单元测试
- [ ] 验证监控功能正常
- [ ] 检查导入路径
- [ ] 验证向后兼容性
- [ ] 更新文档

## 🎯 成功标准

1. ✅ 监控代码减少 65%+
2. ✅ 废弃代码完全移除
3. ✅ 所有测试通过
4. ✅ 向后兼容保持
5. ✅ 性能不退化

---

**创建日期**: 2025-10-06  
**负责人**: PlookingII Team  
**状态**: 规划中

**预期时间**: 3-4 小时  
**预期收益**: 代码减少68.5%，清理废弃代码48K

