#!/usr/bin/env python3
"""
缓存优化配置

统一管理所有缓存系统的配置，简化架构，避免重复。

设计原则：
- 2层缓存架构：Active Cache（当前活跃）+ Nearby Cache（预加载）
- 统一内存管理：所有缓存共享内存预算
- 智能清理策略：基于访问模式和内存压力自动清理
- 性能优先：简化复杂度，提升命中率

Author: PlookingII Team
Version: 1.0.0
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class CacheOptimizationConfig:
    """缓存优化配置

    简化的2层缓存架构配置，避免过度设计。
    """

    # ===== 内存预算 =====
    max_memory_mb: float = 2048.0
    """最大内存使用（MB），所有缓存共享此预算"""

    cleanup_threshold: float = 0.85
    """内存清理阈值（85%），超过此比例时触发清理"""

    target_threshold: float = 0.70
    """目标内存比例（70%），清理后保持在此水平"""

    # ===== Active Cache（活跃缓存）=====
    active_cache_size: int = 20
    """活跃缓存最大项数，存储当前正在查看的图片"""

    active_memory_ratio: float = 0.6
    """活跃缓存内存占比（60%）"""

    # ===== Nearby Cache（预加载缓存）=====
    nearby_cache_size: int = 15
    """预加载缓存最大项数，存储相邻的图片"""

    nearby_memory_ratio: float = 0.4
    """预加载缓存内存占比（40%）"""

    preload_forward: int = 3
    """向前预加载图片数量"""

    preload_backward: int = 1
    """向后预加载图片数量"""

    # ===== CGImage优化 =====
    cgimage_cache_enabled: bool = True
    """启用CGImage对象缓存，减少重复创建"""

    cgimage_cache_size: int = 10
    """CGImage缓存最大项数"""

    zero_copy_render: bool = True
    """启用零拷贝渲染，直接使用CGImage"""

    # ===== 淘汰策略 =====
    eviction_policy: str = "lru"
    """淘汰策略：lru（推荐）"""

    aggressive_cleanup: bool = True
    """激进清理模式：内存压力大时立即清理低优先级项"""

    # ===== 性能调优 =====
    enable_preload: bool = True
    """启用预加载"""

    adaptive_preload: bool = True
    """自适应预加载：根据用户浏览方向调整预加载策略"""

    enable_stats: bool = True
    """启用统计信息收集"""

    thread_safe: bool = True
    """启用线程安全（多线程环境必须启用）"""

    # ===== 清理策略 =====
    auto_cleanup_enabled: bool = True
    """启用自动清理"""

    cleanup_interval_sec: int = 30
    """自动清理间隔（秒）"""

    max_file_size_mb: float = 500.0
    """单个文件最大大小（MB），超过则使用特殊处理"""

    # ===== 调试选项 =====
    debug_logging: bool = False
    """启用详细的调试日志"""

    performance_monitoring: bool = True
    """启用性能监控"""

    def __post_init__(self):
        """验证配置参数"""
        # 验证内存比例
        total_ratio = self.active_memory_ratio + self.nearby_memory_ratio
        if abs(total_ratio - 1.0) > 0.01:
            raise ValueError(f"Memory ratios must sum to 1.0, got {total_ratio}")

        # 验证阈值
        if not 0.0 < self.cleanup_threshold <= 1.0:
            raise ValueError(f"cleanup_threshold must be in (0, 1], got {self.cleanup_threshold}")

        if not 0.0 < self.target_threshold < self.cleanup_threshold:
            raise ValueError(f"target_threshold must be in (0, cleanup_threshold), got {self.target_threshold}")

    @classmethod
    def default(cls) -> "CacheOptimizationConfig":
        """创建默认配置

        Returns:
            默认配置实例
        """
        return cls()

    @classmethod
    def performance_mode(cls) -> "CacheOptimizationConfig":
        """创建性能模式配置

        更大的内存预算，更激进的预加载。

        Returns:
            性能模式配置实例
        """
        return cls(
            max_memory_mb=4096.0,
            active_cache_size=30,
            nearby_cache_size=20,
            preload_forward=5,
            preload_backward=2,
            cgimage_cache_size=15
        )

    @classmethod
    def memory_saver_mode(cls) -> "CacheOptimizationConfig":
        """创建省内存模式配置

        更小的内存预算，更保守的预加载。

        Returns:
            省内存模式配置实例
        """
        return cls(
            max_memory_mb=1024.0,
            active_cache_size=10,
            nearby_cache_size=5,
            preload_forward=2,
            preload_backward=0,
            cgimage_cache_size=5,
            aggressive_cleanup=True
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典

        Returns:
            配置字典
        """
        return {
            "max_memory_mb": self.max_memory_mb,
            "cleanup_threshold": self.cleanup_threshold,
            "target_threshold": self.target_threshold,
            "active_cache_size": self.active_cache_size,
            "active_memory_ratio": self.active_memory_ratio,
            "nearby_cache_size": self.nearby_cache_size,
            "nearby_memory_ratio": self.nearby_memory_ratio,
            "preload_forward": self.preload_forward,
            "preload_backward": self.preload_backward,
            "cgimage_cache_enabled": self.cgimage_cache_enabled,
            "cgimage_cache_size": self.cgimage_cache_size,
            "zero_copy_render": self.zero_copy_render,
            "eviction_policy": self.eviction_policy,
            "aggressive_cleanup": self.aggressive_cleanup,
            "enable_preload": self.enable_preload,
            "adaptive_preload": self.adaptive_preload,
            "enable_stats": self.enable_stats,
            "thread_safe": self.thread_safe,
            "auto_cleanup_enabled": self.auto_cleanup_enabled,
            "cleanup_interval_sec": self.cleanup_interval_sec,
            "max_file_size_mb": self.max_file_size_mb,
            "debug_logging": self.debug_logging,
            "performance_monitoring": self.performance_monitoring
        }

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "CacheOptimizationConfig":
        """从字典创建配置

        Args:
            config_dict: 配置字典

        Returns:
            配置实例
        """
        return cls(**config_dict)


# 预定义配置
DEFAULT_CONFIG = CacheOptimizationConfig.default()
PERFORMANCE_CONFIG = CacheOptimizationConfig.performance_mode()
MEMORY_SAVER_CONFIG = CacheOptimizationConfig.memory_saver_mode()


def get_cache_config(mode: str = "default") -> CacheOptimizationConfig:
    """获取缓存配置

    Args:
        mode: 配置模式，可选值：'default', 'performance', 'memory_saver'

    Returns:
        缓存配置实例
    """
    if mode == "performance":
        return PERFORMANCE_CONFIG
    if mode == "memory_saver":
        return MEMORY_SAVER_CONFIG
    return DEFAULT_CONFIG


__all__ = [
    "DEFAULT_CONFIG",
    "MEMORY_SAVER_CONFIG",
    "PERFORMANCE_CONFIG",
    "CacheOptimizationConfig",
    "get_cache_config"
]

