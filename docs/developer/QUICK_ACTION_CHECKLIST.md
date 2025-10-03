# PlookingII 架构整改快速行动清单

**生成时间**: 2025-09-30  
**基于**: 架构修复与整改方案  
**目的**: 提供可立即执行的具体行动步骤

---

## 🚀 立即可执行的行动项 (本周内)

### 第1步：弃用模块清理 (预计2-3小时)

#### ✅ 确认弃用模块列表
```bash
# 运行以下命令确认弃用模块
grep -r "已弃用\|deprecated" plookingII/ --include="*.py" | head -10
```

**已确认的弃用模块**:
- [ ] `plookingII/monitor/performance.py` (ImagePerformanceMonitor)
- [ ] `plookingII/monitor/memory.py` (MemoryMonitor)
- [ ] `plookingII/monitor/simplified_memory.py` (SimplifiedMemoryMonitor)
- [ ] `plookingII/core/history.py` (HistoryManager类)

#### ✅ 添加更明显的弃用警告
```python
# 在每个弃用模块的开头添加
import warnings

warnings.warn(
    f"{__name__} is deprecated and will be removed in v1.4.0. "
    "Use plookingII.monitor.unified_monitor.UnifiedMonitor instead.",
    DeprecationWarning,
    stacklevel=2
)
```

### 第2步：版本信息标准化 (预计1-2小时)

#### ✅ 更新版本标记
需要更新的文件：
- [ ] `plookingII/config/__init__.py` - 将v1.2.0改为v1.4.0
- [ ] `plookingII/config/manager.py` - 将Version: 1.0.0改为1.4.0
- [ ] `plookingII/monitor/unified_monitor.py` - 添加Version: 1.4.0
- [ ] `plookingII/core/unified_cache_manager.py` - 添加Version: 1.4.0

#### ✅ 标准化版本格式
```python
# 统一的版本信息格式
"""
模块名称

模块描述...

Author: PlookingII Team
Version: 1.4.0
Since: v1.x.x
Status: stable
"""
```

### 第3步：创建迁移指导文档 (预计1小时)

#### ✅ 创建迁移指南
```bash
# 创建文件
touch MIGRATION_GUIDE.md
```

内容模板：
```markdown
# 模块迁移指南

## 监控系统迁移
```python
# 旧方式 (已弃用)
from plookingII.monitor.memory import MemoryMonitor
monitor = MemoryMonitor()

# 新方式 (推荐)
from plookingII.monitor import get_unified_monitor
monitor = get_unified_monitor()
```

## 配置系统迁移
```python
# 旧方式 (已弃用)
from plookingII.core.unified_config import unified_config
value = unified_config.get("key")

# 新方式 (推荐)
from plookingII.config.manager import get_config
value = get_config("key")
```
```

---

## 📋 本周可完成的具体任务

### Day 1: 弃用警告和版本更新
- [ ] **09:00-10:00** 添加弃用警告到所有已确认的弃用模块
- [ ] **10:00-11:00** 更新版本信息标记
- [ ] **11:00-12:00** 运行测试确保警告正常工作

### Day 2: 文档创建和更新  
- [ ] **09:00-10:00** 创建MIGRATION_GUIDE.md
- [ ] **10:00-11:00** 更新README.md中的架构说明
- [ ] **11:00-12:00** 更新DEVELOPER_GUIDE.md中的模块信息

### Day 3: 自动化工具创建
- [ ] **09:00-11:00** 创建重复检查脚本
- [ ] **11:00-12:00** 创建import替换脚本

### Day 4-5: 测试和验证
- [ ] **Day 4** 运行完整测试套件
- [ ] **Day 5** 验证所有变更，准备下周的大规模整改

---

## 🛠️ 实用工具脚本

### 1. 弃用警告添加脚本
```python
# tools/add_deprecation_warnings.py
#!/usr/bin/env python3
"""自动添加弃用警告的脚本"""

import os
import re

DEPRECATED_MODULES = [
    'plookingII/monitor/performance.py',
    'plookingII/monitor/memory.py', 
    'plookingII/monitor/simplified_memory.py'
]

WARNING_TEMPLATE = '''import warnings

warnings.warn(
    f"{__name__} is deprecated and will be removed in v1.4.0. "
    "Use plookingII.monitor.unified_monitor.UnifiedMonitor instead.",
    DeprecationWarning,
    stacklevel=2
)

'''

def add_warning_to_file(file_path):
    """给文件添加弃用警告"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经有警告
    if 'warnings.warn' in content:
        print(f"Warning already exists in {file_path}")
        return
    
    # 在第一个import后添加警告
    lines = content.split('\n')
    insert_pos = 0
    
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_pos = i + 1
            break
    
    lines.insert(insert_pos, WARNING_TEMPLATE)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"Added warning to {file_path}")

if __name__ == '__main__':
    for module in DEPRECATED_MODULES:
        if os.path.exists(module):
            add_warning_to_file(module)
```

### 2. 版本信息更新脚本
```python
# tools/update_version_info.py
#!/usr/bin/env python3
"""更新版本信息的脚本"""

import os
import re

VERSION_UPDATES = {
    'plookingII/config/__init__.py': [
        (r'v1\.2\.0', 'v1.4.0'),
        (r'Version: 1\.0\.0', 'Version: 1.4.0')
    ],
    'plookingII/config/manager.py': [
        (r'Version: 1\.0\.0', 'Version: 1.4.0')
    ]
}

def update_version_in_file(file_path, patterns):
    """更新文件中的版本信息"""
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    for old_pattern, new_value in patterns:
        content = re.sub(old_pattern, new_value, content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated version info in {file_path}")
    else:
        print(f"No changes needed in {file_path}")

if __name__ == '__main__':
    for file_path, patterns in VERSION_UPDATES.items():
        update_version_in_file(file_path, patterns)
```

### 3. 重复检查脚本
```python
# tools/check_duplicates.py
#!/usr/bin/env python3
"""检查重复模块和功能的脚本"""

import os
import ast
import re
from collections import defaultdict

def find_similar_classes():
    """查找相似的类名"""
    classes = defaultdict(list)
    
    for root, dirs, files in os.walk('plookingII'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 使用AST解析类名
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            classes[node.name].append(file_path)
                except:
                    pass
    
    # 输出重复的类名
    print("=== 重复的类名 ===")
    for class_name, files in classes.items():
        if len(files) > 1:
            print(f"{class_name}:")
            for file_path in files:
                print(f"  - {file_path}")
            print()

def find_similar_functions():
    """查找相似的函数名"""
    functions = defaultdict(list)
    
    for root, dirs, files in os.walk('plookingII'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 查找函数定义
                    func_pattern = r'def\s+(\w+)\s*\('
                    functions_in_file = re.findall(func_pattern, content)
                    
                    for func_name in functions_in_file:
                        if not func_name.startswith('_'):  # 忽略私有函数
                            functions[func_name].append(file_path)
                except:
                    pass
    
    # 输出重复的函数名（只显示出现3次以上的）
    print("=== 可能重复的函数名 ===")
    for func_name, files in functions.items():
        if len(files) >= 3:
            print(f"{func_name} ({len(files)}次):")
            for file_path in files[:5]:  # 只显示前5个
                print(f"  - {file_path}")
            if len(files) > 5:
                print(f"  - ... 还有{len(files)-5}个文件")
            print()

if __name__ == '__main__':
    print("PlookingII 重复检查报告")
    print("=" * 50)
    find_similar_classes()
    find_similar_functions()
```

---

## 📊 进度跟踪模板

### 每日进度记录
```markdown
## 2025-09-30 进度记录

### 完成的任务
- [ ] 添加弃用警告到performance.py
- [ ] 添加弃用警告到memory.py  
- [ ] 更新config/__init__.py版本信息
- [ ] 更新config/manager.py版本信息

### 遇到的问题
- 问题描述
- 解决方案

### 明天计划
- 任务1
- 任务2

### 风险提醒
- 需要注意的风险点
```

---

## 🔍 验证清单

### 每个变更后的验证步骤
1. **代码语法检查**
   ```bash
   python -m py_compile plookingII/path/to/modified/file.py
   ```

2. **导入测试**
   ```bash
   python -c "import plookingII.module.name; print('Import OK')"
   ```

3. **弃用警告测试**
   ```bash
   python -c "import plookingII.monitor.performance" 2>&1 | grep -i deprecat
   ```

4. **基本功能测试**
   ```bash
   python -m pytest tests/ -v -k "test_basic_functionality"
   ```

### 周末总结检查
- [ ] 所有计划任务是否完成？
- [ ] 是否引入了新的问题？
- [ ] 测试是否通过？
- [ ] 文档是否同步更新？
- [ ] 下周计划是否明确？

---

## 📞 紧急联系和回滚

### 如果出现问题
1. **立即停止当前操作**
2. **记录具体错误信息**
3. **检查git状态**: `git status`
4. **如需回滚**: `git checkout -- <file>` 或 `git reset --hard HEAD~1`

### 紧急回滚命令
```bash
# 回滚单个文件
git checkout HEAD -- plookingII/path/to/file.py

# 回滚所有未提交的变更
git reset --hard HEAD

# 查看最近的提交
git log --oneline -10
```

---

**清单创建时间**: 2025-09-30  
**适用版本**: v1.4.0  
**更新频率**: 每日更新进度，每周总结调整

> 这个快速行动清单提供了具体的、可立即执行的步骤。建议每天按照清单执行，并及时记录进度和问题。如遇到任何技术问题，请优先保证系统稳定性，必要时进行回滚。
