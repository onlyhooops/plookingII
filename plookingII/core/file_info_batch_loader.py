#!/usr/bin/env python3
"""
批量文件信息获取工具

提供高效的批量文件信息获取功能，减少文件系统 I/O 调用次数。

主要特性：
- 批量获取文件大小、扩展名、存在性等信息
- 使用 os.scandir() 优化目录扫描性能
- 智能缓存减少重复查询
- 异步/线程池支持（可选）

Author: PlookingII Team
Date: 2025-01-XX (实验性优化)
"""

import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

from ..config.constants import APP_NAME
from ..imports import logging

logger = logging.getLogger(APP_NAME)


@dataclass
class FileInfo:
    """文件信息数据类"""

    path: str
    size_bytes: int = 0
    size_mb: float = 0.0
    extension: str = ""
    exists: bool = False
    is_file: bool = False
    is_dir: bool = False
    mtime: float = 0.0
    cached_at: float = 0.0


class FileInfoCache:
    """文件信息缓存管理器

    提供 LRU 缓存机制，减少重复的文件系统调用。
    """

    def __init__(self, max_size: int = 5000, ttl_seconds: float = 300.0):
        """初始化缓存

        Args:
            max_size: 最大缓存条目数
            ttl_seconds: 缓存有效期（秒），0 表示永不过期
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, FileInfo] = OrderedDict()
        self._lock = threading.RLock()

        logger.debug("FileInfoCache initialized: max_size=%s, ttl=%s", max_size, ttl_seconds)

    def get(self, file_path: str) -> FileInfo | None:
        """获取缓存的文件信息

        Args:
            file_path: 文件路径

        Returns:
            文件信息对象，如果不存在或已过期则返回 None
        """
        with self._lock:
            if file_path not in self._cache:
                return None

            info = self._cache[file_path]

            # 检查是否过期
            if self.ttl_seconds > 0:
                age = time.time() - info.cached_at
                if age > self.ttl_seconds:
                    del self._cache[file_path]
                    return None

            # 移到末尾（LRU）
            self._cache.move_to_end(file_path)
            return info

    def put(self, file_info: FileInfo):
        """添加文件信息到缓存

        Args:
            file_info: 文件信息对象
        """
        with self._lock:
            # 如果已存在，先移除
            if file_info.path in self._cache:
                del self._cache[file_info.path]

            # 如果缓存已满，移除最旧的
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)

            # 设置缓存时间
            file_info.cached_at = time.time()
            self._cache[file_info.path] = file_info

    def get_batch(self, file_paths: list[str]) -> dict[str, FileInfo]:
        """批量获取文件信息（优先从缓存）

        Args:
            file_paths: 文件路径列表

        Returns:
            文件路径到文件信息的映射字典
        """
        result = {}
        missing_paths = []

        with self._lock:
            for path in file_paths:
                info = self.get(path)
                if info:
                    result[path] = info
                else:
                    missing_paths.append(path)

        return result, missing_paths

    def clear(self):
        """清空缓存"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.debug("FileInfoCache cleared: removed %s entries", count)

    def get_stats(self) -> dict:
        """获取缓存统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
            }


class FileInfoBatchLoader:
    """批量文件信息加载器

    提供高效的批量文件信息获取功能。
    """

    def __init__(self, cache: FileInfoCache | None = None):
        """初始化批量加载器

        Args:
            cache: 文件信息缓存实例，None 则创建新实例
        """
        self.cache = cache or FileInfoCache()
        self._lock = threading.RLock()

        logger.debug("FileInfoBatchLoader initialized")

    def get_file_info(self, file_path: str, use_cache: bool = True) -> FileInfo:
        """获取单个文件信息

        Args:
            file_path: 文件路径
            use_cache: 是否使用缓存

        Returns:
            文件信息对象
        """
        # 尝试从缓存获取
        if use_cache:
            cached = self.cache.get(file_path)
            if cached:
                return cached

        # 从文件系统获取
        info = self._load_file_info(file_path)
        if use_cache:
            self.cache.put(info)

        return info

    def get_file_info_batch(self, file_paths: list[str], use_cache: bool = True) -> dict[str, FileInfo]:
        """批量获取文件信息

        Args:
            file_paths: 文件路径列表
            use_cache: 是否使用缓存

        Returns:
            文件路径到文件信息的映射字典
        """
        if not file_paths:
            return {}

        # 从缓存获取已有的信息
        if use_cache:
            cached, missing_paths = self.cache.get_batch(file_paths)
        else:
            cached = {}
            missing_paths = file_paths

        # 批量加载缺失的信息
        if missing_paths:
            loaded = self._load_file_info_batch(missing_paths)
            if use_cache:
                for info in loaded.values():
                    self.cache.put(info)
            cached.update(loaded)

        return cached

    def get_file_size_mb(self, file_path: str, use_cache: bool = True) -> float:
        """获取文件大小（MB）

        Args:
            file_path: 文件路径
            use_cache: 是否使用缓存

        Returns:
            文件大小（MB），失败返回 0.0
        """
        info = self.get_file_info(file_path, use_cache)
        return info.size_mb

    def get_file_extension(self, file_path: str, use_cache: bool = True) -> str:
        """获取文件扩展名

        Args:
            file_path: 文件路径
            use_cache: 是否使用缓存

        Returns:
            文件扩展名（小写，不含点号）
        """
        info = self.get_file_info(file_path, use_cache)
        return info.extension

    def scan_directory(self, dir_path: str, filter_exts: tuple[str, ...] | None = None) -> list[FileInfo]:
        """扫描目录并获取文件信息（使用 os.scandir 优化）

        Args:
            dir_path: 目录路径
            filter_exts: 过滤的文件扩展名列表（小写，不含点号），None 表示不过滤

        Returns:
            文件信息列表
        """
        if not os.path.isdir(dir_path):
            return []

        file_infos = []
        filter_exts_lower = tuple(ext.lower().lstrip(".") for ext in (filter_exts or ()))

        try:
            # 使用 os.scandir() 替代 os.listdir()，性能提升 2-3 倍
            with os.scandir(dir_path) as entries:
                for entry in entries:
                    try:
                        # 跳过隐藏文件
                        if entry.name.startswith("."):
                            continue

                        # 过滤扩展名
                        if filter_exts_lower:
                            ext = os.path.splitext(entry.name)[1].lower().lstrip(".")
                            if ext not in filter_exts_lower:
                                continue

                        # 获取文件信息
                        path = entry.path
                        stat_info = entry.stat(follow_symlinks=False)

                        info = FileInfo(
                            path=path,
                            size_bytes=stat_info.st_size,
                            size_mb=stat_info.st_size / (1024 * 1024),
                            extension=os.path.splitext(entry.name)[1].lower().lstrip("."),
                            exists=True,
                            is_file=entry.is_file(follow_symlinks=False),
                            is_dir=entry.is_dir(follow_symlinks=False),
                            mtime=stat_info.st_mtime,
                        )

                        file_infos.append(info)

                    except (OSError, PermissionError) as e:
                        logger.debug("Failed to get info for %s: %s", entry.path, e)
                        continue

        except (OSError, PermissionError) as e:
            logger.warning("Failed to scan directory %s: %s", dir_path, e)
            return []

        # 缓存文件信息
        for info in file_infos:
            self.cache.put(info)

        return file_infos

    def _load_file_info(self, file_path: str) -> FileInfo:
        """加载单个文件信息

        Args:
            file_path: 文件路径

        Returns:
            文件信息对象
        """
        try:
            if os.path.exists(file_path):
                stat_info = os.stat(file_path)
                ext = os.path.splitext(file_path)[1].lower().lstrip(".")

                return FileInfo(
                    path=file_path,
                    size_bytes=stat_info.st_size,
                    size_mb=stat_info.st_size / (1024 * 1024),
                    extension=ext,
                    exists=True,
                    is_file=os.path.isfile(file_path),
                    is_dir=os.path.isdir(file_path),
                    mtime=stat_info.st_mtime,
                )

            return FileInfo(path=file_path, exists=False)

        except (OSError, PermissionError) as e:
            logger.debug("Failed to load file info for %s: %s", file_path, e)
            return FileInfo(path=file_path, exists=False)

    def _load_file_info_batch(self, file_paths: list[str]) -> dict[str, FileInfo]:
        """批量加载文件信息

        Args:
            file_paths: 文件路径列表

        Returns:
            文件路径到文件信息的映射字典
        """
        result = {}

        for file_path in file_paths:
            try:
                info = self._load_file_info(file_path)
                result[file_path] = info
            except Exception as e:
                logger.debug("Failed to load file info for %s: %s", file_path, e)
                result[file_path] = FileInfo(path=file_path, exists=False)

        return result

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()

    def get_stats(self) -> dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "cache": self.cache.get_stats(),
        }


# 全局实例（单例模式）
_global_loader: FileInfoBatchLoader | None = None
_loader_lock = threading.Lock()


def get_file_info_loader() -> FileInfoBatchLoader:
    """获取全局文件信息加载器实例

    Returns:
        文件信息加载器实例
    """
    global _global_loader  # noqa: PLW0603  # 单例模式的合理使用

    if _global_loader is None:
        with _loader_lock:
            if _global_loader is None:
                _global_loader = FileInfoBatchLoader()

    return _global_loader


def reset_file_info_loader():
    """重置全局文件信息加载器（主要用于测试）"""
    global _global_loader  # noqa: PLW0603  # 单例模式的合理使用

    with _loader_lock:
        if _global_loader is not None:
            _global_loader.clear_cache()
        _global_loader = None


__all__ = [
    "FileInfo",
    "FileInfoBatchLoader",
    "FileInfoCache",
    "get_file_info_loader",
    "reset_file_info_loader",
]
