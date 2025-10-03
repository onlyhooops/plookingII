"""
精确图像内存估算器模块

提供基于实际图像数据的精确内存计算，替换硬编码的内存估算。
支持NSImage和PIL Image的精确内存使用量计算。

主要功能：
    - NSImage内存使用量精确计算
    - PIL Image内存使用量精确计算
    - 缩放因子感知的内存计算
    - 多种颜色模式支持

Author: PlookingII Team
Version: 1.0.0
"""

import logging
from typing import Any

from ..config.constants import APP_NAME
from ..imports import NSImage

logger = logging.getLogger(APP_NAME)


class ImageMemoryEstimator:
    """精确的图像内存估算器"""

    def __init__(self):
        """初始化内存估算器"""
        self.cache = {}  # 缓存计算结果
        self.cache_max_size = 1000  # 最大缓存条目数

    def estimate_nsimage_memory(self, image: NSImage) -> float:
        """估算NSImage内存使用量（MB）

        Args:
            image: NSImage对象

        Returns:
            float: 估算的内存使用量（MB）
        """
        try:
            if not image:
                return 0.0

            # 生成缓存键
            cache_key = f"nsimage_{id(image)}"
            if cache_key in self.cache:
                return self.cache[cache_key]

            # 获取图像尺寸
            size = image.size()
            width, height = size.width, size.height

            # 获取缩放因子（Retina显示器支持）
            scale_factor = self._get_nsimage_scale_factor(image)

            # 计算实际像素尺寸
            actual_width = int(width * scale_factor)
            actual_height = int(height * scale_factor)

            # NSImage通常使用RGBA格式，每像素4字节
            bytes_per_pixel = 4
            total_bytes = actual_width * actual_height * bytes_per_pixel

            memory_mb = total_bytes / (1024 * 1024)

            # 缓存结果
            self._cache_result(cache_key, memory_mb)

            return memory_mb

        except Exception as e:
            logger.warning(f"Failed to estimate NSImage memory: {e}")
            return 1.0  # 回退到默认值

    def estimate_pil_memory(self, image) -> float:
        """估算PIL Image内存使用量（MB）

        Args:
            image: PIL Image对象

        Returns:
            float: 估算的内存使用量（MB）
        """
        try:
            if not image:
                return 0.0

            # 生成缓存键
            cache_key = f"pil_{id(image)}_{image.size}_{image.mode}"
            if cache_key in self.cache:
                return self.cache[cache_key]

            width, height = image.size
            mode = image.mode

            # 根据颜色模式计算每像素字节数
            bytes_per_pixel = self._get_pil_bytes_per_pixel(mode)

            total_bytes = width * height * bytes_per_pixel
            memory_mb = total_bytes / (1024 * 1024)

            # 缓存结果
            self._cache_result(cache_key, memory_mb)

            return memory_mb

        except Exception as e:
            logger.warning(f"Failed to estimate PIL memory: {e}")
            return 1.0

    def estimate_image_memory(self, image: Any) -> float:
        """通用图像内存估算

        Args:
            image: 图像对象（NSImage或PIL Image）

        Returns:
            float: 估算的内存使用量（MB）
        """
        if hasattr(image, "size") and hasattr(image, "backingScaleFactor"):
            # NSImage
            return self.estimate_nsimage_memory(image)
        if hasattr(image, "size") and hasattr(image, "mode"):
            # PIL Image
            return self.estimate_pil_memory(image)
        # 未知类型，使用默认估算
        logger.debug(f"Unknown image type: {type(image)}")
        return 1.0

    def _get_nsimage_scale_factor(self, image: NSImage) -> float:
        """获取NSImage的缩放因子"""
        try:
            # 尝试多种方法获取缩放因子
            if hasattr(image, "backingScaleFactor"):
                return image.backingScaleFactor()
            if hasattr(image, "recommendedLayerContentsScale"):
                return image.recommendedLayerContentsScale(0)
            # 检查主屏幕的缩放因子
            try:
                from AppKit import NSScreen


                main_screen = NSScreen.mainScreen()
                if main_screen and hasattr(main_screen, "backingScaleFactor"):
                    return main_screen.backingScaleFactor()
            except Exception:
                pass

            return 1.0  # 默认缩放因子
        except Exception:
            return 1.0

    def _get_pil_bytes_per_pixel(self, mode: str) -> int:
        """获取PIL图像模式的每像素字节数"""
        bytes_per_pixel_map = {
            "L": 1,      # 灰度
            "P": 1,      # 调色板
            "RGB": 3,    # RGB
            "RGBA": 4,   # RGBA
            "CMYK": 4,   # CMYK
            "LAB": 3,    # LAB
            "HSV": 3,    # HSV
            "I": 4,      # 32位整数
            "F": 4,      # 32位浮点
        }
        return bytes_per_pixel_map.get(mode, 4)  # 默认4字节

    def _cache_result(self, key: str, value: float):
        """缓存计算结果"""
        if len(self.cache) >= self.cache_max_size:
            # 清理最旧的缓存条目
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[key] = value

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()

    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        return {
            "cache_size": len(self.cache),
            "max_cache_size": self.cache_max_size,
            "cache_usage_ratio": len(self.cache) / self.cache_max_size
        }
