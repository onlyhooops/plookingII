"""
测试 services/image_loader_service.py

覆盖：文件夹图片加载、渐进式加载开关、策略委托与后台任务调度。
"""

from unittest.mock import MagicMock, patch

import pytest

from plookingII.services.image_loader_service import ImageLoaderService


@pytest.fixture
def service():
    win = MagicMock()
    win.images = []
    win.current_index = 0
    return ImageLoaderService(win)


class TestImageLoaderService:
    def test_load_folder_images_sorts(self, service, tmp_path):
        """加载文件夹图片列表"""
        photos = tmp_path / "photos"
        photos.mkdir()
        (photos / "b.jpg").touch()
        (photos / "a.png").touch()
        (photos / "note.txt").touch()

        images = service.load_folder_images(str(photos))

        assert images == [str(photos / "a.png"), str(photos / "b.jpg")]

    def test_load_folder_images_missing_dir_returns_empty(self, service, tmp_path):
        """目录不存在时返回空列表"""
        assert service.load_folder_images(str(tmp_path / "nope")) == []

    def test_load_and_display_progressive_disabled(self, service):
        """渐进式加载被禁用时直接返回"""
        with patch("plookingII.services.image_loader_service.get_config", return_value=True):
            service.load_and_display_progressive("/a.jpg")
        service.image_manager._load_and_display_progressive.assert_not_called()

    def test_load_and_display_progressive_delegates(self, service):
        """渐进式加载委托给图像管理器"""
        with patch("plookingII.services.image_loader_service.get_config", return_value=False):
            service.load_and_display_progressive("/a.jpg", (100, 100))
        service.image_manager._load_and_display_progressive.assert_called_once_with("/a.jpg", (100, 100))

    def test_display_image_immediate(self, service):
        """立即显示图片到视图"""
        service.display_image_immediate("image")
        service.main_window.image_view.setImage_.assert_called_once_with("image")

    def test_load_image_optimized_with_manager(self, service):
        """优先走图像管理器的 load_image_optimized 接口"""
        service.image_manager.load_image_optimized.return_value = "optimized"
        assert service.load_image_optimized("/a.jpg") == "optimized"
        service.image_manager.load_image_optimized.assert_called_once_with(
            "/a.jpg", target_size=None, strategy="auto"
        )

    def test_load_image_optimized_uses_private_fallback(self, service):
        """图像管理器只有私有接口时走 _load_image_optimized"""
        image_manager = MagicMock()
        del image_manager.load_image_optimized  # 移除公开接口
        image_manager._load_image_optimized.return_value = "via-private"
        service._image_manager = image_manager

        assert service.load_image_optimized("/a.jpg", prefer_preview=True) == "via-private"

    def test_load_image_optimized_uses_cache_without_manager(self, service):
        """无图像管理器时回退到缓存加载"""
        service.main_window.image_manager = None
        service._image_manager = None
        service.image_cache.load_image_with_strategy.return_value = "cached"

        assert service.load_image_optimized("/a.jpg") == "cached"

    def test_load_standard_and_preview(self, service):
        """标准/预览加载委托正确"""
        service.image_manager.load_image_optimized.return_value = "img"
        assert service.load_standard_image("/a.jpg") == "img"
        service.image_manager.load_image_optimized.assert_called_with("/a.jpg", target_size=None, strategy="auto")
        assert service.load_preview_image("/a.jpg") == "img"
        service.image_manager.load_image_optimized.assert_called_with("/a.jpg", target_size=None, strategy="preview")

    def test_load_large_image_progressive_disabled(self, service):
        """超大图渐进式加载被禁用时返回 None"""
        with patch("plookingII.services.image_loader_service.get_config", return_value=True):
            assert service.load_large_image_progressive("/a.jpg") is None

    def test_load_scaled_image_with_pil(self, service):
        """PIL 缩放路径委托预览策略"""
        service.image_manager.load_image_optimized.return_value = "scaled"
        assert service.load_scaled_image_with_pil("/a.jpg", max_dimension=2000) == "scaled"
        service.image_manager.load_image_optimized.assert_called_once_with(
            "/a.jpg", target_size=(2000, 2000), strategy="preview"
        )

    def test_schedule_background_tasks_once(self, service):
        """后台任务只调度一次且执行预加载/内存检查/进度保存"""
        class FakeThread:
            def __init__(self, target=None, daemon=None):
                self._target = target

            def start(self):
                self._target()

        with patch("plookingII.services.image_loader_service.threading.Thread", FakeThread), patch(
            "plookingII.services.image_loader_service.time.sleep"
        ):
            service.schedule_background_tasks()

        service.image_manager.start_preload.assert_called_once()
        service.main_window.memory_monitor.check_memory_usage.assert_called_once()
        service.main_window.session_manager.save_progress.assert_called_once()
        assert service._background_tasks_running is False

        # 正在运行时再次调度应直接返回，不重复启动后台任务
        service._background_tasks_running = True
        service.schedule_background_tasks()
        service.image_manager.start_preload.assert_called_once()

    def test_shutdown_background_tasks(self, service):
        """关闭后台任务时停止预加载并清理缓存"""
        service.shutdown_background_tasks()
        service.image_manager.stop_preload.assert_called_once()
        service.image_cache.cleanup.assert_called_once()
