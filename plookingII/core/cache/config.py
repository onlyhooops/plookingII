"""
缓存配置模块

统一的缓存配置管理，简化配置参数。

Author: PlookingII Team
Version: 2.0.0
"""

from dataclasses import dataclass


@dataclass
class CacheConfig:
    """统一缓存配置

    简化后的2层缓存架构配置：
    - Active Cache: 当前活跃图片（正在查看或刚看过的）
    - Nearby Cache: 相邻图片预加载（提前加载相邻的图片）
    """

    # ===== 内存配置 =====
    max_memory_mb: float = 2048.0
    """最大内存使用（MB），默认2GB"""

    cleanup_threshold: float = 0.8
    """内存清理阈值（0.0-1.0），当使用超过此比例时触发清理"""

    # ===== Active Cache (活跃缓存) =====
    active_cache_size: int = 50
    """活跃缓存最大项数，存储当前正在查看的图片"""

    # ===== Nearby Cache (预加载缓存) =====
    nearby_cache_size: int = 30
    """预加载缓存最大项数，存储相邻的图片"""

    preload_count: int = 5
    """每次预加载的图片数量（向前和向后各加载多少张）"""

    # ===== 策略配置 =====
    eviction_policy: str = "lru"
    """淘汰策略：'lru'（推荐）, 'lfu', 'arc'"""

    # ===== 性能调优 =====
    enable_preload: bool = True
    """是否启用预加载"""

    enable_stats: bool = True
    """是否启用统计信息收集"""

    thread_safe: bool = True
    """是否启用线程安全（多线程环境必须启用）"""

    # ===== 高级配置 =====
    max_file_size_mb: float = 500.0
    """单个文件最大大小（MB），超过则不缓存"""

    enable_auto_cleanup: bool = True
    """是否启用自动清理"""

    cleanup_interval: int = 60
    """自动清理间隔（秒）"""

    # ===== 调试选项 =====
    debug_logging: bool = False
    """是否启用详细的调试日志"""

    def __post_init__(self):
        """验证配置参数"""
        if self.max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive")

        if not 0 < self.cleanup_threshold <= 1.0:
            raise ValueError("cleanup_threshold must be between 0 and 1")

        if self.active_cache_size <= 0:
            raise ValueError("active_cache_size must be positive")

        if self.nearby_cache_size < 0:
            raise ValueError("nearby_cache_size must be non-negative")

        if self.eviction_policy not in ("lru", "lfu", "arc"):
            raise ValueError(f"Unknown eviction policy: {self.eviction_policy}")

    @property
    def total_cache_size(self) -> int:
        """总缓存项数"""
        return self.active_cache_size + self.nearby_cache_size

    @classmethod
    def default(cls) -> "CacheConfig":
        """创建默认配置"""
        return cls()

    @classmethod
    def lightweight(cls) -> "CacheConfig":
        """创建轻量级配置（低内存环境）"""
        return cls(
            max_memory_mb=512.0,
            active_cache_size=20,
            nearby_cache_size=10,
            preload_count=2,
            enable_auto_cleanup=True,
        )

    @classmethod
    def performance(cls) -> "CacheConfig":
        """创建高性能配置（大内存环境）"""
        return cls(
            max_memory_mb=4096.0,
            active_cache_size=100,
            nearby_cache_size=50,
            preload_count=10,
            enable_preload=True,
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "max_memory_mb": self.max_memory_mb,
            "cleanup_threshold": self.cleanup_threshold,
            "active_cache_size": self.active_cache_size,
            "nearby_cache_size": self.nearby_cache_size,
            "preload_count": self.preload_count,
            "eviction_policy": self.eviction_policy,
            "enable_preload": self.enable_preload,
            "enable_stats": self.enable_stats,
            "thread_safe": self.thread_safe,
            "max_file_size_mb": self.max_file_size_mb,
            "enable_auto_cleanup": self.enable_auto_cleanup,
            "cleanup_interval": self.cleanup_interval,
            "debug_logging": self.debug_logging,
        }

    def __repr__(self) -> str:
        """可读的字符串表示"""
        return (
            f"CacheConfig(memory={self.max_memory_mb}MB, "
            f"active={self.active_cache_size}, "
            f"nearby={self.nearby_cache_size}, "
            f"policy={self.eviction_policy})"
        )

