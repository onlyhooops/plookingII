#!/usr/bin/env python3
"""
测试 core/error_handling.py

Author: PlookingII Team
"""

import pytest

from plookingII.core.error_handling import (
    ConfigurationError,
    ErrorCategory,
    ErrorInfo,
    ErrorSeverity,
    ImageProcessingError,
    MemoryError,
    PlookingIIError,
)


class TestErrorSeverity:
    """测试ErrorSeverity枚举"""

    def test_severity_levels(self):
        """测试严重程度级别"""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"


class TestErrorCategory:
    """测试ErrorCategory枚举"""

    def test_error_categories(self):
        """测试错误类别"""
        assert ErrorCategory.SYSTEM.value == "system"
        assert ErrorCategory.CONFIGURATION.value == "configuration"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.FILE_SYSTEM.value == "file_system"
        assert ErrorCategory.MEMORY.value == "memory"
        assert ErrorCategory.IMAGE_PROCESSING.value == "image_processing"
        assert ErrorCategory.UI.value == "ui"
        assert ErrorCategory.DATABASE.value == "database"
        assert ErrorCategory.CACHE.value == "cache"
        assert ErrorCategory.PERFORMANCE.value == "performance"
        assert ErrorCategory.UNKNOWN.value == "unknown"


class TestErrorInfo:
    """测试ErrorInfo数据类"""

    def test_error_info_creation(self):
        """测试错误信息创建"""
        error = ValueError("test error")
        error_info = ErrorInfo(
            error=error,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            context="test context"
        )

        assert error_info.error == error
        assert error_info.category == ErrorCategory.SYSTEM
        assert error_info.severity == ErrorSeverity.MEDIUM
        assert error_info.context == "test context"
        assert error_info.timestamp > 0

    def test_error_info_with_optional_fields(self):
        """测试错误信息可选字段"""
        error = RuntimeError("test")
        error_info = ErrorInfo(
            error=error,
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.HIGH,
            stack_trace="traceback...",
            recovery_action="retry",
            metadata={"key": "value"}
        )

        assert error_info.stack_trace == "traceback..."
        assert error_info.recovery_action == "retry"
        assert error_info.metadata == {"key": "value"}


class TestPlookingIIError:
    """测试PlookingIIError基础异常类"""

    def test_basic_error(self):
        """测试基础错误"""
        error = PlookingIIError("Test error")
        assert str(error) == "Test error"
        assert error.category == ErrorCategory.UNKNOWN
        assert error.severity == ErrorSeverity.MEDIUM

    def test_error_with_category_and_severity(self):
        """测试带类别和严重程度的错误"""
        error = PlookingIIError(
            "Test error",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH
        )
        assert error.category == ErrorCategory.NETWORK
        assert error.severity == ErrorSeverity.HIGH

    def test_error_with_metadata(self):
        """测试带元数据的错误"""
        error = PlookingIIError(
            "Test error",
            file_path="/test/path",
            line_number=42
        )
        assert error.metadata["file_path"] == "/test/path"
        assert error.metadata["line_number"] == 42


class TestConfigurationError:
    """测试ConfigurationError"""

    def test_configuration_error(self):
        """测试配置错误"""
        error = ConfigurationError("Invalid config")
        assert str(error) == "Invalid config"
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.severity == ErrorSeverity.MEDIUM

    def test_configuration_error_with_metadata(self):
        """测试带元数据的配置错误"""
        error = ConfigurationError("Invalid config", config_key="test_key")
        assert error.metadata["config_key"] == "test_key"


class TestImageProcessingError:
    """测试ImageProcessingError"""

    def test_image_processing_error(self):
        """测试图像处理错误"""
        error = ImageProcessingError("Failed to process image")
        assert str(error) == "Failed to process image"
        assert error.category == ErrorCategory.IMAGE_PROCESSING
        assert error.severity == ErrorSeverity.MEDIUM

    def test_image_processing_error_with_custom_severity(self):
        """测试自定义严重程度的图像处理错误"""
        error = ImageProcessingError(
            "Critical image error",
            severity=ErrorSeverity.CRITICAL
        )
        assert error.severity == ErrorSeverity.CRITICAL

    def test_image_processing_error_with_metadata(self):
        """测试带元数据的图像处理错误"""
        error = ImageProcessingError(
            "Failed to load image",
            image_path="/path/to/image.jpg",
            image_size="10MB"
        )
        assert error.metadata["image_path"] == "/path/to/image.jpg"
        assert error.metadata["image_size"] == "10MB"


class TestMemoryError:
    """测试MemoryError"""

    def test_memory_error(self):
        """测试内存错误"""
        error = MemoryError("Out of memory")
        assert str(error) == "Out of memory"
        assert error.category == ErrorCategory.MEMORY
        assert error.severity == ErrorSeverity.HIGH

    def test_memory_error_with_metadata(self):
        """测试带元数据的内存错误"""
        error = MemoryError(
            "Memory limit exceeded",
            current_usage="2GB",
            limit="1GB"
        )
        assert error.metadata["current_usage"] == "2GB"
        assert error.metadata["limit"] == "1GB"


class TestExceptionInheritance:
    """测试异常继承关系"""

    def test_plookingii_error_is_exception(self):
        """测试PlookingIIError是Exception"""
        assert issubclass(PlookingIIError, Exception)

    def test_specific_errors_are_plookingii_error(self):
        """测试特定错误是PlookingIIError"""
        assert issubclass(ConfigurationError, PlookingIIError)
        assert issubclass(ImageProcessingError, PlookingIIError)
        assert issubclass(MemoryError, PlookingIIError)

    def test_catching_base_error(self):
        """测试捕获基础错误"""
        try:
            raise ConfigurationError("test")
        except PlookingIIError as e:
            assert isinstance(e, ConfigurationError)
            assert isinstance(e, PlookingIIError)

