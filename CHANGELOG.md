# Changelog

All notable changes to PlookingII will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### 🎯 Planned
- 实施UI与业务逻辑分离架构重构（v2.0计划）
- API 文档自动生成（Sphinx）
- 多 Python 版本支持测试
- 语义化版本自动发布

---

## [1.5.0] - 2025-10-04

### 🎯 主要变更
- **重大里程碑**: 完成测试系统全面升级，为架构重构做准备
- **测试覆盖率**: 从 33.03% 提升至 36.67% (+3.64%)
- **测试重构**: 测试数量从 1403 减少到 615，提升测试质量和效率
- **架构规划**: 发布《UI与业务逻辑分离架构改进提案》

### ✨ Added
- 完整的测试系统重构（单元测试 + 集成测试）
- 新增 615 个高质量测试用例（替代原 1403 个低质量测试）
- 测试超时保护机制（单个测试 30s，总运行 10m）
- 测试系统完整文档（快速开始、部署报告、文件清单）
- UI与业务逻辑分离架构提案（v2.0 规划文档）
- GitHub 工作流优化（CI/CD 改进）

### 🔧 Changed
- 重构测试架构：从混乱的测试文件到规范的 `tests/{unit,integration}` 结构
- 优化测试运行速度：从 75s 降至约 30s
- 提升测试 ROI：从 0.22% per test 提升至 0.59% per test（2.7倍提升）
- 改进核心模块测试覆盖率（多个模块提升至 70%+）
- 清理过时和重复测试文件（移除 60+ 个过时测试文件）

### 📋 Documentation
- 新增 `TESTING_QUICKSTART.md` - 测试快速入门指南
- 新增 `TEST_SYSTEM_SUMMARY.md` - 测试系统完整总结
- 新增 `TEST_SYSTEM_FILES.md` - 测试文件清单
- 新增 `测试系统部署报告.md` - 中文测试部署文档
- 新增 `docs/architecture/UI_BUSINESS_SEPARATION_PROPOSAL.md` - 架构改进提案
- 新增 `docs/testing/` 目录 - 完整测试文档集合

### 🚀 Performance
- 测试运行时间优化：75s → ~30s（60% 提升）
- 测试效率提升：每个测试平均覆盖率贡献提升 2.7 倍
- 移除低质量测试，专注高价值测试

### 🔒 Quality
- 引入 Bandit 安全扫描
- 引入 Ruff 代码质量检查
- 完善类型注解和文档字符串
- 改进错误处理和边界条件测试

### 📊 Test Coverage Details

#### 整体覆盖率
- **Total**: 33.03% → 36.67% (+3.64%)
- **Tests**: 1403 → 615 (-788, 提升质量)
- **ROI**: 0.22% → 0.59% per test (+2.7x)

#### 模块提升亮点
- `core/functions.py`: 95.39% (+65.66%)
- `core/cleanup_utils.py`: 93.01% (新模块)
- `core/optimized_algorithms.py`: 87.50% (新模块)
- `core/cache/adapters.py`: 77.61% (+39.85%)
- `core/threading.py`: 66.45% (+18.10%)
- `core/session_manager.py`: 61.74% (新模块)

### 🎯 Next Steps
准备实施 v2.0 架构重构：
1. Phase 1: 领域模型层 + 服务层（2周）
2. Phase 2: Presenter 层实现（2周）
3. Phase 3: 集成与迁移（1.5周）
4. Phase 4: 优化与完善（1周）

---

## [1.4.0] - 2025-10-02

### 🎯 主要变更
- **架构优化**: 移除6个弃用模块，统一配置和监控系统
- **代码清理**: 完成架构重构，消除重复实现
- **兼容性**: 保持向后兼容，提供平滑迁移路径

### ✅ Removed
- `plookingII.core.unified_config` → 使用 `plookingII.config.manager`
- `plookingII.core.simple_config` → 使用 `plookingII.config.manager`
- `plookingII.monitor.memory` → 使用 `plookingII.monitor.unified_monitor`
- `plookingII.monitor.performance` → 使用 `plookingII.monitor.unified_monitor`
- `plookingII.monitor.simplified_memory` → 使用 `plookingII.monitor.unified_monitor`
- `plookingII.core.cache_adapter` → 直接使用 `UnifiedCacheManager`

### 🔧 Changed
- 统一配置管理接口
- 整合监控系统
- 简化缓存架构
- 提升代码质量

### 📋 Documentation
- 新增迁移指南 `MIGRATION_GUIDE.md`
- 新增迁移完成报告 `MIGRATION_COMPLETION_REPORT.md`
- 更新架构验证报告 `ARCHITECTURE_VERIFICATION_REPORT.md`
- 完善文档目录结构

### 🚨 Breaking Changes
无 - 所有变更都保持向后兼容

---

## [1.3.1] - 2025-09-20

### 🎯 版本重点
- **废弃内容清理**: 移除过时代码和文档
- **文档整理**: 规范化项目文档结构
- **工具集补充**: 完善开发和维护工具

### ✅ Added
- 完整的项目文档和工具集
- GitHub 仓库地址更新

### 🔧 Changed
- 清理废弃代码和文档
- 规范化文档目录结构

---

## [1.2.5] - 2025-09-15

### 🎯 版本重点
竖向图片性能优化版本

### ✨ Added
- 竖向图片智能优化处理
- 超大像素图片渐进式加载
- 竖向图片预加载优化
- 内存优化策略

### 🔧 Changed
- 优化竖向图片显示性能
- 改进内存管理策略

### 🐛 Fixed
- 修复竖向图片显示问题
- 优化大尺寸图片加载性能

---

## [1.2.4] - 2025-09-10

### 🎯 版本重点
UI 文案统一管理与 Dock 菜单修复

### ✨ Added
- UI 文案统一管理系统
- 国际化支持基础架构

### 🔧 Changed
- 统一应用内所有文案管理
- 改进 Dock 菜单交互

### 🐛 Fixed
- 修复 Dock 菜单历史文件夹错误
- 修复文案显示不一致问题

---

## [1.2.3] - 2025-09-05

### 🎯 版本重点
技术债治理、可观测性、测试、CI 和文档完善

### ✨ Added
- 技术债管理机制
- 可观测性增强
- 完善测试套件
- CI/CD 流程优化

### 🔧 Changed
- 统一"精选"文件夹创建逻辑
- 防止遗留"保留"路径问题
- 修正打包脚本路径
- 同步报告文档位置

### 📋 Documentation
- 完善开发者文档
- 更新维护指南
- 补充测试文档

---

## [1.2.2] - 2025-08-30

### 🎯 版本重点
热修复和重大重构

### 🐛 Fixed
- 关键 bug 修复
- 性能问题修复
- UI 交互问题修复

### 🔧 Changed
- 架构重构优化
- 代码质量提升

---

## [1.2.1] - 2025-08-25

### 🎯 版本重点
实验性侧边栏功能

### ✨ Added
- 实验性侧边栏功能
- 文件夹导航增强

### 🔧 Changed
- UI 布局优化
- 交互体验改进

---

## [1.2.0] - 2025-08-20

### 🎯 版本重点
重大功能更新和性能优化

### ✨ Added
- 新增核心功能
- 性能监控系统
- 缓存优化机制

### 🔧 Changed
- 图像加载策略优化
- 内存管理改进
- UI 响应性提升

---

## [1.1.0] - 2025-07-15

### 🎯 版本重点
功能增强和稳定性提升

### ✨ Added
- EXIF 方向自动修正
- 智能缓存系统
- 拖拽文件夹支持

### 🔧 Changed
- Quartz 渲染引擎优化
- 内存使用优化

### 🐛 Fixed
- 图像加载问题修复
- UI 显示问题修复

---

## [1.0.0] - 2025-06-01

### 🎉 首次发布

PlookingII 正式发布！一款专为 macOS 设计的原生图片浏览器。

### ✨ Core Features
- **Quartz-only 处理**: 完全基于 macOS 原生 Quartz 框架
- **高性能渲染**: CGImage 直通渲染，零拷贝
- **智能缓存**: 多层缓存架构，LRU 淘汰策略
- **自适应优化**: 实时性能监控，动态参数调整
- **原生体验**: macOS 原生 UI，完美融入系统

### 📋 Supported Formats
- JPEG/JPG
- PNG

### 🛠️ Technical Stack
- Python 3.11+
- PyObjC + Cocoa
- Quartz 2D
- pytest + coverage

---

## Legend

- 🎯 主要变更
- ✨ 新功能 (Added)
- 🔧 改进 (Changed)
- 🐛 修复 (Fixed)
- ✅ 移除 (Removed)
- 🚨 破坏性变更 (Breaking Changes)
- 🔒 安全 (Security)
- 📋 文档 (Documentation)
- ⚡ 性能 (Performance)

[Unreleased]: https://github.com/onlyhooops/plookingII/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/onlyhooops/plookingII/compare/v1.3.1...v1.4.0
[1.3.1]: https://github.com/onlyhooops/plookingII/compare/v1.2.5...v1.3.1
[1.2.5]: https://github.com/onlyhooops/plookingII/compare/v1.2.4...v1.2.5
[1.2.4]: https://github.com/onlyhooops/plookingII/compare/v1.2.3...v1.2.4
[1.2.3]: https://github.com/onlyhooops/plookingII/compare/v1.2.2...v1.2.3
[1.2.2]: https://github.com/onlyhooops/plookingII/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/onlyhooops/plookingII/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/onlyhooops/plookingII/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/onlyhooops/plookingII/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/onlyhooops/plookingII/releases/tag/v1.0.0

