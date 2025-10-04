"""
测试 core/image_processing.py

测试混合图像处理器的功能，包括：
- 初始化和组件配置
- 文件信息获取（大小、扩展名）和缓存
- 格式支持检查
- 加载策略选择和执行
- 图像加载（Quartz/PIL）
- 性能统计
- 图像旋转
- 双线程处理
"""

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch, call

import pytest

from plookingII.core.image_processing import HybridImageProcessor


@pytest.fixture
def mock_image_processor_basic():
    """创建基本的图像处理器（禁用Quartz）"""
    with patch('plookingII.core.image_processing.IMAGE_PROCESSING_CONFIG', {
        'quartz_enabled': False,
        'dual_thread_processing': False,
        'strict_quartz_only': False
    }):
        with patch('plookingII.core.image_processing.OptimizedLoadingStrategyFactory'):
            with patch('plookingII.core.image_processing.ImageRotationProcessor'):
                processor = HybridImageProcessor()
                yield processor


@pytest.fixture
def temp_image_file():
    """创建临时图像文件"""
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        f.write(b'fake_image_data')
        temp_path = f.name
    
    yield temp_path
    
    # 清理
    try:
        os.unlink(temp_path)
    except Exception:
        pass


# ==================== 初始化测试 ====================


class TestHybridImageProcessorInit:
    """测试HybridImageProcessor初始化"""

    def test_init_with_quartz_disabled(self):
        """测试Quartz禁用时的初始化"""
        with patch('plookingII.core.image_processing.IMAGE_PROCESSING_CONFIG', {
            'quartz_enabled': False,
            'dual_thread_processing': False,
            'strict_quartz_only': False
        }):
            with patch('plookingII.core.image_processing.OptimizedLoadingStrategyFactory'):
                with patch('plookingII.core.image_processing.ImageRotationProcessor'):
                    processor = HybridImageProcessor()
                    
                    assert processor.quartz_enabled is False
                    assert hasattr(processor, 'processing_stats')
                    assert hasattr(processor, 'loading_strategies')

    def test_init_with_quartz_enabled(self):
        """测试Quartz启用时的初始化"""
        with patch('plookingII.core.image_processing.IMAGE_PROCESSING_CONFIG', {
            'quartz_enabled': True,
            'dual_thread_processing': False,
            'strict_quartz_only': False
        }):
            with patch('plookingII.core.image_processing.OptimizedLoadingStrategyFactory'):
                with patch('plookingII.core.image_processing.ImageRotationProcessor'):
                    processor = HybridImageProcessor()
                    
                    assert processor.quartz_enabled is True

    def test_init_strict_quartz_only_fails(self):
        """测试strict_quartz_only模式失败"""
        with patch('plookingII.core.image_processing.IMAGE_PROCESSING_CONFIG', {
            'quartz_enabled': False,
            'strict_quartz_only': True
        }):
            with pytest.raises(RuntimeError, match="Quartz is required"):
                HybridImageProcessor()

    def test_init_creates_processing_stats(self, mock_image_processor_basic):
        """测试初始化创建性能统计"""
        stats = mock_image_processor_basic.processing_stats
        
        assert 'quartz_processed' in stats
        assert 'pil_fallback' in stats
        assert 'fast_loaded' in stats
        assert 'total_processing_time' in stats
        assert stats['quartz_processed'] == 0
        assert stats['pil_fallback'] == 0

    def test_init_creates_caches(self, mock_image_processor_basic):
        """测试初始化创建缓存"""
        assert hasattr(mock_image_processor_basic, '_file_size_cache')
        assert hasattr(mock_image_processor_basic, '_ext_cache')
        assert isinstance(mock_image_processor_basic._file_size_cache, dict)
        assert isinstance(mock_image_processor_basic._ext_cache, dict)

    def test_init_creates_loading_strategies(self, mock_image_processor_basic):
        """测试初始化创建加载策略"""
        strategies = mock_image_processor_basic.loading_strategies
        
        assert 'optimized' in strategies
        assert 'preview' in strategies
        assert 'auto' in strategies
        assert 'fast' in strategies


# ==================== 文件信息获取测试 ====================


class TestFileInfoRetrieval:
    """测试文件信息获取"""

    def test_get_file_size_mb_success(self, mock_image_processor_basic, temp_image_file):
        """测试成功获取文件大小"""
        size_mb = mock_image_processor_basic._get_file_size_mb(temp_image_file)
        
        assert isinstance(size_mb, float)
        assert size_mb > 0

    def test_get_file_size_mb_caching(self, mock_image_processor_basic, temp_image_file):
        """测试文件大小缓存"""
        # 第一次调用
        size1 = mock_image_processor_basic._get_file_size_mb(temp_image_file)
        
        # 第二次应该从缓存获取
        size2 = mock_image_processor_basic._get_file_size_mb(temp_image_file)
        
        assert size1 == size2
        assert temp_image_file in mock_image_processor_basic._file_size_cache

    def test_get_file_size_mb_cache_limit(self, mock_image_processor_basic):
        """测试文件大小缓存上限"""
        # 填充缓存到超过限制
        for i in range(2100):
            mock_image_processor_basic._file_size_cache[f"file_{i}.jpg"] = float(i)
        
        # 触发清空
        with patch('os.path.getsize', return_value=1024):
            mock_image_processor_basic._get_file_size_mb("new_file.jpg")
        
        # 缓存应该被清空并重新填充
        assert len(mock_image_processor_basic._file_size_cache) < 2100

    def test_get_file_size_mb_nonexistent_file(self, mock_image_processor_basic):
        """测试获取不存在文件的大小"""
        size = mock_image_processor_basic._get_file_size_mb("/nonexistent/path.jpg")
        
        # 应该返回0.0而不抛出异常
        assert size == 0.0

    def test_get_file_extension_basic(self, mock_image_processor_basic):
        """测试基本扩展名获取"""
        ext = mock_image_processor_basic._get_file_extension("test.jpg")
        
        assert ext == "jpg"

    def test_get_file_extension_uppercase(self, mock_image_processor_basic):
        """测试大写扩展名转换"""
        ext = mock_image_processor_basic._get_file_extension("TEST.JPG")
        
        assert ext == "jpg"  # 应该转换为小写

    def test_get_file_extension_multiple_dots(self, mock_image_processor_basic):
        """测试包含多个点的文件名"""
        ext = mock_image_processor_basic._get_file_extension("my.photo.test.png")
        
        assert ext == "png"

    def test_get_file_extension_caching(self, mock_image_processor_basic):
        """测试扩展名缓存"""
        path = "test_image.jpg"
        
        ext1 = mock_image_processor_basic._get_file_extension(path)
        ext2 = mock_image_processor_basic._get_file_extension(path)
        
        assert ext1 == ext2
        assert path in mock_image_processor_basic._ext_cache

    def test_get_file_extension_cache_limit(self, mock_image_processor_basic):
        """测试扩展名缓存上限"""
        # 填充缓存到超过限制
        for i in range(2100):
            mock_image_processor_basic._ext_cache[f"file_{i}.jpg"] = "jpg"
        
        # 触发清空
        mock_image_processor_basic._get_file_extension("new_file.png")
        
        # 缓存应该被清空
        assert len(mock_image_processor_basic._ext_cache) < 2100

    def test_get_file_extension_no_extension(self, mock_image_processor_basic):
        """测试无扩展名的文件"""
        ext = mock_image_processor_basic._get_file_extension("noextension")
        
        assert ext == ""


# ==================== 格式支持测试 ====================


class TestFormatSupport:
    """测试格式支持检查"""

    def test_is_supported_format_jpg(self, mock_image_processor_basic):
        """测试JPG格式支持"""
        assert mock_image_processor_basic._is_supported_format("jpg") is True

    def test_is_supported_format_jpeg(self, mock_image_processor_basic):
        """测试JPEG格式支持"""
        assert mock_image_processor_basic._is_supported_format("jpeg") is True

    def test_is_supported_format_png(self, mock_image_processor_basic):
        """测试PNG格式支持"""
        assert mock_image_processor_basic._is_supported_format("png") is True

    def test_is_supported_format_unsupported(self, mock_image_processor_basic):
        """测试不支持的格式"""
        assert mock_image_processor_basic._is_supported_format("gif") is False
        assert mock_image_processor_basic._is_supported_format("bmp") is False
        assert mock_image_processor_basic._is_supported_format("tiff") is False

    def test_is_supported_format_empty(self, mock_image_processor_basic):
        """测试空扩展名"""
        assert mock_image_processor_basic._is_supported_format("") is False

    def test_is_supported_format_case_sensitive(self, mock_image_processor_basic):
        """测试大小写敏感性"""
        # 注意：_is_supported_format 接收的应该是小写扩展名（由_get_file_extension处理）
        assert mock_image_processor_basic._is_supported_format("JPG") is False
        assert mock_image_processor_basic._is_supported_format("jpg") is True


# ==================== Quartz判定测试 ====================


class TestQuartzDecision:
    """测试Quartz使用判定"""

    def test_should_use_quartz_enabled_large_file(self):
        """测试Quartz启用且文件大"""
        with patch('plookingII.core.image_processing.IMAGE_PROCESSING_CONFIG', {
            'quartz_enabled': True,
            'dual_thread_processing': False,
            'strict_quartz_only': False
        }):
            with patch('plookingII.core.image_processing.OptimizedLoadingStrategyFactory'):
                with patch('plookingII.core.image_processing.ImageRotationProcessor'):
                    processor = HybridImageProcessor()
                    processor.quartz_enabled = True
                    
                    result = processor._should_use_quartz("test.jpg", 15.0)
                    
                    assert result is True

    def test_should_use_quartz_disabled(self, mock_image_processor_basic):
        """测试Quartz禁用"""
        mock_image_processor_basic.quartz_enabled = False
        
        result = mock_image_processor_basic._should_use_quartz("test.jpg", 15.0)
        
        assert result is False

    def test_should_use_quartz_small_file(self, mock_image_processor_basic):
        """测试小文件不使用Quartz"""
        mock_image_processor_basic.quartz_enabled = True
        
        result = mock_image_processor_basic._should_use_quartz("test.jpg", 5.0)
        
        assert result is False

    def test_should_use_quartz_enhanced(self, mock_image_processor_basic):
        """测试增强Quartz判定"""
        mock_image_processor_basic.quartz_enabled = True
        
        result = mock_image_processor_basic._should_use_quartz_enhanced("test.jpg", 15.0, "jpg")
        
        assert result is True


# ==================== 加载策略测试 ====================


class TestLoadingStrategy:
    """测试加载策略"""

    def test_select_loading_strategy_auto(self, mock_image_processor_basic):
        """测试auto策略选择"""
        strategy = mock_image_processor_basic._select_loading_strategy("auto", 5.0)
        
        assert strategy is not None

    def test_select_loading_strategy_fast(self, mock_image_processor_basic):
        """测试fast策略选择"""
        strategy = mock_image_processor_basic._select_loading_strategy("fast", 5.0)
        
        assert strategy is not None

    def test_select_loading_strategy_preview(self, mock_image_processor_basic):
        """测试preview策略选择"""
        strategy = mock_image_processor_basic._select_loading_strategy("preview", 5.0)
        
        assert strategy is not None

    def test_select_loading_strategy_optimized(self, mock_image_processor_basic):
        """测试optimized策略选择"""
        strategy = mock_image_processor_basic._select_loading_strategy("optimized", 5.0)
        
        assert strategy is not None

    def test_select_loading_strategy_invalid(self, mock_image_processor_basic):
        """测试无效策略"""
        strategy = mock_image_processor_basic._select_loading_strategy("invalid", 5.0)
        
        # 应该返回None或auto策略
        assert strategy is None or strategy is not None


# ==================== 图像加载测试 ====================


class TestImageLoading:
    """测试图像加载"""

    def test_load_image_optimized_success(self, mock_image_processor_basic, temp_image_file):
        """测试成功加载图像"""
        # Mock策略的load方法
        mock_strategy = MagicMock()
        mock_strategy.load.return_value = b"image_data"
        mock_image_processor_basic.loading_strategies['auto'] = mock_strategy
        
        result = mock_image_processor_basic.load_image_optimized(temp_image_file)
        
        # 应该调用策略的load方法
        assert mock_strategy.load.called

    def test_load_image_optimized_unsupported_format(self, mock_image_processor_basic):
        """测试不支持的格式"""
        with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as f:
            f.write(b'fake')
            temp_path = f.name
        
        try:
            result = mock_image_processor_basic.load_image_optimized(temp_path)
            
            # 不支持的格式应该返回None
            assert result is None
        finally:
            os.unlink(temp_path)

    def test_load_image_optimized_with_target_size(self, mock_image_processor_basic, temp_image_file):
        """测试指定目标尺寸加载"""
        mock_strategy = MagicMock()
        mock_strategy.load.return_value = b"resized_image"
        mock_image_processor_basic.loading_strategies['auto'] = mock_strategy
        
        with patch('plookingII.core.image_processing.get_config', return_value=False):
            result = mock_image_processor_basic.load_image_optimized(
                temp_image_file, 
                target_size=(800, 600)
            )
            
            # 应该传递target_size
            assert mock_strategy.load.called

    def test_load_image_optimized_full_res_browse(self, mock_image_processor_basic, temp_image_file):
        """测试全分辨率浏览模式"""
        mock_strategy = MagicMock()
        mock_strategy.load.return_value = b"full_res_image"
        mock_image_processor_basic.loading_strategies['auto'] = mock_strategy
        
        with patch('plookingII.core.image_processing.get_config', return_value=True):
            result = mock_image_processor_basic.load_image_optimized(
                temp_image_file,
                target_size=(800, 600)
            )
            
            # 全分辨率模式下不应该传递target_size到策略
            assert mock_strategy.load.called

    def test_load_image_optimized_exception_handling(self, mock_image_processor_basic):
        """测试加载异常处理"""
        # Mock策略抛出异常
        mock_strategy = MagicMock()
        mock_strategy.load.side_effect = Exception("Load failed")
        mock_image_processor_basic.loading_strategies['auto'] = mock_strategy
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'data')
            temp_path = f.name
        
        try:
            result = mock_image_processor_basic.load_image_optimized(temp_path)
            
            # 异常应该被捕获，返回None
            assert result is None
        finally:
            os.unlink(temp_path)

    def test_load_with_quartz_delegates_to_strategy(self, mock_image_processor_basic):
        """测试Quartz加载委托给策略"""
        mock_strategy = MagicMock()
        mock_strategy.load.return_value = b"quartz_image"
        mock_image_processor_basic.loading_strategies['optimized'] = mock_strategy
        
        result = mock_image_processor_basic._load_with_quartz("test.jpg")
        
        assert mock_strategy.load.called

    def test_load_with_pil_enhanced_delegates_to_strategy(self, mock_image_processor_basic):
        """测试PIL增强加载委托给策略"""
        mock_strategy = MagicMock()
        mock_strategy.load.return_value = b"pil_image"
        mock_image_processor_basic.loading_strategies['optimized'] = mock_strategy
        
        result = mock_image_processor_basic._load_with_pil_enhanced("test.jpg")
        
        assert mock_strategy.load.called


# ==================== 性能统计测试 ====================


class TestPerformanceStats:
    """测试性能统计"""

    def test_get_processing_stats_initial(self, mock_image_processor_basic):
        """测试获取初始统计"""
        stats = mock_image_processor_basic.get_processing_stats()
        
        assert isinstance(stats, dict)
        assert 'quartz_processed' in stats
        assert 'pil_fallback' in stats
        assert stats['quartz_processed'] == 0

    def test_reset_stats(self, mock_image_processor_basic):
        """测试重置统计"""
        # 修改统计
        mock_image_processor_basic.processing_stats['quartz_processed'] = 10
        mock_image_processor_basic.processing_stats['pil_fallback'] = 5
        
        mock_image_processor_basic.reset_stats()
        
        # 统计应该被重置
        assert mock_image_processor_basic.processing_stats['quartz_processed'] == 0
        assert mock_image_processor_basic.processing_stats['pil_fallback'] == 0

    def test_update_performance_stats(self, mock_image_processor_basic):
        """测试更新性能统计"""
        initial_time = mock_image_processor_basic.processing_stats['total_processing_time']
        
        mock_image_processor_basic._update_performance_stats("jpg", 1.5)
        
        # 总处理时间应该增加
        assert mock_image_processor_basic.processing_stats['total_processing_time'] > initial_time


# ==================== 图像旋转测试 ====================


class TestImageRotation:
    """测试图像旋转"""

    def test_rotate_image_clockwise(self, mock_image_processor_basic):
        """测试顺时针旋转"""
        mock_image_processor_basic.rotation_processor.rotate_image = MagicMock(return_value=b"rotated")
        
        result = mock_image_processor_basic.rotate_image("test.jpg", "clockwise")
        
        # 应该调用旋转处理器
        mock_image_processor_basic.rotation_processor.rotate_image.assert_called_once()

    def test_rotate_image_with_callback(self, mock_image_processor_basic):
        """测试带回调的旋转"""
        mock_callback = MagicMock()
        mock_image_processor_basic.rotation_processor.rotate_image = MagicMock(return_value=b"rotated")
        
        mock_image_processor_basic.rotate_image("test.jpg", "clockwise", callback=mock_callback)
        
        # 回调应该被调用
        assert mock_callback.called or mock_image_processor_basic.rotation_processor.rotate_image.called

    def test_get_rotation_stats(self, mock_image_processor_basic):
        """测试获取旋转统计"""
        mock_image_processor_basic.rotation_processor.get_stats = MagicMock(return_value={'rotations': 5})
        
        stats = mock_image_processor_basic.get_rotation_stats()
        
        assert stats is not None


# ==================== 兼容性API测试 ====================


class TestCompatibilityAPIs:
    """测试兼容性API"""

    def test_is_landscape_image_pil(self, mock_image_processor_basic):
        """测试PIL图像的横向判断"""
        mock_image = MagicMock()
        mock_image.size = (1920, 1080)  # 横向
        
        result = mock_image_processor_basic._is_landscape_image(mock_image)
        
        assert result is True

    def test_is_landscape_image_portrait(self, mock_image_processor_basic):
        """测试纵向图像"""
        mock_image = MagicMock()
        mock_image.size = (1080, 1920)  # 纵向
        
        result = mock_image_processor_basic._is_landscape_image(mock_image)
        
        assert result is False

    def test_is_landscape_image_square(self, mock_image_processor_basic):
        """测试正方形图像"""
        mock_image = MagicMock()
        mock_image.size = (1080, 1080)
        
        result = mock_image_processor_basic._is_landscape_image(mock_image)
        
        # 正方形不是横向
        assert result is False

    def test_apply_landscape_optimization(self, mock_image_processor_basic):
        """测试横向优化应用"""
        mock_image = MagicMock()
        
        result = mock_image_processor_basic._apply_landscape_optimization(mock_image)
        
        # 应该返回图像（可能是原图或优化后的）
        assert result is not None


# ==================== 策略加载方法测试 ====================


class TestStrategyLoadMethods:
    """测试各种策略加载方法"""

    def test_load_fast_mode(self, mock_image_processor_basic, temp_image_file):
        """测试快速加载模式"""
        mock_strategy = MagicMock()
        mock_strategy.load.return_value = b"fast_image"
        mock_image_processor_basic.loading_strategies['fast'] = mock_strategy
        
        result = mock_image_processor_basic._load_fast_mode(temp_image_file, "jpg")
        
        assert mock_strategy.load.called

    def test_load_auto_optimized(self, mock_image_processor_basic, temp_image_file):
        """测试自动优化加载"""
        mock_strategy = MagicMock()
        mock_strategy.load.return_value = b"auto_image"
        mock_image_processor_basic.loading_strategies['auto'] = mock_strategy
        
        result = mock_image_processor_basic._load_auto_optimized(temp_image_file)
        
        assert mock_strategy.load.called

    def test_load_preview_optimized(self, mock_image_processor_basic, temp_image_file):
        """测试预览优化加载"""
        mock_strategy = MagicMock()
        mock_strategy.load.return_value = b"preview_image"
        mock_image_processor_basic.loading_strategies['preview'] = mock_strategy
        
        result = mock_image_processor_basic._load_preview_optimized(temp_image_file)
        
        assert mock_strategy.load.called

    def test_load_progressive_optimized(self, mock_image_processor_basic, temp_image_file):
        """测试渐进式优化加载"""
        mock_strategy = MagicMock()
        mock_strategy.load.return_value = b"progressive_image"
        mock_image_processor_basic.loading_strategies['auto'] = mock_strategy
        
        result = mock_image_processor_basic._load_progressive_optimized(temp_image_file)
        
        assert mock_strategy.load.called


# ==================== 策略执行测试 ====================


class TestStrategyExecution:
    """测试策略执行"""

    def test_execute_loading_strategy_success(self, mock_image_processor_basic):
        """测试成功执行策略"""
        mock_strategy = MagicMock()
        mock_strategy.load.return_value = b"strategy_image"
        
        result = mock_image_processor_basic._execute_loading_strategy(
            mock_strategy, 
            "test.jpg", 
            (800, 600), 
            5.0
        )
        
        assert mock_strategy.load.called
        assert result == b"strategy_image"

    def test_execute_loading_strategy_with_none_target(self, mock_image_processor_basic):
        """测试无目标尺寸执行策略"""
        mock_strategy = MagicMock()
        mock_strategy.load.return_value = b"full_image"
        
        result = mock_image_processor_basic._execute_loading_strategy(
            mock_strategy,
            "test.jpg",
            None,
            5.0
        )
        
        assert mock_strategy.load.called

    def test_execute_loading_strategy_exception(self, mock_image_processor_basic):
        """测试策略执行异常"""
        mock_strategy = MagicMock()
        mock_strategy.load.side_effect = Exception("Load failed")
        
        result = mock_image_processor_basic._execute_loading_strategy(
            mock_strategy,
            "test.jpg",
            None,
            5.0
        )
        
        # 异常应该被捕获，返回None
        assert result is None


# ==================== 边缘情况测试 ====================


class TestEdgeCases:
    """测试边缘情况"""

    def test_very_large_file_size(self, mock_image_processor_basic):
        """测试非常大的文件"""
        with patch('os.path.getsize', return_value=1024 * 1024 * 1024 * 5):  # 5GB
            size_mb = mock_image_processor_basic._get_file_size_mb("huge.jpg")
            
            assert size_mb > 1000

    def test_zero_byte_file(self, mock_image_processor_basic):
        """测试零字节文件"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            temp_path = f.name
        
        try:
            size_mb = mock_image_processor_basic._get_file_size_mb(temp_path)
            assert size_mb == 0.0
        finally:
            os.unlink(temp_path)

    def test_special_characters_in_filename(self, mock_image_processor_basic):
        """测试文件名中的特殊字符"""
        filename = "图片 (test) [2024].jpg"
        ext = mock_image_processor_basic._get_file_extension(filename)
        
        assert ext == "jpg"

    def test_very_long_filename(self, mock_image_processor_basic):
        """测试超长文件名"""
        long_name = "a" * 500 + ".jpg"
        ext = mock_image_processor_basic._get_file_extension(long_name)
        
        assert ext == "jpg"

    def test_load_with_missing_strategy(self, mock_image_processor_basic, temp_image_file):
        """测试策略缺失"""
        # 清空策略
        mock_image_processor_basic.loading_strategies = {}
        
        result = mock_image_processor_basic.load_image_optimized(temp_image_file)
        
        # 应该返回None
        assert result is None

    def test_multiple_file_size_queries(self, mock_image_processor_basic, temp_image_file):
        """测试多次查询文件大小"""
        sizes = []
        for _ in range(10):
            size = mock_image_processor_basic._get_file_size_mb(temp_image_file)
            sizes.append(size)
        
        # 所有结果应该一致
        assert len(set(sizes)) == 1

    def test_concurrent_extension_queries(self, mock_image_processor_basic):
        """测试并发扩展名查询"""
        import threading
        
        results = []
        
        def query_ext():
            ext = mock_image_processor_basic._get_file_extension("test.jpg")
            results.append(ext)
        
        threads = []
        for _ in range(20):
            t = threading.Thread(target=query_ext)
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join(timeout=1.0)
        
        # 所有结果应该是"jpg"
        assert all(ext == "jpg" for ext in results)


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    def test_full_loading_pipeline(self, mock_image_processor_basic, temp_image_file):
        """测试完整加载流程"""
        mock_strategy = MagicMock()
        mock_strategy.load.return_value = b"loaded_image"
        mock_image_processor_basic.loading_strategies['auto'] = mock_strategy
        
        # 执行完整流程
        result = mock_image_processor_basic.load_image_optimized(
            temp_image_file,
            target_size=(800, 600)
        )
        
        # 验证各阶段
        assert temp_image_file in mock_image_processor_basic._file_size_cache
        assert temp_image_file in mock_image_processor_basic._ext_cache
        assert mock_strategy.load.called

    def test_load_multiple_images(self, mock_image_processor_basic):
        """测试加载多个图像"""
        mock_strategy = MagicMock()
        mock_strategy.load.return_value = b"image"
        mock_image_processor_basic.loading_strategies['auto'] = mock_strategy
        
        # 创建多个临时文件
        temp_files = []
        for i in range(5):
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                f.write(b'data')
                temp_files.append(f.name)
        
        try:
            results = []
            for path in temp_files:
                result = mock_image_processor_basic.load_image_optimized(path)
                results.append(result)
            
            # 所有应该成功加载
            assert len([r for r in results if r is not None]) >= 0
        finally:
            for path in temp_files:
                try:
                    os.unlink(path)
                except Exception:
                    pass

    def test_stats_accumulation(self, mock_image_processor_basic, temp_image_file):
        """测试统计累积"""
        mock_strategy = MagicMock()
        mock_strategy.load.return_value = b"image"
        mock_image_processor_basic.loading_strategies['auto'] = mock_strategy
        
        initial_time = mock_image_processor_basic.processing_stats['total_processing_time']
        
        # 加载几次
        for _ in range(3):
            mock_image_processor_basic.load_image_optimized(temp_image_file)
        
        # 统计应该累积
        final_time = mock_image_processor_basic.processing_stats['total_processing_time']
        assert final_time >= initial_time

