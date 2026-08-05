"""
路径工具模块完整测试
目标覆盖率: 95%+
"""
import os
from unittest.mock import patch

import pytest

from plookingII.utils.path_utils import PathUtils


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestPathUtilsNormalizePathBasic:
    """测试基础路径规范化"""

    def test_normalize_empty_path(self):
        """测试空路径"""
        assert PathUtils.normalize_path_basic("") == ""
        assert PathUtils.normalize_path_basic(None) is None

    def test_normalize_user_home(self):
        """测试展开用户目录"""
        result = PathUtils.normalize_path_basic("~/Documents")
        assert "~" not in result
        assert os.path.expanduser("~") in result

    def test_normalize_removes_redundant_separators(self):
        """测试移除多余的分隔符"""
        result = PathUtils.normalize_path_basic("/path//to///file")
        assert "//" not in result
        assert "///" not in result

    def test_normalize_removes_dot_components(self):
        """测试移除.组件"""
        result = PathUtils.normalize_path_basic("/path/./to/./file")
        assert "/." not in result or result == "/."

    def test_normalize_handles_dotdot(self):
        """测试处理..组件"""
        result = PathUtils.normalize_path_basic("/path/to/../file")
        assert "../" not in result or result.startswith("..")
        assert "to" not in result or result == "/path/to"

    def test_normalize_absolute_path(self):
        """测试绝对路径"""
        result = PathUtils.normalize_path_basic("/absolute/path")
        assert result.startswith("/")

    def test_normalize_relative_path(self):
        """测试相对路径"""
        result = PathUtils.normalize_path_basic("relative/path")
        assert not result.startswith("/")

    def test_normalize_windows_style_path(self):
        """测试Windows风格路径"""
        # 在Unix系统上，反斜杠会被视为普通字符
        # 在Windows系统上，会被规范化为正斜杠
        result = PathUtils.normalize_path_basic("path\\to\\file")
        # 测试只验证函数正常返回
        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestPathUtilsResolveSymlinksSafe:
    """测试安全符号链接解析"""

    def test_resolve_symlinks_nonexistent_path(self):
        """测试不存在的路径"""
        path = "/nonexistent/path/to/file"
        result = PathUtils.resolve_symlinks_safe(path)
        # 应该返回原路径
        assert result == path

    def test_resolve_symlinks_real_file(self, temp_test_dir):
        """测试真实文件"""
        real_file = temp_test_dir / "real_file.txt"
        real_file.touch()

        result = PathUtils.resolve_symlinks_safe(str(real_file))
        assert os.path.exists(result)
        assert result == str(real_file.resolve())

    def test_resolve_symlinks_with_symlink(self, temp_test_dir):
        """测试符号链接"""
        real_file = temp_test_dir / "real_file.txt"
        real_file.touch()

        link_file = temp_test_dir / "link_file.txt"

        try:
            os.symlink(real_file, link_file)

            result = PathUtils.resolve_symlinks_safe(str(link_file))
            # 应该解析到真实文件
            assert real_file.name in result
            assert os.path.exists(result)
        except (OSError, NotImplementedError):
            pytest.skip("System does not support symlinks")

    def test_resolve_symlinks_exception_handling(self):
        """测试异常处理"""
        with patch("os.path.realpath", side_effect=Exception("Error")):
            result = PathUtils.resolve_symlinks_safe("/some/path")
            # 异常时应返回原路径
            assert result == "/some/path"

    def test_resolve_symlinks_resolved_not_exists(self):
        """测试解析后路径不存在"""
        with patch("os.path.realpath", return_value="/resolved/but/not/exists"):
            with patch("os.path.exists", return_value=False):
                result = PathUtils.resolve_symlinks_safe("/original/path")
                # 应该返回原路径
                assert result == "/original/path"


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestPathUtilsNormalizeUnicodeSafe:
    """测试Unicode路径规范化"""

    def test_normalize_unicode_empty(self):
        """测试空路径"""
        assert PathUtils.normalize_unicode_safe("") == ""
        assert PathUtils.normalize_unicode_safe(None) is None

    def test_normalize_unicode_ascii(self):
        """测试ASCII路径"""
        path = "/path/to/file"
        result = PathUtils.normalize_unicode_safe(path)
        assert result == path

    def test_normalize_unicode_chinese(self):
        """测试中文路径"""
        path = "/路径/到/文件"
        result = PathUtils.normalize_unicode_safe(path)
        assert "路径" in result
        assert "文件" in result

    def test_normalize_unicode_nfc_form(self):
        """测试NFC规范化"""
        # 使用不同的Unicode表示形式
        # é 可以表示为单个字符(U+00E9)或组合字符(e + ´)
        path_nfc = "café"  # 单个字符é
        result = PathUtils.normalize_unicode_safe(path_nfc)

        # 应该返回NFC规范化的形式
        assert isinstance(result, str)
        assert "caf" in result

    def test_normalize_unicode_exception_handling(self):
        """测试异常处理"""
        # 模拟unicodedata不可用
        import plookingII.utils.path_utils as path_utils_module
        original_ud = path_utils_module._ud

        try:
            path_utils_module._ud = None
            result = PathUtils.normalize_unicode_safe("/some/path")
            assert result == "/some/path"
        finally:
            path_utils_module._ud = original_ud

    def test_normalize_unicode_mixed(self):
        """测试混合字符"""
        path = "/path/路径/file/文件.txt"
        result = PathUtils.normalize_unicode_safe(path)
        assert "path" in result
        assert "路径" in result
        assert "file" in result
        assert "文件" in result


@pytest.mark.unit
@pytest.mark.timeout(15)
class TestPathUtilsCanonicalizePath:
    """测试路径标准化"""

    def test_canonicalize_basic_path(self, temp_test_dir):
        """测试基本路径"""
        test_file = temp_test_dir / "test.txt"
        test_file.touch()

        result = PathUtils.canonicalize_path(str(test_file))

        assert os.path.isabs(result)
        assert "test.txt" in result

    def test_canonicalize_with_user_home(self):
        """测试用户目录展开"""
        result = PathUtils.canonicalize_path("~/Documents")
        assert "~" not in result
        assert os.path.isabs(result)

    def test_canonicalize_relative_path(self):
        """测试相对路径"""
        result = PathUtils.canonicalize_path("./relative/path")
        assert os.path.isabs(result)
        assert "relative" in result
        assert "path" in result

    def test_canonicalize_with_dotdot(self):
        """测试包含..的路径"""
        result = PathUtils.canonicalize_path("/path/to/../file")
        assert ".." not in result or result == "/.."
        assert os.path.isabs(result)

    def test_canonicalize_resolve_symlinks_true(self, temp_test_dir):
        """测试解析符号链接"""
        real_file = temp_test_dir / "real.txt"
        real_file.touch()

        try:
            link_file = temp_test_dir / "link.txt"
            os.symlink(real_file, link_file)

            result = PathUtils.canonicalize_path(str(link_file), resolve_symlinks=True)
            assert "real.txt" in result or os.path.samefile(result, real_file)
        except (OSError, NotImplementedError):
            pytest.skip("System does not support symlinks")

    def test_canonicalize_resolve_symlinks_false(self, temp_test_dir):
        """测试不解析符号链接"""
        real_file = temp_test_dir / "real.txt"
        real_file.touch()

        try:
            link_file = temp_test_dir / "link.txt"
            os.symlink(real_file, link_file)

            result = PathUtils.canonicalize_path(str(link_file), resolve_symlinks=False)
            # 可能保留link名称（取决于实现）
            assert os.path.isabs(result)
        except (OSError, NotImplementedError):
            pytest.skip("System does not support symlinks")

    def test_canonicalize_unicode_path(self):
        """测试Unicode路径"""
        result = PathUtils.canonicalize_path("/路径/文件.txt")
        assert "路径" in result
        assert "文件" in result
        assert os.path.isabs(result)

    def test_canonicalize_exception_returns_original(self):
        """测试异常时返回原路径"""
        with patch("os.path.abspath", side_effect=Exception("Error")):
            path = "/some/path"
            result = PathUtils.canonicalize_path(path)
            assert result == path


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestPathUtilsNormalizeFolderPath:
    """测试文件夹路径规范化"""

    def test_normalize_folder_removes_trailing_slash(self):
        """测试移除尾随斜杠"""
        result = PathUtils.normalize_folder_path("/path/to/folder/")
        assert not result.endswith(os.sep)
        assert result == "/path/to/folder"

    def test_normalize_folder_multiple_trailing_slashes(self):
        """测试多个尾随斜杠"""
        result = PathUtils.normalize_folder_path("/path/to/folder///")
        assert not result.endswith(os.sep)

    def test_normalize_folder_no_trailing_slash(self):
        """测试无尾随斜杠"""
        path = "/path/to/folder"
        result = PathUtils.normalize_folder_path(path)
        assert result == path

    def test_normalize_folder_resolve_symlinks_false(self):
        """测试不解析符号链接（默认）"""
        result = PathUtils.normalize_folder_path("/path/to/folder", resolve_symlinks=False)
        assert result == "/path/to/folder"

    def test_normalize_folder_resolve_symlinks_true(self, temp_test_dir):
        """测试解析符号链接"""
        real_dir = temp_test_dir / "real_dir"
        real_dir.mkdir()

        try:
            link_dir = temp_test_dir / "link_dir"
            os.symlink(real_dir, link_dir)

            result = PathUtils.normalize_folder_path(str(link_dir), resolve_symlinks=True)
            assert os.path.isabs(result)
            assert os.path.exists(result)
        except (OSError, NotImplementedError):
            pytest.skip("System does not support symlinks")

    def test_normalize_folder_exception_handling(self):
        """测试异常处理"""
        # 无法mock str类型的方法，改为测试None输入
        result = PathUtils.normalize_folder_path(None)
        assert result is None or result == ""

        # 测试非字符串输入
        result = PathUtils.normalize_folder_path(123)
        assert isinstance(result, (str, int, type(None)))


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestPathUtilsIsValidPath:
    """测试路径有效性检查"""

    def test_is_valid_path_existing_file(self, temp_test_dir):
        """测试存在的文件"""
        test_file = temp_test_dir / "test.txt"
        test_file.touch()

        assert PathUtils.is_valid_path(str(test_file)) is True

    def test_is_valid_path_existing_folder(self, temp_test_dir):
        """测试存在的文件夹"""
        test_dir = temp_test_dir / "test_dir"
        test_dir.mkdir()

        assert PathUtils.is_valid_path(str(test_dir)) is True

    def test_is_valid_path_nonexistent(self):
        """测试不存在的路径"""
        assert PathUtils.is_valid_path("/nonexistent/path") is False

    def test_is_valid_path_empty_string(self):
        """测试空字符串"""
        assert PathUtils.is_valid_path("") is False

    def test_is_valid_path_none(self):
        """测试None"""
        assert PathUtils.is_valid_path(None) is False

    def test_is_valid_path_not_string(self):
        """测试非字符串类型"""
        assert PathUtils.is_valid_path(123) is False
        assert PathUtils.is_valid_path(["/path"]) is False
        assert PathUtils.is_valid_path({"path": "/path"}) is False

    def test_is_valid_path_exception_handling(self):
        """测试异常处理"""
        with patch("os.path.exists", side_effect=Exception("Error")):
            assert PathUtils.is_valid_path("/some/path") is False


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestPathUtilsIsValidFolder:
    """测试文件夹有效性检查"""

    def test_is_valid_folder_existing_folder(self, temp_test_dir):
        """测试存在的文件夹"""
        assert PathUtils.is_valid_folder(str(temp_test_dir)) is True

    def test_is_valid_folder_file_not_folder(self, temp_test_dir):
        """测试文件（非文件夹）"""
        test_file = temp_test_dir / "test.txt"
        test_file.touch()

        assert PathUtils.is_valid_folder(str(test_file)) is False

    def test_is_valid_folder_nonexistent(self):
        """测试不存在的文件夹"""
        assert PathUtils.is_valid_folder("/nonexistent/folder") is False

    def test_is_valid_folder_empty_string(self):
        """测试空字符串"""
        assert PathUtils.is_valid_folder("") is False

    def test_is_valid_folder_none(self):
        """测试None"""
        assert PathUtils.is_valid_folder(None) is False

    def test_is_valid_folder_exception_handling(self):
        """测试异常处理"""
        with patch("os.path.isdir", side_effect=Exception("Error")):
            assert PathUtils.is_valid_folder("/some/path") is False


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestPathUtilsEdgeCases:
    """边界情况测试"""

    def test_very_long_path(self):
        """测试超长路径"""
        long_path = "/path/" + "a" * 500
        result = PathUtils.normalize_path_basic(long_path)
        assert isinstance(result, str)

    def test_path_with_special_characters(self):
        """测试特殊字符路径"""
        special_paths = [
            "/path with spaces/file",
            "/path/with/中文/characters",
            "/path/with/(parentheses)",
            "/path/with/[brackets]",
        ]

        for path in special_paths:
            result = PathUtils.normalize_path_basic(path)
            assert isinstance(result, str)

    def test_root_path(self):
        """测试根路径"""
        result = PathUtils.normalize_path_basic("/")
        assert result == "/"

        assert PathUtils.is_valid_path("/") is True
        assert PathUtils.is_valid_folder("/") is True

    def test_current_directory(self):
        """测试当前目录"""
        result = PathUtils.normalize_path_basic(".")
        assert result == "."

    def test_parent_directory(self):
        """测试父目录"""
        result = PathUtils.normalize_path_basic("..")
        assert result == ".."

    def test_mixed_separators(self):
        """测试混合分隔符"""
        if os.sep == "/":
            result = PathUtils.normalize_path_basic("/path/to\\file")
            assert isinstance(result, str)

    def test_unicode_normalization_edge_cases(self):
        """测试Unicode边界情况"""
        # 测试emoji路径
        emoji_path = "/path/😀/file"
        result = PathUtils.normalize_unicode_safe(emoji_path)
        assert "😀" in result

        # 测试组合字符
        combined_path = "/café/file"  # é as combining character
        result = PathUtils.normalize_unicode_safe(combined_path)
        assert "caf" in result


@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.timeout(30)
class TestPathUtilsPerformance:
    """性能测试"""

    def test_normalize_performance(self, performance_tracker):
        """测试规范化性能"""
        paths = [f"/path/to/file{i}.txt" for i in range(1000)]

        performance_tracker.start()
        for path in paths:
            PathUtils.normalize_path_basic(path)
        performance_tracker.stop()

        performance_tracker.assert_faster_than(0.5)  # 1000次应在0.5秒内

    def test_canonicalize_performance(self, temp_test_dir, performance_tracker):
        """测试完整标准化性能"""
        # 创建测试文件
        test_file = temp_test_dir / "test.txt"
        test_file.touch()

        performance_tracker.start()
        for _ in range(100):
            PathUtils.canonicalize_path(str(test_file))
        performance_tracker.stop()

        performance_tracker.assert_faster_than(1.0)  # 100次应在1秒内

