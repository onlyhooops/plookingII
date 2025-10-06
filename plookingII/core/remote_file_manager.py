"""
远程文件管理器

整合远程文件检测、SMB优化和网络缓存功能，提供统一的远程文件访问接口。
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
from .network_cache import get_network_cache
from .remote_file_detector import MountInfo, MountType, get_remote_detector
from .smb_optimizer import ReadStrategy, get_smb_optimizer


class LoadingMode(Enum):
    """加载模式枚举"""

    DIRECT = "direct"  # 直接加载
    CACHED = "cached"  # 使用缓存
    PRELOAD = "preload"  # 预加载
    BATCH = "batch"  # 批量加载


@dataclass
class RemoteFileInfo:
    """远程文件信息数据类"""

    path: str
    is_remote: bool
    mount_type: MountType
    mount_info: MountInfo | None
    latency_ms: float
    file_size: int
    is_cached: bool
    cache_path: str | None = None
    loading_strategy: ReadStrategy = ReadStrategy.SEQUENTIAL


@dataclass
class LoadingResult:
    """加载结果数据类"""

    file_path: str
    data: bytes
    success: bool
    loading_mode: LoadingMode
    latency_ms: float
    from_cache: bool
    error: Exception | None = None


class RemoteFileManager:
    """
    远程文件管理器

    功能：
    1. 统一的远程文件访问接口
    2. 智能加载策略选择
    3. 批量文件处理
    4. 性能监控和优化
    5. 缓存管理集成
    """

    def __init__(self):
        self.logger = get_enhanced_logger()
        self.logging = self.logger  # 为兼容性提供别名
        self.remote_detector = get_remote_detector()
        self.smb_optimizer = get_smb_optimizer()
        self.network_cache = get_network_cache()

        # 配置参数
        self.auto_cache_enabled = get_config("remote_file.auto_cache", True)
        self.batch_size = get_config("remote_file.batch_size", 8)
        self.max_workers = get_config("remote_file.max_workers", 4)
        self.preload_threshold = get_config("remote_file.preload_threshold", 1024 * 1024)  # 1MB

        # 线程池
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers, thread_name_prefix="RemoteFileManager"
        )

        # 性能统计
        self.stats = {
            "total_files_loaded": 0,
            "remote_files_loaded": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "batch_operations": 0,
            "preload_operations": 0,
            "total_latency": 0.0,
            "avg_latency": 0.0,
        }
        self.stats_lock = threading.RLock()

        self.logger.log(LogLevel.DEBUG, LogCategory.SYSTEM, "RemoteFileManager initialized")

    def load_remote_image(self, file_path: str, target_size: tuple[int, int] | None = None) -> LoadingResult | None:
        """
        加载远程图像文件

        Args:
            file_path: 文件路径
            target_size: 目标尺寸 (width, height)

        Returns:
            Optional[LoadingResult]: 加载结果
        """
        try:
            with error_context("remote_image_load", ErrorCategory.FILE_SYSTEM):
                # 获取文件信息
                file_info = self._get_file_info(file_path)
                if not file_info:
                    return None

                # 选择加载策略
                loading_mode = self._select_loading_mode(file_info)

                # 执行加载
                result = self._execute_loading(file_path, file_info, loading_mode)

                # 更新统计信息
                self._update_stats(result)

                return result

        except Exception as e:
            self.logging.getLogger(__name__).log_error(e, "remote_image_load")
            return LoadingResult(
                file_path=file_path,
                data=b"",
                success=False,
                loading_mode=LoadingMode.DIRECT,
                latency_ms=0.0,
                from_cache=False,
                error=e,
            )

    def preload_remote_images(self, file_paths: list[str]) -> list[LoadingResult]:
        """
        预加载远程图像

        Args:
            file_paths: 文件路径列表

        Returns:
            List[LoadingResult]: 预加载结果列表
        """
        try:
            with error_context("remote_images_preload", ErrorCategory.PERFORMANCE):
                if not file_paths:
                    return []

                # 过滤远程文件
                remote_files = [path for path in file_paths if self.remote_detector.is_remote_path(path)]
                if not remote_files:
                    return []

                self.logging.getLogger(__name__).log(
                    LogLevel.DEBUG, LogCategory.PERFORMANCE, f"Starting preload for {len(remote_files)} remote files"
                )

                # 批量预加载
                results = []
                batch_size = min(self.batch_size, len(remote_files))

                for i in range(0, len(remote_files), batch_size):
                    batch = remote_files[i : i + batch_size]
                    batch_results = self._preload_batch(batch)
                    results.extend(batch_results)

                # 更新统计信息
                with self.stats_lock:
                    self.stats["preload_operations"] += 1
                    self.stats["total_files_loaded"] += len(results)
                    self.stats["remote_files_loaded"] += len([r for r in results if r.success])

                self.logging.getLogger(__name__).log(
                    LogLevel.INFO, LogCategory.PERFORMANCE, f"Preload completed: {len(results)} files processed"
                )

                return results

        except Exception as e:
            self.logging.getLogger(__name__).log_error(e, "remote_images_preload")
            return []

    def get_optimized_loading_strategy(self, file_path: str) -> ReadStrategy:
        """
        获取优化的加载策略

        Args:
            file_path: 文件路径

        Returns:
            ReadStrategy: 推荐的加载策略
        """
        try:
            with error_context("loading_strategy_optimization", ErrorCategory.PERFORMANCE):
                # 检查是否为远程文件
                if not self.remote_detector.is_remote_path(file_path):
                    return ReadStrategy.SEQUENTIAL

                # 获取文件信息
                file_info = self._get_file_info(file_path)
                if not file_info:
                    return ReadStrategy.SEQUENTIAL

                # 根据文件大小和网络延迟选择策略
                if file_info.latency_ms > 100:  # 高延迟
                    if file_info.file_size < self.preload_threshold:
                        return ReadStrategy.BATCH
                    return ReadStrategy.PRELOAD
                if file_info.latency_ms > 50:  # 中等延迟
                    return ReadStrategy.ADAPTIVE
                # 低延迟
                return ReadStrategy.SEQUENTIAL

        except Exception as e:
            self.logging.getLogger(__name__).log_error(e, "loading_strategy_optimization")
            return ReadStrategy.SEQUENTIAL

    def batch_load_files(self, file_paths: list[str]) -> list[LoadingResult]:
        """
        批量加载文件

        Args:
            file_paths: 文件路径列表

        Returns:
            List[LoadingResult]: 加载结果列表
        """
        try:
            with error_context("batch_file_load", ErrorCategory.PERFORMANCE):
                if not file_paths:
                    return []

                # 分离远程和本地文件
                remote_files = []
                local_files = []

                for path in file_paths:
                    if self.remote_detector.is_remote_path(path):
                        remote_files.append(path)
                    else:
                        local_files.append(path)

                results = []

                # 批量处理远程文件
                if remote_files:
                    remote_results = self.smb_optimizer.batch_read_files(remote_files)
                    for result in remote_results:
                        loading_result = LoadingResult(
                            file_path=result.file_path,
                            data=result.data,
                            success=result.success,
                            loading_mode=LoadingMode.BATCH,
                            latency_ms=result.latency_ms,
                            from_cache=False,
                            error=result.error,
                        )
                        results.append(loading_result)

                # 处理本地文件
                for path in local_files:
                    try:
                        with open(path, "rb") as f:
                            data = f.read()

                        loading_result = LoadingResult(
                            file_path=path,
                            data=data,
                            success=True,
                            loading_mode=LoadingMode.DIRECT,
                            latency_ms=0.0,
                            from_cache=False,
                        )
                        results.append(loading_result)

                    except Exception as e:
                        loading_result = LoadingResult(
                            file_path=path,
                            data=b"",
                            success=False,
                            loading_mode=LoadingMode.DIRECT,
                            latency_ms=0.0,
                            from_cache=False,
                            error=e,
                        )
                        results.append(loading_result)

                # 更新统计信息
                with self.stats_lock:
                    self.stats["batch_operations"] += 1
                    self.stats["total_files_loaded"] += len(results)
                    self.stats["remote_files_loaded"] += len(remote_files)

                return results

        except Exception as e:
            self.logging.getLogger(__name__).log_error(e, "batch_file_load")
            return []

    def get_file_info(self, file_path: str) -> RemoteFileInfo | None:
        """
        获取文件信息

        Args:
            file_path: 文件路径

        Returns:
            Optional[RemoteFileInfo]: 文件信息
        """
        return self._get_file_info(file_path)

    def get_performance_stats(self) -> dict[str, Any]:
        """获取性能统计信息"""
        with self.stats_lock:
            stats = self.stats.copy()
            if stats["total_files_loaded"] > 0:
                stats["avg_latency"] = stats["total_latency"] / stats["total_files_loaded"]
                stats["remote_file_ratio"] = stats["remote_files_loaded"] / stats["total_files_loaded"]
            else:
                stats["avg_latency"] = 0.0
                stats["remote_file_ratio"] = 0.0

            # 添加缓存统计
            cache_stats = self.network_cache.get_cache_stats()
            stats.update(
                {
                    "cache_hit_rate": cache_stats.get("cache_hit_rate", 0.0),
                    "cache_usage_mb": cache_stats.get("cache_usage_mb", 0.0),
                    "cached_files": cache_stats.get("total_cached_files", 0),
                }
            )

            return stats

    def clear_cache(self):
        """清空缓存"""
        self.network_cache.clear_all_cache()
        self.smb_optimizer.clear_cache()
        self.remote_detector.clear_cache()
        self.logging.getLogger(__name__).log(LogLevel.INFO, LogCategory.SYSTEM, "All remote file caches cleared")

    def _get_file_info(self, file_path: str) -> RemoteFileInfo | None:
        """获取文件信息"""
        try:
            # 检查是否为远程路径
            is_remote = self.remote_detector.is_remote_path(file_path)
            mount_type = self.remote_detector.get_mount_type(file_path)
            mount_info = self.remote_detector.get_mount_info(file_path)

            # 获取网络延迟
            latency_ms = self.remote_detector.get_network_latency(file_path)

            # 获取文件大小
            try:
                file_size = os.path.getsize(file_path)
            except (OSError, PermissionError):
                file_size = 0

            # 检查是否已缓存
            is_cached = False
            cache_path = None
            if is_remote and self.auto_cache_enabled:
                cache_path = self.network_cache.get_cached_path(file_path)
                is_cached = cache_path is not None

            # 选择加载策略
            loading_strategy = self.smb_optimizer.optimize_read_strategy(file_path, file_size)

            return RemoteFileInfo(
                path=file_path,
                is_remote=is_remote,
                mount_type=mount_type,
                mount_info=mount_info,
                latency_ms=latency_ms,
                file_size=file_size,
                is_cached=is_cached,
                cache_path=cache_path,
                loading_strategy=loading_strategy,
            )

        except Exception as e:
            self.logging.getLogger(__name__).log_error(e, f"get_file_info_{file_path}")
            return None

    def _select_loading_mode(self, file_info: RemoteFileInfo) -> LoadingMode:
        """选择加载模式"""
        if not file_info.is_remote:
            return LoadingMode.DIRECT

        if file_info.is_cached and file_info.cache_path:
            return LoadingMode.CACHED

        if file_info.loading_strategy == ReadStrategy.PRELOAD:
            return LoadingMode.PRELOAD

        if file_info.loading_strategy == ReadStrategy.BATCH:
            return LoadingMode.BATCH

        return LoadingMode.DIRECT

    def _execute_loading(self, file_path: str, file_info: RemoteFileInfo, loading_mode: LoadingMode) -> LoadingResult:
        """执行文件加载"""
        start_time = time.perf_counter()

        try:
            if loading_mode == LoadingMode.CACHED:
                # 从缓存加载
                return self._load_from_cache(file_path, file_info, start_time)
            if loading_mode == LoadingMode.PRELOAD:
                # 预加载模式
                return self._preload_file(file_path, file_info, start_time)
            # 直接加载
            return self._load_directly(file_path, file_info, start_time)

        except Exception as e:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            return LoadingResult(
                file_path=file_path,
                data=b"",
                success=False,
                loading_mode=loading_mode,
                latency_ms=latency_ms,
                from_cache=False,
                error=e,
            )

    def _load_from_cache(self, file_path: str, file_info: RemoteFileInfo, start_time: float) -> LoadingResult:
        """从缓存加载文件"""
        try:
            with open(file_info.cache_path, "rb") as f:
                data = f.read()

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            return LoadingResult(
                file_path=file_path,
                data=data,
                success=True,
                loading_mode=LoadingMode.CACHED,
                latency_ms=latency_ms,
                from_cache=True,
            )

        except Exception as e:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            return LoadingResult(
                file_path=file_path,
                data=b"",
                success=False,
                loading_mode=LoadingMode.CACHED,
                latency_ms=latency_ms,
                from_cache=True,
                error=e,
            )

    def _preload_file(self, file_path: str, file_info: RemoteFileInfo, start_time: float) -> LoadingResult:
        """预加载文件"""
        try:
            # 先尝试缓存文件
            from_cache = False
            if self.auto_cache_enabled:
                cache_path = self.network_cache.cache_remote_file(file_path)
                if cache_path:
                    # 从缓存读取
                    with open(cache_path, "rb") as f:
                        data = f.read()
                    from_cache = True
                else:
                    # 直接读取
                    with open(file_path, "rb") as f:
                        data = f.read()
            else:
                # 直接读取
                with open(file_path, "rb") as f:
                    data = f.read()

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            return LoadingResult(
                file_path=file_path,
                data=data,
                success=True,
                loading_mode=LoadingMode.PRELOAD,
                latency_ms=latency_ms,
                from_cache=from_cache,
            )

        except Exception as e:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            return LoadingResult(
                file_path=file_path,
                data=b"",
                success=False,
                loading_mode=LoadingMode.PRELOAD,
                latency_ms=latency_ms,
                from_cache=False,
                error=e,
            )

    def _load_directly(self, file_path: str, file_info: RemoteFileInfo, start_time: float) -> LoadingResult:
        """直接加载文件"""
        try:
            with open(file_path, "rb") as f:
                data = f.read()

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            return LoadingResult(
                file_path=file_path,
                data=data,
                success=True,
                loading_mode=LoadingMode.DIRECT,
                latency_ms=latency_ms,
                from_cache=False,
            )

        except Exception as e:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            return LoadingResult(
                file_path=file_path,
                data=b"",
                success=False,
                loading_mode=LoadingMode.DIRECT,
                latency_ms=latency_ms,
                from_cache=False,
                error=e,
            )

    def _preload_batch(self, file_paths: list[str]) -> list[LoadingResult]:
        """批量预加载文件"""
        results = []

        # 使用线程池并发预加载
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {executor.submit(self._preload_single_file, path): path for path in file_paths}

            for future in concurrent.futures.as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logging.getLogger(__name__).log_error(e, f"preload_batch_{path}")
                    results.append(
                        LoadingResult(
                            file_path=path,
                            data=b"",
                            success=False,
                            loading_mode=LoadingMode.PRELOAD,
                            latency_ms=0.0,
                            from_cache=False,
                            error=e,
                        )
                    )

        return results

    def _preload_single_file(self, file_path: str) -> LoadingResult:
        """预加载单个文件"""
        start_time = time.perf_counter()

        try:
            # 缓存文件
            cache_path = self.network_cache.cache_remote_file(file_path)

            if cache_path:
                # 从缓存读取
                with open(cache_path, "rb") as f:
                    data = f.read()
                from_cache = True
            else:
                # 直接读取
                with open(file_path, "rb") as f:
                    data = f.read()
                from_cache = False

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            return LoadingResult(
                file_path=file_path,
                data=data,
                success=True,
                loading_mode=LoadingMode.PRELOAD,
                latency_ms=latency_ms,
                from_cache=from_cache,
            )

        except Exception as e:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            return LoadingResult(
                file_path=file_path,
                data=b"",
                success=False,
                loading_mode=LoadingMode.PRELOAD,
                latency_ms=latency_ms,
                from_cache=False,
                error=e,
            )

    def _update_stats(self, result: LoadingResult):
        """更新统计信息"""
        with self.stats_lock:
            self.stats["total_files_loaded"] += 1
            if result.success:
                self.stats["total_latency"] += result.latency_ms
            if result.from_cache:
                self.stats["cache_hits"] += 1
            else:
                self.stats["cache_misses"] += 1


# 全局实例
_remote_file_manager_instance: RemoteFileManager | None = None
_remote_file_manager_lock = threading.Lock()


def get_remote_file_manager() -> RemoteFileManager:
    """获取全局RemoteFileManager实例"""
    global _remote_file_manager_instance
    if _remote_file_manager_instance is None:
        with _remote_file_manager_lock:
            if _remote_file_manager_instance is None:
                _remote_file_manager_instance = RemoteFileManager()
    return _remote_file_manager_instance
