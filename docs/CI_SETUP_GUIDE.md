# GitHub CI 配置指南

## 📋 问题复盘

### 原始问题
项目一直无法通过 GitHub CI 测试，经过排查发现：

**根本原因：项目缺少 GitHub Actions 配置文件**

项目目录中完全没有 `.github/workflows/` 目录和任何 CI 配置文件，导致 GitHub 无法运行自动化测试。

## ✅ 解决方案

### 1. 新增的文件

已创建以下 CI/CD 配置文件：

```
.github/
├── workflows/
│   ├── ci.yml           # 主 CI 工作流
│   └── pr-check.yml     # PR 快速检查
├── dependabot.yml       # 依赖自动更新
.pre-commit-config.yaml  # Pre-commit hooks
```

### 2. CI 工作流说明

#### 主 CI 工作流 (`ci.yml`)

**触发条件：**
- Push 到 `main` 或 `develop` 分支
- Pull Request 到 `main` 或 `develop` 分支
- 手动触发

**包含的检查任务：**

1. **代码质量检查** (`code-quality`)
   - Ruff 代码检查和格式检查
   - Flake8 补充检查
   - Mypy 类型检查（警告模式）
   - Bandit 安全扫描

2. **Ubuntu 环境测试** (`test-ubuntu`)
   - Python 3.9, 3.10, 3.11, 3.12 多版本测试
   - 跳过 macOS 特定的 UI 测试
   - 生成测试覆盖率报告
   - 上传到 Codecov

3. **macOS 环境测试** (`test-macos`)
   - Python 3.11 完整测试
   - 包含 PyObjC 和 UI 相关测试
   - 验证 macOS 框架可用性

4. **安全检查** (`security`)
   - Safety 依赖安全扫描
   - Pip-audit 漏洞检查

5. **构建测试** (`build`)
   - 仅在 main 分支 push 时运行
   - 验证版本一致性
   - 测试应用构建

#### PR 快速检查 (`pr-check.yml`)

**目的：** 为 PR 提供快速反馈（3-5 分钟内完成）

**检查内容：**
- Ruff 代码检查和格式检查
- 基础单元测试（跳过慢速测试）
- PR 信息摘要

**优势：**
- 快速反馈周期
- 自动取消过期的检查
- 降低 CI 资源消耗

### 3. 测试策略优化

#### 环境适配

项目的 `tests/conftest.py` 已包含 CI 环境检测：

```python
@pytest.fixture(scope="session")
def is_ci() -> bool:
    """检测是否在CI环境中运行"""
    return os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
```

#### 测试标记

在 CI 环境中会自动处理以下标记：

- `@pytest.mark.skip_ci`: 在 CI 中跳过
- `@pytest.mark.ui`: 需要显示环境（Linux 上自动跳过）
- `@pytest.mark.slow`: 慢速测试（需要 `--run-slow` 选项）
- `@pytest.mark.flaky`: 不稳定测试（需要 `--run-flaky` 选项）

#### CI 测试命令

```bash
# Ubuntu 环境
pytest tests/ \
  -v \
  -m "not ui and not skip_ci" \
  --tb=short \
  --cov=plookingII \
  --cov-report=xml \
  --maxfail=5 \
  --timeout=60

# macOS 环境
pytest tests/ \
  -v \
  -m "not skip_ci" \
  --tb=short \
  --cov=plookingII \
  --cov-report=xml \
  --maxfail=5 \
  --timeout=60
```

### 4. 依赖管理

#### Dependabot 配置

自动化依赖更新：
- **Python 依赖**: 每周一检查
- **GitHub Actions**: 每月检查
- 自动创建 PR
- 限制同时打开的 PR 数量

#### Pre-commit Hooks

本地代码质量保护：

```bash
# 安装
pip install pre-commit
pre-commit install

# 运行
pre-commit run --all-files
```

**包含的检查：**
- Ruff linting 和格式化
- 文件基础检查（行尾空格、文件结尾等）
- Python 特定检查
- Bandit 安全检查

## 🚀 使用指南

### 本地开发流程

1. **安装开发依赖**
   ```bash
   make install-dev
   make pre-commit
   ```

2. **开发前快速检查**
   ```bash
   make quick-check
   ```

3. **提交前完整检查**
   ```bash
   make ci
   ```

4. **运行特定测试**
   ```bash
   # 只运行单元测试
   pytest tests/unit/ -v

   # 跳过 UI 测试
   pytest -m "not ui" -v

   # 运行慢速测试
   pytest --run-slow -v
   ```

### CI 环境变量

CI 会自动设置以下环境变量：

- `CI=true`: 标识 CI 环境
- `GITHUB_ACTIONS=true`: 标识 GitHub Actions
- `PYTEST_CURRENT_TEST`: 当前测试标识

### 查看 CI 状态

1. **在 GitHub 仓库页面**
   - 访问 `Actions` 标签
   - 查看工作流运行历史

2. **在 PR 中**
   - 每个 PR 会显示检查状态
   - 点击 "Details" 查看详细日志

3. **CI 徽章**（可选添加到 README）
   ```markdown
   ![CI](https://github.com/your-username/plookingII/workflows/CI/badge.svg)
   ```

## 🔧 常见问题

### 1. 测试在 CI 中失败但本地通过

**可能原因：**
- 依赖版本差异
- 操作系统差异
- 环境变量差异

**解决方法：**
```bash
# 模拟 CI 环境
export CI=true
make ci
```

### 2. macOS 测试失败

**注意：** macOS runner 是有限资源

**调试方法：**
- 检查 PyObjC 依赖是否正确安装
- 使用 `@pytest.mark.skip_ci` 标记 macOS 特定的测试
- 在本地 macOS 上测试

### 3. 测试超时

**默认超时：** 60 秒/测试，300 秒/全局

**解决方法：**
```python
@pytest.mark.timeout(120)  # 单个测试 120 秒
def test_slow_operation():
    pass

@pytest.mark.slow  # 标记为慢速测试
def test_very_slow():
    pass
```

### 4. 覆盖率不达标

**当前阈值：** 60%

**查看报告：**
```bash
make test-coverage
open htmlcov/index.html
```

### 5. Ruff 检查失败

**自动修复：**
```bash
make format
```

**手动修复：**
```bash
ruff check plookingII/ --fix
ruff format plookingII/
```

## 📊 性能优化

### CI 执行时间预估

| 工作流 | 预估时间 | 并行执行 |
|--------|---------|---------|
| PR 快速检查 | 3-5 分钟 | 是 |
| 代码质量检查 | 2-3 分钟 | 独立 |
| Ubuntu 测试 (4个版本) | 5-8 分钟 | 并行 |
| macOS 测试 | 8-12 分钟 | 独立 |
| 安全检查 | 2-3 分钟 | 独立 |

**总计：** 约 10-15 分钟（并行执行）

### 优化建议

1. **使用缓存**
   - pip 依赖缓存（已启用）
   - pytest 缓存

2. **跳过不必要的测试**
   - 使用标记系统
   - CI 环境跳过 UI 测试

3. **并行测试**
   ```bash
   pytest -n auto  # 使用 pytest-xdist
   ```

4. **减少测试矩阵**
   - 主分支：测试所有 Python 版本
   - PR：只测试 Python 3.11

## 🎯 最佳实践

### 1. 提交前检查清单

- [ ] 运行 `make quick-check`
- [ ] 确保所有测试通过
- [ ] 检查代码覆盖率
- [ ] 更新文档（如需要）
- [ ] 编写有意义的提交信息

### 2. PR 创建清单

- [ ] 描述清晰的变更内容
- [ ] 关联相关 Issue
- [ ] CI 检查通过
- [ ] 代码审查通过
- [ ] 更新 CHANGELOG（如需要）

### 3. 发布前检查

```bash
# 完整 CI 检查
make full-check

# 验证版本号
make verify-version

# 测试构建
make build
```

## 🔄 持续改进

### 未来优化方向

1. **更智能的测试选择**
   - 基于文件变更只运行相关测试
   - 使用 pytest-testmon

2. **Docker 支持**
   - 创建统一的测试环境
   - 提高本地与 CI 的一致性

3. **性能基准测试**
   - 使用 pytest-benchmark
   - 跟踪性能回归

4. **更详细的报告**
   - HTML 测试报告
   - 性能分析报告
   - 安全审计报告

## 📚 相关文档

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Pytest 文档](https://docs.pytest.org/)
- [Ruff 文档](https://docs.astral.sh/ruff/)
- [Pre-commit 文档](https://pre-commit.com/)

## 🆘 获取帮助

遇到问题？

1. 查看 CI 日志中的详细错误信息
2. 在本地重现问题
3. 查阅相关文档
4. 提交 Issue 寻求帮助

---

**最后更新：** 2025-11-06
**维护者：** PlookingII Team
