# PlookingII 性能优化后续计划（P2/P3）

> 文档日期：2026-08-04
> 关联迭代：本轮已落地 P0（快赢）与 P1（核心优化），本文档承接 P2（进阶）与 P3（长期/架构）后续计划。

## 一、本轮已落地内容（背景）

### P0 — 快赢（已完成）

| 编号 | 内容 | 主要改动 |
|---|---|---|
| P0-1 | 精选计数内存化 + 后台校准 | `OperationManager` 增加 `_keep_count_cache`，导航热路径不再主线程 `os.scandir` 精选目录；30s 后台重校兜底外部改动 |
| P0-2 | 尺寸缓存改真正 LRU 并扩大 | `_image_dimensions_cache` 上限 200 → 2000，插入序淘汰改为 `OrderedDict.move_to_end` 真正 LRU |
| P0-3 | 内存状态采样加 TTL | `UnifiedMonitor.get_memory_status()` 增加 500ms 缓存；后台监控循环用 `force=True` 保持新鲜 |
| P0-4 | 热路径 DEBUG 日志降噪 | `SimpleImageCache.get/put` 移除逐次 HIT/MISS/PUT 落盘日志，命中统计保留 |

### P1 — 核心优化（已完成）

| 编号 | 内容 | 主要改动 |
|---|---|---|
| P1-1 | 主线程元数据 I/O 移出导航热路径 | 竖向判定/像素阈值仅读缓存（`_get_cached_dimensions_only`），未知时保守走后台；`prewarm_dimensions` 批量预热尺寸；元信息任务改走 prefetch 池 |
| P1-2 | 内嵌预览提取改异步 | `_try_embedded_preview` 从主线程同步读取改为 `_schedule_embedded_preview_async` 后台提取；无 MPF 结果 LRU 缓存；`_full_shown_generation` 防止预览覆盖已显示的全分辨率画面 |
| P1-3 | 状态栏更新批处理与去重 | `MainWindow._update_status_display_immediate` 改为 50ms 合并刷新；删除导航中每次按键的无效状态刷新 |
| P1-5 | 文件夹跳转异步化 + 邻目录预扫描 | `jump_to_next/previous_folder` 改走 `_start_async_folder_load` 后台加载（代次保护）；进入文件夹后 `_prefetch_neighbor_folder_lists` 预热相邻目录图片列表 |

> 注：P1-4「EXIF 方向修正」已按项目决策回退移除——本项目不处理 EXIF 方向，
> 图片集在筛选前由外部工作流统一纠正朝向。相关渲染变换、方向缓存与
> 缩略图 `WithTransform` 已全部清理，解码/渲染保持零拷贝直绘。

---

## 二、P2 — 进阶优化（建议 2 周内）

### P2-1 解码耗时自适应两阶段显示

**现状**：`_maybe_two_stage_for_ultra` 只对 ≥80MB 或 ≥24MP 的文件启用“预览→全清晰度”两阶段；中低端机器上，文件不大但解码慢（外置盘、高压缩 JPEG）时仍单阶段，首帧等待较长。

**方案**：
1. 把每次 `load_image` 的实际解码耗时（monitor 已有 `load_image` 时长）按文件大小/像素维度归档到经验表；
2. 当同一规格文件的实测耗时超过阈值（如 150ms）时，自动为其走两阶段（先用 subsampling 缩略图显示，再懒解码全分辨率替换）；
3. 经验表带 LRU 上限与重置入口，避免长期运行无界增长。

**改动点**：`image_manager._maybe_two_stage_for_ultra`、`monitor.record_operation` 数据消费。

**预期收益**：中低端机器快速浏览时首帧更早可见，且不牺牲全分辨率清晰度。

**风险**：中。需要保证“经验表命中”与真实设备/磁盘状态一致，建议以近 N 次实测为准，避免陈旧数据误判。

### P2-2 解码线程池有界队列 + 旧任务丢弃

**现状**：`_executor` / `_prefetch_executor` 队列无界，快速导航时可能积压大量任务（虽有代次检查提前退出，但队列本身会增长）。

**方案**：
1. 提交前检查 `ThreadPoolExecutor._work_queue.qsize()`，超过上限（如关键池 8、预取池 6）时丢弃新预取任务；
2. 关键路径（当前图解码、next-ready）保留专用提交接口，不允许丢弃；
3. 为预取任务增加“排队超时即弃”语义，进一步降低积压。

**改动点**：`image_manager._start_background_load` / `_schedule_adaptive_prefetch` / `_schedule_embedded_preview_async` 的提交入口。

**预期收益**：快速导航时线程池行为可预测，关键解码不被积压任务延迟。

### P2-3 深度扫描结果复用，消除重复枚举

**现状**：根目录两阶段扫描中，`_scan_subfolders` 对每个目录执行 `_dir_contains_images`（全量枚举），随后加载首文件夹时又枚举一次；`FileInfoCache` 只缓存逐文件条目，枚举本身仍重复。

**方案**：
1. 给 `DirectoryImageListCache` 增加“目录是否含图”布尔结果缓存（同样以目录 mtime 失效）；
2. 深扫期间顺带把扫描到的图片列表写入目录缓存，供 `get_directory_images` 直接命中；
3. `_dir_contains_images` 改为先查布尔缓存。

**改动点**：`file_info_batch_loader.py`、`folder_manager._scan_subfolders` / `_dir_contains_images`。

**预期收益**：数千目录的大目录树打开时扫描耗时明显下降。

### P2-4 渲染路径统一（drawRect 复用缓存）

**现状**：CGImage 分支 `drawRect_` 内联计算边距/缩放/居中，与 `_get_image_display_rect` 重复且不一致。

**方案**：
1. CGImage 分支改用 `_get_image_display_rect` + `_get_transformed_rect`，删除内联重复计算；
2. 缩放/平移时复用缓存几何，减少重复计算；
3. 为 P3-1 的 CATiledLayer 方案预留统一的“显示矩形 + 变换”抽象。

**改动点**：`views.py drawRect_` / `_get_image_display_rect`。

**预期收益**：代码一致性 + 减少重复几何计算，并为后续分片渲染铺路。

---

## 三、P3 — 长期 / 架构级优化

### P3-1 超高分辨率浏览启用 CATiledLayer / 异步绘制

**现状**：全分辨率 CGImage 懒代理首次绘制时由 GPU 同步解码，10000px+ 图片首帧仍可能出现卡顿。

**方案**：浏览大图时视图层改用 `CATiledLayer`（或 `setLayerContents` + 分片绘制），仅解码并显示可见区域，与懒解码代理配合实现真正的 Preview.app 式“按需渲染”。

**风险**：高，涉及渲染架构改动。先做原型并对比首帧延迟、滚动流畅度、内存占用，达标后再合并。

### P3-2 建立可重复的性能基准

**现状**：项目无基准脚本，monitor 数据未持续收集，优化效果难以量化与防回归。

**方案**：
1. 新增 `scripts/benchmark.py`：合成不同尺寸/格式的图片集；
2. 度量：① 首图加载延迟；② 连续 100 次翻图的主线程阻塞时间（RunLoop tick 间隔）；③ 缓存命中率；④ RSS 内存曲线；⑤ 文件夹跳转延迟（不含 EXIF 方向，项目不处理方向信息）；
3. 输出 JSON 基线，纳入 CI（可选 `benchmark` 标记），每次性能改动跑回归。

**预期收益**：所有优化效果可量化、可防回归。

### P3-3 代码清理：移除休眠模块

**现状**：`core/preload_manager.py` 的 `PreloadManager` / `PreloadExecutor` 因 `feature.disable_bidi_preload` 默认 True 已休眠，实际预取逻辑在 `ImageManager`，存在两套预取逻辑并存的维护成本。

**方案**：删除休眠模块或明确标记废弃并迁移文档；同步清理关联测试与引用。

### P3-4 会话内图片元数据持久化缓存（可选）

**现状**：尺寸元数据缓存为会话内 LRU，跨启动不保留；大目录每次打开仍会重新读取元数据。

**方案**：以目录 mtime 为失效键，将目录级“文件名 → 尺寸”缓存写入应用支持目录（如 `~/Library/Application Support/PlookingII/`），二次打开同一目录直接命中。

**风险**：中。需处理目录变更、文件删除、缓存文件损坏等边界，建议先做只读缓存 + 严格校验。

---

## 四、度量与验收标准

| 指标 | 采集方式 | 目标 |
|---|---|---|
| 单次翻图主线程耗时 | `_execute_image_display_flow` 前后插桩 / RunLoop tick 间隔 | 较基线下降 ≥30%（重点在外置盘/网络盘场景） |
| 缓存命中率 | `image_cache.get_stats()` | ≥90% |
| 首帧显示延迟 | `show_current_image` → `_apply_display` 时间差 | 按文件大小分档记录，大图 ≤200ms |
| RSS 内存曲线 | `psutil.Process().memory_info()` 每 10s | 长会话不超过缓存预算（当前 2–4GB） |
| 文件夹跳转延迟 | `jump_to_next/previous_folder` → 首图显示 | 大文件夹（万张）≤300ms |
| 状态栏更新频率 | `update_status_display` 调用计数/秒 | 快速翻图时 ≤20Hz |
| 精选计数准确性 | 批量 keep/undo 后校验 | 与磁盘实际一致 |

---

## 五、实施顺序建议

1. **第 1 周（P2）**：P2-2 线程池有界（低风险）→ P2-3 扫描复用（低风险）→ P2-1 自适应两阶段（中风险）；
2. **第 2 周（P2）**：P2-4 渲染路径统一，同时开始 P3-1 原型；
3. **第 3–4 周（P3）**：P3-2 基准脚本（建议尽早启动，与 P2 并行）；P3-1 原型评估后决策；P3-3/P3-4 视评估结果排期。

> 建议任何一项合入前先跑 `pytest` 全量回归（当前基线 1904 passed），并对照上表指标留档。
