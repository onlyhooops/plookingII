"""
测试 core/memory_estimator.py 模块

测试目标：达到90%+覆盖率
"""

from unittest.mock import Mock, patch

import pytest

from plookingII.core.memory_estimator import ImageMemoryEstimator


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestImageMemoryEstimatorInit:
    """测试内存估算器初始化"""

    def test_init(self):
        """测试初始化"""
        estimator = ImageMemoryEstimator()
        assert estimator.cache == {}
        assert estimator.cache_max_size == 1000


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestNSImageMemoryEstimation:
    """测试NSImage内存估算"""

    def test_estimate_nsimage_memory_none(self):
        """测试None图像"""
        estimator = ImageMemoryEstimator()
        result = estimator.estimate_nsimage_memory(None)
        assert result == 0.0

    def test_estimate_nsimage_memory_basic(self):
        """测试基本NSImage内存估算"""
        estimator = ImageMemoryEstimator()

        # 模拟NSImage对象
        mock_image = Mock()
        mock_size = Mock()
        mock_size.width = 1920
        mock_size.height = 1080
        mock_image.size.return_value = mock_size

        with patch.object(estimator, "_get_nsimage_scale_factor", return_value=1.0):
            result = estimator.estimate_nsimage_memory(mock_image)

            # 1920 * 1080 * 4 bytes / (1024 * 1024) ≈ 7.91 MB
            assert result > 7.0
            assert result < 9.0

    def test_estimate_nsimage_memory_with_scale(self):
        """测试带缩放因子的NSImage内存估算"""
        estimator = ImageMemoryEstimator()

        # 模拟Retina显示器 (2x)
        mock_image = Mock()
        mock_size = Mock()
        mock_size.width = 1920
        mock_size.height = 1080
        mock_image.size.return_value = mock_size

        with patch.object(estimator, "_get_nsimage_scale_factor", return_value=2.0):
            result = estimator.estimate_nsimage_memory(mock_image)

            # 1920*2 * 1080*2 * 4 bytes / (1024 * 1024) ≈ 31.64 MB
            assert result > 30.0
            assert result < 35.0

    def test_estimate_nsimage_memory_cached(self):
        """测试缓存的内存估算"""
        estimator = ImageMemoryEstimator()

        mock_image = Mock()
        mock_size = Mock()
        mock_size.width = 1920
        mock_size.height = 1080
        mock_image.size.return_value = mock_size

        with patch.object(estimator, "_get_nsimage_scale_factor", return_value=1.0):
            # 第一次调用
            result1 = estimator.estimate_nsimage_memory(mock_image)
            # 第二次调用应该使用缓存
            result2 = estimator.estimate_nsimage_memory(mock_image)

            assert result1 == result2
            assert len(estimator.cache) > 0

    def test_estimate_nsimage_memory_exception(self):
        """测试异常处理"""
        estimator = ImageMemoryEstimator()

        # 模拟抛出异常的图像
        mock_image = Mock()
        mock_image.size.side_effect = Exception("Test error")

        result = estimator.estimate_nsimage_memory(mock_image)
        assert result == 1.0  # 默认值


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestPILImageMemoryEstimation:
    """测试PIL Image内存估算"""

    def test_estimate_pil_memory_none(self):
        """测试None图像"""
        estimator = ImageMemoryEstimator()
        result = estimator.estimate_pil_memory(None)
        assert result == 0.0

    def test_estimate_pil_memory_rgb(self):
        """测试RGB图像"""
        estimator = ImageMemoryEstimator()

        # 模拟PIL Image
        mock_image = Mock()
        mock_image.size = (1920, 1080)
        mock_image.mode = "RGB"

        result = estimator.estimate_pil_memory(mock_image)

        # 1920 * 1080 * 3 bytes / (1024 * 1024) ≈ 5.93 MB
        assert result > 5.0
        assert result < 7.0

    def test_estimate_pil_memory_rgba(self):
        """测试RGBA图像"""
        estimator = ImageMemoryEstimator()

        mock_image = Mock()
        mock_image.size = (1920, 1080)
        mock_image.mode = "RGBA"

        result = estimator.estimate_pil_memory(mock_image)

        # 1920 * 1080 * 4 bytes / (1024 * 1024) ≈ 7.91 MB
        assert result > 7.0
        assert result < 9.0

    def test_estimate_pil_memory_grayscale(self):
        """测试灰度图像"""
        estimator = ImageMemoryEstimator()

        mock_image = Mock()
        mock_image.size = (1920, 1080)
        mock_image.mode = "L"

        result = estimator.estimate_pil_memory(mock_image)

        # 1920 * 1080 * 1 byte / (1024 * 1024) ≈ 1.98 MB
        assert result > 1.5
        assert result < 2.5

    def test_estimate_pil_memory_various_modes(self):
        """测试各种颜色模式"""
        estimator = ImageMemoryEstimator()

        modes_and_bytes = {
            "L": 1,
            "P": 1,
            "RGB": 3,
            "RGBA": 4,
            "CMYK": 4,
            "LAB": 3,
            "HSV": 3,
            "I": 4,
            "F": 4,
        }

        for mode, expected_bytes in modes_and_bytes.items():
            mock_image = Mock()
            mock_image.size = (100, 100)
            mock_image.mode = mode

            result = estimator.estimate_pil_memory(mock_image)
            expected_mb = (100 * 100 * expected_bytes) / (1024 * 1024)

            assert abs(result - expected_mb) < 0.001

    def test_estimate_pil_memory_unknown_mode(self):
        """测试未知颜色模式"""
        estimator = ImageMemoryEstimator()

        mock_image = Mock()
        mock_image.size = (1920, 1080)
        mock_image.mode = "UNKNOWN"

        result = estimator.estimate_pil_memory(mock_image)

        # 应该使用默认值4字节
        assert result > 7.0
        assert result < 9.0

    def test_estimate_pil_memory_cached(self):
        """测试缓存"""
        estimator = ImageMemoryEstimator()

        mock_image = Mock()
        mock_image.size = (1920, 1080)
        mock_image.mode = "RGB"

        result1 = estimator.estimate_pil_memory(mock_image)
        result2 = estimator.estimate_pil_memory(mock_image)

        assert result1 == result2
        assert len(estimator.cache) > 0

    def test_estimate_pil_memory_exception(self):
        """测试异常处理"""
        estimator = ImageMemoryEstimator()

        mock_image = Mock()
        mock_image.size = None  # 会导致错误

        result = estimator.estimate_pil_memory(mock_image)
        assert result == 1.0  # 默认值


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestGenericImageMemoryEstimation:
    """测试通用图像内存估算"""

    def test_estimate_image_memory_nsimage(self):
        """测试识别NSImage"""
        estimator = ImageMemoryEstimator()

        # 模拟NSImage特征
        mock_image = Mock()
        mock_image.size.return_value = Mock(width=100, height=100)
        mock_image.backingScaleFactor.return_value = 1.0

        with patch.object(estimator, "estimate_nsimage_memory", return_value=5.0) as mock_method:
            result = estimator.estimate_image_memory(mock_image)
            mock_method.assert_called_once_with(mock_image)
            assert result == 5.0

    def test_estimate_image_memory_pil(self):
        """测试识别PIL Image"""
        estimator = ImageMemoryEstimator()

        # 模拟PIL Image特征（有size和mode，没有backingScaleFactor）
        mock_image = Mock()
        mock_image.size = (100, 100)
        mock_image.mode = "RGB"
        # 删除backingScaleFactor属性
        delattr(mock_image, "backingScaleFactor")

        with patch.object(estimator, "estimate_pil_memory", return_value=3.0) as mock_method:
            result = estimator.estimate_image_memory(mock_image)
            mock_method.assert_called_once_with(mock_image)
            assert result == 3.0

    def test_estimate_image_memory_unknown(self):
        """测试未知类型"""
        estimator = ImageMemoryEstimator()

        # 未知对象
        unknown_obj = "not an image"

        result = estimator.estimate_image_memory(unknown_obj)
        assert result == 1.0  # 默认值


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestScaleFactorDetection:
    """测试缩放因子检测"""

    def test_get_nsimage_scale_factor_method(self):
        """测试通过backingScaleFactor方法获取"""
        estimator = ImageMemoryEstimator()

        mock_image = Mock()
        mock_image.backingScaleFactor.return_value = 2.0

        result = estimator._get_nsimage_scale_factor(mock_image)
        assert result == 2.0

    def test_get_nsimage_scale_factor_recommended(self):
        """测试通过recommendedLayerContentsScale获取"""
        estimator = ImageMemoryEstimator()

        mock_image = Mock(spec=["recommendedLayerContentsScale"])
        mock_image.recommendedLayerContentsScale.return_value = 2.0

        result = estimator._get_nsimage_scale_factor(mock_image)
        assert result == 2.0

    def test_get_nsimage_scale_factor_default(self):
        """测试默认缩放因子"""
        estimator = ImageMemoryEstimator()

        # 创建一个Mock，但让backingScaleFactor方法抛出AttributeError
        mock_image = Mock()
        mock_image.backingScaleFactor.side_effect = AttributeError("No backingScaleFactor")

        result = estimator._get_nsimage_scale_factor(mock_image)
        assert result == 1.0

    def test_get_nsimage_scale_factor_exception(self):
        """测试异常处理"""
        estimator = ImageMemoryEstimator()

        mock_image = Mock()
        mock_image.backingScaleFactor.side_effect = Exception("Test error")

        result = estimator._get_nsimage_scale_factor(mock_image)
        assert result == 1.0


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestCacheManagement:
    """测试缓存管理"""

    def test_cache_result(self):
        """测试缓存结果"""
        estimator = ImageMemoryEstimator()

        estimator._cache_result("test_key", 10.0)
        assert "test_key" in estimator.cache
        assert estimator.cache["test_key"] == 10.0

    def test_cache_max_size(self):
        """测试缓存最大大小"""
        estimator = ImageMemoryEstimator()
        estimator.cache_max_size = 5

        # 添加超过最大大小的缓存
        for i in range(10):
            estimator._cache_result(f"key_{i}", float(i))

        # 应该只保留最大数量
        assert len(estimator.cache) <= 5

    def test_clear_cache(self):
        """测试清空缓存"""
        estimator = ImageMemoryEstimator()

        estimator._cache_result("key1", 1.0)
        estimator._cache_result("key2", 2.0)

        estimator.clear_cache()
        assert len(estimator.cache) == 0

    def test_get_cache_stats(self):
        """测试获取缓存统计"""
        estimator = ImageMemoryEstimator()
        estimator.cache_max_size = 10

        estimator._cache_result("key1", 1.0)
        estimator._cache_result("key2", 2.0)

        stats = estimator.get_cache_stats()
        assert isinstance(stats, dict)
        assert stats["cache_size"] == 2
        assert stats["max_cache_size"] == 10
        assert stats["cache_usage_ratio"] == 0.2


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestBytesPerPixel:
    """测试每像素字节数计算"""

    def test_get_pil_bytes_per_pixel_all_modes(self):
        """测试所有支持的模式"""
        estimator = ImageMemoryEstimator()

        expected_values = {
            "L": 1,
            "P": 1,
            "RGB": 3,
            "RGBA": 4,
            "CMYK": 4,
            "LAB": 3,
            "HSV": 3,
            "I": 4,
            "F": 4,
        }

        for mode, expected_bytes in expected_values.items():
            result = estimator._get_pil_bytes_per_pixel(mode)
            assert result == expected_bytes

    def test_get_pil_bytes_per_pixel_unknown(self):
        """测试未知模式"""
        estimator = ImageMemoryEstimator()

        result = estimator._get_pil_bytes_per_pixel("UNKNOWN_MODE")
        assert result == 4  # 默认值


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestEdgeCases:
    """测试边缘情况"""

    def test_very_large_image(self):
        """测试超大图像"""
        estimator = ImageMemoryEstimator()

        mock_image = Mock()
        mock_image.size = (10000, 10000)
        mock_image.mode = "RGBA"

        result = estimator.estimate_pil_memory(mock_image)

        # 10000 * 10000 * 4 / (1024 * 1024) ≈ 381.47 MB
        assert result > 380.0
        assert result < 385.0

    def test_very_small_image(self):
        """测试超小图像"""
        estimator = ImageMemoryEstimator()

        mock_image = Mock()
        mock_image.size = (1, 1)
        mock_image.mode = "RGB"

        result = estimator.estimate_pil_memory(mock_image)
        assert result > 0
        assert result < 0.001

    def test_multiple_estimates_same_image(self):
        """测试同一图像的多次估算"""
        estimator = ImageMemoryEstimator()

        mock_image = Mock()
        mock_image.size = (1920, 1080)
        mock_image.mode = "RGB"

        results = [estimator.estimate_pil_memory(mock_image) for _ in range(5)]

        # 所有结果应该相同（使用缓存）
        assert all(r == results[0] for r in results)

    def test_cache_with_different_images(self):
        """测试不同图像的缓存"""
        estimator = ImageMemoryEstimator()

        # 创建多个不同的图像
        images = []
        for i in range(10):
            mock_image = Mock()
            mock_image.size = (100 + i * 10, 100 + i * 10)
            mock_image.mode = "RGB"
            images.append(mock_image)

        # 估算所有图像
        for img in images:
            estimator.estimate_pil_memory(img)

        # 缓存应该包含所有图像
        assert len(estimator.cache) == 10
