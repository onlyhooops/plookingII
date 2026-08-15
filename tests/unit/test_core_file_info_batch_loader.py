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

    def test_get_directory_images_excludes_nested_subdirectories(self, tmp_path):
        """回归：父目录图片列表不得混入子目录（如“精选”目录）中的图片"""
        loader = FileInfoBatchLoader()
        photos = tmp_path / "photos"
        photos.mkdir()
        (photos / "a.jpg").touch()
        (photos / "b.png").touch()

        # 模拟“精选”子目录（父目录名 + “ 精选”），内含图片
        featured = photos / "photos 精选"
        featured.mkdir()
        kept = featured / "kept.jpg"
        kept.touch()

        images = loader.get_directory_images(str(photos), filter_exts=(".jpg", ".png"))

        assert str(kept) not in images
        assert images == [str(photos / "a.jpg"), str(photos / "b.png")]

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

    def test_directory_contains_images_hits_bool_cache(self, tmp_path):
        """含图布尔缓存：重复判断命中缓存，只枚举一次磁盘"""
        loader = FileInfoBatchLoader()
        photos = tmp_path / "photos"
        photos.mkdir()
        (photos / "a.jpg").touch()

        with patch.object(loader, "scan_directory", wraps=loader.scan_directory) as scan:
            first = loader.directory_contains_images(str(photos), filter_exts=(".jpg",))
            second = loader.directory_contains_images(str(photos), filter_exts=(".jpg",))

        assert first is True
        assert second is True
        assert scan.call_count == 1

    def test_directory_contains_images_no_images_cached(self, tmp_path):
        """空目录含图判断返回 False 并缓存"""
        loader = FileInfoBatchLoader()
        empty = tmp_path / "empty"
        empty.mkdir()

        assert loader.directory_contains_images(str(empty), filter_exts=(".jpg",)) is False
        # 命中缓存，不重新枚举
        with patch.object(loader, "scan_directory", wraps=loader.scan_directory) as scan:
            assert loader.directory_contains_images(str(empty), filter_exts=(".jpg",)) is False
            assert scan.call_count == 0

    def test_directory_contains_images_fills_list_cache(self, tmp_path):
        """含图判断顺带填充列表缓存：后续 get_directory_images 直接命中"""
        loader = FileInfoBatchLoader()
        photos = tmp_path / "photos"
        photos.mkdir()
        (photos / "b.jpg").touch()
        (photos / "a.jpg").touch()

        # 先做含图判断（深扫阶段），应顺带写入列表缓存
        assert loader.directory_contains_images(str(photos), filter_exts=(".jpg",)) is True

        # 随后获取列表直接命中缓存，不再扫描
        with patch.object(loader, "scan_directory", wraps=loader.scan_directory) as scan:
            images = loader.get_directory_images(str(photos), filter_exts=(".jpg",))
            assert scan.call_count == 0

        assert images == [str(photos / "a.jpg"), str(photos / "b.jpg")]

    def test_contains_bool_cache_mtime_invalidates(self, tmp_path):
        """含图布尔缓存：目录 mtime 变化后自动失效并重新判断"""
        loader = FileInfoBatchLoader()
        photos = tmp_path / "photos"
        photos.mkdir()

        assert loader.directory_contains_images(str(photos), filter_exts=(".jpg",)) is False

        # 新增图片改变目录 mtime（mtime 粒度不足时强制修改）
        (photos / "a.jpg").touch()
        future = os.stat(str(photos)).st_mtime + 100
        os.utime(str(photos), (future, future))

        assert loader.directory_contains_images(str(photos), filter_exts=(".jpg",)) is True
