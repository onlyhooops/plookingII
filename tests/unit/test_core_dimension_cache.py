"""
测试 core/dimension_cache.py

覆盖 P3-4 目录级图片尺寸持久化缓存：
- 保存/加载往返一致
- 目录 mtime 变化触发失效
- 缓存损坏/格式非法时安全忽略（返回 None）
- 清除与统计
"""

import json
import os

from plookingII.core.dimension_cache import DirectoryDimensionCache, get_dimension_cache, reset_dimension_cache


class TestDirectoryDimensionCache:
    def test_save_and_load_roundtrip(self, tmp_path):
        """保存后加载应返回相同映射"""
        cache = DirectoryDimensionCache(cache_dir=str(tmp_path / "cache"))
        photos = tmp_path / "photos"
        photos.mkdir()
        mtime = os.stat(str(photos)).st_mtime
        dims = {"a.jpg": (1920, 1080), "b.png": (800, 600)}

        assert cache.save(str(photos), mtime, dims) is True
        loaded = cache.load(str(photos), mtime)

        assert loaded == dims

    def test_mtime_mismatch_invalidates(self, tmp_path):
        """目录 mtime 变化后缓存失效"""
        cache = DirectoryDimensionCache(cache_dir=str(tmp_path / "cache"))
        photos = tmp_path / "photos"
        photos.mkdir()
        old_mtime = os.stat(str(photos)).st_mtime
        cache.save(str(photos), old_mtime, {"a.jpg": (1920, 1080)})

        # mtime 变化（模拟目录内文件增删）
        future = old_mtime + 100
        assert cache.load(str(photos), future) is None

    def test_corrupted_cache_ignored(self, tmp_path):
        """缓存文件损坏时安全忽略（返回 None），不影响主流程"""
        cache = DirectoryDimensionCache(cache_dir=str(tmp_path / "cache"))
        photos = tmp_path / "photos"
        photos.mkdir()
        mtime = os.stat(str(photos)).st_mtime

        # 写入损坏内容
        cache_file = cache._cache_file(str(photos))
        os.makedirs(cache_file.parent, exist_ok=True)
        cache_file.write_text("not valid json {{{", encoding="utf-8")

        assert cache.load(str(photos), mtime) is None

    def test_invalid_dims_shape_ignored(self, tmp_path):
        """格式非法的尺寸条目被过滤，合法条目保留"""
        cache = DirectoryDimensionCache(cache_dir=str(tmp_path / "cache"))
        photos = tmp_path / "photos"
        photos.mkdir()
        mtime = os.stat(str(photos)).st_mtime

        cache_file = cache._cache_file(str(photos))
        os.makedirs(cache_file.parent, exist_ok=True)
        payload = {
            "mtime": mtime,
            "dims": {
                "good.jpg": [1920, 1080],
                "bad_shape.jpg": [1920],  # 长度不足
                "bad_type.jpg": ["x", 1080],  # 类型错误
                "zero.jpg": [0, 1080],  # 非正尺寸
            },
        }
        cache_file.write_text(json.dumps(payload), encoding="utf-8")

        loaded = cache.load(str(photos), mtime)
        assert loaded == {"good.jpg": (1920, 1080)}

    def test_save_no_dims_returns_false(self, tmp_path):
        """空映射不写盘"""
        cache = DirectoryDimensionCache(cache_dir=str(tmp_path / "cache"))
        photos = tmp_path / "photos"
        photos.mkdir()
        assert cache.save(str(photos), 0.0, {}) is False

    def test_clear_removes_files(self, tmp_path):
        """清空删除全部缓存文件"""
        cache = DirectoryDimensionCache(cache_dir=str(tmp_path / "cache"))
        photos = tmp_path / "photos"
        photos.mkdir()
        mtime = os.stat(str(photos)).st_mtime
        cache.save(str(photos), mtime, {"a.jpg": (10, 10)})
        assert cache.get_stats()["dir_count"] >= 1

        cache.clear()
        assert cache.get_stats()["dir_count"] == 0

    def test_singleton_and_reset(self, tmp_path, monkeypatch):
        """全局单例可复用，reset 后重建"""
        monkeypatch.setenv("HOME", str(tmp_path))
        reset_dimension_cache()
        try:
            c1 = get_dimension_cache()
            c2 = get_dimension_cache()
            assert c1 is c2
        finally:
            reset_dimension_cache()
