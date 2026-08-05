"""
测试 core/smb_optimizer.py

覆盖：读取策略选择、批量读取、目录列表缓存、预读缓冲与淘汰、统计。
"""

from unittest.mock import MagicMock, patch

import pytest

from plookingII.core.remote_file_detector import MountType
from plookingII.core.smb_optimizer import ReadResult, ReadStrategy, SMBOptimizer


@pytest.fixture
def optimizer(monkeypatch):
    """构造隔离日志与检测器的 SMBOptimizer 实例"""
    monkeypatch.setattr("plookingII.core.smb_optimizer.get_enhanced_logger", lambda: MagicMock())
    monkeypatch.setattr("plookingII.core.smb_optimizer.get_remote_detector", lambda: MagicMock())
    monkeypatch.setattr("plookingII.core.smb_optimizer.get_config", lambda key, default=None: default)
    opt = SMBOptimizer()
    opt.logger = MagicMock()
    yield opt
    opt.shutdown()


class TestSMBOptimizer:
    def test_optimize_read_strategy_non_smb(self, optimizer):
        """非 SMB 路径返回顺序读取策略"""
        optimizer.remote_detector.get_mount_type.return_value = MountType.LOCAL
        assert optimizer.optimize_read_strategy("/local/file.jpg") == ReadStrategy.SEQUENTIAL

    def test_optimize_read_strategy_high_latency(self, optimizer):
        """高延迟：小文件批量、大文件预加载"""
        optimizer.remote_detector.get_mount_type.return_value = MountType.SMB
        optimizer.remote_detector.get_network_latency.return_value = 150.0

        assert optimizer.optimize_read_strategy("/smb/small.jpg", 500) == ReadStrategy.BATCH
        assert optimizer.optimize_read_strategy("/smb/big.jpg", 5 * 1024 * 1024) == ReadStrategy.PRELOAD

    def test_optimize_read_strategy_mid_and_low_latency(self, optimizer):
        """中延迟自适应，低延迟顺序读取"""
        optimizer.remote_detector.get_mount_type.return_value = MountType.SMB
        optimizer.remote_detector.get_network_latency.return_value = 60.0
        assert optimizer.optimize_read_strategy("/smb/x.jpg", 500) == ReadStrategy.ADAPTIVE

        optimizer.remote_detector.get_network_latency.return_value = 10.0
        assert optimizer.optimize_read_strategy("/smb/x.jpg", 500) == ReadStrategy.SEQUENTIAL

    def test_batch_read_files_empty(self, optimizer):
        """空列表直接返回空结果"""
        assert optimizer.batch_read_files([]) == []

    def test_batch_read_files_non_smb_filtered(self, optimizer):
        """非 SMB 路径被过滤，无结果"""
        optimizer.remote_detector.get_mount_type.return_value = MountType.LOCAL
        assert optimizer.batch_read_files(["/local/a.jpg"]) == []

    def test_batch_read_files_smb(self, optimizer):
        """SMB 文件批量读取并更新统计"""
        with patch.object(optimizer, "_is_smb_path", return_value=True), patch.object(
            optimizer,
            "_read_single_file",
            side_effect=[
                ReadResult(file_path="/smb/a.jpg", data=b"a", success=True, latency_ms=1.0),
                ReadResult(file_path="/smb/b.jpg", data=b"b", success=True, latency_ms=2.0),
            ],
        ):
            results = optimizer.batch_read_files(["/smb/a.jpg", "/smb/b.jpg"])

        assert len(results) == 2
        assert optimizer.stats["batch_reads"] == 1
        assert optimizer.stats["total_reads"] == 2

    def test_cache_directory_listing_local(self, optimizer, tmp_path):
        """非 SMB 目录委托给批量文件信息加载器"""
        photos = tmp_path / "photos"
        photos.mkdir()
        (photos / "a.jpg").touch()
        optimizer.remote_detector.get_mount_type.return_value = MountType.LOCAL

        listing = optimizer.cache_directory_listing(str(photos))

        assert str(photos / "a.jpg") in listing

    def test_cache_directory_listing_smb_hit(self, optimizer, tmp_path):
        """SMB 目录第二次访问命中缓存"""
        photos = tmp_path / "photos"
        photos.mkdir()
        (photos / "a.jpg").touch()
        with patch.object(optimizer, "_is_smb_path", return_value=True):
            first = optimizer.cache_directory_listing(str(photos))
            second = optimizer.cache_directory_listing(str(photos))

        assert first == second == ["a.jpg"]
        assert optimizer.stats["cache_hits"] == 1
        assert optimizer.stats["cache_misses"] == 1

    def test_preload_file_data(self, optimizer, tmp_path):
        """SMB 文件预读并可从缓存取回"""
        src = tmp_path / "data.bin"
        src.write_bytes(b"0123456789")
        with patch.object(optimizer, "_is_smb_path", return_value=True):
            assert optimizer.preload_file_data(str(src)) is True
            assert optimizer.preload_file_data(str(src)) is True  # 已缓存直接返回

        assert optimizer.get_cached_file_data(str(src)) == b"0123456789"

    def test_preload_non_smb_rejected(self, optimizer, tmp_path):
        """非 SMB 文件不预读"""
        src = tmp_path / "data.bin"
        src.write_bytes(b"x")
        with patch.object(optimizer, "_is_smb_path", return_value=False):
            assert optimizer.preload_file_data(str(src)) is False

    def test_read_ahead_eviction(self, optimizer, tmp_path):
        """预读缓冲超限时按最旧淘汰"""
        optimizer._MAX_READ_AHEAD_ENTRIES = 2
        paths = []
        for name in ("a", "b", "c"):
            p = tmp_path / name
            p.write_bytes(b"x" * 1024)
            paths.append(str(p))
        with patch.object(optimizer, "_is_smb_path", return_value=True):
            for p in paths:
                optimizer.preload_file_data(p)

        assert optimizer.get_cached_file_data(paths[0]) is None
        assert optimizer.get_cached_file_data(paths[1]) is not None
        assert optimizer.get_cached_file_data(paths[2]) is not None

    def test_clear_cache_and_stats(self, optimizer):
        """清空缓存与统计接口"""
        optimizer.directory_cache["/smb/x"] = (["a"], 0.0)
        optimizer.read_ahead_cache["/smb/y"] = b"data"

        optimizer.clear_cache()
        assert not optimizer.directory_cache
        assert not optimizer.read_ahead_cache
        assert "total_reads" in optimizer.get_performance_stats()
