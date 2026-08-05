"""
测试 core/file_info_batch_loader.py

重点覆盖目录级图片列表缓存的正确性：
- 对外返回副本，调用方原地修改不得污染共享缓存（H1 回归）
- 目录 mtime 变化触发失效
- LRU 淘汰与缓存命中
"""

import os
from unittest.mock import patch

from plookingII.core.file_info_batch_loader import DirectoryImageListCache, FileInfoBatchLoader


class TestDirectoryImageListCache:
    """目录列表缓存单元测试"""

    def test_get_returns_copy_isolated_from_mutation(self, tmp_path):
        """调用方修改返回列表不得污染缓存（H1 回归）"""
        cache = DirectoryImageListCache()
        photos = tmp_path / "photos"
        photos.mkdir()
        cache.put(str(photos), os.stat(str(photos)).st_mtime, ["a.jpg", "b.jpg"])

        first = cache.get(str(photos))
        assert first == ["a.jpg", "b.jpg"]

        # 模拟 main_window.images.pop() 之类的原地修改
        first.pop(0)

        assert cache.get(str(photos)) == ["a.jpg", "b.jpg"]

    def test_put_stores_tuple_and_get_returns_fresh_list(self, tmp_path):
        """内部存储不可变元组，每次 get 返回新列表对象"""
        cache = DirectoryImageListCache()
        photos = tmp_path / "photos"
        photos.mkdir()
        source = ["a.jpg"]
        cache.put(str(photos), os.stat(str(photos)).st_mtime, source)

        result1 = cache.get(str(photos))
        result2 = cache.get(str(photos))

        assert result1 == result2 == ["a.jpg"]
        assert result1 is not result2

    def test_mtime_change_invalidates(self, tmp_path):
        """目录 mtime 变化后缓存自动失效"""
        cache = DirectoryImageListCache()
        photos = tmp_path / "photos"
        photos.mkdir()

        cache.put(str(photos), os.stat(str(photos)).st_mtime, ["a.jpg"])
        assert cache.get(str(photos)) == ["a.jpg"]

        # 修改目录 mtime，触发失效
        future = os.stat(str(photos)).st_mtime + 100
        os.utime(str(photos), (future, future))

        assert cache.get(str(photos)) is None

    def test_lru_eviction(self, tmp_path):
        """超出上限时淘汰最久未访问的目录"""
        cache = DirectoryImageListCache(max_size=2)
        dirs = {}
        for name in ("a", "b", "c"):
            d = tmp_path / name
            d.mkdir()
            dirs[name] = d
        cache.put(str(dirs["a"]), os.stat(str(dirs["a"])).st_mtime, ["a.jpg"])
        cache.put(str(dirs["b"]), os.stat(str(dirs["b"])).st_mtime, ["b.jpg"])
        cache.put(str(dirs["c"]), os.stat(str(dirs["c"])).st_mtime, ["c.jpg"])

        assert cache.get(str(dirs["a"])) is None
        assert cache.get(str(dirs["b"])) == ["b.jpg"]
        assert cache.get(str(dirs["c"])) == ["c.jpg"]


class TestFileInfoBatchLoader:
    """批量加载器集成测试"""

    def test_get_directory_images_sorts_and_filters(self, tmp_path):
        """返回按文件名排序、过滤扩展名的图片列表"""
        loader = FileInfoBatchLoader()
        photos = tmp_path / "photos"
        photos.mkdir()
        (photos / "b.jpg").touch()
        (photos / "a.png").touch()
        (photos / "note.txt").touch()

        images = loader.get_directory_images(str(photos), filter_exts=(".jpg", ".png"))

        assert images == [str(photos / "a.png"), str(photos / "b.jpg")]

    def test_get_directory_images_hits_cache(self, tmp_path):
        """第二次获取同一目录命中缓存，不再扫描磁盘"""
        loader = FileInfoBatchLoader()
        photos = tmp_path / "photos"
        photos.mkdir()
        (photos / "a.jpg").touch()

        with patch.object(loader, "scan_directory", wraps=loader.scan_directory) as scan:
            first = loader.get_directory_images(str(photos), filter_exts=(".jpg",))
            second = loader.get_directory_images(str(photos), filter_exts=(".jpg",))

        assert first == second == [str(photos / "a.jpg")]
        assert scan.call_count == 1

    def test_mutating_result_does_not_pollute_cache(self, tmp_path):
        """H1 回归：精选（原地 pop）后重新获取目录，图片列表不应缺项"""
        loader = FileInfoBatchLoader()
        photos = tmp_path / "photos"
        photos.mkdir()
        for name in ("a.jpg", "b.jpg", "c.jpg"):
            (photos / name).touch()

        first = loader.get_directory_images(str(photos), filter_exts=(".jpg",))
        first.pop(0)  # 模拟 _remove_current_image_from_sequences 的原地修改

        second = loader.get_directory_images(str(photos), filter_exts=(".jpg",))

        assert len(second) == 3
        assert second == [str(photos / "a.jpg"), str(photos / "b.jpg"), str(photos / "c.jpg")]
