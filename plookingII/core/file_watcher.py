#!/usr/bin/env python3
"""
文件监听器模块

提供文件系统变化监听功能，用于检测图片文件的修改、删除等操作。
支持macOS原生的文件系统事件监听。

设计思路：
1. 使用macOS的FSEvents API监听文件系统变化
2. 针对当前查看的图片文件进行精确监听
3. 检测文件修改时间、大小等变化
4. 提供回调机制通知UI更新
5. 支持批量文件夹监听（性能优化）

技术实现：
- 利用watchdog库或直接使用FSEvents
- 文件哈希验证确保文件确实变化
- 防抖机制避免频繁触发
- 线程安全的事件分发

Author: PlookingII Team
"""

import hashlib
import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from ..config.constants import APP_NAME

logger = logging.getLogger(APP_NAME)


class FileChangeType(Enum):
    """文件变化类型"""

    MODIFIED = "modified"  # 文件被修改
    DELETED = "deleted"  # 文件被删除
    CREATED = "created"  # 文件被创建
    MOVED = "moved"  # 文件被移动/重命名


@dataclass
class FileChangeEvent:
    """文件变化事件"""

    file_path: str
    change_type: FileChangeType
    timestamp: float
    old_path: str | None = None  # 用于MOVED事件
    metadata: dict = None


class FileWatcherStrategy:
    """文件监听策略基类"""

    def __init__(self):
        self.is_watching = False
        self.callbacks: list[Callable[[FileChangeEvent], None]] = []

    def add_callback(self, callback: Callable[[FileChangeEvent], None]):
        """添加事件回调"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def remove_callback(self, callback: Callable[[FileChangeEvent], None]):
        """移除事件回调"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def notify_callbacks(self, event: FileChangeEvent):
        """通知所有回调"""
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.exception("文件监听回调执行失败: %s", e)

    def start_watching(self, file_path: str):
        """开始监听文件"""
        raise NotImplementedError

    def stop_watching(self):
        """停止监听"""
        raise NotImplementedError


class PollingFileWatcher(FileWatcherStrategy):
    """基于轮询的文件监听器（兜底方案）

    优点：简单可靠，跨平台
    缺点：CPU占用高，延迟大
    """

    def __init__(self, poll_interval: float = 1.0):
        super().__init__()
        self.poll_interval = poll_interval
        self.watched_files: dict[str, dict] = {}  # path -> {mtime, size, hash}
        self.poll_thread: threading.Thread | None = None
        self.stop_event = threading.Event()

    def start_watching(self, file_path: str):
        """开始监听文件"""
        if not os.path.exists(file_path):
            logger.warning("要监听的文件不存在: %s", file_path)
            return

        # 记录文件初始状态
        try:
            stat = os.stat(file_path)
            file_hash = self._calculate_file_hash(file_path)
            self.watched_files[file_path] = {"mtime": stat.st_mtime, "size": stat.st_size, "hash": file_hash}

            if not self.is_watching:
                self._start_polling()

        except Exception as e:
            logger.exception("开始监听文件失败 %s: %s", file_path, e)

    def stop_watching(self):
        """停止监听"""
        self.stop_event.set()
        if self.poll_thread and self.poll_thread.is_alive():
            self.poll_thread.join(timeout=2.0)
        self.is_watching = False
        self.watched_files.clear()

    def remove_file(self, file_path: str):
        """移除对特定文件的监听"""
        if file_path in self.watched_files:
            del self.watched_files[file_path]

    def _start_polling(self):
        """启动轮询线程"""
        if self.is_watching:
            return

        self.is_watching = True
        self.stop_event.clear()
        self.poll_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.poll_thread.start()
        logger.info("文件监听轮询已启动")

    def _polling_loop(self):
        """轮询循环"""
        while not self.stop_event.wait(self.poll_interval):
            try:
                self._check_files()
            except Exception as e:
                logger.exception("文件监听轮询错误: %s", e)

    def _check_files(self):
        """检查所有监听的文件"""
        files_to_remove = []

        for file_path, old_info in list(self.watched_files.items()):
            try:
                if not os.path.exists(file_path):
                    # 文件被删除
                    event = FileChangeEvent(
                        file_path=file_path, change_type=FileChangeType.DELETED, timestamp=time.time()
                    )
                    self.notify_callbacks(event)
                    files_to_remove.append(file_path)
                    continue

                # 检查文件是否变化
                stat = os.stat(file_path)
                current_mtime = stat.st_mtime
                current_size = stat.st_size

                if current_mtime != old_info["mtime"] or current_size != old_info["size"]:
                    # 文件可能被修改，进一步验证哈希
                    current_hash = self._calculate_file_hash(file_path)
                    if current_hash != old_info["hash"]:
                        # 确认文件内容发生变化
                        event = FileChangeEvent(
                            file_path=file_path,
                            change_type=FileChangeType.MODIFIED,
                            timestamp=time.time(),
                            metadata={
                                "old_mtime": old_info["mtime"],
                                "new_mtime": current_mtime,
                                "old_size": old_info["size"],
                                "new_size": current_size,
                            },
                        )
                        self.notify_callbacks(event)

                        # 更新记录的文件信息
                        self.watched_files[file_path] = {
                            "mtime": current_mtime,
                            "size": current_size,
                            "hash": current_hash,
                        }

            except Exception as e:
                logger.debug("检查文件 %s 时出错: %s", file_path, e)

        # 清理已删除的文件
        for file_path in files_to_remove:
            del self.watched_files[file_path]

    def _calculate_file_hash(self, file_path: str, chunk_size: int = 8192) -> str:
        """计算文件哈希值（仅前64KB，性能优化）

        Note: MD5用于文件变化检测，不用于安全目的
        """
        try:
            # MD5仅用于文件变化检测，不用于加密安全
            hash_md5 = hashlib.md5(usedforsecurity=False)
            with open(file_path, "rb") as f:
                # 只读取前64KB计算哈希，对图片文件足够检测变化
                chunk = f.read(min(chunk_size * 8, 65536))
                hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.debug("计算文件哈希失败 %s: %s", file_path, e)
            return ""


try:
    # 尝试导入watchdog库（更高效的文件监听）
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    class WatchdogFileWatcher(FileWatcherStrategy, FileSystemEventHandler):
        """基于watchdog的文件监听器（推荐方案）

        优点：高效，实时响应，跨平台
        缺点：需要额外依赖
        """

        def __init__(self):
            super().__init__()
            self.observer = Observer()
            self.watched_files: set[str] = set()
            self.watched_dirs: dict[str, int] = {}  # dir -> watch_count

        def start_watching(self, file_path: str):
            """开始监听文件"""
            if not os.path.exists(file_path):
                logger.warning("要监听的文件不存在: %s", file_path)
                return

            file_dir = os.path.dirname(file_path)
            self.watched_files.add(file_path)

            # 如果该目录还没有被监听，添加监听
            if file_dir not in self.watched_dirs:
                try:
                    self.observer.schedule(self, file_dir, recursive=False)
                    self.watched_dirs[file_dir] = 1

                    if not self.is_watching:
                        self.observer.start()
                        self.is_watching = True
                        logger.info("Watchdog文件监听已启动")

                except Exception as e:
                    logger.exception("添加目录监听失败 %s: %s", file_dir, e)
            else:
                self.watched_dirs[file_dir] += 1

        def stop_watching(self):
            """停止监听"""
            if self.is_watching:
                try:
                    self.observer.stop()
                    self.observer.join(timeout=2.0)
                except Exception as e:
                    logger.exception("停止文件监听失败: %s", e)

                self.is_watching = False
                self.watched_files.clear()
                self.watched_dirs.clear()
                logger.info("文件监听已停止")

        def _rebuild_directory_watches(self):
            """重建目录监听（移除不需要的目录）"""
            try:
                if not self.is_watching:
                    return

                # 停止所有当前监听
                self.observer.unschedule_all()

                # 重新添加仍需要的目录监听
                for file_dir in self.watched_dirs:
                    if self.watched_dirs[file_dir] > 0:
                        self.observer.schedule(self, file_dir, recursive=False)
                        logger.debug("重新添加目录监听: %s", file_dir)

            except Exception as e:
                logger.exception("重建目录监听失败: %s", e)

        def remove_file(self, file_path: str):
            """移除对特定文件的监听"""
            if file_path in self.watched_files:
                self.watched_files.remove(file_path)
                file_dir = os.path.dirname(file_path)
                if file_dir in self.watched_dirs:
                    self.watched_dirs[file_dir] -= 1
                    if self.watched_dirs[file_dir] <= 0:
                        del self.watched_dirs[file_dir]
                        # 实际移除目录监听（优化版本）
                        try:
                            # 由于watchdog的API限制，简单的方法是重建所有监听
                            self._rebuild_directory_watches()
                        except Exception as e:
                            logger.warning("重建目录监听失败: %s", e)

        def on_modified(self, event):
            """文件修改事件"""
            if not event.is_directory and event.src_path in self.watched_files:
                file_event = FileChangeEvent(
                    file_path=event.src_path, change_type=FileChangeType.MODIFIED, timestamp=time.time()
                )
                self.notify_callbacks(file_event)

        def on_deleted(self, event):
            """文件删除事件"""
            if not event.is_directory and event.src_path in self.watched_files:
                file_event = FileChangeEvent(
                    file_path=event.src_path, change_type=FileChangeType.DELETED, timestamp=time.time()
                )
                self.notify_callbacks(file_event)

        def on_moved(self, event):
            """文件移动事件"""
            if not event.is_directory:
                if event.src_path in self.watched_files:
                    # 监听的文件被移动
                    file_event = FileChangeEvent(
                        file_path=event.dest_path,
                        change_type=FileChangeType.MOVED,
                        timestamp=time.time(),
                        old_path=event.src_path,
                    )
                    self.notify_callbacks(file_event)

                    # 更新监听文件列表
                    self.watched_files.remove(event.src_path)
                    self.watched_files.add(event.dest_path)

except ImportError:
    # watchdog不可用，使用None标记
    WatchdogFileWatcher = None


class FileWatcher:
    """文件监听器管理类

    自动选择最佳的监听策略，提供统一的接口。
    """

    def __init__(self, strategy: str = "auto"):
        """初始化文件监听器

        Args:
            strategy: 监听策略 ("auto", "watchdog", "polling")
        """
        self.strategy_name = strategy
        self.watcher: FileWatcherStrategy | None = None
        self._create_watcher()

    def _create_watcher(self):
        """创建监听器实例"""
        if self.strategy_name == "auto":
            # 自动选择最佳策略
            if WatchdogFileWatcher is not None:
                self.watcher = WatchdogFileWatcher()
                self.strategy_name = "watchdog"
                logger.info("使用Watchdog文件监听策略")
            else:
                self.watcher = PollingFileWatcher()
                self.strategy_name = "polling"
                logger.info("使用轮询文件监听策略")
        elif self.strategy_name == "watchdog":
            if WatchdogFileWatcher is not None:
                self.watcher = WatchdogFileWatcher()
            else:
                logger.warning("Watchdog不可用，回退到轮询策略")
                self.watcher = PollingFileWatcher()
                self.strategy_name = "polling"
        elif self.strategy_name == "polling":
            self.watcher = PollingFileWatcher()
        else:
            raise ValueError(f"不支持的监听策略: {self.strategy_name}")

    def add_callback(self, callback: Callable[[FileChangeEvent], None]):
        """添加文件变化回调"""
        if self.watcher:
            self.watcher.add_callback(callback)

    def remove_callback(self, callback: Callable[[FileChangeEvent], None]):
        """移除文件变化回调"""
        if self.watcher:
            self.watcher.remove_callback(callback)

    def watch_file(self, file_path: str):
        """开始监听文件"""
        if self.watcher:
            self.watcher.start_watching(file_path)

    def unwatch_file(self, file_path: str):
        """停止监听特定文件"""
        if self.watcher and hasattr(self.watcher, "remove_file"):
            self.watcher.remove_file(file_path)

    def stop(self):
        """停止所有监听"""
        if self.watcher:
            self.watcher.stop_watching()

    @property
    def is_active(self) -> bool:
        """是否正在监听"""
        return self.watcher and self.watcher.is_watching
