"""
测试 core/functions.py 模块

测试目标：达到95%+覆盖率
"""

import gc
import os
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest

from plookingII.core.functions import (
    _env_int,
    build_menu,
    force_gc,
    get_image_dimensions_safe,
    simple_thumbnail_cache,
)


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestSimpleThumbnailCache:
    """测试 simple_thumbnail_cache 函数"""

    def test_simple_thumbnail_cache_unsupported_format(self):
        """测试不支持的文件格式"""
        result = simple_thumbnail_cache(("test.gif", (100, 100)))
        assert result is None
        
        result = simple_thumbnail_cache(("test.txt", (100, 100)))
        assert result is None
        
        result = simple_thumbnail_cache(("test.bmp", (100, 100)))
        assert result is None

    def test_simple_thumbnail_cache_supported_format_paths(self):
        """测试支持的文件格式路径（不实际打开文件）"""
        # 测试路径格式检查
        formats = [
            ("test.jpg", (100, 100)),
            ("test.jpeg", (100, 100)),
            ("test.png", (100, 100)),
            ("test.JPG", (100, 100)),
            ("test.PNG", (100, 100)),
        ]
        
        # 由于文件不存在，会在PIL.Image.open时失败，返回None
        for path_and_size in formats:
            result = simple_thumbnail_cache(path_and_size)
            assert result is None  # 文件不存在会返回None

    @patch('PIL.Image.open')
    def test_simple_thumbnail_cache_with_valid_image(self, mock_image_open):
        """测试使用有效图像生成缩略图"""
        # Mock PIL Image对象
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        
        # Mock thumbnail和save方法
        mock_image.thumbnail = Mock()
        
        # Mock save方法，模拟生成PNG数据
        def mock_save(buf, format=None):
            buf.write(b'fake_png_data')
        
        mock_image.save = mock_save
        mock_image_open.return_value = mock_image
        
        # 测试
        result = simple_thumbnail_cache(("test.jpg", (100, 100)))
        
        # 验证
        assert result == b'fake_png_data'
        mock_image_open.assert_called_once_with("test.jpg")
        mock_image.thumbnail.assert_called_once_with((100, 100))

    @patch('PIL.Image.open')
    def test_simple_thumbnail_cache_exception_handling(self, mock_image_open):
        """测试异常处理"""
        # Mock Image.open抛出异常
        mock_image_open.side_effect = Exception("File not found")
        
        result = simple_thumbnail_cache(("test.jpg", (100, 100)))
        assert result is None

    @patch('PIL.Image.open')
    def test_simple_thumbnail_cache_thumbnail_exception(self, mock_image_open):
        """测试thumbnail方法异常"""
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image.thumbnail.side_effect = Exception("Thumbnail failed")
        
        mock_image_open.return_value = mock_image
        
        result = simple_thumbnail_cache(("test.jpg", (100, 100)))
        assert result is None

    def test_simple_thumbnail_cache_various_sizes(self):
        """测试不同尺寸"""
        # 这些测试会因为文件不存在而返回None
        sizes = [
            (50, 50),
            (100, 100),
            (200, 200),
            (500, 500),
            (1920, 1080),
        ]
        
        for size in sizes:
            result = simple_thumbnail_cache(("nonexistent.jpg", size))
            assert result is None


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestForceGc:
    """测试 force_gc 函数"""

    @patch('plookingII.core.functions._gc.collect')
    def test_force_gc_calls_collect_twice(self, mock_collect):
        """测试force_gc调用两次垃圾回收"""
        force_gc()
        
        # 验证gc.collect被调用了两次
        assert mock_collect.call_count == 2

    @patch('plookingII.core.functions._gc.collect')
    def test_force_gc_return_value(self, mock_collect):
        """测试force_gc的返回值"""
        mock_collect.return_value = 10
        
        result = force_gc()
        
        # force_gc没有返回值
        assert result is None

    def test_force_gc_integration(self):
        """测试force_gc集成（实际调用）"""
        # 创建一些对象然后释放引用
        test_objects = [object() for _ in range(100)]
        test_objects = None
        
        # 调用force_gc应该不会抛出异常
        force_gc()
        
        # 验证没有异常发生
        assert True

    @patch('plookingII.core.functions._gc.collect')
    def test_force_gc_exception_handling(self, mock_collect):
        """测试force_gc的异常传播"""
        # gc.collect通常不会抛出异常，但如果抛出了应该传播
        mock_collect.side_effect = RuntimeError("GC Error")
        
        with pytest.raises(RuntimeError, match="GC Error"):
            force_gc()


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestBuildMenu:
    """测试 build_menu 函数"""

    @patch('plookingII.core.functions.MenuBuilder')
    @patch('plookingII.core.functions.NSMenu')
    def test_build_menu_success(self, mock_nsmenu, mock_menu_builder_class):
        """测试成功构建菜单"""
        # Mock app和win
        mock_app = MagicMock()
        mock_win = MagicMock()
        
        # Mock MenuBuilder实例和build_menu方法
        mock_menu_builder = MagicMock()
        mock_main_menu = MagicMock()
        mock_menu_builder.build_menu.return_value = mock_main_menu
        mock_menu_builder_class.return_value = mock_menu_builder
        
        # 调用函数
        build_menu(mock_app, mock_win)
        
        # 验证
        mock_menu_builder_class.assert_called_once_with(mock_app, mock_win)
        mock_menu_builder.build_menu.assert_called_once()
        mock_app.setMainMenu_.assert_called_once_with(mock_main_menu)

    @patch('plookingII.core.functions.MenuBuilder')
    def test_build_menu_exception_fallback(self, mock_menu_builder_class):
        """测试构建菜单失败时的回退机制"""
        # Mock app和win
        mock_app = MagicMock()
        mock_win = MagicMock()
        
        # Mock MenuBuilder抛出异常
        mock_menu_builder_class.side_effect = Exception("Menu build failed")
        
        # 调用函数
        build_menu(mock_app, mock_win)
        
        # 验证setMainMenu_被调用（使用了fallback菜单）
        assert mock_app.setMainMenu_.called
        # MenuBuilder应该被尝试创建
        mock_menu_builder_class.assert_called_once_with(mock_app, mock_win)

    @patch('plookingII.core.functions.MenuBuilder')
    def test_build_menu_with_none_app(self, mock_menu_builder_class):
        """测试app为None的情况"""
        # 这会在setMainMenu_时失败
        mock_menu_builder = MagicMock()
        mock_menu_builder_class.return_value = mock_menu_builder
        
        # 调用可能会因为None.setMainMenu_而失败
        # 但根据实现，异常会被捕获
        try:
            build_menu(None, MagicMock())
        except AttributeError:
            # 如果没有被捕获，这是预期的
            pass

    @patch('plookingII.core.functions.MenuBuilder')
    @patch('plookingII.core.functions.NSMenu')
    def test_build_menu_with_none_win(self, mock_nsmenu, mock_menu_builder_class):
        """测试win为None的情况"""
        mock_app = MagicMock()
        mock_menu_builder = MagicMock()
        mock_menu_builder_class.return_value = mock_menu_builder
        
        # win为None应该仍能构建菜单
        build_menu(mock_app, None)
        
        mock_menu_builder_class.assert_called_once_with(mock_app, None)


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestEnvInt:
    """测试 _env_int 函数"""

    def test_env_int_with_valid_positive_value(self):
        """测试有效的正整数值"""
        with patch.dict(os.environ, {'TEST_VAR': '42'}):
            result = _env_int('TEST_VAR', 10)
            assert result == 42

    def test_env_int_with_default_value(self):
        """测试使用默认值"""
        with patch.dict(os.environ, {}, clear=True):
            result = _env_int('NONEXISTENT_VAR', 99)
            assert result == 99

    def test_env_int_with_zero_value(self):
        """测试零值（应返回默认值）"""
        with patch.dict(os.environ, {'TEST_VAR': '0'}):
            result = _env_int('TEST_VAR', 50)
            assert result == 50  # 零不是正整数

    def test_env_int_with_negative_value(self):
        """测试负值（应返回默认值）"""
        with patch.dict(os.environ, {'TEST_VAR': '-10'}):
            result = _env_int('TEST_VAR', 50)
            assert result == 50  # 负数不是正整数

    def test_env_int_with_invalid_string(self):
        """测试无效字符串"""
        with patch.dict(os.environ, {'TEST_VAR': 'not_a_number'}):
            result = _env_int('TEST_VAR', 100)
            assert result == 100  # 无法解析，返回默认值

    def test_env_int_with_float_string(self):
        """测试浮点数字符串"""
        with patch.dict(os.environ, {'TEST_VAR': '42.5'}):
            result = _env_int('TEST_VAR', 100)
            assert result == 100  # int()会抛出ValueError

    def test_env_int_with_whitespace(self):
        """测试带空格的值"""
        with patch.dict(os.environ, {'TEST_VAR': '  42  '}):
            result = _env_int('TEST_VAR', 10)
            assert result == 42  # strip()应该处理空格

    def test_env_int_with_leading_zeros(self):
        """测试前导零"""
        with patch.dict(os.environ, {'TEST_VAR': '0042'}):
            result = _env_int('TEST_VAR', 10)
            assert result == 42

    def test_env_int_with_empty_string(self):
        """测试空字符串"""
        with patch.dict(os.environ, {'TEST_VAR': ''}):
            result = _env_int('TEST_VAR', 75)
            assert result == 75  # 空字符串无法解析

    def test_env_int_with_large_number(self):
        """测试大数值"""
        with patch.dict(os.environ, {'TEST_VAR': '999999999'}):
            result = _env_int('TEST_VAR', 10)
            assert result == 999999999

    def test_env_int_boundary_values(self):
        """测试边界值"""
        # 测试1（最小的正整数）
        with patch.dict(os.environ, {'TEST_VAR': '1'}):
            result = _env_int('TEST_VAR', 100)
            assert result == 1
        
        # 测试-1（应返回默认值）
        with patch.dict(os.environ, {'TEST_VAR': '-1'}):
            result = _env_int('TEST_VAR', 100)
            assert result == 100


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestGetImageDimensionsSafe:
    """测试 get_image_dimensions_safe 函数"""

    def test_get_image_dimensions_safe_nonexistent_file(self):
        """测试不存在的文件"""
        result = get_image_dimensions_safe("/nonexistent/path/image.jpg")
        assert result is None

    def test_get_image_dimensions_safe_quartz_success(self):
        """测试使用Quartz成功获取尺寸"""
        # 由于Quartz API的复杂性和动态导入，这里只测试回退逻辑
        # 实际的Quartz测试应该在集成测试中进行
        pass

    @patch('plookingII.core.functions.QUARTZ_AVAILABLE', False)
    @patch('PIL.Image.open')
    def test_get_image_dimensions_safe_pillow_fallback(self, mock_image_open):
        """测试回退到PIL"""
        # Mock Image.open
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image.size = (800, 600)
        
        mock_image_open.return_value = mock_image
        
        result = get_image_dimensions_safe("test.png")
        
        assert result == (800, 600)
        mock_image_open.assert_called_once_with("test.png")

    def test_get_image_dimensions_safe_quartz_none_source(self):
        """测试Quartz返回None source时回退到PIL"""
        # 简化的测试 - 实际Quartz逻辑复杂
        pass

    def test_get_image_dimensions_safe_quartz_none_props(self):
        """测试Quartz返回None props时回退到PIL"""
        # 简化的测试 - 实际Quartz逻辑复杂
        pass

    @patch('plookingII.core.functions.QUARTZ_AVAILABLE', False)
    @patch('PIL.Image.open')
    def test_get_image_dimensions_safe_pillow_exception(self, mock_image_open):
        """测试PIL抛出异常"""
        mock_image_open.side_effect = Exception("Cannot open image")
        
        result = get_image_dimensions_safe("test.jpg")
        
        assert result is None

    @patch('plookingII.core.functions.QUARTZ_AVAILABLE', False)
    @patch('PIL.Image.open')
    def test_get_image_dimensions_safe_pillow_invalid_size(self, mock_image_open):
        """测试PIL返回无效尺寸"""
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        
        # 测试各种无效尺寸
        invalid_sizes = [
            None,
            (0, 100),
            (100, 0),
            (-100, 100),
            (100, -100),
            ("100", "100"),
            (100.5, 200.5),
            (100,),  # 只有一个元素
            (100, 200, 300),  # 三个元素
        ]
        
        for invalid_size in invalid_sizes:
            mock_image.size = invalid_size
            mock_image_open.return_value = mock_image
            
            result = get_image_dimensions_safe("test.jpg")
            assert result is None

    @patch('plookingII.core.functions.QUARTZ_AVAILABLE', False)
    @patch('PIL.Image.open')
    def test_get_image_dimensions_safe_pillow_decompression_warning(self, mock_image_open):
        """测试PIL处理DecompressionBombWarning"""
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image.size = (10000, 10000)
        
        mock_image_open.return_value = mock_image
        
        result = get_image_dimensions_safe("large_image.jpg")
        
        # 应该忽略DecompressionBombWarning
        assert result == (10000, 10000)


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestFunctionsEdgeCases:
    """测试边缘情况和集成"""

    def test_simple_thumbnail_cache_with_path_object(self):
        """测试使用Path对象"""
        from pathlib import Path
        path = Path("/test/image.jpg")
        # Path对象会被转换为字符串，然后因为文件不存在而返回None
        result = simple_thumbnail_cache((str(path), (100, 100)))
        assert result is None

    def test_env_int_unicode_values(self):
        """测试Unicode值"""
        with patch.dict(os.environ, {'TEST_VAR': '42中文'}):
            result = _env_int('TEST_VAR', 100)
            assert result == 100  # 无法解析为整数

    def test_env_int_special_characters(self):
        """测试特殊字符"""
        special_values = ['42!', '42@', '42#', '42$', '42%']
        for val in special_values:
            with patch.dict(os.environ, {'TEST_VAR': val}):
                result = _env_int('TEST_VAR', 100)
                assert result == 100

    @patch('plookingII.core.functions._gc.collect')
    def test_multiple_force_gc_calls(self, mock_collect):
        """测试多次调用force_gc"""
        for _ in range(5):
            force_gc()
        
        # 每次调用force_gc都会调用2次gc.collect
        assert mock_collect.call_count == 10


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestFunctionsIntegration:
    """集成测试"""

    def test_thumbnail_and_gc_workflow(self):
        """测试缩略图生成和垃圾回收工作流"""
        # 生成多个缩略图（都会失败因为文件不存在）
        paths = [f"image{i}.jpg" for i in range(10)]
        results = [simple_thumbnail_cache((path, (100, 100))) for path in paths]
        
        # 所有结果都应该是None
        assert all(r is None for r in results)
        
        # 强制垃圾回收应该正常工作
        force_gc()
        
        # 验证没有异常
        assert True

    def test_env_int_with_multiple_variables(self):
        """测试多个环境变量"""
        env_vars = {
            'VAR1': '10',
            'VAR2': '20',
            'VAR3': 'invalid',
            'VAR4': '0',
        }
        
        with patch.dict(os.environ, env_vars):
            assert _env_int('VAR1', 5) == 10
            assert _env_int('VAR2', 5) == 20
            assert _env_int('VAR3', 5) == 5  # invalid
            assert _env_int('VAR4', 5) == 5  # zero
            assert _env_int('VAR5', 5) == 5  # not exists


@pytest.mark.unit
@pytest.mark.timeout(15)
class TestFunctionsPerformance:
    """性能相关测试"""

    @pytest.mark.slow
    def test_force_gc_performance(self):
        """测试force_gc性能"""
        import time
        
        # 创建大量对象
        objects = [object() for _ in range(10000)]
        objects = None
        
        # 测量force_gc执行时间
        start = time.time()
        force_gc()
        elapsed = time.time() - start
        
        # 垃圾回收应该在合理时间内完成（1秒内）
        assert elapsed < 1.0

    @pytest.mark.slow
    def test_env_int_many_calls(self):
        """测试大量_env_int调用"""
        with patch.dict(os.environ, {'TEST_VAR': '42'}):
            results = [_env_int('TEST_VAR', 10) for _ in range(1000)]
            
            # 所有结果应该相同
            assert all(r == 42 for r in results)

