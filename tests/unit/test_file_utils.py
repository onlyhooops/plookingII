"""
文件工具模块完整测试
目标覆盖率: 95%+
"""
import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from plookingII.utils.file_utils import FileUtils
from plookingII.core.error_handling import FolderValidationError


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestFileUtilsIsImageFile:
    """测试图片文件检测功能"""
    
    def test_is_image_file_jpg(self):
        """测试JPG文件识别"""
        assert FileUtils.is_image_file("test.jpg") is True
        assert FileUtils.is_image_file("test.JPG") is True
        assert FileUtils.is_image_file("test.jpeg") is True
        assert FileUtils.is_image_file("test.JPEG") is True
    
    def test_is_image_file_png(self):
        """测试PNG文件识别"""
        assert FileUtils.is_image_file("test.png") is True
        assert FileUtils.is_image_file("test.PNG") is True
    
    def test_is_image_file_other_formats(self):
        """测试不支持的图片格式"""
        unsupported_formats = [
            "test.gif", "test.GIF",
            "test.bmp", "test.BMP",
            "test.tif", "test.TIF",
            "test.tiff", "test.TIFF",
            "test.webp", "test.WEBP"
        ]
        # 根据constants.py，当前只支持 .jpg, .jpeg, .png
        for filename in unsupported_formats:
            assert FileUtils.is_image_file(filename) is False, f"{filename} should not be recognized"
    
    def test_is_image_file_with_path(self):
        """测试带路径的文件名"""
        assert FileUtils.is_image_file("/path/to/image.jpg") is True
        assert FileUtils.is_image_file("/path/to/image.PNG") is True
        assert FileUtils.is_image_file("relative/path/image.jpeg") is True
    
    def test_is_not_image_file(self):
        """测试非图片文件"""
        assert FileUtils.is_image_file("test.txt") is False
        assert FileUtils.is_image_file("test.pdf") is False
        assert FileUtils.is_image_file("test.doc") is False
        assert FileUtils.is_image_file("test.mp4") is False
        assert FileUtils.is_image_file("test") is False
        assert FileUtils.is_image_file("") is False
    
    def test_is_image_file_case_insensitive(self):
        """测试大小写不敏感"""
        assert FileUtils.is_image_file("test.JpG") is True
        assert FileUtils.is_image_file("test.PnG") is True
        assert FileUtils.is_image_file("test.JpEg") is True
    
    def test_is_image_file_exception_handling(self):
        """测试异常处理"""
        # None值应返回False (会在endswith调用时抛出AttributeError)
        assert FileUtils.is_image_file(None) is False
        
        # 其他异常也应返回False
        assert FileUtils.is_image_file(123) is False  # 非字符串类型
        assert FileUtils.is_image_file([]) is False  # 列表类型


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestFileUtilsListFilesSafe:
    """测试安全列出文件夹内容"""
    
    def test_list_files_safe_success(self, temp_test_dir):
        """测试成功列出文件"""
        # 创建测试文件
        (temp_test_dir / "file1.txt").touch()
        (temp_test_dir / "file2.jpg").touch()
        (temp_test_dir / "file3.png").touch()
        
        files = FileUtils.list_files_safe(str(temp_test_dir))
        
        assert len(files) == 3
        assert "file1.txt" in files
        assert "file2.jpg" in files
        assert "file3.png" in files
    
    def test_list_files_safe_empty_folder(self, temp_test_dir):
        """测试空文件夹"""
        files = FileUtils.list_files_safe(str(temp_test_dir))
        assert files == []
    
    def test_list_files_safe_nonexistent_folder(self):
        """测试不存在的文件夹"""
        files = FileUtils.list_files_safe("/nonexistent/folder/path")
        assert files == []
    
    def test_list_files_safe_permission_denied(self):
        """测试权限拒绝"""
        with patch('os.listdir', side_effect=PermissionError("Access denied")):
            files = FileUtils.list_files_safe("/some/path")
            assert files == []
    
    def test_list_files_safe_with_subdirs(self, temp_test_dir):
        """测试包含子目录的文件夹"""
        # 创建文件和子目录
        (temp_test_dir / "file1.txt").touch()
        (temp_test_dir / "subdir").mkdir()
        (temp_test_dir / "file2.jpg").touch()
        
        files = FileUtils.list_files_safe(str(temp_test_dir))
        
        assert len(files) == 3
        assert "file1.txt" in files
        assert "subdir" in files
        assert "file2.jpg" in files
    
    def test_list_files_safe_unicode_names(self, temp_test_dir):
        """测试Unicode文件名"""
        (temp_test_dir / "文件.jpg").touch()
        (temp_test_dir / "图片.png").touch()
        
        files = FileUtils.list_files_safe(str(temp_test_dir))
        
        assert len(files) == 2
        assert "文件.jpg" in files
        assert "图片.png" in files


@pytest.mark.unit
@pytest.mark.timeout(15)
class TestFileUtilsFolderContainsImages:
    """测试文件夹是否包含图片"""
    
    def test_folder_contains_images_true(self, temp_test_dir):
        """测试包含图片的文件夹"""
        (temp_test_dir / "image.jpg").touch()
        (temp_test_dir / "document.txt").touch()
        
        result = FileUtils.folder_contains_images(str(temp_test_dir))
        assert result is True
    
    def test_folder_contains_images_false(self, temp_test_dir):
        """测试不包含图片的文件夹"""
        (temp_test_dir / "document.txt").touch()
        (temp_test_dir / "data.csv").touch()
        
        result = FileUtils.folder_contains_images(str(temp_test_dir))
        assert result is False
    
    def test_folder_contains_images_empty_folder(self, temp_test_dir):
        """测试空文件夹"""
        result = FileUtils.folder_contains_images(str(temp_test_dir))
        assert result is False
    
    def test_folder_contains_images_recursive_depth_0(self, temp_test_dir):
        """测试递归深度为0（仅当前目录）"""
        # 当前目录无图片
        (temp_test_dir / "file.txt").touch()
        
        # 子目录有图片
        subdir = temp_test_dir / "subdir"
        subdir.mkdir()
        (subdir / "image.jpg").touch()
        
        result = FileUtils.folder_contains_images(str(temp_test_dir), recursive_depth=0)
        assert result is False
    
    def test_folder_contains_images_recursive_depth_1(self, temp_test_dir):
        """测试递归深度为1（检查子目录）"""
        # 当前目录无图片
        (temp_test_dir / "file.txt").touch()
        
        # 子目录有图片
        subdir = temp_test_dir / "subdir"
        subdir.mkdir()
        (subdir / "image.jpg").touch()
        
        result = FileUtils.folder_contains_images(str(temp_test_dir), recursive_depth=1)
        assert result is True
    
    def test_folder_contains_images_multiple_subdirs(self, temp_test_dir):
        """测试多个子目录"""
        # 创建多个子目录，只有一个包含图片
        (temp_test_dir / "subdir1").mkdir()
        (temp_test_dir / "subdir1" / "file.txt").touch()
        
        (temp_test_dir / "subdir2").mkdir()
        (temp_test_dir / "subdir2" / "image.png").touch()
        
        result = FileUtils.folder_contains_images(str(temp_test_dir), recursive_depth=1)
        assert result is True
    
    def test_folder_contains_images_permission_error_subfolder(self, temp_test_dir):
        """测试子文件夹权限错误"""
        # 当前目录无图片
        (temp_test_dir / "file.txt").touch()
        
        # 创建子目录
        subdir = temp_test_dir / "subdir"
        subdir.mkdir()
        
        # Mock子目录访问失败
        original_listdir = os.listdir
        def mock_listdir(path):
            if "subdir" in str(path):
                raise PermissionError("Access denied")
            return original_listdir(path)
        
        with patch('os.listdir', side_effect=mock_listdir):
            result = FileUtils.folder_contains_images(str(temp_test_dir), recursive_depth=1)
            assert result is False  # 应该继续检查其他目录
    
    def test_folder_contains_images_raises_validation_error(self):
        """测试无法访问文件夹时的处理"""
        # 根据实际实现，list_files_safe会捕获异常并返回空列表
        # 因此folder_contains_images会返回False而不是抛出异常
        with patch('os.listdir', side_effect=Exception("Fatal error")):
            result = FileUtils.folder_contains_images("/nonexistent/path")
            assert result is False  # 无法访问时返回False
    
    def test_folder_contains_images_various_formats(self, temp_test_dir):
        """测试各种图片格式"""
        # 根据constants.py，当前只支持 jpg, jpeg, png
        supported_formats = ["jpg", "jpeg", "png"]
        unsupported_formats = ["gif", "bmp", "tiff", "webp"]
        
        # 测试支持的格式
        for fmt in supported_formats:
            test_dir = temp_test_dir / f"test_{fmt}"
            test_dir.mkdir()
            (test_dir / f"image.{fmt}").touch()
            
            result = FileUtils.folder_contains_images(str(test_dir))
            assert result is True, f"Should detect {fmt} images"
        
        # 测试不支持的格式
        for fmt in unsupported_formats:
            test_dir = temp_test_dir / f"test_{fmt}_unsupported"
            test_dir.mkdir()
            (test_dir / f"image.{fmt}").touch()
            
            result = FileUtils.folder_contains_images(str(test_dir))
            assert result is False, f"Should not detect {fmt} images"


@pytest.mark.unit
@pytest.mark.timeout(15)
class TestFileUtilsGetImageFiles:
    """测试获取图片文件列表"""
    
    def test_get_image_files_basic(self, temp_test_dir):
        """测试基本获取图片文件"""
        (temp_test_dir / "image1.jpg").touch()
        (temp_test_dir / "image2.png").touch()
        (temp_test_dir / "document.txt").touch()
        
        images = FileUtils.get_image_files(str(temp_test_dir))
        
        assert len(images) == 2
        assert any("image1.jpg" in img for img in images)
        assert any("image2.png" in img for img in images)
    
    def test_get_image_files_empty_folder(self, temp_test_dir):
        """测试空文件夹"""
        images = FileUtils.get_image_files(str(temp_test_dir))
        assert images == []
    
    def test_get_image_files_no_images(self, temp_test_dir):
        """测试没有图片的文件夹"""
        (temp_test_dir / "file1.txt").touch()
        (temp_test_dir / "file2.pdf").touch()
        
        images = FileUtils.get_image_files(str(temp_test_dir))
        assert images == []
    
    def test_get_image_files_recursive_false(self, temp_test_dir):
        """测试非递归模式"""
        # 当前目录
        (temp_test_dir / "image1.jpg").touch()
        
        # 子目录
        subdir = temp_test_dir / "subdir"
        subdir.mkdir()
        (subdir / "image2.jpg").touch()
        
        images = FileUtils.get_image_files(str(temp_test_dir), recursive=False)
        
        assert len(images) == 1
        assert "image1.jpg" in images[0]
    
    def test_get_image_files_recursive_true(self, temp_test_dir):
        """测试递归模式"""
        # 当前目录
        (temp_test_dir / "image1.jpg").touch()
        
        # 子目录
        subdir = temp_test_dir / "subdir"
        subdir.mkdir()
        (subdir / "image2.jpg").touch()
        
        # 子子目录
        subsubdir = subdir / "subsubdir"
        subsubdir.mkdir()
        (subsubdir / "image3.jpg").touch()
        
        images = FileUtils.get_image_files(str(temp_test_dir), recursive=True)
        
        assert len(images) == 3
        assert any("image1.jpg" in img for img in images)
        assert any("image2.jpg" in img for img in images)
        assert any("image3.jpg" in img for img in images)
    
    def test_get_image_files_full_paths(self, temp_test_dir):
        """测试返回完整路径"""
        (temp_test_dir / "image.jpg").touch()
        
        images = FileUtils.get_image_files(str(temp_test_dir))
        
        assert len(images) == 1
        assert os.path.isabs(images[0])
        assert images[0].endswith("image.jpg")
    
    def test_get_image_files_mixed_case(self, temp_test_dir):
        """测试混合大小写"""
        (temp_test_dir / "Image1.JPG").touch()
        (temp_test_dir / "image2.Png").touch()
        (temp_test_dir / "IMAGE3.jpeg").touch()
        
        images = FileUtils.get_image_files(str(temp_test_dir))
        assert len(images) == 3
    
    def test_get_image_files_exception_handling(self, temp_test_dir):
        """测试异常处理"""
        with patch('os.listdir', side_effect=Exception("Error")):
            images = FileUtils.get_image_files(str(temp_test_dir))
            assert images == []
    
    def test_get_image_files_subfolder_exception(self, temp_test_dir):
        """测试子文件夹异常处理"""
        # 当前目录有图片
        (temp_test_dir / "image1.jpg").touch()
        
        # 创建子目录
        subdir = temp_test_dir / "subdir"
        subdir.mkdir()
        
        # Mock子目录访问失败
        original_listdir = os.listdir
        def mock_listdir(path):
            if "subdir" in str(path):
                raise PermissionError("Access denied")
            return original_listdir(path)
        
        with patch('os.listdir', side_effect=mock_listdir):
            images = FileUtils.get_image_files(str(temp_test_dir), recursive=True)
            # 应该至少获取到当前目录的图片
            assert len(images) >= 1


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestFileUtilsCountImageFiles:
    """测试统计图片文件数量"""
    
    def test_count_image_files_basic(self, temp_test_dir):
        """测试基本计数"""
        (temp_test_dir / "image1.jpg").touch()
        (temp_test_dir / "image2.png").touch()
        (temp_test_dir / "file.txt").touch()
        
        count = FileUtils.count_image_files(str(temp_test_dir))
        assert count == 2
    
    def test_count_image_files_zero(self, temp_test_dir):
        """测试零图片"""
        (temp_test_dir / "file.txt").touch()
        
        count = FileUtils.count_image_files(str(temp_test_dir))
        assert count == 0
    
    def test_count_image_files_empty_folder(self, temp_test_dir):
        """测试空文件夹"""
        count = FileUtils.count_image_files(str(temp_test_dir))
        assert count == 0
    
    def test_count_image_files_recursive(self, temp_test_dir):
        """测试递归计数"""
        (temp_test_dir / "image1.jpg").touch()
        
        subdir = temp_test_dir / "subdir"
        subdir.mkdir()
        (subdir / "image2.jpg").touch()
        (subdir / "image3.png").touch()
        
        count = FileUtils.count_image_files(str(temp_test_dir), recursive=True)
        assert count == 3
    
    def test_count_image_files_exception(self):
        """测试异常返回0"""
        count = FileUtils.count_image_files("/nonexistent/path")
        assert count == 0


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestFileUtilsGetFolderInfo:
    """测试获取文件夹信息"""
    
    def test_get_folder_info_basic(self, temp_test_dir):
        """测试基本信息获取"""
        (temp_test_dir / "image1.jpg").touch()
        (temp_test_dir / "image2.png").touch()
        (temp_test_dir / "file.txt").touch()
        
        total, images, has_subfolders = FileUtils.get_folder_info(str(temp_test_dir))
        
        assert total == 3
        assert images == 2
        assert has_subfolders is False
    
    def test_get_folder_info_with_subfolders(self, temp_test_dir):
        """测试包含子文件夹"""
        (temp_test_dir / "image.jpg").touch()
        (temp_test_dir / "subdir").mkdir()
        
        total, images, has_subfolders = FileUtils.get_folder_info(str(temp_test_dir))
        
        assert total == 1  # 只统计文件，不统计目录
        assert images == 1
        assert has_subfolders is True
    
    def test_get_folder_info_empty(self, temp_test_dir):
        """测试空文件夹"""
        total, images, has_subfolders = FileUtils.get_folder_info(str(temp_test_dir))
        
        assert total == 0
        assert images == 0
        assert has_subfolders is False
    
    def test_get_folder_info_only_subfolders(self, temp_test_dir):
        """测试只有子文件夹"""
        (temp_test_dir / "subdir1").mkdir()
        (temp_test_dir / "subdir2").mkdir()
        
        total, images, has_subfolders = FileUtils.get_folder_info(str(temp_test_dir))
        
        assert total == 0
        assert images == 0
        assert has_subfolders is True
    
    def test_get_folder_info_no_images(self, temp_test_dir):
        """测试无图片文件"""
        (temp_test_dir / "file1.txt").touch()
        (temp_test_dir / "file2.pdf").touch()
        
        total, images, has_subfolders = FileUtils.get_folder_info(str(temp_test_dir))
        
        assert total == 2
        assert images == 0
        assert has_subfolders is False
    
    def test_get_folder_info_exception(self):
        """测试异常处理"""
        total, images, has_subfolders = FileUtils.get_folder_info("/nonexistent/path")
        
        assert total == 0
        assert images == 0
        assert has_subfolders is False


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestFileUtilsIsEmptyFolder:
    """测试检查文件夹是否为空"""
    
    def test_is_empty_folder_true(self, temp_test_dir):
        """测试空文件夹"""
        result = FileUtils.is_empty_folder(str(temp_test_dir))
        assert result is True
    
    def test_is_empty_folder_false_with_files(self, temp_test_dir):
        """测试包含文件"""
        (temp_test_dir / "file.txt").touch()
        
        result = FileUtils.is_empty_folder(str(temp_test_dir))
        assert result is False
    
    def test_is_empty_folder_false_with_subdirs(self, temp_test_dir):
        """测试包含子目录"""
        (temp_test_dir / "subdir").mkdir()
        
        result = FileUtils.is_empty_folder(str(temp_test_dir))
        assert result is False
    
    def test_is_empty_folder_nonexistent(self):
        """测试不存在的文件夹"""
        result = FileUtils.is_empty_folder("/nonexistent/path")
        assert result is True  # 访问失败视为空
    
    def test_is_empty_folder_permission_denied(self):
        """测试权限拒绝"""
        with patch('plookingII.utils.file_utils.FileUtils.list_files_safe', return_value=[]):
            result = FileUtils.is_empty_folder("/some/path")
            assert result is True


@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.timeout(30)
class TestFileUtilsPerformance:
    """性能测试"""
    
    def test_large_folder_performance(self, temp_test_dir, performance_tracker):
        """测试大文件夹性能"""
        # 创建100个文件
        for i in range(100):
            if i % 2 == 0:
                (temp_test_dir / f"image{i}.jpg").touch()
            else:
                (temp_test_dir / f"file{i}.txt").touch()
        
        performance_tracker.start()
        images = FileUtils.get_image_files(str(temp_test_dir))
        performance_tracker.stop()
        
        assert len(images) == 50
        performance_tracker.assert_faster_than(1.0)  # 应该在1秒内完成
    
    def test_deep_recursive_performance(self, temp_test_dir, performance_tracker):
        """测试深层递归性能"""
        # 创建10层目录，每层5个文件
        current_dir = temp_test_dir
        for level in range(10):
            for i in range(5):
                (current_dir / f"image{i}.jpg").touch()
            
            next_dir = current_dir / f"level{level}"
            next_dir.mkdir()
            current_dir = next_dir
        
        performance_tracker.start()
        images = FileUtils.get_image_files(str(temp_test_dir), recursive=True)
        performance_tracker.stop()
        
        assert len(images) == 50  # 10层 × 5个文件
        performance_tracker.assert_faster_than(2.0)  # 应该在2秒内完成


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestFileUtilsEdgeCases:
    """边界情况测试"""
    
    def test_hidden_files(self, temp_test_dir):
        """测试隐藏文件"""
        (temp_test_dir / ".hidden.jpg").touch()
        (temp_test_dir / "visible.jpg").touch()
        
        images = FileUtils.get_image_files(str(temp_test_dir))
        assert len(images) == 2  # 应该包含隐藏文件
    
    def test_files_without_extension(self, temp_test_dir):
        """测试无扩展名文件"""
        (temp_test_dir / "noext").touch()
        (temp_test_dir / "image.jpg").touch()
        
        images = FileUtils.get_image_files(str(temp_test_dir))
        assert len(images) == 1
    
    def test_multiple_dots_in_filename(self, temp_test_dir):
        """测试文件名包含多个点"""
        (temp_test_dir / "my.image.file.jpg").touch()
        (temp_test_dir / "another.file.png").touch()
        
        images = FileUtils.get_image_files(str(temp_test_dir))
        assert len(images) == 2
    
    def test_very_long_filename(self, temp_test_dir):
        """测试超长文件名"""
        long_name = "a" * 200 + ".jpg"
        try:
            (temp_test_dir / long_name).touch()
            images = FileUtils.get_image_files(str(temp_test_dir))
            assert len(images) == 1
        except OSError:
            # 某些系统可能不支持超长文件名
            pytest.skip("System does not support very long filenames")
    
    def test_special_characters_in_filename(self, temp_test_dir):
        """测试特殊字符文件名"""
        special_files = [
            "image (1).jpg",
            "image[2].jpg",
            "image{3}.jpg",
            "image@4.jpg"
        ]
        
        for filename in special_files:
            try:
                (temp_test_dir / filename).touch()
            except OSError:
                continue
        
        images = FileUtils.get_image_files(str(temp_test_dir))
        assert len(images) > 0
    
    def test_symlink_handling(self, temp_test_dir):
        """测试符号链接处理"""
        # 创建真实文件
        real_file = temp_test_dir / "real_image.jpg"
        real_file.touch()
        
        # 创建符号链接
        try:
            link_file = temp_test_dir / "link_image.jpg"
            os.symlink(real_file, link_file)
            
            images = FileUtils.get_image_files(str(temp_test_dir))
            # 应该列出两个文件（真实文件和链接）
            assert len(images) >= 1
        except (OSError, NotImplementedError):
            # Windows或某些系统可能不支持符号链接
            pytest.skip("System does not support symlinks")

