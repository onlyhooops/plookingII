"""
测试 core/loading/strategies.py

覆盖：三种加载策略的格式判定、加载路径选择与统计更新。
"""

from unittest.mock import patch

from plookingII.core.loading.strategies import AutoStrategy, OptimizedStrategy, PreviewStrategy


class TestOptimizedStrategy:
    def test_can_handle_extensions(self):
        """仅支持 jpg/jpeg/png"""
        strategy = OptimizedStrategy()
        assert strategy.can_handle("/a/b.jpg", 1.0)
        assert strategy.can_handle("/a/b.jpeg", 1.0)
        assert strategy.can_handle("/a/b.png", 1.0)
        assert not strategy.can_handle("/a/b.gif", 1.0)

    def test_load_unsupported_format_returns_none(self):
        strategy = OptimizedStrategy()
        assert strategy.load("/a/b.gif") is None

    def test_load_small_uses_nsimage(self):
        strategy = OptimizedStrategy()
        with (
            patch("plookingII.core.loading.strategies.get_file_size_mb", return_value=1.0),
            patch("plookingII.core.loading.strategies.load_with_nsimage", return_value="img"),
        ):
            assert strategy.load("/a/b.jpg") == "img"
        assert strategy.stats.fast_loads == 1

    def test_load_small_prefers_cgimage_proxy(self):
        """小文件优先懒解码 CGImage 代理（缓冲可回收，画质不变）"""
        strategy = OptimizedStrategy()
        strategy.quartz_available = True
        with (
            patch("plookingII.core.loading.strategies.get_file_size_mb", return_value=1.0),
            patch("plookingII.core.loading.strategies.load_with_quartz", return_value="cg"),
            patch("plookingII.core.loading.strategies.load_with_nsimage", return_value="ns") as nsimage,
        ):
            assert strategy.load("/a/b.jpg") == "cg"
            nsimage.assert_not_called()

    def test_load_small_falls_back_to_nsimage_when_quartz_fails(self):
        """Quartz 懒代理失败时回退 NSImage"""
        strategy = OptimizedStrategy()
        strategy.quartz_available = True
        with (
            patch("plookingII.core.loading.strategies.get_file_size_mb", return_value=1.0),
            patch("plookingII.core.loading.strategies.load_with_quartz", return_value=None),
            patch("plookingII.core.loading.strategies.load_with_nsimage", return_value="ns"),
        ):
            assert strategy.load("/a/b.jpg") == "ns"

    def test_load_small_quartz_disabled_uses_nsimage(self):
        """Quartz 不可用时直接走 NSImage"""
        strategy = OptimizedStrategy()
        strategy.quartz_available = False
        with (
            patch("plookingII.core.loading.strategies.get_file_size_mb", return_value=1.0),
            patch("plookingII.core.loading.strategies.load_with_quartz", return_value="cg"),
            patch("plookingII.core.loading.strategies.load_with_nsimage", return_value="ns"),
        ):
            assert strategy.load("/a/b.jpg") == "ns"

    def test_load_medium_uses_quartz(self):
        strategy = OptimizedStrategy()
        strategy.quartz_available = True
        with (
            patch("plookingII.core.loading.strategies.get_file_size_mb", return_value=50.0),
            patch("plookingII.core.loading.strategies.load_with_quartz", return_value="cg"),
        ):
            assert strategy.load("/a/b.jpg") == "cg"
        assert strategy.stats.quartz_loads == 1

    def test_load_medium_fallback_when_quartz_unavailable(self):
        strategy = OptimizedStrategy()
        strategy.quartz_available = False
        with (
            patch("plookingII.core.loading.strategies.get_file_size_mb", return_value=50.0),
            patch("plookingII.core.loading.strategies.load_with_nsimage", return_value="img"),
        ):
            assert strategy.load("/a/b.jpg") == "img"

    def test_load_large_uses_memory_map(self):
        strategy = OptimizedStrategy()
        with (
            patch("plookingII.core.loading.strategies.get_file_size_mb", return_value=500.0),
            patch("plookingII.core.loading.strategies.load_with_memory_map", return_value="mmap"),
        ):
            assert strategy.load("/a/b.jpg") == "mmap"
        assert strategy.stats.memory_map_loads == 1

    def test_load_large_prefers_cgimage_proxy(self):
        """大文件优先懒解码 CGImage 代理（NSImage 内存映射为回退，避免泄漏）"""
        strategy = OptimizedStrategy()
        strategy.quartz_available = True
        with (
            patch("plookingII.core.loading.strategies.get_file_size_mb", return_value=500.0),
            patch("plookingII.core.loading.strategies.load_with_quartz", return_value="cg"),
            patch("plookingII.core.loading.strategies.load_with_memory_map", return_value="mmap") as mmap,
        ):
            assert strategy.load("/a/b.jpg") == "cg"
            mmap.assert_not_called()

    def test_load_large_falls_back_to_memory_map(self):
        """Quartz 懒代理失败时回退内存映射"""
        strategy = OptimizedStrategy()
        strategy.quartz_available = True
        with (
            patch("plookingII.core.loading.strategies.get_file_size_mb", return_value=500.0),
            patch("plookingII.core.loading.strategies.load_with_quartz", return_value=None),
            patch("plookingII.core.loading.strategies.load_with_memory_map", return_value="mmap"),
        ):
            assert strategy.load("/a/b.jpg") == "mmap"

    def test_load_failure_records_failure(self):
        strategy = OptimizedStrategy()
        with patch("plookingII.core.loading.strategies.get_file_size_mb", side_effect=OSError("boom")):
            assert strategy.load("/a/b.jpg") is None
        assert strategy.stats.failed_loads >= 1

    def test_get_stats_and_update_stats(self):
        strategy = OptimizedStrategy()
        stats = strategy.get_stats()
        assert "total_requests" in stats

        strategy.update_stats(True, 0.1)
        strategy.update_stats(False, 0.2)
        assert strategy.get_stats()["total_requests"] == 2


class TestPreviewStrategy:
    def test_can_handle_extensions(self):
        strategy = PreviewStrategy()
        assert strategy.can_handle("/a/b.jpg", 1.0)
        assert not strategy.can_handle("/a/b.gif", 1.0)

    def test_load_unsupported_returns_none(self):
        strategy = PreviewStrategy()
        assert strategy.load("/a/b.gif") is None

    def test_load_uses_quartz_thumbnail(self):
        strategy = PreviewStrategy()
        strategy.quartz_available = True
        with patch("plookingII.core.loading.strategies.load_with_quartz", return_value="cg"):
            assert strategy.load("/a/b.jpg") == "cg"

    def test_load_falls_back_to_nsimage(self):
        strategy = PreviewStrategy()
        strategy.quartz_available = False
        with (
            patch("plookingII.core.loading.strategies.load_with_nsimage", return_value="ns"),
            patch.object(strategy, "_resize_nsimage", return_value="resized"),
        ):
            assert strategy.load("/a/b.jpg") == "resized"

    def test_load_failure_records_failure(self):
        strategy = PreviewStrategy()
        strategy.quartz_available = False
        with patch("plookingII.core.loading.strategies.load_with_nsimage", return_value=None):
            assert strategy.load("/a/b.jpg") is None
        assert strategy.stats.failed_loads >= 1

    def test_get_stats(self):
        strategy = PreviewStrategy()
        assert "total_requests" in strategy.get_stats()


class TestAutoStrategy:
    def test_can_handle_delegates_to_optimized(self):
        strategy = AutoStrategy()
        assert strategy.can_handle("/a/b.jpg", 1.0)
        assert not strategy.can_handle("/a/b.gif", 1.0)

    def test_load_preview_mode(self):
        strategy = AutoStrategy()
        with patch.object(strategy.preview, "load", return_value="preview"):
            assert strategy.load("/a/b.jpg", preview=True) == "preview"

    def test_load_optimized_mode(self):
        strategy = AutoStrategy()
        with patch.object(strategy.optimized, "load", return_value="full"):
            assert strategy.load("/a/b.jpg", preview=False) == "full"

    def test_get_stats_merges(self):
        strategy = AutoStrategy()
        strategy.optimized.stats.record_success("fast", 0.01)
        strategy.preview.stats.record_success("quartz", 0.02)
        stats = strategy.get_stats()
        assert stats["total_requests"] == 2
        assert "optimized" in stats and "preview" in stats
