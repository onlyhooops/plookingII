# Changelog

所有notable changes都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

<!--next-version-->

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
