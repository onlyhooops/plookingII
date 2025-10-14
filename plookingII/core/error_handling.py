"""
统一错误处理模块

提供统一的错误处理机制，减少重复的错误处理代码，
提高错误处理的一致性和可维护性。

主要功能：
- 统一异常类型定义
- 错误处理装饰器
- 错误恢复机制
- 错误报告和日志
- 错误统计和分析

Author: PlookingII Team
"""

import functools
import logging
import os
import sys
import threading
import traceback
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from logging.handlers import RotatingFileHandler
from typing import Any


class ErrorSeverity(Enum):
    """错误严重程度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误类别"""

    SYSTEM = "system"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    FILE_SYSTEM = "file_system"
    MEMORY = "memory"
    IMAGE_PROCESSING = "image_processing"
    UI = "ui"
    DATABASE = "database"
    CACHE = "cache"
    PERFORMANCE = "performance"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """错误信息"""

    error: Exception
    category: ErrorCategory
    severity: ErrorSeverity
    context: str = ""
    timestamp: float = field(default_factory=lambda: __import__("time").time())
    stack_trace: str = ""
    recovery_action: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PlookingIIError(Exception):
    """PlookingII基础异常类"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        **kwargs,
    ):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.metadata = kwargs


class ConfigurationError(PlookingIIError):
    """配置错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM, **kwargs)


class ImageProcessingError(PlookingIIError):
    """图像处理错误"""

    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, **kwargs):
        super().__init__(message, ErrorCategory.IMAGE_PROCESSING, severity, **kwargs)


class MemoryError(PlookingIIError):
    """内存错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, ErrorCategory.MEMORY, ErrorSeverity.HIGH, **kwargs)


class FileSystemError(PlookingIIError):
    """文件系统错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM, **kwargs)


class UIError(PlookingIIError):
    """UI错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, ErrorCategory.UI, ErrorSeverity.MEDIUM, **kwargs)


class DragDropError(PlookingIIError):
    """拖拽操作错误"""

    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.LOW, **kwargs):
        super().__init__(message, ErrorCategory.UI, severity, **kwargs)


class FolderValidationError(PlookingIIError):
    """文件夹验证错误"""

    def __init__(self, message: str, folder_path: str = "", **kwargs):
        super().__init__(message, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW, folder_path=folder_path, **kwargs)


class CacheError(PlookingIIError):
    """缓存错误"""

    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.LOW, **kwargs):
        super().__init__(message, ErrorCategory.CACHE, severity, **kwargs)


class ErrorHandler:
    """错误处理器"""

    def __init__(self):
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._error_history: list[ErrorInfo] = []
        self._error_handlers: dict[type, Callable] = {}
        self._recovery_strategies: dict[ErrorCategory, Callable] = {}
        self._lock = threading.RLock()

        # 注册默认错误处理器
        self._register_default_handlers()

    def _register_default_handlers(self):
        """注册默认错误处理器"""
        # 配置错误处理器
        self.register_handler(ConfigurationError, self._handle_configuration_error)

        # 图像处理错误处理器
        self.register_handler(ImageProcessingError, self._handle_image_processing_error)

        # 内存错误处理器
        self.register_handler(MemoryError, self._handle_memory_error)

        # 文件系统错误处理器
        self.register_handler(FileSystemError, self._handle_file_system_error)

        # 通用错误处理器
        self.register_handler(Exception, self._handle_generic_error)

    def register_handler(self, exception_type: type, handler: Callable):
        """注册错误处理器

        Args:
            exception_type: 异常类型
            handler: 处理函数
        """
        self._error_handlers[exception_type] = handler

    def register_recovery_strategy(self, category: ErrorCategory, strategy: Callable):
        """注册恢复策略

        Args:
            category: 错误类别
            strategy: 恢复策略函数
        """
        self._recovery_strategies[category] = strategy

    def handle_error(self, error: Exception, context: str = "", **kwargs) -> Any:
        """处理错误

        Args:
            error: 异常对象
            context: 错误上下文
            **kwargs: 额外参数

        Returns:
            Any: 处理结果
        """
        # 创建错误信息
        error_info = self._create_error_info(error, context, **kwargs)

        # 记录错误
        self._record_error(error_info)

        # 查找并执行错误处理器
        handler = self._find_handler(type(error))
        if handler:
            try:
                return handler(error_info)
            except Exception as handler_error:
                self.logger.error("Error handler failed: %s", handler_error)

        # 尝试恢复
        return self._attempt_recovery(error_info)

    def _create_error_info(self, error: Exception, context: str, **kwargs) -> ErrorInfo:
        """创建错误信息

        Args:
            error: 异常对象
            context: 错误上下文
            **kwargs: 额外参数

        Returns:
            ErrorInfo: 错误信息
        """
        # 确定错误类别和严重程度
        if isinstance(error, PlookingIIError):
            category = error.category
            severity = error.severity
            metadata = error.metadata.copy()
        else:
            category = self._categorize_error(error)
            severity = self._assess_severity(error)
            metadata = {}

        # 合并元数据
        metadata.update(kwargs)

        return ErrorInfo(
            error=error,
            category=category,
            severity=severity,
            context=context,
            stack_trace=traceback.format_exc(),
            metadata=metadata,
        )

    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """分类错误

        Args:
            error: 异常对象

        Returns:
            ErrorCategory: 错误类别
        """
        error_type = type(error).__name__.lower()

        if "config" in error_type or "setting" in error_type:
            return ErrorCategory.CONFIGURATION
        if "network" in error_type or "connection" in error_type:
            return ErrorCategory.NETWORK
        if "file" in error_type or "path" in error_type or "directory" in error_type:
            return ErrorCategory.FILE_SYSTEM
        if "memory" in error_type or "outofmemory" in error_type:
            return ErrorCategory.MEMORY
        if "image" in error_type or "pil" in error_type or "quartz" in error_type:
            return ErrorCategory.IMAGE_PROCESSING
        if "ui" in error_type or "window" in error_type or "view" in error_type:
            return ErrorCategory.UI
        if "database" in error_type or "sql" in error_type:
            return ErrorCategory.DATABASE
        return ErrorCategory.UNKNOWN

    def _assess_severity(self, error: Exception) -> ErrorSeverity:
        """评估错误严重程度

        Args:
            error: 异常对象

        Returns:
            ErrorSeverity: 错误严重程度
        """
        error_type = type(error).__name__.lower()

        if "critical" in error_type or "fatal" in error_type:
            return ErrorSeverity.CRITICAL
        if "memory" in error_type or "outofmemory" in error_type:
            return ErrorSeverity.HIGH
        if "warning" in error_type or "deprecated" in error_type:
            return ErrorSeverity.LOW
        return ErrorSeverity.MEDIUM

    def _find_handler(self, exception_type: type) -> Callable | None:
        """查找错误处理器

        Args:
            exception_type: 异常类型

        Returns:
            Optional[Callable]: 错误处理器
        """
        # 精确匹配
        if exception_type in self._error_handlers:
            return self._error_handlers[exception_type]

        # 查找父类匹配
        for handler_type, handler in self._error_handlers.items():
            if issubclass(exception_type, handler_type):
                return handler

        return None

    def _record_error(self, error_info: ErrorInfo):
        """记录错误

        Args:
            error_info: 错误信息
        """
        with self._lock:
            self._error_history.append(error_info)

            # 限制历史记录大小
            if len(self._error_history) > 1000:
                self._error_history = self._error_history[-500:]

        # 记录日志
        self._log_error(error_info)

    def _log_error(self, error_info: ErrorInfo):
        """记录错误日志

        Args:
            error_info: 错误信息
        """
        log_level = {
            ErrorSeverity.LOW: logging.WARNING,
            ErrorSeverity.MEDIUM: logging.ERROR,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }.get(error_info.severity, logging.ERROR)

        message = f"[{error_info.category.value}] {error_info.error}"
        if error_info.context:
            message += f" in {error_info.context}"

        self.logger.log(log_level, message, exc_info=error_info.error)

    def _attempt_recovery(self, error_info: ErrorInfo) -> Any:
        """尝试错误恢复

        Args:
            error_info: 错误信息

        Returns:
            Any: 恢复结果
        """
        recovery_strategy = self._recovery_strategies.get(error_info.category)
        if recovery_strategy:
            try:
                result = recovery_strategy(error_info)
                error_info.recovery_action = "recovered"
                self.logger.info("Error recovered: %s", error_info.error)
                return result
            except Exception as recovery_error:
                self.logger.error("Recovery failed: %s", recovery_error)

        return None

    def _handle_configuration_error(self, error_info: ErrorInfo) -> Any:
        """处理配置错误"""
        self.logger.error("Configuration error: %s", error_info.error)
        return None

    def _handle_image_processing_error(self, error_info: ErrorInfo) -> Any:
        """处理图像处理错误"""
        self.logger.error("Image processing error: %s", error_info.error)
        return None

    def _handle_memory_error(self, error_info: ErrorInfo) -> Any:
        """处理内存错误"""
        self.logger.critical("Memory error: %s", error_info.error)
        return None

    def _handle_file_system_error(self, error_info: ErrorInfo) -> Any:
        """处理文件系统错误"""
        self.logger.error("File system error: %s", error_info.error)
        return None

    def _handle_generic_error(self, error_info: ErrorInfo) -> Any:
        """处理通用错误"""
        self.logger.error("Generic error: %s", error_info.error)
        return None

    def get_error_history(
        self, category: ErrorCategory | None = None, severity: ErrorSeverity | None = None
    ) -> list[ErrorInfo]:
        """获取错误历史

        Args:
            category: 错误类别过滤
            severity: 错误严重程度过滤

        Returns:
            List[ErrorInfo]: 错误历史
        """
        with self._lock:
            filtered_errors = self._error_history

            if category:
                filtered_errors = [e for e in filtered_errors if e.category == category]

            if severity:
                filtered_errors = [e for e in filtered_errors if e.severity == severity]

            return filtered_errors.copy()

    def get_error_statistics(self) -> dict[str, Any]:
        """获取错误统计

        Returns:
            Dict[str, Any]: 错误统计
        """
        with self._lock:
            total_errors = len(self._error_history)

            category_counts = {}
            severity_counts = {}

            for error_info in self._error_history:
                category_counts[error_info.category.value] = category_counts.get(error_info.category.value, 0) + 1
                severity_counts[error_info.severity.value] = severity_counts.get(error_info.severity.value, 0) + 1

            return {
                "total_errors": total_errors,
                "category_counts": category_counts,
                "severity_counts": severity_counts,
                "recent_errors": len(
                    [e for e in self._error_history if e.timestamp > __import__("time").time() - 3600]
                ),
            }


def error_handler(
    category: ErrorCategory = ErrorCategory.UNKNOWN, severity: ErrorSeverity = ErrorSeverity.MEDIUM, context: str = ""
):
    """错误处理装饰器

    Args:
        category: 错误类别
        severity: 错误严重程度
        context: 错误上下文
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as error:
                # 创建错误处理器实例
                handler = ErrorHandler()

                # 处理错误
                result = handler.handle_error(error, context or func.__name__)

                # 如果无法恢复，重新抛出异常
                if result is None:
                    raise

                return result

        return wrapper

    return decorator


@contextmanager
def error_context(context: str, category: ErrorCategory = ErrorCategory.UNKNOWN):
    """错误上下文管理器

    Args:
        context: 上下文名称
        category: 错误类别
    """
    handler = ErrorHandler()

    try:
        yield handler
    except Exception as error:
        handler.handle_error(error, context, category=category)
        raise


# 全局错误处理器实例
global_error_handler = ErrorHandler()

# ========== 轮转文件日志与全局异常钩子 ==========
_ERROR_LOG_PATH: str | None = None


def _default_log_dir() -> str:
    """获取默认日志目录（macOS 优先 ~/Library/Logs/PlookingII，失败回退到临时目录）。"""
    try:
        # macOS 常用日志目录
        base = os.path.expanduser(os.path.join("~", "Library", "Logs", "PlookingII"))
        os.makedirs(base, exist_ok=True)
        return base
    except Exception:
        import tempfile

        base = os.path.join(tempfile.gettempdir(), "PlookingII-logs")
        try:
            os.makedirs(base, exist_ok=True)
        except Exception:
            pass
        return base


def setup_error_logging(max_bytes: int = 2 * 1024 * 1024, backup_count: int = 3) -> str:
    """配置轮转文件日志处理器，并附加到 root logger。

    Args:
        max_bytes: 单个日志文件最大字节数
        backup_count: 备份文件个数

    Returns:
        str: 日志文件路径
    """
    global _ERROR_LOG_PATH

    log_dir = _default_log_dir()
    log_path = os.path.join(log_dir, "error.log")

    # 避免重复添加处理器
    root_logger = logging.getLogger()
    for h in root_logger.handlers:
        if isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "").endswith("error.log"):
            _ERROR_LOG_PATH = log_path
            return log_path

    try:
        handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

        root_logger.addHandler(handler)
        # 若未设置全局等级，则设置为 INFO，保留现有配置优先级
        if root_logger.level == logging.NOTSET:
            root_logger.setLevel(logging.INFO)

        _ERROR_LOG_PATH = log_path
        return log_path
    except Exception:
        # 安静失败，不影响主流程
        return log_path


def get_error_log_path() -> str | None:
    """返回当前错误日志路径（若已初始化）。"""
    return _ERROR_LOG_PATH


def install_global_exception_hook() -> None:
    """安装全局异常钩子，将未捕获异常记录到日志并通过统一处理器记录。"""

    def _hook(exctype, value, tb):
        try:
            # 记录到统一错误处理器
            global_error_handler.handle_error(value, context="global_excepthook")
            # 额外写一条 CRITICAL 级日志，附带堆栈
            logging.critical("Uncaught exception", exc_info=(exctype, value, tb))
        except Exception:
            # 避免异常导致递归崩溃
            pass

    try:
        sys.excepthook = _hook
    except Exception:
        pass


# 测试辅助：显式触发当前 excepthook（不抛出）
def _invoke_global_excepthook(err: Exception) -> None:  # pragma: no cover - 简单桥接
    try:
        hook = getattr(sys, "excepthook", None)
        if hook:
            hook(type(err), err, err.__traceback__)
    except Exception:
        pass


# 模块导入时尝试初始化日志与异常钩子（静默失败）
try:
    setup_error_logging()
    install_global_exception_hook()
except Exception:
    pass
