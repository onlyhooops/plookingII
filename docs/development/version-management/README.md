# 版本管理文档

PlookingII 项目的版本号管理体系文档集合。

## 📁 文档列表

### ⭐ 当前使用（推荐）

- **[V2 指南](guide-v2.md)** - 智能版本管理系统 V2.0

  - 单一真源（SSOT）架构
  - 自动化版本提升工具
  - 动态版本读取机制
  - 完整使用指南

- **[自动更新机制](auto-update.md)** - 版本号自动更新说明

  - 自动更新原理
  - 配置说明
  - FAQ

### 📊 历史记录

- **[管理报告](report.md)** - 版本统一管理报告

  - 问题分析
  - 解决方案
  - 实施细节

- **[统一总结](unification.md)** - 版本号统一实施总结

  - 执行概览
  - 完成的工作
  - 验证结果

### 📜 已废弃

- **[V1 指南](guide-v1.md)** - 旧版版本管理方案
  - 仅供历史参考
  - 不推荐使用

## 🎯 版本管理 V2.0 概览

### 设计理念

**真正的单一真源（Single Source of Truth）**：

- 版本号**只在一个地方定义**：`plookingII/__version__.py`
- 所有其他地方**自动导入**，无需手动同步
- 发布新版本时**只需修改一个文件**

### 核心特性

✅ **单一真源**

```python
# plookingII/__version__.py
__version__ = "1.7.1"
__release_date__ = "2025-10-06"
```

✅ **自动化工具**

```bash
# 版本提升工具
python scripts/bump_version.py patch  # 1.7.1 → 1.7.2
python scripts/bump_version.py minor  # 1.7.1 → 1.8.0
python scripts/bump_version.py major  # 1.7.1 → 2.0.0
python scripts/bump_version.py 2.0.0  # 指定版本
```

✅ **动态读取**

```toml
# pyproject.toml
[project]
dynamic = ["version"]

[tool.setuptools.dynamic]
version = {attr = "plookingII.__version__.__version__"}
```

### V1 vs V2 对比

| 特性           | V1                  | V2                    |
| -------------- | ------------------- | --------------------- |
| 版本定义位置   | `constants.py`      | `__version__.py`      |
| 其他模块       | 导入 `constants.py` | 导入 `__version__.py` |
| pyproject.toml | 导入 `constants.py` | 动态读取（PEP 621）   |
| 版本提升       | 手动修改            | 自动化工具            |
| 一致性验证     | 手动                | 内置验证              |
| 符合标准       | 部分                | 完全符合 PEP 621      |

## 🚀 快速使用

### 查看当前版本

```python
from plookingII.__version__ import __version__, __release_date__

print(f"版本: {__version__}")
print(f"发布日期: {__release_date__}")
```

### 发布新版本

```bash
# 1. 提升版本号
python scripts/bump_version.py patch

# 2. 提交更改
git add plookingII/__version__.py
git commit -m "chore: bump version to x.x.x"

# 3. 创建标签
git tag vx.x.x

# 4. 推送
git push && git push --tags
```

### 验证版本一致性

```bash
python scripts/verify_version_consistency.py
```

## 📚 详细文档

- **完整使用指南** → [V2 指南](guide-v2.md)
- **自动更新原理** → [自动更新机制](auto-update.md)
- **历史记录** → [管理报告](report.md) 和 [统一总结](unification.md)

## 🔗 相关资源

- [PEP 621 - Storing project metadata in pyproject.toml](https://peps.python.org/pep-0621/)
- [Semantic Versioning 2.0.0](https://semver.org/)
- [项目 CHANGELOG](../../../CHANGELOG.md)

______________________________________________________________________

**版本**: 2.0
**最后更新**: 2025-10-14
**状态**: ✅ 生产就绪
