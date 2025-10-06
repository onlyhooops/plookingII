#!/usr/bin/env python3
"""
测试 config/cache_optimization_config.py

Author: PlookingII Team
"""

import pytest

from plookingII.config.cache_optimization_config import (
    DEFAULT_CONFIG,
    MEMORY_SAVER_CONFIG,
    PERFORMANCE_CONFIG,
    CacheOptimizationConfig,
    get_cache_config,
)


class TestCacheOptimizationConfig:
    """测试 CacheOptimizationConfig 类"""

    def test_default_config_creation(self):
        """测试默认配置创建"""
        config = CacheOptimizationConfig()
        assert config.max_memory_mb == 2048.0
        assert config.active_cache_size == 20
        assert config.nearby_cache_size == 15
        assert config.preload_forward == 3
        assert config.preload_backward == 1

    def test_memory_ratio_validation(self):
        """测试内存比例验证"""
        # 正常情况
        config = CacheOptimizationConfig(active_memory_ratio=0.6, nearby_memory_ratio=0.4)
        assert config.active_memory_ratio == 0.6
        assert config.nearby_memory_ratio == 0.4

        # 比例和不为1.0应该抛出异常
        with pytest.raises(ValueError, match="Memory ratios must sum to 1.0"):
            CacheOptimizationConfig(active_memory_ratio=0.5, nearby_memory_ratio=0.4)

    def test_cleanup_threshold_validation(self):
        """测试清理阈值验证"""
        # 正常情况
        config = CacheOptimizationConfig(cleanup_threshold=0.85)
        assert config.cleanup_threshold == 0.85

        # 无效阈值
        with pytest.raises(ValueError, match="cleanup_threshold must be in"):
            CacheOptimizationConfig(cleanup_threshold=0.0)

        with pytest.raises(ValueError, match="cleanup_threshold must be in"):
            CacheOptimizationConfig(cleanup_threshold=1.5)

    def test_target_threshold_validation(self):
        """测试目标阈值验证"""
        # 正常情况
        config = CacheOptimizationConfig(target_threshold=0.70, cleanup_threshold=0.85)
        assert config.target_threshold == 0.70

        # target_threshold 必须小于 cleanup_threshold
        with pytest.raises(ValueError, match="target_threshold must be in"):
            CacheOptimizationConfig(target_threshold=0.9, cleanup_threshold=0.85)

    def test_default_class_method(self):
        """测试 default 类方法"""
        config = CacheOptimizationConfig.default()
        assert isinstance(config, CacheOptimizationConfig)
        assert config.max_memory_mb == 2048.0
        assert config.eviction_policy == "lru"

    def test_performance_mode(self):
        """测试性能模式配置"""
        config = CacheOptimizationConfig.performance_mode()
        assert config.max_memory_mb == 4096.0
        assert config.active_cache_size == 30
        assert config.nearby_cache_size == 20
        assert config.preload_forward == 5
        assert config.preload_backward == 2
        assert config.cgimage_cache_size == 15

    def test_memory_saver_mode(self):
        """测试省内存模式配置"""
        config = CacheOptimizationConfig.memory_saver_mode()
        assert config.max_memory_mb == 1024.0
        assert config.active_cache_size == 10
        assert config.nearby_cache_size == 5
        assert config.preload_forward == 2
        assert config.preload_backward == 0
        assert config.cgimage_cache_size == 5
        assert config.aggressive_cleanup is True

    def test_to_dict(self):
        """测试转换为字典"""
        config = CacheOptimizationConfig()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["max_memory_mb"] == 2048.0
        assert config_dict["active_cache_size"] == 20
        assert config_dict["nearby_cache_size"] == 15
        assert config_dict["eviction_policy"] == "lru"
        assert "cgimage_cache_enabled" in config_dict
        assert "enable_preload" in config_dict

    def test_from_dict(self):
        """测试从字典创建配置"""
        config_dict = {
            "max_memory_mb": 3000.0,
            "active_cache_size": 25,
            "nearby_cache_size": 10,
            "active_memory_ratio": 0.7,
            "nearby_memory_ratio": 0.3,
            "cleanup_threshold": 0.8,
            "target_threshold": 0.6,
        }

        config = CacheOptimizationConfig.from_dict(config_dict)
        assert config.max_memory_mb == 3000.0
        assert config.active_cache_size == 25
        assert config.nearby_cache_size == 10
        assert config.active_memory_ratio == 0.7
        assert config.nearby_memory_ratio == 0.3

    def test_to_dict_from_dict_roundtrip(self):
        """测试字典转换往返一致性"""
        original = CacheOptimizationConfig(
            max_memory_mb=1500.0,
            active_cache_size=15,
            nearby_cache_size=10,
        )

        config_dict = original.to_dict()
        restored = CacheOptimizationConfig.from_dict(config_dict)

        assert restored.max_memory_mb == original.max_memory_mb
        assert restored.active_cache_size == original.active_cache_size
        assert restored.nearby_cache_size == original.nearby_cache_size
        assert restored.eviction_policy == original.eviction_policy

    def test_cgimage_config(self):
        """测试 CGImage 相关配置"""
        config = CacheOptimizationConfig()
        assert config.cgimage_cache_enabled is True
        assert config.cgimage_cache_size == 10
        assert config.zero_copy_render is True

    def test_preload_config(self):
        """测试预加载配置"""
        config = CacheOptimizationConfig()
        assert config.enable_preload is True
        assert config.adaptive_preload is True
        assert config.preload_forward == 3
        assert config.preload_backward == 1

    def test_eviction_policy(self):
        """测试淘汰策略配置"""
        config = CacheOptimizationConfig()
        assert config.eviction_policy == "lru"
        assert config.aggressive_cleanup is True

    def test_performance_monitoring_config(self):
        """测试性能监控配置"""
        config = CacheOptimizationConfig()
        assert config.enable_stats is True
        assert config.performance_monitoring is True
        assert config.debug_logging is False

    def test_thread_safe_config(self):
        """测试线程安全配置"""
        config = CacheOptimizationConfig()
        assert config.thread_safe is True

    def test_auto_cleanup_config(self):
        """测试自动清理配置"""
        config = CacheOptimizationConfig()
        assert config.auto_cleanup_enabled is True
        assert config.cleanup_interval_sec == 30
        assert config.max_file_size_mb == 500.0


class TestPredefinedConfigs:
    """测试预定义配置"""

    def test_default_config(self):
        """测试默认配置实例"""
        assert isinstance(DEFAULT_CONFIG, CacheOptimizationConfig)
        assert DEFAULT_CONFIG.max_memory_mb == 2048.0

    def test_performance_config(self):
        """测试性能配置实例"""
        assert isinstance(PERFORMANCE_CONFIG, CacheOptimizationConfig)
        assert PERFORMANCE_CONFIG.max_memory_mb == 4096.0

    def test_memory_saver_config(self):
        """测试省内存配置实例"""
        assert isinstance(MEMORY_SAVER_CONFIG, CacheOptimizationConfig)
        assert MEMORY_SAVER_CONFIG.max_memory_mb == 1024.0


class TestGetCacheConfig:
    """测试 get_cache_config 函数"""

    def test_get_default_config(self):
        """测试获取默认配置"""
        config = get_cache_config("default")
        assert config is DEFAULT_CONFIG

    def test_get_performance_config(self):
        """测试获取性能配置"""
        config = get_cache_config("performance")
        assert config is PERFORMANCE_CONFIG

    def test_get_memory_saver_config(self):
        """测试获取省内存配置"""
        config = get_cache_config("memory_saver")
        assert config is MEMORY_SAVER_CONFIG

    def test_get_default_when_invalid_mode(self):
        """测试无效模式返回默认配置"""
        config = get_cache_config("invalid_mode")
        assert config is DEFAULT_CONFIG

    def test_get_default_when_no_argument(self):
        """测试无参数返回默认配置"""
        config = get_cache_config()
        assert config is DEFAULT_CONFIG


class TestCacheOptimizationConfigEdgeCases:
    """测试 CacheOptimizationConfig 边界情况"""

    def test_minimum_valid_thresholds(self):
        """测试最小有效阈值"""
        config = CacheOptimizationConfig(
            cleanup_threshold=0.5,
            target_threshold=0.4,
        )
        assert config.cleanup_threshold == 0.5
        assert config.target_threshold == 0.4

    def test_custom_cache_sizes(self):
        """测试自定义缓存大小"""
        config = CacheOptimizationConfig(
            active_cache_size=50,
            nearby_cache_size=30,
            cgimage_cache_size=20,
        )
        assert config.active_cache_size == 50
        assert config.nearby_cache_size == 30
        assert config.cgimage_cache_size == 20

    def test_custom_preload_settings(self):
        """测试自定义预加载设置"""
        config = CacheOptimizationConfig(
            preload_forward=10,
            preload_backward=5,
            enable_preload=False,
        )
        assert config.preload_forward == 10
        assert config.preload_backward == 5
        assert config.enable_preload is False

    def test_all_features_disabled(self):
        """测试禁用所有可选功能"""
        config = CacheOptimizationConfig(
            cgimage_cache_enabled=False,
            zero_copy_render=False,
            enable_preload=False,
            adaptive_preload=False,
            enable_stats=False,
            performance_monitoring=False,
            auto_cleanup_enabled=False,
        )
        assert config.cgimage_cache_enabled is False
        assert config.zero_copy_render is False
        assert config.enable_preload is False
        assert config.adaptive_preload is False
        assert config.enable_stats is False
        assert config.performance_monitoring is False
        assert config.auto_cleanup_enabled is False
