# CHANGELOG

## v2.5.1 (2026-08-15)

### 🐛 Bug Fixes

- 修复 `test_get_config_manager_singleton` 将 Mock 泄漏进全局配置单例导致的跨测试污染（`try/finally` 恢复原单例）
- 同步版本断言 2.4.1 → 2.5.0（当前 `__version__`）
- 修复 `ci-success` 汇总步骤放行 `test-macos` failure 的矛盾逻辑：测试与覆盖率失败时 CI 必须变红
- 补齐 Makefile/文档引用的缺失脚本：`verify_version_consistency` / `unify_version` / `clear_recent_items` / `analyze_simplification`（含 `bump_version` 的 DTZ/PLW 遗留修复）

### ⚡ Performance Improvements

- **P2-1 解码耗时自适应两阶段显示**：新增解码耗时经验表（按文件大小分档、近 5 次实测均值、LRU 上限 + 重置入口），每次后台解码后归档实测耗时；同一规格文件实测解码 ≥150ms 时自动启用"预览 → 懒解码全分辨率"两阶段，中低端机器上文件不大但解码慢（外置盘、高压缩 JPEG）时首帧更早可见
- **P2-2 解码线程池有界队列**：关键池（当前图解码/next-ready）非关键后台任务增加队列深度上限，快速导航时过期任务不再无限积压挤占关键解码线程；预取池上限收敛至 6
- **P3-1 CATiledLayer 超高分辨率分片渲染（原型）**：新增 `TiledImageView` 视图，以 CATiledLayer 为 backing layer，按需请求可见 tile、从源 CGImage 裁剪对应区域绘制（`CGImageCreateWithImageInRect` + ImageIO 懒解码），仅解码可见像素，避免 10000px+ 全分辨率图片首帧 GPU 同步解码卡顿。**默认关闭**，经真机对比达标后可默认开启
- **P3-2 可重复性能基准（`scripts/benchmark.py`）**：合成多尺寸/格式图片集，度量首图加载延迟、连续翻页主线程阻塞（p50/p95/p99）、缓存命中率、RSS 内存曲线、文件夹冷/热扫描延迟；输出 JSON 基线（含版本/时间戳），支持 `--quick` 与 `--output`，用于优化效果量化与防回归
- **P3-3 移除休眠模块**：删除零引用的 `ui/video_player_view.py`（480 行，AVFoundation 视频播放组件，项目已收敛为纯图片浏览）
- **P3-4 图片元数据持久化缓存（`core/dimension_cache.py`）**：目录级"文件名 → 尺寸"映射以目录 mtime 为失效键持久化到应用支持目录，二次打开同一目录批量回填内存 LRU，跳过逐文件元数据读取；只读缓存 + 严格校验（损坏/格式非法安全忽略），LRU 上限 + 原子写盘
- 目录扫描复用（P2-3）：`DirectoryImageListCache` 增加"目录是否含图"布尔缓存（mtime 失效），深度扫描阶段每目录只枚举一次；含图判断顺带填充图片列表缓存，消除重复枚举
- 渲染路径统一（P2-4）：`drawRect_` CGImage 分支复用 `_get_image_display_rect` 几何缓存与 `_get_transformed_rect`，删除内联重复计算
- 导航按键热路径减负：防抖计算改用轻量入口 `calculate_optimal_debounce`，不再同步生成按键路径上不会被消费的预加载索引
- 热路径配置快照：`full_res_browse` / `progressive_loading_enabled` 构造时快照到实例属性，翻页/显示路径不再重复 RLock 查询
- 轻量性能跟踪 `perf_tracker`：聚合统计 + 采样控制 + 慢事件捕获 + 内存采样 + JSON/Markdown 会话报告（退出或定期落盘）

### 🧪 测试与工程化

- 新增目录含图布尔缓存、有界提交丢弃、经验表、持久化缓存、tiled 渲染等 40+ 测试
- 修复 `unify_version.py` 对子目录测试文件的版本同步 bug
- 全量测试 1608 → 1619 passed，覆盖率 58.51%（门槛 45%）
- Python 版本声明收紧至 >=3.11（代码实际使用 PEP 604/typing.Self），classifiers 与 README 徽章同步
- 修复文档死链：docs/reports 索引页、CONTRIBUTING.md、quick-start 脚本引用
- Makefile 优先使用 .venv、新增 verify/unify/benchmark 目标
- ruff 配置补 scripts 豁免；mypy.ini 清理从未生效的 unused section
- package_release.py 动态探测打包解释器版本、签名失败软降级
- .gitignore 解除 scripts/ 忽略（版本管理与基准工具随仓库托管）

## v2.5.0 (2026-08-05)

### Features

- PlookingII v2.5.0 初始版本
