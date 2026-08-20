# 图片显示管线调研报告（qView 与 macOS 开源生态）

> 调研日期：2026-08-20
> 背景：PlookingII v2.8.0 实机会话（`logs/perf_20260820_202637.json`）显示
> 内存 74.7MB → 20.9GB，看门狗阈值触发正常但回收无效。本次调研回答：
> **业界成熟的图片浏览器如何组织显示/解码管线？对 PyObjC 应用的最佳
> 技术路线是什么？**

---

## 〇、结论速览（TL;DR）

1. **qView**（Qt/C++）：后台线程全量解码 → QPixmap → QGraphicsView；
   QCache 按内存成本 LRU（默认 250MB）。不处理超大图、不分片。它没有
   内存问题的原因是 **C++ RAII 确定性释放**，不存在 PyObjC 的 autorelease
   pool 问题——其架构思想（后台线程解码）可借鉴，但机制不可移植。
2. **Apple 官方模式**：超大图唯一推荐是 **PhotoScroller 模式**
   （CATiledLayer + CGImageSource 分片按需解码），Preview.app 同源。
3. **本应用实测（6000×4000 JPEG，真实 NSView）**：
   | 解码位置/方式 | 泄漏 |
   |---|---|
   | 主线程 NSImage | +11MB/张 |
   | 常驻池线程（ThreadPoolExecutor，永不退出）NSImage | +10MB/张 |
   | **新线程（任务结束即退出）NSImage** | **~0（30 张 +0.1MB）** |
   | 懒代理创建（任意线程） | ~0 |
   | 懒代理绘制（任意线程，缓冲归 CGImage） | ~0 |
   | **图层后备 wantsLayer=True 显示（主线程）** | **+3MB/张（视网膜更大）** |
   | 图层后备关闭后显示 | ~0 |
   | 缩略图 eager（ShouldCacheImmediately=True） | +1.63MB/张 |
   | 缩略图 lazy（ShouldCacheImmediately=False） | +0.01MB/张 |
4. **根因**：PyObjC 仅在**线程退出**时 drain 该线程 autorelease pool；
   主线程与常驻线程池永不退出 → 池内 ObjC 对象永不释放。看门狗只能回收
   Python 可达引用，池内存不可达 → 回收无效（与 v2.8.0 实测吻合）。
5. **推荐路线（v2.9.0）**：显示管线保持 CGImage 直通不变，叠加三条内存
   规则——① 关闭图层后备（已改，v2.8.1）；② 一切解码走**临时线程**
   （任务结束即退出，替代常驻池）；③ 懒代理/懒缩略图为主路径（已改）。

---

## 一、qView 显示管线（源码分析）

仓库：https://github.com/jurplel/qView （Qt 5/6，C++，约 7600 行）

### 1.1 加载流程

```
loadFile() ──► QtConcurrent::run(readFile) ──► QImage（全量解码，后台线程池）
                  │                                 │
                  └── QFutureWatcher::finished ──► loadPixmap()（主线程）
                                                        │
                                                        ▼
                                              QPixmap → QGraphicsPixmapItem → QGraphicsView
```

- `readFile()`：`QImageReader` 全量解码 + 色彩空间转换（`targetColorSpace`），
  在 Qt 全局线程池（QThreadPool）后台执行——UI 永不因解码阻塞。
- `loadPixmap()`：主线程把 QImage 转 QPixmap（QImage 跨线程安全）。
- 显示：`QGraphicsView` + `QGraphicsPixmapItem`；`makeUnscaled()` 显示
  全尺寸；缩放时 `scaleExpensively(mappedPixmapSize)` 预生成**显示尺寸
  缩放图**（避免每帧 GPU 缩放全分辨率图）。

### 1.2 缓存与预取

- `static QCache<QString, ReadData> imageCache`：**按 KiB 成本 LRU**；
  默认 `PreloadingMode=1` → 上限 250MB（模式 2 → 2GB，模式 0 关闭）。
- 预取距离 1~4 张（默认 1），预取解码同样走线程池。
- **超大文件（> maxCost/2）不缓存**：只显示不缓存，防止缓存被单图撑爆。

### 1.3 超大图处理

**没有**分片/懒解码：一律全量解码。仅有的缓解：
后台线程解码（UI 不卡）+ 不缓存超大文件。qView 不做 100MP+ 图集的
专用优化。

### 1.4 对 PlookingII 的启示

- ✅ 可借鉴：**解码全部在后台线程**；QCache 式成本 LRU（我们已有
  NSCache 等价物）；缩放用预生成缩放图（我们的 CGContextDrawImage
  由 GPU 缩放，等价且无需额外内存）。
- ❌ 不可移植：其内存安全来自 C++ RAII；PyObjC 的 ObjC 对象受
  autorelease pool 生命周期约束（见第二节），照搬"线程池后台解码"
  反而会踩坑——**Qt 线程池是常驻线程，在 PyObjC 下等于主线程的泄漏
  行为（实测 +10MB/张）**。

---

## 二、PyObjC autorelease pool 生命周期的实测规则

（本节为本次调研补充的实机实验，6000×4000 JPEG，venv Python 3.14）

### 2.1 关键实验

| 实验 | 结果 |
|---|---|
| 主线程 `NSImage.initWithContentsOfFile_` ×10 | +111.6MB（+11MB/张） |
| 同一常驻线程 ×30（线程不退出） | +301MB（+10MB/张） |
| **新线程（每任务一线程，退出后测量）×30** | **+0.1MB** |
| 懒代理（CGImageSourceCreateImageAtIndex）创建 ×20 | +0.0MB |
| 懒代理 + CGBitmapContext 全图绘制 ×10 | +0.0MB |
| **图层后备 NSView 显示 ×20（默认 wantsLayer=True）** | **+60MB（+3MB/张）** |
| 同视图 `setWantsLayer_(False)` ×15 | +0.01MB/张 |
| 缩略图 eager（ShouldCacheImmediately=True）×30 | +48.8MB（+1.63MB/张） |
| 缩略图 lazy（ShouldCacheImmediately=False）×30 | +0.4MB |

### 2.2 结论（三条铁律）

1. **池生命周期 = 线程生命周期**：PyObjC 为每个线程懒创建 autorelease
   pool，**只在线程退出时 drain**。主线程与 `ThreadPoolExecutor` 常驻
   线程永不退出 → 池内解码缓冲永不释放。这解释了：
   - 历史会话 8.6GB/18.6GB 的增长（解码发生在主线程与 `imgmgr_*`/`prefetch_*`
     常驻池线程）；
   - v2.8.0 看门狗失效（evict 缓存只释放 Python 可达引用，池内存不可达）。
2. **懒代理（ShouldCache=False）不依赖池**：解码缓冲归 CGImage 自身
   （CF Create 语义），PyObjC 包装器释放即回收，任意线程安全——这是
   PyObjC 下唯一"创建与显示都零泄漏"的原图保真路径。
3. **图层后备是主线程的隐藏泄漏源**：wantsLayer=True 每次显示把视图
   尺寸后备位图塞进主线程池（视网膜下 15~30MB/次）——v2.8.0 会话
   18.6GB 的主源。关闭后实测零泄漏，绘制逻辑不变。

---

## 三、macOS 生态调研

### 3.1 Apple 官方模式：PhotoScroller（CATiledLayer + CGImageSource）

Apple 官方示例 [PhotoScroller](https://developer.apple.com/library/archive/samplecode/PhotoScroller/)（WWDC 2010-2012 多次演示）与
[jessedc/CATiledLayer-2012 分享资料](https://github.com/jessedc/CATiledLayer-2012) 确立了
Apple 平台处理超大图的**唯一官方推荐模式**：

```
CGImageSource（懒解码，ShouldCacheImmediately=False）
  └─ CATiledLayer.drawLayer:inContext: 中按可见 tile 矩形
       CGImageCreateWithImageInRect 裁剪 → CGContextDrawImage
       （tile 尺寸 256~512px，多级 levelsOfDetail 支持缩小显示）
```

要点：**源图只创建一次懒代理，系统仅请求可见 tile**；每个 tile 是独立
CF 对象、绘制即弃 → 解码内存与可见面积成正比，与图幅无关。Preview.app
对超大图即此路线。StackOverflow 上 [NSImageView 大图性能问题](https://stackoverflow.com/questions/45191237)与
[大图显示方案](https://stackoverflow.com/questions/27255438) 的共识同样是
"NSImageView 不适合大图，应自绘（drawRect/CATiledLayer）+ 懒解码"。

### 3.2 xee（Objective-C，开源）

[xee](https://github.com/Metal-Snake/xee)（经典 macOS 查看器，Cocoa/Objective-C，
带 retina 改进版）：以 CGImageSource 为加载核心（XeeCGImageSource/
XeeImage），NSImage 包装显示；无分片渲染，超大图不做专门处理。其年代
（2005-2012）早于大图时代，架构对我们是"历史参照"而非"更优方案"。

### 3.3 Loupe（macOS Sequoia 默认查看器，闭源）

无可信逆向分析公开资料。可观察行为：打开超大图即显示完整画质、滚动
流畅、内存无明显飙升——与"CGImageSource 懒解码 + 按需（分片/GPU）渲染"
一致，即 PhotoScroller 路线的当代实现。

### 3.4 其他生态结论

- **qimgv / nomacs（Qt）**：与 qView 同构（后台线程全量解码 + 缩放图），
  受 Qt RAII 保护无池问题，同样不做分片。
- **缩略图接口的取舍**：react-native 曾因 `CGImageSourceCreateThumbnailAtIndex`
  行为问题改回 `CGImageSourceCreateImageAtIndex` 解码全尺寸图——印证
  缩略图 API 用于"最终显示"有陷阱；我们已改为 lazy 缩略图（只做预览占位）。
- **对本项目的直接结论**：macOS 原生生态不存在"既保持原图质量、又不
  依赖线程退出回收"的银弹——**要么 CATiledLayer 分片（内存 ∝ 可见面积），
  要么按线程生命周期管理解码池（内存 ∝ 在途任务）**。我们的实测表明
  后者在 PyObjC 下可简单实现（临时线程），且不改变显示管线。

---

## 四、推荐技术路线（v2.9.0）

### 4.1 架构

```
显示（主线程，管线不变）
  AdaptiveImageView.drawRect → CGContextDrawImage（全分辨率原图）
  ├─ 图层后备：关闭（v2.8.1，已改，实测零泄漏）
  └─ 超大图（≥50MP，可选）：TiledImageView（CATiledLayer 分片，
     PhotoScroller 模式，已有实现待真机验证）

解码（全部走"临时线程"——任务结束线程退出 → 池被 drain）
  临时线程工厂：run_decode(fn) 每任务新建 daemon 线程并 join/回调
  ├─ 主路径：懒解码 CGImage 代理（任意线程安全，v2.8.0/2.8.1 已改）
  ├─ 缩略图/预览：lazy（ShouldCacheImmediately=False，v2.8.1 已改）
  └─ NSImage 回退（Quartz 不可用等）：仅在临时线程中创建

缓存/回收
  NSCache 成本 LRU（已有）+ MemoryWatchdog（已有）
  └─ 新增动作：周期性重建解码线程池（shutdown+recreate）以 drain
     常驻池线程（替代"解码任务迁移到临时线程"的过渡兜底）
```

### 4.2 具体落地清单

1. **（v2.8.1，已完成，待发布）**
   - `views.py` AdaptiveImageView/OverlayView 关闭图层后备；
   - `image_view_controller.py` 容器关闭图层后备；
   - `helpers.py` JPEG 缩略图 `ShouldCacheImmediately` → False；
   - `strategies.py` `_load_large` 优先懒代理（内存映射降为回退）。
2. **（v2.9.0）临时线程解码**
   - 新增 `plookingII/core/decode_threads.py`：`run_decode(fn)` 在新建
     daemon 线程执行并等待结果（线程退出 → 池 drain），供 NSImage 回退
     路径与 MPF 提取（`extract_embedded_preview` 的 NSData 创建）使用；
   - `_executor`/`_prefetch_executor` 中的解码类任务迁移到临时线程，
     或由 MemoryWatchdog 在 RSS 越过预防阈值时重建两个线程池。
3. **（v2.9.0，可选）超大图分片**：`TILED_RENDERING_ENABLED` 按像素
   阈值开启（需真机验证 CATiledLayer 表现）。

### 4.3 预期效果

- 显示零泄漏（wantsLayer=False 实测）+ 解码零泄漏（临时线程实测）
  → 长会话 RSS 应呈平台型（受 NSCache 预算 ~2-4GB 控制）。
- 导航 p95 与内存脱钩（当前 p95 396ms 的慢事件集中在内存膨胀期）。
- 全量质量不变：全程原图（懒代理全分辨率），无降采样。

---

## 五、参考

- qView 源码：https://github.com/jurplel/qView
- Apple PhotoScroller 示例（CATiledLayer + CGImageSource 分片模式）
- CATiledLayer 详解与 JCTiledScrollView：
  https://github.com/jessedc/CATiledLayer-2012
- xee（经典 macOS 查看器）：https://github.com/Metal-Snake/xee
- NSImageView 大图性能讨论：https://stackoverflow.com/questions/45191237 、
  https://stackoverflow.com/questions/27255438
- 本报告实测数据：`logs/perf_20260820_202637.json`（v2.8.0 实机会话）、
  `/tmp/plooking_mem_experiment{1,2,3,4}.py` 系列实验（6000×4000 JPEG）
