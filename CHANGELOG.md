# CHANGELOG


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
