"""
测试 utils/robust_error_handler.py 模块

测试目标：达到85%+覆盖率
"""

import time
from unittest.mock import patch

import pytest

from plookingII.utils.robust_error_handler import (
    ErrorRecoveryStrategy,
    RobustErrorHandler,
    auto_retry,
    boundary_check,
    get_error_handler,
    safe_call,
)


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestErrorRecoveryStrategy:
    """测试错误恢复策略"""

    def test_init(self):
        """测试初始化"""
        strategy = ErrorRecoveryStrategy(max_retries=5, retry_delay=0.2)
        assert strategy.max_retries == 5
        assert strategy.retry_delay == 0.2

    def test_should_retry(self):
        """测试是否应该重试"""
        strategy = ErrorRecoveryStrategy(max_retries=3)

        assert strategy.should_retry(Exception(), 0) is True
        assert strategy.should_retry(Exception(), 1) is True
        assert strategy.should_retry(Exception(), 2) is True
        assert strategy.should_retry(Exception(), 3) is False

    def test_get_retry_delay(self):
        """测试获取重试延迟"""
        strategy = ErrorRecoveryStrategy(retry_delay=0.1)

        # 指数退避
        assert strategy.get_retry_delay(0) == 0.1
        assert strategy.get_retry_delay(1) == 0.2
        assert strategy.get_retry_delay(2) == 0.4
        assert strategy.get_retry_delay(3) == 0.8

    def test_on_error(self):
        """测试错误回调"""
        strategy = ErrorRecoveryStrategy()

        with patch("plookingII.utils.robust_error_handler.logger") as mock_logger:
            strategy.on_error(ValueError("test"), {"function": "test_func"})
            mock_logger.error.assert_called_once()

    def test_on_retry(self):
        """测试重试回调"""
        strategy = ErrorRecoveryStrategy()

        with patch("plookingII.utils.robust_error_handler.logger") as mock_logger:
            strategy.on_retry(ValueError("test"), 1, {"function": "test_func"})
            mock_logger.warning.assert_called_once()

    def test_on_failure(self):
        """测试失败回调"""
        strategy = ErrorRecoveryStrategy()

        with patch("plookingII.utils.robust_error_handler.logger") as mock_logger:
            strategy.on_failure(ValueError("test"), {"function": "test_func"})
            mock_logger.error.assert_called_once()


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestRobustErrorHandler:
    """测试鲁棒性错误处理器"""

    def test_init(self):
        """测试初始化"""
        handler = RobustErrorHandler()
        assert handler.default_strategy is not None
        assert len(handler.recovery_strategies) == 0
        assert len(handler.error_stats) == 0

    def test_register_strategy(self):
        """测试注册策略"""
        handler = RobustErrorHandler()
        strategy = ErrorRecoveryStrategy(max_retries=5)

        handler.register_strategy(ValueError, strategy)
        assert ValueError in handler.recovery_strategies

    def test_get_strategy_registered(self):
        """测试获取已注册的策略"""
        handler = RobustErrorHandler()
        custom_strategy = ErrorRecoveryStrategy(max_retries=5)
        handler.register_strategy(ValueError, custom_strategy)

        strategy = handler.get_strategy(ValueError("test"))
        assert strategy == custom_strategy

    def test_get_strategy_default(self):
        """测试获取默认策略"""
        handler = RobustErrorHandler()

        strategy = handler.get_strategy(RuntimeError("test"))
        assert strategy == handler.default_strategy

    def test_handle_with_retry_success(self):
        """测试成功执行"""
        handler = RobustErrorHandler()

        def test_func(x):
            return x * 2

        result = handler.handle_with_retry(test_func, 5)
        assert result == 10

    def test_handle_with_retry_with_failures(self):
        """测试带失败的重试"""
        handler = RobustErrorHandler()
        handler.default_strategy.max_retries = 3
        handler.default_strategy.retry_delay = 0.01

        call_count = []

        def test_func():
            call_count.append(1)
            if len(call_count) < 3:
                raise ValueError("Not ready")
            return "success"

        result = handler.handle_with_retry(test_func)
        assert result == "success"
        assert len(call_count) == 3

    def test_handle_with_retry_all_fail(self):
        """测试所有重试都失败"""
        handler = RobustErrorHandler()
        handler.default_strategy.max_retries = 2
        handler.default_strategy.retry_delay = 0.01

        def test_func():
            raise ValueError("Always fails")

        result = handler.handle_with_retry(test_func, fallback="fallback")
        assert result == "fallback"

    def test_handle_with_retry_with_context(self):
        """测试带上下文的重试"""
        handler = RobustErrorHandler()

        result = handler.handle_with_retry(lambda: 42, context={"operation": "test"})
        assert result == 42

    def test_handle_with_retry_error_stats(self):
        """测试错误统计"""
        handler = RobustErrorHandler()
        handler.default_strategy.max_retries = 1
        handler.default_strategy.retry_delay = 0.01

        def test_func():
            raise ValueError("Test error")

        handler.handle_with_retry(test_func, fallback=None)

        stats = handler.get_error_stats()
        assert stats["total_errors"] > 0

    def test_safe_call_success(self):
        """测试安全调用成功"""
        handler = RobustErrorHandler()

        result = handler.safe_call(lambda x: x * 2, 5)
        assert result == 10

    def test_safe_call_with_exception(self):
        """测试安全调用异常处理"""
        handler = RobustErrorHandler()

        def test_func():
            raise ValueError("Test error")

        result = handler.safe_call(test_func, fallback=42)
        assert result == 42

    def test_safe_call_no_logging(self):
        """测试禁用日志的安全调用"""
        handler = RobustErrorHandler()

        with patch("plookingII.utils.robust_error_handler.logger") as mock_logger:
            result = handler.safe_call(lambda: 1 / 0, fallback=0, log_error=False)
            mock_logger.error.assert_not_called()
            assert result == 0

    def test_get_error_stats(self):
        """测试获取错误统计"""
        handler = RobustErrorHandler()

        # 触发一些错误
        handler.safe_call(lambda: 1 / 0, fallback=0)
        handler.safe_call(lambda: [][0], fallback=0)

        stats = handler.get_error_stats()
        assert "total_errors" in stats
        assert "error_counts" in stats
        assert "recent_errors" in stats
        assert stats["total_errors"] == 2

    def test_clear_stats(self):
        """测试清空统计"""
        handler = RobustErrorHandler()

        # 触发错误
        handler.safe_call(lambda: 1 / 0, fallback=0)

        # 清空统计
        handler.clear_stats()

        stats = handler.get_error_stats()
        assert stats["total_errors"] == 0


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestAutoRetryDecorator:
    """测试自动重试装饰器"""

    def test_auto_retry_success(self):
        """测试成功执行"""

        @auto_retry()
        def test_func(x):
            return x * 2

        result = test_func(5)
        assert result == 10

    def test_auto_retry_with_failures(self):
        """测试带失败的重试"""
        call_count = []

        @auto_retry(max_retries=3, retry_delay=0.01)
        def test_func():
            call_count.append(1)
            if len(call_count) < 3:
                raise ValueError("Not ready")
            return "success"

        result = test_func()
        assert result == "success"
        assert len(call_count) == 3

    def test_auto_retry_all_fail(self):
        """测试所有重试都失败"""

        @auto_retry(max_retries=2, retry_delay=0.01, fallback="fallback")
        def test_func():
            raise ValueError("Always fails")

        result = test_func()
        assert result == "fallback"

    def test_auto_retry_specific_exceptions(self):
        """测试只重试特定异常"""
        call_count = []

        @auto_retry(max_retries=2, retry_delay=0.01, exceptions=(ValueError,))
        def test_func():
            call_count.append(1)
            if len(call_count) == 1:
                raise ValueError("Retry this")
            raise TypeError("Don't retry this")

        # TypeError 应该立即抛出
        with pytest.raises(TypeError):
            test_func()

    def test_auto_retry_preserves_function_name(self):
        """测试保留函数名"""

        @auto_retry()
        def my_function():
            return "test"

        assert my_function.__name__ == "my_function"


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestSafeCallDecorator:
    """测试安全调用装饰器"""

    def test_safe_call_success(self):
        """测试成功执行"""

        @safe_call()
        def test_func(x):
            return x * 2

        result = test_func(5)
        assert result == 10

    def test_safe_call_with_exception(self):
        """测试异常处理"""

        @safe_call(fallback=42)
        def test_func():
            raise ValueError("Test error")

        result = test_func()
        assert result == 42

    def test_safe_call_no_logging(self):
        """测试禁用日志"""

        @safe_call(fallback=0, log_error=False)
        def test_func():
            raise ValueError("Test error")

        with patch("plookingII.utils.robust_error_handler.logger") as mock_logger:
            result = test_func()
            mock_logger.error.assert_not_called()
            assert result == 0

    def test_safe_call_preserves_function_name(self):
        """测试保留函数名"""

        @safe_call()
        def my_function():
            return "test"

        assert my_function.__name__ == "my_function"


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestBoundaryCheckDecorator:
    """测试边界检查装饰器"""

    def test_boundary_check_pass(self):
        """测试边界检查通过"""

        @boundary_check(lambda x: x > 0, fallback=0)
        def test_func(x):
            return x * 2

        result = test_func(5)
        assert result == 10

    def test_boundary_check_fail(self):
        """测试边界检查失败"""

        @boundary_check(lambda x: x > 0, fallback=0)
        def test_func(x):
            return x * 2

        result = test_func(-5)
        assert result == 0

    def test_boundary_check_exception(self):
        """测试检查函数异常"""

        def bad_check(*args, **kwargs):
            raise RuntimeError("Check failed")

        @boundary_check(bad_check, fallback=-1)
        def test_func(x):
            return x * 2

        result = test_func(5)
        assert result == -1

    def test_boundary_check_with_kwargs(self):
        """测试带关键字参数的边界检查"""

        @boundary_check(lambda x, y: x > 0 and y > 0, fallback=0)
        def test_func(x, y):
            return x + y

        assert test_func(5, 10) == 15
        assert test_func(-5, 10) == 0

    def test_boundary_check_preserves_function_name(self):
        """测试保留函数名"""

        @boundary_check(lambda x: True, fallback=0)
        def my_function(x):
            return x

        assert my_function.__name__ == "my_function"


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestGetErrorHandler:
    """测试全局错误处理器"""

    def test_get_error_handler_singleton(self):
        """测试单例模式"""
        handler1 = get_error_handler()
        handler2 = get_error_handler()

        assert handler1 is handler2

    def test_get_error_handler_returns_handler(self):
        """测试返回处理器实例"""
        handler = get_error_handler()
        assert isinstance(handler, RobustErrorHandler)


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestEdgeCases:
    """测试边缘情况"""

    def test_nested_decorators(self):
        """测试嵌套装饰器"""

        @safe_call(fallback=0)
        @auto_retry(max_retries=2, retry_delay=0.01)
        def test_func():
            return 42

        result = test_func()
        assert result == 42

    def test_error_recovery_with_no_retries(self):
        """测试零重试"""
        strategy = ErrorRecoveryStrategy(max_retries=0)
        assert not strategy.should_retry(Exception(), 0)

    def test_handler_with_multiple_error_types(self):
        """测试多种错误类型"""
        handler = RobustErrorHandler()

        # 触发不同类型的错误
        handler.safe_call(lambda: 1 / 0, fallback=0)  # ZeroDivisionError
        handler.safe_call(lambda: [][0], fallback=0)  # IndexError
        handler.safe_call(lambda: {}["key"], fallback=0)  # KeyError

        stats = handler.get_error_stats()
        assert stats["total_errors"] == 3
        assert len(stats["error_counts"]) == 3

    def test_decorator_with_class_method(self):
        """测试装饰类方法"""

        class TestClass:
            @auto_retry(max_retries=2, retry_delay=0.01)
            def method(self, x):
                if x < 0:
                    raise ValueError("Negative")
                return x * 2

        obj = TestClass()
        assert obj.method(5) == 10

    def test_exponential_backoff_timing(self):
        """测试指数退避时间"""
        call_times = []

        @auto_retry(max_retries=3, retry_delay=0.1)
        def test_func():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("Not ready")
            return "success"

        result = test_func()
        assert result == "success"

        # 验证延迟递增
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            # 第二次延迟应该大约是第一次的两倍
            assert delay2 > delay1

    def test_error_stats_last_error(self):
        """测试最后一个错误信息"""
        handler = RobustErrorHandler()

        def test_func():
            raise ValueError("Test error message")

        handler.safe_call(test_func, fallback=None)

        stats = handler.get_error_stats()

        # 验证基本统计信息
        assert "total_errors" in stats
        assert "error_counts" in stats
        assert "recent_errors" in stats
        assert stats["total_errors"] >= 1

        # safe_call 不会记录详细的last_errors（只有handle_with_retry才会）
        # 所以我们只检查error_counts
        assert len(stats["error_counts"]) > 0
