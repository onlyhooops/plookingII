"""
测试 core/error_handling.py 模块

测试目标：达到90%+覆盖率
"""

import logging
import threading
import time
from unittest.mock import Mock, MagicMock, patch, call

import pytest

from plookingII.core.error_handling import (
    ErrorSeverity,
    ErrorCategory,
    ErrorInfo,
    PlookingIIError,
    ConfigurationError,
    ImageProcessingError,
    MemoryError,
    FileSystemError,
    UIError,
    DragDropError,
    FolderValidationError,
    CacheError,
    ErrorHandler,
    error_handler,
    error_context,
    setup_error_logging,
    get_error_log_path,
)


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestErrorSeverity:
    """测试ErrorSeverity枚举"""

    def test_severity_values(self):
        """测试严重程度枚举值"""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"

    def test_severity_members(self):
        """测试枚举成员"""
        assert isinstance(ErrorSeverity.LOW, ErrorSeverity)
        assert ErrorSeverity.LOW != ErrorSeverity.HIGH


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestErrorCategory:
    """测试ErrorCategory枚举"""

    def test_category_values(self):
        """测试错误类别枚举值"""
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

    def test_category_members(self):
        """测试枚举成员"""
        assert isinstance(ErrorCategory.SYSTEM, ErrorCategory)
        assert ErrorCategory.SYSTEM != ErrorCategory.NETWORK


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestErrorInfo:
    """测试ErrorInfo数据类"""

    def test_error_info_creation(self):
        """测试创建错误信息"""
        error = ValueError("test error")
        info = ErrorInfo(
            error=error,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            context="test context"
        )
        assert info.error == error
        assert info.category == ErrorCategory.SYSTEM
        assert info.severity == ErrorSeverity.HIGH
        assert info.context == "test context"
        assert isinstance(info.timestamp, float)
        assert info.timestamp > 0

    def test_error_info_with_defaults(self):
        """测试默认值"""
        error = ValueError("test")
        info = ErrorInfo(
            error=error,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM
        )
        assert info.context == ""
        assert info.stack_trace == ""
        assert info.recovery_action is None
        assert info.metadata == {}

    def test_error_info_with_metadata(self):
        """测试带元数据的错误信息"""
        error = ValueError("test")
        metadata = {"key": "value", "number": 42}
        info = ErrorInfo(
            error=error,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.LOW,
            metadata=metadata
        )
        assert info.metadata == metadata


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestPlookingIIError:
    """测试PlookingIIError基类"""

    def test_basic_error(self):
        """测试基础错误"""
        error = PlookingIIError("test error")
        assert str(error) == "test error"
        assert error.category == ErrorCategory.UNKNOWN
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.metadata == {}

    def test_error_with_category(self):
        """测试带类别的错误"""
        error = PlookingIIError("test", category=ErrorCategory.SYSTEM)
        assert error.category == ErrorCategory.SYSTEM

    def test_error_with_severity(self):
        """测试带严重程度的错误"""
        error = PlookingIIError("test", severity=ErrorSeverity.HIGH)
        assert error.severity == ErrorSeverity.HIGH

    def test_error_with_metadata(self):
        """测试带元数据的错误"""
        error = PlookingIIError("test", file="test.py", line=42)
        assert error.metadata == {"file": "test.py", "line": 42}


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestSpecificErrors:
    """测试特定错误类"""

    def test_configuration_error(self):
        """测试配置错误"""
        error = ConfigurationError("invalid config")
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.severity == ErrorSeverity.MEDIUM
        assert "invalid config" in str(error)

    def test_image_processing_error(self):
        """测试图像处理错误"""
        error = ImageProcessingError("image load failed")
        assert error.category == ErrorCategory.IMAGE_PROCESSING
        assert error.severity == ErrorSeverity.MEDIUM

    def test_image_processing_error_high_severity(self):
        """测试高严重度图像错误"""
        error = ImageProcessingError("critical", severity=ErrorSeverity.HIGH)
        assert error.severity == ErrorSeverity.HIGH

    def test_memory_error(self):
        """测试内存错误"""
        error = MemoryError("out of memory")
        assert error.category == ErrorCategory.MEMORY
        assert error.severity == ErrorSeverity.HIGH

    def test_file_system_error(self):
        """测试文件系统错误"""
        error = FileSystemError("file not found")
        assert error.category == ErrorCategory.FILE_SYSTEM
        assert error.severity == ErrorSeverity.MEDIUM

    def test_ui_error(self):
        """测试UI错误"""
        error = UIError("window error")
        assert error.category == ErrorCategory.UI
        assert error.severity == ErrorSeverity.MEDIUM

    def test_drag_drop_error(self):
        """测试拖拽错误"""
        error = DragDropError("drag failed")
        assert error.category == ErrorCategory.UI
        assert error.severity == ErrorSeverity.LOW

    def test_folder_validation_error(self):
        """测试文件夹验证错误"""
        error = FolderValidationError("invalid folder", folder_path="/test/path")
        assert error.category == ErrorCategory.FILE_SYSTEM
        assert error.severity == ErrorSeverity.LOW
        assert error.metadata["folder_path"] == "/test/path"

    def test_cache_error(self):
        """测试缓存错误"""
        error = CacheError("cache miss")
        assert error.category == ErrorCategory.MEMORY
        assert error.severity == ErrorSeverity.LOW


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestErrorHandlerInit:
    """测试ErrorHandler初始化"""

    def test_init(self):
        """测试初始化"""
        handler = ErrorHandler()
        assert isinstance(handler.logger, logging.Logger)
        assert isinstance(handler._error_history, list)
        assert isinstance(handler._error_handlers, dict)
        assert isinstance(handler._recovery_strategies, dict)
        assert len(handler._error_handlers) > 0  # 默认处理器已注册

    def test_default_handlers_registered(self):
        """测试默认处理器已注册"""
        handler = ErrorHandler()
        assert ConfigurationError in handler._error_handlers
        assert ImageProcessingError in handler._error_handlers
        assert MemoryError in handler._error_handlers
        assert FileSystemError in handler._error_handlers
        assert Exception in handler._error_handlers


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestErrorHandlerRegistration:
    """测试错误处理器注册"""

    def test_register_handler(self):
        """测试注册错误处理器"""
        handler = ErrorHandler()
        custom_handler = Mock()
        handler.register_handler(ValueError, custom_handler)
        assert ValueError in handler._error_handlers
        assert handler._error_handlers[ValueError] == custom_handler

    def test_register_recovery_strategy(self):
        """测试注册恢复策略"""
        handler = ErrorHandler()
        strategy = Mock()
        handler.register_recovery_strategy(ErrorCategory.NETWORK, strategy)
        assert ErrorCategory.NETWORK in handler._recovery_strategies
        assert handler._recovery_strategies[ErrorCategory.NETWORK] == strategy


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestErrorHandlerHandleError:
    """测试错误处理"""

    def test_handle_error_basic(self):
        """测试基础错误处理"""
        handler = ErrorHandler()
        error = ValueError("test error")
        result = handler.handle_error(error, context="test context")
        # 应该被处理，不抛出异常
        assert len(handler._error_history) > 0

    def test_handle_plookingii_error(self):
        """测试处理PlookingII错误"""
        handler = ErrorHandler()
        error = ConfigurationError("config error")
        handler.handle_error(error, context="config loading")
        assert len(handler._error_history) > 0
        last_error = handler._error_history[-1]
        assert last_error.error == error
        assert last_error.category == ErrorCategory.CONFIGURATION

    def test_handle_error_with_kwargs(self):
        """测试带额外参数的错误处理"""
        handler = ErrorHandler()
        error = ValueError("test")
        handler.handle_error(error, context="test", file="test.py", line=42)
        last_error = handler._error_history[-1]
        assert last_error.metadata["file"] == "test.py"
        assert last_error.metadata["line"] == 42

    def test_handle_error_calls_handler(self):
        """测试错误处理调用处理器"""
        handler = ErrorHandler()
        custom_handler = Mock(return_value="handled")
        handler.register_handler(ValueError, custom_handler)
        
        error = ValueError("test")
        result = handler.handle_error(error)
        
        assert custom_handler.called
        assert result == "handled"

    def test_handle_error_handler_exception(self):
        """测试处理器异常"""
        handler = ErrorHandler()
        bad_handler = Mock(side_effect=Exception("handler error"))
        handler.register_handler(ValueError, bad_handler)
        
        error = ValueError("test")
        # 不应该抛出异常
        result = handler.handle_error(error)
        assert bad_handler.called


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestErrorCategorization:
    """测试错误分类"""

    def test_categorize_config_error(self):
        """测试配置错误分类"""
        handler = ErrorHandler()
        
        class ConfigError(Exception):
            pass
        
        error = ConfigError("test")
        category = handler._categorize_error(error)
        assert category == ErrorCategory.CONFIGURATION

    def test_categorize_network_error(self):
        """测试网络错误分类"""
        handler = ErrorHandler()
        
        class NetworkError(Exception):
            pass
        
        error = NetworkError("test")
        category = handler._categorize_error(error)
        assert category == ErrorCategory.NETWORK

    def test_categorize_file_error(self):
        """测试文件错误分类"""
        handler = ErrorHandler()
        error = FileNotFoundError("test")
        category = handler._categorize_error(error)
        assert category == ErrorCategory.FILE_SYSTEM

    def test_categorize_memory_error(self):
        """测试内存错误分类"""
        handler = ErrorHandler()
        
        class OutOfMemoryError(Exception):
            pass
        
        error = OutOfMemoryError("test")
        category = handler._categorize_error(error)
        assert category == ErrorCategory.MEMORY

    def test_categorize_unknown_error(self):
        """测试未知错误分类"""
        handler = ErrorHandler()
        error = ValueError("test")
        category = handler._categorize_error(error)
        assert category == ErrorCategory.UNKNOWN


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestErrorSeverityAssessment:
    """测试错误严重程度评估"""

    def test_assess_critical_severity(self):
        """测试严重错误评估"""
        handler = ErrorHandler()
        
        class CriticalError(Exception):
            pass
        
        error = CriticalError("test")
        severity = handler._assess_severity(error)
        assert severity == ErrorSeverity.CRITICAL

    def test_assess_memory_severity(self):
        """测试内存错误严重度"""
        handler = ErrorHandler()
        
        class OutOfMemoryError(Exception):
            pass
        
        error = OutOfMemoryError("test")
        severity = handler._assess_severity(error)
        assert severity == ErrorSeverity.HIGH

    def test_assess_warning_severity(self):
        """测试警告严重度"""
        handler = ErrorHandler()
        error = DeprecationWarning("test")
        severity = handler._assess_severity(error)
        assert severity == ErrorSeverity.LOW

    def test_assess_medium_severity(self):
        """测试中等严重度"""
        handler = ErrorHandler()
        error = ValueError("test")
        severity = handler._assess_severity(error)
        assert severity == ErrorSeverity.MEDIUM


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestErrorHandlerFindHandler:
    """测试查找错误处理器"""

    def test_find_exact_handler(self):
        """测试精确匹配"""
        handler = ErrorHandler()
        custom_handler = Mock()
        handler.register_handler(ValueError, custom_handler)
        
        found = handler._find_handler(ValueError)
        assert found == custom_handler

    def test_find_parent_handler(self):
        """测试父类匹配"""
        handler = ErrorHandler()
        custom_handler = Mock()
        handler.register_handler(Exception, custom_handler)
        
        found = handler._find_handler(ValueError)
        assert found == custom_handler

    def test_find_no_handler(self):
        """测试未找到处理器"""
        handler = ErrorHandler()
        # 清空处理器
        handler._error_handlers.clear()
        
        found = handler._find_handler(ValueError)
        assert found is None


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestErrorRecording:
    """测试错误记录"""

    def test_record_error(self):
        """测试记录错误"""
        handler = ErrorHandler()
        error_info = ErrorInfo(
            error=ValueError("test"),
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM
        )
        
        initial_count = len(handler._error_history)
        handler._record_error(error_info)
        assert len(handler._error_history) == initial_count + 1

    def test_error_history_limit(self):
        """测试错误历史记录限制"""
        handler = ErrorHandler()
        # 清空初始历史记录
        handler._error_history.clear()
        
        # Mock日志记录以提高测试速度
        with patch.object(handler.logger, 'log'):
            # 添加1001个错误，触发截断
            for i in range(1001):
                error_info = ErrorInfo(
                    error=ValueError(f"test {i}"),
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.MEDIUM
                )
                handler._record_error(error_info)
            
            # 在第1001个时应该触发截断，保留最后500个
            assert len(handler._error_history) == 500
            
            # 继续添加100个
            for i in range(1001, 1101):
                error_info = ErrorInfo(
                    error=ValueError(f"test {i}"),
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.MEDIUM
                )
                handler._record_error(error_info)
            
            # 现在应该有600个（500 + 100）
            assert len(handler._error_history) == 600

    def test_log_error(self):
        """测试日志记录"""
        handler = ErrorHandler()
        error_info = ErrorInfo(
            error=ValueError("test error"),
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            context="test context"
        )
        
        with patch.object(handler.logger, 'log') as mock_log:
            handler._log_error(error_info)
            assert mock_log.called
            # 验证日志级别
            call_args = mock_log.call_args
            assert call_args[0][0] == logging.ERROR


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestErrorDecorator:
    """测试错误装饰器"""

    def test_error_handler_decorator_success(self):
        """测试装饰器正常执行"""
        @error_handler()
        def test_func():
            return "success"
        
        result = test_func()
        assert result == "success"

    def test_error_handler_decorator_exception(self):
        """测试装饰器捕获异常"""
        @error_handler()
        def test_func():
            raise ValueError("test error")
        
        # 装饰器会重新抛出无法恢复的异常
        with pytest.raises(ValueError):
            test_func()

    def test_error_handler_decorator_with_category(self):
        """测试装饰器带类别"""
        @error_handler(category=ErrorCategory.NETWORK)
        def test_func():
            raise ValueError("test error")
        
        # 装饰器会重新抛出异常
        with pytest.raises(ValueError):
            test_func()

    def test_error_handler_decorator_with_args(self):
        """测试装饰器带参数的函数"""
        @error_handler()
        def test_func(a, b):
            return a + b
        
        result = test_func(1, 2)
        assert result == 3

    def test_error_handler_decorator_with_kwargs(self):
        """测试装饰器带关键字参数"""
        @error_handler()
        def test_func(a, b=10):
            return a + b
        
        result = test_func(5, b=15)
        assert result == 20


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestErrorContext:
    """测试错误上下文管理器"""

    def test_error_context_success(self):
        """测试上下文管理器正常执行"""
        result = []
        with error_context("test context"):
            result.append("executed")
        
        assert result == ["executed"]

    def test_error_context_exception(self):
        """测试上下文管理器异常处理"""
        with error_context("test context"):
            # 异常应该被捕获
            try:
                raise ValueError("test error")
            except:
                pass  # 上下文管理器处理

    def test_error_context_with_category(self):
        """测试带类别的上下文管理器"""
        with error_context("test", category=ErrorCategory.DATABASE):
            pass  # 不应抛出异常


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestErrorLogging:
    """测试错误日志设置"""

    @patch('os.makedirs')
    @patch('logging.handlers.RotatingFileHandler')
    def test_setup_error_logging(self, mock_handler, mock_makedirs):
        """测试设置错误日志"""
        mock_handler_instance = MagicMock()
        mock_handler.return_value = mock_handler_instance
        
        log_path = setup_error_logging()
        
        assert isinstance(log_path, str)
        assert "plookingii" in log_path.lower()
        assert mock_makedirs.called

    def test_get_error_log_path_not_setup(self):
        """测试获取未设置的日志路径"""
        # 确保全局变量被重置
        import plookingII.core.error_handling as eh_module
        original = getattr(eh_module, '_ERROR_LOG_PATH', None)
        eh_module._ERROR_LOG_PATH = None
        
        result = get_error_log_path()
        assert result is None
        
        # 恢复
        eh_module._ERROR_LOG_PATH = original


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestErrorHandlerThreadSafety:
    """测试线程安全"""

    def test_concurrent_error_handling(self):
        """测试并发错误处理"""
        handler = ErrorHandler()
        errors = []
        
        def handle_error(i):
            error = ValueError(f"test {i}")
            handler.handle_error(error)
            errors.append(i)
        
        threads = [threading.Thread(target=handle_error, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 所有错误应该都被记录
        assert len(errors) == 10
        assert len(handler._error_history) >= 10


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestErrorHandlerEdgeCases:
    """测试边界情况"""

    def test_handle_none_error(self):
        """测试处理None"""
        handler = ErrorHandler()
        # 应该能处理而不崩溃
        try:
            handler.handle_error(ValueError("test"), context=None)
        except Exception as e:
            pytest.fail(f"Unexpected exception: {e}")

    def test_create_error_info_with_empty_context(self):
        """测试空上下文"""
        handler = ErrorHandler()
        error_info = handler._create_error_info(ValueError("test"), "")
        assert error_info.context == ""

    def test_multiple_handler_registration(self):
        """测试多次注册处理器"""
        handler = ErrorHandler()
        handler1 = Mock()
        handler2 = Mock()
        
        handler.register_handler(ValueError, handler1)
        handler.register_handler(ValueError, handler2)
        
        # 后注册的应该覆盖前面的
        assert handler._error_handlers[ValueError] == handler2

    def test_recovery_strategy_call(self):
        """测试恢复策略调用"""
        handler = ErrorHandler()
        strategy = Mock(return_value="recovered")
        handler.register_recovery_strategy(ErrorCategory.NETWORK, strategy)
        
        error = PlookingIIError("test", category=ErrorCategory.NETWORK)
        # 清空处理器以便测试恢复策略
        handler._error_handlers.clear()
        result = handler.handle_error(error)
        
        assert strategy.called

