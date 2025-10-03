# PlookingII

macOS 原生图片浏览器 - 高性能、智能化的图片浏览体验

[![CI](https://github.com/onlyhooops/plookingII/workflows/CI/badge.svg)](https://github.com/onlyhooops/plookingII/actions/workflows/ci.yml)
[![Documentation](https://github.com/onlyhooops/plookingII/workflows/Documentation/badge.svg)](https://github.com/onlyhooops/plookingII/actions/workflows/docs.yml)
[![codecov](https://codecov.io/gh/onlyhooops/plookingII/branch/main/graph/badge.svg)](https://codecov.io/gh/onlyhooops/plookingII)
[![Python 3.9-3.12](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## 🚀 快速开始

### 安装使用
1. 下载最新版本：[Releases](https://github.com/your-username/plookingII/releases)
2. 解压并运行 `PlookingII.app`
3. 拖拽文件夹到窗口开始浏览

### 基本操作
- **左右箭头键** - 切换图片
- **空格键** - 拖拽移动图片
- **Cmd+R** - 在Finder中显示当前图片
- **Cmd+Option+R/L** - 向右/左旋转90度
- **右键** - 打开方式菜单

## 📚 文档导航

### 👥 用户文档
- **[用户指南](docs/user/guides/README.md)** - 详细使用说明
- **[项目概览](docs/user/guides/PROJECT_OVERVIEW.md)** - 功能特性介绍
- **[拖拽功能](docs/user/guides/DRAG_DROP_FEATURE.md)** - 拖拽文件夹使用指南
- **[迁移指南](docs/user/guides/MIGRATION_GUIDE.md)** - 版本升级指南
- **[未来规划](docs/user/guides/FUTURE_ROADMAP.md)** - 功能路线图

### 👨‍💻 开发者文档
- **[技术指南](docs/developer/TECHNICAL_GUIDE.md)** - 完整技术实现
- **[开发者指南](docs/developer/DEVELOPER_GUIDE.md)** - 开发环境搭建
- **[架构设计](docs/architecture/design/ARCHITECTURE.md)** - 系统架构文档
- **[维护指南](docs/developer/MAINTENANCE_GUIDELINES.md)** - 项目维护规范
- **[贡献指南](docs/developer/contributing/CONTRIBUTING.md)** - 如何参与贡献

### 📊 项目报告
- **[版本历史](docs/reports/releases/UNIFIED_VERSION_HISTORY.md)** - 完整版本记录
- **[测试覆盖率](docs/reports/coverage/)** - 测试覆盖率报告
- **[性能报告](docs/reports/performance/)** - 性能优化报告
- **[项目报告](docs/reports/)** - 其他项目报告

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

欢迎贡献代码！请查看 [贡献指南](docs/developer/contributing/CONTRIBUTING.md) 了解如何参与。

## 📞 支持

- 问题反馈：[GitHub Issues](https://github.com/your-username/plookingII/issues)
- 功能建议：[GitHub Discussions](https://github.com/your-username/plookingII/discussions)

---

**PlookingII Team** © 2025  
**当前版本**: v1.4.0  
**最后更新**: 2025-09-30
