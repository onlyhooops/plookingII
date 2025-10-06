import os

from ..config.constants import APP_NAME, IMAGE_PROCESSING_CONFIG
from ..config.manager import get_config
from ..imports import logging, threading, time
from .image_rotation import ImageRotationProcessor
from .optimized_loading_strategies import OptimizedLoadingStrategyFactory

logger = logging.getLogger(APP_NAME)
_dual_thread_start_logged = False
_dual_thread_log_lock = threading.Lock()

class HybridImageProcessor:
    """图像处理器 - 重构版

    使用策略模式重构，将复杂的加载逻辑抽象化。
    每个加载策略负责特定的加载模式，提高代码可维护性。
    """

    def __init__(self):
        """初始化混合图像处理器

        实现 macOS 原生通道和 PIL 兜底的图像处理机制，包括：
        - Quartz/ImageIO 硬件加速处理
        - PIL 备用处理方案
        - 双线程处理机制
        - 性能统计和缓存优化
        - 智能格式选择和加载策略

        注意：
            - 自动检测 Quartz 可用性
            - 根据配置处理EXIF方向信息
            - 支持多种加载模式（快速、自动、预览）
        """
        self.quartz_enabled = IMAGE_PROCESSING_CONFIG["quartz_enabled"]
        # 严格Quartz-only：若不可用则早失败
        if IMAGE_PROCESSING_CONFIG.get("strict_quartz_only", False) and not self.quartz_enabled:
            raise RuntimeError("Quartz is required (strict_quartz_only) but not available on this platform.")

        # 初始化组件
        self._init_quartz_components()

        # 性能统计（增强版）
        self.processing_stats = {
            "quartz_processed": 0,
            "pil_fallback": 0,
            "fast_loaded": 0,  # 快速加载统计
            "total_processing_time": 0.0,
            "quartz_avg_time": 0.0,
            "pil_avg_time": 0.0,
            "cache_hits": 0,
            "gpu_accelerated": 0,
        }

        # 双线程处理机制
        if IMAGE_PROCESSING_CONFIG.get("dual_thread_processing", True):
            self._init_dual_thread_processing()

        # 智能缓存
        self.format_performance_cache = {}  # 格式性能缓存
        self.size_threshold_cache = {}  # 尺寸阈值缓存

        # 加载策略
        self._init_loading_strategies()

        # 图像旋转处理器
        self.rotation_processor = ImageRotationProcessor()

        # 轻量文件大小缓存，减少重复 os.stat 调用
        self._file_size_cache = {}
        # 轻量扩展名缓存
        self._ext_cache = {}

    def _init_quartz_components(self):
        """初始化Quartz图像处理组件"""
        if not self.quartz_enabled:
            return

        try:
            # 配置Quartz选项（启用EXIF方向自动变换）
            self.quartz_options = {
                "kCGImageSourceShouldCache": True,
                "kCGImageSourceShouldAllowFloat": True,
                "kCGImageSourceCreateThumbnailFromImageAlways": True,
                "kCGImageSourceCreateThumbnailWithTransform": True  # 启用EXIF方向处理
            }
        except Exception:
            self.quartz_enabled = False

    def _init_loading_strategies(self):
        """初始化精简的加载策略"""
        self.loading_strategies = {
            "optimized": OptimizedLoadingStrategyFactory.create_strategy("optimized"),
            "preview": OptimizedLoadingStrategyFactory.create_strategy("preview"),
            "auto": OptimizedLoadingStrategyFactory.create_strategy("auto"),
            "fast": OptimizedLoadingStrategyFactory.create_strategy("fast")
        }

    def load_image_optimized(self, file_path, target_size=None, progressive=False, strategy="auto"):
        """智能图像加载 - 重构版

        使用策略模式简化加载逻辑，根据文件特征自动选择最优策略。

        Args:
            file_path: 图像文件路径
            target_size: 目标尺寸
            progressive: 已废弃参数（兼容旧接口），请使用 strategy
            strategy: 加载策略名称

        Returns:
            加载的图像对象，失败时返回None
        """
        start_time = time.time()

        try:
            # 获取文件信息
            file_size_mb = self._get_file_size_mb(file_path)
            file_ext = self._get_file_extension(file_path)

            # 验证文件格式
            if not self._is_supported_format(file_ext):
                return None

            # 选择并执行加载策略（原图优先：禁用预览策略介入）
            selected_strategy = self._select_loading_strategy(strategy, file_size_mb)
            if not selected_strategy:
                logger.warning(f"No suitable loading strategy found for {file_path}")
                return None

            # 执行加载
            # 原图优先：当开关启用时，不向策略层传递target_size以避免缩略图路径
            if get_config("feature.full_res_browse", True):
                effective_target = None
            else:
                effective_target = target_size
            result = self._execute_loading_strategy(selected_strategy, file_path, effective_target, file_size_mb)

            # 更新统计信息（兼容旧签名，仅传文件扩展名与耗时）
            self._update_performance_stats(file_ext, time.time() - start_time)

            return result

        except Exception as e:
            logger.error(f"Failed to load image {file_path}: {e}")
            self._update_performance_stats(file_ext, time.time() - start_time)
            return None

    def _get_file_size_mb(self, file_path: str) -> float:
        """获取文件大小（MB）

        Args:
            file_path: 文件路径

        Returns:
            float: 文件大小（MB）
        """
        try:
            if file_path in self._file_size_cache:
                return self._file_size_cache[file_path]
            size_bytes = os.path.getsize(file_path)
            size_mb = size_bytes / (1024 * 1024)
            # 简单上限，避免缓存过大
            if len(self._file_size_cache) > 2048:
                self._file_size_cache.clear()
            self._file_size_cache[file_path] = size_mb
            return size_mb
        except Exception as e:
            logger.warning(f"Failed to get file size for {file_path}: {e}")
            return 0.0

    def _get_file_extension(self, file_path: str) -> str:
        """获取文件扩展名

        Args:
            file_path: 文件路径

        Returns:
            str: 文件扩展名（小写，不含点号）
        """
        try:
            if file_path in self._ext_cache:
                return self._ext_cache[file_path]
            ext = os.path.splitext(file_path)[1].lower().lstrip(".")
            if len(self._ext_cache) > 2048:
                self._ext_cache.clear()
            self._ext_cache[file_path] = ext
            return ext
        except Exception:
            return ""

    def _is_supported_format(self, file_ext: str) -> bool:
        """检查文件格式是否支持

        Args:
            file_ext: 文件扩展名

        Returns:
            bool: 是否支持
        """
        # 范围收敛：仅 JPG/JPEG/PNG
        return file_ext in ("jpg", "jpeg", "png")

    # 兼容旧API：用于判断是否使用增强的 Quartz 路径
    def _should_use_quartz_enhanced(self, file_path: str, file_size_mb: float, file_ext: str) -> bool:
        try:
            return self.quartz_enabled and file_size_mb >= 10
        except Exception:
            return False

    # 兼容旧API：基础 Quartz 判定
    def _should_use_quartz(self, file_path: str, file_size_mb: float) -> bool:
        try:
            return self.quartz_enabled and file_size_mb >= 10
        except Exception:
            return False

    # 兼容旧API：增强的 Quartz 加载
    def _load_with_quartz_enhanced(self, file_path: str, target_size=None):
        try:
            # 委托给优化策略，内部会根据文件大小与Quartz可用性选择路径
            strategy = self.loading_strategies.get("optimized")
            return strategy.load(file_path, target_size)
        except Exception:
            return None

    # 兼容旧API：基础 Quartz 加载
    def _load_with_quartz(self, file_path: str, target_size=None):
        try:
            strategy = self.loading_strategies.get("optimized")
            return strategy.load(file_path, target_size)
        except Exception:
            return None

    # 兼容旧API：增强的 PIL 加载
    def _load_with_pil_enhanced(self, file_path: str, target_size=None):
        try:
            # 兜底走 optimized（内部会回退到 PIL 方案）
            strategy = self.loading_strategies.get("optimized")
            return strategy.load(file_path, target_size)
        except Exception:
            return None

    # 兼容旧API：判断横向图像
    def _is_landscape_image(self, image) -> bool:
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

    # 兼容旧API：应用横向优化
    def _apply_landscape_optimization(self, image):
        try:
            # 简单实现：直接返回原图
            return image
        except Exception:
            return None

    # 兼容旧API：图像加载工作器
    def _image_load_worker(self):
        try:
            # 简单实现：返回None（旧API可能期望一个工作器对象）
            return
        except Exception:
            return

    # 兼容旧API：UI更新工作器
    def _ui_update_worker(self):
        try:
            # 简单实现：返回None（旧API可能期望一个工作器对象）
            return
        except Exception:
            return

    # 兼容旧API：队列图像加载
    def queue_image_load(self, file_path: str, target_size=None, callback=None):
        try:
            # 委托给优化策略
            strategy = self.loading_strategies.get("optimized")
            result = strategy.load(file_path, target_size)
            # 如果有回调函数，调用它
            if callback and callable(callback):
                callback(result)
            return result
        except Exception:
            return None

    # 兼容旧API：队列UI更新
    def queue_ui_update(self, update_func, *args):
        try:
            # 如果有更新函数，调用它
            if update_func and callable(update_func):
                return update_func(*args)
            return True
        except Exception:
            return False

    # 兼容旧API，提供占位实现，委托到优化策略的快速路径
    def _load_fast_mode(self, file_path: str, file_ext: str):
        try:
            strategy = self.loading_strategies.get("fast") or self.loading_strategies.get("optimized")
            # 旧API传入的是 file_ext，这里忽略并走快速策略
            return strategy.load(file_path, None)
        except Exception:
            return None

    # 兼容旧API
    def _load_auto_optimized(self, file_path: str, file_size_mb=None, file_ext: str = None,
                              target_size=None, progressive: bool = False):
        try:
            strategy = self.loading_strategies.get("auto") or self.loading_strategies.get("optimized")
            return strategy.load(file_path, target_size)
        except Exception:
            return None

    # 兼容旧API
    def _load_preview_optimized(self, file_path: str, target_size=None):
        try:
            strategy = self.loading_strategies.get("preview")
            return strategy.load(file_path, target_size)
        except Exception:
            return None

    # 兼容旧API
    def _load_progressive_optimized(self, file_path: str, target_size=None):
        try:
            # 渐进式已统一到 optimized/auto，这里委托 auto 策略
            strategy = self.loading_strategies.get("auto") or self.loading_strategies.get("optimized")
            return strategy.load(file_path, target_size)
        except Exception:
            return None

    def _select_loading_strategy(self, strategy_name: str, file_size_mb: float):
        """选择加载策略

        Args:
            strategy_name: 策略名称
            file_size_mb: 文件大小（MB）

        Returns:
            选中的加载策略
        """
        if strategy_name in self.loading_strategies:
            strategy = self.loading_strategies[strategy_name]
            # 检查策略是否可以处理该文件
            if strategy.can_handle("", file_size_mb):
                return strategy
            # 策略无法处理，回退到自动策略
            logger.debug(f"Strategy {strategy_name} cannot handle file size {file_size_mb}MB, falling back to auto")
            return self.loading_strategies["auto"]

        # 如果策略不存在，使用自动策略
        logger.warning(f"Unknown loading strategy: {strategy_name}, falling back to auto")
        return self.loading_strategies["auto"]

    def _execute_loading_strategy(self, strategy, file_path: str, target_size, file_size_mb: float):
        """执行加载策略

        Args:
            strategy: 加载策略
            file_path: 文件路径
            target_size: 目标尺寸
            file_size_mb: 文件大小（MB）

        Returns:
            加载的图像对象
        """
        try:
            # 检查策略是否可以处理该文件
            if not strategy.can_handle(file_path, file_size_mb, target_size):
                logger.warning(f"Strategy {strategy.name} cannot handle {file_path}")
                return None

            # 执行加载
            return strategy.load(file_path, target_size)

        except Exception as e:
            logger.error(f"Strategy {strategy.name} failed to load {file_path}: {e}")
            return None

    def _update_performance_stats(self, file_ext: str, processing_time: float):
        """更新性能统计信息

        Args:
            file_ext: 文件扩展名（兼容旧签名）
            processing_time: 处理时间
        """
        try:
            self.processing_stats["total_processing_time"] += processing_time

            # 旧签名不区分策略与成功与否，这里仅累计时间

        except Exception as e:
            logger.warning(f"Failed to update performance stats: {e}")

    def _init_dual_thread_processing(self):
        """初始化双线程处理机制"""
        global _dual_thread_start_logged

        with _dual_thread_log_lock:
            if not _dual_thread_start_logged:
                logger.info("Initializing dual-thread processing")
                _dual_thread_start_logged = True

    def get_processing_stats(self) -> dict:
        """获取处理统计信息

        Returns:
            dict: 包含各种处理统计的字典
        """
        stats = self.processing_stats.copy()

        # 添加策略统计
        strategy_stats = {}
        for name, strategy in self.loading_strategies.items():
            try:
                get_stats = getattr(strategy, "get_stats", None)
                strategy_stats[name] = get_stats() if callable(get_stats) else {}
            except Exception:
                strategy_stats[name] = {}

        stats["strategies"] = strategy_stats

        return stats

    def reset_stats(self):
        """重置统计信息"""
        self.processing_stats = {
            "quartz_processed": 0,
            "pil_fallback": 0,
            "fast_loaded": 0,
            "total_processing_time": 0.0,
            "quartz_avg_time": 0.0,
            "pil_avg_time": 0.0,
            "cache_hits": 0,
            "gpu_accelerated": 0,
        }

        # 重置策略统计
        for strategy in self.loading_strategies.values():
            strategy.stats = {
                "total_requests": 0,
                "successful_loads": 0,
                "failed_loads": 0,
                "total_time": 0.0,
                "avg_time": 0.0
            }

        # 重置旋转统计
        if hasattr(self, "rotation_processor"):
            self.rotation_processor.reset_rotation_stats()

    def rotate_image(self, image_path, direction="clockwise", callback=None):
        """旋转图像

        Args:
            image_path: 图像文件路径
            direction: 旋转方向 ("clockwise" 或 "counterclockwise")
            callback: 完成回调函数

        Returns:
            bool: 旋转是否成功
        """
        try:
            if not hasattr(self, "rotation_processor"):
                logger.error("旋转处理器未初始化")
                return False

            return self.rotation_processor.rotate_image(image_path, direction, callback)

        except Exception as e:
            logger.error(f"图像旋转失败 {image_path}: {e}")
            return False

    def get_rotation_stats(self):
        """获取旋转统计信息

        Returns:
            dict: 旋转统计信息
        """
        if hasattr(self, "rotation_processor"):
            return self.rotation_processor.get_rotation_stats()
        return {}
