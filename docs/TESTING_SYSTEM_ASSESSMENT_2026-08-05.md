# 测试与验证系统评估报告

> 评估日期：2026-08-05
> 评估对象：PlookingII 的测试与验证体系（pytest 生态 + CI 门禁 + 静态分析）
> 评估问题：当前测试/验证系统是否“过时”？是否有必要重新搭建更“先进”的系统？

---

## 一、结论（先行）

**当前测试系统并不“过时”，不需要推倒重建。** 工具的选型是行业主流且仍在活跃演进；真正的问题是**“工具已装但门禁未生效、能力未启用”**——覆盖率门槛形同虚设、CI 软性放行、已安装的 hypothesis / pytest-benchmark / tox 等工具完全没有接入。

建议的路径是**“增强并真正启用现有体系”**，而不是迁移到另一套框架：补上缺失的测试类型（属性测试、性能基准、变异测试抽样、UI 集成测试），把门禁从“建议”变成“硬约束”。这比更换框架收益大得多、风险小得多。

---

## 二、现状盘点

| 工具 | 版本（本机实测） | 用途 | 是否真正接入门禁 |
| --- | --- | --- | --- |
| pytest | 9.1.1 | 主测试框架 | ✅ 全量跑 |
| pytest-cov / coverage | 7.15.3 / 7.15.3 | 覆盖率 | ⚠️ 阈值 45% 此前未达标（已修复至 52%+） |
| pytest-timeout | 2.4.0 | 防挂死 | ✅ |
| pytest-xdist | 3.8.0 | 并发 | 未启用（`-n auto` 被注释） |
| pytest-randomly | 4.1.0 | 随机测试顺序 | ✅（默认开启） |
| pytest-mock | 3.15.1 | Mock | ✅ |
| pytest-benchmark | 4.0.0 | 性能基准 | ❌ 已安装未使用 |
| hypothesis | 6.82.0 | 属性测试 | ❌ 已安装未使用 |
| tox | 4.6.0 | 多环境矩阵 | ❌ 已安装未使用 |
| ruff | — | lint | ✅ 源码硬门（已清零），测试层未纳入 |
| mypy / flake8 / bandit / safety | — | 类型/风格/安全 | ⚠️ CI 中 `continue-on-error` |
| memory-profiler / py-spy | — | 内存/性能剖析 | ❌ 手动工具 |

### 覆盖情况（2026-08-05 全量实测）

- 测试：1571 通过 / 13 跳过
- 总覆盖率：52.17%（阈值 45%，已达标）
- 高覆盖：utils（90%+）、config（90%+）、core/history（90%）、simple_cache（76%）
- 低覆盖：`ui/views.py`（约 9%）、`ui/window.py`（约 20%）、`video_player_view.py`（约 0%）

---

## 三、判断依据：为什么“不旧”

1. **pytest 仍是 Python 生态的事实标准**（2026 年），unittest 是旧标准，pytest 的插件生态（timeout/xdist/randomly/benchmark/hypothesis 集成）是当前主流方案。没有更主流的替代品。
2. **测试类型完整度是“未启用”，不是“无能力”**：hypothesis、pytest-benchmark、tox 都已装进 `requirements-dev.txt`，说明项目团队当时就计划引入，只是没有落地配置与门禁。
3. **平台特殊性限制了“更先进”选项**：这是 pyobjc/AppKit 的 macOS 桌面应用。跨平台 UI 自动化框架（Playwright/Selenium）不适用；XCUITest 是 Apple 官方方案，但对 PyObjC 应用需要桥接层，成本高。用 mock 单元测试 + 少量真机 smoke 是务实组合。
4. **近期两次真实回归恰好是“门禁失效”而非“工具过时”的例证**：历史恢复功能丢失、弹窗焦点卡死，都在测试通过的情况下进入用户侧——因为对应路径没有测试覆盖、CI 又软性放行。

---

## 四、真实差距（按优先级）

| 优先级 | 差距 | 现状 | 建议 |
| --- | --- | --- | --- |
| P0 | 覆盖率门槛未生效 | 43.78% < 45%，CI `|| echo` + `continue-on-error` | 已修复：覆盖率 52.17%，CI 测试步骤改为硬门禁 |
| P0 | UI/集成测试薄弱 | views/window/video_player 覆盖 <20% | 逐步补；至少为历史恢复、弹窗、导航加集成回归（已补核心路径） |
| P1 | 属性测试未启用 | hypothesis 已装未用 | 对缓存/历史/路径检测等纯逻辑启用 hypothesis |
| P1 | 性能基准未启用 | pytest-benchmark 已装未用 | 为懒解码/目录扫描/缓存命中建立基准与回归阈值 |
| P1 | 变异测试缺失 | 无 | 抽样运行 mutmut/cosmic-ray，找出“假绿”测试 |
| P2 | 慢测试未入常规门禁 | `--run-slow` 跳过 11 个 | nightly 任务专门跑慢测试 |
| P2 | UI 端到端自动化缺失 | 无 XCUITest/pyobjc 驱动 | 可选：真实启动 app + 截图 smoke；成本高，按需 |
| P2 | 多环境矩阵未启用 | tox 已装未用 | 至少覆盖 Python 3.11/3.12 |

---

## 五、建议路线（增强而非重建）

### 第 1 步（已完成）
- 补覆盖率至阈值以上（52.17%）；
- CI 测试与覆盖率失败即失败；
- 源码 lint 清零；测试层空白行债务批量清理（1187 → 120 处残留语义级问题）；
- 移除未使用的 opencv 依赖。

### 第 2 步（建议 2 周内）
- 对以下纯逻辑启用 hypothesis 属性测试：
  - `SimpleImageCache`（LRU/容量/内存记账不变量）
  - `DirectoryImageListCache`（mtime 失效/LRU）
  - `TaskHistoryManager`（保存/加载往返一致性）
  - `RemoteFileDetector` / `SMBOptimizer`（策略选择边界）
- 用 pytest-benchmark 给关键路径建立基准：目录扫描、首帧加载、缓存命中翻页；
- 抽样变异测试（先对 core 模块跑 mutmut，设阈值如 80% 杀灭率）。

### 第 3 步（建议 1-2 个月）
- 慢测试移入 nightly workflow；
- tox 矩阵（3.11/3.12）接入 CI；
- 视成本评估真实 app smoke 测试（启动→打开目录→翻页→退出，截图比对）。

---

## 六、结论重申

**系统不旧，缺的是“把能力真正用起来”的工程纪律。** 本轮已把覆盖率门禁、CI 硬约束、lint 清理落地；下一步的价值增量在属性测试与性能基准，而不是更换测试框架。
