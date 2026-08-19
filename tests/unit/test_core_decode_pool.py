"""
测试 core/decode_pool.py

覆盖：
- DecodePool 初始化与子进程启动
- decode 端到端（真实子进程解码，临时文件生成与清理）
- 子进程周期重启（任务计数归零）
- shutdown 清理
"""

import os
from pathlib import Path

from plookingII.core.decode_pool import DecodePool, get_decode_pool, reset_decode_pool

# 测试图片（6000x4000 JPEG，由脚本生成，不存在则跳过）
TEST_IMAGES = Path("/tmp/plk_mem_analysis/images")


def _make_test_image(tmp_path: Path) -> Path:
    """生成一张小测试 JPEG（1600x1200，够解码用）"""
    from PIL import Image

    img = Image.new("RGB", (1600, 1200), color=(120, 130, 140))
    p = tmp_path / "test_img.jpg"
    img.save(p, "JPEG", quality=85)
    return p


class TestDecodePool:
    def test_init_starts_workers(self):
        """初始化后子进程池就绪"""
        pool = DecodePool(max_workers=2, max_tasks_per_worker=5)
        try:
            stats = pool.get_stats()
            assert stats["workers"] == 2
            assert len(stats["tasks_per_worker"]) == 2
        finally:
            pool.shutdown()

    def test_decode_returns_file(self, tmp_path):
        """子进程解码返回临时文件路径"""
        img = _make_test_image(tmp_path)
        pool = DecodePool(max_workers=1, max_tasks_per_worker=5)
        try:
            result = pool.decode(str(img), target_size=(800, 600))
            assert result is not None
            assert os.path.exists(result)
            # 文件可被加载
            from AppKit import NSImage

            ns = NSImage.alloc().initWithContentsOfFile_(result)
            assert ns is not None
        finally:
            pool.shutdown()

    def test_cleanup_file(self, tmp_path):
        """cleanup_file 删除临时文件"""
        img = _make_test_image(tmp_path)
        pool = DecodePool(max_workers=1, max_tasks_per_worker=5)
        try:
            result = pool.decode(str(img), target_size=(800, 600))
            assert result is not None
            assert os.path.exists(result)
            pool.cleanup_file(result)
            assert not os.path.exists(result)
        finally:
            pool.shutdown()

    def test_worker_restart_after_max_tasks(self, tmp_path):
        """达到任务上限后子进程重启（任务计数归零）"""
        img = _make_test_image(tmp_path)
        pool = DecodePool(max_workers=1, max_tasks_per_worker=2)
        try:
            # 3 次解码：第 3 次应触发重启
            for _ in range(3):
                result = pool.decode(str(img), target_size=(800, 600))
                assert result is not None
            stats = pool.get_stats()
            # 重启后任务计数应重新累积（<= max_tasks）
            assert all(t <= 2 for t in stats["tasks_per_worker"])
        finally:
            pool.shutdown()

    def test_decode_failure_returns_none(self, tmp_path):
        """解码不存在的文件返回 None"""
        pool = DecodePool(max_workers=1, max_tasks_per_worker=5)
        try:
            result = pool.decode(str(tmp_path / "nonexistent.jpg"), target_size=(800, 600))
            assert result is None
        finally:
            pool.shutdown()

    def test_shutdown_closes_workers(self, tmp_path):
        """shutdown 后无残留子进程"""
        pool = DecodePool(max_workers=2, max_tasks_per_worker=5)
        assert pool.get_stats()["workers"] == 2
        pool.shutdown()
        assert pool.get_stats()["workers"] == 0

    def test_singleton_and_reset(self):
        """全局单例可复用，reset 后重建"""
        reset_decode_pool()
        try:
            p1 = get_decode_pool()
            p2 = get_decode_pool()
            assert p1 is p2
        finally:
            reset_decode_pool()
