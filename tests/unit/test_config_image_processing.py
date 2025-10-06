#!/usr/bin/env python3
"""
测试 config/image_processing_config.py

Author: PlookingII Team
"""

from plookingII.config.image_processing_config import (
    CACHE_CONFIG,
    EXIF_PROCESSING_CONFIG,
    IMAGE_LOADING_OPTIMIZATIONS,
    IMAGE_ROTATION_CONFIG,
    PERFORMANCE_MONITORING,
    PIL_FALLBACK_CONFIG,
    QUARTZ_CONFIG,
)


class TestExifProcessingConfig:
    """测试 EXIF 处理配置"""

    def test_exif_config_structure(self):
        """测试配置结构"""
        assert isinstance(EXIF_PROCESSING_CONFIG, dict)
        assert "process_orientation" in EXIF_PROCESSING_CONFIG
        assert "process_metadata" in EXIF_PROCESSING_CONFIG
        assert "apply_exif_transform" in EXIF_PROCESSING_CONFIG

    def test_exif_config_values(self):
        """测试配置值（性能优化：默认关闭）"""
        assert EXIF_PROCESSING_CONFIG["process_orientation"] is False
        assert EXIF_PROCESSING_CONFIG["process_metadata"] is False
        assert EXIF_PROCESSING_CONFIG["apply_exif_transform"] is False


class TestImageLoadingOptimizations:
    """测试图像加载优化配置"""

    def test_loading_optimizations_structure(self):
        """测试配置结构"""
        assert isinstance(IMAGE_LOADING_OPTIMIZATIONS, dict)
        required_keys = [
            "fast_load_threshold",
            "fast_load_enabled",
            "progressive_load_threshold",
            "progressive_load_enabled",
            "preview_load_threshold",
            "preview_load_enabled",
        ]
        for key in required_keys:
            assert key in IMAGE_LOADING_OPTIMIZATIONS

    def test_loading_optimizations_values(self):
        """测试配置值"""
        assert IMAGE_LOADING_OPTIMIZATIONS["fast_load_threshold"] == 50
        assert IMAGE_LOADING_OPTIMIZATIONS["fast_load_enabled"] is True
        assert IMAGE_LOADING_OPTIMIZATIONS["progressive_load_threshold"] == 100
        assert IMAGE_LOADING_OPTIMIZATIONS["progressive_load_enabled"] is True
        assert IMAGE_LOADING_OPTIMIZATIONS["preview_load_threshold"] == 20
        assert IMAGE_LOADING_OPTIMIZATIONS["preview_load_enabled"] is True

    def test_loading_thresholds_order(self):
        """测试阈值顺序合理性"""
        preview = IMAGE_LOADING_OPTIMIZATIONS["preview_load_threshold"]
        fast = IMAGE_LOADING_OPTIMIZATIONS["fast_load_threshold"]
        progressive = IMAGE_LOADING_OPTIMIZATIONS["progressive_load_threshold"]

        assert preview < fast < progressive


class TestQuartzConfig:
    """测试 Quartz 配置"""

    def test_quartz_config_structure(self):
        """测试配置结构"""
        assert isinstance(QUARTZ_CONFIG, dict)
        required_keys = [
            "enabled",
            "should_cache",
            "should_allow_float",
            "create_thumbnail_always",
            "apply_exif_transform",
            "should_cache_immediately",
        ]
        for key in required_keys:
            assert key in QUARTZ_CONFIG

    def test_quartz_config_values(self):
        """测试配置值"""
        assert QUARTZ_CONFIG["enabled"] is True
        assert QUARTZ_CONFIG["should_cache"] is True
        assert QUARTZ_CONFIG["should_allow_float"] is True
        assert QUARTZ_CONFIG["create_thumbnail_always"] is True
        assert QUARTZ_CONFIG["apply_exif_transform"] is False
        assert QUARTZ_CONFIG["should_cache_immediately"] is False


class TestPilFallbackConfig:
    """测试 PIL 备用方案配置"""

    def test_pil_config_structure(self):
        """测试配置结构"""
        assert isinstance(PIL_FALLBACK_CONFIG, dict)
        required_keys = [
            "enabled",
            "process_exif",
            "default_quality",
            "optimize_save",
            "resampling_method",
        ]
        for key in required_keys:
            assert key in PIL_FALLBACK_CONFIG

    def test_pil_config_values(self):
        """测试配置值"""
        assert PIL_FALLBACK_CONFIG["enabled"] is True
        assert PIL_FALLBACK_CONFIG["process_exif"] is False
        assert PIL_FALLBACK_CONFIG["default_quality"] == 95
        assert PIL_FALLBACK_CONFIG["optimize_save"] is True
        assert PIL_FALLBACK_CONFIG["resampling_method"] == "LANCZOS"


class TestCacheConfig:
    """测试缓存配置"""

    def test_cache_config_structure(self):
        """测试配置结构"""
        assert isinstance(CACHE_CONFIG, dict)
        required_keys = [
            "max_size",
            "max_preview_size",
            "max_preload_size",
            "max_memory_mb",
            "max_preview_memory_mb",
            "max_preload_memory_mb",
        ]
        for key in required_keys:
            assert key in CACHE_CONFIG

    def test_cache_config_values(self):
        """测试配置值"""
        assert CACHE_CONFIG["max_size"] == 20
        assert CACHE_CONFIG["max_preview_size"] == 10
        assert CACHE_CONFIG["max_preload_size"] == 5
        assert CACHE_CONFIG["max_memory_mb"] == 4096
        assert CACHE_CONFIG["max_preview_memory_mb"] == 600
        assert CACHE_CONFIG["max_preload_memory_mb"] == 1200

    def test_cache_sizes_order(self):
        """测试缓存大小顺序合理性"""
        preload = CACHE_CONFIG["max_preload_size"]
        preview = CACHE_CONFIG["max_preview_size"]
        main = CACHE_CONFIG["max_size"]

        assert preload < preview < main

    def test_memory_limits_order(self):
        """测试内存限制顺序合理性"""
        preview_mem = CACHE_CONFIG["max_preview_memory_mb"]
        preload_mem = CACHE_CONFIG["max_preload_memory_mb"]
        total_mem = CACHE_CONFIG["max_memory_mb"]

        # 子缓存内存总和应小于总内存
        assert preview_mem + preload_mem < total_mem


class TestPerformanceMonitoring:
    """测试性能监控配置"""

    def test_monitoring_config_structure(self):
        """测试配置结构"""
        assert isinstance(PERFORMANCE_MONITORING, dict)
        required_keys = [
            "enabled",
            "detailed_logging",
            "warning_threshold",
            "error_threshold",
        ]
        for key in required_keys:
            assert key in PERFORMANCE_MONITORING

    def test_monitoring_config_values(self):
        """测试配置值"""
        assert PERFORMANCE_MONITORING["enabled"] is True
        assert PERFORMANCE_MONITORING["detailed_logging"] is False
        assert PERFORMANCE_MONITORING["warning_threshold"] == 1.0
        assert PERFORMANCE_MONITORING["error_threshold"] == 5.0

    def test_thresholds_order(self):
        """测试阈值顺序"""
        warning = PERFORMANCE_MONITORING["warning_threshold"]
        error = PERFORMANCE_MONITORING["error_threshold"]

        assert warning < error


class TestImageRotationConfig:
    """测试图像旋转配置"""

    def test_rotation_config_structure(self):
        """测试配置结构"""
        assert isinstance(IMAGE_ROTATION_CONFIG, dict)
        required_keys = [
            "enabled",
            "pil_threshold_mb",
            "quartz_threshold_mb",
            "process_exif_orientation",
            "rotation_quality",
            "performance",
            "ui",
        ]
        for key in required_keys:
            assert key in IMAGE_ROTATION_CONFIG

    def test_rotation_config_basic_values(self):
        """测试基本配置值"""
        assert IMAGE_ROTATION_CONFIG["enabled"] is True
        assert IMAGE_ROTATION_CONFIG["pil_threshold_mb"] == 10.0
        assert IMAGE_ROTATION_CONFIG["quartz_threshold_mb"] == 10.0
        assert IMAGE_ROTATION_CONFIG["process_exif_orientation"] is True

    def test_rotation_quality_config(self):
        """测试旋转质量配置"""
        quality = IMAGE_ROTATION_CONFIG["rotation_quality"]
        assert isinstance(quality, dict)
        assert quality["jpeg_quality"] == 95
        assert quality["png_optimize"] is True
        assert quality["resampling_method"] == "LANCZOS"

    def test_rotation_performance_config(self):
        """测试旋转性能配置"""
        performance = IMAGE_ROTATION_CONFIG["performance"]
        assert isinstance(performance, dict)
        assert performance["background_processing"] is True
        assert performance["cache_clear_after_rotation"] is True
        assert performance["max_rotation_stack_size"] == 10

    def test_rotation_ui_config(self):
        """测试旋转UI配置"""
        ui = IMAGE_ROTATION_CONFIG["ui"]
        assert isinstance(ui, dict)
        assert ui["show_rotation_progress"] is True
        assert ui["rotation_feedback_duration"] == 2.0
        assert ui["enable_rotation_undo"] is True


class TestConfigExports:
    """测试配置导出"""

    def test_all_configs_exported(self):
        """测试所有配置都可以导入"""
        from plookingII.config import image_processing_config

        assert hasattr(image_processing_config, "EXIF_PROCESSING_CONFIG")
        assert hasattr(image_processing_config, "IMAGE_LOADING_OPTIMIZATIONS")
        assert hasattr(image_processing_config, "QUARTZ_CONFIG")
        assert hasattr(image_processing_config, "PIL_FALLBACK_CONFIG")
        assert hasattr(image_processing_config, "CACHE_CONFIG")
        assert hasattr(image_processing_config, "PERFORMANCE_MONITORING")
        assert hasattr(image_processing_config, "IMAGE_ROTATION_CONFIG")

    def test_config_types(self):
        """测试所有配置都是字典类型"""
        configs = [
            EXIF_PROCESSING_CONFIG,
            IMAGE_LOADING_OPTIMIZATIONS,
            QUARTZ_CONFIG,
            PIL_FALLBACK_CONFIG,
            CACHE_CONFIG,
            PERFORMANCE_MONITORING,
            IMAGE_ROTATION_CONFIG,
        ]

        for config in configs:
            assert isinstance(config, dict)


class TestConfigIntegration:
    """测试配置集成"""

    def test_exif_processing_consistency(self):
        """测试 EXIF 处理配置一致性"""
        # Quartz 和 PIL 都应该遵循相同的 EXIF 处理策略
        assert QUARTZ_CONFIG["apply_exif_transform"] == EXIF_PROCESSING_CONFIG["apply_exif_transform"]
        assert PIL_FALLBACK_CONFIG["process_exif"] == EXIF_PROCESSING_CONFIG["process_metadata"]

    def test_rotation_thresholds_equal(self):
        """测试旋转阈值相等（切换点）"""
        # PIL 和 Quartz 阈值应该在同一点
        assert IMAGE_ROTATION_CONFIG["pil_threshold_mb"] == IMAGE_ROTATION_CONFIG["quartz_threshold_mb"]

    def test_all_boolean_configs_are_valid(self):
        """测试所有布尔配置值有效"""
        def check_booleans(config_dict):
            for key, value in config_dict.items():
                if isinstance(value, dict):
                    check_booleans(value)
                elif key.startswith("enable") or key.startswith("should") or key.endswith("enabled"):
                    assert isinstance(value, bool)

        check_booleans(EXIF_PROCESSING_CONFIG)
        check_booleans(IMAGE_LOADING_OPTIMIZATIONS)
        check_booleans(QUARTZ_CONFIG)
        check_booleans(PIL_FALLBACK_CONFIG)
        check_booleans(PERFORMANCE_MONITORING)
        check_booleans(IMAGE_ROTATION_CONFIG)

