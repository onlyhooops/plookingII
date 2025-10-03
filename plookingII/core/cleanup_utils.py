"""
清理工具 - 用于清理重复代码和统一常用操作

该模块提供常用的清理和工具函数，用于：
- 清理重复的错误处理模式
- 统一日志记录格式
- 简化常见的try-except模式
- 提供通用的验证函数
"""

import functools
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

from ..config.constants import APP_NAME
from ..imports import logging

logger = logging.getLogger(APP_NAME)


def safe_call(func: Callable, *args, default_return=None, error_msg: str | None = None, **kwargs) -> Any:
    """安全调用函数 - 统一的异常处理模式

    Args:
        func: 要调用的函数
        *args: 函数参数
        default_return: 异常时的默认返回值
        error_msg: 自定义错误消息
        **kwargs: 函数关键字参数

    Returns:
        Any: 函数返回值或默认值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if error_msg:
            logger.warning(f"{error_msg}: {e}")
        else:
            logger.warning(f"调用 {func.__name__} 失败: {e}")
        return default_return


def safe_method_call(obj: Any, method_name: str, *args, default_return=None, **kwargs) -> Any:
    """安全调用对象方法 - 统一的方法调用模式

    Args:
        obj: 目标对象
        method_name: 方法名称
        *args: 方法参数
        default_return: 异常时的默认返回值
        **kwargs: 方法关键字参数

    Returns:
        Any: 方法返回值或默认值
    """
    try:
        if hasattr(obj, method_name):
            method = getattr(obj, method_name)
            if callable(method):
                return method(*args, **kwargs)
        return default_return
    except Exception as e:
        logger.warning(f"调用 {obj.__class__.__name__}.{method_name} 失败: {e}")
        return default_return


def logged_operation(operation_name: str):
    """操作日志装饰器 - 统一的操作日志记录

    Args:
        operation_name: 操作名称

    Returns:
        装饰器函数
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                logger.debug(f"开始 {operation_name}")
                result = func(*args, **kwargs)
                logger.debug(f"完成 {operation_name}")
                return result
            except Exception as e:
                logger.error(f"{operation_name} 失败: {e}")
                raise
        return wrapper
    return decorator


@contextmanager
def error_context(operation_name: str, reraise: bool = True):
    """错误上下文管理器 - 统一的错误处理上下文

    Args:
        operation_name: 操作名称
        reraise: 是否重新抛出异常

    Yields:
        None
    """
    try:
        logger.debug(f"开始 {operation_name}")
        yield
        logger.debug(f"完成 {operation_name}")
    except Exception as e:
        logger.error(f"{operation_name} 失败: {e}")
        if reraise:
            raise


def validate_and_get(obj: Any, attr_name: str, validator: Callable | None = None, default: Any = None) -> Any:
    """验证并获取对象属性 - 统一的属性验证模式

    Args:
        obj: 目标对象
        attr_name: 属性名称
        validator: 验证函数
        default: 默认值

    Returns:
        Any: 属性值或默认值
    """
    try:
        if not hasattr(obj, attr_name):
            return default

        value = getattr(obj, attr_name)

        if validator and not validator(value):
            logger.warning(f"属性 {attr_name} 验证失败")
            return default

        return value
    except Exception as e:
        logger.warning(f"获取属性 {attr_name} 失败: {e}")
        return default


def batch_clear_cache(cache_objects: dict[str, Any]) -> dict[str, bool]:
    """批量清理缓存 - 统一的缓存清理模式

    Args:
        cache_objects: 缓存对象字典 {名称: 对象}

    Returns:
        Dict[str, bool]: 清理结果 {名称: 成功/失败}
    """
    results = {}

    for name, cache_obj in cache_objects.items():
        try:
            # 尝试多种清理方法
            if hasattr(cache_obj, "clear_cache"):
                cache_obj.clear_cache()
                results[name] = True
            elif hasattr(cache_obj, "clear"):
                cache_obj.clear()
                results[name] = True
            elif hasattr(cache_obj, "cleanup"):
                cache_obj.cleanup()
                results[name] = True
            else:
                logger.warning(f"缓存对象 {name} 没有清理方法")
                results[name] = False

        except Exception as e:
            logger.warning(f"清理缓存 {name} 失败: {e}")
            results[name] = False

    success_count = sum(results.values())
    total_count = len(results)
    logger.info(f"批量缓存清理完成: {success_count}/{total_count}")

    return results


def unified_status_update(status_controllers: dict[str, Any], message: str, **kwargs) -> dict[str, bool]:
    """统一状态更新 - 统一的状态更新模式

    Args:
        status_controllers: 状态控制器字典 {名称: 控制器}
        message: 状态消息
        **kwargs: 额外状态参数

    Returns:
        Dict[str, bool]: 更新结果 {名称: 成功/失败}
    """
    results = {}

    for name, controller in status_controllers.items():
        try:
            # 尝试多种状态更新方法
            if hasattr(controller, "set_status_message"):
                controller.set_status_message(message)
                results[name] = True
            elif hasattr(controller, "update_status_message"):
                controller.update_status_message(message)
                results[name] = True
            elif hasattr(controller, "set_message"):
                controller.set_message(message)
                results[name] = True
            else:
                logger.warning(f"状态控制器 {name} 没有状态更新方法")
                results[name] = False

        except Exception as e:
            logger.warning(f"更新状态 {name} 失败: {e}")
            results[name] = False

    return results


def create_fallback_chain(*functions):
    """创建回退调用链 - 统一的回退模式

    Args:
        *functions: 函数列表，按优先级排序

    Returns:
        Callable: 回退调用函数
    """
    def fallback_caller(*args, **kwargs):
        for i, func in enumerate(functions):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if i == len(functions) - 1:  # 最后一个函数
                    logger.error(f"所有回退函数都失败，最后错误: {e}")
                    raise
                logger.debug(f"函数 {func.__name__} 失败，尝试回退: {e}")
        return None

    return fallback_caller


# 常用的验证器函数
def is_not_none(value: Any) -> bool:
    """验证值不为None"""
    return value is not None


def is_not_empty(value: Any) -> bool:
    """验证值不为空"""
    if value is None:
        return False
    if hasattr(value, "__len__"):
        return len(value) > 0
    return True


def is_callable_attr(obj: Any, attr_name: str) -> bool:
    """验证对象属性是否可调用"""
    return hasattr(obj, attr_name) and callable(getattr(obj, attr_name))


# 常用的清理函数
def cleanup_resources(*resources):
    """清理资源列表"""
    for resource in resources:
        safe_call(getattr, resource, "close", error_msg=f"关闭资源 {resource}")
        safe_call(getattr, resource, "cleanup", error_msg=f"清理资源 {resource}")
        safe_call(getattr, resource, "shutdown", error_msg=f"关闭资源 {resource}")


def log_performance(func):
    """性能日志装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            if duration > 0.1:  # 只记录超过100ms的操作
                logger.debug(f"{func.__name__} 执行时间: {duration:.3f}s")
            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            logger.warning(f"{func.__name__} 执行失败 (耗时: {duration:.3f}s): {e}")
            raise
    return wrapper
