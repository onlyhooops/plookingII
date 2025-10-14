"""
加载辅助函数

提供各种图片加载方法的底层实现。

Author: PlookingII Team
Date: 2025-10-06
"""

import logging
import mmap
import os
from typing import Any

logger = logging.getLogger(__name__)

# 文件大小缓存（避免重复 os.path.getsize）
_file_size_cache: dict[str, tuple[float, float]] = {}  # path -> (size_mb, timestamp)
_FILE_SIZE_CACHE_TTL = 5.0  # 5秒TTL


def get_file_size_mb(file_path: str, use_cache: bool = True) -> float:
    """获取文件大小(MB)

    Args:
        file_path: 文件路径
        use_cache: 是否使用缓存

    Returns:
        文件大小（MB）
    """
    try:
        import time

        now = time.time()

        # 检查缓存
        if use_cache and file_path in _file_size_cache:
            size_mb, timestamp = _file_size_cache[file_path]
            if (now - timestamp) < _FILE_SIZE_CACHE_TTL:
                return size_mb

        # 获取文件大小
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)

        # 更新缓存
        if use_cache:
            _file_size_cache[file_path] = (size_mb, now)

        return size_mb
    except Exception as e:
        logger.warning("获取文件大小失败 %s: {e}", file_path)
        return 0.0


def clear_file_size_cache() -> None:
    """清除文件大小缓存"""
    _file_size_cache.clear()


def check_quartz_availability() -> bool:
    """检查Quartz是否可用"""
    try:
        from Quartz import CGImageSourceCreateWithURL  # noqa: F401

        return True
    except ImportError:
        return False


def load_with_nsimage(file_path: str) -> Any | None:
    """使用NSImage加载（快速，适合小文件）

    Args:
        file_path: 文件路径

    Returns:
        NSImage对象，失败返回None
    """
    try:
        from AppKit import NSImage

        image = NSImage.alloc().initWithContentsOfFile_(file_path)
        return image
    except Exception as e:
        logger.exception("NSImage加载失败 %s: {e}", file_path)
        return None


def load_with_quartz(file_path: str, target_size: tuple[int, int] | None = None, thumbnail: bool = False) -> Any | None:
    """使用Quartz加载（优化，适合中等文件）

    Args:
        file_path: 文件路径
        target_size: 目标尺寸 (width, height)
        thumbnail: 是否创建缩略图

    Returns:
        CGImage对象，失败返回None
    """
    try:
        from Foundation import NSURL
        from Quartz import (
            CGImageSourceCreateImageAtIndex,
            CGImageSourceCreateThumbnailAtIndex,
            CGImageSourceCreateWithURL,
            kCGImageSourceCreateThumbnailFromImageAlways,
            kCGImageSourceCreateThumbnailWithTransform,
            kCGImageSourceShouldAllowFloat,
            kCGImageSourceShouldCache,
            kCGImageSourceThumbnailMaxPixelSize,
        )

        url = NSURL.fileURLWithPath_(file_path)
        source = CGImageSourceCreateWithURL(url, None)

        if not source:
            logger.warning("无法创建CGImageSource: %s", file_path)
            return None

        if thumbnail and target_size:
            # 创建缩略图
            max_size = max(target_size)
            options = {
                kCGImageSourceThumbnailMaxPixelSize: max_size,
                kCGImageSourceShouldCache: True,
                kCGImageSourceCreateThumbnailFromImageAlways: True,
                kCGImageSourceCreateThumbnailWithTransform: True,
                kCGImageSourceShouldAllowFloat: True,
            }
            return CGImageSourceCreateThumbnailAtIndex(source, 0, options)
        # 加载完整图片
        options = {
            kCGImageSourceShouldCache: True,
            kCGImageSourceShouldAllowFloat: True,
        }
        return CGImageSourceCreateImageAtIndex(source, 0, options)

    except Exception as e:
        logger.exception("Quartz加载失败 %s: {e}", file_path)
        return None


def load_with_memory_map(file_path: str, target_size: tuple[int, int] | None = None) -> Any | None:
    """使用内存映射加载（大文件优化）

    Args:
        file_path: 文件路径
        target_size: 目标尺寸（当前未使用）

    Returns:
        NSImage对象，失败返回None
    """
    try:
        from AppKit import NSData, NSImage

        with open(file_path, "rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            # 从内存映射创建NSData
            data = NSData.dataWithBytes_length_(mm, len(mm))
            image = NSImage.alloc().initWithData_(data)
            return image
    except Exception as e:
        logger.exception("内存映射加载失败 %s: {e}", file_path)
        return None


def cgimage_to_nsimage(cgimage: Any) -> Any | None:
    """将CGImage转换为NSImage

    Args:
        cgimage: CGImage对象

    Returns:
        NSImage对象，失败返回None
    """
    try:
        from AppKit import NSBitmapImageRep, NSImage

        if cgimage is None:
            return None

        # 获取CGImage尺寸
        from Quartz import CGImageGetHeight, CGImageGetWidth

        width = CGImageGetWidth(cgimage)
        height = CGImageGetHeight(cgimage)

        # 创建NSImage
        bitmap = NSBitmapImageRep.alloc().initWithCGImage_(cgimage)
        image = NSImage.alloc().initWithSize_((width, height))
        image.addRepresentation_(bitmap)

        return image
    except Exception as e:
        logger.exception("CGImage转NSImage失败: %s", e)
        return None


def get_image_dimensions(file_path: str) -> tuple[int, int] | None:
    """获取图片尺寸（不加载完整图片）

    Args:
        file_path: 文件路径

    Returns:
        (width, height) 或 None
    """
    try:
        from Foundation import NSURL
        from Quartz import (
            CGImageSourceCopyPropertiesAtIndex,
            CGImageSourceCreateWithURL,
            kCGImagePropertyPixelHeight,
            kCGImagePropertyPixelWidth,
        )

        url = NSURL.fileURLWithPath_(file_path)
        source = CGImageSourceCreateWithURL(url, None)

        if not source:
            return None

        props = CGImageSourceCopyPropertiesAtIndex(source, 0, None)
        if not props:
            return None

        width = props.get(kCGImagePropertyPixelWidth, 0)
        height = props.get(kCGImagePropertyPixelHeight, 0)

        return (int(width), int(height))
    except Exception as e:
        logger.exception("获取图片尺寸失败 %s: {e}", file_path)
        return None


def get_loader(strategy: str = "auto"):
    """获取加载器实例（工厂函数）

    Args:
        strategy: 策略名称 ('auto', 'optimized', 'preview')

    Returns:
        对应的加载器实例
    """
    from .strategies import AutoStrategy, OptimizedStrategy, PreviewStrategy

    if strategy == "auto":
        return AutoStrategy()
    if strategy == "optimized":
        return OptimizedStrategy()
    if strategy == "preview":
        return PreviewStrategy()
    logger.warning("未知策略 %s，使用 auto", strategy)
    return AutoStrategy()


def create_loader(config=None, **kwargs):
    """创建自定义加载器

    Args:
        config: LoadingConfig对象
        **kwargs: 传递给策略的额外参数

    Returns:
        OptimizedStrategy实例
    """
    from .config import LoadingConfig
    from .strategies import OptimizedStrategy

    if config is None:
        config = LoadingConfig.from_global_config()

    return OptimizedStrategy(config=config, **kwargs)
