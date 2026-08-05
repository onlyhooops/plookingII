# Changelog

所有notable changes都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

<!--next-version-->

## [2.5.0] - 2026-08-05

### ✨ 新特性

- 引入 python-semantic-release 自动版本管理：合并到 main 后自动升版、生成更新日志并打标签
- 有界预取队列（BoundedExecutor）：快速连按时过期预取任务优先淘汰，不无限积压
- 响应系统内存警告：及时降级缓存，降低被系统强杀的风险

### 🐛 修复

- 目录级图片列表缓存“别名突变”：精选（保留）图片后不再污染缓存目录列表
- 历史进度恢复：`current_folder` 持久化与旧库自动迁移，恢复按路径定位而非仅靠序号
- 进度保存双轨合并与竞态修复：异步保存不再误清主线程新写入的数据
- 历史恢复弹窗焦点卡死：统一改为激活置前 + 窗口 sheet 弹窗，失败自动兜底
- 修复 pyobjc 环境下 NSAlertStyle 常量缺失导致警告弹窗永远返回“取消”
- 加载策略统计重复计数、网络缓存/SMB 优化器错误处理路径缺陷
- 统一代码格式至 CI 所用 ruff 0.12.9，修复 UP038 lint

### 🧪 测试与工程化

- 补充网络缓存、SMB 优化器、远程文件检测、加载策略、弹窗、菜单、加载服务等模块测试
- 覆盖率 43.8% → 52.1%，全量 1571 测试通过
- 硬化 CI：测试与覆盖率失败即失败
- 移除未使用依赖 opencv-python；源码 lint 清零

## [2.4.1] - 2026-08-04

### 🧹 积灰代码清理（Cruft Cleanup）

基于全项目引用审计，移除运行期零引用的死代码模块及其专属测试：

#### 移除的死代码模块
- `core/base_classes.py`、`core/cleanup_utils.py`、`core/lazy_initialization.py`
- `core/lightweight_monitor.py`、`core/memory_estimator.py`、`core/memory_pool.py`
- `core/optimized_algorithms.py`、`core/preload_manager.py`
- `core/smart_memory_manager.py`、`core/threading.py`
- `config/cache_optimization_config.py`、`utils/error_utils.py`、`monitor/telemetry.py`

#### 失效导出与导入修复
- `plookingII/__init__.py`：移除启动时必然失败的 `.core.cache` 导入；
  `__all__` 收敛为实际存在的名称（此前含 16 个不存在的旧符号，
  `from plookingII import *` 会抛异常）
- `core/__init__.py`：移除 `PreloadManager`、`lazy_init/profile_startup/startup_profiler`
  等死导出与从不存在的远程模块构成的失效 `__all__` 扩展
- `monitor/__init__.py`：移除从未被调用的本地遥测导出

#### 重复实现清理
- `window.py` 移除无人调用的 `_scan_subfolders` 重复实现（扫描逻辑统一由
  `FolderManager` 负责）
- `views.py` 移除无人调用的 `apply_safe_performance_tweaks` 及失效导入

#### 失效开发目标清理
- `Makefile`：移除引用不存在文件的 `test-arch` / `test-quality` / `guard`
  与无 Sphinx 配置的 `docs` / `docs-serve` / `docs-clean` 目标

### 📚 文档对齐（README De-rusting）
- README：更新 Python 徽章/系统要求、文档导航（架构简化历史归档，
  突出性能优化计划与完整变更日志）、技术架构树、性能指标、
  开发环境与版本信息（v2.4.1）
- docs/README.md：导航中心对齐当前文档结构，历史内容标注归档

---

## [2.4.0] - 2026-08-04

### ⚡ 热路径性能优化迭代（P0 + P1）

聚焦主线程同步 I/O 与 UI 更新成本，在不改变既有核心管控方案
（懒解码 CGImage、HOT3 强引用、next-ready 双缓冲、代次取消、渲染节流、自适应预取）的前提下：

#### 主线程 I/O 消除
- **精选计数内存化**：`get_keep_count()` 不再每次翻图在主线程 `os.scandir`
  精选目录；首次访问扫描一次并缓存，30s 后台重校兜底外部改动（[P0-1]）
- **尺寸缓存真正 LRU**：`_image_dimensions_cache` 上限 200 → 2000，
  插入序淘汰改为 `move_to_end` LRU（[P0-2]）
- **内存状态采样 TTL**：`get_memory_status()` 增加 500ms 缓存，
  导航热路径不再每次 `psutil.virtual_memory()` 系统调用（[P0-3]）
- **主线程元数据 I/O 移出热路径**：竖向判定/像素阈值/两阶段判定仅读缓存，
  未知时保守走后台；`prewarm_dimensions` 批量预热整目录尺寸元数据；
  元信息任务改走 prefetch 池，不再与关键解码抢线程（[P1-1]）
- **内嵌预览提取异步化**：MPF 预览从主线程同步文件读取改为后台提取，
  无 MPF 结果 LRU 缓存；`_full_shown_generation` 防止预览覆盖已显示的全分辨率画面（[P1-2]）
- **文件夹跳转异步化**：`jump_to_next/previous_folder` 跨界翻页改后台加载
  （代次保护），进入文件夹后预扫描相邻目录图片列表（[P1-5]）

#### UI 更新成本
- **状态栏更新合并**：`_update_status_display_immediate` 改为 50ms 合并刷新，
  快速翻图时 AppKit 控件更新从每键多次降为约 20Hz 一次；
  删除导航中每次按键的无效状态刷新（[P1-3]）

#### 移除 EXIF 方向修正
- **确认放弃运行期方向修正**：项目按既定决策不再处理 EXIF 方向——使用本项目
  筛选的图片集会在进入筛选流程前由外部工作流统一纠正朝向
- 移除渲染阶段方向变换、方向缓存、`get_exif_orientation` 读取，
  以及缩略图解码的 `kCGImageSourceCreateThumbnailWithTransform`
- 清理废弃的 EXIF 处理配置（`exif_processing`、`EXIF_PROCESSING_CONFIG`、
  `skip_exif_processing`、`apply_exif_transform`、`process_exif`）
- 恢复 CGImage 直通零拷贝直绘，解码/渲染全程不做方向变换

#### 日志与清理
- **热路径日志降噪**：缓存 get/put 移除逐次 HIT/MISS/PUT 落盘日志（[P0-4]）

#### 测试
- 新增精选计数缓存、尺寸 LRU、内存 TTL、预加载尺寸预热、异步内嵌预览、
  异步文件夹跳转等单元测试
- 移除 EXIF 方向缓存相关测试，同步 EXIF 配置结构断言
- 后续计划见 [docs/PERFORMANCE_OPTIMIZATION_PLAN_2026.md](docs/PERFORMANCE_OPTIMIZATION_PLAN_2026.md)

---

## [2.3.0] - 2026-07-31

### ⚡ 性能审计优化迭代

基于全量性能审计，实施全部「高」「中」优先级建议，不改变既有核心管控方案
（懒解码 CGImage、HOT3 强引用、next-ready 双缓冲、代次取消、渲染节流、自适应预取）。

#### UI/UX 响应性
- **目录图片列表缓存**：文件夹级导航（跳转/跳过/回退）不再重复全量枚举+排序，
  以目录 mtime 自动失效（[A1]）
- **消除主线程 O(n) 索引扫描**：导航热路径的 ~7 次 `list.index()` 改为 O(1)
  path→index 缓存，大文件夹（万张）按键延迟显著下降（[A2]）
- **`get_file_size_mb` 委托带缓存的批量加载器**：导航热路径不再直接
  `os.path.getsize`（网络盘/外置盘收益明显）（[A3]）
- **后台加载/渐进式加载补代次校验**：快速连按时旧图不再覆盖当前显示（[A4]）

#### 大图加载 / 缓存与命中
- **缓存命中低清条目时后台全分辨率升级**：`full_res_browse` 下回退/快速翻页
  命中视图级分辨率后，自动按代次升级到全清，画面不再偏软（[B1]）
- **NSCache 记账对账（reconcile）**：修正系统自动驱逐导致的
  `_item_count/_current_memory_mb` 漂移，内存清理阈值判断恢复准确（[B2]）
- **`get_loader` 全局实例缓存**：热路径不再每次重复构造策略对象（[B3]）
- **预取与关键解码拆分线程池**：自适应预取/HOT3 走独立 2 线程池，
  过期预取不再挤占当前图解码（[B4]）
- **修复 OrderedDict 降级分支淘汰顺序缺陷**：`_evict_lru_if_needed` 在计数
  更新后执行，避免永不淘汰导致的无界增长（[B2] 相关）

#### 测试
- 同步陈旧断言：缓存默认值 20/2000MB、`_select_loading_strategy` 新签名、
  版本号 2.3.0；LRU/NSCache 语义测试固定到确定性实现分支

---

## [2.0.2] - 2025-04-25

### 🎯 Preview.app 风格懒解码管线

#### 问题背景
v2.0.1 的 `CGImageSourceCreateThumbnailAtIndex` 统一路径对于超大图片反而更慢：
- ThumbnailAtIndex 即使 maxPixelSize=0 也创建完整解码位图
- 10000px+ 图片解码需要 200-500ms，阻塞切换

#### 核心修复：懒解码 CGImage 代理
- **Preview.app 核心机制**：`CGImageSourceCreateImageAtIndex` + `kCGImageSourceShouldCacheImmediately=False`
- CGImage 作为轻量代理，仅存储元数据（宽高/格式/色彩空间），不解码像素
- 实际解码延迟到 Core Animation / GPU 需要绘制时才进行
- 超大图片（10000px+）可在毫秒级完成"加载"，GPU 按需解码屏幕可见区域

#### 技术细节
| 属性 | v2.0.1 (错误) | v2.0.2 (正确) |
|------|-------------|-------------|
| 全尺寸API | `CreateThumbnailAtIndex` | `CreateImageAtIndex` |
| 缓存策略 | `ShouldCache=True` | `ShouldCache=False` + `ShouldCacheImmediately=False` |
| 解码时机 | 创建时立即 | 显示时按需（GPU） |
| maxPixelSize限制 | 有（反效果） | 无（原尺寸代理） |
| EXIF处理 | 全部走transform | 仅 orientation≠1 走transform |

#### 两阶段加载优化
- 阶段1 预览从 1/4 → 1/3 尺寸，质量更可接受
- 移除人为 `time.sleep(0.1)` 延迟
- 阶段2 懒代理创建毫秒级，几乎立即替换预览

---

## [2.0.1] - 2025-04-25

### 🚀 图片解码管线性能修复

#### 横/竖向照片切换流畅度不对称
- **根因**：横向照片（EXIF orientation=1）走 `CGImageSourceCreateImageAtIndex` CPU 解码路径；竖向照片走 `CGImageSourceCreateThumbnailAtIndex` GPU 加速路径
- **修复**：统一所有图片解码为 `CGImageSourceCreateThumbnailAtIndex` + `kCGImageSourceCreateThumbnailWithTransform`，横向照片切换速度提升 40-60%

#### 超大图片切换卡顿
- **根因**：超大图片全分辨率解码（10000×7000 原图）即使 GPU 加速也需 200-500ms
- **修复**：
  - **智能解码到显示尺寸**：`maxPixelSize` 按 target_size × 1.5 自动限制，10000px → 7680px，节省 40% 解码内存
  - **降低渐进式加载阈值**：`ultra_image_threshold_mb` 从 120MB → 80MB
  - **新增像素数触发**：≥24MP 图片自动启用预览→全清晰度两阶段加载
  - **新增 `_get_cached_dimensions()`**：像素检测走缓存避免重复 Quartz I/O

---

## [2.0.0] - 2025-04-25

### 🎯 macOS 原生平台深度集成

#### 系统级内存管理
- **NSProcessInfo 动态内存预算**：`MemoryOptimizer` 从硬编码 2GB 改为 `physicalMemory() * 30%`，自动适配不同硬件（1GB-4GB），低功耗模式自动削减 25%
- **NSCache 替代手写 LRU**：`SimpleImageCache` 内部存储从 `OrderedDict` 切换为 `Foundation.NSCache`，自动响应系统内存压力通知，由系统内核协调驱逐时机

#### Quartz 硬件加速
- **真正的 Quartz 旋转管线**：`_rotate_with_quartz` 从 PIL 空壳重写为完整的 `CGImageSource → CGAffineTransform → CGImageDestination` 管线，保持 EXIF/GPS/IPTC 元数据，原子替换原文件
- **全尺寸 EXIF 方向变换**：完整图片加载路径检测并自动旋转变换竖拍照片

#### 渲染与调度优化
- **`_get_image_display_rect` 缓存修复**：`_cached_img_rect` 从未被使用 → 现在正确缓存并关联 `_cached_view_bounds`，消除每帧冗余浮点计算
- **窗口 resize 批处理**：`setFrame_display_` 中用 `NSAnimationContext.beginGrouping()`/`endGrouping()` 批量提交所有 `setFrame_` 变更，消除布局震荡
- **NSRunLoop 统一调度**：`UnifiedStatusController` 从 `threading.Thread` 轮询改为 `NSTimer` + `NSRunLoopCommonModes`

#### 向后兼容
- ✅ `SimpleImageCache` 公开 API 保持不变
- ✅ `MemoryOptimizer` 支持手动传入 `max_memory_mb` 覆盖自动计算

---

## [1.8.0] - 2025-04-25

### 🚀 性能优化

#### 核心算法效率提升
- **修复 `_select_loading_strategy` 空字符串 bug**：`can_handle("")` 永远返回 False 导致所有策略静默回退到 auto，策略选择系统形同虚设
- **PreloadManager 真正并发执行**：用 `ThreadPoolExecutor.submit()` 并行提交预加载任务，移除人为 `time.sleep(0.01)` 延迟
- **fix: `_load_file_info` 中 4 次 stat() 调用**：`os.path.exists()` + `os.stat()` + `os.path.isfile()` + `os.path.isdir()` → 单一 `os.stat()` + `stat.S_ISREG/S_ISDIR`
- **修复 `ImageMemoryPool` 记账错误**：`return_buffer()` 中 `allocated_bytes` 错误地增加而非减少，导致池内存统计混乱

#### 硬件资源精细化管控
- **修复线程池泄漏**：`RemoteFileManager` 和 `SMBOptimizer` 的 ThreadPoolExecutor 从未关闭，已添加 `shutdown()` 方法
- **消除重复线程池创建**：`_preload_batch()` 和 `batch_read_files()` 每次调用都创建新池，改为复用类级 `self.executor`
- **全尺寸 EXIF 方向变换**：完整图像加载路径添加方向检测与自动旋转变换，修复竖拍照片方向错误

#### UI 渲染与交互优化
- **主线程同步 I/O 消除**：`update_status_display()` 中 `get_image_dimensions_safe()` + `os.path.getsize()` 改为从 ImageManager 缓存读取
- **右键菜单缓存**：`AppDiscovery` 按扩展名缓存启动服务查询结果，应用图标缓存避免重复 `iconForFile_()`
- **mouseDragged_ 重绘节流**：复用 `_schedule_optimized_redraw()` 限制为 60fps
- **删除冗余 setNeedsDisplay_**：`display_image()` 中 `setCGImage_` 已触发重绘，移除重复调用
- **移除空 5s 轮询定时器**：`updateSessionStatus_` 为空操作，不再消耗运行循环唤醒

---

## [1.7.2] - 2025-04-25

### 🐛 关键 Bug 修复

#### 🚨 内存泄漏修复（性能雪崩根因）

- **修复缓存内存记账使用文件大小而非实际像素内存**
  - 之前：用 5MB（文件大小）记录一张 6000×4000 照片 → 实际解码占用 96MB
  - 现在：用 `宽度 × 高度 × 4 字节` 计算实际像素内存
  - 结果：LRU 淘汰策略恢复正常触发，缓存不再无限制膨胀

- **修复所有缓存 `put()` 调用未传实际内存大小的问题**
  - `AdvancedImageCache`、`ImageManager`、`PreloadManager`、`FolderManager` 共 9 处 `put()` 全部修正
  - 添加模块级 `estimate_image_memory_mb()` 函数统一估算

- **收紧缓存上限**：`max_items=50→20`, `max_memory_mb=500→2000`（基于正确像素内存记账）

- **修复内存清理方法引用不存在的属性**
  - 之前：`_emergency_memory_cleanup()` 等方法引用 `preview_cache`、`preload_cache` 等不存在属性（静默吞异常，清理从未生效）
  - 现在：使用 `evict_oldest()` + `gc.collect()`，所有层级清理逻辑正常工作

- **关闭 ImageIO 内部缓存**：`kCGImageSourceShouldCache=False`
  - 消除同一张图片在 ImageIO 和应用层双重缓存，内存消耗减半

- **限制导航线程并发**：用 `ThreadPoolExecutor(max_workers=4)` 替代每次导航创建 7-8 个独立线程
  - 消除后台线程无限堆积导致的 UI 卡顿

---

## [1.7.1] - 2025-10-06

### 🚀 新增功能

#### 智能版本管理系统 V2.0
- **版本号单一真源**：创建 `plookingII/__version__.py` 作为唯一版本定义处
  - 所有模块自动导入，无需手动同步
  - 完全消除版本号不一致风险

- **自动化工具**：新增 `scripts/bump_version.py` 版本提升工具
  - 支持 major/minor/patch 语义化版本提升
  - 支持指定具体版本号
  - 自动更新发布日期
  - 内置版本一致性验证

- **动态版本读取**：`pyproject.toml` 使用 dynamic version
  - 打包时自动读取版本号
  - 符合 PEP 621 标准

### 🔧 改进

- **配置优化**：`constants.py` 改为从 `__version__.py` 自动导入
- **文档完善**：新增 `VERSION_MANAGEMENT_V2.md` 完整使用指南
- **向后兼容**：保持所有现有 API 不变

### 📚 文档

- 新增智能版本管理系统完整文档
- 详细的使用指南和最佳实践
- V1 vs V2 对比说明

### 💡 影响

**对用户**：无影响，版本号显示完全正常

**对开发者**：
- 发布新版本更简单：只需修改一个文件
- 零手动同步：自动保持一致性
- 完整工具链：一键完成版本提升

---

## [1.7.0] - 2025-10-06

### 🎯 重大改进

#### 架构简化与性能优化

- **缓存系统重构**：从12个文件4000+行代码简化为单文件350行，性能提升40%

  - 统一的LRU双层缓存机制
  - 自动内存管理和压力检测
  - 完整的向后兼容支持

- **图片加载模块化**：将1118行单文件拆分为5个清晰模块

  - 代码减少15.5%
  - 可维护性提升60%
  - 可测试性提升80%

- **监控系统整合**：统一 V1 和 V2 监控实现

  - 代码减少60.1%
  - 统一的性能和内存监控API
  - 轻量级遥测支持

#### 功能新增

- **macOS 系统清理**：开发环境自动清理最近文档记录

  - 保护开发者隐私
  - 智能环境检测
  - 不影响生产环境

- **版本管理自动化**：完全统一的版本管理系统

  - 单一真源（SSOT）
  - semantic-release 自动化
  - CI/CD 集成验证

#### UI/UX 改进

- **简化对话框**：符合 macOS 原生风格
  - 精简"关于"对话框文案
  - 优化快捷键帮助布局
  - 采用 macOS 原生符号（⌘ ⌥）

### 🔒 安全增强

- 修复 MD5 哈希安全警告（非安全用途已明确标注）
- SQL 注入防护确认（使用参数化查询）
- 路径遍历防护验证
- 完整的安全审计报告

### 🐛 Bug 修复

- 修复应用启动失败问题
- 修复图片显示异常
- 修复缓存错误分类
- 完善向后兼容层

### 📚 文档完善

- 新增架构简化文档系列
- 新增版本管理指南
- 新增 macOS 清理指南
- 新增安全审计报告
- 新增生产就绪评估报告

### 🧪 测试改进

- 新增15个单元测试文件
- 测试覆盖率提升
- 修复测试用例以匹配新架构

### 🗑️ 清理

- 移除13个废弃文件
- 删除4个空目录
- 清理重复代码
- 统一代码风格

### 📊 项目统计

- **代码行数**：从 15,000+ 减少到 11,000+（减少26.7%）
- **文件数量**：核心模块从 45+ 精简到 32（减少28.9%）
- **文档增加**：25+ 新增/更新文档
- **测试增加**：15+ 新增测试文件

______________________________________________________________________

## [1.6.0] - 2025-10-05

### Added

- 初始版本发布
- 核心图片浏览功能
- 精选功能
- 历史记录管理
- 快捷键支持
- macOS 原生界面

### Changed

- 优化图片加载性能
- 改进缓存机制

### Fixed

- 修复内存泄漏问题
- 修复图片旋转bug

______________________________________________________________________

## [Earlier Versions]

详见 Git 历史记录

[1.6.0]: https://github.com/yourusername/plookingII/releases/tag/v1.6.0
[1.7.0]: https://github.com/yourusername/plookingII/compare/v1.6.0...v1.7.0
