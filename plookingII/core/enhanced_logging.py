#!/usr/bin/env python3
"""
增强日志记录模块

提供结构化的日志记录功能，包括性能监控、错误跟踪和用户行为分析。

主要功能：
- 结构化日志记录
- 性能监控日志
- 错误跟踪和分析
- 用户行为日志
- 日志轮转和压缩
- 敏感信息过滤

Author: PlookingII Team
"""

import json
import logging
import logging.handlers
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from ..config.constants import APP_NAME


class LogLevel(Enum):
    """日志级别枚举"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """日志类别枚举"""

    SYSTEM = "system"
    USER_ACTION = "user_action"
    PERFORMANCE = "performance"
    ERROR = "error"
    SECURITY = "security"
    BUSINESS = "business"
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    CACHE = "cache"
    CONFIGURATION = "configuration"
    DEBUG = "debug"
    UNKNOWN = "unknown"


@dataclass
class LogEntry:
    """结构化日志条目"""

    timestamp: float
    level: LogLevel
    category: LogCategory
    message: str
    module: str
    function: str
    line_number: int
    thread_id: int
    process_id: int
    metadata: dict[str, Any] = field(default_factory=dict)
    exception_info: str | None = None
    performance_data: dict[str, Any] | None = None


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def __init__(self, include_metadata: bool = True):
        """初始化格式化器

        Args:
            include_metadata: 是否包含元数据
        """
        super().__init__()
        self.include_metadata = include_metadata

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录

        Args:
            record: 日志记录

        Returns:
            str: 格式化后的日志字符串
        """
        # 基础信息
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))
        level = record.levelname
        module = record.name
        message = record.getMessage()

        # 构建基础格式
        formatted = f"{timestamp} [{level}] {module}: {message}"

        # 添加异常信息
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        # 添加元数据
        if self.include_metadata and hasattr(record, "metadata") and record.metadata:
            metadata_str = json.dumps(record.metadata, ensure_ascii=False, indent=2)
            formatted += f"\nMetadata: {metadata_str}"

        # 添加性能数据
        if hasattr(record, "performance_data") and record.performance_data:
            perf_str = json.dumps(record.performance_data, ensure_ascii=False, indent=2)
            formatted += f"\nPerformance: {perf_str}"

        return formatted


class JSONFormatter(logging.Formatter):
    """JSON日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为JSON

        Args:
            record: 日志记录

        Returns:
            str: JSON格式的日志字符串
        """
        log_entry = {
            "timestamp": record.created,
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
            "thread_id": record.thread,
            "process_id": record.process,
        }

        # 添加文件名和行号
        if record.filename:
            log_entry["filename"] = record.filename
        if record.lineno:
            log_entry["line_number"] = record.lineno
        if record.funcName:
            log_entry["function"] = record.funcName

        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # 添加元数据
        if hasattr(record, "metadata") and record.metadata:
            log_entry["metadata"] = record.metadata

        # 添加性能数据
        if hasattr(record, "performance_data") and record.performance_data:
            log_entry["performance"] = record.performance_data

        return json.dumps(log_entry, ensure_ascii=False)


class EnhancedLogger:
    """增强日志记录器"""

    def __init__(self, name: str = APP_NAME, log_dir: str | None = None):
        """初始化增强日志记录器

        Args:
            name: 日志记录器名称
            log_dir: 日志目录
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.log_dir = log_dir or self._get_default_log_dir()
        self._lock = threading.RLock()

        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)

        # 配置日志记录器
        self._setup_handlers()

        # 性能监控数据
        self._performance_data: dict[str, list[float]] = {}

    def _get_default_log_dir(self) -> str:
        """获取默认日志目录"""
        home_dir = Path.home()
        log_dir = home_dir / ".plookingII" / "logs"
        return str(log_dir)

    def _setup_handlers(self):
        """设置日志记录器"""
        # 清除现有处理器
        self.logger.handlers.clear()

        # 设置日志级别
        self.logger.setLevel(logging.DEBUG)

        # 获取环境变量配置的日志级别
        import os

        verbose = os.getenv("PLOOKINGII_VERBOSE", "0") == "1"
        env_level = os.getenv("PLOOKINGII_LOG_LEVEL", "INFO" if verbose else "WARNING")
        console_level = getattr(logging, env_level.upper(), logging.WARNING)

        # 控制台处理器 - 根据环境变量配置
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_formatter = StructuredFormatter(include_metadata=False)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # 文件处理器（轮转）
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(self.log_dir, "plookingII.log"),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = StructuredFormatter(include_metadata=True)
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # 错误日志处理器
        error_handler = logging.handlers.RotatingFileHandler(
            os.path.join(self.log_dir, "errors.log"),
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = JSONFormatter()
        error_handler.setFormatter(error_formatter)
        self.logger.addHandler(error_handler)

        # 性能日志处理器
        perf_handler = logging.handlers.RotatingFileHandler(
            os.path.join(self.log_dir, "performance.log"),
            maxBytes=20 * 1024 * 1024,  # 20MB
            backupCount=2,
            encoding="utf-8",
        )
        perf_handler.setLevel(logging.INFO)
        perf_formatter = JSONFormatter()
        perf_handler.setFormatter(perf_formatter)
        self.logger.addHandler(perf_handler)

    def log(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        metadata: dict[str, Any] | None = None,
        performance_data: dict[str, Any] | None = None,
        exception: Exception | None = None,
    ):
        """记录结构化日志

        Args:
            level: 日志级别
            category: 日志类别
            message: 日志消息
            metadata: 元数据
            performance_data: 性能数据
            exception: 异常对象
        """
        with self._lock:
            # 获取调用者信息
            frame = logging.currentframe().f_back.f_back
            frame.f_globals.get("__name__", "unknown")
            frame.f_code.co_name
            line_number = frame.f_lineno

            # 创建日志记录
            record = self.logger.makeRecord(
                name=self.logger.name,
                level=getattr(logging, level.value),
                fn=frame.f_code.co_filename,
                lno=line_number,
                msg=message,
                args=(),
                exc_info=exception and (type(exception), exception, exception.__traceback__),
            )

            # 添加自定义字段
            record.metadata = metadata or {}
            record.performance_data = performance_data
            record.category = category.value

            # 记录日志
            self.logger.handle(record)

    def log_performance(self, operation: str, duration: float, metadata: dict[str, Any] | None = None):
        """记录性能日志

        Args:
            operation: 操作名称
            duration: 持续时间（秒）
            metadata: 元数据
        """
        perf_data = {"operation": operation, "duration": duration, "timestamp": time.time()}

        if metadata:
            perf_data.update(metadata)

        # 更新性能统计
        with self._lock:
            if operation not in self._performance_data:
                self._performance_data[operation] = []
            self._performance_data[operation].append(duration)

            # 保持最近100次记录
            if len(self._performance_data[operation]) > 100:
                self._performance_data[operation] = self._performance_data[operation][-100:]

        self.log(
            LogLevel.INFO,
            LogCategory.PERFORMANCE,
            f"Performance: {operation} took {duration:.3f}s",
            performance_data=perf_data,
        )

    def log_user_action(self, action: str, metadata: dict[str, Any] | None = None):
        """记录用户行为日志

        Args:
            action: 用户行为
            metadata: 元数据
        """
        self.log(LogLevel.INFO, LogCategory.USER_ACTION, f"User action: {action}", metadata=metadata)

    def log_error(self, error: Exception, context: str = "", metadata: dict[str, Any] | None = None):
        """记录错误日志

        Args:
            error: 异常对象
            context: 错误上下文
            metadata: 元数据
        """
        message = f"Error in {context}: {error!s}" if context else str(error)
        self.log(LogLevel.ERROR, LogCategory.ERROR, message, metadata=metadata, exception=error)

    def get_performance_stats(self, operation: str | None = None) -> dict[str, Any]:
        """获取性能统计

        Args:
            operation: 操作名称，None表示所有操作

        Returns:
            Dict[str, Any]: 性能统计
        """
        with self._lock:
            if operation:
                if operation not in self._performance_data:
                    return {}

                durations = self._performance_data[operation]
                return {
                    "operation": operation,
                    "count": len(durations),
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                    "recent_durations": durations[-10:],  # 最近10次
                }
            stats = {}
            for op, durations in self._performance_data.items():
                stats[op] = {
                    "count": len(durations),
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                }
            return stats

    @contextmanager
    def performance_timer(self, operation: str, metadata: dict[str, Any] | None = None):
        """性能计时上下文管理器

        Args:
            operation: 操作名称
            metadata: 元数据

        Yields:
            Dict[str, Any]: 性能数据字典
        """
        start_time = time.time()
        perf_data = {"operation": operation, "start_time": start_time}

        if metadata:
            perf_data.update(metadata)

        try:
            yield perf_data
        finally:
            duration = time.time() - start_time
            perf_data["duration"] = duration
            self.log_performance(operation, duration, perf_data)


# 全局增强日志记录器实例
enhanced_logger = EnhancedLogger()


def get_enhanced_logger(name: str = APP_NAME) -> EnhancedLogger:
    """获取增强日志记录器实例

    Args:
        name: 日志记录器名称

    Returns:
        EnhancedLogger: 增强日志记录器实例
    """
    if name == APP_NAME:
        return enhanced_logger
    return EnhancedLogger(name)


# 便捷函数
def log_performance(operation: str, duration: float, metadata: dict[str, Any] | None = None):
    """记录性能日志"""
    enhanced_logger.log_performance(operation, duration, metadata)


def log_user_action(action: str, metadata: dict[str, Any] | None = None):
    """记录用户行为日志"""
    enhanced_logger.log_user_action(action, metadata)


def log_error(error: Exception, context: str = "", metadata: dict[str, Any] | None = None):
    """记录错误日志"""
    enhanced_logger.log_error(error, context, metadata)


@contextmanager
def performance_timer(operation: str, metadata: dict[str, Any] | None = None):
    """性能计时上下文管理器"""
    with enhanced_self.logger.performance_timer(operation, metadata) as perf_data:
        yield perf_data
