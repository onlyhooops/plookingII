#!/usr/bin/env python3
"""
延迟初始化模块

提供延迟初始化功能，优化应用程序启动性能。
通过延迟创建重型组件，减少启动时间和内存使用。

主要功能：
- 延迟初始化装饰器
- 懒加载属性
- 组件池管理
- 启动性能监控

Author: PlookingII Team
"""

import functools
import threading
import time
from collections.abc import Callable
from typing import Any, Generic, TypeVar

from ..imports import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class LazyProperty(Generic[T]):
    """懒加载属性装饰器

    只有在第一次访问时才创建对象，后续访问直接返回缓存的对象。
    """

    def __init__(self, factory: Callable[[], T], name: str | None = None):
        """初始化懒加载属性

        Args:
            factory: 创建对象的工厂函数
            name: 属性名称，用于调试
        """
        self.factory = factory
        self.name = name or factory.__name__
        self._value: T | None = None
        self._lock = threading.RLock()
        self._initialized = False

    def __get__(self, instance: Any, owner: Any) -> T:
        """获取属性值，如果未初始化则创建"""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    start_time = time.time()
                    try:
                        self._value = self.factory()
                        self._initialized = True
                        elapsed = time.time() - start_time
                        logging.getLogger(__name__).debug(f"LazyProperty '{self.name}' initialized in {elapsed:.3f}s")
                    except Exception as e:
                        logging.getLogger(__name__).error(f"Failed to initialize LazyProperty '{self.name}': {e}")
                        raise
        return self._value

    def __set__(self, instance: Any, value: T) -> None:
        """设置属性值"""
        with self._lock:
            self._value = value
            self._initialized = True

    def reset(self) -> None:
        """重置属性，下次访问时重新创建"""
        with self._lock:
            self._value = None
            self._initialized = False


def lazy_init(factory_func: Callable[[], T]) -> LazyProperty[T]:
    """创建懒加载属性的便捷函数

    Args:
        factory_func: 创建对象的工厂函数

    Returns:
        LazyProperty实例
    """
    return LazyProperty(factory_func)


class ComponentPool:
    """组件池管理器

    管理重型组件的创建和复用，减少重复初始化的开销。
    """

    def __init__(self, max_size: int = 10):
        """初始化组件池

        Args:
            max_size: 池的最大大小
        """
        self.max_size = max_size
        self._pool: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._creation_times: dict[str, float] = {}

    def get_or_create(self, key: str, factory: Callable[[], T]) -> T:
        """获取或创建组件

        Args:
            key: 组件键
            factory: 创建组件的工厂函数

        Returns:
            组件实例
        """
        with self._lock:
            if key not in self._pool:
                if len(self._pool) >= self.max_size:
                    # 清理最旧的组件
                    self._cleanup_oldest()

                start_time = time.time()
                try:
                    self._pool[key] = factory()
                    self._creation_times[key] = start_time
                    elapsed = time.time() - start_time
                    logging.getLogger(__name__).debug(f"Component '{key}' created in {elapsed:.3f}s")
                except Exception as e:
                    logging.getLogger(__name__).error(f"Failed to create component '{key}': {e}")
                    raise

            return self._pool[key]

    def _cleanup_oldest(self) -> None:
        """清理最旧的组件"""
        if not self._creation_times:
            return

        oldest_key = min(self._creation_times.keys(), key=lambda k: self._creation_times[k])

        if oldest_key in self._pool:
            del self._pool[oldest_key]
            del self._creation_times[oldest_key]
            logging.getLogger(__name__).debug(f"Cleaned up oldest component: {oldest_key}")

    def clear(self) -> None:
        """清空组件池"""
        with self._lock:
            self._pool.clear()
            self._creation_times.clear()
            logging.getLogger(__name__).debug("Component pool cleared")


class StartupProfiler:
    """启动性能分析器

    监控和记录启动过程中各个组件的初始化时间。
    """

    def __init__(self):
        """初始化启动分析器"""
        self._timings: dict[str, float] = {}
        self._start_time = time.time()
        self._lock = threading.RLock()

    def start_timing(self, component: str) -> None:
        """开始计时

        Args:
            component: 组件名称
        """
        with self._lock:
            self._timings[f"{component}_start"] = time.time()

    def end_timing(self, component: str) -> None:
        """结束计时

        Args:
            component: 组件名称
        """
        with self._lock:
            end_time = time.time()
            start_key = f"{component}_start"
            if start_key in self._timings:
                duration = end_time - self._timings[start_key]
                self._timings[component] = duration
                del self._timings[start_key]
                logging.getLogger(__name__).debug(f"Component '{component}' initialized in {duration:.3f}s")

    def get_total_time(self) -> float:
        """获取总启动时间"""
        return time.time() - self._start_time

    def get_report(self) -> dict[str, float]:
        """获取性能报告"""
        with self._lock:
            report = self._timings.copy()
            report["total_startup_time"] = self.get_total_time()
            return report

    def log_report(self) -> None:
        """记录性能报告（简化版）"""
        report = self.get_report()
        total_time = report.get("total_startup_time", 0)
        # 只记录总启动时间，详细信息仅在DEBUG模式下记录
        logging.getLogger(__name__).info(f"Application started in {total_time:.3f}s")

        # 详细报告仅在DEBUG级别记录
        logging.getLogger(__name__).debug("Detailed startup timings:")
        for component, duration in sorted(report.items(), key=lambda x: x[1], reverse=True):
            if component != "total_startup_time":
                logging.getLogger(__name__).debug(f"  {component}: {duration:.3f}s")


# 全局启动分析器实例
startup_profiler = StartupProfiler()


def profile_startup(component_name: str):
    """启动性能分析装饰器

    Args:
        component_name: 组件名称
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            startup_profiler.start_timing(component_name)
            try:
                return func(*args, **kwargs)
            finally:
                startup_profiler.end_timing(component_name)

        return wrapper

    return decorator


# 全局组件池实例
component_pool = ComponentPool()
