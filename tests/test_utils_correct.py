#!/usr/bin/env python3
"""
Utils模块正确测试

测试第3周重构创建的工具模块类和函数
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

# 导入被测试的模块
from plookingII.utils.path_utils import PathUtils
from plookingII.utils.file_utils import FileUtils
from plookingII.utils.validation_utils import ValidationUtils
from plookingII.utils.error_utils import safe_execute, handle_exceptions, ErrorCollector


class TestPathUtils:
    """PathUtils类测试"""
    
    def test_normalize_path_basic(self):
        """测试基础路径规范化"""
        # 测试正常路径
        path = "/Users/test/Documents"
        result = PathUtils.normalize_path_basic(path)
        assert result == path
        
        # 测试空路径
        result = PathUtils.normalize_path_basic("")
        assert result == ""
        
        # 测试None
        result = PathUtils.normalize_path_basic(None)
        assert result == ""
    
    def test_canon_path(self):
        """测试路径标准化"""
        # 测试相对路径
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = os.path.join(temp_dir, "test")
            os.makedirs(test_path, exist_ok=True)
            
            result = PathUtils.canon_path(test_path)
            assert os.path.isabs(result)
            assert os.path.exists(result)
    
    def test_safe_path_join(self):
        """测试安全路径连接"""
        base = "/Users/test"
        relative = "Documents/file.txt"
        
        result = PathUtils.safe_path_join(base, relative)
        expected = os.path.join(base, relative)
        assert result == expected
        
        # 测试空参数
        result = PathUtils.safe_path_join("", "test")
        assert result == "test"
    
    def test_get_parent_directory(self):
        """测试获取父目录"""
        path = "/Users/test/Documents/file.txt"
        result = PathUtils.get_parent_directory(path)
        assert result == "/Users/test/Documents"
        
        # 测试根目录
        result = PathUtils.get_parent_directory("/")
        assert result == "/"
    
    def test_is_subdirectory(self):
        """测试子目录检查"""
        parent = "/Users/test"
        child = "/Users/test/Documents"
        
        result = PathUtils.is_subdirectory(child, parent)
        assert result is True
        
        # 测试非子目录
        result = PathUtils.is_subdirectory("/Users/other", parent)
        assert result is False
    
    def test_get_relative_path(self):
        """测试获取相对路径"""
        base = "/Users/test"
        target = "/Users/test/Documents/file.txt"
        
        result = PathUtils.get_relative_path(target, base)
        assert result == "Documents/file.txt"
    
    def test_ensure_directory_exists(self):
        """测试确保目录存在"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = os.path.join(temp_dir, "new_dir")
            
            result = PathUtils.ensure_directory_exists(test_dir)
            assert result is True
            assert os.path.exists(test_dir)
            assert os.path.isdir(test_dir)
    
    def test_get_file_extension(self):
        """测试获取文件扩展名"""
        result = PathUtils.get_file_extension("test.jpg")
        assert result == ".jpg"
        
        result = PathUtils.get_file_extension("test.tar.gz")
        assert result == ".gz"
        
        result = PathUtils.get_file_extension("test")
        assert result == ""


class TestFileUtils:
    """FileUtils类测试"""
    
    def test_is_image_file(self):
        """测试图片文件检测"""
        # 测试图片文件
        assert FileUtils.is_image_file("test.jpg") is True
        assert FileUtils.is_image_file("test.png") is True
        assert FileUtils.is_image_file("test.gif") is True
        
        # 测试非图片文件
        assert FileUtils.is_image_file("test.txt") is False
        assert FileUtils.is_image_file("test.pdf") is False
        
        # 测试大小写
        assert FileUtils.is_image_file("test.JPG") is True
    
    def test_get_file_size(self):
        """测试获取文件大小"""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_file.flush()
            
            try:
                size = FileUtils.get_file_size(temp_file.name)
                assert size == 12  # "test content" 长度
            finally:
                os.unlink(temp_file.name)
        
        # 测试不存在的文件
        size = FileUtils.get_file_size("/nonexistent/file.txt")
        assert size == 0
    
    def test_folder_contains_images(self):
        """测试文件夹包含图片检测"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建图片文件
            img_file = os.path.join(temp_dir, "test.jpg")
            with open(img_file, 'w') as f:
                f.write("fake image")
            
            result = FileUtils.folder_contains_images(temp_dir)
            assert result is True
            
            # 测试空文件夹
            empty_dir = os.path.join(temp_dir, "empty")
            os.makedirs(empty_dir)
            result = FileUtils.folder_contains_images(empty_dir)
            assert result is False
    
    def test_get_image_files_in_folder(self):
        """测试获取文件夹中的图片文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            files = ["test1.jpg", "test2.png", "test3.txt", "test4.gif"]
            for filename in files:
                filepath = os.path.join(temp_dir, filename)
                with open(filepath, 'w') as f:
                    f.write("test")
            
            result = FileUtils.get_image_files_in_folder(temp_dir)
            image_files = [os.path.basename(f) for f in result]
            
            assert "test1.jpg" in image_files
            assert "test2.png" in image_files
            assert "test4.gif" in image_files
            assert "test3.txt" not in image_files
    
    def test_safe_file_read(self):
        """测试安全文件读取"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("test content")
            temp_file.flush()
            
            try:
                content = FileUtils.safe_file_read(temp_file.name)
                assert content == "test content"
            finally:
                os.unlink(temp_file.name)
        
        # 测试不存在的文件
        content = FileUtils.safe_file_read("/nonexistent/file.txt")
        assert content == ""
    
    def test_safe_file_write(self):
        """测试安全文件写入"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            content = "test content"
            
            result = FileUtils.safe_file_write(test_file, content)
            assert result is True
            
            # 验证写入内容
            with open(test_file, 'r') as f:
                assert f.read() == content
    
    def test_create_backup_filename(self):
        """测试创建备份文件名"""
        original = "/path/to/file.txt"
        backup = FileUtils.create_backup_filename(original)
        
        assert backup.startswith("/path/to/file_backup_")
        assert backup.endswith(".txt")


class TestValidationUtils:
    """ValidationUtils类测试"""
    
    def test_is_valid_path(self):
        """测试路径有效性验证"""
        # 测试有效路径
        assert ValidationUtils.is_valid_path("/Users/test") is True
        assert ValidationUtils.is_valid_path("relative/path") is True
        
        # 测试无效路径
        assert ValidationUtils.is_valid_path("") is False
        assert ValidationUtils.is_valid_path(None) is False
    
    def test_is_safe_filename(self):
        """测试安全文件名验证"""
        # 测试安全文件名
        assert ValidationUtils.is_safe_filename("test.jpg") is True
        assert ValidationUtils.is_safe_filename("my_file_123.png") is True
        
        # 测试不安全文件名
        assert ValidationUtils.is_safe_filename("../test.jpg") is False
        assert ValidationUtils.is_safe_filename("test/file.jpg") is False
        assert ValidationUtils.is_safe_filename("") is False
    
    def test_validate_image_extension(self):
        """测试图片扩展名验证"""
        # 测试有效扩展名
        assert ValidationUtils.validate_image_extension(".jpg") is True
        assert ValidationUtils.validate_image_extension(".png") is True
        assert ValidationUtils.validate_image_extension(".gif") is True
        
        # 测试无效扩展名
        assert ValidationUtils.validate_image_extension(".txt") is False
        assert ValidationUtils.validate_image_extension(".pdf") is False
        assert ValidationUtils.validate_image_extension("") is False
    
    def test_is_within_size_limit(self):
        """测试文件大小限制验证"""
        # 测试在限制内
        assert ValidationUtils.is_within_size_limit(1024, 2048) is True
        assert ValidationUtils.is_within_size_limit(0, 1024) is True
        
        # 测试超出限制
        assert ValidationUtils.is_within_size_limit(2048, 1024) is False
        
        # 测试边界情况
        assert ValidationUtils.is_within_size_limit(1024, 1024) is True
    
    def test_validate_folder_structure(self):
        """测试文件夹结构验证"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建有效的文件夹结构
            sub_dir = os.path.join(temp_dir, "subdir")
            os.makedirs(sub_dir)
            
            result = ValidationUtils.validate_folder_structure(temp_dir)
            assert result is True
            
            # 测试无效路径
            result = ValidationUtils.validate_folder_structure("/nonexistent/path")
            assert result is False
    
    def test_check_permissions(self):
        """测试权限检查"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试可读写目录
            result = ValidationUtils.check_permissions(temp_dir, read=True, write=True)
            assert result is True
            
            # 测试不存在的路径
            result = ValidationUtils.check_permissions("/nonexistent/path", read=True)
            assert result is False
    
    def test_validate_configuration(self):
        """测试配置验证"""
        # 测试有效配置
        config = {
            "cache_size": 100,
            "max_files": 1000,
            "timeout": 30
        }
        result = ValidationUtils.validate_configuration(config)
        assert result is True
        
        # 测试无效配置
        invalid_config = {
            "cache_size": -1,  # 负数
            "max_files": "invalid",  # 非数字
        }
        result = ValidationUtils.validate_configuration(invalid_config)
        assert result is False
    
    def test_sanitize_input(self):
        """测试输入清理"""
        # 测试正常输入
        result = ValidationUtils.sanitize_input("normal text")
        assert result == "normal text"
        
        # 测试需要清理的输入
        result = ValidationUtils.sanitize_input("  text with spaces  ")
        assert result == "text with spaces"
        
        # 测试空输入
        result = ValidationUtils.sanitize_input("")
        assert result == ""
    
    def test_validate_url(self):
        """测试URL验证"""
        # 测试有效URL
        assert ValidationUtils.validate_url("http://example.com") is True
        assert ValidationUtils.validate_url("https://example.com/path") is True
        
        # 测试无效URL
        assert ValidationUtils.validate_url("not-a-url") is False
        assert ValidationUtils.validate_url("") is False


class TestErrorUtils:
    """ErrorUtils函数测试"""
    
    def test_safe_execute(self):
        """测试安全执行"""
        # 测试成功执行
        def success_func():
            return "success"
        
        result = safe_execute(success_func)
        assert result == "success"
        
        # 测试异常处理
        def error_func():
            raise ValueError("test error")
        
        result = safe_execute(error_func, default="default")
        assert result == "default"
    
    def test_handle_exceptions_decorator(self):
        """测试异常处理装饰器"""
        @handle_exceptions(default_return="error")
        def test_func():
            raise ValueError("test error")
        
        result = test_func()
        assert result == "error"
    
    def test_error_collector(self):
        """测试错误收集器"""
        collector = ErrorCollector()
        
        # 测试添加错误
        collector.add_error("test error", "test context")
        
        # 测试获取错误
        errors = collector.get_errors()
        assert len(errors) == 1
        assert "test error" in str(errors[0])


@pytest.mark.integration
class TestUtilsIntegration:
    """Utils模块集成测试"""
    
    def test_complete_file_processing_workflow(self):
        """测试完整的文件处理工作流"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. 创建测试文件
            test_file = os.path.join(temp_dir, "test.jpg")
            with open(test_file, 'w') as f:
                f.write("fake image content")
            
            # 2. 路径验证
            normalized_path = PathUtils.normalize_path_basic(test_file)
            assert ValidationUtils.is_valid_path(normalized_path)
            
            # 3. 文件验证
            assert FileUtils.is_image_file(normalized_path)
            assert ValidationUtils.is_safe_filename(os.path.basename(normalized_path))
            
            # 4. 文件操作
            content = FileUtils.safe_file_read(normalized_path)
            assert content == "fake image content"
            
            # 5. 错误处理测试
            def risky_operation():
                return FileUtils.get_file_size(normalized_path)
            
            size = safe_execute(risky_operation, default=0)
            assert size > 0
    
    def test_folder_scanning_workflow(self):
        """测试文件夹扫描工作流"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件结构
            files = ["image1.jpg", "image2.png", "document.txt", "image3.gif"]
            for filename in files:
                filepath = os.path.join(temp_dir, filename)
                with open(filepath, 'w') as f:
                    f.write("test content")
            
            # 1. 文件夹验证
            assert ValidationUtils.validate_folder_structure(temp_dir)
            assert ValidationUtils.check_permissions(temp_dir, read=True)
            
            # 2. 图片检测
            assert FileUtils.folder_contains_images(temp_dir)
            
            # 3. 获取图片文件列表
            image_files = FileUtils.get_image_files_in_folder(temp_dir)
            assert len(image_files) == 3  # jpg, png, gif
            
            # 4. 路径处理
            for img_file in image_files:
                normalized = PathUtils.normalize_path_basic(img_file)
                assert ValidationUtils.is_valid_path(normalized)
                assert ValidationUtils.validate_image_extension(
                    PathUtils.get_file_extension(normalized)
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
