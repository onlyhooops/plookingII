"""
测试 core/remote_file_detector.py

覆盖：远程路径判定、挂载类型缓存、延迟测量缓存、SMB 信息解析、清缓存。
"""

from unittest.mock import MagicMock, patch

import pytest

from plookingII.core.remote_file_detector import MountType, RemoteFileDetector


@pytest.fixture
def detector(monkeypatch):
    """构造隔离日志的 RemoteFileDetector 实例"""
    monkeypatch.setattr("plookingII.core.remote_file_detector.get_enhanced_logger", lambda: MagicMock())
    det = RemoteFileDetector()
    det.logger = MagicMock()
    return det


class TestRemoteFileDetector:
    def test_is_remote_path_local(self, detector, tmp_path):
        """本地路径判定为非远程"""
        with patch.object(detector, "_detect_mount_type", return_value=MountType.LOCAL):
            assert detector.is_remote_path(str(tmp_path)) is False

    def test_is_remote_path_remote(self, detector, tmp_path):
        """SMB 路径判定为远程"""
        with patch.object(detector, "_detect_mount_type", return_value=MountType.SMB):
            assert detector.is_remote_path(str(tmp_path)) is True

    def test_is_remote_path_cached(self, detector, tmp_path):
        """缓存有效期内不重复检测"""
        detect = MagicMock(return_value=MountType.SMB)
        with patch.object(detector, "_detect_mount_type", detect):
            assert detector.is_remote_path(str(tmp_path)) is True
            assert detector.is_remote_path(str(tmp_path)) is True

        assert detect.call_count == 1

    def test_get_mount_type_cached(self, detector, tmp_path):
        """挂载类型缓存命中"""
        detect = MagicMock(return_value=MountType.NFS)
        with patch.object(detector, "_detect_mount_type", detect):
            assert detector.get_mount_type(str(tmp_path)) == MountType.NFS
            assert detector.get_mount_type(str(tmp_path)) == MountType.NFS

        assert detect.call_count == 1

    def test_get_network_latency_local_is_zero(self, detector, tmp_path):
        """本地路径延迟为 0"""
        with patch.object(detector, "is_remote_path", return_value=False):
            assert detector.get_network_latency(str(tmp_path)) == 0.0

    def test_get_network_latency_cached(self, detector, tmp_path):
        """延迟结果缓存，不重复测量"""
        detector._latency_cache[str(tmp_path)] = 42.0
        with patch.object(detector, "_measure_latency", return_value=99.0) as measure:
            assert detector.get_network_latency(str(tmp_path)) == 42.0

        measure.assert_not_called()

    def test_is_high_latency(self, detector, tmp_path):
        """高于阈值判定为高延迟"""
        with patch.object(detector, "get_network_latency", return_value=150.0):
            assert detector.is_high_latency(str(tmp_path)) is True
        with patch.object(detector, "get_network_latency", return_value=10.0):
            assert detector.is_high_latency(str(tmp_path)) is False

    def test_get_mount_info_local(self, detector, tmp_path):
        """本地目录返回可访问的 MountInfo"""
        with patch.object(detector, "_detect_mount_type", return_value=MountType.LOCAL), patch.object(
            detector, "_measure_latency", return_value=5.0
        ) as measure:
            info = detector.get_mount_info(str(tmp_path))

        assert info is not None
        assert info.mount_type == MountType.LOCAL
        assert info.latency_ms == 0.0
        assert info.is_accessible is True
        measure.assert_not_called()

    def test_get_mount_info_smb_parses_server(self, detector, tmp_path):
        """SMB 挂载信息解析服务器与共享名"""
        with patch.object(detector, "_detect_mount_type", return_value=MountType.SMB), patch.object(
            detector, "_parse_smb_info", return_value=("server", "share")
        ):
            info = detector.get_mount_info(str(tmp_path))

        assert info is not None
        assert info.server == "server"
        assert info.share == "share"

    def test_parse_smb_info(self, detector):
        """解析 mount 输出中的 SMB 服务器与共享"""
        fake_output = (
            "map auto_home on /System/Volumes/Data/home (autofs, automounted, nobrowse)\n"
            "//server/share on /Volumes/share (smbfs, nodev, nosuid, mounted by user)\n"
        )
        with patch(
            "plookingII.core.remote_file_detector.subprocess.run",
            return_value=MagicMock(returncode=0, stdout=fake_output),
        ):
            assert detector._parse_smb_info("/Volumes/share") == ("server", "share")

    def test_parse_smb_info_no_match(self, detector):
        """无 SMB 挂载时返回空元组"""
        with patch(
            "plookingII.core.remote_file_detector.subprocess.run",
            return_value=MagicMock(returncode=0, stdout="no smb here\n"),
        ):
            assert detector._parse_smb_info("/local") == (None, None)

    def test_detect_mount_type_smb_via_df(self, detector):
        """df 输出以 // 开头判定为 SMB"""
        with patch(
            "plookingII.core.remote_file_detector.subprocess.run",
            return_value=MagicMock(returncode=0, stdout="Filesystem  Size\n//server/share  1.0G\n"),
        ):
            assert detector._detect_mount_type("/Volumes/share") == MountType.SMB

    def test_clear_cache(self, detector, tmp_path):
        """清空挂载与延迟缓存"""
        with patch.object(detector, "_detect_mount_type", return_value=MountType.SMB):
            detector.is_remote_path(str(tmp_path))
        detector._latency_cache[str(tmp_path)] = 1.0
        assert detector._mount_cache and detector._latency_cache

        detector.clear_cache()

        assert not detector._mount_cache
        assert not detector._latency_cache

    def test_get_remote_detector_singleton(self, monkeypatch):
        """全局检测器为单例"""
        monkeypatch.setattr("plookingII.core.remote_file_detector.get_enhanced_logger", lambda: MagicMock())
        import plookingII.core.remote_file_detector as rfd

        rfd._remote_detector_instance = None
        first = rfd.get_remote_detector()
        second = rfd.get_remote_detector()
        assert first is second
        rfd._remote_detector_instance = None
