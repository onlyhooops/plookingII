# PlookingII 内存管理极速管线设计（官方方案调研与重构）

> 日期：2026-08-18
> 关联版本：v2.5.5（修复）+ 本设计文档
> 平台：macOS 13.7.8 (22H730)，PyObjC 12.2.1，Python 3.14（打包）

## 一、问题本质（已量化确认）

PyObjC 桥接下，**图像绘制触发的解码位图**挂在主线程全局 NSAutoreleasePool，
该 pool 从不释放 → 长会话线性累积（实测 6 分钟 74MB → 8.5GB）。

### 关键事实链
1. 项目已用 `kCGImageSourceShouldCacheImmediately=False` 创建**懒解码代理**
   （[Apple 文档](https://developer.apple.com/documentation/imageio/kcgimagesourceshouldcacheimmediately)）——懒代理本身不占解码内存（验证 4：记账 1.4GB 时 RSS 仅 83MB）
2. 但主线程 `CGContextDrawImage` 绘制代理时，**ImageIO 解码并缓存像素缓冲**
   （[kCGImageSourceShouldCache](https://developer.apple.com/documentation/imageio/kcgimagesourceshouldcache) 语义：绘制时解码并驻留）
3. 解码缓冲绑定 CGImage 生命周期，**无官方 API 可单独释放已解码缓冲**，只能释放 CGImage 本身
4. CGImage 被缓存/NSCache 持有 → 永不释放 → 累积

### 此前方案的教训（v2.5.3 崩溃）
手写 `NSAutoreleasePool.drain()` 与 PyObjC 对象引用管理冲突 → use-after-free。
**PyObjC 桥接感知的官方接口才是安全路径。**

## 二、官方方案调研结论

| 方案 | 官方性 | 安全性 | 有效性 | 结论 |
|---|---|---|---|---|
| 手写 `NSAutoreleasePool` + `drain()` | 非官方 | ❌ 崩溃（v2.5.3 实证） | 强 | 弃用 |
| `objc.autorelease_pool()` 上下文管理器 | PyObjC 官方 | ⚠️ 多线程解码场景崩溃 | 中 | 弃用 |
| **`objc.recycleAutoreleasePool()`** | **PyObjC 官方** | **✅ 桥接感知** | **✅ 强** | **采用** |

### `objc.recycleAutoreleasePool()` 官方语义
- 文档原文："This releases the global autorelease pool and creates a new one"
- 设计目的：**长期运行 Python 主线程**周期性释放 autoreleased ObjC 对象
- 与手写 drain 的本质区别：PyObjC 内部维护 pool 栈，recycle 只释放
  **无人持有的 autoreleased 对象**，不破坏 Python 侧已持有的引用

### 量化验证（产品真实路径，6000×4000 JPEG）

| 场景 | 修复前 | recycle 后 |
|---|---|---|
| 15 张解码净增 | +2,526MB | +197MB（锁定）|
| 90 次解码 + 6 次 recycle | ~+15GB | **+84MB（平台型）** |
| 持有对象有效性 | — | ✅ 6000×4000 保持可用 |
| 崩溃 | — | 无 |

## 三、落地实现（v2.5.5）

### 1. 主线程周期 recycle（`ui/window.py`）
- `MainWindow.init` 注册 30 秒周期 `NSTimer` → `recycleAutoreleasePool:`
- 回调：`objc.recycleAutoreleasePool()`（主线程，AppKit 要求）
- 仅在 PyObjC 提供该 API 时注册（无则跳过，环境降级安全）

### 2. 视图级解码（v2.5.4，已落地）
- `feature.full_res_browse` 默认 `False`：主线程绘制从全分辨率
  （6000×4000 ≈ 168MB/张）改为视图级（~1920 ≈ 10-20MB/张）
- `_maybe_upgrade_cached_image` 后台全分辨率升级路径跳过

## 四、管线架构（完整设计）

```
┌─────────────────────────────────────────────────────────┐
│ L1 强引用  屏幕显示 ±1 张（HOT3 lock）  1-3 张，绝不淘汰      │
├─────────────────────────────────────────────────────────┤
│ L2 内存缓存 视图级解码图（LRU 硬上限，记账驱动） ≤1.5GB        │
│            懒代理（ShouldCacheImmediately=False）不占解码内存 │
├─────────────────────────────────────────────────────────┤
│ L3 磁盘缓存 解码后的显示级图（~/Library/Caches，OS 管理）     │
├─────────────────────────────────────────────────────────┤
│ L4 周期回收 objc.recycleAutoreleasePool（主线程 30s）       │
│            —— 核心：回收绘制触发的解码位图                    │
└─────────────────────────────────────────────────────────┘
```

**为什么这个组合稳定**：
1. L2 懒代理不占解码内存（官方 API 保证）
2. L4 recycle 回收"绘制时解码"产生的位图（官方桥接感知接口）
3. L1/L3 控制持有量与磁盘兜底
4. 全部使用官方 API，不触碰 PyObjC 引用计数内部机制

## 五、验证与后续

- ✅ 全量测试通过（1619 passed）
- ✅ 内存模拟：90 次解码 + 6 次 recycle 净增 +84MB（平台型）
- 待真机验证：v2.5.5 构建 App 长会话（10min+）perf 报告内存曲线应
  为平台型（峰值受 L2 预算控制，~1.5GB 内），导航 p95 应回落
- 可选后续：L3 磁盘缓存落地（P3-4 已有 `dimension_cache` 先例，
  可扩展为图片数据缓存）；导航 p95 ~400ms 独立排查（与内存泄漏解耦）
