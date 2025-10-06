"""
网络缓存管理系统

负责管理远程文件的本地缓存，包括缓存策略、过期管理、空间控制等。
"""

import hashlib
import json
import os
import shutil
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum

from ..config.manager import get_config
from .enhanced_logging import LogCategory, LogLevel, get_enhanced_logger
from .error_handling import ErrorCategory, error_context
from .remote_file_detector import get_remote_detector


class CacheStrategy(Enum):
    """缓存策略枚举"""
    LRU = "lru"           # 最近最少使用
    LFU = "lfu"           # 最少使用频率
    SIZE_BASED = "size"   # 基于大小
    TIME_BASED = "time"   # 基于时间

@dataclass
class CacheEntry:
    """缓存条目数据类"""
    remote_path: str
    local_path: str
    file_size: int
    created_time: float
    last_access_time: float
    access_count: int
    checksum: str
    is_valid: bool = True

class NetworkCache:
    """
    网络缓存管理器

    功能：
    1. 远程文件本地缓存
    2. 缓存策略管理
    3. 过期缓存清理
    4. 缓存空间控制
    5. 缓存一致性检查
    """

    def __init__(self, cache_size_mb: int = None):
        self.logger = get_enhanced_logger()
        self.remote_detector = get_remote_detector()

        # 配置参数
        self.cache_size_mb = cache_size_mb or get_config("network_cache.size_mb", 256)
        self.max_cache_size = self.cache_size_mb * 1024 * 1024  # 转换为字节
        self.cache_ttl = get_config("network_cache.ttl_seconds", 3600)  # 1小时
        self.cleanup_threshold = get_config("network_cache.cleanup_threshold", 0.8)  # 80%
        self.cache_strategy = CacheStrategy(get_config("network_cache.strategy", "lru"))

        # 缓存目录
        self.cache_dir = self._get_cache_directory()
        self.metadata_file = os.path.join(self.cache_dir, "cache_metadata.json")

        # 缓存索引
        self.cache_index: dict[str, CacheEntry] = {}
        self.access_order: OrderedDict[str, float] = OrderedDict()  # LRU支持
        self.access_counts: dict[str, int] = {}  # LFU支持

        # 线程安全
        self.cache_lock = threading.RLock()
        self.metadata_lock = threading.RLock()

        # 统计信息
        self.stats = {
            "total_cached_files": 0,
            "total_cache_size": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_evictions": 0,
            "last_cleanup": 0.0
        }

        # 初始化
        self._ensure_cache_directory()
        self._load_metadata()
        self.cleanup_expired_cache()

        self.logger.log(LogLevel.DEBUG,
            LogCategory.SYSTEM,
            f"NetworkCache initialized: {self.cache_size_mb}MB, strategy={self.cache_strategy.value}"
        )

    def cache_remote_file(self, remote_path: str) -> str | None:
        """
        缓存远程文件到本地

        Args:
            remote_path: 远程文件路径

        Returns:
            Optional[str]: 本地缓存路径，如果失败则返回None
        """
        try:
            with error_context("remote_file_cache", ErrorCategory.CACHE):
                # 检查是否为远程路径
                if not self.remote_detector.is_remote_path(remote_path):
                    return None

                # 生成缓存键和本地路径
                cache_key = self._generate_cache_key(remote_path)
                local_path = self._get_local_cache_path(cache_key)

                # 检查是否已缓存
                with self.cache_lock:
                    if cache_key in self.cache_index:
                        entry = self.cache_index[cache_key]
                        if entry.is_valid and os.path.exists(local_path):
                            # 更新访问信息
                            self._update_access_info(cache_key)
                            with self.metadata_lock:
                                self.stats["cache_hits"] += 1
                            return local_path

                # 缓存文件
                success = self._copy_file_to_cache(remote_path, local_path)
                if not success:
                    return None

                # 获取文件信息
                file_size = os.path.getsize(local_path)
                checksum = self._calculate_checksum(local_path)

                # 创建缓存条目
                entry = CacheEntry(
                    remote_path=remote_path,
                    local_path=local_path,
                    file_size=file_size,
                    created_time=time.time(),
                    last_access_time=time.time(),
                    access_count=1,
                    checksum=checksum
                )

                # 添加到索引
                with self.cache_lock:
                    self.cache_index[cache_key] = entry
                    self._update_access_info(cache_key)

                    # 检查缓存空间
                    self._ensure_cache_space(file_size)

                    # 更新统计信息
                    with self.metadata_lock:
                        self.stats["total_cached_files"] += 1
                        self.stats["total_cache_size"] += file_size
                        self.stats["cache_misses"] += 1

                # 保存元数据
                self._save_metadata()

                self.logger.log(LogLevel.DEBUG,
                    LogCategory.CACHE,
                    f"File cached: {remote_path} -> {local_path} ({file_size} bytes)"
                )

                return local_path

        except Exception as e:
            self.logger.log_error(e, "remote_file_cache")
            return None

    def get_cached_path(self, remote_path: str) -> str | None:
        """
        获取缓存的本地路径

        Args:
            remote_path: 远程文件路径

        Returns:
            Optional[str]: 本地缓存路径，如果未缓存则返回None
        """
        try:
            with error_context("cached_path_lookup", ErrorCategory.CACHE):
                cache_key = self._generate_cache_key(remote_path)

                with self.cache_lock:
                    if cache_key in self.cache_index:
                        entry = self.cache_index[cache_key]
                        if entry.is_valid and os.path.exists(entry.local_path):
                            # 更新访问信息
                            self._update_access_info(cache_key)
                            with self.metadata_lock:
                                self.stats["cache_hits"] += 1
                            return entry.local_path

                with self.metadata_lock:
                    self.stats["cache_misses"] += 1

                return None

        except Exception as e:
            self.logging.getLogger(__name__).log_error(e, "cached_path_lookup")
            return None

    def is_cached(self, remote_path: str) -> bool:
        """检查文件是否已缓存"""
        return self.get_cached_path(remote_path) is not None

    def remove_cached_file(self, remote_path: str) -> bool:
        """
        移除缓存的文件

        Args:
            remote_path: 远程文件路径

        Returns:
            bool: 是否成功移除
        """
        try:
            with error_context("cached_file_removal", ErrorCategory.CACHE):
                cache_key = self._generate_cache_key(remote_path)

                with self.cache_lock:
                    if cache_key in self.cache_index:
                        entry = self.cache_index[cache_key]

                        # 删除本地文件
                        if os.path.exists(entry.local_path):
                            os.remove(entry.local_path)

                        # 从索引中移除
                        del self.cache_index[cache_key]

                        # 清理访问信息
                        if cache_key in self.access_order:
                            del self.access_order[cache_key]
                        if cache_key in self.access_counts:
                            del self.access_counts[cache_key]

                        # 更新统计信息
                        with self.metadata_lock:
                            self.stats["total_cached_files"] -= 1
                            self.stats["total_cache_size"] -= entry.file_size

                        self._save_metadata()
                        return True

                return False

        except Exception as e:
            self.logging.getLogger(__name__).log_error(e, "cached_file_removal")
            return False

    def cleanup_expired_cache(self):
        """清理过期缓存"""
        try:
            with error_context("expired_cache_cleanup", ErrorCategory.CACHE):
                current_time = time.time()
                expired_keys = []

                with self.cache_lock:
                    for cache_key, entry in self.cache_index.items():
                        if current_time - entry.last_access_time > self.cache_ttl:
                            expired_keys.append(cache_key)

                # 删除过期缓存
                for cache_key in expired_keys:
                    entry = self.cache_index[cache_key]
                    if os.path.exists(entry.local_path):
                        os.remove(entry.local_path)
                    del self.cache_index[cache_key]

                    # 清理访问信息
                    if cache_key in self.access_order:
                        del self.access_order[cache_key]
                    if cache_key in self.access_counts:
                        del self.access_counts[cache_key]

                if expired_keys:
                    with self.metadata_lock:
                        self.stats["total_cached_files"] -= len(expired_keys)
                        self.stats["last_cleanup"] = current_time

                    self._save_metadata()

                    self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

        except Exception as e:
            self.logger.error(f"Failed to cleanup expired cache: {e}")

    def clear_all_cache(self):
        """清空所有缓存"""
        try:
            with error_context("clear_all_cache", ErrorCategory.CACHE):
                with self.cache_lock:
                    # 删除所有缓存文件
                    for entry in self.cache_index.values():
                        if os.path.exists(entry.local_path):
                            os.remove(entry.local_path)

                    # 清空索引
                    self.cache_index.clear()
                    self.access_order.clear()
                    self.access_counts.clear()

                    # 重置统计信息
                    with self.metadata_lock:
                        self.stats["total_cached_files"] = 0
                        self.stats["total_cache_size"] = 0
                        self.stats["cache_hits"] = 0
                        self.stats["cache_misses"] = 0
                        self.stats["cache_evictions"] = 0

                self._save_metadata()

                self.logger.log(LogLevel.INFO, LogCategory.SYSTEM, "All cache cleared")

        except Exception as e:
            self.logger.log_error(e, "clear_all_cache")

    def get_cache_stats(self) -> dict[str, any]:
        """获取缓存统计信息"""
        with self.metadata_lock:
            stats = self.stats.copy()
            stats["cache_hit_rate"] = (
                stats["cache_hits"] / (stats["cache_hits"] + stats["cache_misses"])
                if (stats["cache_hits"] + stats["cache_misses"]) > 0 else 0.0
            )
            stats["cache_usage_mb"] = stats["total_cache_size"] / (1024 * 1024)
            stats["cache_usage_percent"] = (stats["total_cache_size"] / self.max_cache_size) * 100
            return stats

    def _get_cache_directory(self) -> str:
        """获取缓存目录路径"""
        if os.name == "nt":  # Windows
            cache_dir = os.path.join(os.getenv("APPDATA", ""), "PlookingII", "network_cache")
        else:  # macOS/Linux
            cache_dir = os.path.join(os.path.expanduser("~"), ".plookingII", "network_cache")

        return cache_dir

    def _ensure_cache_directory(self):
        """确保缓存目录存在"""
        os.makedirs(self.cache_dir, exist_ok=True)

    def _generate_cache_key(self, remote_path: str) -> str:
        """生成缓存键
        
        Note: MD5仅用于生成缓存键，不用于安全目的
        """
        # 使用路径的哈希值作为缓存键（非安全用途）
        return hashlib.md5(remote_path.encode("utf-8"), usedforsecurity=False).hexdigest()

    def _get_local_cache_path(self, cache_key: str) -> str:
        """获取本地缓存文件路径"""
        return os.path.join(self.cache_dir, f"{cache_key}.cache")

    def _copy_file_to_cache(self, remote_path: str, local_path: str) -> bool:
        """复制文件到缓存目录"""
        try:
            shutil.copy2(remote_path, local_path)
            return True
        except Exception as e:
            self.logger.log_error(e, f"copy_to_cache_{remote_path}")
            return False

    def _calculate_checksum(self, file_path: str) -> str:
        """计算文件校验和
        
        Note: MD5仅用于文件完整性检查，不用于安全目的
        """
        try:
            with open(file_path, "rb") as f:
                # MD5仅用于文件完整性检查，不用于加密安全
                return hashlib.md5(f.read(), usedforsecurity=False).hexdigest()
        except Exception:
            return ""

    def _update_access_info(self, cache_key: str):
        """更新访问信息"""
        current_time = time.time()

        # 更新访问时间
        self.access_order[cache_key] = current_time

        # 更新访问计数
        self.access_counts[cache_key] = self.access_counts.get(cache_key, 0) + 1

        # 更新缓存条目
        if cache_key in self.cache_index:
            self.cache_index[cache_key].last_access_time = current_time
            self.cache_index[cache_key].access_count += 1

    def _ensure_cache_space(self, required_size: int):
        """确保有足够的缓存空间"""
        current_size = self.stats["total_cache_size"]

        if current_size + required_size > self.max_cache_size:
            # 需要清理空间
            self._evict_cache_entries(required_size)

    def _evict_cache_entries(self, required_size: int):
        """根据策略清理缓存条目"""
        evicted_size = 0
        evicted_count = 0

        if self.cache_strategy == CacheStrategy.LRU:
            # LRU策略：移除最久未访问的条目
            for cache_key in list(self.access_order.keys()):
                if evicted_size >= required_size:
                    break

                if cache_key in self.cache_index:
                    entry = self.cache_index[cache_key]
                    if os.path.exists(entry.local_path):
                        os.remove(entry.local_path)

                    evicted_size += entry.file_size
                    evicted_count += 1

                    del self.cache_index[cache_key]
                    del self.access_order[cache_key]
                    if cache_key in self.access_counts:
                        del self.access_counts[cache_key]

        elif self.cache_strategy == CacheStrategy.LFU:
            # LFU策略：移除访问次数最少的条目
            sorted_keys = sorted(
                self.access_counts.keys(),
                key=lambda k: self.access_counts[k]
            )

            for cache_key in sorted_keys:
                if evicted_size >= required_size:
                    break

                if cache_key in self.cache_index:
                    entry = self.cache_index[cache_key]
                    if os.path.exists(entry.local_path):
                        os.remove(entry.local_path)

                    evicted_size += entry.file_size
                    evicted_count += 1

                    del self.cache_index[cache_key]
                    del self.access_counts[cache_key]
                    if cache_key in self.access_order:
                        del self.access_order[cache_key]

        # 更新统计信息
        with self.metadata_lock:
            self.stats["total_cached_files"] -= evicted_count
            self.stats["total_cache_size"] -= evicted_size
            self.stats["cache_evictions"] += evicted_count

        if evicted_count > 0:
            self.logger.log(LogLevel.INFO,
                LogCategory.CACHE,
                f"Evicted {evicted_count} cache entries ({evicted_size} bytes)"
            )

    def _load_metadata(self):
        """加载缓存元数据"""
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file) as f:
                    data = json.load(f)

                # 恢复缓存索引
                for key, entry_data in data.get("cache_index", {}).items():
                    entry = CacheEntry(**entry_data)
                    self.cache_index[key] = entry

                # 恢复访问信息
                self.access_order = OrderedDict(data.get("access_order", {}))
                self.access_counts = data.get("access_counts", {})

                # 恢复统计信息
                self.stats.update(data.get("stats", {}))

                self.logger.log(LogLevel.DEBUG,
                    LogCategory.CACHE,
                    f"Loaded metadata: {len(self.cache_index)} cached files"
                )

        except Exception as e:
            self.logger.log_error(e, "metadata_load")

    def _save_metadata(self):
        """保存缓存元数据"""
        try:
            with self.metadata_lock:
                data = {
                    "cache_index": {
                        key: {
                            "remote_path": entry.remote_path,
                            "local_path": entry.local_path,
                            "file_size": entry.file_size,
                            "created_time": entry.created_time,
                            "last_access_time": entry.last_access_time,
                            "access_count": entry.access_count,
                            "checksum": entry.checksum,
                            "is_valid": entry.is_valid
                        }
                        for key, entry in self.cache_index.items()
                    },
                    "access_order": dict(self.access_order),
                    "access_counts": self.access_counts,
                    "stats": self.stats
                }

            with open(self.metadata_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.logging.getLogger(__name__).log_error(e, "metadata_save")

# 全局实例
_network_cache_instance: NetworkCache | None = None
_network_cache_lock = threading.Lock()

def get_network_cache() -> NetworkCache:
    """获取全局NetworkCache实例"""
    global _network_cache_instance
    if _network_cache_instance is None:
        with _network_cache_lock:
            if _network_cache_instance is None:
                _network_cache_instance = NetworkCache()
    return _network_cache_instance
