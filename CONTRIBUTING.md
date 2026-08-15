# 贡献指南

感谢您对 PlookingII 的关注与贡献！

## 🐛 报告问题

- 访问 [GitHub Issues](https://github.com/onlyhooops/plookingII/issues) 提交问题
- 请包含：操作系统版本、应用版本、复现步骤、预期行为与实际行为

## 💡 功能建议

- 访问 [GitHub Discussions](https://github.com/onlyhooops/plookingII/discussions) 讨论
- 描述使用场景与预期效果，便于评估

## 🔒 安全报告

请通过 [GitHub Security Advisories](https://github.com/onlyhooops/plookingII/security/advisories) 报告安全问题，不要公开披露。

## 🛠️ 提交代码

### 环境准备

```bash
make install-dev     # 安装依赖
make pre-commit      # 安装 pre-commit hooks
```

### 提交规范

项目遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```bash
git commit -m "feat: add new feature"     # 新功能
git commit -m "fix: fix bug"              # Bug 修复
git commit -m "docs: update docs"         # 文档更新
git commit -m "refactor: refactor code"   # 代码重构
```

### 提交前检查

```bash
make lint            # 代码检查（ruff + flake8）
make test            # 运行全部测试
make verify-version  # 验证版本号一致性
```

> **注意**：本应用为 macOS x86 专用，代码涉及 PyObjC/AppKit/Quartz。
> 修改 UI/渲染相关代码时请在 macOS 环境验证后再提交。

## 📄 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE)。
