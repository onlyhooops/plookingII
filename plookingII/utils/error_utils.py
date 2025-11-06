"""
错误处理辅助工具模块

提供常用的错误处理装饰器和辅助函数，简化重复的错误处理代码。

主要功能：
    - 错误处理装饰器
    - 安全调用包装器
    - 错误记录辅助函数
    - 重试机制

Author: PlookingII Team
"""

import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from plookingII.config.constants import APP_NAME

logger = logging.getLogger(APP_NAME)

T = TypeVar("T")


def safe_execute(
    func: Callable[..., T], *args, default: T = None, log_error: bool = True, context: str = "", **kwargs
) -> T:
    """安全执行函数，捕获异常并返回默认值

    Args:
        func: 要执行的函数
        *args: 函数参数
        default: 异常时返回的默认值
        log_error: 是否记录错误日志
        context: 错误上下文描述
        **kwargs: 函数关键字参数

    Returns:
        T: 函数返回值或默认值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            error_msg = f"执行函数 {func.__name__} 失败"
            if context:
                error_msg += f" ({context})"
            error_msg += f": {e}"
            logger.debug(error_msg, exc_info=True)
        return default


def handle_exceptions(default_return: Any = None, log_level: str = "debug", context: str = "", reraise: bool = False):
    """异常处理装饰器

    Args:
        default_return: 异常时返回的默认值
        log_level: 日志级别 (debug, info, warning, error, critical)
        context: 错误上下文描述
        reraise: 是否重新抛出异常

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 记录错误日志
                error_msg = f"函数 {func.__name__} 执行失败"
                if context:
                    error_msg += f" ({context})"
                error_msg += f": {e}"

                log_func = getattr(logger, log_level.lower(), logger.debug)
                log_func(error_msg, exc_info=True)

                if reraise:
                    raise
                return default_return

        return wrapper

    return decorator


def suppress_exceptions(*exception_types, log_error: bool = True, context: str = "", default_return: Any = None):
    """抑制指定异常类型的装饰器

    Args:
        *exception_types: 要抑制的异常类型
        log_error: 是否记录错误日志
        context: 错误上下文描述
        default_return: 异常时返回的默认值

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                if log_error:
                    error_msg = f"函数 {func.__name__} 发生预期异常"
                    if context:
                        error_msg += f" ({context})"
                    error_msg += f": {e}"
                    logger.debug(error_msg)
                return default_return
            except Exception:
                # 其他异常继续抛出
                raise

        return wrapper

    return decorator


def retry_on_failure(
    max_retries: int = 3, delay: float = 1.0, backoff_factor: float = 2.0, exceptions: tuple = (Exception,)
):
    """失败重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff_factor: 延迟递增因子
        exceptions: 需要重试的异常类型

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    if attempt == max_retries:
                        logger.exception("函数 %s 重试 {max_retries} 次后仍然失败: {e}", func.__name__)
                        raise

                    logger.debug("函数 %s 第 {attempt + 1} 次尝试失败，{current_delay}秒后重试: {e}", func.__name__)

                    import time

                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            return None

        return wrapper

    return decorator


class ErrorCollector:
    """错误收集器，用于批量收集和处理错误"""

    def __init__(self, max_errors: int = 100):
        self.errors = []
        self.max_errors = max_errors

    def add_error(self, error: Exception, context: str = ""):
        """添加错误

        Args:
            error: 异常对象
            context: 错误上下文
        """
        error_info = {"error": error, "context": context, "type": type(error).__name__, "message": str(error)}

        self.errors.append(error_info)

        # 限制错误数量
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors // 2 :]

    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0

    def get_error_summary(self) -> dict:
        """获取错误摘要

        Returns:
            dict: 错误统计信息
        """
        if not self.errors:
            return {"total": 0, "types": {}}

        error_types = {}
        for error_info in self.errors:
            error_type = error_info["type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return {"total": len(self.errors), "types": error_types, "latest": self.errors[-1] if self.errors else None}

    def clear(self):
        """清空错误记录"""
        self.errors.clear()


def validate_parameter(
    param: Any,
    param_name: str,
    expected_type: type | None = None,
    allow_none: bool = False,
    custom_validator: Callable | None = None,
) -> bool:
    """参数验证辅助函数

    Args:
        param: 参数值
        param_name: 参数名称
        expected_type: 期望的类型
        allow_none: 是否允许None值
        custom_validator: 自定义验证函数

    Returns:
        bool: 参数是否有效

    Raises:
        ValueError: 参数无效时抛出
    """
    # 检查None值
    if param is None:
        if allow_none:
            return True
        raise ValueError(f"参数 {param_name} 不能为None")

    # 检查类型
    if expected_type is not None and not isinstance(param, expected_type):
        raise ValueError(f"参数 {param_name} 类型错误，期望 {expected_type.__name__}，实际 {type(param).__name__}")

    # 自定义验证
    if custom_validator is not None and not custom_validator(param):
        raise ValueError(f"参数 {param_name} 未通过自定义验证")

    return True
