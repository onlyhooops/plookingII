"""
测试 core/cleanup_utils.py

测试清理工具函数，包括：
- safe_call
- safe_method_call
- logged_operation装饰器
- error_context上下文管理器
- validate_and_get
- batch_clear_cache
- unified_status_update
- create_fallback_chain
- 验证器函数
- cleanup_resources
- log_performance装饰器
"""

from unittest.mock import MagicMock, Mock, patch, call
import time

import pytest

from plookingII.core.cleanup_utils import (
    safe_call,
    safe_method_call,
    logged_operation,
    error_context,
    validate_and_get,
    batch_clear_cache,
    unified_status_update,
    create_fallback_chain,
    is_not_none,
    is_not_empty,
    is_callable_attr,
    cleanup_resources,
    log_performance,
)


# ==================== safe_call 测试 ====================


class TestSafeCall:
    """测试safe_call"""

    def test_safe_call_success(self):
        """测试成功调用"""
        def test_func(a, b):
            return a + b
        
        result = safe_call(test_func, 3, 4)
        assert result == 7

    def test_safe_call_with_kwargs(self):
        """测试带关键字参数的调用"""
        def test_func(a, b=10):
            return a * b
        
        result = safe_call(test_func, 5, b=3)
        assert result == 15

    def test_safe_call_exception_default_return(self):
        """测试异常时返回默认值"""
        def test_func():
            raise ValueError("Test error")
        
        result = safe_call(test_func, default_return="default")
        assert result == "default"

    def test_safe_call_exception_custom_error_msg(self):
        """测试自定义错误消息"""
        def test_func():
            raise ValueError("Test error")
        
        with patch('plookingII.core.cleanup_utils.logger') as mock_logger:
            safe_call(test_func, error_msg="Custom error")
            mock_logger.warning.assert_called()
            assert "Custom error" in str(mock_logger.warning.call_args)

    def test_safe_call_exception_default_error_msg(self):
        """测试默认错误消息"""
        def test_func():
            raise ValueError("Test error")
        
        with patch('plookingII.core.cleanup_utils.logger') as mock_logger:
            safe_call(test_func)
            mock_logger.warning.assert_called()


# ==================== safe_method_call 测试 ====================


class TestSafeMethodCall:
    """测试safe_method_call"""

    def test_safe_method_call_success(self):
        """测试成功调用方法"""
        obj = MagicMock()
        obj.test_method.return_value = "success"
        
        result = safe_method_call(obj, "test_method")
        assert result == "success"

    def test_safe_method_call_with_args(self):
        """测试带参数的方法调用"""
        obj = MagicMock()
        obj.test_method.return_value = "result"
        
        result = safe_method_call(obj, "test_method", "arg1", key="value")
        obj.test_method.assert_called_with("arg1", key="value")
        assert result == "result"

    def test_safe_method_call_method_not_exists(self):
        """测试方法不存在"""
        obj = MagicMock(spec=[])
        
        result = safe_method_call(obj, "nonexistent_method", default_return="default")
        assert result == "default"

    def test_safe_method_call_not_callable(self):
        """测试属性不可调用"""
        obj = MagicMock()
        obj.not_callable = "just a string"
        
        result = safe_method_call(obj, "not_callable", default_return="default")
        assert result == "default"

    def test_safe_method_call_exception(self):
        """测试方法调用异常"""
        obj = MagicMock()
        obj.test_method.side_effect = Exception("Method error")
        
        with patch('plookingII.core.cleanup_utils.logger') as mock_logger:
            result = safe_method_call(obj, "test_method", default_return="default")
            assert result == "default"
            mock_logger.warning.assert_called()


# ==================== logged_operation 装饰器测试 ====================


class TestLoggedOperation:
    """测试logged_operation装饰器"""

    def test_logged_operation_success(self):
        """测试成功操作的日志记录"""
        @logged_operation("测试操作")
        def test_func():
            return "success"
        
        with patch('plookingII.core.cleanup_utils.logger') as mock_logger:
            result = test_func()
            assert result == "success"
            assert mock_logger.debug.call_count >= 2  # 开始和完成

    def test_logged_operation_exception(self):
        """测试异常操作的日志记录"""
        @logged_operation("失败操作")
        def test_func():
            raise ValueError("Test error")
        
        with patch('plookingII.core.cleanup_utils.logger') as mock_logger:
            with pytest.raises(ValueError):
                test_func()
            mock_logger.error.assert_called()

    def test_logged_operation_with_args(self):
        """测试带参数的装饰器"""
        @logged_operation("参数操作")
        def test_func(a, b):
            return a + b
        
        with patch('plookingII.core.cleanup_utils.logger'):
            result = test_func(3, 4)
            assert result == 7


# ==================== error_context 上下文管理器测试 ====================


class TestErrorContext:
    """测试error_context上下文管理器"""

    def test_error_context_success(self):
        """测试成功操作"""
        with patch('plookingII.core.cleanup_utils.logger') as mock_logger:
            with error_context("测试上下文"):
                pass
            assert mock_logger.debug.call_count >= 2

    def test_error_context_exception_reraise(self):
        """测试异常重新抛出"""
        with patch('plookingII.core.cleanup_utils.logger') as mock_logger:
            with pytest.raises(ValueError):
                with error_context("失败上下文", reraise=True):
                    raise ValueError("Test error")
            mock_logger.error.assert_called()

    def test_error_context_exception_no_reraise(self):
        """测试异常不重新抛出"""
        with patch('plookingII.core.cleanup_utils.logger') as mock_logger:
            with error_context("失败上下文", reraise=False):
                raise ValueError("Test error")
            mock_logger.error.assert_called()


# ==================== validate_and_get 测试 ====================


class TestValidateAndGet:
    """测试validate_and_get"""

    def test_validate_and_get_success(self):
        """测试成功获取属性"""
        obj = MagicMock()
        obj.test_attr = "value"
        
        result = validate_and_get(obj, "test_attr")
        assert result == "value"

    def test_validate_and_get_with_validator(self):
        """测试带验证器"""
        obj = MagicMock()
        obj.test_attr = 10
        
        result = validate_and_get(obj, "test_attr", validator=lambda x: x > 5)
        assert result == 10

    def test_validate_and_get_validator_fails(self):
        """测试验证器失败"""
        obj = MagicMock()
        obj.test_attr = 3
        
        with patch('plookingII.core.cleanup_utils.logger'):
            result = validate_and_get(obj, "test_attr", validator=lambda x: x > 5, default="default")
            assert result == "default"

    def test_validate_and_get_attr_not_exists(self):
        """测试属性不存在"""
        obj = MagicMock(spec=[])
        
        result = validate_and_get(obj, "nonexistent", default="default")
        assert result == "default"

    def test_validate_and_get_exception(self):
        """测试获取属性异常"""
        obj = MagicMock()
        # 让getattr抛出异常
        type(obj).test_attr = property(lambda self: 1 / 0)
        
        with patch('plookingII.core.cleanup_utils.logger'):
            result = validate_and_get(obj, "test_attr", default="default")
            assert result == "default"


# ==================== batch_clear_cache 测试 ====================


class TestBatchClearCache:
    """测试batch_clear_cache"""

    def test_batch_clear_cache_success(self):
        """测试成功批量清理"""
        cache1 = MagicMock(spec=['clear'])
        cache2 = MagicMock(spec=['clear'])
        
        caches = {"cache1": cache1, "cache2": cache2}
        
        with patch('plookingII.core.cleanup_utils.logger'):
            results = batch_clear_cache(caches)
            
            assert results["cache1"] is True
            assert results["cache2"] is True
            cache1.clear.assert_called_once()
            cache2.clear.assert_called_once()

    def test_batch_clear_cache_different_methods(self):
        """测试不同清理方法"""
        cache1 = MagicMock(spec=['clear_cache'])
        cache2 = MagicMock(spec=['clear'])
        cache3 = MagicMock(spec=['cleanup'])
        
        caches = {"cache1": cache1, "cache2": cache2, "cache3": cache3}
        
        with patch('plookingII.core.cleanup_utils.logger'):
            results = batch_clear_cache(caches)
            
            assert all(results.values())
            cache1.clear_cache.assert_called_once()
            cache2.clear.assert_called_once()
            cache3.cleanup.assert_called_once()

    def test_batch_clear_cache_no_method(self):
        """测试没有清理方法"""
        cache = MagicMock(spec=[])
        
        caches = {"cache": cache}
        
        with patch('plookingII.core.cleanup_utils.logger') as mock_logger:
            results = batch_clear_cache(caches)
            
            assert results["cache"] is False
            mock_logger.warning.assert_called()

    def test_batch_clear_cache_exception(self):
        """测试清理异常"""
        cache = MagicMock(spec=['clear'])
        cache.clear.side_effect = Exception("Clear error")
        
        caches = {"cache": cache}
        
        with patch('plookingII.core.cleanup_utils.logger') as mock_logger:
            results = batch_clear_cache(caches)
            
            assert results["cache"] is False
            mock_logger.warning.assert_called()


# ==================== unified_status_update 测试 ====================


class TestUnifiedStatusUpdate:
    """测试unified_status_update"""

    def test_unified_status_update_success(self):
        """测试成功更新状态"""
        controller1 = MagicMock()
        controller2 = MagicMock()
        
        controllers = {"ctrl1": controller1, "ctrl2": controller2}
        
        with patch('plookingII.core.cleanup_utils.logger'):
            results = unified_status_update(controllers, "Status message")
            
            assert results["ctrl1"] is True
            assert results["ctrl2"] is True
            controller1.set_status_message.assert_called_with("Status message")
            controller2.set_status_message.assert_called_with("Status message")

    def test_unified_status_update_different_methods(self):
        """测试不同更新方法"""
        ctrl1 = MagicMock(spec=['set_status_message'])
        ctrl2 = MagicMock(spec=['update_status_message'])
        ctrl3 = MagicMock(spec=['set_message'])
        
        controllers = {"ctrl1": ctrl1, "ctrl2": ctrl2, "ctrl3": ctrl3}
        
        with patch('plookingII.core.cleanup_utils.logger'):
            results = unified_status_update(controllers, "Message")
            
            assert all(results.values())
            ctrl1.set_status_message.assert_called_once_with("Message")
            ctrl2.update_status_message.assert_called_once_with("Message")
            ctrl3.set_message.assert_called_once_with("Message")

    def test_unified_status_update_no_method(self):
        """测试没有更新方法"""
        controller = MagicMock(spec=[])
        
        controllers = {"ctrl": controller}
        
        with patch('plookingII.core.cleanup_utils.logger') as mock_logger:
            results = unified_status_update(controllers, "Message")
            
            assert results["ctrl"] is False
            mock_logger.warning.assert_called()

    def test_unified_status_update_exception(self):
        """测试更新异常"""
        controller = MagicMock()
        controller.set_status_message.side_effect = Exception("Update error")
        
        controllers = {"ctrl": controller}
        
        with patch('plookingII.core.cleanup_utils.logger') as mock_logger:
            results = unified_status_update(controllers, "Message")
            
            assert results["ctrl"] is False


# ==================== create_fallback_chain 测试 ====================


class TestCreateFallbackChain:
    """测试create_fallback_chain"""

    def test_fallback_chain_first_succeeds(self):
        """测试第一个函数成功"""
        func1 = Mock(return_value="result1")
        func2 = Mock(return_value="result2")
        
        chain = create_fallback_chain(func1, func2)
        result = chain()
        
        assert result == "result1"
        func1.assert_called_once()
        func2.assert_not_called()

    def test_fallback_chain_second_succeeds(self):
        """测试第二个函数成功"""
        def func1():
            raise Exception("Error1")
        
        def func2():
            return "result2"
        
        with patch('plookingII.core.cleanup_utils.logger'):
            chain = create_fallback_chain(func1, func2)
            result = chain()
            
            assert result == "result2"

    def test_fallback_chain_all_fail(self):
        """测试所有函数失败"""
        func1 = Mock(side_effect=Exception("Error1"))
        func2 = Mock(side_effect=Exception("Error2"))
        
        with patch('plookingII.core.cleanup_utils.logger'):
            chain = create_fallback_chain(func1, func2)
            
            with pytest.raises(Exception):
                chain()

    def test_fallback_chain_with_args(self):
        """测试带参数的回退链"""
        def func1(*args, **kwargs):
            raise Exception("Error")
        
        def func2(*args, **kwargs):
            return f"result: {args}, {kwargs}"
        
        with patch('plookingII.core.cleanup_utils.logger'):
            chain = create_fallback_chain(func1, func2)
            result = chain("arg1", key="value")
            
            assert "arg1" in result
            assert "value" in result


# ==================== 验证器函数测试 ====================


class TestValidators:
    """测试验证器函数"""

    def test_is_not_none_true(self):
        """测试is_not_none返回True"""
        assert is_not_none("value") is True
        assert is_not_none(0) is True
        assert is_not_none("") is True

    def test_is_not_none_false(self):
        """测试is_not_none返回False"""
        assert is_not_none(None) is False

    def test_is_not_empty_true(self):
        """测试is_not_empty返回True"""
        assert is_not_empty("value") is True
        assert is_not_empty([1, 2, 3]) is True
        assert is_not_empty({"key": "value"}) is True
        assert is_not_empty(123) is True  # 没有__len__

    def test_is_not_empty_false(self):
        """测试is_not_empty返回False"""
        assert is_not_empty(None) is False
        assert is_not_empty("") is False
        assert is_not_empty([]) is False
        assert is_not_empty({}) is False

    def test_is_callable_attr_true(self):
        """测试is_callable_attr返回True"""
        obj = MagicMock()
        obj.method = MagicMock()
        
        assert is_callable_attr(obj, "method") is True

    def test_is_callable_attr_false(self):
        """测试is_callable_attr返回False"""
        # 创建一个有非可调用属性的对象
        class TestObj:
            not_method = "value"
        
        obj = TestObj()
        
        assert is_callable_attr(obj, "not_method") is False
        assert is_callable_attr(obj, "nonexistent") is False


# ==================== cleanup_resources 测试 ====================


class TestCleanupResources:
    """测试cleanup_resources"""

    def test_cleanup_resources_success(self):
        """测试成功清理资源"""
        resource1 = MagicMock()
        resource2 = MagicMock()
        
        with patch('plookingII.core.cleanup_utils.safe_call') as mock_safe_call:
            cleanup_resources(resource1, resource2)
            
            assert mock_safe_call.call_count >= 2  # 至少调用了2次

    def test_cleanup_resources_empty(self):
        """测试清理空资源列表"""
        with patch('plookingII.core.cleanup_utils.safe_call') as mock_safe_call:
            cleanup_resources()
            
            mock_safe_call.assert_not_called()


# ==================== log_performance 装饰器测试 ====================


class TestLogPerformance:
    """测试log_performance装饰器"""

    def test_log_performance_fast_operation(self):
        """测试快速操作（<100ms）不记录"""
        @log_performance
        def fast_func():
            return "fast"
        
        with patch('plookingII.core.cleanup_utils.logger') as mock_logger:
            result = fast_func()
            assert result == "fast"
            # 快速操作不应该记录
            mock_logger.debug.assert_not_called()

    def test_log_performance_slow_operation(self):
        """测试慢速操作（>100ms）记录"""
        @log_performance
        def slow_func():
            time.sleep(0.15)
            return "slow"
        
        with patch('plookingII.core.cleanup_utils.logger') as mock_logger:
            result = slow_func()
            assert result == "slow"
            mock_logger.debug.assert_called()

    def test_log_performance_exception(self):
        """测试异常操作记录"""
        @log_performance
        def error_func():
            raise ValueError("Test error")
        
        with patch('plookingII.core.cleanup_utils.logger') as mock_logger:
            with pytest.raises(ValueError):
                error_func()
            mock_logger.warning.assert_called()


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    def test_complete_workflow(self):
        """测试完整工作流"""
        # 创建对象
        obj = MagicMock()
        obj.data = "test_value"
        obj.process = Mock(return_value="processed")
        
        # 验证并获取
        data = validate_and_get(obj, "data", validator=is_not_empty)
        assert data == "test_value"
        
        # 安全调用方法
        result = safe_method_call(obj, "process")
        assert result == "processed"

    def test_cache_and_status_workflow(self):
        """测试缓存和状态更新工作流"""
        # 创建缓存和控制器
        cache1 = MagicMock()
        cache2 = MagicMock()
        controller = MagicMock()
        
        # 批量清理缓存
        with patch('plookingII.core.cleanup_utils.logger'):
            results = batch_clear_cache({"cache1": cache1, "cache2": cache2})
            assert all(results.values())
            
            # 更新状态
            status_results = unified_status_update({"ctrl": controller}, "清理完成")
            assert status_results["ctrl"] is True

