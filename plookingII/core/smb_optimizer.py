"""
SMB优化器

专门针对SMB网络文件系统的性能优化器。
实现预读缓冲、批量读取、连接池等优化策略。
"""

import concurrent.futures
import os
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..config.manager import get_config
from .enhanced_logging import LogCategory, LogLevel, get_enhanced_logger
from .error_handling import ErrorCategory, error_context
from .remote_file_detector import MountType, get_remote_detector


class ReadStrategy(Enum):
    """读取策略枚举"""

    SEQUENTIAL = "sequential"  # 顺序读取
    BATCH = "batch"  # 批量读取
    PRELOAD = "preload"  # 预加载
    ADAPTIVE = "adaptive"  # 自适应


@dataclass
class ReadRequest:
    """读取请求数据类"""

    file_path: str
    offset: int = 0
    size: int = -1
    priority: int = 0  # 优先级，数字越大优先级越高
    timestamp: float = 0.0


@dataclass
class ReadResult:
    """读取结果数据类"""

    file_path: str
    data: bytes
    success: bool
    latency_ms: float
    error: Exception | None = None


class SMBOptimizer:
    """
    SMB优化器

    功能：
    1. 智能读取策略选择
    2. 批量读取优化
    3. 预读缓冲管理
    4. 连接池管理
    5. 目录列表缓存
    """

    def __init__(self):
        self.logger = get_enhanced_logger()
        self.remote_detector = get_remote_detector()

        # 配置参数
        self.read_ahead_buffer = get_config("smb.read_ahead_buffer", 64 * 1024)  # 64KB
        self.batch_size = get_config("smb.batch_size", 8)  # 批量读取文件数
        self.max_workers = get_config("smb.max_workers", 4)  # 最大并发数
        self.cache_ttl = get_config("smb.cache_ttl", 300)  # 缓存有效期（秒）

        # 连接池
        self.connection_pool: dict[str, Any] = {}
        self.connection_lock = threading.RLock()

        # 目录缓存
        self.directory_cache: dict[str, tuple[list[str], float]] = {}
        self.directory_cache_lock = threading.RLock()

        # 预读缓冲
        self.read_ahead_cache: dict[str, bytes] = {}
        self.read_ahead_lock = threading.RLock()

        # 性能统计
        self.stats = {
            "total_reads": 0,
            "batch_reads": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_latency": 0.0,
            "total_latency": 0.0,
        }
        self.stats_lock = threading.RLock()

        # 线程池
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers, thread_name_prefix="SMBOptimizer"
        )

        self.logger.log(LogLevel.DEBUG, LogCategory.SYSTEM, "SMBOptimizer initialized")

    def optimize_read_strategy(self, file_path: str, file_size: int = -1) -> ReadStrategy:
        """
        优化SMB读取策略

        Args:
            file_path: 文件路径
            file_size: 文件大小（字节），-1表示未知

        Returns:
            ReadStrategy: 推荐的读取策略
        """
        try:
            with error_context("read_strategy_optimization", ErrorCategory.PERFORMANCE):
                # 检查是否为SMB路径
                if not self._is_smb_path(file_path):
                    return ReadStrategy.SEQUENTIAL

                # 获取网络延迟
                latency = self.remote_detector.get_network_latency(file_path)

                # 根据延迟和文件大小选择策略
                if latency > 100:  # 高延迟
                    if file_size > 0 and file_size < 1024 * 1024:  # 小文件
                        return ReadStrategy.BATCH
                    return ReadStrategy.PRELOAD
                if latency > 50:  # 中等延迟
                    return ReadStrategy.ADAPTIVE
                # 低延迟
                return ReadStrategy.SEQUENTIAL

        except Exception as e:
            self.logger.exception("Failed to optimize read strategy: %s", e)
            return ReadStrategy.SEQUENTIAL

    def batch_read_files(self, file_paths: list[str]) -> list[ReadResult]:
        """
        批量读取文件，减少网络往返

        Args:
            file_paths: 文件路径列表

        Returns:
            List[ReadResult]: 读取结果列表
        """
        try:
            with error_context("batch_file_read", ErrorCategory.FILE_SYSTEM):
                if not file_paths:
                    return []

                # 过滤SMB路径
                smb_paths = [path for path in file_paths if self._is_smb_path(path)]
                if not smb_paths:
                    return []

                self.logging.getLogger(__name__).log(
                    LogLevel.DEBUG, LogCategory.PERFORMANCE, f"Starting batch read for {len(smb_paths)} SMB files"
                )

                # 使用线程池并发读取
                results = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_to_path = {executor.submit(self._read_single_file, path): path for path in smb_paths}

                    for future in concurrent.futures.as_completed(future_to_path):
                        path = future_to_path[future]
                        try:
                            result = future.result()
                            results.append(result)
                        except Exception as e:
                            self.logging.getLogger(__name__).log_error(e, f"batch_read_file_{path}")
                            results.append(ReadResult(file_path=path, data=b"", success=False, latency_ms=0.0, error=e))

                # 更新统计信息
                with self.stats_lock:
                    self.stats["batch_reads"] += 1
                    self.stats["total_reads"] += len(results)

                self.logging.getLogger(__name__).log(
                    LogLevel.INFO, LogCategory.PERFORMANCE, f"Batch read completed: {len(results)} files processed"
                )

                return results

        except Exception as e:
            self.logging.getLogger(__name__).log_error(e, "batch_file_read")
            return []

    def cache_directory_listing(self, dir_path: str) -> list[str]:
        """
        缓存目录列表，减少网络请求

        Args:
            dir_path: 目录路径

        Returns:
            List[str]: 目录中的文件列表
        """
        try:
            with error_context("directory_listing_cache", ErrorCategory.FILE_SYSTEM):
                if not self._is_smb_path(dir_path):
                    # 非SMB路径直接返回
                    return os.listdir(dir_path) if os.path.isdir(dir_path) else []

                current_time = time.time()

                # 检查缓存
                with self.directory_cache_lock:
                    if dir_path in self.directory_cache:
                        cached_list, cache_time = self.directory_cache[dir_path]
                        if current_time - cache_time < self.cache_ttl:
                            self.logging.getLogger(__name__).log(
                                LogLevel.DEBUG, LogCategory.CACHE, f"Directory cache hit for: {dir_path}"
                            )
                            with self.stats_lock:
                                self.stats["cache_hits"] += 1
                            return cached_list

                # 读取目录
                start_time = time.perf_counter()
                try:
                    file_list = os.listdir(dir_path)
                except (OSError, PermissionError) as e:
                    self.logging.getLogger(__name__).log_error(e, f"directory_listing_{dir_path}")
                    return []

                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000

                # 更新缓存
                with self.directory_cache_lock:
                    self.directory_cache[dir_path] = (file_list, current_time)

                # 更新统计信息
                with self.stats_lock:
                    self.stats["cache_misses"] += 1
                    self.stats["total_latency"] += latency_ms
                    self.stats["avg_latency"] = self.stats["total_latency"] / (
                        self.stats["cache_hits"] + self.stats["cache_misses"]
                    )

                self.logging.getLogger(__name__).log(
                    LogLevel.DEBUG,
                    LogCategory.CACHE,
                    f"Directory cached: {dir_path} ({len(file_list)} files, {latency_ms:.2f}ms)",
                )

                return file_list

        except Exception as e:
            self.logging.getLogger(__name__).log_error(e, "directory_listing_cache")
            return []

    def preload_file_data(self, file_path: str, size: int | None = None) -> bool:
        """
        预加载文件数据到缓存

        Args:
            file_path: 文件路径
            size: 预加载大小，None表示整个文件

        Returns:
            bool: 是否成功预加载
        """
        try:
            with error_context("file_preload", ErrorCategory.PERFORMANCE):
                if not self._is_smb_path(file_path):
                    return False

                # 检查是否已缓存
                with self.read_ahead_lock:
                    if file_path in self.read_ahead_cache:
                        return True

                # 读取文件数据
                start_time = time.perf_counter()
                try:
                    with open(file_path, "rb") as f:
                        data = f.read() if size is None else f.read(size)
                except (OSError, PermissionError) as e:
                    self.logging.getLogger(__name__).log_error(e, f"file_preload_{file_path}")
                    return False

                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000

                # 缓存数据
                with self.read_ahead_lock:
                    self.read_ahead_cache[file_path] = data

                self.logging.getLogger(__name__).log(
                    LogLevel.DEBUG,
                    LogCategory.PERFORMANCE,
                    f"File preloaded: {file_path} ({len(data)} bytes, {latency_ms:.2f}ms)",
                )

                return True

        except Exception as e:
            self.logging.getLogger(__name__).log_error(e, "file_preload")
            return False

    def get_cached_file_data(self, file_path: str) -> bytes | None:
        """
        获取缓存的文件数据

        Args:
            file_path: 文件路径

        Returns:
            Optional[bytes]: 缓存的数据，如果不存在则返回None
        """
        with self.read_ahead_lock:
            return self.read_ahead_cache.get(file_path)

    def get_performance_stats(self) -> dict[str, Any]:
        """获取性能统计信息"""
        with self.stats_lock:
            return self.stats.copy()

    def clear_cache(self):
        """清空所有缓存"""
        with self.directory_cache_lock:
            self.directory_cache.clear()
        with self.read_ahead_lock:
            self.read_ahead_cache.clear()

        self.logging.getLogger(__name__).log(LogLevel.INFO, LogCategory.SYSTEM, "SMB optimizer cache cleared")

    def _is_smb_path(self, file_path: str) -> bool:
        """检查是否为SMB路径"""
        try:
            mount_type = self.remote_detector.get_mount_type(file_path)
            return mount_type == MountType.SMB
        except Exception:
            return False

    def _read_single_file(self, file_path: str) -> ReadResult:
        """读取单个文件"""
        start_time = time.perf_counter()
        try:
            with open(file_path, "rb") as f:
                data = f.read()

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            return ReadResult(file_path=file_path, data=data, success=True, latency_ms=latency_ms)

        except Exception as e:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            return ReadResult(file_path=file_path, data=b"", success=False, latency_ms=latency_ms, error=e)


# 全局实例
_smb_optimizer_instance: SMBOptimizer | None = None
_smb_optimizer_lock = threading.Lock()


def get_smb_optimizer() -> SMBOptimizer:
    """获取全局SMBOptimizer实例"""
    global _smb_optimizer_instance  # noqa: PLW0603  # 单例模式的合理使用
    if _smb_optimizer_instance is None:
        with _smb_optimizer_lock:
            if _smb_optimizer_instance is None:
                _smb_optimizer_instance = SMBOptimizer()
    return _smb_optimizer_instance
