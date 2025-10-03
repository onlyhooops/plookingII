import os
from typing import Any

from ..config.constants import APP_NAME, MAX_CACHE_SIZE
from ..config.manager import get_config
from ..imports import logging

logger = logging.getLogger(APP_NAME)


class SimpleCacheLayer:
    """简化的缓存层实现"""

    def __init__(self, max_size: int = 50):
        self.cache = {}
        self.access_order = []
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def get(self, key: str):
        """获取缓存项"""
        if key in self.cache:
            self.hits += 1
            # 更新访问顺序
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        self.misses += 1
        return None

    def put(self, key: str, value, size_mb: float = 0):
        """添加缓存项"""
        # 如果已存在，更新
        if key in self.cache:
            self.cache[key] = value
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            return True

        # 检查是否需要清理
        while len(self.cache) >= self.max_size and self.access_order:
            oldest_key = self.access_order.pop(0)
            if oldest_key in self.cache:
                del self.cache[oldest_key]

        # 添加新项
        self.cache[key] = value
        self.access_order.append(key)
        return True

    def remove(self, key: str):
        """移除缓存项"""
        if key in self.cache:
            del self.cache[key]
            if key in self.access_order:
                self.access_order.remove(key)
            return True
        return False

    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_order.clear()

    def get_stats(self):
        """获取统计信息"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate
        }


class AdvancedImageCache:
    """高级图像缓存管理器 - 重构版

    使用策略模式和分层架构重构，显著降低复杂度。
    每个缓存层负责特定功能，策略类管理淘汰逻辑。
    """

    def __init__(self, max_size=MAX_CACHE_SIZE) -> None:
        """初始化高级图像缓存管理器

        Args:
            max_size: 最大缓存图片数量，默认使用配置文件中的MAX_CACHE_SIZE
        """
        import threading

        # 简化缓存初始化 - 移除复杂的多层架构
        self.cache = {}
        self.access_order = []
        self.max_size = max_size

        # 两层为默认（main/preview）；其余层按功能开关决定是否启用
        enable_preload = not get_config("feature.disable_preload_layer", True)
        enable_progressive = not get_config("feature.disable_progressive_layer", True)

        # 主要缓存层的快速引用
        self.main_cache = SimpleCacheLayer(max_size=max_size)
        self.preview_cache = SimpleCacheLayer(max_size=30)
        self.preload_cache = SimpleCacheLayer(max_size=20) if enable_preload else None
        self.progressive_cache = SimpleCacheLayer(max_size=10) if enable_progressive else None

        # 构建层映射（默认仅 main/preview）
        self.cache_layers = {
            "main": self.main_cache,
            "preview": self.preview_cache,
        }
        if self.preload_cache is not None:
            self.cache_layers["preload"] = self.preload_cache
        if self.progressive_cache is not None:
            self.cache_layers["progressive"] = self.progressive_cache

        # 线程安全锁
        self._cache_lock = threading.RLock()

        # 内存监控器
        self.memory_monitor = None

        # 图像处理器由外部注入，避免重复创建导致策略重复初始化
        self.image_processor = None

        # 文件大小缓存
        self.file_size_cache = {}

        # 性能统计
        self.cache_hits = 0
        self.cache_misses = 0

        # 初始化时调整动态配额
        try:
            self._adjust_dynamic_quotas()
        except Exception:
            logger.exception("Failed to adjust dynamic quotas on init")

    def _init_cache_layers(self):
        """初始化缓存层（已废弃，保留以兼容旧引用）。

        说明：当前实现已使用 SimpleCacheLayer 直接构建层并在 __init__ 完成映射。
        此函数作为占位符，不再进行任何操作。
        """
        return

    def get(self, key: str, prefer_preview: bool = False,
            target_size: tuple[int, int] | None = None) -> Any | None:
        """获取缓存的图片

        Args:
            key: 图像键（通常为文件路径）
            prefer_preview: 是否优先返回预览缓存中的中分辨率图像
            target_size: 目标尺寸（用于调用方的显示或策略记录）

        Returns:
            图像对象（NSImage 或 PIL.Image 等）或 None
        """
        with self._cache_lock:
            # 优先从预览缓存获取（如果请求预览）
            if prefer_preview:
                result = self.preview_cache.get(key)
                if result:
                    self.cache_hits += 1
                    return result

            # 从主缓存获取
            result = self.main_cache.get(key)
            if result:
                self.cache_hits += 1
                return result

            # 检查预加载缓存（可能被禁用）
            result = self.preload_cache.get(key) if self.preload_cache else None
            if result:
                self.cache_hits += 1
                return result

            # 检查渐进式缓存（可能被禁用）
            result = self.progressive_cache.get(key) if self.progressive_cache else None
            if result:
                self.cache_hits += 1
                return result

            # 缓存未命中
            self.cache_misses += 1
            return None


    # 重载put方法以支持旧API签名
    def put(self, key: str, image: Any, is_preview: bool = False,
            target_size: tuple[int, int] | None = None,
            cache_type: str = "main", is_preload: bool = False) -> bool:
        """重载put方法以支持旧API签名"""
        # 根据参数选择缓存层
        if is_preview:
            layer = "preview"
        elif is_preload:
            # 若预加载层不可用，则回退到 preview 层
            layer = "preload" if "preload" in self.cache_layers else "preview"
        elif cache_type == "progressive":
            layer = "progressive"
        else:
            layer = "main"

        # 估算图像大小
        estimated_size_mb = self._estimate_image_size(image)

        # 调用新的put方法
        return self.put_new(key, image, layer, estimated_size_mb)

    def put_new(self, key: str, value: Any, layer: str = "main",
                estimated_size_mb: float | None = None) -> bool:
        """新的put方法实现"""
        if layer not in self.cache_layers:
            # 层被禁用时的兼容回退：优先 preview，其次 main
            fallback = "preview" if "preview" in self.cache_layers else "main"
            return self.put_new(key, value, fallback, estimated_size_mb)

        # 自动估算内存大小
        if estimated_size_mb is None:
            estimated_size_mb = self._estimate_image_size(value)

        with self._cache_lock:
            try:
                cache_layer = self.cache_layers[layer]
                success = cache_layer.put(key, value, estimated_size_mb)

                if success:
                    logger.debug(f"Successfully added {key} to {layer} cache")
                else:
                    logger.warning(f"Failed to add {key} to {layer} cache")

                return success

            except Exception as e:
                logger.error(f"Error adding {key} to {layer} cache: {e}")
        return False

    def _is_landscape_image(self, image) -> bool:
        """判断是否为横向图像（兼容旧API）"""
        try:
            # 支持 PIL Image 与 NSImage（尽力而为）
            if hasattr(image, "size"):
                w, h = image.size
                return bool(w > h)
            if hasattr(image, "size") and callable(image.size):
                sz = image.size()
                w = getattr(sz, "width", 0) if hasattr(sz, "width") else sz[0]
                h = getattr(sz, "height", 0) if hasattr(sz, "height") else sz[1]
                return bool(w > h)
        except Exception:
            # 无法判断时默认非横向
            return False

    def _is_landscape_image_by_path(self, file_path: str) -> bool:
        """通过文件路径判断是否为横向图像（兼容旧API）"""
        try:
            from .functions import get_image_dimensions_safe
            dims = get_image_dimensions_safe(file_path)
            if dims:
                w, h = dims
                return bool(w > h)
            return False
        except Exception:
            # 无法判断时默认非横向
            return False

    def _evict_oldest(self) -> Any | None:
        """驱逐最旧的缓存项（兼容旧API）"""
        try:
            # 从主缓存层驱逐最旧的项
            if "main" in self.cache_layers:
                cache_layer = self.cache_layers["main"]
                # 假设缓存层有evict_oldest方法
                if hasattr(cache_layer, "evict_oldest"):
                    return cache_layer.evict_oldest()
                # 如果没有evict_oldest方法，尝试从缓存中移除一个项
                if hasattr(cache_layer, "cache") and cache_layer.cache:
                    # 移除第一个项（假设是LRU顺序）
                    key = next(iter(cache_layer.cache))
                    return cache_layer.remove(key)
            return None
        except Exception:
            return None

    def _evict_oldest_preview(self) -> Any | None:
        """驱逐最旧的预览缓存项（兼容旧API）"""
        try:
            # 从预览缓存层驱逐最旧的项
            if "preview" in self.cache_layers:
                cache_layer = self.cache_layers["preview"]
                # 假设缓存层有evict_oldest方法
                if hasattr(cache_layer, "evict_oldest"):
                    return cache_layer.evict_oldest()
                # 如果没有evict_oldest方法，尝试从缓存中移除一个项
                if hasattr(cache_layer, "cache") and cache_layer.cache:
                    # 移除第一个项（假设是LRU顺序）
                    key = next(iter(cache_layer.cache))
                    return cache_layer.remove(key)
            return None
        except Exception:
            return None

    def clear_overflow(self) -> None:
        """按水位清理缓存溢出项目（轻量策略）。

        - 对 main/preview 层分别检测当前项数是否超过配额的 90%，
          若超过则裁剪到配额的 80%。
        - 基于 SimpleCacheLayer.access_order 按最旧优先移除。
        """
        try:
            with self._cache_lock:
                def _trim_layer(layer_name: str, target_ratio: float = 0.8, high_ratio: float = 0.9) -> None:
                    layer = self.cache_layers.get(layer_name)
                    if layer is None:
                        return
                    # 当前项数与上限
                    max_size = getattr(layer, "max_size", None)
                    cache_dict = getattr(layer, "cache", None)
                    order_list = getattr(layer, "access_order", None)
                    if not max_size or cache_dict is None or order_list is None:
                        return
                    cur = len(cache_dict)
                    high = int(max_size * high_ratio)
                    if cur <= high:
                        return
                    target = max(0, int(max_size * target_ratio))
                    # 逐步按最旧顺序移除直到达到目标
                    while len(cache_dict) > target and order_list:
                        oldest_key = order_list.pop(0)
                        if oldest_key in cache_dict:
                            del cache_dict[oldest_key]

                # 针对主缓存与预览缓存执行裁剪
                _trim_layer("preview")
                _trim_layer("main")
        except Exception:
            # 清理失败不应影响主流程
            pass

    def _evict_oldest_preload(self) -> Any | None:
        """驱逐最旧的预加载缓存项（兼容旧API）"""
        try:
            # 从预加载缓存层驱逐最旧的项
            if "preload" in self.cache_layers:
                cache_layer = self.cache_layers["preload"]
                # 假设缓存层有evict_oldest方法
                if hasattr(cache_layer, "evict_oldest"):
                    return cache_layer.evict_oldest()
                # 如果没有evict_oldest方法，尝试从缓存中移除一个项
                if hasattr(cache_layer, "cache") and cache_layer.cache:
                    # 移除第一个项（假设是LRU顺序）
                    key = next(iter(cache_layer.cache))
                    return cache_layer.remove(key)
            return None
        except Exception:
            return None

    def remove(self, key: str, layer: str | None = None) -> Any | None:
        """从缓存中移除图像

        Args:
            key: 缓存键
            layer: 缓存层名称，如果为None则从所有层移除

        Returns:
            被移除的图像对象，如果不存在则返回None
        """
        with self._cache_lock:
            if layer:
                # 从指定层移除
                if layer in self.cache_layers:
                    return self.cache_layers[layer].remove(key)
                return None
            # 从所有层移除
            for cache_layer in self.cache_layers.values():
                result = cache_layer.remove(key)
                if result:
                    return result
            return None

    def clear_all(self) -> None:
        """清空所有缓存层"""
        with self._cache_lock:
            for cache_layer in self.cache_layers.values():
                cache_layer.clear()

    # 重载clear方法以支持旧API签名（无参数）
    def clear(self) -> None:
        """重载clear方法以支持旧API签名（无参数）"""
        self.clear_all()

    def get_size(self) -> int:
        """获取缓存总大小（兼容旧API）"""
        try:
            total_size = 0
            for cache_layer in self.cache_layers.values():
                if hasattr(cache_layer, "size"):
                    total_size += cache_layer.size
                elif hasattr(cache_layer, "cache"):
                    total_size += len(cache_layer.cache)
            return total_size
        except Exception:
            return 0

    def get_total_size(self) -> int:
        """获取缓存总大小（兼容旧API）"""
        return self.get_size()

    def get_memory_usage(self) -> float:
        """获取内存使用量（MB）（兼容旧API）"""
        try:
            total_memory_mb = 0.0
            for cache_layer in self.cache_layers.values():
                if hasattr(cache_layer, "memory_usage_mb"):
                    total_memory_mb += cache_layer.memory_usage_mb
                elif hasattr(cache_layer, "cache"):
                    # 估算内存使用量
                    for key, value in cache_layer.cache.items():
                        total_memory_mb += self._estimate_image_size(value)
            return total_memory_mb
        except Exception:
            return 0.0

    def get_preload_memory_usage(self) -> float:
        """获取预加载缓存内存使用量（MB）（兼容旧API）"""
        try:
            if "preload" in self.cache_layers:
                cache_layer = self.cache_layers["preload"]
                if hasattr(cache_layer, "memory_usage_mb"):
                    return cache_layer.memory_usage_mb
                if hasattr(cache_layer, "cache"):
                    # 估算内存使用量
                    total_memory_mb = 0.0
                    for key, value in cache_layer.cache.items():
                        total_memory_mb += self._estimate_image_size(value)
                    return total_memory_mb
            return 0.0
        except Exception:
            return 0.0

    def get_cache_stats(self) -> dict:
        """获取缓存统计信息（兼容旧API）"""
        return self.get_stats()

    def load_image_with_strategy(
        self,
        file_path: str,
        strategy: str = "auto",
        target_size=None,
        force_reload: bool = False,
    ) -> Any | None:
        """使用指定策略加载图像（兼容旧API）"""
        try:
            # 如果不强制重新加载，先检查缓存
            if not force_reload:
                cached_image = self.get(file_path)
                if cached_image:
                    return cached_image

            # 使用图像处理器加载图像
            if hasattr(self, "image_processor") and self.image_processor:
                image = self.image_processor.load_image_optimized(file_path, target_size, strategy=strategy)
                if image:
                    # 缓存加载的图像
                    self.put(file_path, image, "main")
                return image
            return None
        except Exception:
            return None

    def get_stats(self) -> dict:
        """获取缓存统计信息

        Returns:
            dict: 包含各层缓存的统计信息
        """
        with self._cache_lock:
            stats = {
                "total_hits": self.cache_hits,
                "total_misses": self.cache_misses,
                "total_requests": self.cache_hits + self.cache_misses,
                "layers": {}
            }

            # 计算总体命中率
            if stats["total_requests"] > 0:
                stats["hit_rate"] = (self.cache_hits / stats["total_requests"]) * 100
            else:
                stats["hit_rate"] = 0.0

            # 各层统计信息
            for layer_name, cache_layer in self.cache_layers.items():
                stats["layers"][layer_name] = cache_layer.get_stats()

            return stats

    def _estimate_image_size(self, image: Any) -> float:
        """估算图像的内存大小

        Args:
            image: 图像对象

        Returns:
            float: 估算的内存大小（MB）
        """
        try:
            # 这里应该根据实际的图像类型来实现
            # 暂时返回一个默认值
            return 1.0
        except Exception:
            return 1.0

    def get_file_size_mb(self, file_path: str) -> float:
        """获取文件大小（MB），带本地缓存优化

        使用文件大小缓存避免重复的磁盘I/O操作，提升文件大小查询的性能。

        Args:
            file_path: 文件路径

        Returns:
            float: 文件大小，单位为MB；获取失败时返回0

        Note:
            - 首次查询时缓存结果，后续查询直接返回缓存值
            - 线程安全：在缓存锁保护下执行
            - 异常处理：获取失败时记录0并缓存
        """
        with self._cache_lock:
            if file_path not in self.file_size_cache:
                try:
                    size_bytes = os.path.getsize(file_path)
                    self.file_size_cache[file_path] = size_bytes / (1024 * 1024)
                except Exception:
                    logger.exception("Failed to get file size for %s", file_path)
                    self.file_size_cache[file_path] = 0
            return self.file_size_cache[file_path]

    def _adjust_dynamic_quotas(self) -> None:
        """调整动态内存配额

        根据系统可用内存动态调整各缓存层的内存配额。
        """
        try:
            if not self.memory_monitor:
                return

            # 获取可用内存
            available_memory_mb = self.memory_monitor.get_available_memory_mb()

            # 根据可用内存调整配额
            if available_memory_mb < 1000:
                # 内存不足，减少配额
                self._reduce_memory_quotas()
            elif available_memory_mb > 4000:
                # 内存充足，增加配额
                self._increase_memory_quotas()

        except Exception as e:
            logger.warning(f"Failed to adjust dynamic quotas: {e}")

    def _reduce_memory_quotas(self) -> None:
        """减少内存配额"""
        try:
            # 减少各层缓存的内存配额
            for cache_layer in self.cache_layers.values():
                cache_layer.max_memory_mb *= 0.8

            logger.info("Reduced memory quotas due to low available memory")
        except Exception as e:
            logger.warning(f"Failed to reduce memory quotas: {e}")

    def _increase_memory_quotas(self) -> None:
        """增加内存配额"""
        try:
            # 增加各层缓存的内存配额
            for cache_layer in self.cache_layers.values():
                cache_layer.max_memory_mb *= 1.2

            logger.info("Increased memory quotas due to abundant available memory")
        except Exception as e:
            logger.warning(f"Failed to increase memory quotas: {e}")

    def trim_to_budget(self) -> None:
        """根据预算裁剪缓存

        当内存使用超过预算时，主动清理缓存项。
        """
        with self._cache_lock:
            try:
                # 检查各层缓存是否需要清理
                for layer_name, cache_layer in self.cache_layers.items():
                    if cache_layer.current_memory_mb > cache_layer.max_memory_mb * 0.9:
                        logger.info(f"Trimming {layer_name} cache to budget")
                        self._trim_layer_to_budget(cache_layer)

            except Exception as e:
                logger.warning(f"Failed to trim cache to budget: {e}")

    def _trim_layer_to_budget(self, cache_layer) -> None:
        """裁剪指定层到预算范围内"""
        try:
            target_memory = cache_layer.max_memory_mb * 0.8

            while (cache_layer.current_memory_mb > target_memory and
                   len(cache_layer.cache) > 0):
                # 使用策略选择要淘汰的项
                key, value = cache_layer.strategy.select_eviction_candidate(cache_layer.cache)
                cache_layer.remove(key)

        except Exception as e:
            logger.warning(f"Failed to trim cache layer: {e}")
