#!/usr/bin/env python3
"""
Utils模块简化测试

测试第3周重构创建的工具模块中实际存在的函数
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

# 导入被测试的模块
import plookingII.utils.path_utils as path_utils
import plookingII.utils.file_utils as file_utils
import plookingII.utils.validation_utils as validation_utils
import plookingII.utils.error_utils as error_utils


class TestPathUtilsBasic:
    """PathUtils基础测试"""
    
    def test_normalize_path_basic_exists(self):
        """测试normalize_path_basic函数存在"""
        assert hasattr(path_utils, 'normalize_path_basic')
        
        # 测试基本功能
        result = path_utils.normalize_path_basic("/test/path")
        assert isinstance(result, str)
    
    def test_canon_path_exists(self):
        """测试canon_path函数存在"""
        assert hasattr(path_utils, 'canon_path')
        
        # 测试基本功能
        with tempfile.TemporaryDirectory() as temp_dir:
            result = path_utils.canon_path(temp_dir)
            assert isinstance(result, str)
    
    def test_safe_path_join_exists(self):
        """测试safe_path_join函数存在"""
        assert hasattr(path_utils, 'safe_path_join')
        
        # 测试基本功能
        result = path_utils.safe_path_join("/base", "relative")
        assert isinstance(result, str)


class TestFileUtilsBasic:
    """FileUtils基础测试"""
    
    def test_is_image_file_exists(self):
        """测试is_image_file函数存在"""
        assert hasattr(file_utils, 'is_image_file')
        
        # 测试基本功能
        result = file_utils.is_image_file("test.jpg")
        assert isinstance(result, bool)
        assert result is True
        
        result = file_utils.is_image_file("test.txt")
        assert isinstance(result, bool)
        assert result is False
    
    def test_get_file_size_exists(self):
        """测试get_file_size函数存在"""
        assert hasattr(file_utils, 'get_file_size')
        
        # 测试不存在的文件
        result = file_utils.get_file_size("/nonexistent/file.txt")
        assert isinstance(result, int)
        assert result == 0
    
    def test_folder_contains_images_exists(self):
        """测试folder_contains_images函数存在"""
        assert hasattr(file_utils, 'folder_contains_images')
        
        # 测试基本功能
        with tempfile.TemporaryDirectory() as temp_dir:
            result = file_utils.folder_contains_images(temp_dir)
            assert isinstance(result, bool)


class TestValidationUtilsBasic:
    """ValidationUtils基础测试"""
    
    def test_is_valid_path_exists(self):
        """测试is_valid_path函数存在"""
        assert hasattr(validation_utils, 'is_valid_path')
        
        # 测试基本功能
        result = validation_utils.is_valid_path("/test/path")
        assert isinstance(result, bool)
    
    def test_is_safe_filename_exists(self):
        """测试is_safe_filename函数存在"""
        assert hasattr(validation_utils, 'is_safe_filename')
        
        # 测试基本功能
        result = validation_utils.is_safe_filename("test.jpg")
        assert isinstance(result, bool)
    
    def test_validate_image_extension_exists(self):
        """测试validate_image_extension函数存在"""
        assert hasattr(validation_utils, 'validate_image_extension')
        
        # 测试基本功能
        result = validation_utils.validate_image_extension(".jpg")
        assert isinstance(result, bool)


class TestErrorUtilsBasic:
    """ErrorUtils基础测试"""
    
    def test_safe_execute_exists(self):
        """测试safe_execute函数存在"""
        assert hasattr(error_utils, 'safe_execute')
        
        # 测试成功执行
        def success_func():
            return "success"
        
        result = error_utils.safe_execute(success_func)
        assert result == "success"
        
        # 测试异常处理
        def error_func():
            raise ValueError("test error")
        
        result = error_utils.safe_execute(error_func, default="default")
        assert result == "default"
    
    def test_log_error_exists(self):
        """测试log_error函数存在"""
        assert hasattr(error_utils, 'log_error')
        
        # 测试基本功能（不验证具体行为，只确保不抛异常）
        try:
            error_utils.log_error(ValueError("test"), "test context")
        except Exception as e:
            pytest.fail(f"log_error raised {e} unexpectedly!")


@pytest.mark.integration
class TestUtilsIntegrationBasic:
    """Utils模块基础集成测试"""
    
    def test_file_processing_workflow(self):
        """测试基本文件处理工作流"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            test_file = os.path.join(temp_dir, "test.jpg")
            with open(test_file, 'w') as f:
                f.write("fake image content")
            
            # 测试路径处理
            normalized_path = path_utils.normalize_path_basic(test_file)
            assert validation_utils.is_valid_path(normalized_path)
            
            # 测试文件检测
            assert file_utils.is_image_file(normalized_path)
            
            # 测试安全执行
            def get_size():
                return file_utils.get_file_size(normalized_path)
            
            size = error_utils.safe_execute(get_size, default=0)
            assert size >= 0
    
    def test_validation_workflow(self):
        """测试验证工作流"""
        # 测试文件名验证
        assert validation_utils.is_safe_filename("test.jpg")
        assert not validation_utils.is_safe_filename("../test.jpg")
        
        # 测试扩展名验证
        assert validation_utils.validate_image_extension(".jpg")
        assert not validation_utils.validate_image_extension(".txt")
        
        # 测试路径验证
        assert validation_utils.is_valid_path("/valid/path")
        assert not validation_utils.is_valid_path("")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
