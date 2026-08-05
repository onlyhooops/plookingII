"""
图像处理配置文件

集中管理图像处理的各项配置与性能优化选项。

说明：项目已放弃运行期 EXIF 方向修正——使用本项目筛选的图片集
会在进入筛选流程前由外部工作流统一纠正朝向，因此不再保留任何
EXIF 方向处理相关的配置与代码。
"""

# 图像加载性能优化配置
IMAGE_LOADING_OPTIMIZATIONS = {
    # 快速加载阈值（MB）
    "fast_load_threshold": 50,
    # 是否启用快速加载模式
    "fast_load_enabled": True,
    # 渐进式加载阈值（MB）
    "progressive_load_threshold": 100,
    # 是否启用渐进式加载
    "progressive_load_enabled": True,
    # 预览模式阈值（MB）
    "preview_load_threshold": 20,
    # 是否启用预览模式
    "preview_load_enabled": True,
}

# Quartz/ImageIO配置
QUARTZ_CONFIG = {
    # 是否启用Quartz处理
    "enabled": True,
    # 是否缓存图像源
    "should_cache": True,
    # 是否允许浮点数据
    "should_allow_float": True,
    # 是否总是创建缩略图
    "create_thumbnail_always": True,
    # 是否立即缓存
    "should_cache_immediately": False,
}

# PIL备用方案配置
PIL_FALLBACK_CONFIG = {
    # 是否启用PIL备用方案
    "enabled": True,
    # 默认图像质量
    "default_quality": 95,
    # 是否优化保存
    "optimize_save": True,
    # 缩放算法
    "resampling_method": "LANCZOS",
}

# 缓存配置
CACHE_CONFIG = {
    # 主缓存最大大小
    "max_size": 20,
    # 预览缓存最大大小
    "max_preview_size": 10,
    # 预加载缓存最大大小
    "max_preload_size": 5,
    # 内存限制（MB）- 提升到4GB总预算
    "max_memory_mb": 4096,
    # 预览内存限制（MB）
    "max_preview_memory_mb": 600,
    # 预加载内存限制（MB）
    "max_preload_memory_mb": 1200,
}

# 性能监控配置
PERFORMANCE_MONITORING = {
    # 是否启用性能统计
    "enabled": True,
    # 是否记录详细日志
    "detailed_logging": False,
    # 性能阈值警告（秒）
    "warning_threshold": 1.0,
    # 性能阈值错误（秒）
    "error_threshold": 5.0,
}

# 导出所有配置
__all__ = [
    "CACHE_CONFIG",
    "IMAGE_LOADING_OPTIMIZATIONS",
    "PERFORMANCE_MONITORING",
    "PIL_FALLBACK_CONFIG",
    "PNG_OPTIMIZATION_CONFIG",
    "QUARTZ_CONFIG",
]

# PNG 格式专属优化配置
# PNG 使用 DEFLATE 无损压缩，解码开销显著高于 JPEG 的 DCT 解压，
# 且 PNG 无内嵌缩略图、无 EXIF 方向信息，需差异化处理。
PNG_OPTIMIZATION_CONFIG = {
    # 缩略图 Subsampling 因子：PNG 解码重，使用更大降采样
    # 4 表示解码时每 4 个像素仅保留 1 个，像素量降至 1/16
    "thumbnail_subsample_factor": 4,
    # 策略阈值因子：PNG 阈值 = JPEG 阈值 × factor
    # 0.6 使 PNG 文件更早进入 Quartz/mmap 优化路径
    "threshold_factor": 0.6,
    # 是否检测 Alpha 通道（避免不必要的 RGBA 处理）
    "detect_alpha": True,
    # 是否跳过元数据解析（PNG 元数据对浏览无用）
    "skip_metadata": True,
    # PNG 专用缓存内存系数：每个 PNG 像素的实际内存占用
    # 无 Alpha: 3 bytes/pixel (RGB), 有 Alpha: 4 bytes/pixel (RGBA)
    # JPEG 始终为 3 bytes/pixel (RGB)
    "memory_per_pixel_no_alpha": 3,
    "memory_per_pixel_alpha": 4,
    # 预加载窗口调整因子：PNG 解码更慢，预加载窗口缩小
    "prefetch_window_factor": 0.7,
}
