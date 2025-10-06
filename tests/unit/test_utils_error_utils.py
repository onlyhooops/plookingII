"""
测试 utils/error_utils.py 模块

测试目标：达到90%+覆盖率
"""

import time
from unittest.mock import patch

import pytest

from plookingII.utils.error_utils import (
    ErrorCollector,
    handle_exceptions,
    retry_on_failure,
    safe_execute,
    suppress_exceptions,
    validate_parameter,
)


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestSafeExecute:
    """测试安全执行函数"""

    def test_safe_execute_success(self):
        """测试成功执行"""

        def test_func(x, y):
            return x + y

        result = safe_execute(test_func, 1, 2)
        assert result == 3

    def test_safe_execute_with_kwargs(self):
        """测试带关键字参数的执行"""

        def test_func(x, y=10):
            return x + y

        result = safe_execute(test_func, 5, y=20)
        assert result == 25

    def test_safe_execute_exception_with_default(self):
        """测试异常时返回默认值"""

        def test_func():
            raise ValueError("Test error")

        result = safe_execute(test_func, default=42)
        assert result == 42

    def test_safe_execute_exception_no_default(self):
        """测试异常时返回None"""

        def test_func():
            raise ValueError("Test error")

        result = safe_execute(test_func)
        assert result is None

    def test_safe_execute_with_logging(self):
        """测试错误日志记录"""

        def test_func():
            raise ValueError("Test error")

        with patch("plookingII.utils.error_utils.logger") as mock_logger:
            safe_execute(test_func, log_error=True, context="test context")
            mock_logger.debug.assert_called_once()

    def test_safe_execute_without_logging(self):
        """测试禁用错误日志"""

        def test_func():
            raise ValueError("Test error")

        with patch("plookingII.utils.error_utils.logger") as mock_logger:
            safe_execute(test_func, log_error=False)
            mock_logger.debug.assert_not_called()

    def test_safe_execute_with_context(self):
        """测试带上下文的错误处理"""

        def test_func():
            raise ValueError("Test error")

        result = safe_execute(test_func, default="fallback", context="test operation")
        assert result == "fallback"


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestHandleExceptionsDecorator:
    """测试异常处理装饰器"""

    def test_handle_exceptions_success(self):
        """测试正常执行"""

        @handle_exceptions(default_return=0)
        def test_func(x):
            return x * 2

        result = test_func(5)
        assert result == 10

    def test_handle_exceptions_with_exception(self):
        """测试异常处理"""

        @handle_exceptions(default_return=0)
        def test_func():
            raise ValueError("Test error")

        result = test_func()
        assert result == 0

    def test_handle_exceptions_log_levels(self):
        """测试不同的日志级别"""
        log_levels = ["debug", "info", "warning", "error", "critical"]

        for level in log_levels:

            @handle_exceptions(default_return=None, log_level=level)
            def test_func():
                raise ValueError("Test error")

            with patch("plookingII.utils.error_utils.logger") as mock_logger:
                test_func()
                # 验证对应的日志方法被调用
                log_method = getattr(mock_logger, level.lower())
                log_method.assert_called_once()

    def test_handle_exceptions_with_context(self):
        """测试带上下文的异常处理"""

        @handle_exceptions(default_return=None, context="test context")
        def test_func():
            raise ValueError("Test error")

        with patch("plookingII.utils.error_utils.logger") as mock_logger:
            test_func()
            mock_logger.debug.assert_called_once()

    def test_handle_exceptions_reraise(self):
        """测试重新抛出异常"""

        @handle_exceptions(default_return=0, reraise=True)
        def test_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            test_func()

    def test_handle_exceptions_preserves_function_name(self):
        """测试装饰器保留函数名"""

        @handle_exceptions()
        def test_func():
            return "test"

        assert test_func.__name__ == "test_func"

    def test_handle_exceptions_with_args_and_kwargs(self):
        """测试带参数和关键字参数的函数"""

        @handle_exceptions(default_return=0)
        def test_func(x, y, z=10):
            return x + y + z

        result = test_func(1, 2, z=3)
        assert result == 6


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestSuppressExceptionsDecorator:
    """测试抑制异常装饰器"""

    def test_suppress_exceptions_success(self):
        """测试正常执行"""

        @suppress_exceptions(ValueError, default_return=0)
        def test_func(x):
            return x * 2

        result = test_func(5)
        assert result == 10

    def test_suppress_exceptions_suppressed(self):
        """测试抑制指定异常"""

        @suppress_exceptions(ValueError, default_return=42)
        def test_func():
            raise ValueError("Test error")

        result = test_func()
        assert result == 42

    def test_suppress_exceptions_not_suppressed(self):
        """测试不抑制其他异常"""

        @suppress_exceptions(ValueError, default_return=0)
        def test_func():
            raise TypeError("Test error")

        with pytest.raises(TypeError):
            test_func()

    def test_suppress_exceptions_multiple_types(self):
        """测试抑制多种异常类型"""

        @suppress_exceptions(ValueError, TypeError, default_return=0)
        def test_func(error_type):
            if error_type == "value":
                raise ValueError("Value error")
            raise TypeError("Type error")

        result1 = test_func("value")
        result2 = test_func("type")
        assert result1 == 0
        assert result2 == 0

    def test_suppress_exceptions_with_logging(self):
        """测试带日志的异常抑制"""

        @suppress_exceptions(ValueError, log_error=True, default_return=None)
        def test_func():
            raise ValueError("Test error")

        with patch("plookingII.utils.error_utils.logger") as mock_logger:
            test_func()
            mock_logger.debug.assert_called_once()

    def test_suppress_exceptions_without_logging(self):
        """测试禁用日志的异常抑制"""

        @suppress_exceptions(ValueError, log_error=False, default_return=None)
        def test_func():
            raise ValueError("Test error")

        with patch("plookingII.utils.error_utils.logger") as mock_logger:
            test_func()
            mock_logger.debug.assert_not_called()

    def test_suppress_exceptions_with_context(self):
        """测试带上下文的异常抑制"""

        @suppress_exceptions(ValueError, context="test operation", default_return=None)
        def test_func():
            raise ValueError("Test error")

        result = test_func()
        assert result is None


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestRetryOnFailureDecorator:
    """测试重试装饰器"""

    def test_retry_success_first_attempt(self):
        """测试第一次尝试成功"""
        call_count = []

        @retry_on_failure(max_retries=3, delay=0.1)
        def test_func():
            call_count.append(1)
            return "success"

        result = test_func()
        assert result == "success"
        assert len(call_count) == 1

    def test_retry_success_after_failures(self):
        """测试多次尝试后成功"""
        call_count = []

        @retry_on_failure(max_retries=3, delay=0.1)
        def test_func():
            call_count.append(1)
            if len(call_count) < 3:
                raise ValueError("Not ready")
            return "success"

        result = test_func()
        assert result == "success"
        assert len(call_count) == 3

    def test_retry_all_attempts_fail(self):
        """测试所有尝试都失败"""
        call_count = []

        @retry_on_failure(max_retries=2, delay=0.1)
        def test_func():
            call_count.append(1)
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            test_func()

        assert len(call_count) == 3  # 初始 + 2次重试

    def test_retry_with_backoff(self):
        """测试指数退避"""
        call_times = []

        @retry_on_failure(max_retries=2, delay=0.1, backoff_factor=2.0)
        def test_func():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("Not ready")
            return "success"

        test_func()

        # 验证延迟时间递增
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            assert delay2 > delay1

    def test_retry_specific_exceptions(self):
        """测试只重试特定异常"""
        call_count = []

        @retry_on_failure(max_retries=2, delay=0.1, exceptions=(ValueError,))
        def test_func():
            call_count.append(1)
            if len(call_count) == 1:
                raise ValueError("Retry this")
            raise TypeError("Don't retry this")

        with pytest.raises(TypeError):
            test_func()

        assert len(call_count) == 2

    def test_retry_preserves_function_name(self):
        """测试装饰器保留函数名"""

        @retry_on_failure()
        def test_func():
            return "test"

        assert test_func.__name__ == "test_func"


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestErrorCollector:
    """测试错误收集器"""

    def test_error_collector_init(self):
        """测试初始化"""
        collector = ErrorCollector(max_errors=50)
        assert collector.max_errors == 50
        assert len(collector.errors) == 0

    def test_add_error(self):
        """测试添加错误"""
        collector = ErrorCollector()
        error = ValueError("Test error")

        collector.add_error(error, context="test context")

        assert len(collector.errors) == 1
        assert collector.errors[0]["type"] == "ValueError"
        assert collector.errors[0]["message"] == "Test error"
        assert collector.errors[0]["context"] == "test context"

    def test_add_multiple_errors(self):
        """测试添加多个错误"""
        collector = ErrorCollector()

        for i in range(5):
            collector.add_error(ValueError(f"Error {i}"))

        assert len(collector.errors) == 5

    def test_max_errors_limit(self):
        """测试错误数量限制"""
        collector = ErrorCollector(max_errors=10)

        # 添加超过限制的错误
        for i in range(20):
            collector.add_error(ValueError(f"Error {i}"))

        # 应该只保留一半
        assert len(collector.errors) <= 10

    def test_has_errors(self):
        """测试是否有错误"""
        collector = ErrorCollector()

        assert not collector.has_errors()

        collector.add_error(ValueError("Test"))
        assert collector.has_errors()

    def test_get_error_summary_empty(self):
        """测试空错误摘要"""
        collector = ErrorCollector()

        summary = collector.get_error_summary()
        assert summary["total"] == 0
        assert summary["types"] == {}

    def test_get_error_summary_with_errors(self):
        """测试有错误的摘要"""
        collector = ErrorCollector()

        collector.add_error(ValueError("Error 1"))
        collector.add_error(ValueError("Error 2"))
        collector.add_error(TypeError("Error 3"))

        summary = collector.get_error_summary()
        assert summary["total"] == 3
        assert summary["types"]["ValueError"] == 2
        assert summary["types"]["TypeError"] == 1
        assert summary["latest"]["type"] == "TypeError"

    def test_clear_errors(self):
        """测试清空错误"""
        collector = ErrorCollector()

        collector.add_error(ValueError("Error 1"))
        collector.add_error(TypeError("Error 2"))

        collector.clear()
        assert len(collector.errors) == 0
        assert not collector.has_errors()


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestValidateParameter:
    """测试参数验证函数"""

    def test_validate_parameter_valid(self):
        """测试有效参数"""
        result = validate_parameter("test", "param_name", str)
        assert result is True

    def test_validate_parameter_none_allowed(self):
        """测试允许None"""
        result = validate_parameter(None, "param_name", str, allow_none=True)
        assert result is True

    def test_validate_parameter_none_not_allowed(self):
        """测试不允许None"""
        with pytest.raises(ValueError, match="不能为None"):
            validate_parameter(None, "param_name", str, allow_none=False)

    def test_validate_parameter_type_mismatch(self):
        """测试类型不匹配"""
        with pytest.raises(ValueError, match="类型错误"):
            validate_parameter(123, "param_name", str)

    def test_validate_parameter_no_type_check(self):
        """测试不检查类型"""
        result = validate_parameter(123, "param_name", expected_type=None)
        assert result is True

    def test_validate_parameter_custom_validator_success(self):
        """测试自定义验证成功"""

        def custom_check(value):
            return value > 0

        result = validate_parameter(5, "param_name", int, custom_validator=custom_check)
        assert result is True

    def test_validate_parameter_custom_validator_failure(self):
        """测试自定义验证失败"""

        def custom_check(value):
            return value > 0

        with pytest.raises(ValueError, match="未通过自定义验证"):
            validate_parameter(-5, "param_name", int, custom_validator=custom_check)

    def test_validate_parameter_combined(self):
        """测试组合验证"""

        def is_positive(value):
            return value > 0

        result = validate_parameter(10, "param_name", expected_type=int, allow_none=False, custom_validator=is_positive)
        assert result is True

    def test_validate_parameter_various_types(self):
        """测试各种类型"""
        test_cases = [
            ("string", "param", str, True),
            (123, "param", int, True),
            (12.5, "param", float, True),
            (True, "param", bool, True),
            ([], "param", list, True),
            ({}, "param", dict, True),
        ]

        for value, name, expected_type, should_pass in test_cases:
            if should_pass:
                result = validate_parameter(value, name, expected_type)
                assert result is True


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestEdgeCases:
    """测试边缘情况"""

    def test_nested_decorators(self):
        """测试嵌套装饰器"""

        @handle_exceptions(default_return=0)
        @retry_on_failure(max_retries=2, delay=0.1)
        def test_func():
            return 42

        result = test_func()
        assert result == 42

    def test_exception_in_error_collector(self):
        """测试错误收集器中的异常"""
        collector = ErrorCollector()

        # 添加各种类型的异常
        collector.add_error(ValueError("Value error"))
        collector.add_error(TypeError("Type error"))
        collector.add_error(RuntimeError("Runtime error"))
        collector.add_error(KeyError("Key error"))

        summary = collector.get_error_summary()
        assert summary["total"] == 4
        assert len(summary["types"]) == 4

    def test_safe_execute_with_lambda(self):
        """测试安全执行lambda"""
        result = safe_execute(lambda x: x * 2, 5)
        assert result == 10

    def test_decorator_on_class_method(self):
        """测试装饰类方法"""

        class TestClass:
            @handle_exceptions(default_return=0)
            def method(self, x):
                if x < 0:
                    raise ValueError("Negative value")
                return x * 2

        obj = TestClass()
        assert obj.method(5) == 10
        assert obj.method(-5) == 0

    def test_invalid_log_level(self):
        """测试无效的日志级别"""

        @handle_exceptions(default_return=None, log_level="invalid_level")
        def test_func():
            raise ValueError("Test error")

        # 应该回退到debug级别
        result = test_func()
        assert result is None
