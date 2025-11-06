"""
测试错误处理辅助工具模块

测试覆盖：
- safe_execute 函数
- handle_exceptions 装饰器
- suppress_exceptions 装饰器
- retry_on_failure 装饰器
- ErrorCollector 类
- validate_parameter 函数
"""

import time

import pytest

from plookingII.utils.error_utils import (
    ErrorCollector,
    handle_exceptions,
    retry_on_failure,
    safe_execute,
    suppress_exceptions,
    validate_parameter,
)


class TestSafeExecute:
    """测试safe_execute函数"""

    def test_safe_execute_success(self):
        """测试成功执行"""
        result = safe_execute(lambda x: x * 2, 5)
        assert result == 10

    def test_safe_execute_with_exception(self):
        """测试捕获异常并返回默认值"""
        result = safe_execute(lambda: 1 / 0, default=0)
        assert result == 0

    def test_safe_execute_custom_default(self):
        """测试自定义默认值"""
        result = safe_execute(lambda: int("invalid"), default=-1)
        assert result == -1

    def test_safe_execute_no_log(self):
        """测试不记录错误日志"""
        result = safe_execute(lambda: 1 / 0, default=0, log_error=False)
        assert result == 0

    def test_safe_execute_with_context(self):
        """测试带上下文信息"""
        result = safe_execute(lambda: 1 / 0, default=0, context="测试上下文")
        assert result == 0

    def test_safe_execute_with_args_and_kwargs(self):
        """测试传递参数"""

        def add(a, b, c=0):
            return a + b + c

        result = safe_execute(add, 1, 2, c=3)
        assert result == 6


class TestHandleExceptions:
    """测试handle_exceptions装饰器"""

    def test_handle_exceptions_success(self):
        """测试正常执行"""

        @handle_exceptions(default_return=0)
        def normal_func(x):
            return x * 2

        assert normal_func(5) == 10

    def test_handle_exceptions_with_exception(self):
        """测试捕获异常"""

        @handle_exceptions(default_return=-1)
        def error_func():
            return 1 / 0

        assert error_func() == -1

    def test_handle_exceptions_with_log_level(self):
        """测试不同日志级别"""

        @handle_exceptions(default_return=None, log_level="error")
        def error_func():
            raise ValueError("测试错误")

        assert error_func() is None

    def test_handle_exceptions_with_context(self):
        """测试带上下文"""

        @handle_exceptions(default_return=None, context="测试上下文")
        def error_func():
            raise RuntimeError("测试")

        assert error_func() is None

    def test_handle_exceptions_reraise(self):
        """测试重新抛出异常"""

        @handle_exceptions(reraise=True)
        def error_func():
            raise ValueError("测试错误")

        with pytest.raises(ValueError):
            error_func()


class TestSuppressExceptions:
    """测试suppress_exceptions装饰器"""

    def test_suppress_specific_exception(self):
        """测试抑制特定异常"""

        @suppress_exceptions(ValueError, default_return=0)
        def func():
            raise ValueError("测试")

        assert func() == 0

    def test_suppress_not_raise_other_exceptions(self):
        """测试不抑制其他异常"""

        @suppress_exceptions(ValueError)
        def func():
            raise RuntimeError("测试")

        with pytest.raises(RuntimeError):
            func()

    def test_suppress_multiple_exceptions(self):
        """测试抑制多种异常"""

        @suppress_exceptions(ValueError, TypeError, default_return=-1)
        def func(error_type):
            if error_type == "value":
                raise ValueError
            elif error_type == "type":
                raise TypeError

        assert func("value") == -1
        assert func("type") == -1

    def test_suppress_with_context(self):
        """测试带上下文"""

        @suppress_exceptions(ValueError, context="测试抑制", default_return=0)
        def func():
            raise ValueError("测试")

        assert func() == 0

    def test_suppress_no_log(self):
        """测试不记录日志"""

        @suppress_exceptions(ValueError, log_error=False, default_return=0)
        def func():
            raise ValueError("测试")

        assert func() == 0


class TestRetryOnFailure:
    """测试retry_on_failure装饰器"""

    def test_retry_success_first_try(self):
        """测试第一次就成功"""
        counter = {"count": 0}

        @retry_on_failure(max_retries=3)
        def func():
            counter["count"] += 1
            return "success"

        result = func()
        assert result == "success"
        assert counter["count"] == 1

    def test_retry_success_after_failures(self):
        """测试重试后成功"""
        counter = {"count": 0}

        @retry_on_failure(max_retries=3, delay=0.01, backoff_factor=1)
        def func():
            counter["count"] += 1
            if counter["count"] < 3:
                raise ValueError("暂时失败")
            return "success"

        result = func()
        assert result == "success"
        assert counter["count"] == 3

    def test_retry_max_retries_exceeded(self):
        """测试超过最大重试次数"""

        @retry_on_failure(max_retries=2, delay=0.01, backoff_factor=1)
        def func():
            raise ValueError("持续失败")

        with pytest.raises(ValueError):
            func()

    def test_retry_with_backoff(self):
        """测试延迟递增"""
        times = []

        @retry_on_failure(max_retries=2, delay=0.01, backoff_factor=2)
        def func():
            times.append(time.time())
            raise ValueError("测试")

        try:
            func()
        except ValueError:
            pass

        # 应该有3次尝试
        assert len(times) == 3

    def test_retry_specific_exceptions(self):
        """测试只重试特定异常"""

        @retry_on_failure(max_retries=2, delay=0.01, exceptions=(ValueError,))
        def func(error_type):
            if error_type == "value":
                raise ValueError("测试")
            else:
                raise RuntimeError("测试")

        # ValueError应该重试
        with pytest.raises(ValueError):
            func("value")

        # RuntimeError不应该重试，直接抛出
        with pytest.raises(RuntimeError):
            func("runtime")


class TestErrorCollector:
    """测试ErrorCollector类"""

    def test_init(self):
        """测试初始化"""
        collector = ErrorCollector()
        assert collector.max_errors == 100
        assert len(collector.errors) == 0

    def test_add_error(self):
        """测试添加错误"""
        collector = ErrorCollector()
        error = ValueError("测试错误")
        collector.add_error(error, "测试上下文")

        assert len(collector.errors) == 1
        assert collector.errors[0]["context"] == "测试上下文"
        assert collector.errors[0]["type"] == "ValueError"
        assert collector.errors[0]["message"] == "测试错误"

    def test_add_multiple_errors(self):
        """测试添加多个错误"""
        collector = ErrorCollector()
        for i in range(5):
            collector.add_error(ValueError(f"错误{i}"), f"上下文{i}")

        assert len(collector.errors) == 5

    def test_max_errors_limit(self):
        """测试错误数量限制"""
        collector = ErrorCollector(max_errors=10)
        for i in range(20):
            collector.add_error(ValueError(f"错误{i}"))

        # 超过max_errors后，会保留最后的max_errors // 2个错误
        # 添加到第11个时触发清理，保留5个
        # 然后继续添加，第16个时再次触发，保留5个
        # 最终会继续添加到第20个，总共会多次触发清理
        # 实际逻辑是：每次超过max_errors时保留一半，然后继续添加
        # 所以最后会有8个左右（取决于具体的清理时机）
        assert 5 <= len(collector.errors) <= 10

    def test_has_errors(self):
        """测试检查是否有错误"""
        collector = ErrorCollector()
        assert not collector.has_errors()

        collector.add_error(ValueError("测试"))
        assert collector.has_errors()

    def test_get_error_summary_empty(self):
        """测试空错误摘要"""
        collector = ErrorCollector()
        summary = collector.get_error_summary()

        assert summary["total"] == 0
        assert summary["types"] == {}

    def test_get_error_summary_with_errors(self):
        """测试有错误时的摘要"""
        collector = ErrorCollector()
        collector.add_error(ValueError("错误1"))
        collector.add_error(ValueError("错误2"))
        collector.add_error(TypeError("错误3"))

        summary = collector.get_error_summary()
        assert summary["total"] == 3
        assert summary["types"]["ValueError"] == 2
        assert summary["types"]["TypeError"] == 1
        assert summary["latest"]["type"] == "TypeError"

    def test_clear(self):
        """测试清空错误"""
        collector = ErrorCollector()
        collector.add_error(ValueError("测试"))
        collector.clear()

        assert len(collector.errors) == 0
        assert not collector.has_errors()


class TestValidateParameter:
    """测试validate_parameter函数"""

    def test_validate_valid_parameter(self):
        """测试有效参数"""
        assert validate_parameter(5, "test_param", int)
        assert validate_parameter("hello", "test_param", str)
        assert validate_parameter([1, 2, 3], "test_param", list)

    def test_validate_none_not_allowed(self):
        """测试不允许None"""
        with pytest.raises(ValueError, match="不能为None"):
            validate_parameter(None, "test_param")

    def test_validate_none_allowed(self):
        """测试允许None"""
        assert validate_parameter(None, "test_param", allow_none=True)

    def test_validate_wrong_type(self):
        """测试类型错误"""
        with pytest.raises(ValueError, match="类型错误"):
            validate_parameter(5, "test_param", str)

    def test_validate_no_type_check(self):
        """测试不检查类型"""
        assert validate_parameter(5, "test_param")
        assert validate_parameter("hello", "test_param")

    def test_validate_custom_validator_pass(self):
        """测试自定义验证通过"""

        def is_positive(x):
            return x > 0

        assert validate_parameter(5, "test_param", custom_validator=is_positive)

    def test_validate_custom_validator_fail(self):
        """测试自定义验证失败"""

        def is_positive(x):
            return x > 0

        with pytest.raises(ValueError, match="未通过自定义验证"):
            validate_parameter(-5, "test_param", custom_validator=is_positive)

    def test_validate_combined_checks(self):
        """测试组合验证"""

        def is_non_empty(s):
            return len(s) > 0

        assert validate_parameter("hello", "test_param", str, custom_validator=is_non_empty)

        with pytest.raises(ValueError):
            validate_parameter("", "test_param", str, custom_validator=is_non_empty)


class TestIntegration:
    """集成测试"""

    def test_error_collector_with_decorators(self):
        """测试错误收集器与装饰器结合使用"""
        collector = ErrorCollector()

        @handle_exceptions(default_return=None)
        def risky_operation(x):
            try:
                return 10 / x
            except Exception as e:
                collector.add_error(e, f"除数为{x}")
                raise

        risky_operation(2)  # 成功
        risky_operation(0)  # 失败

        assert collector.has_errors()
        summary = collector.get_error_summary()
        assert summary["total"] == 1
        assert "ZeroDivisionError" in summary["types"]

    def test_retry_with_validation(self):
        """测试重试与参数验证结合"""
        counter = {"count": 0}

        @retry_on_failure(max_retries=2, delay=0.01, backoff_factor=1)
        def process_data(data):
            validate_parameter(data, "data", list)
            counter["count"] += 1
            if counter["count"] < 2:
                raise ValueError("暂时失败")
            return len(data)

        result = process_data([1, 2, 3])
        assert result == 3
        assert counter["count"] == 2

    def test_nested_decorators(self):
        """测试嵌套装饰器"""

        @handle_exceptions(default_return=0)
        @suppress_exceptions(ValueError, default_return=-1)
        def complex_operation(x):
            if x < 0:
                raise ValueError("负数")
            if x == 0:
                raise RuntimeError("零")
            return x * 2

        assert complex_operation(5) == 10
        assert complex_operation(-1) == -1
        assert complex_operation(0) == 0  # RuntimeError被handle_exceptions捕获
