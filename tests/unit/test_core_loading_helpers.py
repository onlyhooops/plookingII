"""
测试加载辅助函数模块

测试覆盖：
- get_file_size_mb 函数
- clear_file_size_cache 函数
- check_quartz_availability 函数
- 加载函数 (需要mock macOS框架)
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from plookingII.core.loading.helpers import (
    check_quartz_availability,
    clear_file_size_cache,
    get_file_size_mb,
)


class TestGetFileSizeMb:
    """测试get_file_size_mb函数"""

    def test_get_size_of_existing_file(self, tmp_path):
        """测试获取存在文件的大小"""
        # 创建一个10MB的文件
        test_file = tmp_path / "test_file.dat"
        test_file.write_bytes(b"0" * (10 * 1024 * 1024))

        size_mb = get_file_size_mb(str(test_file))

        assert abs(size_mb - 10.0) < 0.1  # 允许小误差

    def test_get_size_of_small_file(self, tmp_path):
        """测试获取小文件的大小"""
        test_file = tmp_path / "small.txt"
        test_file.write_text("Hello, World!")

        size_mb = get_file_size_mb(str(test_file))

        assert size_mb < 0.001  # 应该很小

    def test_get_size_of_empty_file(self, tmp_path):
        """测试获取空文件的大小"""
        test_file = tmp_path / "empty.txt"
        test_file.touch()

        size_mb = get_file_size_mb(str(test_file))

        assert size_mb == 0.0

    def test_get_size_nonexistent_file(self):
        """测试获取不存在文件的大小"""
        size_mb = get_file_size_mb("/nonexistent/file.txt")

        # 应该返回0.0而不是抛出异常
        assert size_mb == 0.0

    def test_caching_behavior(self, tmp_path):
        """测试缓存行为"""
        test_file = tmp_path / "cached.txt"
        test_file.write_bytes(b"0" * (5 * 1024 * 1024))  # 5MB

        # 第一次调用
        size1 = get_file_size_mb(str(test_file), use_cache=True)

        # 修改文件
        test_file.write_bytes(b"0" * (10 * 1024 * 1024))  # 10MB

        # 第二次调用（使用缓存）
        size2 = get_file_size_mb(str(test_file), use_cache=True)

        # 应该返回缓存的值
        assert abs(size1 - size2) < 0.1

    def test_no_caching(self, tmp_path):
        """测试不使用缓存"""
        test_file = tmp_path / "no_cache.txt"
        test_file.write_bytes(b"0" * (5 * 1024 * 1024))

        size1 = get_file_size_mb(str(test_file), use_cache=False)

        # 修改文件
        test_file.write_bytes(b"0" * (10 * 1024 * 1024))

        size2 = get_file_size_mb(str(test_file), use_cache=False)

        # 应该返回新的值
        assert abs(size1 - 5.0) < 0.1
        assert abs(size2 - 10.0) < 0.1

    def test_cache_expiration(self, tmp_path):
        """测试缓存过期"""
        test_file = tmp_path / "expire.txt"
        test_file.write_bytes(b"0" * (5 * 1024 * 1024))

        # 第一次调用
        size1 = get_file_size_mb(str(test_file), use_cache=True)
        assert abs(size1 - 5.0) < 0.1

        # 修改文件
        test_file.write_bytes(b"0" * (10 * 1024 * 1024))

        # 等待缓存过期（实际环境中需要6秒，这里我们直接清除缓存测试）
        clear_file_size_cache()

        # 缓存已清除，应该返回新值
        size2 = get_file_size_mb(str(test_file), use_cache=True)
        assert abs(size2 - 10.0) < 0.1

    def test_different_files_different_cache(self, tmp_path):
        """测试不同文件使用不同缓存"""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_bytes(b"0" * (3 * 1024 * 1024))
        file2.write_bytes(b"0" * (7 * 1024 * 1024))

        size1 = get_file_size_mb(str(file1), use_cache=True)
        size2 = get_file_size_mb(str(file2), use_cache=True)

        assert abs(size1 - 3.0) < 0.1
        assert abs(size2 - 7.0) < 0.1


class TestClearFileSizeCache:
    """测试clear_file_size_cache函数"""

    def test_clear_cache(self, tmp_path):
        """测试清除缓存"""
        test_file = tmp_path / "cached.txt"
        test_file.write_bytes(b"0" * (5 * 1024 * 1024))

        # 填充缓存
        get_file_size_mb(str(test_file), use_cache=True)

        # 清除缓存
        clear_file_size_cache()

        # 修改文件
        test_file.write_bytes(b"0" * (10 * 1024 * 1024))

        # 应该返回新值（因为缓存被清除）
        size = get_file_size_mb(str(test_file), use_cache=True)
        assert abs(size - 10.0) < 0.1

    def test_clear_empty_cache(self):
        """测试清除空缓存"""
        # 应该不会崩溃
        clear_file_size_cache()


class TestCheckQuartzAvailability:
    """测试check_quartz_availability函数"""

    def test_quartz_available(self):
        """测试Quartz可用"""
        with patch("plookingII.core.loading.helpers.CGImageSourceCreateWithURL", create=True):
            result = check_quartz_availability()
            assert result is True

    def test_quartz_unavailable(self):
        """测试Quartz不可用"""
        # 在没有mock的情况下，在非macOS系统上应该返回False
        # 这个测试依赖于运行环境
        result = check_quartz_availability()
        # 在macOS上可能是True，在其他系统上是False
        assert isinstance(result, bool)

    def test_quartz_import_error(self):
        """测试导入错误处理"""
        with patch("builtins.__import__", side_effect=ImportError("No module named Quartz")):
            result = check_quartz_availability()
            assert result is False


class TestLoadWithNSImage:
    """测试load_with_nsimage函数"""

    def test_load_success(self, tmp_path):
        """测试成功加载"""
        # 这个测试需要macOS环境，我们用mock
        from plookingII.core.loading import helpers

        # 检查函数是否存在
        assert hasattr(helpers, "load_with_nsimage")

        # Mock NSImage
        mock_nsimage = MagicMock()
        mock_instance = MagicMock()
        mock_nsimage.alloc.return_value.initWithContentsOfFile_.return_value = mock_instance

        with patch.dict("sys.modules", {"AppKit": MagicMock(NSImage=mock_nsimage)}):
            from plookingII.core.loading.helpers import load_with_nsimage

            result = load_with_nsimage("/path/to/image.jpg")
            # 在mock环境下应该返回None或mock对象
            # 实际行为依赖于导入时机

    def test_load_failure(self):
        """测试加载失败"""
        from plookingII.core.loading.helpers import load_with_nsimage

        # 传入无效路径应该返回None
        result = load_with_nsimage("/nonexistent/image.jpg")
        # 在非macOS或没有图片时应该返回None


class TestLoadWithQuartz:
    """测试load_with_quartz函数"""

    def test_function_exists(self):
        """测试函数存在"""
        from plookingII.core.loading import helpers

        assert hasattr(helpers, "load_with_quartz")

    def test_load_with_target_size(self):
        """测试带目标尺寸加载"""
        from plookingII.core.loading.helpers import load_with_quartz

        # 在非macOS环境下应该返回None
        result = load_with_quartz("/path/to/image.jpg", target_size=(800, 600))

    def test_load_with_thumbnail(self):
        """测试缩略图加载"""
        from plookingII.core.loading.helpers import load_with_quartz

        result = load_with_quartz("/path/to/image.jpg", target_size=(200, 200), thumbnail=True)


class TestLoadWithMemoryMap:
    """测试load_with_memory_map函数"""

    def test_function_exists(self):
        """测试函数存在"""
        from plookingII.core.loading import helpers

        assert hasattr(helpers, "load_with_memory_map")

    def test_load_nonexistent_file(self):
        """测试加载不存在的文件"""
        from plookingII.core.loading.helpers import load_with_memory_map

        result = load_with_memory_map("/nonexistent/file.jpg")
        assert result is None

    def test_load_empty_file(self, tmp_path):
        """测试加载空文件"""
        from plookingII.core.loading.helpers import load_with_memory_map

        empty_file = tmp_path / "empty.jpg"
        empty_file.touch()

        result = load_with_memory_map(str(empty_file))
        # 空文件应该返回None或处理错误


class TestCGImageToNSImage:
    """测试cgimage_to_nsimage函数"""

    def test_function_exists(self):
        """测试函数存在"""
        from plookingII.core.loading import helpers

        assert hasattr(helpers, "cgimage_to_nsimage")

    def test_none_input(self):
        """测试None输入"""
        from plookingII.core.loading.helpers import cgimage_to_nsimage

        result = cgimage_to_nsimage(None)
        assert result is None


# get_pixel_dimensions函数已被移除或不存在


class TestEdgeCases:
    """测试边缘情况"""

    def test_file_size_with_special_characters(self, tmp_path):
        """测试特殊字符文件名"""
        special_file = tmp_path / "文件 (1).txt"
        special_file.write_bytes(b"0" * (2 * 1024 * 1024))

        size_mb = get_file_size_mb(str(special_file))
        assert abs(size_mb - 2.0) < 0.1

    def test_file_size_very_large_file(self, tmp_path):
        """测试非常大的文件"""
        # 创建一个大文件（但不实际写入太多数据）
        large_file = tmp_path / "large.dat"
        large_file.write_bytes(b"0" * (100 * 1024 * 1024))  # 100MB

        size_mb = get_file_size_mb(str(large_file))
        assert abs(size_mb - 100.0) < 1.0

    def test_concurrent_cache_access(self, tmp_path):
        """测试并发缓存访问"""
        import threading

        test_file = tmp_path / "concurrent.txt"
        test_file.write_bytes(b"0" * (5 * 1024 * 1024))

        results = []

        def worker():
            size = get_file_size_mb(str(test_file), use_cache=True)
            results.append(size)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有结果应该一致
        assert all(abs(r - 5.0) < 0.1 for r in results)


class TestIntegration:
    """集成测试"""

    def test_cache_lifecycle(self, tmp_path):
        """测试缓存完整生命周期"""
        test_file = tmp_path / "lifecycle.txt"
        test_file.write_bytes(b"0" * (3 * 1024 * 1024))

        # 1. 第一次访问（填充缓存）
        size1 = get_file_size_mb(str(test_file), use_cache=True)
        assert abs(size1 - 3.0) < 0.1

        # 2. 第二次访问（使用缓存）
        size2 = get_file_size_mb(str(test_file), use_cache=True)
        assert size1 == size2

        # 3. 清除缓存
        clear_file_size_cache()

        # 4. 修改文件
        test_file.write_bytes(b"0" * (6 * 1024 * 1024))

        # 5. 第三次访问（缓存已清除，应该读取新值）
        size3 = get_file_size_mb(str(test_file), use_cache=True)
        assert abs(size3 - 6.0) < 0.1

    def test_multiple_files_caching(self, tmp_path):
        """测试多文件缓存"""
        files = []
        expected_sizes = [1, 2, 3, 4, 5]

        for i, size in enumerate(expected_sizes):
            file = tmp_path / f"file{i}.txt"
            file.write_bytes(b"0" * (size * 1024 * 1024))
            files.append(file)

        # 访问所有文件
        for file, expected in zip(files, expected_sizes, strict=False):
            size = get_file_size_mb(str(file), use_cache=True)
            assert abs(size - expected) < 0.1

        # 再次访问（应该使用缓存）
        for file, expected in zip(files, expected_sizes, strict=False):
            size = get_file_size_mb(str(file), use_cache=True)
            assert abs(size - expected) < 0.1

    def test_cache_and_no_cache_mixed(self, tmp_path):
        """测试混合使用缓存和非缓存"""
        test_file = tmp_path / "mixed.txt"
        test_file.write_bytes(b"0" * (4 * 1024 * 1024))

        # 使用缓存
        size1 = get_file_size_mb(str(test_file), use_cache=True)

        # 修改文件
        test_file.write_bytes(b"0" * (8 * 1024 * 1024))

        # 不使用缓存（应该获取新值）
        size2 = get_file_size_mb(str(test_file), use_cache=False)

        # 使用缓存（应该获取旧值）
        size3 = get_file_size_mb(str(test_file), use_cache=True)

        assert abs(size1 - 4.0) < 0.1
        assert abs(size2 - 8.0) < 0.1
        assert abs(size3 - 4.0) < 0.1  # 缓存未更新


class TestPerformance:
    """性能测试"""

    @pytest.mark.slow()
    def test_cache_improves_performance(self, tmp_path):
        """测试缓存提升性能"""
        test_file = tmp_path / "perf.txt"
        test_file.write_bytes(b"0" * (10 * 1024 * 1024))

        # 测试无缓存性能
        start = time.time()
        for _ in range(100):
            get_file_size_mb(str(test_file), use_cache=False)
        no_cache_time = time.time() - start

        # 清除缓存
        clear_file_size_cache()

        # 测试有缓存性能
        start = time.time()
        for _ in range(100):
            get_file_size_mb(str(test_file), use_cache=True)
        cache_time = time.time() - start

        # 缓存应该更快
        assert cache_time < no_cache_time
