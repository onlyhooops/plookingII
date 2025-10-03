# 架构守护文档

## 概述

架构守护（Architecture Guard）是PlookingII项目的代码质量和架构完整性保护系统。它通过自动化检查防止代码质量回退和架构破坏。

## 目标

1. **防止架构回退** - 确保已移除的弃用代码不会被重新引入
2. **保持代码质量** - 强制执行代码质量标准
3. **提前发现问题** - 在代码合并前捕获潜在问题
4. **文档化标准** - 明确项目的质量要求

## 架构守护组成

### 1. 自动化测试

#### 架构完整性测试 (`tests/test_architecture.py`)

**检查内容:**
- ✅ 弃用模块检查 - 确保已移除的模块不被重新引入
- ✅ 弃用导入检查 - 确保代码不使用已弃用的导入
- ✅ 核心模块完整性 - 验证必需的核心模块存在
- ✅ 循环导入检测 - 基础的循环依赖检查
- ✅ 配置结构完整性 - 验证配置模块结构
- ✅ UI结构完整性 - 验证UI模块结构

**弃用模块列表:**
```python
- plookingII/core/unified_config.py
- plookingII/core/simple_config.py
- plookingII/monitor/memory.py
- plookingII/monitor/performance.py
- plookingII/monitor/simplified_memory.py
- plookingII/core/cache_adapter.py
```

#### 代码质量测试 (`tests/test_code_quality.py`)

**检查内容:**
- 🔍 Ruff代码风格检查
- 🔍 Flake8代码规范检查
- 🔍 Mypy类型检查
- 📊 Radon复杂度检查
- 📊 可维护性指数检查
- 🔒 依赖安全漏洞检查
- 📝 文档完整性检查
- 📁 文件组织结构检查
- ⚡ 最佳实践检查

### 2. 架构守护工具 (`tools/architecture_guard.py`)

独立的命令行工具，可在本地和CI环境中运行。

**使用方法:**
```bash
# 直接运行
python tools/architecture_guard.py

# 或使用Make命令
make guard
```

**检查项目:**
1. ✅ 弃用模块检查
2. ✅ 弃用导入检查
3. ✅ 核心模块完整性
4. ✅ 版本一致性
5. ✅ 代码风格(Ruff)
6. ✅ 安全基线
7. ✅ 依赖管理

**输出示例:**
```
================================================================================
🛡️  架构守护 - 防止架构回退检查
================================================================================

📊 检查结果汇总
================================================================================

✅ 通过 (6):
  • 弃用模块检查: 所有弃用模块已正确移除
  • 弃用导入检查: 未发现使用弃用导入
  • 核心模块检查: 所有核心模块完整
  • 版本一致性检查: 版本号格式正确: 1.3.1
  • 安全基线检查: 未发现明显的安全问题
  • 依赖管理检查: 依赖管理正常

================================================================================
总计: 7 项检查
通过: 6 项 (85%)
警告: 1 项
错误: 0 项
================================================================================

✅ 架构守护检查全部通过！代码质量良好。
```

### 3. Pre-commit Hooks (`.pre-commit-config.yaml`)

Git提交前自动运行的检查。

**安装:**
```bash
# 安装pre-commit
pip install pre-commit

# 安装hooks
pre-commit install

# 或使用Make命令
make pre-commit
```

**包含的检查:**
1. **Ruff** - 快速Python代码检查和自动修复
2. **Black** - 代码格式化
3. **isort** - 导入语句排序
4. **基础文件检查** - YAML/JSON格式、大文件、合并冲突等
5. **Bandit** - 安全漏洞扫描
6. **Mypy** - 类型检查
7. **Interrogate** - 文档字符串覆盖率
8. **架构守护** - 自定义架构检查
9. **快速测试** - 架构测试快速验证

### 4. CI/CD集成

#### GitHub Actions Workflows

**主CI流程** (`.github/workflows/ci.yml`)
- 🛡️ 架构守护检查
- 🧪 架构完整性测试
- 🧪 代码质量测试
- 🧪 完整测试套件(带覆盖率)
- 🔍 代码风格检查(Ruff, Flake8)
- 📊 复杂度检查(Radon)
- 🔍 类型检查(Mypy)
- 🔒 安全审计(pip-audit)
- 📊 生成质量报告

**架构守护专用流程** (`.github/workflows/architecture_guard.yml`)
- 检查弃用模块和导入
- 验证版本一致性
- 检查统一接口使用
- 运行架构测试
- 生成架构检查报告
- 代码质量检查
- 安全扫描

## 使用指南

### 日常开发

**开发时的快速检查:**
```bash
# 快速检查(架构+基础测试)
make quick-check

# 或单独运行
make guard           # 架构守护
make test-arch      # 架构测试
make lint           # 代码检查
```

**提交前检查:**
```bash
# 如果安装了pre-commit，会自动运行
git commit -m "your message"

# 手动运行所有pre-commit检查
make pre-commit-run

# 或运行完整的本地CI模拟
make ci
```

### 修复常见问题

#### 1. 弃用模块被重新引入

**错误:**
```
❌ 弃用模块检查: 发现已弃用的模块被重新引入
  - plookingII/core/unified_config.py
```

**解决:**
```bash
# 删除弃用模块
rm plookingII/core/unified_config.py

# 使用新的接口替代
# 参考: docs/MIGRATION_GUIDE.md
```

#### 2. 代码风格问题

**错误:**
```
⚠️ 代码风格检查(Ruff): 发现 15 个代码风格问题
```

**解决:**
```bash
# 自动修复大部分问题
make format

# 或手动运行ruff
ruff check --fix plookingII/
ruff format plookingII/
```

#### 3. 高复杂度代码

**错误:**
```
⚠️ 发现高复杂度代码(D级及以上)
```

**解决:**
- 重构大函数为多个小函数
- 提取复杂逻辑到独立方法
- 使用早期返回减少嵌套
- 考虑使用策略模式或其他设计模式

#### 4. 类型检查失败

**错误:**
```
⚠️ Mypy类型检查发现问题
```

**解决:**
```bash
# 添加类型注解
def function_name(param: str) -> int:
    ...

# 或在特定行忽略(谨慎使用)
result = some_function()  # type: ignore
```

### 发布前检查

```bash
# 运行完整检查
make full-check

# 确保所有检查通过:
# ✅ 架构守护
# ✅ 所有测试
# ✅ 代码质量
# ✅ 安全检查
# ✅ 测试覆盖率 >= 40%
```

## 质量标准

### 代码覆盖率
- **最低要求:** 40%
- **目标:** 60%+
- **核心模块:** 建议70%+

### 复杂度阈值
- **圈复杂度:** 单个函数不超过D级(21-50)
- **可维护性指数:** 模块不低于C级
- **建议:** 保持函数简单，单一职责

### 代码质量
- **Ruff检查:** 必须通过(0错误)
- **Flake8:** 允许少量警告(≤10)
- **类型检查:** 建议通过，非强制

### 安全要求
- **禁止:** eval(), exec()的使用
- **禁止:** 硬编码的凭据和密钥
- **要求:** 定期更新依赖修复安全漏洞

### 文档要求
- **公共类:** 必须有文档字符串
- **复杂函数:** 建议有文档说明
- **README:** 保持更新和完整

## 配置文件

### pytest.ini
```ini
[pytest]
addopts = --cov=plookingII --cov-fail-under=40
testpaths = tests
```

### pyproject.toml
```toml
[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "B", "W", "PL", "TRY", "N"]
```

### .flake8
```ini
[flake8]
max-line-length = 120
ignore = E501,W503,F403,F405
```

### mypy.ini
```ini
[mypy]
python_version = 3.11
ignore_missing_imports = True
warn_unused_ignores = True
```

## 常见问题

### Q: 如何跳过pre-commit检查？

**A:** 不推荐，但紧急情况下可以：
```bash
git commit --no-verify -m "message"
```

### Q: 如何临时忽略某个检查？

**A:** 在测试文件中使用pytest标记：
```python
@pytest.mark.skip(reason="临时跳过")
def test_something():
    ...
```

### Q: 架构守护检查太严格怎么办？

**A:** 
1. 首先考虑是否真的需要放宽限制
2. 如果确实需要，修改 `tools/architecture_guard.py` 中的阈值
3. 提交PR说明原因

### Q: CI检查失败但本地通过？

**A:** 常见原因：
1. 依赖版本不一致 - 更新requirements.txt
2. 环境差异 - 使用相同的Python版本(3.11)
3. 缓存问题 - 清理并重新运行

## 最佳实践

### 1. 提交前检查

```bash
# 始终在提交前运行
make quick-check
```

### 2. 定期运行完整检查

```bash
# 每天至少一次
make ci
```

### 3. 保持代码简洁

- 函数不超过50行
- 类不超过300行
- 文件不超过1000行

### 4. 编写测试

- 新功能必须有测试
- Bug修复必须有回归测试
- 保持测试覆盖率稳步提升

### 5. 文档同步

- 代码变更时更新文档
- API变更必须更新文档
- 保持CHANGELOG更新

## 贡献指南

### 添加新的架构检查

1. 在 `tests/test_architecture.py` 中添加测试
2. 在 `tools/architecture_guard.py` 中添加检查逻辑
3. 更新本文档
4. 提交PR并说明新检查的目的

### 修改质量标准

1. 在团队中讨论并达成共识
2. 更新配置文件(pytest.ini, pyproject.toml等)
3. 更新文档
4. 逐步推进，给团队时间适应

## 参考资源

- [Ruff文档](https://docs.astral.sh/ruff/)
- [Pytest文档](https://docs.pytest.org/)
- [Pre-commit文档](https://pre-commit.com/)
- [语义化版本](https://semver.org/lang/zh-CN/)
- [Python类型提示](https://docs.python.org/zh-cn/3/library/typing.html)

## 维护者

如需帮助或有建议，请：
1. 查看本文档
2. 查看相关测试文件
3. 提交Issue或PR

---

**最后更新:** 2025-10-01  
**版本:** 1.3.1

