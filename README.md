# PlookingII

macOS 原生图片浏览器 - 高性能、智能化的图片浏览体验

[![CI](https://github.com/onlyhooops/plookingII/actions/workflows/ci.yml/badge.svg)](https://github.com/onlyhooops/plookingII/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/onlyhooops/plookingII/branch/main/graph/badge.svg)](https://codecov.io/gh/onlyhooops/plookingII)
[![Security](https://github.com/onlyhooops/plookingII/actions/workflows/security.yml/badge.svg)](https://github.com/onlyhooops/plookingII/actions/workflows/security.yml)
[![Release](https://github.com/onlyhooops/plookingII/actions/workflows/release.yml/badge.svg)](https://github.com/onlyhooops/plookingII/actions/workflows/release.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/linter-ruff-brightgreen.svg)](https://github.com/astral-sh/ruff)

## 🚀 快速开始

### 安装使用

1. 下载最新版本：[Releases](https://github.com/onlyhooops/plookingII/releases)
2. 解压并运行 `PlookingII.app`
3. 拖拽文件夹到窗口开始浏览

### 系统要求

> **⚠️ 平台限制**: 本应用专为 **macOS x86 (Intel)** 架构设计开发，使用了 PyObjC、AppKit、Quartz 等 macOS 原生框架，**不支持跨平台**运行。

- **操作系统**: macOS 10.15 (Catalina) 或更高版本
- **架构**: Intel x86_64（不支持 Apple Silicon M1/M2，不支持 Linux/Windows）
- **Python**: 3.11 或更高
- **内存**: 建议 4GB 以上
- **存储**: 至少 100MB 可用空间
- **网络**: 支持 SMB 远程存储访问

### 基本操作

- **左右箭头键** - 切换图片
- **空格键** - 拖拽移动图片
- **Cmd+R** - 在Finder中显示当前图片
- **右键** - 打开方式菜单

## 📚 文档导航

> **💡 提示**: 完整的文档体系请访问 [docs/README.md](docs/README.md)

### 🏗️ 架构与性能

- **[架构文档](docs/architecture/)** - 架构设计、简化记录与开发阶段归档
- **[性能优化后续计划](docs/PERFORMANCE_OPTIMIZATION_PLAN_2026.md)** - P2/P3 优化路线图 ⭐
- **[性能优化机会分析](docs/PERFORMANCE_OPTIMIZATION_OPPORTUNITIES.md)** - 历史优化分析记录

### 👨‍💻 开发文档

- **[开发指南](docs/development/)** - 开发环境和工具使用
  - [快速开始](docs/development/quick-start.md) - 架构快速了解
  - [版本管理 V2](docs/development/version-management/guide-v2.md) - 智能版本管理系统 ⭐
  - [macOS 清理指南](docs/development/macos-cleanup.md) - 开发环境隐私保护

### 📊 项目报告

- **[评估报告](docs/reports/)** - 各类评估和审计报告
  - [技术质量审计报告](docs/TECHNICAL_QUALITY_AUDIT_REPORT.md) - 完整技术质量审计
  - [质量审计摘要](docs/QUALITY_AUDIT_SUMMARY.md) - 审计结论摘要

### 🚀 发布记录

- **[完整变更日志](CHANGELOG.md)** - 当前版本与历史版本的详细记录
- **[历史发布说明](docs/releases/)** - 早期版本发布说明（归档）

## ✨ 核心特性

- **Quartz-only处理** - 完全基于macOS原生Quartz框架
- **Preview.app风格懒解码** - 大图毫秒级加载，按需解码屏幕可见区域
- **CGImage直通渲染** - 零拷贝渲染，提升显示性能
- **自适应性能调优** - 实时监控性能，动态调整参数
- **智能缓存系统** - 统一LRU缓存，基于实际像素内存的精确淘汰策略，
  配合 HOT3 强引用与双向预加载保证翻页零延迟
- **目录级图片列表缓存** - 文件夹切换不再重复全量枚举与排序，以目录 mtime 自动失效
- **内嵌性能跟踪** - 低开销聚合图片显示、导航、文件夹扫描/跳转等关键指标，
  每次运行只生成一份完整会话报告（周期自动落盘与退出落盘合并覆盖同一文件，
  含操作统计/慢事件/内存曲线，默认 `~/Library/Logs/PlookingII/perf`），
  便于后续性能分析与优化
- **异步文件夹跳转** - 跨界翻页后台加载，大文件夹/网络盘不冻结 UI
- **内存安全** - 自动内存监控和分级清理，防止长期运行性能退化
- **高效元数据预热** - 后台批量读取图片尺寸，导航热路径零磁盘 I/O
- **拖拽文件夹支持** - 直接从Finder拖拽文件夹浏览
- **系统级右键菜单** - 支持跳转到其他图片编辑工具

> **关于图片方向**：本项目**不处理 EXIF 方向信息**。待筛选的图片集请在
> 进入筛选流程前由外部工作流统一纠正朝向，项目专注照片的浏览与筛选。

## 🛠️ 技术架构

```
plookingII/
├── app/                    # 应用程序层
├── core/                   # 核心业务逻辑
├── ui/                     # 用户界面层
├── config/                 # 配置管理
├── services/               # 服务层
├── monitor/                # 性能与内存监控
├── utils/                  # 通用工具
└── db/                     # 数据访问层
```

## 📈 性能指标

- **图像加载**: Preview.app 风格懒解码，大图毫秒级加载、按需解码可见区域
- **翻页流畅度**: next-ready 双缓冲 + HOT3 强引用 + 双向预加载，回退零延迟
- **主线程开销**: 导航热路径零磁盘 I/O（元数据预热 + 精选计数缓存 + 目录列表缓存）
- **内存使用**: 智能 LRU 缓存，基于实际像素内存精确记账，分级清理防退化
- **测试**: 全量单元 + 集成测试（1400+ 用例），覆盖率门槛 45%（pytest.ini）

## 🔧 开发环境

### 系统要求

- macOS 10.15+
- Python 3.11+
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
make test           # 运行全部测试（pytest，覆盖率门槛 45%）
make lint           # 代码检查
make format         # 代码格式化
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

**PlookingII Team** © 2025-2026
**当前版本**: v2.5.6
**最后更新**: 2026-08-04
