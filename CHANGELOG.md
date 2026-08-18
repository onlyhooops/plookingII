# CHANGELOG

## v2.5.7 (2026-08-18)

### 🐛 Bug Fixes

- **移除主线程 recycleAutoreleasePool 定时器（修复启动崩溃）**：v2.5.5 的
  `objc.recycleAutoreleasePool()` 周期调用在 NSTimer 回调（RunLoop 已压
  autorelease pool）中触发 `AutoreleasePoolPage::badPop` → SIGABRT（该 API
  官方标注 "for system use only"）。回滚后 window.py 恢复 v2.5.4 稳定状态

### ⚡ 已知问题

- 长会话内存增长问题保留：PyObjC 12 无安全周期 drain 全局 pool 的官方 API
  （recycle / autorelease_pool / 手写 drain 均已验证不可行），内存方案需
  架构级重构（见 `docs/reports/memory-pipeline-design.md`）

### 🧪 测试与工程化

- 全量测试通过（1620 passed）

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