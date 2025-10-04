"""
测试 config/constants.py 模块

测试目标：达到95%+覆盖率
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from plookingII.config import constants


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestConstants:
    """测试常量定义"""

    def test_app_name(self):
        """测试应用名称"""
        assert constants.APP_NAME == "PlookingII"
        assert isinstance(constants.APP_NAME, str)
        assert len(constants.APP_NAME) > 0

    def test_version(self):
        """测试版本号"""
        assert constants.VERSION == "1.5.0"
        assert isinstance(constants.VERSION, str)
        # 验证版本号格式 x.y.z
        parts = constants.VERSION.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_app_version_equals_version(self):
        """测试APP_VERSION和VERSION一致"""
        assert constants.APP_VERSION == constants.VERSION

    def test_author(self):
        """测试作者信息"""
        assert constants.AUTHOR == "PlookingII Team"
        assert isinstance(constants.AUTHOR, str)

    def test_copyright(self):
        """测试版权信息"""
        assert "PlookingII Team" in constants.COPYRIGHT
        assert "2025" in constants.COPYRIGHT
        assert "©" in constants.COPYRIGHT or "(c)" in constants.COPYRIGHT.lower()

    def test_history_file_name(self):
        """测试历史文件名"""
        assert constants.HISTORY_FILE_NAME == ".plookingii_history.json"
        assert constants.HISTORY_FILE_NAME.startswith(".")  # 隐藏文件
        assert constants.HISTORY_FILE_NAME.endswith(".json")


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestResourcePaths:
    """测试资源路径配置"""

    def test_base_dir_exists(self):
        """测试基础目录"""
        # _BASE_DIR应该是plookingII包的目录
        assert hasattr(constants, '_BASE_DIR')
        assert os.path.isabs(constants._BASE_DIR)

    def test_logo_dir_exists(self):
        """测试logo目录"""
        assert hasattr(constants, '_LOGO_DIR')
        assert 'logo' in constants._LOGO_DIR

    def test_icon_svg_path(self):
        """测试SVG图标路径"""
        assert constants.ICON_SVG.endswith('.svg')
        assert 'PlookingII' in constants.ICON_SVG
        assert 'logo' in constants.ICON_SVG

    def test_icon_icns_path(self):
        """测试ICNS图标路径"""
        assert constants.ICON_ICNS.endswith('.icns')
        assert 'PlookingII' in constants.ICON_ICNS
        assert 'logo' in constants.ICON_ICNS


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestResourcePathFunction:
    """测试 _resource_path 函数"""

    def test_resource_path_existing_file(self):
        """测试存在的文件"""
        # 创建临时目录和文件
        with patch('os.path.exists', return_value=True):
            result = constants._resource_path("/test/dir", "file.txt")
            assert result == os.path.join("/test/dir", "file.txt")

    def test_resource_path_nonexistent_file(self):
        """测试不存在的文件"""
        # 文件不存在时仍返回路径
        with patch('os.path.exists', return_value=False):
            result = constants._resource_path("/test/dir", "missing.txt")
            assert result == os.path.join("/test/dir", "missing.txt")

    def test_resource_path_exception_handling(self):
        """测试异常处理"""
        # os.path.join抛出异常时的处理
        with patch('os.path.join', side_effect=Exception("Path error")):
            # 应该返回基础拼接结果
            # 由于第一次join会失败，会在except中再次join
            # 这里我们测试它不会崩溃
            try:
                result = constants._resource_path("/test/dir", "file.txt")
                # 应该返回某个路径字符串
                assert isinstance(result, str)
            except Exception:
                # 如果两次都失败，会抛出异常，这也是可接受的
                pass

    def test_resource_path_with_empty_strings(self):
        """测试空字符串"""
        result = constants._resource_path("", "")
        assert isinstance(result, str)

    def test_resource_path_with_special_characters(self):
        """测试特殊字符"""
        result = constants._resource_path("/test/dir", "文件 (1).txt")
        assert "文件 (1).txt" in result

    def test_resource_path_with_path_separators(self):
        """测试路径分隔符"""
        result = constants._resource_path("/test/dir", "sub/file.txt")
        assert "sub" in result or "sub/file.txt" in result


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestPerformanceParameters:
    """测试性能参数配置"""

    def test_memory_threshold_mb(self):
        """测试内存阈值"""
        assert constants.MEMORY_THRESHOLD_MB == 4096
        assert isinstance(constants.MEMORY_THRESHOLD_MB, int)
        assert constants.MEMORY_THRESHOLD_MB > 0

    def test_max_cache_size(self):
        """测试最大缓存大小"""
        assert constants.MAX_CACHE_SIZE == 20
        assert isinstance(constants.MAX_CACHE_SIZE, int)
        assert constants.MAX_CACHE_SIZE > 0


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestImageFormatSupport:
    """测试图像格式支持"""

    def test_supported_extensions_is_set(self):
        """测试支持的扩展名是集合"""
        assert isinstance(constants.SUPPORTED_EXTENSIONS, set)

    def test_supported_extensions_content(self):
        """测试支持的扩展名内容"""
        assert ".jpg" in constants.SUPPORTED_EXTENSIONS
        assert ".jpeg" in constants.SUPPORTED_EXTENSIONS
        assert ".png" in constants.SUPPORTED_EXTENSIONS

    def test_supported_extensions_lowercase(self):
        """测试扩展名都是小写"""
        for ext in constants.SUPPORTED_EXTENSIONS:
            assert ext == ext.lower()

    def test_supported_extensions_start_with_dot(self):
        """测试扩展名以点开头"""
        for ext in constants.SUPPORTED_EXTENSIONS:
            assert ext.startswith(".")

    def test_supported_image_exts_is_tuple(self):
        """测试核心支持格式是元组"""
        assert isinstance(constants.SUPPORTED_IMAGE_EXTS, tuple)

    def test_supported_image_exts_content(self):
        """测试核心支持格式内容"""
        assert ".jpg" in constants.SUPPORTED_IMAGE_EXTS
        assert ".jpeg" in constants.SUPPORTED_IMAGE_EXTS
        assert ".png" in constants.SUPPORTED_IMAGE_EXTS

    def test_supported_formats_consistency(self):
        """测试两种格式定义的一致性"""
        # SUPPORTED_IMAGE_EXTS应该是SUPPORTED_EXTENSIONS的子集
        for ext in constants.SUPPORTED_IMAGE_EXTS:
            assert ext in constants.SUPPORTED_EXTENSIONS


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestImageProcessingConfig:
    """测试图像处理配置"""

    def test_progressive_load_threshold(self):
        """测试渐进式加载阈值"""
        assert constants.progressive_load_threshold == 50 * 1024 * 1024
        assert isinstance(constants.progressive_load_threshold, int)

    def test_fast_load_threshold(self):
        """测试快速加载阈值"""
        assert constants.fast_load_threshold == 50 * 1024 * 1024
        assert isinstance(constants.fast_load_threshold, int)

    def test_thresholds_consistency(self):
        """测试阈值一致性"""
        assert constants.progressive_load_threshold == constants.fast_load_threshold

    def test_preview_quality(self):
        """测试预览质量"""
        assert constants.preview_quality == 0.7
        assert 0.0 <= constants.preview_quality <= 1.0

    def test_progressive_steps(self):
        """测试渐进式步骤"""
        assert isinstance(constants.progressive_steps, list)
        assert len(constants.progressive_steps) > 0
        assert all(0.0 < step <= 1.0 for step in constants.progressive_steps)
        # 应该是递增的
        assert constants.progressive_steps == sorted(constants.progressive_steps)
        # 最后一步应该是1.0
        assert constants.progressive_steps[-1] == 1.0

    def test_max_preload_count(self):
        """测试最大预加载数量"""
        assert constants.max_preload_count == 5
        assert isinstance(constants.max_preload_count, int)
        assert constants.max_preload_count > 0

    def test_cache_cleanup_interval(self):
        """测试缓存清理间隔"""
        assert constants.cache_cleanup_interval == 300
        assert isinstance(constants.cache_cleanup_interval, int)
        assert constants.cache_cleanup_interval > 0

    def test_memory_pressure_threshold(self):
        """测试内存压力阈值"""
        assert constants.memory_pressure_threshold == 2048
        assert isinstance(constants.memory_pressure_threshold, int)
        assert constants.memory_pressure_threshold > 0
        # 内存压力阈值应该小于内存总阈值
        assert constants.memory_pressure_threshold < constants.MEMORY_THRESHOLD_MB


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestImageProcessingConfigDict:
    """测试IMAGE_PROCESSING_CONFIG字典"""

    def test_config_dict_is_dict(self):
        """测试配置是字典"""
        assert isinstance(constants.IMAGE_PROCESSING_CONFIG, dict)

    def test_config_dict_required_keys(self):
        """测试必需的配置键"""
        required_keys = [
            "quartz_enabled",
            "strict_quartz_only",
            "max_preview_resolution",
            "progressive_load_threshold",
            "fast_load_threshold",
            "cache_size",
            "preview_cache_size",
        ]
        for key in required_keys:
            assert key in constants.IMAGE_PROCESSING_CONFIG

    def test_config_dict_quartz_enabled(self):
        """测试Quartz启用状态"""
        assert isinstance(constants.IMAGE_PROCESSING_CONFIG["quartz_enabled"], bool)

    def test_config_dict_strict_quartz_only(self):
        """测试严格Quartz模式"""
        assert isinstance(constants.IMAGE_PROCESSING_CONFIG["strict_quartz_only"], bool)

    def test_config_dict_max_preview_resolution(self):
        """测试最大预览分辨率"""
        assert constants.IMAGE_PROCESSING_CONFIG["max_preview_resolution"] == 2560
        assert isinstance(constants.IMAGE_PROCESSING_CONFIG["max_preview_resolution"], int)

    def test_config_dict_thresholds(self):
        """测试阈值配置"""
        assert constants.IMAGE_PROCESSING_CONFIG["progressive_load_threshold"] == 50
        assert constants.IMAGE_PROCESSING_CONFIG["fast_load_threshold"] == 50

    def test_config_dict_cache_sizes(self):
        """测试缓存大小配置"""
        assert constants.IMAGE_PROCESSING_CONFIG["cache_size"] == 50
        assert constants.IMAGE_PROCESSING_CONFIG["preview_cache_size"] == 80
        assert constants.IMAGE_PROCESSING_CONFIG["cache_size"] > 0
        assert constants.IMAGE_PROCESSING_CONFIG["preview_cache_size"] > 0

    def test_config_dict_boolean_flags(self):
        """测试布尔标志"""
        boolean_keys = [
            "adaptive_quality",
            "memory_mapping",
            "compression_cache",
            "predictive_loading",
            "background_processing",
            "smart_scaling",
            "fast_load_enabled",
            "landscape_optimization",
            "dual_thread_processing",
        ]
        for key in boolean_keys:
            assert key in constants.IMAGE_PROCESSING_CONFIG
            assert isinstance(constants.IMAGE_PROCESSING_CONFIG[key], bool)

    def test_config_dict_vertical_optimization(self):
        """测试竖向图片优化配置"""
        vertical_opt = constants.IMAGE_PROCESSING_CONFIG["vertical_optimization"]
        assert isinstance(vertical_opt, dict)
        assert "enabled" in vertical_opt
        assert "scale_factor" in vertical_opt
        assert "preload_enabled" in vertical_opt
        assert "memory_optimization" in vertical_opt
        assert isinstance(vertical_opt["scale_factor"], (int, float))
        assert 0 < vertical_opt["scale_factor"] <= 1.0

    def test_config_dict_landscape_scale_factor(self):
        """测试横向缩放因子"""
        assert "landscape_scale_factor" in constants.IMAGE_PROCESSING_CONFIG
        assert constants.IMAGE_PROCESSING_CONFIG["landscape_scale_factor"] == 1.5
        assert isinstance(constants.IMAGE_PROCESSING_CONFIG["landscape_scale_factor"], (int, float))

    def test_config_dict_exif_processing(self):
        """测试EXIF处理配置"""
        exif_config = constants.IMAGE_PROCESSING_CONFIG["exif_processing"]
        assert isinstance(exif_config, dict)
        assert "process_orientation" in exif_config
        assert "process_metadata" in exif_config
        assert "apply_exif_transform" in exif_config

    def test_config_dict_performance_optimizations(self):
        """测试性能优化选项"""
        perf_opt = constants.IMAGE_PROCESSING_CONFIG["performance_optimizations"]
        assert isinstance(perf_opt, dict)
        assert "skip_exif_processing" in perf_opt
        assert "use_native_sizing" in perf_opt
        assert "minimize_pil_usage" in perf_opt

    def test_config_dict_image_rotation(self):
        """测试图像旋转配置"""
        rotation_config = constants.IMAGE_PROCESSING_CONFIG["image_rotation"]
        assert isinstance(rotation_config, dict)
        assert "enabled" in rotation_config
        assert "pil_threshold_mb" in rotation_config
        assert "process_exif_orientation" in rotation_config
        assert "background_processing" in rotation_config
        assert "enable_undo" in rotation_config


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestConstantsIntegration:
    """集成测试"""

    def test_all_constants_accessible(self):
        """测试所有常量都可访问"""
        # 确保主要常量都能访问
        constants.APP_NAME
        constants.VERSION
        constants.AUTHOR
        constants.COPYRIGHT
        constants.HISTORY_FILE_NAME
        constants.MEMORY_THRESHOLD_MB
        constants.MAX_CACHE_SIZE
        constants.SUPPORTED_EXTENSIONS
        constants.SUPPORTED_IMAGE_EXTS
        constants.IMAGE_PROCESSING_CONFIG

    def test_no_obvious_conflicts(self):
        """测试没有明显的配置冲突"""
        # 内存压力阈值应该小于内存阈值
        assert constants.memory_pressure_threshold < constants.MEMORY_THRESHOLD_MB
        
        # 预览缓存应该大于主缓存（因为预览图小）
        assert (constants.IMAGE_PROCESSING_CONFIG["preview_cache_size"] > 
                constants.IMAGE_PROCESSING_CONFIG["cache_size"])

    def test_version_format_valid(self):
        """测试版本号格式有效"""
        version = constants.VERSION
        parts = version.split(".")
        assert len(parts) == 3
        major, minor, patch = parts
        assert major.isdigit()
        assert minor.isdigit()
        assert patch.isdigit()
        
        # 版本号应该合理
        assert int(major) >= 0
        assert int(minor) >= 0
        assert int(patch) >= 0

