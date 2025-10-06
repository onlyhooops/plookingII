"""
图片加载服务

统一管理所有图片加载策略和优化逻辑，从MainWindow中提取出来的核心图片加载功能。
这个服务作为高级抽象层，协调ImageManager、缓存系统和各种加载策略。
"""

import logging
import os
import threading
import time
from typing import Any

from ..config.constants import APP_NAME, SUPPORTED_IMAGE_EXTS
from ..config.manager import get_config

logger = logging.getLogger(APP_NAME)

class ImageLoaderService:
    """
    图片加载服务

    负责所有图片加载策略和优化逻辑，提供统一的图片加载接口。
    从MainWindow中提取的核心功能，实现关注点分离。

    主要职责：
    1. 统一图片加载策略管理
    2. 协调ImageManager和缓存系统
    3. 提供高质量图片加载
    4. 管理渐进式加载
    5. 处理文件夹图片扫描
    6. 后台任务调度
    """

    def __init__(self, main_window):
        """
        初始化图片加载服务

        Args:
            main_window: MainWindow实例，用于访问相关组件
        """
        self.main_window = main_window
        self._background_tasks_running = False

        # 缓存组件引用
        self._image_manager = None
        self._image_cache = None

    @property
    def image_manager(self):
        """获取图像管理器实例"""
        if self._image_manager is None and hasattr(self.main_window, "image_manager"):
            self._image_manager = self.main_window.image_manager
        return self._image_manager

    @property
    def image_cache(self):
        """获取图像缓存实例"""
        if self._image_cache is None and hasattr(self.main_window, "image_cache"):
            self._image_cache = self.main_window.image_cache
        return self._image_cache

    def load_folder_images(self, folder_path: str) -> list[str]:
        """
        加载指定文件夹的图片列表

        Args:
            folder_path: 文件夹路径

        Returns:
            图片文件路径列表，按文件名排序
        """
        try:
            images = []

            for filename in os.listdir(folder_path):
                if filename.lower().endswith(SUPPORTED_IMAGE_EXTS):
                    image_path = os.path.join(folder_path, filename)
                    images.append(image_path)

            # 图片始终按正常顺序排序，不受reverse_folder_order影响
            images.sort()
            return images

        except Exception as e:
            logger.warning(f"加载文件夹图片失败: {e}")
            return []

    def load_and_display_progressive(self, image_path: str, target_size: tuple[int, int] | None = None):
        """
        渐进式加载并显示图片

        Args:
            image_path: 图片路径
            target_size: 目标尺寸
        """
        try:
            # 检查是否禁用渐进式加载
            if get_config("feature.disable_progressive_layer", True):
                if hasattr(self.main_window, "status_bar_controller") and self.main_window.status_bar_controller:
                    try:
                        self.main_window.status_bar_controller.set_status_message("渐进式已禁用")
                    except Exception:
                        pass
                return

            # 委托给ImageManager处理
            if self.image_manager and hasattr(self.image_manager, "_load_and_display_progressive"):
                self.image_manager._load_and_display_progressive(image_path, target_size)

        except Exception as e:
            logger.warning(f"渐进式加载失败: {e}")

    def display_image_immediate(self, image: Any):
        """
        立即显示图片

        Args:
            image: 图片对象
        """
        try:
            if hasattr(self.main_window, "image_view") and self.main_window.image_view:
                self.main_window.image_view.setImage_(image)
                self.main_window.image_view.setNeedsDisplay_(True)
        except Exception as e:
            logger.warning(f"立即显示图片失败: {e}")

    def request_high_quality_image(self):
        """
        请求加载当前图像的高质量版本

        用于缩放时提升显示质量，在后台线程异步加载。
        """
        if not (hasattr(self.main_window, "images") and self.main_window.images and
                hasattr(self.main_window, "current_index") and
                self.main_window.current_index < len(self.main_window.images)):
            return

        image_path = self.main_window.images[self.main_window.current_index]

        def load_high_quality():
            try:
                # 获取视图尺寸，使用更大的目标尺寸以获得更好的质量
                if hasattr(self.main_window, "image_view") and self.main_window.image_view:
                    view_frame = self.main_window.image_view.frame()
                    # 使用4倍分辨率以支持高倍缩放
                    target_size = (int(view_frame.size.width * 4), int(view_frame.size.height * 4))
                else:
                    target_size = (3840, 2160)  # 默认4K分辨率

                # 使用图像管理器加载高质量图像
                high_quality_image = None
                if self.image_manager:
                    high_quality_image = self.image_manager.load_image_optimized(
                        image_path, target_size=target_size, strategy="auto"
                    )

                if high_quality_image:
                    # 在主线程更新图像
                    def update_image():
                        if hasattr(self.main_window, "image_view") and self.main_window.image_view:
                            self.main_window.image_view.setImage_(high_quality_image)
                            self.main_window.image_view.setNeedsDisplay_(True)

                    try:
                        from Foundation import NSOperationQueue
                        NSOperationQueue.mainQueue().addOperationWithBlock_(update_image)
                    except Exception:
                        update_image()

            except Exception as e:
                logger.warning(f"加载高质量图像失败: {e}")

        # 在后台线程加载高质量图像
        threading.Thread(target=load_high_quality, daemon=True).start()

    def load_image_optimized(self, img_path: str, prefer_preview: bool = False,
                           target_size: tuple[int, int] | None = None) -> Any | None:
        """
        智能图片加载方法

        Args:
            img_path: 图片路径
            prefer_preview: 是否偏好预览模式
            target_size: 目标尺寸

        Returns:
            加载的图片对象，失败时返回None
        """
        try:
            # 优先使用图像管理器
            if self.image_manager:
                # 根据参数选择策略
                strategy = "preview" if prefer_preview else "auto"

                if hasattr(self.image_manager, "load_image_optimized"):
                    return self.image_manager.load_image_optimized(
                        img_path, target_size=target_size, strategy=strategy
                    )
                if hasattr(self.image_manager, "_load_image_optimized"):
                    return self.image_manager._load_image_optimized(
                        img_path, prefer_preview=prefer_preview, target_size=target_size
                    )

            # 如果没有图像管理器，使用缓存加载
            if self.image_cache and hasattr(self.image_cache, "load_image_with_strategy"):
                strategy = "preview" if prefer_preview else "auto"
                return self.image_cache.load_image_with_strategy(img_path, strategy, target_size)

            return None

        except Exception as e:
            logger.warning(f"优化图像加载失败: {e}")
            return None

    def load_standard_image(self, img_path: str) -> Any | None:
        """
        标准图片加载，修复EXIF方向处理

        Args:
            img_path: 图片路径

        Returns:
            加载的图片对象，失败时返回None
        """
        try:
            # 使用优化加载方法，策略为auto
            return self.load_image_optimized(img_path, prefer_preview=False, target_size=None)

        except Exception as e:
            logger.warning(f"标准图像加载失败: {e}")
            return None

    def load_with_pil_fallback(self, img_path: str) -> Any | None:
        """
        PIL备用加载路径

        Args:
            img_path: 图片路径

        Returns:
            加载的图片对象，失败时返回None
        """
        try:
            return self.load_standard_image(img_path)
        except Exception as e:
            logger.warning(f"PIL备用加载失败: {e}")
            return None

    def load_preview_image(self, img_path: str, file_size_mb: float | None = None) -> Any | None:
        """
        加载预览质量图片

        Args:
            img_path: 图片路径
            file_size_mb: 文件大小（MB），用于优化策略选择

        Returns:
            加载的图片对象，失败时返回None
        """
        try:
            # 使用预览策略加载
            return self.load_image_optimized(img_path, prefer_preview=True, target_size=None)

        except Exception as e:
            logger.warning(f"预览图像加载失败: {e}")
            return None

    def load_large_image_progressive(self, img_path: str) -> Any | None:
        """
        渐进式加载超大图片

        Args:
            img_path: 图片路径

        Returns:
            加载的图片对象，失败时返回None
        """
        try:
            # 检查是否禁用渐进式加载
            if get_config("feature.disable_progressive_layer", True):
                return None

            # 使用渐进式策略加载
            if self.image_manager:
                if hasattr(self.image_manager, "load_image_optimized"):
                    return self.image_manager.load_image_optimized(img_path, strategy="progressive")
                if hasattr(self.image_manager, "_load_image_optimized"):
                    return self.image_manager._load_image_optimized(img_path, prefer_preview=False)

            # 使用缓存加载
            if self.image_cache and hasattr(self.image_cache, "load_image_with_strategy"):
                return self.image_cache.load_image_with_strategy(img_path, "progressive")

            return None

        except Exception as e:
            logger.warning(f"渐进式图像加载失败: {e}")
            return None

    def load_scaled_image_with_pil(self, img_path: str, max_dimension: int = 3000) -> Any | None:
        """
        使用PIL加载缩放图片

        Args:
            img_path: 图片路径
            max_dimension: 最大尺寸

        Returns:
            加载的图片对象，失败时返回None
        """
        try:
            # 计算目标尺寸
            target_size = (max_dimension, max_dimension)

            # 使用预览策略加载缩放图像
            return self.load_image_optimized(img_path, prefer_preview=True, target_size=target_size)

        except Exception as e:
            logger.warning(f"缩放图像加载失败: {e}")
            return None

    def load_large_image_with_pil(self, img_path: str) -> Any | None:
        """
        使用PIL处理超大图片

        Args:
            img_path: 图片路径

        Returns:
            加载的图片对象，失败时返回None
        """
        try:
            # 使用自动策略处理大图像
            return self.load_image_optimized(img_path, prefer_preview=False, target_size=None)

        except Exception as e:
            logger.warning(f"大图像加载失败: {e}")
            return None

    def schedule_background_tasks(self):
        """
        调度后台任务

        启动后台线程处理预加载、内存检查、进度保存等任务。
        """
        if self._background_tasks_running:
            return

        self._background_tasks_running = True

        def background_worker():
            try:
                # 启动预加载（延迟执行，避免与当前加载冲突）
                time.sleep(0.1)
                if self.image_manager and hasattr(self.image_manager, "start_preload"):
                    self.image_manager.start_preload()

                # 检查内存使用
                time.sleep(0.2)
                if hasattr(self.main_window, "memory_monitor") and self.main_window.memory_monitor:
                    self.main_window.memory_monitor.check_memory_usage()

                # 保存任务进度
                time.sleep(0.3)
                if hasattr(self.main_window, "session_manager") and self.main_window.session_manager:
                    self.main_window.session_manager.save_progress()

            except Exception as e:
                logger.warning(f"后台任务执行失败: {e}")
            finally:
                self._background_tasks_running = False

        # 启动后台任务线程
        bg_thread = threading.Thread(target=background_worker, daemon=True)
        bg_thread.start()

    def shutdown_background_tasks(self):
        """
        关闭后台任务

        清理资源，停止所有后台任务。
        """
        try:
            self._background_tasks_running = False

            # 停止预加载
            if self.image_manager and hasattr(self.image_manager, "stop_preload"):
                self.image_manager.stop_preload()

            # 清理缓存
            if self.image_cache and hasattr(self.image_cache, "cleanup"):
                self.image_cache.cleanup()

            logger.debug("后台任务已关闭")

        except Exception as e:
            logger.warning(f"关闭后台任务失败: {e}")

    def get_loading_strategy_info(self, img_path: str) -> dict:
        """
        获取图片加载策略信息

        Args:
            img_path: 图片路径

        Returns:
            包含策略信息的字典
        """
        try:
            info = {
                "path": img_path,
                "exists": os.path.exists(img_path),
                "size_mb": 0,
                "recommended_strategy": "auto",
                "has_image_manager": self.image_manager is not None,
                "has_image_cache": self.image_cache is not None
            }

            if info["exists"]:
                try:
                    file_size = os.path.getsize(img_path)
                    info["size_mb"] = file_size / (1024 * 1024)

                    # 根据文件大小推荐策略
                    if info["size_mb"] > 50:
                        info["recommended_strategy"] = "progressive"
                    elif info["size_mb"] > 10:
                        info["recommended_strategy"] = "preview"
                    else:
                        info["recommended_strategy"] = "auto"

                except Exception:
                    pass

            return info

        except Exception as e:
            logger.warning(f"获取加载策略信息失败: {e}")
            return {"error": str(e)}

    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            self.shutdown_background_tasks()
        except Exception:
            pass
