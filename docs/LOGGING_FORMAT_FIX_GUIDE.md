# 日志格式批量修复指南

**目标**: 修复剩余358个日志格式问题 (G004)
**工作量**: 预计12-16小时
**优先级**: 中 (代码规范，非功能性)

______________________________________________________________________

## 🎯 修复目标

将所有 f-string 格式的日志调用转换为 `%` 格式（Python 日志最佳实践）：

### 修复模式

```python
# ❌ 修复前 - f-string格式
logger.debug(f"Loading {path}")
logger.info(f"Cache '{name}' size: {size_mb:.2f}MB")
logger.error(f"Failed to process {item}: {error}")

# ✅ 修复后 - %格式
logger.debug("Loading %s", path)
logger.info("Cache '%s' size: %.2fMB", name, size_mb)
logger.error("Failed to process %s: %s", item, error)
```

### 为什么使用 `%` 格式？

1. **性能更好**: 仅在实际记录时才格式化字符串
1. **日志分析友好**: 日志聚合工具更容易识别模式
1. **Python 官方推荐**: [Python Logging Best Practices](https://docs.python.org/3/howto/logging.html#optimization)
1. **避免注入攻击**: 更安全的字符串处理

______________________________________________________________________

## 📊 问题分布（358个）

### 按模块分类

| 模块                | 文件数 | 问题数  | 优先级 | 工作量     |
| ------------------- | ------ | ------- | ------ | ---------- |
| **ui/controllers/** | 5      | 72      | 高     | 4h         |
| **core/**           | 10     | 121     | 高     | 6h         |
| **services/**       | 4      | 42      | 高     | 2h         |
| **ui/managers/**    | 3      | 35      | 中     | 2h         |
| **ui/**             | 2      | 34      | 中     | 2h         |
| **其他**            | 10     | 54      | 低     | 2-4h       |
| **总计**            | **34** | **358** | -      | **12-16h** |

### 按文件优先级（Top 10）

| 文件                                        | 问题数 | 优先级 | 原因         |
| ------------------------------------------- | ------ | ------ | ------------ |
| ui/controllers/unified_status_controller.py | 23     | ⚠️ 高  | 核心UI控制器 |
| ui/window.py                                | 22     | ⚠️ 高  | 主窗口       |
| ui/managers/image_update_manager.py         | 14     | ⚠️ 高  | 图片更新管理 |
| ui/controllers/menu_controller.py           | 14     | ⚠️ 高  | 菜单控制     |
| services/background_task_manager.py         | 14     | ⚠️ 高  | 后台任务     |
| core/cleanup_utils.py                       | 14     | ⚠️ 高  | 清理工具     |
| config/manager.py                           | 14     | ⚠️ 高  | 配置管理     |
| services/image_loader_service.py            | 13     | ⚠️ 高  | 图片加载     |
| core/image_rotation.py                      | 13     | ⚠️ 高  | 图片旋转     |
| ui/views.py                                 | 12     | ⚠️ 高  | UI视图       |

______________________________________________________________________

## 🛠️ 修复方法

### 方法一：手动修复（推荐，最安全）⭐⭐⭐

适用于：生产环境，质量优先

#### 步骤

```bash
# 1. 创建修复分支
git checkout -b fix/logging-format

# 2. 按优先级修复文件
# 优先修复：core/, services/ (核心业务逻辑)
# 其次修复：ui/controllers/ (用户交互)
# 最后修复：ui/managers/, utils/ (工具类)

# 3. 每修复一个文件，立即验证
python3 -c "import py_compile; py_compile.compile('plookingII/xxx.py', doraise=True)"
python3 -m ruff check plookingII/xxx.py --select G004

# 4. 每修复10-20个问题，运行测试
make test  # 或 pytest tests/

# 5. 分批提交
git add plookingII/core/
git commit -m "fix(logging): 修复core模块日志格式 (G004)"

git add plookingII/services/
git commit -m "fix(logging): 修复services模块日志格式 (G004)"
```

#### 修复示例

**简单情况（无格式化）**:

```python
# 查找
logger.debug(f"Loading {path}")

# 替换为
logger.debug("Loading %s", path)
```

**复杂情况（带格式化）**:

```python
# 查找
logger.info(f"Cache size: {size_mb:.2f}MB, items: {count:d}")

# 替换为
logger.info("Cache size: %.2fMB, items: %d", size_mb, count)
```

**多行情况**:

```python
# 查找
logger.debug(f"Processing {name}: size={size:.2f}, time={duration:.3f}s")

# 替换为
logger.debug("Processing %s: size=%.2f, time=%.3fs", name, size, duration)
```

#### 格式说明符对照表

| f-string    | % 格式 | 说明               |
| ----------- | ------ | ------------------ |
| `{var}`     | `%s`   | 字符串（万能）     |
| `{var:d}`   | `%d`   | 整数               |
| `{var:.2f}` | `%.2f` | 浮点数（2位小数）  |
| `{var:.3f}` | `%.3f` | 浮点数（3位小数）  |
| `{var:,}`   | `%s`   | 千分位（使用`%s`） |
| `{var!r}`   | `%r`   | repr表示           |

### 方法二：半自动修复（平衡）⭐⭐

适用于：非核心模块，中等风险接受度

#### 使用 sed 批量替换简单模式

```bash
# ⚠️ 警告：仅适用于简单情况，需要充分测试！

# 1. 备份
git branch backup-$(date +%Y%m%d)

# 2. 处理简单的单变量情况
# 模式: logger.xxx(f"text {var}")
find plookingII -name "*.py" -exec sed -i.bak \
  's/logger\.\(debug\|info\|warning\|error\)(f"\([^{]*\){\([^}:]*\)}\([^{]*\)")/logger.\1("\2%s\4", \3)/g' {} +

# 3. 立即验证
python3 -m ruff check plookingII
make test

# 4. 如果有问题，立即回滚
find plookingII -name "*.py.bak" -exec sh -c 'mv "$0" "${0%.bak}"' {} \;
```

⚠️ **注意**: sed 只能处理最简单的情况，复杂格式化需要手动处理。

### 方法三：使用自定义脚本（快速但有风险）⚠️

适用于：测试环境，快速迭代

#### 脚本位置

`scripts/fix_code_quality.py`（项目本地，未提交到 Git）

#### 使用方法

```bash
# 1. 预览修复（强烈建议！）
python3 scripts/fix_code_quality.py --dry-run --verbose

# 2. 检查预览结果
# 重点关注：
# - 格式化的 f-string 是否正确转换
# - 多行日志是否正确处理
# - 特殊字符是否转义

# 3. 如果预览OK，执行修复
python3 scripts/fix_code_quality.py

# 4. 立即验证
python3 -m ruff check plookingII
make test

# 5. 检查语法
python3 -c "
import py_compile
from pathlib import Path
for f in Path('plookingII').rglob('*.py'):
    try:
        py_compile.compile(f, doraise=True)
    except Exception as e:
        print(f'ERROR: {f}: {e}')
"

# 6. 如果有问题，立即回滚
git restore .
```

#### 脚本功能

- ✅ 处理简单的 f-string 日志
- ✅ 处理格式化的 f-string（.2f, :d 等）
- ✅ 支持多行日志
- ✅ Dry-run 预览模式
- ❌ 不处理复杂嵌套表达式
- ❌ 不处理字符串中的特殊字符

______________________________________________________________________

## 📝 修复清单

### Phase 1: 核心模块（高优先级）

- [ ] **core/** (121个，6小时)

  - [ ] simple_cache.py (11个) ✅ 已完成
  - [ ] cleanup_utils.py (14个)
  - [ ] image_rotation.py (13个)
  - [ ] file_watcher.py (11个)
  - [ ] image_processing.py (9个)
  - [ ] base_classes.py (9个)
  - [ ] error_handling.py (8个)
  - [ ] unified_interfaces.py (8个)
  - [ ] 其他文件 (38个)

- [ ] **services/** (42个，2小时)

  - [ ] background_task_manager.py (14个)
  - [ ] image_loader_service.py (13个)
  - [ ] history_manager.py (7个)
  - [ ] recent.py (8个)

### Phase 2: UI控制器（中优先级）

- [ ] **ui/controllers/** (72个，4小时)

  - [ ] unified_status_controller.py (23个)
  - [ ] menu_controller.py (14个)
  - [ ] drag_drop_controller.py (10个)
  - [ ] 其他控制器 (25个)

- [ ] **ui/** (34个，2小时)

  - [ ] window.py (22个)
  - [ ] views.py (12个)

- [ ] **ui/managers/** (35个，2小时)

  - [ ] image_update_manager.py (14个)
  - [ ] image_manager.py (9个)
  - [ ] 其他管理器 (12个)

### Phase 3: 配置和工具（低优先级）

- [ ] **config/** (14个，1小时)

  - [ ] manager.py (14个)

- [ ] **其他模块** (40个，2小时)

  - [ ] __init__.py (2个)
  - [ ] utils/ (6个)
  - [ ] monitor/ (6个)
  - [ ] db/ (少量)

______________________________________________________________________

## ✅ 验证步骤

### 每个文件修复后

```bash
# 1. 语法检查
python3 -c "import py_compile; py_compile.compile('文件路径', doraise=True)"

# 2. 检查 G004 是否修复
python3 -m ruff check 文件路径 --select G004

# 3. 快速功能验证（如果可能）
python3 -c "from plookingII.模块 import 类; print('OK')"
```

### 每个模块修复后

```bash
# 1. 运行单元测试
pytest tests/unit/test_模块.py -v

# 2. 检查整个模块
python3 -m ruff check plookingII/模块/ --select G004

# 3. 查看统计
python3 -m ruff check plookingII --statistics | grep G004
```

### 全部修复后

```bash
# 1. 完整测试套件
make test
# 或
pytest tests/ -v

# 2. 类型检查
mypy plookingII/

# 3. 完整 lint检查
python3 -m ruff check plookingII --statistics

# 4. 手动功能测试
python3 -m plookingII
# 测试：打开文件夹、浏览图片、缩放、旋转等

# 5. 检查日志输出
# 确保日志消息正确显示，变量正确替换
```

______________________________________________________________________

## 🎯 预期成果

### 修复前后对比

| 指标         | 修复前 | 修复后 | 改善    |
| ------------ | ------ | ------ | ------- |
| G004 问题    | 369    | 0      | ↓ 100%  |
| 代码质量评分 | 75/100 | 78/100 | +3分    |
| 总问题数     | 889    | 531    | ↓ 40.3% |

### 代码质量提升

- ✅ **性能改善**: 日志格式化延迟到实际输出时
- ✅ **代码规范**: 符合 Python 官方最佳实践
- ✅ **可维护性**: 统一的日志风格，便于搜索和分析
- ✅ **日志分析**: 更容易用工具聚合和分析日志

______________________________________________________________________

## ⚠️ 注意事项

### 常见陷阱

1. **字符串中的引号**

   ```python
   # ❌ 错误
   logger.info("File '%s' not found", path)  # 引号冲突

   # ✅ 正确
   logger.info("File '%s' not found", path)  # 使用转义或双引号
   ```

1. **格式说明符错误**

   ```python
   # ❌ 错误
   logger.info("Size: %dMB", 3.5)  # %d 不能格式化浮点数

   # ✅ 正确
   logger.info("Size: %.1fMB", 3.5)  # 使用 %f
   ```

1. **参数数量不匹配**

   ```python
   # ❌ 错误
   logger.info("Loading %s from %s", path)  # 少一个参数

   # ✅ 正确
   logger.info("Loading %s from %s", path, source)
   ```

1. **表达式嵌套**

   ```python
   # ❌ 难以自动修复
   logger.debug(f"Result: {calculate(x) + 1}")

   # ✅ 手动修复
   result = calculate(x) + 1
   logger.debug("Result: %s", result)
   ```

### 测试关键点

- [ ] 日志消息显示正确
- [ ] 变量值正确替换
- [ ] 没有引入语法错误
- [ ] 应用正常启动和运行
- [ ] 所有测试通过

______________________________________________________________________

## 📊 进度跟踪

### 使用 Ruff 跟踪进度

```bash
# 查看剩余问题数
python3 -m ruff check plookingII --select G004 --statistics

# 查看具体问题
python3 -m ruff check plookingII --select G004 | wc -l

# 按文件查看
python3 -m ruff check plookingII --select G004 2>&1 | \
  grep "plookingII/" | cut -d: -f1 | sort | uniq -c | sort -rn
```

### 提交策略

```bash
# 建议按模块分批提交
git commit -m "fix(logging): 修复core模块日志格式 (G004, 121个)"
git commit -m "fix(logging): 修复services模块日志格式 (G004, 42个)"
git commit -m "fix(logging): 修复ui/controllers日志格式 (G004, 72个)"
git commit -m "fix(logging): 修复其他模块日志格式 (G004, 剩余)"
```

______________________________________________________________________

## 🎓 参考资源

### Python 日志最佳实践

- [Python Logging HOWTO](https://docs.python.org/3/howto/logging.html)
- [Python Logging Cookbook](https://docs.python.org/3/howto/logging-cookbook.html)
- [Logging Performance](https://docs.python.org/3/howto/logging.html#optimization)

### Ruff 文档

- [G004 Rule](https://docs.astral.sh/ruff/rules/logging-f-string/)
- [Ruff Configuration](https://docs.astral.sh/ruff/configuration/)

### 项目文档

- [代码质量改进计划](CODE_QUALITY_IMPROVEMENT_PLAN.md)
- [代码质量修复总结](CODE_QUALITY_FIX_SUMMARY.md)
- [最终总结报告](CODE_QUALITY_FINAL_SUMMARY.md)

______________________________________________________________________

## 💡 经验总结

### 已完成的示例

参考 `plookingII/core/simple_cache.py` 的修复：

- ✅ 11个日志格式问题全部修复
- ✅ 语法检查通过
- ✅ Ruff 检查通过
- ✅ 功能正常

### 修复模式

```python
# 示例 1：简单变量
- logger.info(f"Loading {path}")
+ logger.info("Loading %s", path)

# 示例 2：多个变量
- logger.debug(f"Cache HIT [{self.name}]: {key}")
+ logger.debug("Cache HIT [%s]: %s", self.name, key)

# 示例 3：浮点数格式化
- logger.info(f"Size: {size_mb:.2f}MB")
+ logger.info("Size: %.2fMB", size_mb)

# 示例 4：多行日志
- logger.debug(
-     f"Cache PUT [{self.name}]: {key} (size={size_mb:.2f}MB)"
- )
+ logger.debug(
+     "Cache PUT [%s]: %s (size=%.2fMB)",
+     self.name, key, size_mb
+ )
```

______________________________________________________________________

## 📅 时间估算

### 按技能水平

| 开发者经验       | 预计时间 | 建议方法                        |
| ---------------- | -------- | ------------------------------- |
| 高级（熟悉项目） | 8-10h    | 混合：手动（核心）+脚本（其他） |
| 中级（了解项目） | 12-16h   | 手动修复为主，谨慎使用脚本      |
| 初级（学习项目） | 16-24h   | 完全手动，每步验证              |

### 分阶段执行

- **Week 1**: 核心模块（core/, services/） - 163个问题
- **Week 2**: UI模块（ui/controllers/, ui/managers/） - 141个问题
- **Week 3**: 其他模块 - 54个问题

______________________________________________________________________

**文档创建**: 2025-10-14
**状态**: ✅ 就绪
**最后更新**: 2025-10-14
**相关文档**: [代码质量最终总结](CODE_QUALITY_FINAL_SUMMARY.md)
