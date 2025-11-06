"""
加载策略配置

集中管理所有加载相关配置，避免分散的 get_config 调用，
提高热路径性能。

Author: PlookingII Team
Date: 2025-10-06
"""

from dataclasses import dataclass


@dataclass
class LoadingConfig:
    """加载配置

    集中管理所有加载相关配置，避免分散的 get_config 调用
    """

    # 文件大小阈值 (MB)
    quartz_threshold: float = 10.0  # 小于此值用NSImage
    memory_map_threshold: float = 100.0  # 大于此值用内存映射

    # 质量配置
    preview_max_size: int = 512
    thumbnail_quality: float = 0.7
    thumbnail_overscale_factor: float = 1.5

    # 大文件优化
    large_file_threshold_mb: float = 50.0
    large_file_overscale_factor: float = 1.2

    # 超高像素优化
    ultra_high_pixel_threshold_mp: float = 150.0
    high_pixel_threshold_mp: float = 50.0
    ultra_high_pixel_overscale: float = 1.0
    high_pixel_overscale: float = 1.1

    # 性能配置
    enable_cache: bool = True
    max_parallel_loads: int = 3
    prefer_cgimage_pipeline: bool = True

    # 统计
    enable_stats: bool = True

    # Slim mode（轻量模式）
    slim_mode: bool = False

    @classmethod
    def default(cls) -> "LoadingConfig":
        """默认配置"""
        return cls()

    @classmethod
    def fast(cls) -> "LoadingConfig":
        """快速模式（低质量，高性能）"""
        return cls(
            preview_max_size=256,
            thumbnail_quality=0.5,
            thumbnail_overscale_factor=1.0,
            slim_mode=True,
        )

    @classmethod
    def quality(cls) -> "LoadingConfig":
        """质量模式（高质量，低性能）"""
        return cls(
            preview_max_size=1024,
            thumbnail_quality=0.9,
            thumbnail_overscale_factor=2.0,
            slim_mode=False,
        )

    @classmethod
    def from_global_config(cls) -> "LoadingConfig":
        """从全局配置创建（兼容旧系统）"""
        try:
            from ...config.manager import get_config

            slim = get_config("feature.slim_mode", False)

            return cls(
                quartz_threshold=get_config("image_processing.quartz_threshold_mb", 10.0),
                memory_map_threshold=get_config("image_processing.memory_mapping_threshold_mb", 100.0),
                preview_max_size=get_config("image_processing.preview_max_size", 512),
                thumbnail_overscale_factor=(
                    1.0 if slim else get_config("image_processing.thumbnail_overscale_factor", 1.5)
                ),
                large_file_threshold_mb=get_config("image_processing.large_file_overscale_threshold_mb", 50.0),
                large_file_overscale_factor=get_config("image_processing.large_file_overscale_factor", 1.2),
                ultra_high_pixel_threshold_mp=get_config("image_processing.ultra_high_pixel_threshold_mp", 150.0),
                high_pixel_threshold_mp=get_config("image_processing.high_pixel_threshold_mp", 50.0),
                ultra_high_pixel_overscale=get_config("image_processing.ultra_high_pixel_overscale", 1.0),
                high_pixel_overscale=get_config("image_processing.high_pixel_overscale", 1.1),
                prefer_cgimage_pipeline=get_config("image_processing.prefer_cgimage_pipeline", True),
                slim_mode=slim,
            )
        except Exception:
            # 如果配置读取失败，返回默认配置
            return cls.default()


# 全局默认配置实例
_default_config: LoadingConfig | None = None


def get_default_config() -> LoadingConfig:
    """获取全局默认配置"""
    global _default_config  # noqa: PLW0603  # 单例模式的合理使用
    if _default_config is None:
        _default_config = LoadingConfig.from_global_config()
    return _default_config


def set_default_config(config: LoadingConfig) -> None:
    """设置全局默认配置"""
    global _default_config  # noqa: PLW0603  # 单例模式的合理使用
    _default_config = config
