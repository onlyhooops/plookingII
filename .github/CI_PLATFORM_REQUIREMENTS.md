# CI 平台要求说明

## 🍎 项目特性

PlookingII 是一个 **macOS x86 (Intel) 专用应用**，使用了以下 macOS 专用框架：
- **PyObjC**: Python 与 Objective-C 桥接
- **AppKit**: macOS 原生 UI 框架
- **Quartz**: macOS 图形渲染框架
- **Cocoa**: macOS 应用开发框架

**不支持跨平台**：不支持 Windows、Linux 或 Apple Silicon (M1/M2)。

---

## 📋 CI 工作流平台配置

### 1. **ci.yml** - 主 CI 流程

| 作业 | 运行平台 | 说明 | 合理性 |
|------|---------|------|--------|
| `code-quality` | `ubuntu-latest` | 代码质量检查（ruff, flake8, mypy, bandit） | ✅ 静态分析工具，不需要运行代码 |
| `test-macos` | `macos-13` (x86) | macOS 专用测试套件 | ✅ **必须** 在 macOS x86 上运行 |
| `security` | `ubuntu-latest` | 依赖安全检查（safety, pip-audit） | ✅ 只检查依赖列表，不运行代码 |
| `build` | `macos-13` (x86) | 构建测试和版本验证 | ✅ **必须** 在 macOS x86 上运行 |
| `ci-success` | `ubuntu-latest` | CI 状态汇总 | ✅ 仅输出状态，任何平台均可 |

**Python 版本**：3.11 和 3.12

---

### 2. **pr-check.yml** - PR 快速检查

| 作业 | 运行平台 | 说明 |
|------|---------|------|
| `quick-check` | `ubuntu-latest` | 快速代码检查（ruff） |
| `pr-info` | `ubuntu-latest` | PR 信息显示 |

**说明**：PR 快速检查只进行静态分析，完整测试在合并后的 CI 流程中进行。

---

### 3. **security.yml** - 安全扫描

| 作业 | 运行平台 | 说明 |
|------|---------|------|
| `dependency-scan` | `macos-13` (x86) | 依赖安全扫描（safety） |
| `code-scan` | `macos-13` (x86) | 代码安全扫描（bandit） |
| `secret-scan` | `macos-13` (x86) | 密钥泄露扫描（trufflehog） |

**说明**：虽然这些扫描理论上可以在任何平台运行，但为保持环境一致性，统一使用 macOS x86。

---

### 4. **test-timeout-protection.yml** - 超时保护验证

| 作业 | 运行平台 | 说明 |
|------|---------|------|
| `verify-timeout` | `macos-13` (x86) | 验证 pytest 超时机制 |

**说明**：需要实际运行测试，**必须**在 macOS x86 上。

---

## ⚠️ 重要说明

### macOS 版本选择

- ✅ **macos-13**: Intel x86_64 架构（推荐）
- ❌ **macos-latest**: Apple Silicon (M1/M2) - **不兼容**
- ❌ **macos-12**: 虽然是 x86，但 GitHub 即将弃用

### 为什么不能使用 Ubuntu/Windows？

1. **PyObjC 依赖**：只能在 macOS 上安装和运行
2. **AppKit/Quartz**：macOS 专用系统框架
3. **UI 测试**：需要 macOS 窗口系统
4. **文件系统特性**：依赖 macOS 的文件系统行为

### 静态分析工具可以在 Ubuntu 上运行的原因

- **ruff, flake8, mypy**：纯 Python 静态分析工具
- **不执行代码**：只分析语法和类型
- **节省 CI 资源**：Ubuntu runner 比 macOS 便宜且更快

---

## 🔄 更新历史

- **2025-01-06**: 修正所有工作流为 macOS x86 专用配置
- **2025-01-06**: 移除 Ubuntu 测试任务
- **2025-01-06**: 更新 ruff 配置以适配 macOS 代码模式

---

## 📚 参考文档

- [GitHub Actions - macOS runners](https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners#supported-runners-and-hardware-resources)
- [PyObjC 文档](https://pyobjc.readthedocs.io/)
- [项目 README](../README.md)
