"""
测试 core/cache/config.py

测试缓存配置功能
"""

import pytest

from plookingII.core.cache.config import CacheConfig


# ==================== 基本测试 ====================


class TestCacheConfigInit:
    """测试CacheConfig初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        config = CacheConfig()
        
        assert config.max_memory_mb == 2048.0
        assert config.active_cache_size == 50
        assert config.nearby_cache_size == 30
        assert config.eviction_policy == "lru"

    def test_init_custom(self):
        """测试自定义初始化"""
        config = CacheConfig(
            max_memory_mb=1024.0,
            active_cache_size=100,
            nearby_cache_size=50
        )
        
        assert config.max_memory_mb == 1024.0
        assert config.active_cache_size == 100
        assert config.nearby_cache_size == 50


# ==================== 验证测试 ====================


class TestCacheConfigValidation:
    """测试CacheConfig验证"""

    def test_validation_negative_memory(self):
        """测试负内存值"""
        with pytest.raises(ValueError, match="max_memory_mb must be positive"):
            CacheConfig(max_memory_mb=-1)

    def test_validation_zero_memory(self):
        """测试零内存值"""
        with pytest.raises(ValueError, match="max_memory_mb must be positive"):
            CacheConfig(max_memory_mb=0)

    def test_validation_cleanup_threshold_zero(self):
        """测试清理阈值为0"""
        with pytest.raises(ValueError, match="cleanup_threshold must be between 0 and 1"):
            CacheConfig(cleanup_threshold=0)

    def test_validation_cleanup_threshold_negative(self):
        """测试负清理阈值"""
        with pytest.raises(ValueError, match="cleanup_threshold must be between 0 and 1"):
            CacheConfig(cleanup_threshold=-0.5)

    def test_validation_cleanup_threshold_over_one(self):
        """测试清理阈值大于1"""
        with pytest.raises(ValueError, match="cleanup_threshold must be between 0 and 1"):
            CacheConfig(cleanup_threshold=1.5)

    def test_validation_cleanup_threshold_valid(self):
        """测试有效的清理阈值"""
        config = CacheConfig(cleanup_threshold=1.0)
        assert config.cleanup_threshold == 1.0

    def test_validation_negative_active_cache(self):
        """测试负活跃缓存大小"""
        with pytest.raises(ValueError, match="active_cache_size must be positive"):
            CacheConfig(active_cache_size=-1)

    def test_validation_zero_active_cache(self):
        """测试零活跃缓存大小"""
        with pytest.raises(ValueError, match="active_cache_size must be positive"):
            CacheConfig(active_cache_size=0)

    def test_validation_negative_nearby_cache(self):
        """测试负预加载缓存大小"""
        with pytest.raises(ValueError, match="nearby_cache_size must be non-negative"):
            CacheConfig(nearby_cache_size=-1)

    def test_validation_zero_nearby_cache_ok(self):
        """测试零预加载缓存大小（允许）"""
        config = CacheConfig(nearby_cache_size=0)
        assert config.nearby_cache_size == 0

    def test_validation_invalid_eviction_policy(self):
        """测试无效淘汰策略"""
        with pytest.raises(ValueError, match="Unknown eviction policy"):
            CacheConfig(eviction_policy="invalid")

    def test_validation_valid_eviction_policies(self):
        """测试有效淘汰策略"""
        for policy in ["lru", "lfu", "arc"]:
            config = CacheConfig(eviction_policy=policy)
            assert config.eviction_policy == policy


# ==================== 属性测试 ====================


class TestCacheConfigProperties:
    """测试CacheConfig属性"""

    def test_total_cache_size(self):
        """测试总缓存大小"""
        config = CacheConfig(active_cache_size=50, nearby_cache_size=30)
        
        assert config.total_cache_size == 80

    def test_total_cache_size_zero_nearby(self):
        """测试零预加载缓存的总大小"""
        config = CacheConfig(active_cache_size=50, nearby_cache_size=0)
        
        assert config.total_cache_size == 50


# ==================== 工厂方法测试 ====================


class TestCacheConfigFactoryMethods:
    """测试CacheConfig工厂方法"""

    def test_default_factory(self):
        """测试default工厂方法"""
        config = CacheConfig.default()
        
        assert config.max_memory_mb == 2048.0
        assert config.active_cache_size == 50
        assert config.nearby_cache_size == 30

    def test_lightweight_factory(self):
        """测试lightweight工厂方法"""
        config = CacheConfig.lightweight()
        
        assert config.max_memory_mb == 512.0
        assert config.active_cache_size == 20
        assert config.nearby_cache_size == 10
        assert config.preload_count == 2
        assert config.enable_auto_cleanup is True

    def test_performance_factory(self):
        """测试performance工厂方法"""
        config = CacheConfig.performance()
        
        assert config.max_memory_mb == 4096.0
        assert config.active_cache_size == 100
        assert config.nearby_cache_size == 50
        assert config.preload_count == 10
        assert config.enable_preload is True


# ==================== 转换方法测试 ====================


class TestCacheConfigConversion:
    """测试CacheConfig转换方法"""

    def test_to_dict(self):
        """测试to_dict方法"""
        config = CacheConfig()
        
        result = config.to_dict()
        
        assert isinstance(result, dict)
        assert "max_memory_mb" in result
        assert "active_cache_size" in result
        assert "nearby_cache_size" in result
        assert "eviction_policy" in result
        assert result["max_memory_mb"] == 2048.0
        assert result["active_cache_size"] == 50

    def test_to_dict_custom_config(self):
        """测试自定义配置的to_dict"""
        config = CacheConfig(
            max_memory_mb=1024.0,
            active_cache_size=100,
            debug_logging=True
        )
        
        result = config.to_dict()
        
        assert result["max_memory_mb"] == 1024.0
        assert result["active_cache_size"] == 100
        assert result["debug_logging"] is True

    def test_repr(self):
        """测试__repr__方法"""
        config = CacheConfig()
        
        result = repr(config)
        
        assert isinstance(result, str)
        assert "CacheConfig" in result
        assert "memory=2048.0MB" in result
        assert "active=50" in result
        assert "nearby=30" in result
        assert "policy=lru" in result

    def test_repr_custom_config(self):
        """测试自定义配置的__repr__"""
        config = CacheConfig(
            max_memory_mb=512.0,
            active_cache_size=20,
            nearby_cache_size=10,
            eviction_policy="lfu"
        )
        
        result = repr(config)
        
        assert "memory=512.0MB" in result
        assert "active=20" in result
        assert "nearby=10" in result
        assert "policy=lfu" in result


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    def test_complete_workflow(self):
        """测试完整工作流"""
        # 1. 创建配置
        config = CacheConfig.default()
        assert config.max_memory_mb == 2048.0
        
        # 2. 获取总大小
        total = config.total_cache_size
        assert total == 80
        
        # 3. 转换为字典
        d = config.to_dict()
        assert isinstance(d, dict)
        
        # 4. 字符串表示
        s = repr(config)
        assert isinstance(s, str)

    def test_factory_methods_comparison(self):
        """测试工厂方法对比"""
        default = CacheConfig.default()
        lightweight = CacheConfig.lightweight()
        performance = CacheConfig.performance()
        
        # 轻量级 < 默认 < 高性能
        assert lightweight.max_memory_mb < default.max_memory_mb < performance.max_memory_mb
        assert lightweight.active_cache_size < default.active_cache_size < performance.active_cache_size


# ==================== 边界情况测试 ====================


class TestEdgeCases:
    """测试边界情况"""

    def test_minimal_valid_config(self):
        """测试最小有效配置"""
        config = CacheConfig(
            max_memory_mb=0.1,
            cleanup_threshold=0.01,
            active_cache_size=1,
            nearby_cache_size=0
        )
        
        assert config.max_memory_mb == 0.1
        assert config.cleanup_threshold == 0.01
        assert config.active_cache_size == 1
        assert config.nearby_cache_size == 0

    def test_maximum_values(self):
        """测试极大值"""
        config = CacheConfig(
            max_memory_mb=100000.0,
            active_cache_size=10000,
            nearby_cache_size=10000
        )
        
        assert config.max_memory_mb == 100000.0
        assert config.total_cache_size == 20000

    def test_all_features_disabled(self):
        """测试所有功能禁用"""
        config = CacheConfig(
            enable_preload=False,
            enable_stats=False,
            enable_auto_cleanup=False,
            debug_logging=False
        )
        
        assert config.enable_preload is False
        assert config.enable_stats is False
        assert config.enable_auto_cleanup is False
        assert config.debug_logging is False

    def test_all_features_enabled(self):
        """测试所有功能启用"""
        config = CacheConfig(
            enable_preload=True,
            enable_stats=True,
            enable_auto_cleanup=True,
            debug_logging=True,
            thread_safe=True
        )
        
        assert config.enable_preload is True
        assert config.enable_stats is True
        assert config.enable_auto_cleanup is True
        assert config.debug_logging is True
        assert config.thread_safe is True

