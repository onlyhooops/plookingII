# PlookingII 技术自查报告

> 评估日期：2026-08-05
> 评估对象：`plookingII`（macOS 原生图片浏览器，AppKit / PyObjC / Quartz）
> 评估方法：全量测试套件实测、Ruff 静态分析、核心模块逐文件审阅、Git 历史与文档交叉核对
> 说明：本报告为本地自查材料，不纳入版本管理；其中的量化指标均为 2026-08-05 在本机实测结果。

---

## 一、客观指标（实测）

| 指标 | 数值 | 备注 |
| --- | --- | --- |
| 版本 | 2.4.1 | `plookingII/__version__.py` |
| 源码规模 | 71 个 `.py`，约 23,842 行 | 不含测试 |
| 测试规模 | 45 个文件，约 19,332 行 | `tests/unit/` |
| 测试结果 | 1465 通过 / 13 跳过 | 全量套件实测，约 75 秒 |
| 测试覆盖率 | **43.78%**（阈值 45%，未达标） | `--cov-fail-under=45` 失败 |
| 源码 Ruff | **9 处** | helpers.py 2 处、video_player_view.py 5 处等 |
| 测试 Ruff | **1187 处** | 绝大多数为空白行 W293 |
| 主分支提交数 | 41 个 | 常规提交风格，中文描述 |
| 目标平台 | macOS x86_64（Intel） | 明确不支持 Apple Silicon |
| 打包方式 | py2app，强制 `-arch x86_64` | 无 universal2 |
| 运行依赖 | psutil / Pillow / opencv-python / pyobjc | **opencv-python 源码零引用** |

---

## 二、总体结论（明确结论）

**总体评价：B+（良好偏优）——性能架构有真实深度，工程纪律较好；主要风险不在“设计”而在“质量护栏未真正生效”和少数正确性缺陷。**

这是一个为“大批量照片筛选/浏览”场景认真做过性能工程的项目：懒解码、零拷贝直绘、像素内存记账缓存、目录级列表缓存、两阶段扫描、自适应预取等优化不是口号，而是有对应实现和注释支撑的。同时它也是一个“自我要求高但落地不完整”的项目：覆盖率门槛设了但未达标、CI 大量 `continue-on-error`、测试层 lint 债务上千处、两个真实 UI 回归（历史恢复丢失、弹窗焦点卡死）都未被测试捕获。

简言之：**性能是优点，回归防护与少数正确性细节是短板；按“P0/P1 修复清单”执行后，可以支撑到接近生产就绪的状态。**

---

## 三、优点

### 3.1 性能工程有真实深度（核心优势）

- **Preview.app 风格懒解码**：`CGImageSourceCreateImageAtIndex` + `ShouldCacheImmediately=False` 创建不解码像素的 CGImage 代理，超大图毫秒级“加载”，解码延迟到 Core Animation 需要时。
- **零拷贝直绘**：CGImage 直接渲染，不做格式转换；项目明确放弃了 EXIF 方向修正（外部工作流预纠正），换来零拷贝路径，决策清晰且有注释。
- **差异化缩略图参数**：PNG 与 JPEG/HEIC 使用不同的 `SubsampleFactor`、`ShouldCacheImmediately`、`CreateThumbnailFromImageAlways/IfAbsent` 组合，针对 DEFLATE 与 DCT 解码特性分别调优。
- **大文件读取优化**：F_NOCACHE 标记顺序读取不污染系统页缓存；MPF 内嵌预览图异步提取，避免全图解码。
- **两阶段文件夹扫描**：先浅层扫描直系子目录毫秒级出首帧，再后台深度遍历补全，配合代次（generation）保护防止过期结果覆盖新状态。
- **异步文件夹跳转**：跨界翻页在后台线程枚举目标文件夹，不冻结 UI。
- **自适应导航**：按键防抖随浏览速度 5–20ms 自适应、速度历史统计、预取窗口动态调整。

### 3.2 缓存体系设计成熟

- `SimpleImageCache`：NSCache 实现 + 按**实际解码像素**（w×h×4）记账，而非压缩文件大小；含 `reconcile()` 对账 NSCache 自动驱逐导致的统计漂移——说明作者处理过真实的内存记账陷阱。
- 目录级图片列表缓存：以目录 mtime 自动失效，文件夹切换跳过全量枚举与排序。
- 尺寸元数据预热：后台批量读取分辨率，导航热路径零磁盘 I/O。
- HOT3 锁定、双向缓存池、prefetch 与解码线程池分离、代次取消，形成完整的“预取—缓存—显示”闭环。

### 3.3 架构分层与工程纪律

- 分层清晰：`ui/controllers`、`ui/managers`、`services`、`core`、`config`、`utils`、`db`，控制器/管理器各司其职。
- 最近的 v2.4.1 清理真实有效：删除约 12k 行零引用死代码，修复失效导出，收敛重复实现。
- 防御式编程无处不在：AppKit 调用几乎全部 try/except + 回退；SQLite 用 WAL、同步 NORMAL、外键；路径做符号链接规范化并兼容旧库；文件操作带重试退避；所有后台线程 daemon 化。
- 文档纪律好：CHANGELOG、性能优化计划（P0/P1 已落地，P2/P3 有路线）、发布说明、安全/生产就绪审计报告齐备。
- 测试数量大（1465 个），带超时、并发防护、AppKit mock 体系，且能覆盖真实文件系统与 SQLite。

### 3.4 最近两次回归修复值得肯定

- 历史进度恢复：两阶段扫描快速路径此前丢失保存/恢复，已修复并有回归测试。
- 历史恢复弹窗：应用级 `runModal` 在失焦时导致按钮不可点、界面停摆，已改为窗口 sheet + 激活置前 + 失败兜底，并有 5 个回归测试。

---

## 四、缺点与风险（按严重度分级）

### 高严重度

#### H1. 目录列表缓存的“别名突变”正确性缺陷

`FileInfoBatchLoader.get_directory_images()` 直接把内部缓存的 list 对象返回给调用方（`DirectoryImageListCache.get` 返回引用而非拷贝）。而 `OperationManager._remove_current_image_from_sequences()` 会对 `main_window.images` 执行 `pop()`（“保留/精选”操作后），**原地修改了共享的缓存列表**。

后果：精选操作后，该文件夹的目录级列表缓存被污染——被移走的图片会从缓存中“永久消失”，直到目录 mtime 变化触发重扫；同一会话内重新进入该文件夹，图片列表缺项。

> 影响面：所有“保留图片”工作流；属真实 bug，建议 P0 修复（返回拷贝或让调用方先拷贝）。

#### H2. 质量护栏未真正生效，回归检测弱

- 覆盖率 43.78% < 45%，本地 `pytest` 带 `--cov-fail-under=45` 即失败；CI 的测试步骤用 `|| echo "部分测试失败，但继续执行"` + `continue-on-error: true` 软性放行。
- 代码质量（ruff）在 CI 是硬门，但本机 pre-commit 未安装（上次提交需 `--no-verify` 跳过），源码仍残留 9 处、测试 1187 处 lint 问题。
- 事实佐证：近期两个真实 UI 回归（历史恢复功能整体丢失、弹窗焦点卡死导致强杀进程）都逃过了测试网，说明 UI 层覆盖与集成测试不足。

### 中严重度

#### M1. 历史恢复精度依赖“文件夹序号”而非路径

`TaskHistoryManager.save_task_progress()` 持久化了 `current_subfolder_index`，但 **`current_folder` 字段从未写入数据库**（schema 无此列），恢复时只能按历史列表里的索引定位。一旦两次会话之间文件夹列表顺序/构成变化（增删目录、精选过滤、排序规则变化），恢复会落到错误的文件夹。

#### M2. 进度保存存在双轨与竞态

- 存在两套并行节流保存：`HistoryManager.save_task_progress()`（2s 节流）与 `FolderManager._save_task_progress()`（3s 节流），职责重叠，容易各改各的。
- `HistoryManager._async_save_progress()` 的工作线程在保存后无条件清空 `_pending_save_data`，若主线程在此期间已写入更新的待保存数据，**最新的进度会被丢弃**；退出时只保存“最后一刻有值”的 pending，极端情况下丢失最终位置。

#### M3. 线程管理分散，退出时序无强保证

- 全项目 43 处直接 `threading.Thread(...)`（多数 daemon），另有多个独立线程池；散线程缺乏统一生命周期管理。
- 应用退出时，主进程终止可能与仍在执行的 SQLite 写操作竞争（WAL 降低了损坏概率，但非零风险）；关闭清理流程分散在窗口/控制器/管理器多处。
- `core/loading/helpers.py` 的全局 `_file_size_cache` 无锁访问（dict 读改写 + 计数器），多线程下存在低危数据竞争。

#### M4. 弹窗焦点问题只修了“一处”

历史恢复弹窗已改为 sheet，但 `operation_manager.py`（6 处）与 `ui/utils/user_feedback.py`（5 处）仍使用 `alert.runModal()`。这些调用多由用户交互触发，风险较低，但同一类“应用不在最前端时模态弹窗无法聚焦”的问题理论上仍存在，未统一治理。

### 低严重度

- **L1**：`video_player_view.py`（新功能，约 500 行）无测试、5 处 lint（未使用导入、未排序导入、未用变量）。
- **L2**：`requirements.txt` 依赖 `opencv-python`，源码零引用；psutil/Pillow 在代码里是可选导入，却写为强依赖。
- **L3**：仅支持 Intel x86_64（README 明示不支持 M 系列），py2app 强制 `-arch x86_64`；没有 universal2，无法覆盖 Apple Silicon 用户，是明确的产品增长限制。
- **L4**：文档存在陈旧与矛盾：`docs/reports/production-readiness.md` 停留在 v1.6.0（61 个测试）而当前是 1465 个；多份 `TEST_COVERAGE_*` 报告口径不一。
- **L5**：`imports.py` 兼容 shim（`from ..imports import logging, threading, time`）使真实导入路径不直观，`__all__` 混入私有名称；属于历史包袱，但影响可维护性。
- **L6**：大量裸 `except Exception: pass` 静默吞错，真实失败模式难以从日志还原（部分已带 debug 日志，但仍有不少无声路径）。

---

## 五、优化建议

### 5.1 性能（Performance）

1. **修复 H1 缓存别名突变（P0）**：`get_directory_images()` 返回拷贝，或让业务方先 `list()` 拷贝再持有；`main_window.images` 一律视为“可变的私有列表”。
2. **解码自适应两阶段（P1）**：按实测解码耗时归档（项目 P2-1 已计划），中低端机器上中小文件也享受“先缩略图后全分辨率”，避免首帧等待。
3. **缩放重解码优化（P1）**：缓存键升级为 `(path, target_size)`，避免缩放时重复全尺寸解码；超大图绘制可改用 `CATiledLayer` 平铺渲染，缩放首帧更顺滑。
4. **预取有界化（P1）**：为 prefetch 队列加显式上限与丢弃过期任务的策略（已有代次机制，补队列上限即可）；在文件夹末图时预取下一文件夹首图，跨界翻页接近零等待。
5. **目录变更监听（P2）**：用 FSEventStream/NSWorkspace 通知替代每次 `get()` 的 mtime stat，既省 I/O 又能立刻感知外部改动。
6. **内存自适应（P2）**：缓存预算从固定 2GB 改为按系统可用内存/RSS 自适应；响应 `NSApplicationDidReceiveMemoryWarningNotification` 立即降级清理。
7. **启动与体积（P2）**：PIL/psutil 改为真正惰性导入；移除未使用的 opencv 依赖；打包输出 universal2，覆盖 Apple Silicon。

### 5.2 UI / 交互

1. **弹窗统一治理（P1）**：把所有确认/提示弹窗统一为“激活应用 + 窗口 sheet”，消除 `runModal` 焦点类故障（历史弹窗已示范，推广到 operation_manager / user_feedback）。
2. **恢复对话框信息增强（P1）**：在“发现历史记录”弹窗中显示目标文件夹名与路径预览，降低用户误判；恢复后状态栏提示“已恢复到上次位置”。
3. **状态栏/会话信息增强（P2）**：展示精选计数、浏览速度、当前文件夹名等（已有 session 跟踪基础，补齐展示即可）。
4. **浏览体验（P2）**：按文件夹记忆缩放级别与浏览位置；增加沉浸式全屏模式（隐藏菜单/状态栏）；可选缩略图网格/时间线视图作为第二浏览维度。
5. **可访问性（P3）**：为图片视图补充 VoiceOver 标签、键盘焦点环；按钮与状态文本支持动态字体与高对比度。

### 5.3 稳定性 / 可靠性

1. **崩溃与异常可见性（P1）**：注册 `sys.excepthook` / `NSApplication.reportException`，把未捕获异常连同版本、路径、最近操作写入日志；提供“导出诊断日志”入口。
2. **进度保存单源化（P1）**：合并 HistoryManager 与 FolderManager 两套节流；用“版本号 + 主线程只增不减”的方式避免 worker 清空新 pending；持久化 `current_folder` 并在恢复时校验路径存在性与列表一致性。
3. **后台任务统一执行器（P2）**：收敛散线程到有名字、有界、可优雅关闭的执行器；退出流程统一“停止调度 → 等待关键任务（如进度落盘）→ 释放资源”。
4. **数据竞争清理（P2）**：为 `_file_size_cache` 加锁或改为线程安全结构；为 NSCache 记账增加定期对账（已有 `reconcile()`，纳入定时任务）。
5. **数据库写入原子化（P2）**：进度保存改为“单条 UPSERT + 事务”，减少多表写入窗口。

### 5.4 工程化 / 质量

1. **让覆盖率门槛真实生效（P1）**：CI 中覆盖率失败即失败；优先补 UI 层（views.py 9%、window.py 20%）与弹窗/导航集成测试——这正是两次真实回归漏网的区域。
2. **清零 lint 债务（P1）**：先修源码 9 处；测试层 1187 处多为空白行，可一次性 `ruff check --fix` 批量处理；安装 pre-commit 并接入 CI。
3. **收敛重复实现（P2）**：FolderManager 与 HistoryManager 的保存路径、`_post_to_main`、`load_folder_images` 等重复代码统一到单一实现。
4. **文档去陈旧（P2）**：删除或重写过期的 production-readiness / 多份覆盖率报告，建立单一“当前事实”文档入口。
5. **依赖审计（P1）**：移除未使用的 opencv-python；确认 psutil/Pillow 是否可降级为可选依赖并做运行期降级测试。

### 5.5 产品 / 平台

- **Apple Silicon 支持（P2）**：这是当前最直接的增长机会——改为 universal2 构建并在 arm64 跑通 CI；README 的产品限制即可解除。
- **发布自动化（P2）**：现有 release workflow 已有基础；补上签名/公证（notarization）与自动版本 bump，降低分发门槛（Gatekeeper 场景）。

---

## 六、优先级路线图

| 优先级 | 事项 | 预期收益 |
| --- | --- | --- |
| P0 | 修复目录缓存别名突变（H1） | 消除“精选后文件夹缺图”的正确性 bug |
| P0 | CI 覆盖率门槛硬性生效 + 补弹窗/导航集成测试 | 阻止“历史恢复/弹窗卡死”类回归再发生 |
| P1 | 弹窗统一 sheet、崩溃钩子、进度保存单源化 + current_folder 持久化 | 消除失焦停摆与进度丢失 |
| P1 | lint 清零、pre-commit、依赖审计 | 恢复质量门槛的公信力 |
| P2 | 自适应两阶段解码、预取有界化、FSEvents、内存自适应、universal2 | 性能与平台覆盖面再上一个台阶 |
| P3 | 网格视图、可访问性、沉浸模式、签名公证 | 产品完成度 |

---

## 七、附录：关键证据索引

| 证据 | 位置 |
| --- | --- |
| 懒解码 / 差异化缩略图 | `core/loading/helpers.py`（`load_with_quartz`） |
| 像素内存记账缓存 + reconcile | `core/simple_cache.py` |
| 目录列表缓存返回引用（H1） | `core/file_info_batch_loader.py`（`get_directory_images`） |
| 原地 pop 污染缓存（H1） | `ui/managers/operation_manager.py`（`_remove_current_image_from_sequences`） |
| 双轨进度保存（M2） | `services/history_manager.py` vs `ui/managers/folder_manager.py` |
| current_folder 未持久化（M1） | `core/history.py`（`save_task_progress` / `_build_progress_data`） |
| 弹窗 sheet 化范例 | `ui/managers/folder_manager.py`（`_show_task_history_restore_dialog`） |
| 仍用 runModal（M4） | `ui/managers/operation_manager.py`、`ui/utils/user_feedback.py` |
| 覆盖率阈值未达标 | `pytest.ini`（`--cov-fail-under=45`）+ 全量实测 43.78% |
| CI 软性放行（H2） | `.github/workflows/ci.yml`（`continue-on-error`） |
| 依赖冗余（L2） | `requirements.txt`（opencv-python 零引用） |
| 仅 x86_64（L3） | `tools/package_release.py`（`-arch x86_64`）、README |

---

## 八、执行进度更新（2026-08-05）

按“从低到高（P0→P2，P3 暂缓）”推进后的最新状态：

| 事项 | 状态 | 说明 |
| --- | --- | --- |
| H1 目录缓存别名突变 | ✅ 已修复 | `DirectoryImageListCache` 内部存元组、对外返回副本；7 个新测试 |
| 覆盖率门槛（P0） | ✅ 已达标 | 全量 1571 通过，覆盖率 43.78% → **52.17%** |
| CI 硬门禁（P0） | ✅ 已启用 | 测试/覆盖率失败即失败（移除 `continue-on-error`） |
| 进度保存单源化 + current_folder 持久化（P1） | ✅ 已修复 | 新增列 + 旧库迁移；恢复按路径定位；清理 FolderManager 重复实现；竞态修复 |
| 弹窗统一 sheet + 激活置前（P1） | ✅ 已修复 | 新增 `alert_utils`，operation_manager 与 user_feedback 统一；修复 NSAlertStyle 常量缺失 bug |
| 崩溃可见性（P1） | ✅ 已确认+补测 | 全局异常钩子原本已存在，新增测试覆盖 |
| lint 清理（P1） | ✅ 源码清零 | 源码 9 处→0；测试层空白行 1078 处自动清理，残留 120 处语义级问题 |
| 依赖审计（P1） | ✅ 已完成 | 移除零引用的 opencv-python |
| 有界预取队列（P2） | ✅ 已实现 | `BoundedExecutor`：队列满淘汰最旧过期任务，修复瞬时完成自锁 |
| 系统内存警告响应（P2） | ✅ 已实现 | 订阅内存警告通知，主线程紧急清理 |
| 自适应两阶段解码（P2） | ⏸ 暂缓 | 需要真机解码耗时样本校准，已列入既有 P2-1 计划 |
| FSEvents 目录监听（P2） | ⏸ 暂缓 | 运行时验证成本高；mtime 失效机制当前可用 |
| universal2 / Apple Silicon（P2） | ⏸ 暂缓 | 需要构建机与 arm64 环境验证 |
| 测试系统评估（用户第 2 项） | ✅ 已完成 | 见 `docs/TESTING_SYSTEM_ASSESSMENT_2026-08-05.md` |

### 修正后的指标

- 测试：1571 通过 / 13 跳过（此前 1465）
- 覆盖率：52.17%（此前 43.78%）
- 源码 Ruff：0 处（此前 9 处）
- 测试 Ruff：120 处残留（此前 1187 处，已自动清理 1078 处空白行类问题）
