#!/usr/bin/env python3
"""
鲁棒性错误处理器

提供增强的错误处理和恢复机制，确保应用程序在异常情况下也能正常运行。

主要特性：
- 优雅的错误恢复
- 自动重试机制
- 边界情况处理
- 详细的错误日志
- 用户友好的错误提示

Author: PlookingII Team
"""

import functools
import logging
import time
import traceback
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from ..config.constants import APP_NAME

logger = logging.getLogger(APP_NAME)


class ErrorRecoveryStrategy:
    """错误恢复策略基类"""

    def __init__(self, max_retries: int = 3, retry_delay: float = 0.1):
        """初始化恢复策略

        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """判断是否应该重试

        Args:
            exception: 捕获的异常
            attempt: 当前尝试次数

        Returns:
            是否应该重试
        """
        return attempt < self.max_retries

    def get_retry_delay(self, attempt: int) -> float:
        """获取重试延迟时间

        Args:
            attempt: 当前尝试次数

        Returns:
            延迟时间（秒）
        """
        # 指数退避
        return self.retry_delay * (2**attempt)

    def on_error(self, exception: Exception, context: dict):
        """错误回调

        Args:
            exception: 捕获的异常
            context: 错误上下文信息
        """
        logger.error("Error in %s: %s", context.get('function', 'unknown'), exception, exc_info=True)

    def on_retry(self, exception: Exception, attempt: int, context: dict):
        """重试回调

        Args:
            exception: 捕获的异常
            attempt: 当前尝试次数
            context: 错误上下文信息
        """
        logger.warning(
            "Retrying %s (attempt %s/%s) due to: %s",
            context.get('function', 'unknown'), attempt, self.max_retries, exception
        )

    def on_failure(self, exception: Exception, context: dict):
        """最终失败回调

        Args:
            exception: 捕获的异常
            context: 错误上下文信息
        """
        logger.error("All retries failed for %s: %s", context.get('function', 'unknown'), exception, exc_info=True)


class RobustErrorHandler:
    """鲁棒性错误处理器

    提供自动重试、错误恢复和详细日志记录。
    """

    def __init__(self):
        """初始化错误处理器"""
        self.recovery_strategies = {}
        self.error_stats = defaultdict(int)
        self.last_errors = {}

        # 默认恢复策略
        self.default_strategy = ErrorRecoveryStrategy()

    def register_strategy(self, error_type: type[Exception], strategy: ErrorRecoveryStrategy):
        """注册错误恢复策略

        Args:
            error_type: 异常类型
            strategy: 恢复策略
        """
        self.recovery_strategies[error_type] = strategy

    def get_strategy(self, exception: Exception) -> ErrorRecoveryStrategy:
        """获取异常对应的恢复策略

        Args:
            exception: 异常对象

        Returns:
            恢复策略
        """
        for error_type, strategy in self.recovery_strategies.items():
            if isinstance(exception, error_type):
                return strategy
        return self.default_strategy

    def handle_with_retry(
        self, func: Callable, *args, fallback: Any = None, context: dict | None = None, **kwargs
    ) -> Any:
        """执行函数并自动处理错误和重试

        Args:
            func: 要执行的函数
            *args: 函数位置参数
            fallback: 失败时的回退值
            context: 错误上下文信息
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果或回退值
        """
        if context is None:
            context = {"function": func.__name__}
        else:
            context = {**context, "function": func.__name__}

        attempt = 0
        last_exception = None

        while True:
            try:
                result = func(*args, **kwargs)

                # 成功执行，重置错误计数
                if context["function"] in self.error_stats:
                    del self.error_stats[context["function"]]

                return result

            except Exception as e:
                attempt += 1

                # 更新错误统计
                error_key = f"{context['function']}:{type(e).__name__}"
                self.error_stats[error_key] += 1
                self.last_errors[error_key] = {
                    "exception": str(e),
                    "time": time.time(),
                    "traceback": traceback.format_exc(),
                }

                # 获取恢复策略
                strategy = self.get_strategy(e)

                # 检查是否应该重试
                if strategy.should_retry(e, attempt):
                    strategy.on_retry(e, attempt, context)
                    delay = strategy.get_retry_delay(attempt - 1)
                    time.sleep(delay)
                    continue
                # 不再重试，执行失败回调
                strategy.on_failure(e, context)
                break

        # 所有重试都失败，返回回退值
        return fallback

    def safe_call(self, func: Callable, *args, fallback: Any = None, log_error: bool = True, **kwargs) -> Any:
        """安全调用函数，捕获所有异常

        Args:
            func: 要调用的函数
            *args: 函数位置参数
            fallback: 失败时的回退值
            log_error: 是否记录错误
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果或回退值
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if log_error:
                logger.error("Error in safe_call to %s: %s", func.__name__, e, exc_info=True)

            # 更新错误统计
            error_key = f"{func.__name__}:{type(e).__name__}"
            self.error_stats[error_key] += 1

            return fallback

    def get_error_stats(self) -> dict:
        """获取错误统计信息

        Returns:
            错误统计字典
        """
        return {
            "total_errors": sum(self.error_stats.values()),
            "error_counts": dict(self.error_stats),
            "recent_errors": self.last_errors,
        }

    def clear_stats(self):
        """清空错误统计"""
        self.error_stats.clear()
        self.last_errors.clear()


# 装饰器：自动重试
def auto_retry(
    max_retries: int = 3,
    retry_delay: float = 0.1,
    fallback: Any = None,
    exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """自动重试装饰器

    Args:
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
        fallback: 失败时的回退值
        exceptions: 要捕获的异常类型
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_retries:
                        logger.error("All %s retries failed for %s: %s", max_retries, func.__name__, e, exc_info=True)
                        return fallback

                    logger.warning("Retry %s/{max_retries} for {func.__name__} due to: {e}", attempt)
                    time.sleep(retry_delay * (2 ** (attempt - 1)))  # 指数退避

            return fallback

        return wrapper

    return decorator


# 装饰器：安全调用
def safe_call(fallback: Any = None, log_error: bool = True):
    """安全调用装饰器

    Args:
        fallback: 失败时的回退值
        log_error: 是否记录错误
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error("Error in %s: %s", func.__name__, e, exc_info=True)
                return fallback

        return wrapper

    return decorator


# 装饰器：边界检查
def boundary_check(check_func: Callable[[Any], bool], fallback: Any = None, error_msg: str = "Boundary check failed"):
    """边界检查装饰器

    Args:
        check_func: 检查函数，返回True表示通过
        fallback: 检查失败时的回退值
        error_msg: 错误消息
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 检查参数边界
            try:
                if not check_func(*args, **kwargs):
                    logger.warning("%s for {func.__name__}", error_msg)
                    return fallback
            except Exception as e:
                logger.error("Boundary check error in %s: {e}", func.__name__)
                return fallback

            # 执行函数
            return func(*args, **kwargs)

        return wrapper

    return decorator


# 全局错误处理器实例
_global_error_handler = None


def get_error_handler() -> RobustErrorHandler:
    """获取全局错误处理器实例

    Returns:
        错误处理器实例
    """
    global _global_error_handler

    if _global_error_handler is None:
        _global_error_handler = RobustErrorHandler()

    return _global_error_handler


__all__ = [
    "ErrorRecoveryStrategy",
    "RobustErrorHandler",
    "auto_retry",
    "boundary_check",
    "get_error_handler",
    "safe_call",
]
