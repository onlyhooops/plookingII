"""
测试 core/network_cache.py

覆盖：缓存命中/未命中、移除、过期清理、LRU 淘汰、元数据持久化、统计。
"""

import os
import time
from unittest.mock import MagicMock, patch

from plookingII.core.network_cache import CacheEntry, CacheStrategy, NetworkCache


def make_cache(tmp_path, **kwargs):
    """构造隔离到临时目录的 NetworkCache 实例"""
    with patch("plookingII.core.network_cache.get_enhanced_logger", return_value=MagicMock()), patch(
        "plookingII.core.network_cache.get_remote_detector", return_value=MagicMock()
    ), patch(
        "plookingII.core.network_cache.get_config", side_effect=lambda key, default=None: default
    ), patch.object(
        NetworkCache, "_get_cache_directory", lambda self: str(tmp_path)
    ):
        cache = NetworkCache(**kwargs)
        cache.logger = MagicMock()
        return cache


class TestNetworkCache:
    def test_init_creates_cache_dir(self, tmp_path):
        """初始化创建缓存目录"""
        cache = make_cache(tmp_path / "nc")
        assert os.path.isdir(cache.cache_dir)

    def test_cache_remote_file_non_remote_returns_none(self, tmp_path):
        """非远程路径直接返回 None"""
        cache = make_cache(tmp_path / "nc")
        cache.remote_detector.is_remote_path.return_value = False

        assert cache.cache_remote_file("/local/file.jpg") is None

    def test_cache_remote_file_success_and_hit(self, tmp_path):
        """远程文件成功缓存，二次访问命中缓存"""
        cache = make_cache(tmp_path / "nc")
        src = tmp_path / "src.jpg"
        src.write_bytes(b"hello image")
        cache.remote_detector.is_remote_path.return_value = True

        local = cache.cache_remote_file(str(src))

        assert local is not None
        assert os.path.exists(local)
        with open(local, "rb") as f:
            assert f.read() == b"hello image"

        local2 = cache.cache_remote_file(str(src))
        assert local2 == local
        assert cache.stats["cache_hits"] == 1

    def test_get_cached_path_miss_increments_miss(self, tmp_path):
        """未缓存的远程路径产生一次 miss 统计"""
        cache = make_cache(tmp_path / "nc")

        assert cache.get_cached_path("/remote/not-cached.jpg") is None
        assert cache.stats["cache_misses"] == 1

    def test_remove_cached_file(self, tmp_path):
        """移除缓存：文件删除且索引清理"""
        cache = make_cache(tmp_path / "nc")
        src = tmp_path / "src.jpg"
        src.write_bytes(b"x")
        cache.remote_detector.is_remote_path.return_value = True
        local = cache.cache_remote_file(str(src))
        assert local is not None

        assert cache.remove_cached_file(str(src)) is True
        assert not os.path.exists(local)
        assert cache.is_cached(str(src)) is False

    def test_cleanup_expired_cache(self, tmp_path):
        """过期条目被清理，文件同步删除"""
        cache = make_cache(tmp_path / "nc")
        local = tmp_path / "expired.cache"
        local.write_bytes(b"x")
        entry = CacheEntry(
            remote_path="/remote/old.jpg",
            local_path=str(local),
            file_size=1,
            created_time=0.0,
            last_access_time=time.time() - 99999,
            access_count=1,
            checksum="",
        )
        key = cache._generate_cache_key("/remote/old.jpg")
        cache.cache_index[key] = entry
        cache.access_order[key] = 0.0
        cache.stats["total_cached_files"] = 1

        cache.cleanup_expired_cache()

        assert key not in cache.cache_index
        assert not os.path.exists(local)
        assert cache.stats["total_cached_files"] == 0

    def test_clear_all_cache(self, tmp_path):
        """清空缓存：文件、索引与统计全部重置"""
        cache = make_cache(tmp_path / "nc")
        src = tmp_path / "src.jpg"
        src.write_bytes(b"x")
        cache.remote_detector.is_remote_path.return_value = True
        cache.cache_remote_file(str(src))
        assert cache.cache_index

        cache.clear_all_cache()

        assert not cache.cache_index
        assert cache.stats["total_cached_files"] == 0
        assert not list((tmp_path / "nc").glob("*.cache"))

    def test_lru_eviction(self, tmp_path):
        """LRU 策略下按最久未访问顺序淘汰"""
        cache = make_cache(tmp_path / "nc")
        cache.cache_strategy = CacheStrategy.LRU
        files = {}
        for name in ("a", "b"):
            p = tmp_path / f"{name}.src"
            p.write_bytes(b"x")
            files[name] = p
        cache.remote_detector.is_remote_path.return_value = True
        path_a = cache.cache_remote_file(str(files["a"]))
        path_b = cache.cache_remote_file(str(files["b"]))
        assert path_a and path_b

        # 把容量压到刚好多出 1 字节，触发淘汰最旧的 a（LRU）
        cache.max_cache_size = 2
        cache._ensure_cache_space(1)

        assert not os.path.exists(path_a)
        assert os.path.exists(path_b)

    def test_metadata_roundtrip(self, tmp_path):
        """元数据落盘后新实例可恢复缓存索引"""
        cache_dir = tmp_path / "nc"
        cache1 = make_cache(cache_dir)
        src = tmp_path / "src.jpg"
        src.write_bytes(b"data")
        cache1.remote_detector.is_remote_path.return_value = True
        cache1.cache_remote_file(str(src))
        assert cache1.cache_index

        cache2 = make_cache(cache_dir)

        assert set(cache2.cache_index) == set(cache1.cache_index)
        entry = next(iter(cache2.cache_index.values()))
        assert entry.remote_path == str(src)

    def test_get_cache_stats(self, tmp_path):
        """统计信息包含命中率与使用量"""
        cache = make_cache(tmp_path / "nc")
        src = tmp_path / "src.jpg"
        src.write_bytes(b"data")
        cache.remote_detector.is_remote_path.return_value = True
        cache.cache_remote_file(str(src))

        stats = cache.get_cache_stats()

        assert stats["cache_hit_rate"] == 0.0
        assert stats["cache_usage_mb"] > 0
        assert 0 <= stats["cache_usage_percent"] <= 100
