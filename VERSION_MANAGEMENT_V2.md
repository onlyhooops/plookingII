# PlookingII 智能版本管理系统 V2.0

**创建日期**: 2025-10-06  
**版本**: 2.0  
**状态**: ✅ 生产就绪

---

## 🎯 设计理念

**真正的单一真源（Single Source of Truth）**：
- 版本号**只在一个地方定义**：`plookingII/__version__.py`
- 所有其他地方**自动导入**，无需手动同步
- 发布新版本时**只需修改一个文件**

---

## 📁 文件结构

```
plookingII/
├── __version__.py              # 🎯 版本号唯一真源
├── config/
│   └── constants.py            # 从 __version__.py 自动导入
├── ui/
│   └── controllers/
│       └── menu_controller.py  # 从 constants.py 自动导入
└── ...

pyproject.toml                  # 动态读取版本号
scripts/
├── bump_version.py             # 🔧 版本号自动提升工具
└── verify_version_consistency.py  # 验证脚本
```

---

## 🚀 使用方法

### 1. 发布新版本（自动提升）

```bash
# 修复 Bug（1.7.0 → 1.7.1）
python scripts/bump_version.py patch

# 新增功能（1.7.0 → 1.8.0）
python scripts/bump_version.py minor

# 重大更新（1.7.0 → 2.0.0）
python scripts/bump_version.py major
```

### 2. 发布新版本（指定版本）

```bash
# 直接指定版本号
python scripts/bump_version.py 1.8.0
```

### 3. 试运行（不修改文件）

```bash
# 查看将要执行的操作
python scripts/bump_version.py minor --dry-run
```

### 4. 在代码中获取版本号

```python
# 方式1：直接导入
from plookingII.__version__ import __version__
print(f"Version: {__version__}")  # 输出: Version: 1.7.0

# 方式2：通过 constants（向后兼容）
from plookingII.config.constants import VERSION
print(f"Version: {VERSION}")  # 输出: Version: 1.7.0

# 方式3：获取完整信息
from plookingII.__version__ import get_full_version
print(get_full_version())  # 输出: PlookingII v1.7.0 (Architecture Refinement)

# 方式4：获取版本元组
from plookingII.__version__ import VERSION_INFO
major, minor, patch = VERSION_INFO
print(f"{major}.{minor}.{patch}")  # 输出: 1.7.0
```

---

## 🔄 完整发布流程

### 步骤 1: 提升版本号

```bash
# 选择合适的提升类型
python scripts/bump_version.py minor

# 输出:
# ======================================================================
# 🔄 PlookingII 版本号提升
# ======================================================================
# 当前版本: 1.7.0
# 新版本:   1.8.0
# 
# 是否继续? [Y/n] y
# 📝 更新版本文件: __version__.py
# ✅ 版本文件已更新
# 🔍 验证版本号一致性...
# ✅ 版本号一致性验证通过
```

### 步骤 2: 更新 CHANGELOG

```bash
# 编辑 CHANGELOG.md，添加版本 1.8.0 的变更说明
vim CHANGELOG.md
```

### 步骤 3: 提交并标记

```bash
# 提交所有更改
git add -A
git commit -m "chore: bump version to 1.8.0"

# 创建版本标签
git tag -a v1.8.0 -m "Release v1.8.0"
```

### 步骤 4: 推送到远程

```bash
# 推送代码和标签
git push origin main
git push origin v1.8.0
```

---

## 🎨 版本号文件详解

### `plookingII/__version__.py` - 版本号唯一真源

```python
# 🎯 唯一版本号定义 - 发布新版本时只需修改这里
__version__ = "1.7.0"

# 版本号别名（向后兼容）
VERSION = __version__
APP_VERSION = __version__

# 版本信息元组
VERSION_INFO = (1, 7, 0)
MAJOR, MINOR, PATCH = VERSION_INFO

# 版本描述
VERSION_DESCRIPTION = "Architecture Refinement"

# 发布日期
RELEASE_DATE = "2025-10-06"
```

**关键特性**：
- ✅ **唯一定义处**：所有版本信息都在这里
- ✅ **语义化版本**：遵循 SemVer 2.0.0 规范
- ✅ **自动解析**：`VERSION_INFO` 自动从字符串解析
- ✅ **丰富信息**：包含版本号、描述、发布日期

### `pyproject.toml` - 动态版本读取

```toml
[project]
name = "plookingII"
dynamic = ["version"]  # 声明版本号为动态

[tool.setuptools.dynamic]
version = {attr = "plookingII.__version__.__version__"}  # 从 __version__.py 读取
```

**优势**：
- ✅ 打包时自动读取版本号
- ✅ 无需手动同步
- ✅ 符合 PEP 621 标准

---

## 🔧 自动化工具

### `scripts/bump_version.py` - 版本号自动提升

**功能**：
- 自动提升版本号（major/minor/patch）
- 支持指定具体版本号
- 自动更新发布日期
- 自动验证版本一致性
- 提供详细的下一步操作指引

**使用示例**：

```bash
# 1. 提升修订号（Bug修复）
$ python scripts/bump_version.py patch
当前版本: 1.7.0
新版本:   1.7.1
✅ 版本号已提升

# 2. 提升次版本号（功能新增）
$ python scripts/bump_version.py minor
当前版本: 1.7.0
新版本:   1.8.0
✅ 版本号已提升

# 3. 指定具体版本
$ python scripts/bump_version.py 2.0.0
当前版本: 1.7.0
新版本:   2.0.0
✅ 版本号已提升

# 4. 试运行模式
$ python scripts/bump_version.py minor --dry-run
当前版本: 1.7.0
新版本:   1.8.0
🔍 试运行模式 - 不会实际修改文件
```

---

## ✅ 验证机制

### 1. 自动验证

```bash
# bump_version.py 执行后自动验证
python scripts/bump_version.py minor
# 输出:
# ✅ 版本文件已更新
# 🔍 验证版本号一致性...
# ✅ 版本号一致性验证通过
```

### 2. 手动验证

```bash
# 使用验证脚本
python scripts/verify_version_consistency.py

# 输出:
# 🔍 PlookingII 版本号一致性验证
# ============================================================
# 📌 规范版本号: 1.7.0
# ✅ 未发现硬编码版本号
# ✅ VERSION 正确导入
# ============================================================
# ✅ 版本号一致性验证通过！
```

### 3. CI/CD 集成

```yaml
# .github/workflows/ci.yml
version-check:
  runs-on: macos-latest
  steps:
    - name: 验证版本号一致性
      run: python scripts/verify_version_consistency.py
```

---

## 🎓 最佳实践

### ✅ DO（推荐）

1. **使用 bump_version.py 工具**
   ```bash
   python scripts/bump_version.py minor
   ```

2. **在代码中导入版本号**
   ```python
   from plookingII.__version__ import __version__
   ```

3. **遵循语义化版本规范**
   - 不兼容更新 → `major`
   - 功能新增 → `minor`
   - Bug修复 → `patch`

4. **更新 CHANGELOG**
   每次版本更新都记录变更内容

### ❌ DON'T（避免）

1. **不要手动修改版本号**
   ```python
   # ❌ 错误：手动硬编码
   VERSION = "1.7.0"
   ```

2. **不要在多个地方定义版本号**
   ```python
   # ❌ 错误：重复定义
   # constants.py
   VERSION = "1.7.0"
   
   # __init__.py
   __version__ = "1.7.0"
   ```

3. **不要跳过验证步骤**
   ```bash
   # ❌ 错误：不验证就推送
   git push origin main
   ```

---

## 🔄 版本号同步流程图

```
┌─────────────────────────────────────────────────────────┐
│              plookingII/__version__.py                  │
│                                                         │
│  __version__ = "1.7.0"  ← 🎯 唯一修改点               │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ 自动导入
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌───────────────┐         ┌───────────────┐
│ constants.py  │         │pyproject.toml │
│               │         │               │
│ from          │         │ dynamic =     │
│ __version__   │         │ ["version"]   │
│ import VERSION│         │               │
└───────┬───────┘         └───────────────┘
        │
        │ 自动导入
        │
        ▼
┌───────────────┐
│menu_controller│
│               │
│ from constants│
│ import VERSION│
└───────────────┘
```

**关键点**：
- 🎯 **单向依赖**：所有模块都从 `__version__.py` 导入
- ✅ **自动同步**：修改一处，全局生效
- 🚫 **无需手动**：不需要手动同步多个文件

---

## 🆚 V1 vs V2 对比

| 特性 | V1（旧方案） | V2（新方案） |
|------|-------------|-------------|
| **版本号定义** | 2个文件手动同步 | 1个文件自动同步 ✅ |
| **修改点** | `pyproject.toml` + `constants.py` | 仅 `__version__.py` ✅ |
| **自动化** | 需要 semantic-release | 内置 bump_version.py ✅ |
| **验证** | 手动运行脚本 | 自动验证 ✅ |
| **易用性** | 中等 | 优秀 ✅ |
| **错误风险** | 容易遗漏同步 | 零风险 ✅ |

---

## 📚 相关文档

- [语义化版本规范](https://semver.org/lang/zh-CN/)
- [PEP 621 - 项目元数据](https://peps.python.org/pep-0621/)
- [PEP 440 - 版本识别](https://peps.python.org/pep-0440/)

---

## 🎉 总结

**V2.0 智能版本管理系统**实现了：

✅ **真正的单一真源**：版本号只在 `__version__.py` 定义  
✅ **完全自动化**：使用 `bump_version.py` 一键提升  
✅ **零手动同步**：所有地方自动导入最新版本  
✅ **内置验证**：自动检查版本一致性  
✅ **开发友好**：清晰的工具和文档  
✅ **CI/CD就绪**：完整的自动化流程

**现在发布新版本，只需三步**：
```bash
1. python scripts/bump_version.py minor
2. 更新 CHANGELOG.md
3. git commit && git tag && git push
```

---

**PlookingII Team**  
*2025年10月6日*

