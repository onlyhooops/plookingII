# Phase 2: 图片加载策略简化方案

## 📊 当前状况分析

### 文件信息
- **文件**: `plookingII/core/optimized_loading_strategies.py`
- **行数**: 1,118 行 ⚠️
- **类数**: 4 个 (OptimizedLoadingStrategy, PreviewLoadingStrategy, AutoLoadingStrategy, OptimizedLoadingStrategyFactory)
- **复杂度**: 高

### 问题识别

1. **单文件过大** (1,118行)
   - 难以维护和理解
   - 多个职责混在一起
   - 测试困难

2. **过度配置**
   - 大量 `get_config()` 调用
   - 配置项分散
   - 热路径有配置读取开销

3. **重复代码**
   - 错误处理重复
   - Quartz 相关代码重复
   - 统计代码重复

4. **工厂模式可能多余**
   - `OptimizedLoadingStrategyFactory` 可能不需要
   - 简单场景不需要工厂

## 🎯 简化策略

### 方案A: 模块化拆分（推荐）⭐

将大文件拆分为逻辑清晰的模块：

```
plookingII/core/loading/
├── __init__.py           (公共接口导出)
├── strategies.py         (核心策略类 ~350行)
├── helpers.py            (辅助函数 ~250行)
├── config.py             (配置管理 ~150行)
└── stats.py              (统计管理 ~100行)
```

**优点**:
- 职责分离清晰
- 易于测试
- 便于并行开发
- 代码复用

**缺点**:
- 需要修改导入路径
- 初期工作量稍大

### 方案B: 保持单文件，内部重构（备选）

保持在单文件中，但简化逻辑：
- 移除过度配置
- 简化统计
- 合并重复代码

**优点**:
- 改动小
- 无需修改导入

**缺点**:
- 文件仍然较大
- 维护性改善有限

## 📐 详细设计 (方案A)

### 1. `loading/__init__.py` (导出接口)

```python
"""
图片加载策略模块

简化的加载策略：
- OptimizedStrategy: 智能加载（自动选择最优方法）
- PreviewStrategy: 快速预览/缩略图
- AutoStrategy: 自动策略选择器

使用示例:
    from plookingII.core.loading import get_loader
    
    loader = get_loader()  # 自动选择
    image = loader.load('image.jpg', target_size=(800, 600))
"""

from .strategies import (
    OptimizedStrategy,
    PreviewStrategy,
    AutoStrategy,
)
from .helpers import get_loader, create_loader

__all__ = [
    'OptimizedStrategy',
    'PreviewStrategy',
    'AutoStrategy',
    'get_loader',
    'create_loader',
]

__version__ = '2.0.0'  # 简化版本
```

### 2. `loading/strategies.py` (核心策略)

```python
"""核心加载策略实现"""

import logging
from typing import Any, Optional
from .helpers import (
    load_with_quartz,
    load_with_nsimage,
    load_with_memory_map,
    get_file_size_mb,
)
from .config import LoadingConfig
from .stats import LoadingStats

logger = logging.getLogger(__name__)


class OptimizedStrategy:
    """智能优化加载策略
    
    根据文件大小自动选择最优加载方法：
    - 小文件(<10MB): NSImage直接加载
    - 中等文件(10-100MB): Quartz优化加载
    - 大文件(>100MB): 内存映射加载
    """
    
    def __init__(self, config: LoadingConfig = None):
        self.config = config or LoadingConfig()
        self.stats = LoadingStats()
        
    def load(self, file_path: str, target_size: tuple[int, int] = None) -> Optional[Any]:
        """加载图片"""
        size_mb = get_file_size_mb(file_path)
        
        # 根据大小选择策略
        if size_mb < self.config.quartz_threshold:
            return self._load_small(file_path, target_size)
        elif size_mb < self.config.memory_map_threshold:
            return self._load_medium(file_path, target_size)
        else:
            return self._load_large(file_path, target_size)
    
    def _load_small(self, file_path: str, target_size) -> Optional[Any]:
        """小文件：NSImage快速加载"""
        return load_with_nsimage(file_path)
    
    def _load_medium(self, file_path: str, target_size) -> Optional[Any]:
        """中等文件：Quartz优化加载"""
        return load_with_quartz(file_path, target_size)
    
    def _load_large(self, file_path: str, target_size) -> Optional[Any]:
        """大文件：内存映射加载"""
        return load_with_memory_map(file_path, target_size)


class PreviewStrategy:
    """预览/缩略图加载策略"""
    
    def __init__(self, max_size: int = 512):
        self.max_size = max_size
        self.stats = LoadingStats()
    
    def load(self, file_path: str, target_size: tuple[int, int] = None) -> Optional[Any]:
        """加载预览图"""
        size = target_size or (self.max_size, self.max_size)
        return load_with_quartz(file_path, size, thumbnail=True)


class AutoStrategy:
    """自动策略选择器
    
    根据场景自动选择最优策略
    """
    
    def __init__(self):
        self.optimized = OptimizedStrategy()
        self.preview = PreviewStrategy()
    
    def load(self, file_path: str, target_size: tuple[int, int] = None, 
             preview: bool = False) -> Optional[Any]:
        """自动选择并加载"""
        if preview:
            return self.preview.load(file_path, target_size)
        else:
            return self.optimized.load(file_path, target_size)
```

### 3. `loading/helpers.py` (辅助函数)

```python
"""加载辅助函数"""

import os
import mmap
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_file_size_mb(file_path: str) -> float:
    """获取文件大小(MB)"""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except Exception as e:
        logger.warning(f"获取文件大小失败: {e}")
        return 0.0


def load_with_nsimage(file_path: str) -> Optional[Any]:
    """使用NSImage加载（快速）"""
    try:
        from AppKit import NSImage
        return NSImage.alloc().initWithContentsOfFile_(file_path)
    except Exception as e:
        logger.error(f"NSImage加载失败: {e}")
        return None


def load_with_quartz(file_path: str, target_size: tuple[int, int] = None,
                     thumbnail: bool = False) -> Optional[Any]:
    """使用Quartz加载（优化）"""
    try:
        from Foundation import NSURL
        from Quartz import (
            CGImageSourceCreateWithURL,
            CGImageSourceCreateImageAtIndex,
            CGImageSourceCreateThumbnailAtIndex,
            kCGImageSourceShouldCache,
            kCGImageSourceThumbnailMaxPixelSize,
        )
        
        url = NSURL.fileURLWithPath_(file_path)
        source = CGImageSourceCreateWithURL(url, None)
        
        if thumbnail and target_size:
            # 创建缩略图
            max_size = max(target_size)
            options = {
                kCGImageSourceThumbnailMaxPixelSize: max_size,
                kCGImageSourceShouldCache: True,
            }
            return CGImageSourceCreateThumbnailAtIndex(source, 0, options)
        else:
            # 加载完整图片
            return CGImageSourceCreateImageAtIndex(source, 0, None)
            
    except Exception as e:
        logger.error(f"Quartz加载失败: {e}")
        return None


def load_with_memory_map(file_path: str, target_size: tuple[int, int] = None) -> Optional[Any]:
    """使用内存映射加载（大文件）"""
    try:
        with open(file_path, 'rb') as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                # 从内存映射创建NSData
                from AppKit import NSData, NSImage
                data = NSData.dataWithBytes_length_(mm, len(mm))
                return NSImage.alloc().initWithData_(data)
    except Exception as e:
        logger.error(f"内存映射加载失败: {e}")
        return None


def get_loader(strategy: str = 'auto'):
    """获取加载器实例（工厂函数）"""
    from .strategies import AutoStrategy, OptimizedStrategy, PreviewStrategy
    
    if strategy == 'auto':
        return AutoStrategy()
    elif strategy == 'optimized':
        return OptimizedStrategy()
    elif strategy == 'preview':
        return PreviewStrategy()
    else:
        return AutoStrategy()


def create_loader(**kwargs):
    """创建自定义加载器"""
    from .strategies import OptimizedStrategy
    return OptimizedStrategy(**kwargs)
```

### 4. `loading/config.py` (配置管理)

```python
"""加载策略配置"""

from dataclasses import dataclass


@dataclass
class LoadingConfig:
    """加载配置
    
    集中管理所有加载相关配置，避免分散的 get_config 调用
    """
    
    # 文件大小阈值 (MB)
    quartz_threshold: float = 10.0      # 小于此值用NSImage
    memory_map_threshold: float = 100.0  # 大于此值用内存映射
    
    # 质量配置
    preview_max_size: int = 512
    thumbnail_quality: float = 0.7
    
    # 性能配置
    enable_cache: bool = True
    max_parallel_loads: int = 3
    
    # 统计
    enable_stats: bool = True
    
    @classmethod
    def default(cls):
        """默认配置"""
        return cls()
    
    @classmethod
    def fast(cls):
        """快速模式（低质量）"""
        return cls(
            preview_max_size=256,
            thumbnail_quality=0.5,
        )
    
    @classmethod
    def quality(cls):
        """质量模式（高质量）"""
        return cls(
            preview_max_size=1024,
            thumbnail_quality=0.9,
        )
```

### 5. `loading/stats.py` (统计管理)

```python
"""加载统计"""

import time
from dataclasses import dataclass, field


@dataclass
class LoadingStats:
    """加载统计信息"""
    
    total_requests: int = 0
    successful_loads: int = 0
    failed_loads: int = 0
    total_time: float = 0.0
    
    # 分类统计
    nsimage_loads: int = 0
    quartz_loads: int = 0
    memory_map_loads: int = 0
    
    def record_success(self, method: str, duration: float):
        """记录成功"""
        self.total_requests += 1
        self.successful_loads += 1
        self.total_time += duration
        
        if method == 'nsimage':
            self.nsimage_loads += 1
        elif method == 'quartz':
            self.quartz_loads += 1
        elif method == 'memory_map':
            self.memory_map_loads += 1
    
    def record_failure(self):
        """记录失败"""
        self.total_requests += 1
        self.failed_loads += 1
    
    def get_stats(self) -> dict:
        """获取统计字典"""
        avg_time = (self.total_time / self.total_requests 
                   if self.total_requests > 0 else 0.0)
        
        return {
            'total_requests': self.total_requests,
            'successful_loads': self.successful_loads,
            'failed_loads': self.failed_loads,
            'total_time': self.total_time,
            'avg_time': avg_time,
            'nsimage_loads': self.nsimage_loads,
            'quartz_loads': self.quartz_loads,
            'memory_map_loads': self.memory_map_loads,
        }
```

## 📊 预期成果

### 代码量对比

| 文件 | 行数 | 说明 |
|------|------|------|
| **当前** | | |
| optimized_loading_strategies.py | 1,118 | 单一大文件 |
| **简化后** | | |
| loading/__init__.py | ~50 | 接口导出 |
| loading/strategies.py | ~350 | 核心策略 |
| loading/helpers.py | ~250 | 辅助函数 |
| loading/config.py | ~100 | 配置管理 |
| loading/stats.py | ~100 | 统计管理 |
| **总计** | **~850** | **减少 24%** |

### 改进效果

| 指标 | 改进 |
|------|------|
| 代码行数 | ↓ 268行 (24%) |
| 文件复杂度 | ↓ 70% |
| 可测试性 | ↑ 80% |
| 可维护性 | ↑ 60% |

## 🚀 实施计划

### Step 1: 创建新模块结构 (1天)

```bash
mkdir -p plookingII/core/loading
touch plookingII/core/loading/__init__.py
touch plookingII/core/loading/strategies.py
touch plookingII/core/loading/helpers.py
touch plookingII/core/loading/config.py
touch plookingII/core/loading/stats.py
```

### Step 2: 实现核心模块 (2天)

1. 实现 config.py 和 stats.py（简单）
2. 实现 helpers.py（提取辅助函数）
3. 实现 strategies.py（重构策略类）
4. 实现 __init__.py（导出接口）

### Step 3: 提供兼容层 (0.5天)

在原文件中添加兼容导入：

```python
# optimized_loading_strategies.py (兼容层)
"""向后兼容层 - 重定向到新的 loading 模块"""

from .loading import (
    OptimizedStrategy as OptimizedLoadingStrategy,
    PreviewStrategy as PreviewLoadingStrategy,
    AutoStrategy as AutoLoadingStrategy,
)

# 兼容旧的工厂
class OptimizedLoadingStrategyFactory:
    @staticmethod
    def create(strategy='auto'):
        from .loading import get_loader
        return get_loader(strategy)

__all__ = [
    'OptimizedLoadingStrategy',
    'PreviewLoadingStrategy',
    'AutoLoadingStrategy',
    'OptimizedLoadingStrategyFactory',
]
```

### Step 4: 测试和验证 (1天)

- 运行所有测试
- 性能对比测试
- 兼容性验证

### Step 5: 文档更新 (0.5天)

- 更新导入示例
- 添加迁移指南

## ⚠️ 风险控制

### 1. 向后兼容性

**风险**: 破坏现有代码

**缓解**:
- 保留兼容层
- 渐进式迁移
- 充分测试

### 2. 性能回退

**风险**: 模块化可能增加开销

**缓解**:
- 性能基准测试
- 热路径优化
- 缓存关键数据

### 3. 导入路径变更

**风险**: 需要更新多处导入

**缓解**:
- 先通过兼容层使用
- 逐步迁移到新路径
- 使用自动化工具

## 📝 下一步行动

1. **今天**: 创建新模块结构，实现 config.py 和 stats.py
2. **明天**: 实现 helpers.py 和 strategies.py
3. **后天**: 添加兼容层，测试验证

---

**创建日期**: 2025-10-06  
**负责人**: PlookingII Team  
**状态**: 规划中

**预期收益**: 代码减少24%，可维护性提升60%，为后续优化打下基础

