# 版本号自动更新机制说明

**日期**: 2025-10-06  
**状态**: ✅ 已配置自动更新

---

## 📋 问题回答

### ❓ 关于菜单中的版本号是否能自动拉取最新版本？

**✅ 是的，版本号完全自动化，无需手动更新！**

---

## 🔄 自动更新机制

### 1. 版本号存储位置

PlookingII 项目使用**单一真源（Single Source of Truth）**管理版本号：

```
版本号定义位置：
├── pyproject.toml               (主版本号)
│   └── [project].version = "1.6.0"
│
└── plookingII/config/constants.py  (应用内版本号)
    └── VERSION = "1.6.0"
```

### 2. 关于菜单如何获取版本号

**关于菜单**通过以下链路自动获取版本号：

```python
# 第1步: constants.py 中定义版本号
VERSION = "1.6.0"  # 由 semantic-release 自动更新

# 第2步: menu_controller.py 中导入版本号
from plookingII.config.constants import VERSION, APP_NAME, AUTHOR, COPYRIGHT

# 第3步: 显示关于对话框时传递版本号
def show_about(self, sender):
    about_text = ui_strings.get_about_dialog_text(VERSION, AUTHOR, COPYRIGHT)
    alert.setInformativeText_(about_text)

# 第4步: 格式化显示
def get_about_dialog_text(self, version: str, ...):
    sections = [
        f"V {version}",  # 显示为 "V 1.6.0"
        ...
    ]
```

**结论**: 关于菜单**自动显示** `constants.py` 中的最新版本号，无需任何手动操作。

---

## 🤖 Semantic Release 自动化

### 配置详情

在 `pyproject.toml` 中配置了自动版本管理：

```toml
[tool.semantic_release]
# 自动更新这两个位置的版本号
version_toml = ["pyproject.toml:project.version"]
version_variables = ["plookingII/config/constants.py:VERSION"]

branch = "main"
upload_to_pypi = false
upload_to_release = true
build_command = "python tools/package_release.py --build"
changelog_file = "CHANGELOG.md"
changelog_placeholder = "<!--next-version-->"

[tool.semantic_release.commit_parser_options]
# 根据 commit message 自动判断版本号升级类型
allowed_tags = ["feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert"]
minor_tags = ["feat"]      # feat: 触发小版本号升级 (1.6.0 → 1.7.0)
patch_tags = ["fix", "perf", "refactor"]  # fix/perf/refactor: 触发补丁版本升级 (1.6.0 → 1.6.1)
```

### 工作流程

```
1. 开发者提交代码
   └── git commit -m "feat: 添加新功能"

2. 推送到 GitHub
   └── git push origin main

3. GitHub Actions 触发
   └── semantic-release 分析 commit messages

4. 自动判断版本号类型
   ├── feat: → 小版本升级 (1.6.0 → 1.7.0)
   ├── fix:  → 补丁升级   (1.6.0 → 1.6.1)
   └── BREAKING CHANGE: → 大版本升级 (1.6.0 → 2.0.0)

5. 自动更新版本号
   ├── 更新 pyproject.toml
   ├── 更新 plookingII/config/constants.py
   └── 更新 CHANGELOG.md

6. 创建 Git Tag 和 Release
   └── 构建并上传发布包

7. 用户下载新版本
   └── 关于菜单自动显示新版本号 ✅
```

---

## ✅ 自动化优势

### 1. 零手动操作

| 操作 | 手动方式 | 自动方式 |
|------|---------|---------|
| 更新版本号 | ❌ 需要手动改 3+ 处 | ✅ 自动更新所有位置 |
| 生成 Changelog | ❌ 手动编写 | ✅ 自动生成 |
| 创建 Git Tag | ❌ 手动创建 | ✅ 自动创建 |
| 构建发布包 | ❌ 手动执行 | ✅ 自动构建 |
| 上传 Release | ❌ 手动上传 | ✅ 自动上传 |

### 2. 版本一致性保证

```
✅ pyproject.toml 版本: 1.6.0
✅ constants.py 版本:   1.6.0
✅ 关于菜单显示:        V 1.6.0
✅ Git Tag:            v1.6.0
✅ CHANGELOG.md:       ## 1.6.0
```

所有位置的版本号**自动保持一致**，不会出现不一致的情况。

### 3. 遵循语义化版本规范

- **主版本号** (Major): 不兼容的 API 修改
- **次版本号** (Minor): 向下兼容的功能性新增
- **修订号** (Patch): 向下兼容的问题修正

```
1.6.0 → 1.6.1  (修复bug)
1.6.0 → 1.7.0  (添加新功能)
1.6.0 → 2.0.0  (破坏性更改)
```

---

## 🔍 验证方法

### 检查当前版本号

```bash
# 方法1: 查看 constants.py
grep "VERSION =" plookingII/config/constants.py

# 方法2: 查看 pyproject.toml
grep "version =" pyproject.toml | head -1

# 方法3: Python 脚本查看
python3 -c "from plookingII.config.constants import VERSION; print(VERSION)"

# 方法4: 运行应用查看关于菜单
python3 -m plookingII
# 然后点击菜单: PlookingII → 关于
```

### 验证自动更新配置

```bash
# 检查 semantic-release 配置
grep -A 5 "\[tool.semantic_release\]" pyproject.toml

# 验证版本一致性
python3 scripts/verify_version_consistency.py
```

---

## 🛠️ 开发者工作流

### 日常开发（无需关心版本号）

```bash
# 1. 开发新功能
git checkout -b feature/new-feature
# ... 编写代码 ...

# 2. 提交时使用规范的 commit message
git commit -m "feat: 添加快捷键支持"
# 或
git commit -m "fix: 修复图片加载问题"

# 3. 推送到远程
git push origin feature/new-feature

# 4. 创建 Pull Request
# 合并后，GitHub Actions 会自动处理版本号

# 5. ✅ 版本号自动更新，无需任何手动操作！
```

### Commit Message 规范

```bash
# 功能添加 (触发 minor 版本升级)
git commit -m "feat: 添加图片旋转功能"
git commit -m "feat(ui): 新增快捷键帮助弹窗"

# Bug 修复 (触发 patch 版本升级)
git commit -m "fix: 修复内存泄漏问题"
git commit -m "fix(cache): 解决缓存失效问题"

# 性能优化 (触发 patch 版本升级)
git commit -m "perf: 优化图片加载速度"

# 重构 (触发 patch 版本升级)
git commit -m "refactor: 简化缓存系统"

# 文档更新 (不触发版本升级)
git commit -m "docs: 更新 README"

# 破坏性更改 (触发 major 版本升级)
git commit -m "feat!: 重构 API 接口

BREAKING CHANGE: 移除了旧的缓存 API"
```

---

## 📊 版本更新示例

### 场景 1: 添加新功能

```bash
# 开发者提交
git commit -m "feat: 添加批量导出功能"
git push

# 自动流程
当前版本: 1.6.0
↓
semantic-release 分析: "feat" → 小版本升级
↓
新版本: 1.7.0
↓
自动更新:
  - pyproject.toml: version = "1.7.0"
  - constants.py: VERSION = "1.7.0"
  - CHANGELOG.md: 添加 1.7.0 条目
  - Git Tag: v1.7.0
↓
关于菜单自动显示: V 1.7.0 ✅
```

### 场景 2: 修复 Bug

```bash
# 开发者提交
git commit -m "fix: 修复启动崩溃问题"
git push

# 自动流程
当前版本: 1.7.0
↓
semantic-release 分析: "fix" → 补丁升级
↓
新版本: 1.7.1
↓
自动更新所有位置
↓
关于菜单自动显示: V 1.7.1 ✅
```

---

## 🎯 总结

### 问题回答

| 问题 | 答案 |
|------|------|
| 版本号能否自动拉取？ | ✅ 是，关于菜单自动显示 constants.py 中的版本号 |
| 是否需要手动更新？ | ❌ 否，semantic-release 会自动更新 |
| 如何触发版本升级？ | 使用规范的 commit message（feat/fix/等） |
| 版本号在哪里定义？ | constants.py (单一真源，自动同步) |
| 多久更新一次版本？ | 每次 push 到 main 分支时自动检查 |

### 核心优势

1. ✅ **完全自动化** - 无需手动修改任何文件
2. ✅ **版本一致性** - 所有位置版本号自动同步
3. ✅ **语义化版本** - 遵循 SemVer 规范
4. ✅ **零维护成本** - 开发者只需关注代码和 commit message
5. ✅ **关于菜单自动更新** - 用户总是看到最新版本号

### 最佳实践

1. **使用规范的 commit message** - 这是触发自动版本升级的关键
2. **不要手动修改版本号** - 让 semantic-release 自动处理
3. **定期查看 CHANGELOG.md** - 了解版本更新历史
4. **验证版本一致性** - 运行 `make verify-version`

---

## 🔗 相关文档

- [版本管理指南](docs/VERSION_MANAGEMENT.md)
- [版本统一报告](VERSION_MANAGEMENT_REPORT.md)
- [Semantic Release 文档](https://python-semantic-release.readthedocs.io/)
- [语义化版本规范](https://semver.org/lang/zh-CN/)

---

**更新日期**: 2025-10-06  
**维护状态**: ✅ 自动化运行中  
**版本一致性**: ✅ 所有位置同步

**🎉 PlookingII 使用完全自动化的版本管理，关于菜单始终显示最新版本号！**

