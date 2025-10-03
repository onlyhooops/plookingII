# 背景
文件名：2025-09-15_1_batch-photo-lossless-compress.md
创建于：2025-09-15_00:00:00
创建者：unknown
主分支：main
任务分支：task/batch-photo-lossless-compress_2025-09-15_1
Yolo模式：Off

# 任务描述
开发一个高效、可靠的照片批量无损压缩脚本，满足中文路径兼容、保留核心元数据、仅处理JPEG/PNG、并发不超过4、提供进度与日志显示、直接覆盖原文件且确保处理可靠性。

# 项目概览
工作区路径：/Volumes/aigo/Python/plookingII
项目包含桌面应用与图像处理核心模块，拟新增独立批处理脚本（命令行模式），与现有模块复用可行性待评估。

⚠️ 警告：永远不要修改此部分 ⚠️
遵循RIPER-5协议要点：模式声明、研究/创新/规划/执行/审查分离；未经批准不实施；执行严格按计划清单；审查标注任何偏差；中文常规交互、英文代码块；禁用表情；不做未授权修改。
⚠️ 警告：永远不要修改此部分 ⚠️

# 分析
待填：阅读现有图像处理与配置模块，识别可复用函数（如EXIF处理、方向校正、无损保存），扫描日志/线程工具以复用。

# 提议的解决方案
方案A：纯 Python 实现（Pillow + piexif）
- 优点：部署简单、无外部依赖、跨平台潜力；代码可控、便于单元测试。
- 缺点：JPEG 视觉无损需要谨慎设定quality与subsampling，压缩率通常逊于mozjpeg；EXIF 精简需自行维护字段白名单逻辑；旋转为再编码（非真正无损路径），但符合“视觉无损”定义。
- 适用：对外部可执行依赖敏感的环境，或需最小化系统集成复杂度。

方案B：系统工具增强路径（jpegtran/mozjpeg + oxipng + exiftool）
- 优点：
  - JPEG：mozjpeg的`-optimize`/`-progressive`在保持视觉质量下有更优压缩率；`jpegtran -copy all -optimize -progressive`可进行无损转码；物理旋转使用`jpegtran -rotate`真正无损；
  - PNG：`oxipng -o4~6 --strip safe`在无损前提下显著减小体积；
  - 元数据：`exiftool`以字段白名单/黑名单操作更稳健，移除缩略图与非核心数据更可靠。
- 缺点：引入外部依赖与进程开销；需处理可执行文件存在性与版本差异；错误处理更复杂。
- 适用：macOS 目标环境、允许安装外部工具、追求更高压缩率与更可靠的元数据操作。

方案C：混合策略（Python 主控 + 外部工具可选加速）
- 思路：默认使用系统工具路径；若工具缺失或出错，回退到纯 Python 路径，保证鲁棒性。
- 优点：兼顾效果与可用性；对不同机器弹性好；渐进式部署。
- 缺点：实现复杂度较高，测试矩阵扩大；日志与错误报告需更细致。

元数据处理策略（适用于所有方案）
- 白名单保留：图像尺寸、Orientation、拍摄时间（DateTimeOriginal）、拍摄参数（ExposureTime/FNumber/ISO/FocalLength/ExposureProgram）、相机型号（Make/Model）、色彩空间（ColorSpace）、压缩信息（Compression/EncodingProcess）、镜头信息（LensInfo/LensSerialNumber）。
- 清理：缩略图（Thumbnail Image）、软件/版本、相机内部参数、自动对焦/测光细节、优化参数、用户评论/版权（如非必要）、面部识别与环境信息、其它自定义字段。
- 实现：
  - 使用`exiftool`时：通过`-tagsFromFile @` + `-all:all=`清空再逐项复制白名单，或`-XMP:all= -IPTC:all=`等选择性清理；移除`-ThumbnailImage=`。
  - 使用Python时：`piexif`解析/重写 EXIF，Pillow保存时附加；PNG 无 EXIF，保留最小化文本块（可选）。

朝向校正策略
- JPEG：优先`jpegtran -rotate 90/180/270 -copy all`物理旋转，并将Orientation归一为1；回退路径使用Pillow旋转并重写EXIF。
- PNG：使用Pillow进行像素旋转（PNG无EXIF Orientation）。

并行与任务调度
- 采用`multiprocessing.Pool(processes<=4)`分配任务；任务按文件大小或扩展名分组以提升工具复用效率；对失败任务自动重试一次（不同实现路径）。

覆盖与原子替换
- 始终写入同目录临时文件（`.tmp`或随机后缀），完成后`os.replace`原子替换；失败即回滚并删除临时文件。

进度与日志
- 终端进度条（单行）展示已处理/总数、成功/跳过/失败计数、累计节省体积；
- 控制台分级日志（INFO/WARN/ERROR），并将汇总信息写入日志文件（如`compress.log`）。

路径与中文兼容
- 统一使用`pathlib.Path`与`subprocess.run`传递`str(Path)`；显式`encoding='utf-8'`处理stdout/stderr；确保对空格与中文路径正确转义。

失败回退与重试
- 外部工具失败：回退到纯Python路径；纯Python失败：标记失败并清理临时文件；不中断整体批处理。

预期效果对比（经验值，随素材而变）
- 纯Python：JPEG 5%~15%，PNG 0%~5%；
- 系统工具：JPEG 10%~30%（mozjpeg/progressive更优），PNG 5%~20%（oxipng 中高等级）。

# 当前执行步骤："1. 代码与需求调研"

# 任务进度
[2025-09-15_00:00:00]
- 已修改：.tasks/2025-09-15_1_batch-photo-lossless-compress.md
- 更改：初始化任务文件并（若可）创建任务分支
- 原因：遵循RIPER-5研究模式准备
- 阻碍因素：待确认是否git仓库
- 状态：未确认

# 最终审查
待完成后填写。
