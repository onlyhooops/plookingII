#!/usr/bin/env python3
"""
测试 core/enhanced_logging.py

Author: PlookingII Team
"""

import logging

import pytest

from plookingII.core.enhanced_logging import (
    LogCategory,
    LogEntry,
    LogLevel,
    StructuredFormatter,
)


class TestLogLevel:
    """测试LogLevel枚举"""

    def test_log_levels(self):
        """测试日志级别"""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"


class TestLogCategory:
    """测试LogCategory枚举"""

    def test_log_categories(self):
        """测试日志类别"""
        assert LogCategory.SYSTEM.value == "system"
        assert LogCategory.USER_ACTION.value == "user_action"
        assert LogCategory.PERFORMANCE.value == "performance"
        assert LogCategory.ERROR.value == "error"
        assert LogCategory.SECURITY.value == "security"
        assert LogCategory.BUSINESS.value == "business"
        assert LogCategory.FILE_SYSTEM.value == "file_system"
        assert LogCategory.NETWORK.value == "network"
        assert LogCategory.CACHE.value == "cache"
        assert LogCategory.CONFIGURATION.value == "configuration"
        assert LogCategory.DEBUG.value == "debug"
        assert LogCategory.UNKNOWN.value == "unknown"


class TestLogEntry:
    """测试LogEntry数据类"""

    def test_log_entry_creation(self):
        """测试日志条目创建"""
        entry = LogEntry(
            timestamp=1234567890.0,
            level=LogLevel.INFO,
            category=LogCategory.SYSTEM,
            message="Test message",
            module="test_module",
            function="test_function",
            line_number=42,
            thread_id=1,
            process_id=100
        )

        assert entry.timestamp == 1234567890.0
        assert entry.level == LogLevel.INFO
        assert entry.category == LogCategory.SYSTEM
        assert entry.message == "Test message"
        assert entry.module == "test_module"
        assert entry.function == "test_function"
        assert entry.line_number == 42
        assert entry.thread_id == 1
        assert entry.process_id == 100

    def test_log_entry_with_defaults(self):
        """测试日志条目默认值"""
        entry = LogEntry(
            timestamp=1234567890.0,
            level=LogLevel.INFO,
            category=LogCategory.SYSTEM,
            message="Test",
            module="test",
            function="test",
            line_number=1,
            thread_id=1,
            process_id=1
        )

        assert entry.metadata == {}
        assert entry.exception_info is None
        assert entry.performance_data is None

    def test_log_entry_with_optional_fields(self):
        """测试日志条目可选字段"""
        entry = LogEntry(
            timestamp=1234567890.0,
            level=LogLevel.ERROR,
            category=LogCategory.ERROR,
            message="Error occurred",
            module="test",
            function="test",
            line_number=1,
            thread_id=1,
            process_id=1,
            metadata={"key": "value"},
            exception_info="Traceback...",
            performance_data={"duration": 1.5}
        )

        assert entry.metadata == {"key": "value"}
        assert entry.exception_info == "Traceback..."
        assert entry.performance_data == {"duration": 1.5}


class TestStructuredFormatter:
    """测试StructuredFormatter"""

    def test_formatter_initialization(self):
        """测试格式化器初始化"""
        formatter = StructuredFormatter(include_metadata=True)
        assert formatter.include_metadata is True

        formatter2 = StructuredFormatter(include_metadata=False)
        assert formatter2.include_metadata is False

    def test_format_basic_record(self):
        """测试格式化基本日志记录"""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)
        assert isinstance(formatted, str)
        assert "INFO" in formatted
        assert "Test message" in formatted

    def test_format_with_extra_fields(self):
        """测试格式化带额外字段的记录"""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=42,
            msg="Warning message",
            args=(),
            exc_info=None
        )
        record.category = "test_category"
        record.metadata = {"key": "value"}

        formatted = formatter.format(record)
        assert isinstance(formatted, str)
        assert "WARNING" in formatted

    def test_format_without_metadata(self):
        """测试不包含元数据的格式化"""
        formatter = StructuredFormatter(include_metadata=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test",
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)
        assert isinstance(formatted, str)

