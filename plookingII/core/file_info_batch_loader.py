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


class DirectoryImageListCache:
    """目录图片列表缓存：以目录 mtime 为失效依据，避免重复扫描+排序

    照片浏览会话中同一文件夹的图片列表很少变化；目录 mtime 在
    文件被添加/删除时会更新，因此可安全作为缓存失效依据。

    用途：文件夹级导航（跳转/跳过/回退）反复扫描相邻文件夹时，
    命中缓存可跳过 NSDirectoryEnumerator 全量枚举与排序。

    同时维护"目录是否含图"布尔缓存：目录树深度扫描阶段对每个目录
    只枚举一次，之后 _dir_contains_images 直接命中布尔结果，避免
    "先判断是否含图、再枚举图片列表"的两轮全量枚举。
    """

    def __init__(self, max_size: int = 64):
        """初始化缓存

        Args:
            max_size: 最大缓存目录数（LRU 淘汰）
        """
        self.max_size = max_size
        # 内部以不可变元组保存图片列表，对外返回副本：
        # 防止调用方（如 main_window.images）原地 pop/修改污染共享缓存
        self._cache: OrderedDict[str, tuple[float, tuple[str, ...]]] = OrderedDict()  # dir -> (mtime, images)
        # 含图布尔缓存：dir -> (mtime, has_images)
        self._contains_cache: OrderedDict[str, tuple[float, bool]] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, dir_path: str) -> list[str] | None:
        """获取缓存的图片列表；目录 mtime 变化或不存在时返回 None"""
        with self._lock:
            entry = self._cache.get(dir_path)
            if entry is None:
                return None
            mtime, images = entry
            try:
                current_mtime = os.stat(dir_path).st_mtime
            except OSError:
                current_mtime = -1.0
            if abs(current_mtime - mtime) > 1e-9:
                del self._cache[dir_path]
                return None
            # LRU：移动到末尾
            self._cache.move_to_end(dir_path)
            # 返回副本：缓存内部元组保持不可变，调用方修改结果不影响缓存
            return list(images)

    def put(self, dir_path: str, mtime: float, images: list[str]) -> None:
        """写入缓存条目"""
        with self._lock:
            if dir_path in self._cache:
                del self._cache[dir_path]
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            # 以不可变元组存储，杜绝外部引用突变
            self._cache[dir_path] = (mtime, tuple(images))

    def get_contains(self, dir_path: str) -> bool | None:
        """获取目录是否含图的布尔缓存；mtime 变化或不存在时返回 None"""
        with self._lock:
            entry = self._contains_cache.get(dir_path)
            if entry is None:
                return None
            mtime, has_images = entry
            try:
                current_mtime = os.stat(dir_path).st_mtime
            except OSError:
                current_mtime = -1.0
            if abs(current_mtime - mtime) > 1e-9:
                del self._contains_cache[dir_path]
                return None
            # LRU：移动到末尾
            self._contains_cache.move_to_end(dir_path)
            return has_images

    def put_contains(self, dir_path: str, mtime: float, has_images: bool) -> None:
        """写入含图布尔缓存条目"""
        with self._lock:
            if dir_path in self._contains_cache:
                del self._contains_cache[dir_path]
            while len(self._contains_cache) >= self.max_size:
                self._contains_cache.popitem(last=False)
            self._contains_cache[dir_path] = (mtime, bool(has_images))

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._contains_cache.clear()


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
        self._dir_images_cache = DirectoryImageListCache()
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
        """扫描目录并获取文件信息（使用 NSDirectoryEnumerator 优化）

        macOS NSFileManager.enumerator 底层使用 getattrlistbulk()，
        批量预取文件属性，比 os.scandir() + 逐文件 stat() 快 3-5x。

        注意：仅扫描 dir_path 本身的直接子项，不递归进入任何子目录
        （与 _scan_directory_fallback 的 os.scandir 行为保持一致）。
        递归扫描会导致父目录的图片列表混入子目录（如“精选”目录）中的图片，
        破坏“按文件夹浏览”的核心逻辑。

        Args:
            dir_path: 目录路径
            filter_exts: 过滤的文件扩展名列表（小写，不含点号），None 表示不过滤

        Returns:
            文件信息列表
        """
        if not os.path.isdir(dir_path):
            return []

        filter_exts_lower = tuple(ext.lower().lstrip(".") for ext in (filter_exts or ()))
        file_infos = []

        try:
            # 使用 NSFileManager.enumeratorAtURL 批量预取文件属性
            # NSURLFileSizeKey, NSURLContentModificationDateKey, NSURLIsDirectoryKey, NSURLIsRegularFileKey
            # 底层调用 getattrlistbulk() — macOS 专属批量属性获取
            from Foundation import (
                NSURL,
                NSDirectoryEnumerationSkipsHiddenFiles,
                NSDirectoryEnumerationSkipsSubdirectoryDescendants,
                NSFileManager,
                NSURLContentModificationDateKey,
                NSURLFileSizeKey,
                NSURLIsDirectoryKey,
                NSURLIsRegularFileKey,
            )

            folder_url = NSURL.fileURLWithPath_(dir_path)
            keys = [
                NSURLFileSizeKey,
                NSURLContentModificationDateKey,
                NSURLIsDirectoryKey,
                NSURLIsRegularFileKey,
            ]
            enumerator = (
                NSFileManager.defaultManager().enumeratorAtURL_includingPropertiesForKeys_options_errorHandler_(
                    folder_url,
                    keys,
                    NSDirectoryEnumerationSkipsHiddenFiles | NSDirectoryEnumerationSkipsSubdirectoryDescendants,
                    None,
                )
            )

            if enumerator is None:
                # 回退到 os.scandir
                return self._scan_directory_fallback(dir_path, filter_exts_lower)

            scan_time = time.time()
            for url in enumerator:
                try:
                    # resourceValuesForKeys 从 NSDirectoryEnumerator 预取缓存读取，不触发 I/O
                    values, _ = url.resourceValuesForKeys_error_(keys, None)
                    if values is None:
                        continue

                    is_dir = values.get(NSURLIsDirectoryKey, False)
                    if is_dir:
                        continue

                    is_file = values.get(NSURLIsRegularFileKey, False)
                    if not is_file:
                        continue

                    path = url.path()
                    name = url.lastPathComponent()

                    # 检查隐藏文件（NSDirectoryEnumerationSkipsHiddenFiles 已过滤，
                    # 但部分隐藏文件可能漏过，做二次检查）
                    if name.startswith("."):
                        continue

                    # 过滤扩展名
                    if filter_exts_lower:
                        ext = os.path.splitext(name)[1].lower().lstrip(".")
                        if ext not in filter_exts_lower:
                            continue

                    # 从预取缓存获取大小和修改时间
                    file_size = values.get(NSURLFileSizeKey, 0)
                    mtime_val = values.get(NSURLContentModificationDateKey)

                    size_bytes = int(file_size) if file_size else 0
                    mtime = mtime_val.timeIntervalSince1970() if mtime_val else 0.0

                    info = FileInfo(
                        path=path,
                        size_bytes=size_bytes,
                        size_mb=size_bytes / (1024 * 1024),
                        extension=os.path.splitext(name)[1].lower().lstrip("."),
                        exists=True,
                        is_file=True,
                        is_dir=False,
                        mtime=mtime,
                        cached_at=scan_time,
                    )
                    file_infos.append(info)

                except Exception:
                    continue

        except Exception as e:
            logger.warning("NSDirectoryEnumerator 扫描失败 %s: %s，回退到 os.scandir", dir_path, e)
            return self._scan_directory_fallback(dir_path, filter_exts_lower)

        # 缓存文件信息
        for info in file_infos:
            self.cache.put(info)

        return file_infos

    def get_directory_images(self, dir_path: str, filter_exts: tuple[str, ...] | None = None) -> list[str]:
        """获取目录内按文件名排序的图片路径列表（目录级缓存）

        以目录 mtime 作为缓存失效依据：会话内重复访问同一文件夹时，
        直接返回缓存的排序结果，跳过目录枚举与排序。mtime 变化
        （文件增删）时自动失效并重新扫描。

        Args:
            dir_path: 目录路径
            filter_exts: 过滤的文件扩展名列表（小写，不含点号），None 表示不过滤

        Returns:
            图片文件路径列表（按文件名排序）
        """
        if not os.path.isdir(dir_path):
            return []

        try:
            mtime = os.stat(dir_path).st_mtime
        except OSError:
            mtime = -1.0

        cached = self._dir_images_cache.get(dir_path)
        if cached is not None:
            return cached

        file_infos = self.scan_directory(dir_path, filter_exts=filter_exts)
        images = [info.path for info in file_infos if info.is_file]
        images.sort()
        self._dir_images_cache.put(dir_path, mtime, images)
        return images

    def directory_contains_images(self, dir_path: str, filter_exts: tuple[str, ...] | None = None) -> bool:
        """判断目录是否包含图片（目录级布尔缓存）

        深度扫描阶段对目录树逐目录判断"是否含图"时，首次枚举后写入
        布尔缓存；后续重复判断（如阶段2深扫与阶段1浅扫重叠、邻目录
        预扫描）直接命中，避免对同一目录反复全量枚举。

        顺带将本次枚举到的图片列表写入列表缓存，使随后的
        get_directory_images 直接命中，进一步消除重复枚举。

        Args:
            dir_path: 目录路径
            filter_exts: 过滤的文件扩展名列表（小写，不含点号），None 表示不过滤

        Returns:
            目录是否包含图片
        """
        if not os.path.isdir(dir_path):
            return False

        try:
            mtime = os.stat(dir_path).st_mtime
        except OSError:
            mtime = -1.0

        cached = self._dir_images_cache.get_contains(dir_path)
        if cached is not None:
            return cached

        file_infos = self.scan_directory(dir_path, filter_exts=filter_exts)
        images = [info.path for info in file_infos if info.is_file]
        has_images = bool(images)

        # 顺带填充列表缓存：后续 get_directory_images 直接命中
        if images:
            images.sort()
            self._dir_images_cache.put(dir_path, mtime, images)
        self._dir_images_cache.put_contains(dir_path, mtime, has_images)
        return has_images

    def _scan_directory_fallback(self, dir_path: str, filter_exts_lower: tuple[str, ...]) -> list[FileInfo]:
        """回退方案：os.scandir() + 逐文件 stat()

        Args:
            dir_path: 目录路径
            filter_exts_lower: 小写扩展名过滤元组

        Returns:
            文件信息列表
        """
        file_infos = []
        try:
            with os.scandir(dir_path) as entries:
                for entry in entries:
                    try:
                        if entry.name.startswith("."):
                            continue

                        if filter_exts_lower:
                            ext = os.path.splitext(entry.name)[1].lower().lstrip(".")
                            if ext not in filter_exts_lower:
                                continue

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
                            cached_at=time.time(),
                        )
                        file_infos.append(info)

                    except OSError:
                        continue
        except (OSError, PermissionError) as e:
            logger.warning("Failed to scan directory %s: %s", dir_path, e)
            return []

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
        # 始终提取扩展名（即使文件不存在）
        ext = os.path.splitext(file_path)[1].lower().lstrip(".")

        try:
            import stat

            try:
                stat_info = os.stat(file_path)
            except OSError:
                return FileInfo(path=file_path, extension=ext, exists=False, cached_at=time.time())

            mode = stat_info.st_mode
            return FileInfo(
                path=file_path,
                size_bytes=stat_info.st_size,
                size_mb=stat_info.st_size / (1024 * 1024),
                extension=ext,
                exists=True,
                is_file=stat.S_ISREG(mode),
                is_dir=stat.S_ISDIR(mode),
                mtime=stat_info.st_mtime,
                cached_at=time.time(),
            )

        except (OSError, PermissionError) as e:
            logger.debug("Failed to load file info for %s: %s", file_path, e)
            return FileInfo(path=file_path, extension=ext, exists=False, cached_at=time.time())

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
                # 即使失败也提取扩展名
                ext = os.path.splitext(file_path)[1].lower().lstrip(".")
                result[file_path] = FileInfo(path=file_path, extension=ext, exists=False, cached_at=time.time())

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
            _global_loader._dir_images_cache.clear()
        _global_loader = None


__all__ = [
    "DirectoryImageListCache",
    "FileInfo",
    "FileInfoBatchLoader",
    "FileInfoCache",
    "get_file_info_loader",
    "reset_file_info_loader",
]
