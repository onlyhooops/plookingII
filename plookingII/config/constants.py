"""PlookingII 应用配置常量模块

定义应用程序的全局常量、配置参数和资源路径。
包含应用元信息、性能参数、图像处理配置等核心设置。

主要功能：
    - 应用基础信息：名称、版本、作者等
    - 资源路径配置：图标、logo等资源文件路径
    - 性能参数：内存阈值、缓存大小等
    - 图像处理配置：加载策略、质量参数等
    - 系统配置：文件格式支持、界面设置等

设计原则：
    - 集中管理：所有配置常量统一在此模块定义
    - 类型安全：使用明确的类型注解和值范围
    - 文档完整：每个常量都有详细的说明和用途
    - 易于维护：分类清晰，便于查找和修改

Author: PlookingII Team
Version: 1.5.0
"""

from ..imports import QUARTZ_AVAILABLE, os

# ==================== 应用基础信息 ====================

# 应用名称：用于日志记录、窗口标题、配置文件等标识
APP_NAME = "PlookingII"

# 应用版本：遵循语义化版本规范 (major.minor.patch)
# 单一真源（normalized，无前缀）
VERSION = "1.5.0"
# 对外暴露的统一版本别名，供打包与外部工具读取
APP_VERSION = VERSION

# 开发团队：用于关于对话框和版权声明
AUTHOR = "PlookingII Team"

# 版权信息：显示在应用界面和文档中
COPYRIGHT = "© 2025 PlookingII Team. All rights reserved."

# 历史记录文件名：存储用户浏览历史的JSON文件
# 使用隐藏文件格式，避免用户误删
HISTORY_FILE_NAME = ".plookingii_history.json"

# ==================== 资源路径配置 ====================

# 动态计算项目基础目录，避免硬编码路径问题
# 当前文件路径：plookingII/plookingII/config/constants.py
# 基础目录：plookingII/plookingII/
_BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Logo资源目录：存放应用图标和标识文件
_LOGO_DIR = os.path.join(_BASE_DIR, "logo")


def _resource_path(dir_path, filename):
    """构建资源文件的安全路径

    生成资源文件的完整路径，支持开发和打包环境。
    即使文件不存在也返回路径，便于调试时发现缺失资源。

    Args:
        dir_path (str): 资源目录路径
        filename (str): 资源文件名

    Returns:
        str: 资源文件的完整路径

    Note:
        - 兼容开发环境和打包后的应用结构
        - 异常安全：路径操作失败时返回基础拼接结果
        - 不验证文件存在性，由调用方处理
    """
    try:
        candidate = os.path.join(dir_path, filename)
        return candidate if os.path.exists(candidate) else candidate
    except Exception:
        # 路径操作异常时返回基础拼接，确保程序继续运行
        return os.path.join(dir_path, filename)

# SVG格式应用图标：用于高分辨率显示和界面元素
# 矢量格式，支持任意缩放不失真
ICON_SVG = _resource_path(_LOGO_DIR, "PlookingII.svg")


# ICNS格式应用图标：macOS系统专用图标格式
# 包含多种尺寸，用于Dock、Finder等系统界面
ICON_ICNS = _resource_path(_LOGO_DIR, "PlookingII.icns")

# ==================== 性能参数配置 ====================

# 内存使用阈值：当系统可用内存低于此值时触发内存优化
# 4096MB = 4GB，适合现代桌面环境的大图像处理
# 用于：缓存清理、预加载策略调整、内存压力检测
MEMORY_THRESHOLD_MB = 4096

# 最大缓存项数量：图像缓存池中同时保存的图像数量上限
# 20个图像项，平衡内存占用与访问性能
# 用于：AdvancedImageCache、BidirectionalCachePool等缓存组件
# 超出此限制时自动清理最久未使用的缓存项
MAX_CACHE_SIZE = 20

# ==================== 图像格式支持 ====================

# 支持的图像文件扩展名集合（项目已收敛：仅 JPG/JPEG/PNG）
# 用于：文件过滤、格式验证、加载策略选择
SUPPORTED_EXTENSIONS = {
    # 项目范围收敛：仅支持 JPG/JPEG/PNG
    ".jpg", ".jpeg", ".png"
}

# 核心支持格式（用于快速过滤）
# 包含最常用的图像格式，确保核心功能的稳定性
# 用于：文件过滤、格式验证、快速加载策略
SUPPORTED_IMAGE_EXTS = (".jpg", ".jpeg", ".png")

# ==================== 图像处理配置 ====================

# 渐进式加载阈值（兼容旧API，默认关闭）：超过此大小可触发旧渐进式路径
# 50MB = 52,428,800 字节
# 说明：默认由 unified_config 的 feature.disable_progressive_layer=True 禁用
progressive_load_threshold = 50 * 1024 * 1024

# 快速加载阈值：小于等于此大小的图像直接全量加载
# 50MB = 52,428,800 字节，与渐进式阈值保持一致
# 用于：小图像优化，提供即时显示体验
fast_load_threshold = 50 * 1024 * 1024

# 预览图像质量系数：控制预览模式的图像质量
# 0.7 = 70%质量，平衡显示效果与加载速度
# 范围：0.0（最低质量）到 1.0（原始质量）
preview_quality = 0.7

# 渐进式加载步骤（兼容旧API）：定义质量递进序列
# 说明：默认关闭，仅兼容旧接口调用
progressive_steps = [0.25, 0.5, 0.75, 1.0]

# 最大预加载数量：双向缓存池同时预加载的图像数量上限
# 5个图像，平衡预加载效果与内存占用
# 用于：BidirectionalCachePool的智能预加载策略
max_preload_count = 5

# 缓存清理间隔：自动清理过期缓存的时间间隔
# 300秒 = 5分钟，定期释放不再需要的内存
# 用于：后台缓存维护，防止内存泄漏
cache_cleanup_interval = 300

# 内存压力阈值：触发积极内存清理的可用内存下限
# 2048MB = 2GB，当系统可用内存低于此值时加强清理
# 用于：动态内存管理，确保系统稳定性
memory_pressure_threshold = 2048

# 图像处理配置字典：集中管理所有图像处理相关参数
# 用于：统一配置管理，便于组件间共享设置
IMAGE_PROCESSING_CONFIG = {
    # Quartz渲染引擎启用状态：macOS平台的高质量图像渲染
    "quartz_enabled": QUARTZ_AVAILABLE,

    # 严格模式：仅允许Quartz解码。若Quartz不可用则在启动时失败
    "strict_quartz_only": True,

    # 最大预览分辨率：预览模式下图像的最大像素尺寸
    # 2560像素，适配2K显示器，平衡质量与性能
    "max_preview_resolution": 2560,

    # 渐进式加载阈值：配置项形式的阈值设置（MB单位）
    "progressive_load_threshold": 50,

    # 快速加载阈值：配置项形式的阈值设置（MB单位）
    # 简化为两级：50MB及以下原图加载，50MB以上智能加载
    "fast_load_threshold": 50,

    # 主缓存大小：主图像缓存池的容量限制
    # 50个缓存项，用于常用图像的快速访问
    "cache_size": 50,

    # 预览缓存大小：预览图像专用缓存的容量限制
    # 80个缓存项，预览图像占用内存较小可适当增加
    "preview_cache_size": 80,

    # 自适应质量：根据图像大小和系统性能动态调整质量
    "adaptive_quality": True,

    # 内存映射：大文件使用内存映射技术减少内存占用
    "memory_mapping": True,

    # 压缩缓存：缓存时使用压缩算法节省内存空间
    "compression_cache": True,

    # 预测性加载：基于用户行为预测并预加载可能访问的图像
    "predictive_loading": True,

    # 后台处理：在后台线程进行图像处理，避免阻塞UI
    "background_processing": True,

    # 智能缩放：根据显示需求智能选择缩放算法和参数
    "smart_scaling": True,

    # 快速加载启用：启用小图像的快速加载优化
    "fast_load_enabled": True,

    # 横向图像优化：针对宽屏图像的特殊优化处理
    "landscape_optimization": True,

    # 竖向图片优化：针对竖向图片的特殊优化处理
    "vertical_optimization": {
        "enabled": True,                     # 启用竖向图片优化
        "scale_factor": 0.8,                 # 竖向图片缩放因子
        "preload_enabled": True,             # 启用竖向图片预加载
        "memory_optimization": True,         # 启用内存优化
        "ultra_high_pixel_threshold": 2000,  # 超大像素阈值
        "progressive_loading": True,         # 启用渐进式加载
    },

    # 双线程处理：使用多线程并行处理提升性能
    "dual_thread_processing": True,

    # 横向图像缩放因子：横向图像的特殊缩放系数
    # 1.5倍，适配宽屏显示的视觉效果
    "landscape_scale_factor": 1.5,

    # EXIF处理策略：禁用EXIF处理以提高性能
    "exif_processing": {
        "process_orientation": True,      # 启用方向信息处理
        "process_metadata": True,        # 启用元数据处理
        "apply_exif_transform": True,    # 启用EXIF变换应用
    },

    # 性能优化选项
    "performance_optimizations": {
        "skip_exif_processing": True,     # 跳过EXIF处理
        "use_native_sizing": True,        # 使用原生尺寸获取
        "minimize_pil_usage": True,       # 最小化PIL使用
    },

    # 图像旋转功能配置
    "image_rotation": {
        "enabled": True,                  # 启用图像旋转功能
        "pil_threshold_mb": 10.0,          # PIL处理阈值
        "process_exif_orientation": True, # 处理EXIF方向信息
        "background_processing": True,    # 后台处理
        "enable_undo": True,              # 启用撤销功能
    },
}
