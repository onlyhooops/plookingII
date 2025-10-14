"""
核心加载策略实现

简化的策略类，提供清晰的职责分离和简洁的API。

Author: PlookingII Team
Date: 2025-10-06
"""

import logging
import os
import time
from typing import Any

from .config import LoadingConfig, get_default_config
from .helpers import (
    cgimage_to_nsimage,
    check_quartz_availability,
    get_file_size_mb,
    load_with_memory_map,
    load_with_nsimage,
    load_with_quartz,
)
from .stats import LoadingStats

logger = logging.getLogger(__name__)

_optimized_init_logged = False


class OptimizedStrategy:
    """智能优化加载策略

    根据文件大小自动选择最优加载方法：
    - 小文件(<10MB): NSImage直接加载
    - 中等文件(10-100MB): Quartz优化加载
    - 大文件(>100MB): 内存映射加载

    特性：
    - 自动策略选择
    - 完整的统计功能
    - 灵活的配置
    - 向后兼容
    """

    def __init__(self, config: LoadingConfig | None = None):
        """初始化优化加载策略

        Args:
            config: 加载配置，None则使用默认配置
        """
        self.config = config or get_default_config()
        self.stats = LoadingStats()
        self.name = "optimized"

        # 检查系统能力
        self.quartz_available = check_quartz_availability()
        self.memory_mapping_available = True  # 内存映射总是可用

        global _optimized_init_logged
        if not _optimized_init_logged:
            logger.info("OptimizedStrategy initialized - Quartz: %s, Config: {self.config}", self.quartz_available)
            _optimized_init_logged = True

    def can_handle(self, file_path: str, file_size_mb: float, target_size: tuple[int, int] | None = None) -> bool:
        """检查是否可以处理文件

        Args:
            file_path: 文件路径
            file_size_mb: 文件大小（MB）
            target_size: 目标尺寸

        Returns:
            True（总是可以处理）
        """
        # 检查文件格式
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png"):
            return False
        return True

    def load(self, file_path: str, target_size: tuple[int, int] | None = None) -> Any | None:
        """加载图片（智能选择方法）

        Args:
            file_path: 文件路径
            target_size: 目标尺寸 (width, height)

        Returns:
            图片对象（NSImage或CGImage），失败返回None
        """
        start_time = time.time()

        try:
            # 检查文件格式
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in (".jpg", ".jpeg", ".png"):
                logger.debug("不支持的文件格式: %s", ext)
                return None

            # 获取文件大小
            size_mb = get_file_size_mb(file_path)

            # 根据大小选择策略
            if size_mb < self.config.quartz_threshold:
                image = self._load_small(file_path, target_size)
                method = "fast"
            elif size_mb < self.config.memory_map_threshold:
                image = self._load_medium(file_path, target_size)
                method = "quartz"
            else:
                image = self._load_large(file_path, target_size)
                method = "memory_map"

            # 更新统计
            duration = time.time() - start_time
            if image is not None:
                self.stats.record_success(method, duration)
            else:
                self.stats.record_failure()

            return image

        except Exception as e:
            logger.error("加载失败 %s: {e}", file_path)
            self.stats.record_failure()
            return None

    def _load_small(self, file_path: str, target_size: tuple[int, int] | None) -> Any | None:
        """小文件：NSImage快速加载"""
        image = load_with_nsimage(file_path)
        if image is not None:
            self.stats.fast_loads += 1
        return image

    def _load_medium(self, file_path: str, target_size: tuple[int, int] | None) -> Any | None:
        """中等文件：Quartz优化加载"""
        if not self.quartz_available:
            # Quartz不可用，回退到NSImage
            return self._load_small(file_path, target_size)

        # 使用Quartz加载
        cgimage = load_with_quartz(file_path, target_size, thumbnail=False)
        if cgimage is None:
            # 加载失败，回退到NSImage
            logger.warning("Quartz加载失败，回退到NSImage: %s", file_path)
            return self._load_small(file_path, target_size)

        self.stats.quartz_loads += 1

        # 如果需要NSImage，转换CGImage
        if self.config.prefer_cgimage_pipeline:
            return cgimage
        return cgimage_to_nsimage(cgimage)

    def _load_large(self, file_path: str, target_size: tuple[int, int] | None) -> Any | None:
        """大文件：内存映射加载"""
        if not self.memory_mapping_available:
            # 内存映射不可用，回退到Quartz
            return self._load_medium(file_path, target_size)

        image = load_with_memory_map(file_path, target_size)
        if image is None:
            # 加载失败，回退到Quartz
            logger.warning("内存映射加载失败，回退到Quartz: %s", file_path)
            return self._load_medium(file_path, target_size)

        self.stats.memory_map_loads += 1
        return image

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息（兼容旧接口）"""
        return self.stats.get_stats()

    def update_stats(self, success: bool, duration: float) -> None:
        """更新统计信息（兼容旧接口）

        Args:
            success: 是否成功
            duration: 耗时（秒）
        """
        if success:
            self.stats.record_success("unknown", duration)
        else:
            self.stats.record_failure()


class PreviewStrategy:
    """预览/缩略图加载策略

    快速生成预览图，适合缩略图列表和快速浏览场景。

    特性：
    - 快速生成缩略图
    - 自动尺寸控制
    - 低内存占用
    """

    def __init__(self, max_size: int = 512, config: LoadingConfig | None = None):
        """初始化预览策略

        Args:
            max_size: 最大尺寸（像素）
            config: 加载配置
        """
        self.config = config or get_default_config()
        self.max_size = max_size or self.config.preview_max_size
        self.stats = LoadingStats()
        self.name = "preview"

        # 检查Quartz可用性
        self.quartz_available = check_quartz_availability()

        logger.debug("PreviewStrategy initialized - max_size: %s", self.max_size)

    def can_handle(self, file_path: str, file_size_mb: float, target_size: tuple[int, int] | None = None) -> bool:
        """检查是否可以处理"""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in (".jpg", ".jpeg", ".png")

    def load(self, file_path: str, target_size: tuple[int, int] | None = None) -> Any | None:
        """加载预览图

        Args:
            file_path: 文件路径
            target_size: 目标尺寸 (width, height)

        Returns:
            预览图对象，失败返回None
        """
        start_time = time.time()

        try:
            # 检查文件格式
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in (".jpg", ".jpeg", ".png"):
                return None

            # 确定目标尺寸
            if target_size is None:
                target_size = (self.max_size, self.max_size)

            # 使用Quartz创建缩略图（最快）
            if self.quartz_available:
                cgimage = load_with_quartz(file_path, target_size, thumbnail=True)
                if cgimage is not None:
                    duration = time.time() - start_time
                    self.stats.record_success("quartz", duration)

                    # 转换为NSImage
                    if self.config.prefer_cgimage_pipeline:
                        return cgimage
                    return cgimage_to_nsimage(cgimage)

            # Quartz不可用或失败，使用NSImage
            image = load_with_nsimage(file_path)
            if image is not None:
                # 缩放到目标尺寸
                image = self._resize_nsimage(image, target_size)

                duration = time.time() - start_time
                self.stats.record_success("nsimage", duration)
                return image

            self.stats.record_failure()
            return None

        except Exception as e:
            logger.error("预览加载失败 %s: {e}", file_path)
            self.stats.record_failure()
            return None

    def _resize_nsimage(self, image: Any, target_size: tuple[int, int]) -> Any:
        """缩放NSImage到目标尺寸

        Args:
            image: NSImage对象
            target_size: 目标尺寸

        Returns:
            缩放后的NSImage
        """
        try:
            from AppKit import NSImage

            # 获取原始尺寸
            size = image.size()
            width, height = size.width, size.height

            # 计算缩放比例
            target_width, target_height = target_size
            scale = min(target_width / width, target_height / height)

            if scale >= 1.0:
                # 不需要缩放
                return image

            # 创建缩放后的图片
            new_width = int(width * scale)
            new_height = int(height * scale)

            resized = NSImage.alloc().initWithSize_((new_width, new_height))
            resized.lockFocus()
            image.drawInRect_fromRect_operation_fraction_(
                ((0, 0), (new_width, new_height)),
                ((0, 0), (width, height)),
                2,
                1.0,  # NSCompositeCopy
            )
            resized.unlockFocus()

            return resized

        except Exception as e:
            logger.error("缩放NSImage失败: %s", e)
            return image

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return self.stats.get_stats()


class AutoStrategy:
    """自动策略选择器

    根据场景自动选择最优策略：
    - 预览模式：使用PreviewStrategy
    - 正常模式：使用OptimizedStrategy

    这是最推荐的策略，适合大多数场景。
    """

    def __init__(self, config: LoadingConfig | None = None):
        """初始化自动策略

        Args:
            config: 加载配置
        """
        self.config = config or get_default_config()
        self.optimized = OptimizedStrategy(self.config)
        self.preview = PreviewStrategy(config=self.config)
        self.name = "auto"

        logger.debug("AutoStrategy initialized")

    def can_handle(self, file_path: str, file_size_mb: float, target_size: tuple[int, int] | None = None) -> bool:
        """检查是否可以处理"""
        return self.optimized.can_handle(file_path, file_size_mb, target_size)

    def load(self, file_path: str, target_size: tuple[int, int] | None = None, preview: bool = False) -> Any | None:
        """自动选择并加载

        Args:
            file_path: 文件路径
            target_size: 目标尺寸
            preview: 是否预览模式

        Returns:
            图片对象，失败返回None
        """
        if preview:
            return self.preview.load(file_path, target_size)
        return self.optimized.load(file_path, target_size)

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息（合并两个策略）"""
        opt_stats = self.optimized.get_stats()
        prev_stats = self.preview.get_stats()

        return {
            "optimized": opt_stats,
            "preview": prev_stats,
            "total_requests": opt_stats["total_requests"] + prev_stats["total_requests"],
            "total_time": opt_stats["total_time"] + prev_stats["total_time"],
        }
