# PlookingII 项目文档

欢迎来到 PlookingII 项目文档中心。本文档提供了项目的完整文档导航。

## 📚 文档结构

### ⚡ [性能优化](PERFORMANCE_OPTIMIZATION_PLAN_2026.md) ⭐

当前性能优化路线图与本轮迭代记录

- [性能优化后续计划（P2/P3）](PERFORMANCE_OPTIMIZATION_PLAN_2026.md) - 进阶与长期优化路线图 ⭐
- [性能优化机会分析](PERFORMANCE_OPTIMIZATION_OPPORTUNITIES.md) - 历史优化分析（归档）

### 🏗️ [架构文档](architecture/)

项目架构设计与开发历程记录

- **[架构简化](architecture/simplification/)** - 架构简化记录（历史归档）

  - [简化计划](architecture/simplification/plan.md) - 详细的架构简化方案
  - [简化总结](architecture/simplification/summary.md) - 架构简化成果总结
  - [简化索引](architecture/simplification/index.md) - 简化相关文档索引
  - [简化进度](architecture/simplification/progress.md) - 实时进度跟踪
  - [完成报告](architecture/simplification/completed.md) - 阶段性完成报告

- **[开发阶段](architecture/phases/)** - 各个开发阶段的详细记录（归档）

  - [Phase 2: 加载简化](architecture/phases/phase2-loading.md)
  - [Phase 3: 监控简化](architecture/phases/phase3-monitor.md)
  - [Phase 4-5-6: 综合优化](architecture/phases/phase4-5-6-plan.md)

### 👨‍💻 [开发文档](development/)

开发指南、工具使用和最佳实践

- [快速开始指南](development/quick-start.md) - 快速了解项目架构和使用
- [macOS 清理指南](development/macos-cleanup.md) - 开发环境隐私保护
- **[版本管理](development/version-management/)** - 版本号管理体系
  - [V2 指南](development/version-management/guide-v2.md) - 智能版本管理系统 V2.0 ⭐
  - [自动更新机制](development/version-management/auto-update.md) - 版本号自动更新说明
  - [管理报告](development/version-management/report.md) - 版本统一管理报告
  - [统一总结](development/version-management/unification.md) - 版本统一实施总结
  - [V1 指南](development/version-management/guide-v1.md) - 旧版版本管理指南（已废弃）

### 📊 [项目报告](reports/)

各类评估报告、审计报告和总结文档

- [技术质量审计报告](TECHNICAL_QUALITY_AUDIT_REPORT.md) - 完整技术质量审计
- [质量审计摘要](QUALITY_AUDIT_SUMMARY.md) - 审计结论摘要
- [技术自审报告](TECHNICAL_SELF_REVIEW_2026-08-05.md) - 最新技术自审

### 🚀 [发布记录](releases/)

各个版本的发布说明和更新日志

- [完整变更日志](../CHANGELOG.md) - 当前版本与历史版本记录
- 早期版本发布说明（归档）：[v1.7.1](releases/v1.7.1.md) / [v1.7.0](releases/v1.7.0.md)

### 🔧 [修复记录](fixes/)

重要问题的修复记录和解决方案（归档）

- [图片显示修复](fixes/image-display-fix.md)
- [图片显示完整修复](fixes/image-display-complete-fix.md)
- [启动问题修复](fixes/startup-fix.md)
- [UI 对话框更新](fixes/ui-dialog-update.md)

## 🔍 快速查找

### 我想了解...

- **项目概览** → 查看根目录 [README.md](../README.md)
- **性能优化** → [性能优化后续计划](PERFORMANCE_OPTIMIZATION_PLAN_2026.md) ⭐
- **如何使用** → [快速开始指南](development/quick-start.md)
- **架构设计** → [架构文档](architecture/)
- **版本管理** → [版本管理 V2 指南](development/version-management/guide-v2.md)
- **发布历史** → [CHANGELOG.md](../CHANGELOG.md) 或 [发布记录](releases/)
- **安全性** → [项目报告](reports/)（安全审计结论见 [CI 安全检查流程](../.github/workflows/security.yml)）
- **生产部署** → [项目报告](reports/)（生产就绪评估）
- **历史质量审计** → [质量审计报告](QUALITY_AUDIT_SUMMARY.md)（归档）

## 📝 文档维护

### 文档组织原则

1. **根目录保持简洁** - 仅保留核心文档（README、CHANGELOG、LICENSE）
1. **分类清晰** - 所有文档按类型归档到相应目录
1. **命名规范** - 使用小写字母和连字符，避免空格和特殊字符
1. **及时归档** - 临时文档和过程文档完成后及时归档
1. **保持更新** - 定期检查和更新文档内容

### 添加新文档

添加新文档时，请遵循以下步骤：

1. 确定文档类型和归属目录
1. 使用规范的文件命名
1. 在相应目录的 README 中添加索引
1. 在本文档中更新导航链接

### 文档规范

- 使用 Markdown 格式
- 文件名使用小写字母和连字符（kebab-case）
- 添加适当的标题层级和目录
- 包含创建/更新日期和版本信息
- 使用表情符号提升可读性（适度使用）

## 🤝 贡献

欢迎对文档提出改进建议！请参考 [贡献指南](../CONTRIBUTING.md)（如存在）。

______________________________________________________________________

**文档版本**: 1.1
**最后更新**: 2026-08-04
**维护者**: PlookingII Team
