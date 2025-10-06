# 版本管理指南

PlookingII 采用自动化的语义化版本管理策略，确保版本号在整个项目中保持一致。

## 📋 目录

- [版本管理策略](#%E7%89%88%E6%9C%AC%E7%AE%A1%E7%90%86%E7%AD%96%E7%95%A5)
- [版本号格式](#%E7%89%88%E6%9C%AC%E5%8F%B7%E6%A0%BC%E5%BC%8F)
- [如何更新版本](#%E5%A6%82%E4%BD%95%E6%9B%B4%E6%96%B0%E7%89%88%E6%9C%AC)
- [开发者指南](#%E5%BC%80%E5%8F%91%E8%80%85%E6%8C%87%E5%8D%97)
- [CI/CD 集成](#cicd-%E9%9B%86%E6%88%90)
- [故障排除](#%E6%95%85%E9%9A%9C%E6%8E%92%E9%99%A4)

## 版本管理策略

### 单一真实来源（Single Source of Truth）

版本号只在以下位置定义：

1. **`plookingII/config/constants.py`** - 主版本号定义

   ```python
   VERSION = "1.6.0"
   APP_VERSION = VERSION  # 别名
   ```

1. **`pyproject.toml`** - 项目元数据

   ```toml
   [project]
   version = "1.6.0"
   ```

### 自动化更新

使用 [python-semantic-release](https://python-semantic-release.readthedocs.io/) 自动管理版本号：

- ✅ 根据 commit 信息自动计算新版本号
- ✅ 自动更新 `pyproject.toml` 和 `constants.py`
- ✅ 自动生成 `CHANGELOG.md`
- ✅ 自动创建 Git tags
- ✅ 自动发布 GitHub Release

### 配置文件

在 `pyproject.toml` 中的配置：

```toml
[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
version_variables = ["plookingII/config/constants.py:VERSION"]
branch = "main"
upload_to_pypi = false
upload_to_release = true
build_command = "python tools/package_release.py --build"
changelog_file = "CHANGELOG.md"
changelog_placeholder = "<!--next-version-->"
```

## 版本号格式

遵循 [Semantic Versioning 2.0.0](https://semver.org/) 规范：

```
MAJOR.MINOR.PATCH

例如: 1.6.0
```

### 版本号含义

- **MAJOR (主版本号)**: 不兼容的 API 修改
- **MINOR (次版本号)**: 向后兼容的功能新增
- **PATCH (修订号)**: 向后兼容的问题修正

### 版本号递增规则

| Commit 类型        | 触发的版本更新 | 示例          |
| ------------------ | -------------- | ------------- |
| `feat:`            | MINOR +1       | 1.6.0 → 1.7.0 |
| `fix:`             | PATCH +1       | 1.6.0 → 1.6.1 |
| `perf:`            | PATCH +1       | 1.6.0 → 1.6.1 |
| `BREAKING CHANGE:` | MAJOR +1       | 1.6.0 → 2.0.0 |

## 如何更新版本

### 方法一：语义化提交（推荐）

使用规范的 commit 信息，semantic-release 将自动处理：

```bash
# 新功能 (MINOR)
git commit -m "feat: 添加图片旋转功能"

# Bug 修复 (PATCH)
git commit -m "fix: 修复内存泄漏问题"

# 性能优化 (PATCH)
git commit -m "perf: 优化图片加载速度"

# 破坏性变更 (MAJOR)
git commit -m "feat!: 重构缓存 API

BREAKING CHANGE: 缓存接口发生重大变化"
```

### 方法二：手动更新（不推荐）

如果必须手动更新：

1. 更新 `pyproject.toml` 中的版本号
1. 更新 `plookingII/config/constants.py` 中的 VERSION
1. 运行验证：
   ```bash
   make verify-version
   ```

## 开发者指南

### 在代码中使用版本号

✅ **正确方式**：

```python
from plookingII.config.constants import VERSION

# 在日志中使用
logger.info(f"PlookingII version {VERSION} started")

# 在 UI 中显示
about_text = f"Version {VERSION}"

# 在功能中使用
if version_compare(VERSION, "1.5.0") >= 0:
    # 新功能代码
    pass
```

❌ **错误方式**：

```python
# 不要硬编码版本号
VERSION = "1.6.0"  # ❌

# 不要创建独立的版本变量
__version__ = "1.6.0"  # ❌

# 不要在文档字符串中硬编码
"""
Module documentation
Version: 1.6.0  # ❌
"""
```

### 版本号验证工具

我们提供了自动化工具来确保版本号一致性：

#### 1. 验证版本号一致性

```bash
# 使用 Makefile
make verify-version

# 或直接运行脚本
python3 scripts/verify_version_consistency.py
```

输出示例：

```
🔍 PlookingII 版本号一致性验证
============================================================
📌 规范版本号: 1.6.0

📋 验证 pyproject.toml...
   ✅ pyproject.toml 版本号一致

🔧 验证 semantic-release 配置...
   ✅ semantic-release 配置正确

🔍 检查硬编码版本号...
   ✅ 未发现硬编码版本号

📦 验证 VERSION 导入...
   ✅ VERSION 正确导入

============================================================
✅ 版本号一致性验证通过！
```

#### 2. 统一版本号（清理硬编码）

如果发现硬编码版本号，使用此工具清理：

```bash
# 使用 Makefile
make unify-version

# 或直接运行脚本
python3 scripts/unify_version.py
```

此工具会：

- 移除文档字符串中的硬编码版本号
- 删除独立的 `__version__` 变量
- 清理过时的版本号引用
- 自动运行验证检查

## CI/CD 集成

### GitHub Actions 工作流

版本号验证已集成到 CI 流程中：

```yaml
# .github/workflows/ci.yml
jobs:
  version-check:
    name: 版本号一致性验证
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: python3 scripts/verify_version_consistency.py
```

每次 push 和 PR 都会自动验证版本号一致性。

### 本地预提交检查

在提交前运行快速检查：

```bash
# 包含版本号验证的快速检查
make quick-check

# 完整的 CI 模拟（包含所有检查）
make ci
```

### Pre-commit Hook（可选）

创建 `.git/hooks/pre-commit` 文件：

```bash
#!/bin/sh
# 在提交前验证版本号一致性

echo "🔍 验证版本号一致性..."
python3 scripts/verify_version_consistency.py

if [ $? -ne 0 ]; then
    echo "❌ 版本号验证失败！"
    echo "💡 运行 'make unify-version' 修复问题"
    exit 1
fi

echo "✅ 版本号验证通过"
```

## 故障排除

### 问题 1: 版本号不一致

**症状**：

```
❌ 版本号不一致:
   constants.py: 1.6.0
   pyproject.toml: 1.5.0
```

**解决方案**：

1. 确定哪个是正确的版本号
1. 手动更新另一个文件使其一致
1. 运行 `make verify-version` 确认

### 问题 2: 发现硬编码版本号

**症状**：

```
❌ 发现 3 处硬编码版本号:
   - plookingII/core/cache.py: __version__ 变量
   - plookingII/ui/views.py: 文档字符串版本号
```

**解决方案**：

```bash
# 自动清理所有硬编码
make unify-version
```

### 问题 3: semantic-release 配置错误

**症状**：

```
❌ semantic_release 未配置更新 constants.py
```

**解决方案**：
检查 `pyproject.toml` 中的配置，确保包含：

```toml
[tool.semantic_release]
version_variables = ["plookingII/config/constants.py:VERSION"]
```

### 问题 4: CI 中版本验证失败

**解决方案**：

1. 在本地运行 `make verify-version`
1. 修复所有报告的问题
1. 提交修复并重新触发 CI

## 最佳实践

### ✅ DO（推荐做法）

- ✅ 使用语义化 commit 信息
- ✅ 让 semantic-release 自动管理版本
- ✅ 从 `constants.py` 导入 VERSION
- ✅ 在提交前运行 `make verify-version`
- ✅ 遵循 Semantic Versioning 规范

### ❌ DON'T（避免做法）

- ❌ 手动编辑版本号（除非必要）
- ❌ 在多个地方定义版本号
- ❌ 在文档字符串中硬编码版本
- ❌ 创建独立的 `__version__` 变量
- ❌ 跳过版本号验证

## 版本发布流程

### 自动发布（推荐）

1. 合并 PR 到 main 分支
1. semantic-release 自动：
   - 分析 commits
   - 计算新版本号
   - 更新版本文件
   - 生成 CHANGELOG
   - 创建 Git tag
   - 发布 GitHub Release
   - 构建并上传构建产物

### 手动发布（特殊情况）

```bash
# 1. 确保在 main 分支
git checkout main
git pull

# 2. 验证版本号
make verify-version

# 3. 手动触发 semantic-release
semantic-release publish

# 4. 或使用项目脚本
python3 tools/package_release.py --build --release
```

## 相关资源

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [python-semantic-release](https://python-semantic-release.readthedocs.io/)
- [项目 CHANGELOG](../CHANGELOG.md)
- [版本管理报告](../VERSION_MANAGEMENT_REPORT.md)

## 常见问题

### Q: 为什么使用自动化版本管理？

A: 自动化版本管理有以下优势：

- 减少人为错误
- 确保版本号一致性
- 自动生成 CHANGELOG
- 标准化发布流程
- 节省时间和精力

### Q: 如何触发 MAJOR 版本更新？

A: 在 commit 信息中添加 `BREAKING CHANGE:`：

```bash
git commit -m "feat!: 重构 API

BREAKING CHANGE: 修改了缓存接口的参数"
```

### Q: 可以手动编辑 CHANGELOG 吗？

A: 可以，但建议：

- 让 semantic-release 自动生成基础内容
- 手动添加详细说明和补充信息
- 不要删除自动生成的版本标记

### Q: 版本号验证会影响开发效率吗？

A: 不会。验证过程很快（通常 < 2秒），且可以：

- 及早发现版本号问题
- 避免发布时的意外
- 确保代码质量

______________________________________________________________________

**维护者**: PlookingII Team
**最后更新**: 2025-10-06
**文档版本**: 1.0.0
