# PlookingII

macOS 原生图片浏览器 - 高性能、智能化的图片浏览体验

## 🚀 项目概述

- macOS 原生图片浏览器，专注本地 JPG/JPEG/PNG 的高效浏览
- 低延迟切图与稳定内存占用，面向高分辨率照片筛选
- Quartz-only架构：统一图像处理管道，自适应性能调优

### 核心特性
- **Quartz-only处理**: 完全基于macOS原生Quartz框架，无第三方依赖
- **EXIF方向自动修正**: 自动处理图像方向信息，解决颠倒问题  
- **CGImage直通渲染**: 零拷贝渲染，提升显示性能
- **自适应性能调优**: 实时监控性能，动态调整参数
- **智能缓存系统**: 默认两层缓存（主缓存/预览），LRU淘汰；预加载可选（默认关闭）
- **图像旋转功能**: 支持90度旋转，保持EXIF信息

## 📋 功能特性

### 🖼️ 图像处理
- **统一处理管道**: 所有图像处理都通过Quartz进行，确保一致性
- **EXIF方向处理**: 自动修正图像方向，支持所有EXIF方向标签
- **硬件加速**: 充分利用macOS的GPU加速能力
- **内存映射**: 大文件使用内存映射技术，减少内存占用
- **智能缩略图**: 基于目标尺寸的智能缩略图生成

### 🎯 用户体验
- **原生macOS界面** - 完全使用AppKit构建
- **拖拽文件夹支持** - 直接从Finder拖拽文件夹到窗口开始浏览
- **系统级右键菜单** - 图片上右键呼出"打开方式"菜单，无缝跳转到其他图片编辑工具
- **智能应用过滤** - 自动屏蔽浏览器应用，专注图片编辑工作流
- **文件修改检测** - 实时监听图片变化，支持外部编辑后自动重载
- **快捷键支持** - 完整的键盘操作支持
- **文件夹导航** - 智能文件夹扫描和导航
- **历史记录** - 自动保存浏览进度
- **流畅交互** - 优化的拖拽响应，零卡顿体验

### ⚡ 性能优化
- **自适应调优**: 实时性能监控，动态调整解码并发度和预加载窗口
- **CGImage直通**: 避免NSImage包装开销，直接绘制CGImage
- **坐标系优化**: 简化绘制流程，移除不必要的变换计算
- **智能预加载**: 基于性能状态的自适应预加载策略
- **内存分级管理**: 根据系统内存状态的分级优化策略

## 🛠️ 技术架构

### 核心模块
```
plookingII/
├── app/            # 应用程序层
│   └── main.py            # 应用入口和代理
├── ui/             # 用户界面层
│   ├── window.py          # 主窗口
│   ├── views.py           # CGImage直通视图
│   ├── controllers/       # 控制器
│   └── managers/          # UI管理器
├── core/           # 核心功能层
│   ├── image_processing.py      # 混合图像处理器
│   ├── cache.py                # 高级图像缓存
│   ├── bidirectional_cache.py  # 双向缓存
│   ├── optimized_loading_strategies.py # 优化加载策略
│   └── performance.py          # 性能监控器
├── services/       # 服务层
│   └── recent.py          # 最近文件服务
├── db/            # 数据层
│   └── connection.py      # 数据库连接
├── monitor/       # 监控层
│   └── memory.py          # 内存监控
└── config/        # 配置层
    └── constants.py       # 常量配置
```

### 设计模式
- **策略模式** - 图像加载策略选择
- **工厂模式** - 组件创建
- **MVC架构** - 清晰的代码结构
- **观察者模式** - 性能监控和参数调整
- **单例模式** - 性能监控器

## 📦 安装使用

### 系统要求
- macOS 10.15+ (Catalina 或更高)
- Python 3.8+
- 支持的文件格式: JPG, JPEG, PNG（不涉及 RAW 或其他格式）

### 依赖说明
- **系统框架**: AppKit、Quartz/ImageIO（随系统提供）
- **Python 绑定（必需）**: PyObjC（Objective-C 桥接）
- **运行时依赖（最小集合）**: `psutil`、`Pillow`（用于图像操作与降级路径）
  - 参见 `requirements.txt` 与 `requirements-dev.txt`

### 安装方法

#### 方法1: 直接运行
```bash
git clone https://github.com/yourusername/plookingII.git
cd plookingII
python3 -m plookingII
```

#### 方法2: 打包应用
```bash
# 使用构建工具打包
python3 tools/build.py --package
```

### 运行应用
```bash
# 直接运行
python3 -m plookingII

# 或运行打包后的应用
open dist/PlookingII.app
```

### CLI 使用示例
```bash
# 运行基准测试（需要指定图片根目录）
python3 tools/benchmark_images.py /path/to/your/images --out reports/my_benchmark.csv

# 生成基准测试报告摘要
python3 tools/generate_reports.py --input reports/my_benchmark.csv --output_dir reports
```

## 🎮 使用指南

### 基本操作

#### 打开文件夹
- **菜单方式**: `Cmd+O` 或菜单 "文件" → "打开文件夹"
- **拖拽方式**: 直接从 Finder 拖拽包含照片的文件夹到应用程序窗口
  - 支持检测 JPG、JPEG、PNG 格式的图片文件
  - 自动识别文件夹及子文件夹中的图片
  - 拖拽时显示蓝色高亮边框和状态提示
  - 自动添加到最近打开文件夹记录

#### 图片浏览
- **下一张图片**: `→` 右方向键
- **上一张图片**: `←` 左方向键
- **下一文件夹**: `Cmd+→` 跳过当前文件夹
- **上一文件夹**: `Cmd+←` 撤销跳过文件夹
- **在Finder中显示**: `Cmd+R` 定位当前图片
- **退出应用**: `Cmd+Q`

### 高级功能
- **精选图片**: `↓` 下方向键 - 将图片移动到"精选"文件夹（仅在首次精选时创建该文件夹；打开/切换文件夹不再自动创建）
- **撤销操作**: `Cmd+Z` - 撤销最后的保留操作
- **退出文件夹**: `ESC` 键 - 退出当前文件夹
- **拖拽浏览**: `Space` + 拖拽（在缩放>100%时启用）
- **图片旋转**: `Cmd+Option+R` 向右旋转90°，`Cmd+Option+L` 向左旋转90°
- **系统级右键菜单**: 在图片上右键点击呼出"打开方式"菜单
  - 显示系统中可用的图片编辑应用程序及其图标
  - 自动过滤浏览器应用程序（115浏览器、Safari、Chrome等）
  - 支持默认应用程序标识和"其他..."选择
  - 一键跳转到Photoshop、Pixelmator等专业编辑工具

## 🔧 开发信息

### 代码质量
- **代码风格**: 通过 flake8 检查
- **复杂度**: 通过 radon 分析
- **测试覆盖率**: 当前总覆盖率约 42%（核心模块 ≥30%）
- **安全审计**: 通过 pip-audit 检查

### 性能指标
- **启动时间**: < 2秒
- **内存使用**: 动态调整，最大500MB
- **图像加载**: 小文件 < 100ms；大文件采用Quartz缩略/内存映射降压
- **缓存命中率**: > 80%
- **EXIF处理**: 自动方向修正，无额外延迟

### 开发环境
```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
python3 -m pytest tests/

# 代码质量检查
flake8 plookingII/
radon cc plookingII/
coverage run -m pytest tests/
```

## ❓ 常见问题 / 性能建议

### 横竖切换时出现轻微卡顿？

- 已在 v1.1.3 优化：预取在 full‑res 模式下降级为“视图级动态目标尺寸”，显著降低超大图在横竖切换时的解码压力；next‑ready 会按“最近导航方向”选择左/右相邻，左向与右向命中率一致。
- 建议：
  - 优先在 100% 或更低缩放下快速连切；或适度减小窗口尺寸，以降低视图级目标尺寸，缓解跨方向切换抖动。
  - 在准备快速连切前，先停留 0.2–0.3 秒给预取线程时间，就绪率更高、切换更顺滑。
  - 横竖混排序列中，长时间高速连击时可适当放慢按键节奏，避免超出自适应预取窗口。
  - 首次通览一遍后再次浏览会更顺滑（缓存与“热三帧”常驻已就位）。

### 快速连击后仍有极短延迟？

- 系统存在 10–20ms 级别的防抖与主队列调度延迟，属预期范围。v1.1.3 已改为“队列式步进 + 单次渲染”，松手即停，不会额外多跳一张。

### 超大图（>120MB）多方向混排的建议

- 控制窗口宽高在需要的最小范围，可让动态目标尺寸更小，切换更顺滑。
- 如需频繁 10x 放大细看，完成后建议还原至 100% 再进行快速切换。

## 🧰 故障诊断

- 日志位置（自动轮转）：`~/Library/Logs/PlookingII/plookingII.log`（macOS）
- 全局异常钩子：未捕获异常会记录到上述日志（包含完整堆栈）。
- 反馈问题时请附带最近的日志片段（注意清理隐私路径）。

## 📊 版本变更
- **当前版本**: v1.3.1（详见 `plookingII/config/constants.py` 的 `VERSION`）
- **完整版本历史**: 查看 [VERSION_HISTORY.md](VERSION_HISTORY.md)
- **更新日志**: 查看 [CHANGELOG.md](CHANGELOG.md)
- **技术指南**: 查看 [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md)
- **项目综述**: 查看 [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

### 代码规范
- 遵循 PEP 8 代码风格
- 添加适当的注释和文档
- 编写单元测试
- 确保所有测试通过

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- macOS 开发社区
- Python 图像处理库
- 所有贡献者和用户

## 📞 支持

如果您遇到问题或有建议，请：

1. 创建新的 Issue

---

**PlookingII** - 让图片浏览更简单、更高效！ 🎉
