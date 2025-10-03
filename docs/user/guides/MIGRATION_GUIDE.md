# PlookingII 模块迁移指南

**版本**: v1.4.0  
**更新时间**: 2025-09-30  
**适用范围**: 从旧模块迁移到统一接口

---

## 🎯 迁移概述

PlookingII v1.4.0 完成了系统架构的统一化，多个重复的模块已被弃用并将在 v1.4.0 中移除。本指南帮助开发者从旧接口迁移到新的统一接口。

### 主要变更
- **监控系统统一** - 所有监控功能整合到 `UnifiedMonitor`
- **配置系统统一** - 统一使用 `ConfigManager`
- **版本信息标准化** - 所有模块版本信息更新到 v1.4.0

---

## 🔄 监控系统迁移

### ❌ 已弃用的监控模块

以下模块已标记为弃用，将在 v1.4.0 中移除：

```python
# ❌ 已弃用 - 不要使用
from plookingII.monitor.memory import MemoryMonitor
from plookingII.monitor.performance import ImagePerformanceMonitor  
from plookingII.monitor.simplified_memory import SimplifiedMemoryMonitor
```

### ✅ 推荐的新接口

```python
# ✅ 推荐 - 使用统一监控器
from plookingII.monitor import get_unified_monitor

# 获取统一监控器实例
monitor = get_unified_monitor()

# 统一的监控接口
memory_status = monitor.get_memory_status()
performance_metrics = monitor.get_performance_metrics()
system_health = monitor.get_system_health()
```

### 具体迁移示例

#### 内存监控迁移

```python
# 旧方式 ❌
from plookingII.monitor.memory import MemoryMonitor

memory_monitor = MemoryMonitor()
usage = memory_monitor.get_memory_usage()
is_high = memory_monitor.is_memory_usage_high()

# 新方式 ✅
from plookingII.monitor import get_unified_monitor

monitor = get_unified_monitor()
memory_status = monitor.get_memory_status()
usage = memory_status['current_usage_mb']
is_high = memory_status['is_high_usage']
```

#### 性能监控迁移

```python
# 旧方式 ❌
from plookingII.monitor.performance import ImagePerformanceMonitor

perf_monitor = ImagePerformanceMonitor()
perf_monitor.record_load_time("image.jpg", 1.2, "quartz")
metrics = perf_monitor.get_performance_summary()

# 新方式 ✅
from plookingII.monitor import get_unified_monitor

monitor = get_unified_monitor()
monitor.record_operation("image_load", {
    'file_path': "image.jpg",
    'load_time': 1.2,
    'method': "quartz"
})
metrics = monitor.get_performance_metrics()
```

---

## ⚙️ 配置系统迁移

### ❌ 已弃用的配置模块

```python
# ❌ 已弃用 - 不要使用
from plookingII.core.unified_config import unified_config
from plookingII.core.simple_config import SimpleConfig
```

### ✅ 推荐的新接口

```python
# ✅ 推荐 - 使用统一配置管理器
from plookingII.config.manager import get_config, set_config, ConfigManager

# 简单的配置访问
value = get_config("key", default_value)
set_config("key", new_value)

# 高级配置管理
config_manager = ConfigManager()
config_manager.load_config()
all_configs = config_manager.get_all_configs()
```

### 具体迁移示例

#### 基本配置访问

```python
# 旧方式 ❌
from plookingII.core.unified_config import unified_config

threshold = unified_config.get("memory_threshold", 1000)
unified_config.set("memory_threshold", 1200)

# 新方式 ✅
from plookingII.config.manager import get_config, set_config

threshold = get_config("memory_threshold", 1000)
set_config("memory_threshold", 1200)
```

#### 配置验证和类型检查

```python
# 旧方式 ❌
from plookingII.core.unified_config import UnifiedConfig

config = UnifiedConfig()
if config.validate_config("key", value):
    config.set("key", value)

# 新方式 ✅
from plookingII.config.manager import ConfigManager

config_manager = ConfigManager()
try:
    config_manager.set_config("key", value)  # 自动验证
except ValueError as e:
    print(f"配置验证失败: {e}")
```

---

## 📚 历史记录管理迁移

### ❌ 已弃用的历史管理器

```python
# ❌ 已弃用 - 不要使用
from plookingII.core.history import HistoryManager
```

### ✅ 推荐的新接口

```python
# ✅ 推荐 - 使用任务历史管理器
from plookingII.core.history import TaskHistoryManager

history_manager = TaskHistoryManager()
history_manager.save_current_state(current_index, image_list, folder_list)
history_data = history_manager.load_history()
```

---

## 🛠️ 自动化迁移工具

### 快速检查脚本

创建一个脚本来检查代码中是否还有旧的导入：

```python
#!/usr/bin/env python3
"""检查代码中的旧导入"""

import os
import re

DEPRECATED_IMPORTS = [
    r'from plookingII\.monitor\.memory import',
    r'from plookingII\.monitor\.performance import',
    r'from plookingII\.monitor\.simplified_memory import',
    r'from plookingII\.core\.unified_config import',
    r'from plookingII\.core\.simple_config import',
    r'from plookingII\.core\.history import HistoryManager'
]

def check_file(file_path):
    """检查单个文件中的旧导入"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    issues = []
    for pattern in DEPRECATED_IMPORTS:
        matches = re.findall(pattern, content)
        if matches:
            issues.append(f"Found deprecated import: {pattern}")
    
    return issues

# 使用示例
for root, dirs, files in os.walk('plookingII'):
    for file in files:
        if file.endswith('.py'):
            file_path = os.path.join(root, file)
            issues = check_file(file_path)
            if issues:
                print(f"\n{file_path}:")
                for issue in issues:
                    print(f"  - {issue}")
```

### 批量替换脚本

```python
#!/usr/bin/env python3
"""批量替换旧导入的脚本"""

import os
import re

IMPORT_REPLACEMENTS = {
    # 监控系统替换
    r'from plookingII\.monitor\.memory import MemoryMonitor': 
        'from plookingII.monitor import get_unified_monitor',
    r'from plookingII\.monitor\.performance import ImagePerformanceMonitor':
        'from plookingII.monitor import get_unified_monitor',
    
    # 配置系统替换
    r'from plookingII\.core\.unified_config import unified_config':
        'from plookingII.config.manager import get_config, set_config',
    r'from plookingII\.core\.unified_config import UnifiedConfig':
        'from plookingII.config.manager import ConfigManager',
}

def replace_imports_in_file(file_path):
    """替换文件中的旧导入"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    for old_pattern, new_import in IMPORT_REPLACEMENTS.items():
        content = re.sub(old_pattern, new_import, content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated imports in {file_path}")
        return True
    
    return False

# 使用示例
updated_files = 0
for root, dirs, files in os.walk('plookingII'):
    for file in files:
        if file.endswith('.py'):
            file_path = os.path.join(root, file)
            if replace_imports_in_file(file_path):
                updated_files += 1

print(f"Updated {updated_files} files")
```

---

## ⚠️ 迁移注意事项

### 1. 向后兼容性

- **当前版本 (v1.4.0)**: 旧接口仍然可用，但会显示弃用警告
- **下个版本 (v1.4.0)**: 旧接口将被完全移除

### 2. 功能差异

#### 监控系统
- **UnifiedMonitor** 提供了更丰富的监控数据
- 接口方法名可能略有不同，但功能更强大
- 支持更灵活的配置和扩展

#### 配置系统
- **ConfigManager** 提供了更好的类型检查和验证
- 支持环境变量覆盖
- 更好的错误处理和日志记录

### 3. 性能影响

- 新的统一接口在性能上有所优化
- 减少了模块间的重复代码
- 更好的内存使用效率

---

## 🧪 迁移测试

### 测试清单

在完成迁移后，请确保以下功能正常工作：

#### 监控功能测试
```python
from plookingII.monitor import get_unified_monitor

monitor = get_unified_monitor()

# 测试内存监控
memory_status = monitor.get_memory_status()
assert 'current_usage_mb' in memory_status
assert 'is_high_usage' in memory_status

# 测试性能监控
monitor.record_operation("test_operation", {"duration": 1.0})
metrics = monitor.get_performance_metrics()
assert 'operations' in metrics
```

#### 配置功能测试
```python
from plookingII.config.manager import get_config, set_config

# 测试配置读写
original_value = get_config("test_key", "default")
set_config("test_key", "new_value")
new_value = get_config("test_key")
assert new_value == "new_value"
```

### 回归测试

运行完整的测试套件以确保迁移没有破坏现有功能：

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定的监控测试
python -m pytest tests/test_monitor.py -v

# 运行特定的配置测试  
python -m pytest tests/test_config.py -v
```

---

## 📞 获取帮助

如果在迁移过程中遇到问题：

1. **查看弃用警告** - 运行代码时注意控制台的弃用警告信息
2. **参考测试代码** - 查看 `tests/` 目录中的测试用例了解正确用法
3. **查看API文档** - 参考 `TECHNICAL_GUIDE.md` 中的API说明

---

## 📈 迁移时间表

### 建议的迁移时间表

| 阶段 | 时间 | 任务 |
|------|------|------|
| 第1周 | 立即开始 | 使用检查脚本识别所有旧导入 |
| 第2周 | | 开始替换非关键路径的导入 |
| 第3-4周 | | 替换核心功能的导入并测试 |
| 第5-6周 | | 完成所有迁移并进行全面测试 |
| v1.4.0发布前 | | 确保没有旧导入残留 |

### 优先级建议

1. **高优先级**: 新开发的功能直接使用新接口
2. **中优先级**: 经常修改的代码模块优先迁移
3. **低优先级**: 稳定且很少修改的代码可以延后迁移

---

**文档版本**: v1.4.0  
**最后更新**: 2025-09-30  
**维护者**: PlookingII Team

> 本迁移指南将随着项目发展持续更新。建议定期查看最新版本以获取最准确的迁移信息。
