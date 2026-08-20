# CHANGELOG


## v2.9.1 (2026-08-20)

### Bug Fixes

- 渐进加载阶段2策略名 quartz→optimized（消除告警刷屏）
  ([`25a9984`](https://github.com/onlyhooops/plookingII/commit/25a99842c2acd86bb40a83a93436f4c28204d150))

实机日志（21:36:55-21:37:07）发现 load_image_with_strategy(img_path, "quartz", ...) 传入未注册策略名，每次触发 get_loader
  告警并回退 auto。 "optimized" 即懒解码代理路径，语义一致且不再告警。

### Chores

- 同步版本断言至 v2.9.0
  ([`8b5fb14`](https://github.com/onlyhooops/plookingII/commit/8b5fb1465c8bfe0398397755a7936b688f8d66db))


## v2.9.0 (2026-08-20)

### Chores

- 同步版本断言至 v2.8.1
  ([`b7bbd98`](https://github.com/onlyhooops/plookingII/commit/b7bbd981dae3505cb21f51f2ffefaa74b7f8954c))

### Features

- 解码走临时线程（线程退出即回收 autorelease pool）——补全内存架构
  ([`5d00d5c`](https://github.com/onlyhooops/plookingII/commit/5d00d5c6c9e26e96cdf9dd80730d6f2d28716bcf))

实机验证结论（见 docs/reports/display-pipeline-research-2026-08-20.md）： PyObjC 只为每个线程懒创建 autorelease pool
  且仅在线程退出时 drain。 主线程与 ThreadPoolExecutor 常驻池线程永不退出 → 池内解码缓冲永不 释放（实测：主线程/常驻池 NSImage +10~11MB/张；新线程
  30 张 +0.1MB）。

v2.8.1 已消除主泄漏源（图层后备/懒缩略图/大文件懒代理），本版本把 剩余的 ObjC 对象创建路径（NSImage 回退、内嵌预览 NSData）全部迁入
  "新建线程、任务结束即退出"的执行模型：

1. 新增 core/decode_threads.py： - run_decode()：临时线程同步执行（线程退出 → pool drain，返回的 ObjC 对象由 Python
  包装器持有，随后可回收） - run_decode_async()：异步 fire-and-forget，线程退出自动回收 2. strategies.py：NSImage
  回退路径（load_with_nsimage / cgimage_to_nsimage / load_with_memory_map）一律经 run_decode 执行 ——
  无论调用方在主线程还是常驻池线程均不再泄漏。 3. image_manager：extract_embedded_preview（内部创建 NSData）经 run_decode 执行，消除常驻
  prefetch 池的 MPF 提取泄漏。

主路径不变：懒解码 CGImage 代理（CF 语义、任意线程安全）仍为首选。 新增 8 例 decode_threads 测试；全量测试 1677 passed。


## v2.8.1 (2026-08-20)

### Bug Fixes

- 修复显示/解码路径主线程 autorelease pool 泄漏（实机 20 分钟 20.9GB）
  ([`1cc1967`](https://github.com/onlyhooops/plookingII/commit/1cc19679fef924e1dfd45451c68ecdefb119fa67))

实机验证（logs/perf_20260820_202637.json）：v2.8.0 会话 74.7MB→20.9GB， 看门狗阈值触发正常但 evict 无效——根因是解码缓冲挂永不 drain
  的线程 autorelease pool（PyObjC 仅在线程退出时 drain），不在 Python 可达引用内。

6000×4000 JPEG 实机实验定位三个主泄漏源并修复： 1. 图层后备（wantsLayer=True）：每次显示向主线程池追加视图尺寸后备位图 （1200×800 ≈
  3MB/次，视网膜+大窗口 15~30MB/次）——会话 18.6GB 主源。 AdaptiveImageView/OverlayView/主容器全部关闭图层后备（绘制逻辑不变， 实测
  Δ+0.0MB）。 2. JPEG 缩略图 eager 解码（ShouldCacheImmediately=True）：+1.63MB/张。 改为懒解码（False），实测
  +0.01MB/张，像素结果不变。 3. 大文件内存映射 NSImage（>100MB）：+11MB/张。_load_large 优先懒解码 CGImage 代理（CF
  语义可回收），内存映射降为回退。

调研报告：docs/reports/display-pipeline-research-2026-08-20.md （qView 管线分析 + macOS 生态调研 + 实测数据表）

新增防回归测试：AdaptiveImageView 非图层后备、_load_large 懒代理优先。 全量测试 1669 passed。

### Chores

- 同步版本断言至 v2.8.0
  ([`67e6645`](https://github.com/onlyhooops/plookingII/commit/67e6645d6b62a3ba1315f9a53ead981f028656c9))


## v2.8.0 (2026-08-20)

### Features

- 内存看门狗（rss 阈值触发 + 定期回收）——根治长会话内存增长
  ([`c8986f9`](https://github.com/onlyhooops/plookingII/commit/c8986f98a564c051606d33f520ababd89307ac16))

产品决策：显示管线保持不变（原图/全分辨率直通），内存控制改为 "RSS 阈值触发 + 定期回收"看门狗，替代被否的分片渲染与子进程方案。

真机 v2.6.1/v2.7.x 确认：主进程 ObjC 解码缓冲挂主线程 autorelease pool 且从不被 drain（PyObjC 结构性限制，所有官方释放 API 均已实测
  崩溃）。因此内存只能靠"及时释放 Python 侧可回收引用"收敛：

1. 新增 core/memory_watchdog.py：进程 RSS 采样（psutil → mach task_info → resource 三级回退）+ 清理等级判定（preventive
  / moderate / aggressive / emergency，阈值随物理内存自适应，可配置）。 2. ImageManager 监控线程每 5s 检查 RSS，按等级递进回收：缓存收缩/
  减半/保留HOT3/仅保留当前图 + 释放预取双缓冲 + 清空小缓存 + gc。 3. 修复 SimpleImageCache.evict_oldest 永不生效的缺陷（旧实现仅在
  count>=条目数时清空，导致既有清理函数全部空转）；统一 NSCache/ OrderedDict 分支的近似 LRU 顺序维护。 4. 加载侧少制造不可回收对象：小文件路径（<10MB）由
  NSImage 改为 懒解码 CGImage 代理（CF Create 语义、包装器释放即回收），显示 质量不变（仍为全分辨率原图、无降采样）；Quartz 失败回退 NSImage。 5.
  移除已废弃的 _load_image_via_subprocess（死代码 + 错误相对导入， 子进程方案不再使用）。 6. TILED_RENDERING_ENABLED
  恢复默认关闭，显示管线保持原有直通路径。

验证：全量测试 1666 passed（新增 watchdog 28 例、evict_oldest 9 例、 _load_small 代理 3 例、RSS 升级 8 例）。


## v2.7.1 (2026-08-19)

### Bug Fixes

- 修复 v2.7.0 打包 App 图片不显示（子进程解码不可用回退）
  ([`b54b696`](https://github.com/onlyhooops/plookingII/commit/b54b696374540bec62f296097c895099ea7f5900))

真机 v2.7.0：内存平台型但窗口空白、翻页正常。根因： 1. py2app 打包缺 multiprocessing 模块（spawn 子进程无法启动） -> setup.py
  生成器（tools/package_release.py create_setup_py） includes 补 multiprocessing/concurrent.futures/queue
  2. 子进程失败无回退 -> _load_image_via_subprocess 直接返回 None -> 回退主进程视图级解码（load_with_quartz
  thumbnail/NSImage）， 保证图片始终可显示（子进程仅是内存优化，不阻塞功能） 3. 缺 multiprocessing.freeze_support() ->
  __main__.py 启动前调用

验证：真实 ImageManager 子进程路径返回 NSImage 1920×1280；回退分支 主进程解码正常；全量测试 1627 passed。


## v2.7.0 (2026-08-19)

### Chores

- 同步版本断言至 v2.6.1
  ([`b35571e`](https://github.com/onlyhooops/plookingII/commit/b35571e75487fc278d2d663da5b8754b6a990a5b))

### Features

- 解码子进程隔离——根治主进程 ObjC 解码内存泄漏
  ([`863e0e9`](https://github.com/onlyhooops/plookingII/commit/863e0e9e63bcc3be48e74a732d502ebc4b9e5c4c))

真机 v2.6.1 确认：主进程任何 ObjC 图像解码（fast 路径 NSImage 全分辨率） 其解码缓冲挂主线程 autorelease pool 永不释放（43 次解码 ≈ 8.6GB）。
  已验证所有官方释放 API（drain/autorelease_pool/recycle）均不可行或崩溃。

根治：图像解码迁移到独立子进程（spawn）—— - 解码内存（~242MB/张）全部隔离在子进程 - 子进程解码后写显示级 JPEG 临时文件回传，主进程只加载小图 - 子进程累计任务上限后重启 →
  解码内存随进程销毁彻底释放 - fast 路径非全分辨率时改用子进程解码

验证：30 次解码父进程 RSS 净增 -0.3MB（对比 ~+5GB）； 全量测试 1627 passed（新增 7 例 decode_pool 测试）。


## v2.6.1 (2026-08-18)

### Bug Fixes

- 移除主线程 recycleAutoreleasePool 定时器（修复启动崩溃）
  ([`27d0494`](https://github.com/onlyhooops/plookingII/commit/27d04941f6bc8b8fa5d4b5288a10be2a79d67057))

崩溃报告（logs/崩溃报告.md）：v2.5.5 的主线程周期 recycleAutoreleasePool 在 NSTimer 回调（RunLoop 已压 autorelease pool）中调用
  objc.recycleAutoreleasePool() 导致 AutoreleasePoolPage::badPop -> SIGABRT（该 API 官方标注 for system use
  only）。回滚 recycle 定时器，window.py 恢复 v2.5.4 稳定状态。

内存问题保留：PyObjC 12 无安全周期 drain 全局 pool 的官方 API（已验证 recycle / autorelease_pool / 手写 drain
  均不可行），内存方案需架构级 重构（见 docs/reports/memory-pipeline-design.md 后续）。

### Chores

- 同步版本断言至 v2.6.0
  ([`f8a96a7`](https://github.com/onlyhooops/plookingII/commit/f8a96a7858664fe108f671188757886d08b294a0))

- 同步版本至 v2.5.7 并记录 recycle 回滚
  ([`8ecb5aa`](https://github.com/onlyhooops/plookingII/commit/8ecb5aa8a3e3eea0570a1a251a2c8c248835ef5b))


## v2.6.0 (2026-08-18)

### Features

- 性能跟踪报告改为会话级单文件
  ([`975ba91`](https://github.com/onlyhooops/plookingII/commit/975ba918e09da5b47752f78a24f64b34cebdb1ef))

一次运行只生成一份 perf_<启动时间戳>.json/.md，周期自动落盘与退出 落盘合并覆盖同一文件，不再产生分散的 _auto/_quit 片段；报告含完整
  最终状态（操作统计+慢事件+内存曲线+会话元信息+最近更新原因）， MD 标注'单次运行的完整会话记录'。

- 新增单会话单文件测试，轮转测试改多会话场景 - README 同步更新内嵌性能跟踪说明


## v2.5.5 (2026-08-18)

### Bug Fixes

- 主线程周期 recycleAutoreleasePool 修复长会话内存线性增长
  ([`b16cb47`](https://github.com/onlyhooops/plookingII/commit/b16cb4703c93a84c0e9736cc2eee0b3d3187b047))

调研结论：PyObjC 官方 objc.recycleAutoreleasePool()（'释放全局池并新建'） 是唯一桥接感知的安全周期回收接口（手写 drain 在 v2.5.3 已证崩溃）。

落地： - MainWindow 主线程注册 30s NSTimer -> recycleAutoreleasePool: - 仅在 PyObjC 提供该 API 时启用（降级安全） - 修复
  verify 脚本对 '## [x.y.z]' 占位格式的兼容

量化验证：90 次真实解码 + 6 次 recycle -> RSS 净增 +84MB（平台型）， 对比修复前 ~+15GB；持有对象有效性保持（无 use-after-free）。

设计文档：docs/reports/memory-pipeline-design.md（HOT3 + 视图级解码 LRU + 磁盘缓存 + 周期回收的完整管线）。

### Chores

- 同步版本断言至 v2.5.4
  ([`2fd7dcf`](https://github.com/onlyhooops/plookingII/commit/2fd7dcf221e9baafff5d621cc0d888c4a1b1f892))


## v2.5.4 (2026-08-18)

### Bug Fixes

- 回滚 autorelease 方案修复启动崩溃，full_res_browse 默认改视图级解码
  ([`13962f9`](https://github.com/onlyhooops/plookingII/commit/13962f963808a415e7cc30c3c948a42da0bbb711))

崩溃（logs/崩溃报告.md，v2.5.3）：PyObjC 桥接下手动 NSAutoreleasePool 与 PyObjC 对象引用管理冲突，解码线程池中 pool drain 后 Python
  侧 del/帧清理二次释放 ObjC 对象 → use-after-free SIGSEGV（启动即崩）。

修复： - 完全回滚 v2.5.3 的 autorelease pool 方案（删除 core/autorelease.py 及所有解码路径包裹，源码恢复 v2.5.2 稳定状态） -
  feature.full_res_browse 默认 True → False：主线程绘制解码从全分辨率 （6000×4000 ≈ 168MB/张）改为视图级（~1920 ≈
  10-20MB/张）， 消除长会话内存增长与 swap 卡顿主因，不触碰 autorelease 机制

验证：产品路径 60 次翻页 RSS 净增 +7.4MB（对比全分辨率 +2.5GB/15张）； 全量测试 1619 passed。分析报告已更新记录崩溃根因与经验教训。


## v2.5.3 (2026-08-18)

### Bug Fixes

- 修复 PyObjC 桥接内存泄漏（越用越卡根因）
  ([`0df83a9`](https://github.com/onlyhooops/plookingII/commit/0df83a98544f8ce5c7e4dcca3ade03ca3fd09500))

量化定位：解码产生的 ObjC 中间对象进入全局 NSAutoreleasePool 且从不 drain，Python 侧 del/gc/缓存驱逐均无法触发 ObjC dealloc，导致解码内存
  （实测 168-255MB/张）永久残留、长会话线性增长（6 分钟 84MB→9.5GB）。

修复： - 新增 core/autorelease.py：objc_autorelease_pool() 上下文管理器， 在解码/图像操作外围创建并立即 drain 局部
  NSAutoreleasePool - 解码路径全面接入：OptimizedStrategy/PreviewStrategy.load、
  load_image_with_strategy、_load_image_optimized、 _load_image_with_concurrency、内嵌预览提取 - 返回值由 Python
  引用计数持有（with 后仍有效），非 macOS 自动降级

验证：15 张解码净增 2526MB → 1MB（回收率 99.96%）； 120 次翻页模拟 RSS 平台型（+28MB）。

分析报告：docs/reports/memory-analysis-2026-08-18.md； 解除 docs/reports/ 忽略（README 索引 + 报告随仓库托管）； 新增 logs/
  忽略（运行时性能报告不入库）。

### Chores

- 同步版本断言至 v2.5.2，版本脚本兼容 semantic-release 格式
  ([`118d6e3`](https://github.com/onlyhooops/plookingII/commit/118d6e3d65317ce8aafc375acb398a51d4ae019a))

semantic-release 自动发布 v2.5.2 后同步测试断言与 README； verify/unify 脚本的 CHANGELOG 检查兼容 '## vX.Y.Z' 生成格式，
  避免误插占位条目。


## v2.5.2 (2026-08-16)

### Bug Fixes

- 修复 CI Ruff 检查 UP038 违规
  ([`b587179`](https://github.com/onlyhooops/plookingII/commit/b58717958e468c21d93da21fc6fd9d29d1618b00))

ruff 0.12.9（CI 固定版本）对 isinstance 元组参数触发 UP038， 改用 X | Y 联合类型语法（dimension_cache / perf_tracker）。

### Chores

- 同步版本号至 v2.5.1 并恢复可读 CHANGELOG
  ([`dd8f32c`](https://github.com/onlyhooops/plookingII/commit/dd8f32cebae22f692a0b8fe05dfa87dbb60307f3))

semantic-release 自动版本提升已根据 git 提交类型将版本定为 v2.5.1 （fix/perf/chore → patch 级），同步测试断言与 README 至一致； 将生成的
  CHANGELOG 整理为人类可读格式，保留 P2~P3 各阶段详细记录。


## v2.5.1 (2026-08-15)

### Bug Fixes

- 修复测试污染、ci 门禁逻辑与版本管理工具链
  ([`6687884`](https://github.com/onlyhooops/plookingII/commit/6687884d727c41e9365d0452ce8d758b917f1a1f))

- 修复 test_get_config_manager_singleton 将 Mock 泄漏进全局配置 单例导致的跨测试污染（try/finally 恢复原单例） - 同步版本断言 2.4.1 →
  2.5.0（当前 __version__） - 修复 ci-success 汇总步骤放行 test-macos failure 的矛盾逻辑， 测试与覆盖率失败时 CI 必须变红 - 补齐
  Makefile/文档引用的缺失脚本： verify_version_consistency / unify_version / clear_recent_items /
  analyze_simplification（含 bump_version 的 DTZ/PLW 遗留修复）

### Chores

- 工程化配置与文档更新
  ([`8974b21`](https://github.com/onlyhooops/plookingII/commit/8974b21d317d6c0472ffc851d5473a21e7ce1d6d))

- Python 版本声明收紧至 >=3.11（代码实际使用 PEP 604/typing.Self）， classifiers 与 README 徽章同步 - 修复文档死链：docs/reports
  索引页、CONTRIBUTING.md、quick-start 脚本引用 - Makefile 优先使用 .venv、新增 verify/unify/benchmark 目标 - ruff 配置补
  scripts 豁免；mypy.ini 清理从未生效的 unused section - package_release.py 动态探测打包解释器版本、签名失败软降级 - .gitignore
  解除 scripts/ 忽略（版本管理与基准工具随仓库托管）

### Performance Improvements

- P2~p3 性能优化全阶段落地（v2.5.1→v2.6.0）
  ([`da4007c`](https://github.com/onlyhooops/plookingII/commit/da4007c618a206070919b2dc0850306eb5b81b23))

- P2-1 解码耗时自适应两阶段：经验表按文件大小分档归档实测解码耗时， 同规格 ≥150ms 自动降级预览→懒解码全分辨率 - P2-2
  解码线程池有界：关键池非关键任务有界提交（满即丢），预取池上限 6 - P3-1 CATiledLayer 超高分辨率分片渲染原型（TiledImageView，默认关闭 待真机验证）：按需
  tile + CGImageCreateWithImageInRect 仅解码可见像素 - P3-2 可重复性能基准 scripts/benchmark.py：合成图片集度量首图/翻页/
  缓存命中/RSS/文件夹扫描，输出 JSON 基线 - P3-3 移除零引用休眠模块 ui/video_player_view.py（480 行） - P3-4 图片元数据持久化缓存
  core/dimension_cache.py：目录 mtime 失效、 原子写盘、损坏容错，二次打开同目录跳过元数据重读 - 轻量性能跟踪 perf_tracker + 目录含图布尔缓存 +
  渲染路径统一 - 全量测试 1608→1619 passed，覆盖率 58.51%


## v2.5.0 (2026-08-05)

### Features

- Plookingii v2.5.0 初始版本
  ([`5fe58e7`](https://github.com/onlyhooops/plookingII/commit/5fe58e7217fea97027db1f8e071b6ac2a108b48a))
