# PlookingII

macOS 原生图片浏览器 - 高性能、智能化的图片浏览体验

[![CI](https://github.com/onlyhooops/plookingII/actions/workflows/ci.yml/badge.svg)](https://github.com/onlyhooops/plookingII/actions/workflows/ci.yml)
[![Documentation](https://github.com/onlyhooops/plookingII/actions/workflows/docs.yml/badge.svg)](https://github.com/onlyhooops/plookingII/actions/workflows/docs.yml)
[![codecov](https://codecov.io/gh/onlyhooops/plookingII/branch/main/graph/badge.svg)](https://codecov.io/gh/onlyhooops/plookingII)
[![Security](https://github.com/onlyhooops/plookingII/actions/workflows/security.yml/badge.svg)](https://github.com/onlyhooops/plookingII/actions/workflows/security.yml)
[![Release](https://github.com/onlyhooops/plookingII/actions/workflows/release.yml/badge.svg)](https://github.com/onlyhooops/plookingII/actions/workflows/release.yml)
[![Python 3.9-3.12](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## 🚀 快速开始

### 安装使用

1. 下载最新版本：[Releases](https://github.com/onlyhooops/plookingII/releases)
1. 解压并运行 `PlookingII.app`
1. 拖拽文件夹到窗口开始浏览

### 系统要求

> **⚠️ 平台限制**: 本应用专为 **macOS x86 (Intel)** 架构设计开发，使用了 PyObjC、AppKit、Quartz 等 macOS 原生框架，**不支持跨平台**运行。

- **操作系统**: macOS 10.15 (Catalina) 或更高版本
- **架构**: Intel x86_64（不支持 Apple Silicon M1/M2，不支持 Linux/Windows）
- **Python**: 3.11 或 3.12
- **内存**: 建议 4GB 以上
- **存储**: 至少 100MB 可用空间
- **网络**: 支持 SMB 远程存储访问

### 基本操作

- **左右箭头键** - 切换图片
- **空格键** - 拖拽移动图片
- **Cmd+R** - 在Finder中显示当前图片
- **Cmd+Option+R/L** - 向右/左旋转90度
- **右键** - 打开方式菜单

## 📚 文档导航

> **💡 提示**: 完整的文档体系请访问 [docs/README.md](docs/README.md)

### 🏗️ 架构文档

- **[架构简化文档](docs/architecture/)** - 架构设计和优化方案
  - [架构简化计划](docs/architecture/simplification/plan.md) - 详细优化方案
  - [架构简化总结](docs/architecture/simplification/summary.md) - 成果展示（代码减少93.1%）
  - [开发阶段记录](docs/architecture/phases/) - 各阶段详细记录

### 👨‍💻 开发文档

- **[开发指南](docs/development/)** - 开发环境和工具使用
  - [快速开始](docs/development/quick-start.md) - 架构快速了解
  - [版本管理 V2](docs/development/version-management/guide-v2.md) - 智能版本管理系统 ⭐
  - [macOS 清理指南](docs/development/macos-cleanup.md) - 开发环境隐私保护

### 📊 项目报告

- **[评估报告](docs/reports/)** - 各类评估和审计报告
  - [生产就绪报告](docs/reports/production-readiness.md) - 生产环境评估
  - [安全审计报告](docs/reports/security-audit.md) - 完整安全审计

### 🚀 发布记录

- **[版本历史](docs/releases/)** - 发布说明和更新日志
  - [v1.7.1 发布说明](docs/releases/v1.7.1.md) - 版本管理 V2.0
  - [v1.7.0 发布说明](docs/releases/v1.7.0.md) - 架构优化版本
  - [完整变更日志](CHANGELOG.md) - 所有版本的详细记录

## ✨ 核心特性

- **Quartz-only处理** - 完全基于macOS原生Quartz框架
- **EXIF方向自动修正** - 自动处理图像方向信息
- **CGImage直通渲染** - 零拷贝渲染，提升显示性能
- **自适应性能调优** - 实时监控性能，动态调整参数
- **智能缓存系统** - 多层缓存架构，LRU淘汰策略
- **拖拽文件夹支持** - 直接从Finder拖拽文件夹浏览
- **系统级右键菜单** - 支持跳转到其他图片编辑工具

## 🛠️ 技术架构

```
plookingII/
├── app/                    # 应用程序层
├── core/                   # 核心业务逻辑
├── ui/                     # 用户界面层
├── config/                 # 配置管理
├── services/               # 服务层
└── db/                     # 数据访问层
```

## 📈 性能指标

- **启动时间**: < 2秒
- **图像加载**: 小文件 < 100ms，大文件渐进式加载
- **缓存命中率**: > 80%
- **内存使用**: 动态调整，最大500MB
- **测试覆盖率**: 核心模块 80%+

## 🔧 开发环境

### 系统要求

- macOS 10.15+
- Python 3.9+ (支持 3.9, 3.10, 3.11, 3.12)
- Xcode Command Line Tools

### 快速开始

```bash
# 克隆项目
git clone https://github.com/onlyhooops/plookingII.git
cd plookingII

# 安装依赖
make install-dev

# 安装 pre-commit hooks
make pre-commit

# 运行测试
make test

# 构建应用
make build
```

### 开发工具

```bash
make help           # 查看所有可用命令
make test           # 运行测试（覆盖率 ≥60%）
make lint           # 代码检查
make format         # 代码格式化
make docs           # 生成 API 文档
make docs-serve     # 本地预览文档
make ci             # 模拟完整 CI 流程
```

### 提交代码

项目使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```bash
git commit -m "feat: add new feature"     # 新功能
git commit -m "fix: fix bug"              # Bug 修复
git commit -m "docs: update docs"         # 文档更新
git commit -m "refactor: refactor code"   # 代码重构
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🤝 贡献

欢迎贡献代码！提交问题或建议请访问 [GitHub Issues](https://github.com/onlyhooops/plookingII/issues)。

## 📞 支持

- 问题反馈：[GitHub Issues](https://github.com/onlyhooops/plookingII/issues)
- 功能建议：[GitHub Discussions](https://github.com/onlyhooops/plookingII/discussions)
- 安全报告：请通过 [GitHub Security Advisories](https://github.com/onlyhooops/plookingII/security/advisories) 报告安全问题

______________________________________________________________________

**PlookingII Team** © 2025
**当前版本**: v1.7.1
**最后更新**: 2025-10-14
