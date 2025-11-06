"""
图像处理配置文件

集中管理图像处理的各项配置，包括EXIF处理策略、性能优化选项等。
"""

# EXIF处理策略配置
EXIF_PROCESSING_CONFIG = {
    # 是否处理EXIF方向信息
    "process_orientation": False,
    # 是否处理EXIF元数据
    "process_metadata": False,
    # 是否应用EXIF变换
    "apply_exif_transform": False,
    # 说明：用户通常提前处理好照片文件的EXIF信息，使用准确的方向信息
    # 因此不需要在运行时处理EXIF，可以显著减少处理开销
}

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
    # 是否应用EXIF变换（关闭以提高性能）
    "apply_exif_transform": False,
    # 是否立即缓存
    "should_cache_immediately": False,
}

# PIL备用方案配置
PIL_FALLBACK_CONFIG = {
    # 是否启用PIL备用方案
    "enabled": True,
    # 是否处理EXIF信息（关闭以提高性能）
    "process_exif": False,
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

# 图像旋转配置
IMAGE_ROTATION_CONFIG = {
    # 是否启用图像旋转功能
    "enabled": True,
    # PIL处理阈值（MB）- 小于此值使用PIL处理
    "pil_threshold_mb": 10.0,
    # Quartz处理阈值（MB）- 大于等于此值使用Quartz处理
    "quartz_threshold_mb": 10.0,
    # 是否处理EXIF方向信息
    "process_exif_orientation": True,
    # 旋转质量设置
    "rotation_quality": {
        "jpeg_quality": 95,  # JPEG保存质量
        "png_optimize": True,  # PNG优化
        "resampling_method": "LANCZOS",  # 重采样算法
    },
    # 性能优化设置
    "performance": {
        "background_processing": True,  # 后台处理
        "cache_clear_after_rotation": True,  # 旋转后清除缓存
        "max_rotation_stack_size": 10,  # 最大旋转操作栈大小
    },
    # 用户界面设置
    "ui": {
        "show_rotation_progress": True,  # 显示旋转进度
        "rotation_feedback_duration": 2.0,  # 反馈显示时长（秒）
        "enable_rotation_undo": True,  # 启用旋转撤销
    },
}

# 导出所有配置
__all__ = [
    "CACHE_CONFIG",
    "EXIF_PROCESSING_CONFIG",
    "IMAGE_LOADING_OPTIMIZATIONS",
    "IMAGE_ROTATION_CONFIG",
    "PERFORMANCE_MONITORING",
    "PIL_FALLBACK_CONFIG",
    "QUARTZ_CONFIG",
]
