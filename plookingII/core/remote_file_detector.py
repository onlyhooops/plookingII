"""
远程文件系统检测器

负责检测和识别远程挂载的文件系统，特别是SMB挂载的盘符。
支持检测网络延迟、挂载类型等信息。
"""

import os
import subprocess
import threading
import time
from dataclasses import dataclass
from enum import Enum

from .enhanced_logging import LogCategory, LogLevel, get_enhanced_logger
from .error_handling import ErrorCategory, error_context


class MountType(Enum):
    """挂载类型枚举"""

    LOCAL = "local"
    SMB = "smb"
    AFP = "afp"
    NFS = "nfs"
    SSHFS = "sshfs"
    UNKNOWN = "unknown"


@dataclass
class MountInfo:
    """挂载信息数据类"""

    path: str
    mount_type: MountType
    server: str | None = None
    share: str | None = None
    latency_ms: float | None = None
    is_accessible: bool = True
    last_checked: float = 0.0


class RemoteFileDetector:
    """
    远程文件系统检测器

    功能：
    1. 检测文件路径是否为远程挂载
    2. 识别挂载类型（SMB、AFP、NFS等）
    3. 测量网络延迟
    4. 缓存挂载信息以提高性能
    """

    def __init__(self):
        self.logger = get_enhanced_logger()
        self._mount_cache: dict[str, MountInfo] = {}
        self._cache_lock = threading.RLock()
        self._latency_cache: dict[str, float] = {}
        self._latency_cache_lock = threading.RLock()

        # 缓存有效期（秒）
        self.cache_ttl = 300  # 5分钟

        # 网络延迟阈值
        self.high_latency_threshold = 100.0  # 100ms

        self.logger.log(LogLevel.DEBUG, LogCategory.SYSTEM, "RemoteFileDetector initialized")

    def is_remote_path(self, file_path: str) -> bool:
        """
        检测是否为远程路径

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否为远程路径
        """
        try:
            with error_context("remote_path_detection", ErrorCategory.FILE_SYSTEM):
                # 标准化路径
                normalized_path = os.path.normpath(file_path)

                # 检查缓存
                with self._cache_lock:
                    if normalized_path in self._mount_cache:
                        mount_info = self._mount_cache[normalized_path]
                        # 检查缓存是否过期
                        if time.time() - mount_info.last_checked < self.cache_ttl:
                            return mount_info.mount_type != MountType.LOCAL

                # 检测挂载类型
                mount_type = self._detect_mount_type(normalized_path)

                # 缓存结果
                mount_info = MountInfo(path=normalized_path, mount_type=mount_type, last_checked=time.time())

                with self._cache_lock:
                    self._mount_cache[normalized_path] = mount_info

                is_remote = mount_type != MountType.LOCAL
                self.logger.log(
                    LogLevel.DEBUG,
                    LogCategory.FILE_SYSTEM,
                    f"Path '{normalized_path}' detected as {'remote' if is_remote else 'local'} ({mount_type.value})",
                )

                return is_remote

        except Exception as e:
            self.logger.log_error(e, "remote_path_detection")
            # 发生错误时，假设为本地路径
            return False

    def get_mount_type(self, file_path: str) -> MountType:
        """
        获取挂载类型

        Args:
            file_path: 文件路径

        Returns:
            MountType: 挂载类型
        """
        try:
            with error_context("mount_type_detection", ErrorCategory.FILE_SYSTEM):
                normalized_path = os.path.normpath(file_path)

                # 检查缓存
                with self._cache_lock:
                    if normalized_path in self._mount_cache:
                        mount_info = self._mount_cache[normalized_path]
                        if time.time() - mount_info.last_checked < self.cache_ttl:
                            return mount_info.mount_type

                # 检测挂载类型
                mount_type = self._detect_mount_type(normalized_path)

                # 更新缓存
                with self._cache_lock:
                    if normalized_path in self._mount_cache:
                        self._mount_cache[normalized_path].mount_type = mount_type
                        self._mount_cache[normalized_path].last_checked = time.time()
                    else:
                        self._mount_cache[normalized_path] = MountInfo(
                            path=normalized_path, mount_type=mount_type, last_checked=time.time()
                        )

                return mount_type

        except Exception as e:
            self.logger.log_error(e, "mount_type_detection")
            return MountType.UNKNOWN

    def get_network_latency(self, file_path: str) -> float:
        """
        测量网络延迟

        Args:
            file_path: 文件路径

        Returns:
            float: 延迟时间（毫秒），-1表示无法测量
        """
        try:
            with error_context("network_latency_measurement", ErrorCategory.NETWORK):
                normalized_path = os.path.normpath(file_path)

                # 检查缓存
                with self._latency_cache_lock:
                    if normalized_path in self._latency_cache:
                        return self._latency_cache[normalized_path]

                # 如果不是远程路径，返回0延迟
                if not self.is_remote_path(normalized_path):
                    return 0.0

                # 测量延迟
                latency = self._measure_latency(normalized_path)

                # 缓存结果
                with self._latency_cache_lock:
                    self._latency_cache[normalized_path] = latency

                return latency

        except Exception as e:
            self.logger.log_error(e, "network_latency_measurement")
            return -1.0

    def get_mount_info(self, file_path: str) -> MountInfo | None:
        """
        获取完整的挂载信息

        Args:
            file_path: 文件路径

        Returns:
            Optional[MountInfo]: 挂载信息，如果无法获取则返回None
        """
        try:
            with error_context("mount_info_retrieval", ErrorCategory.FILE_SYSTEM):
                normalized_path = os.path.normpath(file_path)

                # 检查缓存
                with self._cache_lock:
                    if normalized_path in self._mount_cache:
                        mount_info = self._mount_cache[normalized_path]
                        if time.time() - mount_info.last_checked < self.cache_ttl:
                            return mount_info

                # 获取挂载信息
                mount_type = self._detect_mount_type(normalized_path)
                latency = self._measure_latency(normalized_path) if mount_type != MountType.LOCAL else 0.0

                # 解析服务器和共享信息（仅对SMB）
                server, share = None, None
                if mount_type == MountType.SMB:
                    server, share = self._parse_smb_info(normalized_path)

                mount_info = MountInfo(
                    path=normalized_path,
                    mount_type=mount_type,
                    server=server,
                    share=share,
                    latency_ms=latency,
                    is_accessible=self._check_accessibility(normalized_path),
                    last_checked=time.time(),
                )

                # 更新缓存
                with self._cache_lock:
                    self._mount_cache[normalized_path] = mount_info

                return mount_info

        except Exception as e:
            self.logger.log_error(e, "mount_info_retrieval")
            return None

    def is_high_latency(self, file_path: str) -> bool:
        """
        检查是否为高延迟路径

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否为高延迟路径
        """
        latency = self.get_network_latency(file_path)
        return latency > self.high_latency_threshold

    def clear_cache(self):
        """清空缓存"""
        with self._cache_lock:
            self._mount_cache.clear()
        with self._latency_cache_lock:
            self._latency_cache.clear()
        self.logger.log(LogLevel.INFO, LogCategory.SYSTEM, "Remote file detector cache cleared")

    def _detect_mount_type(self, file_path: str) -> MountType:
        """检测挂载类型"""
        try:
            # 获取文件系统的挂载信息
            result = subprocess.run(["df", file_path], check=False, capture_output=True, text=True, timeout=5)

            if result.returncode != 0:
                return MountType.UNKNOWN

            output_lines = result.stdout.strip().split("\n")
            if len(output_lines) < 2:
                return MountType.UNKNOWN

            # 解析挂载点信息
            mount_info = output_lines[1].split()
            if len(mount_info) < 1:
                return MountType.UNKNOWN

            mount_point = mount_info[0]

            # 检查挂载类型
            if mount_point.startswith("//"):
                # SMB挂载
                return MountType.SMB
            if mount_point.startswith("afp://"):
                # AFP挂载
                return MountType.AFP
            if ":" in mount_point and not mount_point.startswith("/"):
                # NFS挂载 (格式: server:/path)
                return MountType.NFS
            if mount_point.startswith("sshfs"):
                # SSHFS挂载
                return MountType.SSHFS
            # 本地挂载
            return MountType.LOCAL

        except Exception as e:
            self.logger.log(LogLevel.DEBUG, LogCategory.FILE_SYSTEM, f"Mount type detection failed: {e}")
            return MountType.UNKNOWN

    def _measure_latency(self, file_path: str) -> float:
        """测量网络延迟"""
        try:
            # 对于远程路径，通过尝试访问一个小的测试文件来测量延迟
            test_start = time.perf_counter()

            # 尝试列出目录（这是一个轻量级操作）
            if os.path.isdir(file_path):
                # 对于目录，尝试列出内容
                try:
                    list(os.path.listdir(file_path)[:1])  # 只获取第一个条目
                except (OSError, PermissionError):
                    # 如果无法列出，尝试访问目录本身
                    os.path.exists(file_path)
            else:
                # 对于文件，检查是否存在
                os.path.exists(file_path)

            test_end = time.perf_counter()
            return (test_end - test_start) * 1000

        except Exception as e:
            self.logger.log(LogLevel.DEBUG, LogCategory.NETWORK, f"Latency measurement failed: {e}")
            return -1.0

    def _parse_smb_info(self, file_path: str) -> tuple[str | None, str | None]:
        """解析SMB挂载的服务器和共享信息"""
        try:
            # 获取挂载信息
            result = subprocess.run(["mount"], check=False, capture_output=True, text=True, timeout=5)

            if result.returncode != 0:
                return None, None

            # 查找包含目标路径的挂载信息
            for line in result.stdout.split("\n"):
                if "smbfs" in line or "cifs" in line:
                    # 解析SMB挂载信息
                    # 格式通常为: //server/share on /mount/point (smbfs, ...)
                    parts = line.split()
                    if len(parts) >= 3:
                        mount_source = parts[0]
                        if mount_source.startswith("//"):
                            # 提取服务器和共享名
                            path_parts = mount_source[2:].split("/")
                            if len(path_parts) >= 2:
                                server = path_parts[0]
                                share = path_parts[1]
                                return server, share

            return None, None

        except Exception as e:
            self.logger.log(LogLevel.DEBUG, LogCategory.FILE_SYSTEM, f"SMB info parsing failed: {e}")
            return None, None

    def _check_accessibility(self, file_path: str) -> bool:
        """检查路径是否可访问"""
        try:
            return os.path.exists(file_path)
        except Exception:
            return False


# 全局实例
_remote_detector_instance: RemoteFileDetector | None = None
_remote_detector_lock = threading.Lock()


def get_remote_detector() -> RemoteFileDetector:
    """获取全局RemoteFileDetector实例"""
    global _remote_detector_instance  # noqa: PLW0603  # 单例模式的合理使用
    if _remote_detector_instance is None:
        with _remote_detector_lock:
            if _remote_detector_instance is None:
                _remote_detector_instance = RemoteFileDetector()
    return _remote_detector_instance
