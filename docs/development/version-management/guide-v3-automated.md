# PlookingII 自动化版本管理指南 V3

**创建日期**: 2026-08-05
**版本**: 3.0
**状态**: 推荐使用

---

## 一、为什么 V2 会“不同步”

V2 的核心是“单一真源 + 手动执行”：

```bash
python scripts/bump_version.py patch   # 手动升版
vim CHANGELOG.md                       # 手动写日志
git tag v1.7.1                         # 手动打标签
```

只要任何一步被跳过（忘了升版、忘了打标签、忘了写日志），版本号、CHANGELOG 与 git 标签就会漂移。本项目实际已经出现：`__version__.py` 是 2.4.1、CHANGELOG 有 [2.4.1]，但仓库里只有 v1.5.0/v1.6.0/v1.7.1 三个旧标签。

**结论：人肉执行必然漂移，必须把“升版 + 日志 + 标签”交给机器。**

---

## 二、V3 方案：语义化自动发布

采用 Python 生态事实标准 **python-semantic-release**（项目已预留配置，现补齐执行链路）：

```
代码合并到 main
    │
    ▼
GitHub Actions（version-bump.yml）
    │ 读取自上次标签以来的 Conventional Commits
    ▼
自动计算下一版本：feat→minor，fix/perf/refactor→patch，其他→不升版
    ▼
更新 plookingII/__version__.py（唯一真源）
    ▼
在 CHANGELOG.md 的 <!--next-version--> 处插入新版本记录
    ▼
自动创建提交 chore(release): vX.Y.Z 与标签 vX.Y.Z
    ▼
推送回仓库 → 触发 release.yml 构建发布
```

**效果：每一个被合并的代码变动，都会自动带来一次版本号提升与一条更新日志。** 开发者的唯一职责是写规范提交信息。

---

## 三、提交信息规范（必须遵守）

版本号由提交信息自动推导，请使用 Conventional Commits：

| 提交前缀 | 触发版本变化 | 示例 |
| --- | --- | --- |
| `feat:` | minor（0.1.0 → 0.2.0） | `feat: 新增网格视图` |
| `fix:` | patch | `fix: 修复历史恢复弹窗焦点` |
| `perf:` / `refactor:` | patch | `perf: 优化目录扫描` |
| `docs:` / `chore:` / `ci:` / `test:` / `style:` | 不升版 | `docs: 更新README` |
| 带 `!` 或 `BREAKING CHANGE` | major | `feat!: 重写存储格式` |

提交信息中的主题会进入 CHANGELOG，因此请写**有意义的主题**，而不是 `update` / `fix bug`。

> 注意：CHANGELOG 由提交信息自动生成，会覆盖手工撰写的详细说明段落。需要保留
> 手工描述的版本，请把说明写进提交信息正文，或改用 PSR 的自定义 changelog 模板。

---

## 四、日常用法

### 正常流程（无需任何手动操作）

1. 写代码；
2. 用规范的提交信息提交（如 `fix: ...`、`feat: ...`）；
3. 合并到 `main`；
4. CI 自动完成升版 + CHANGELOG + 标签 + 发布。

### 本地预览“下一次会升到什么版本”

```bash
make release-dry-run
```

只打印计算结果，不修改任何文件。

### 本地直接执行升版（不依赖 CI）

```bash
make release-version
git push origin <分支> --tags
```

### 手动补齐历史积压

在 GitHub Actions 页面手动运行 `🔖 自动版本提升与更新日志`（workflow_dispatch）。

---

## 五、关键配置

| 位置 | 配置 | 说明 |
| --- | --- | --- |
| `pyproject.toml` | `[tool.semantic_release]` | 版本文件、分支、CHANGELOG、标签规则 |
| `pyproject.toml` | `version_variables` | 唯一真源 `plookingII/__version__.py` |
| `pyproject.toml` | `commit_parser_options` | feat→minor、fix/perf/refactor→patch |
| `.github/workflows/version-bump.yml` | 自动执行链路 | 合并 main 后自动升版 |
| `.github/workflows/release.yml` | 标签触发构建 | 标签 vX.Y.Z 触发应用构建发布 |

---

## 六、常见问题

### Q1：为什么不是“每个 commit 都升版”？

对每个 commit 升版会产生大量中间版本（v2.4.1-rc.3 之类的噪音），且打断“提交即原子操作”的语义。业界标准做法是**在每个变更合并到 main 时升版一次**——对用户而言，这已经等价于“每个代码变动都自动更新版号与日志”。

### Q2：旧标签缺失，工具如何计算基线？

需要为当前已发布状态补一个基线标签（如 `v2.4.1`）。已提供说明；缺失时工具会从最早提交计算，产生不合理的版本跳跃。

### Q3：CI 推送版本提交会不会无限循环触发？

不会。版本提交的类型是 `chore(release)`，不在升版规则内，推送后不会再次触发升版。

### Q4：GITHUB_TOKEN 权限？

`version-bump.yml` 需要 `contents: write`（已配置）。普通 PR 无需该权限。
