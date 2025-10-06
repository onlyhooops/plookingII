"""
图像管理器

负责处理图像加载、缓存、处理策略和内存管理。
"""

import logging
import threading
import time

from ...config.constants import APP_NAME, IMAGE_PROCESSING_CONFIG
from ...config.manager import get_config, set_config
from ...core.image_processing import HybridImageProcessor
from ...core.simple_cache import AdvancedImageCache, BidirectionalCachePool

# 使用统一监控系统
from ...monitor import get_unified_monitor

logger = logging.getLogger(APP_NAME)


class ImageManager:
    """图像管理器，负责图像加载、缓存和处理策略"""

    def __init__(self, main_window):
        """初始化图像管理器

        Args:
            main_window: MainWindow实例
        """
        self.main_window = main_window

        # 统一监控器
        self.monitor = get_unified_monitor()
        self.slim_mode = get_config("feature.slim_mode", False)

        # 高级图像缓存
        self.image_cache = AdvancedImageCache()

        # 竖向图片缓存优化配置
        self._portrait_cache_config = {
            "compression_level": 0.8,  # 竖向图片使用更高压缩
            "memory_multiplier": 0.7,  # 竖向图片分配更少内存
            "priority_boost": 1.2,  # 竖向图片优先级略高（因为加载慢）
        }

        # 混合图像处理器
        self.hybrid_processor = HybridImageProcessor()
        self.image_processor = self.hybrid_processor
        # 注入处理器到缓存，避免缓存内部再次创建处理器导致重复策略初始化
        try:
            self.image_cache.image_processor = self.hybrid_processor
        except Exception:
            pass
        self.processing_mode = "auto"

        # 渐进式加载控制（已收敛为默认禁用，兼容旧逻辑保留开关）
        self.progressive_loading_enabled = not get_config("feature.disable_progressive_layer", True)
        self.current_progressive_task = None

        # 双向缓存池
        self.bidi_pool = BidirectionalCachePool(
            preload_count=5,
            keep_previous=3,
            image_processor=self.hybrid_processor,
            advanced_cache=self.image_cache,
        )

        # 内存监控线程
        self._memory_monitor_running = False

        # 双缓冲：下一张就绪缓冲与代次控制（用于取消过时任务）
        self._next_ready_image = None
        self._next_ready_path = None
        self._load_generation = 0
        self._decode_lock = threading.Lock()
        self._last_index = None
        self._nav_history = []  # [(timestamp, direction)] 最近导航事件
        self._last_sequence_sync = 0  # 上次序列同步时间

    def show_current_image(self):
        """显示当前图像"""
        if not self.main_window.images or self.main_window.current_index >= len(self.main_window.images):
            return

        image_path = self.main_window.images[self.main_window.current_index]

        # 设置当前图片路径到图像视图，支持右键菜单
        if hasattr(self.main_window, "image_view") and hasattr(self.main_window.image_view, "setCurrentImagePath_"):
            self.main_window.image_view.setCurrentImagePath_(image_path)

        # 设置图片更新监听
        if hasattr(self.main_window, "image_update_manager"):
            self.main_window.image_update_manager.set_current_image(image_path)

        # 导航代次递增，取消过时后台任务
        try:
            self._load_generation += 1
        except Exception:
            self._load_generation = 1

        # 记录导航方向与速度
        try:
            prev_idx = self._last_index
            cur_idx = self.main_window.current_index
            if prev_idx is not None and isinstance(prev_idx, int):
                direction = 1 if cur_idx > prev_idx else (-1 if cur_idx < prev_idx else 0)
            else:
                direction = 0
            self._update_navigation_stats(direction)
            self._last_index = cur_idx
        except Exception:
            self._last_index = self.main_window.current_index

        # 更新会话状态
        self._update_session_progress()

        self._show_image_common(image_path)

    def _update_session_progress(self):
        """更新会话进度"""
        try:
            if hasattr(self.main_window, "status_bar_controller") and (self.main_window.status_bar_controller):
                # 更新图片总数 - 保留基础会话跟踪
                if self.main_window.images:
                    self.main_window.status_bar_controller.session_manager.set_image_count(len(self.main_window.images))

                # 标记图片已浏览 - 保留基础会话跟踪
                self.main_window.status_bar_controller.session_manager.image_viewed()

        except Exception:
            logger.exception("更新会话进度时发生错误")

    def _show_image_common(self, image_path: str):
        """通用图像显示方法

        Args:
            image_path: 图像文件路径
        """
        # 检查是否正在关闭应用
        if getattr(self.main_window, "_shutting_down", False):
            return

        # 执行图像显示流程
        self._execute_image_display_flow(image_path)

    def _execute_image_display_flow(self, image_path: str):
        """执行图像显示流程（重构版：消除重复，提升可读性）

        Args:
            image_path: 图像文件路径
        """
        # 1. 更新状态栏和通知
        self._update_status_and_notices()
        t_start = time.time()

        # 2. 通知双向缓存池并计算目标尺寸
        self._notify_bidirectional_cache(image_path)
        target_size = self._calculate_target_size()

        # 3. 尝试快速显示路径（Early Return）
        display_method = None
        if self._try_display_next_ready(image_path):
            display_method = "next_ready"
        elif self._try_display_cached_image(image_path, target_size):
            display_method = "cache_hit"
            self._record_cache_hit()

        if display_method:
            self._post_display_tasks(image_path, target_size, t_start, display_method)
            return

        # 4. 缓存未命中，执行加载策略
        self._execute_loading_with_strategy(image_path, target_size)
        self._post_display_tasks(image_path, target_size, t_start, "background_or_progressive")

    def _update_status_and_notices(self):
        """更新状态栏并显示一次性通知"""
        self.main_window._update_status_display_immediate()

        # 展示来自策略层的一次性提示（解码失败/回退）
        try:
            notice_fail = get_config("_notice.decode_failure", None)
            notice_fb = get_config("_notice.decode_fallback", None)

            if (
                notice_fail
                and hasattr(self.main_window, "status_bar_controller")
                and self.main_window.status_bar_controller
            ):
                self.main_window.status_bar_controller.set_status_message(str(notice_fail))
                set_config("_notice.decode_failure", None)
            elif (
                notice_fb
                and hasattr(self.main_window, "status_bar_controller")
                and self.main_window.status_bar_controller
            ):
                self.main_window.status_bar_controller.set_status_message(str(notice_fb))
                set_config("_notice.decode_fallback", None)
        except Exception:
            pass

    def _calculate_target_size(self):
        """计算视图目标尺寸

        Returns:
            tuple or None: 目标尺寸(width, height)，全分辨率时返回None
        """
        if get_config("feature.full_res_browse", True):
            return None
        return self._get_dynamic_target_size()

    def _record_cache_hit(self):
        """记录缓存命中"""
        try:
            self.monitor.record_operation("cache_hit", 0, cache_hit=True)
        except Exception:
            pass

    def _post_display_tasks(self, image_path: str, target_size, t_start: float, method: str):
        """图像显示后的后台任务

        Args:
            image_path: 图像文件路径
            target_size: 目标尺寸
            t_start: 开始时间
            method: 显示方法
        """
        # 后台任务
        self._schedule_background_tasks()
        self._prepare_next_image_async(image_path, target_size)

        # 非精简模式：执行扩展预取
        if not self.slim_mode:
            self._cancel_stale_prefetches()
            self._schedule_adaptive_prefetch(image_path, target_size)
            self._ensure_hot3_residency(image_path, target_size)

        # 记录性能
        try:
            self.monitor.record_operation(
                "load_image",
                max(0.0, time.time() - t_start) * 1000,  # 转换为毫秒
                method=method,
                success=True,
            )
        except Exception:
            pass

    def _execute_loading_with_strategy(self, image_path: str, target_size):
        """使用策略执行加载

        Args:
            image_path: 图像文件路径
            target_size: 目标尺寸
        """
        if self.slim_mode:
            # 精简模式：直接执行加载策略
            self._execute_loading_strategy(image_path, target_size)
        else:
            # 完整模式：尝试两阶段加载
            if not self._maybe_two_stage_for_ultra(image_path, target_size):
                self._execute_loading_strategy(image_path, target_size)
            self._schedule_background_tasks()

    def _notify_bidirectional_cache(self, image_path: str):
        """通知双向缓存池当前图片

        Args:
            image_path: 图像文件路径
        """
        try:
            self.bidi_pool.set_current_image_sync(image_path, image_path)
        except Exception as e:
            logger.debug(f"bidi_pool.set_current_image_sync failed: {e}")

    def _try_display_cached_image(self, image_path: str, target_size: tuple) -> bool:
        """尝试显示缓存的图像

        Args:
            image_path: 图像文件路径
            target_size: 目标尺寸

        Returns:
            bool: 是否成功显示缓存的图像
        """
        try:
            cached_image = self.image_cache.get(image_path, target_size=target_size)
        except Exception as e:
            cached_image = None
            logger.debug(f"image_cache.get failed: {e}")

        if cached_image:
            # 缓存命中，立即显示
            self._display_image_immediate(cached_image)
            self._schedule_background_tasks()
            return True

        return False

    def _execute_loading_strategy(self, image_path: str, target_size: tuple):
        """执行加载策略

        Args:
            image_path: 图像文件路径
            target_size: 目标尺寸
        """
        # 获取文件大小以决定加载策略
        file_size_mb = self._get_file_size_safely(image_path)

        # 智能加载策略选择：根据文件大小选择最优加载方式
        if self._should_use_fast_loading(file_size_mb):
            self._execute_fast_loading(image_path)
            return

        # 大文件：渐进式路径已默认禁用，保留兼容开关
        if self._should_use_progressive(file_size_mb):
            self._load_and_display_progressive(image_path, target_size)
            self._schedule_background_tasks()
            return

        # 默认策略：后台异步加载，避免阻塞UI
        self._start_background_load(image_path, target_size)
        self._schedule_background_tasks()

    def _get_file_size_safely(self, image_path: str) -> float:
        """安全地获取文件大小

        Args:
            image_path: 图像文件路径

        Returns:
            float: 文件大小（MB），失败时返回0
        """
        try:
            return self.image_cache.get_file_size_mb(image_path)
        except Exception as e:
            logger.debug(f"get_file_size_mb failed, fallback to 0: {e}")
            return 0

    def _should_use_fast_loading(self, file_size_mb: float) -> bool:
        """判断是否应该使用快速加载

        Args:
            file_size_mb: 文件大小（MB）

        Returns:
            bool: 是否应该使用快速加载
        """
        fast_threshold = IMAGE_PROCESSING_CONFIG.get("fast_load_threshold", 50)
        return file_size_mb <= fast_threshold and IMAGE_PROCESSING_CONFIG.get("fast_load_enabled", True)

    def _execute_fast_loading(self, image_path: str):
        """执行快速加载

        Args:
            image_path: 图像文件路径
        """
        try:
            image = self._load_image_optimized(image_path, target_size=None)
            if image:
                self._display_image_immediate(image)
                self._schedule_background_tasks()
                # 快速显示后预热下一张（传递图像路径用于自适应优化）
                target_size = self._get_target_size_for_view(scale_factor=2, image_path=image_path)
                self._prepare_next_image_async(image_path, target_size)
                self._cancel_stale_prefetches()
                self._schedule_adaptive_prefetch(image_path, target_size)
                self._ensure_hot3_residency(image_path, target_size)
        except Exception as e:
            logger.debug(f"Fast sync load failed, fallback to background: {e}")
            # 快速加载失败，回退到后台加载（传递图像路径用于自适应优化）
            target_size = self._get_target_size_for_view(scale_factor=2, image_path=image_path)
            self._start_background_load(image_path, target_size)
            self._schedule_background_tasks()

    def _get_target_size_for_view(self, scale_factor=2, image_path=None):
        """获取视图的目标尺寸（支持横向竖向自适应优化）

        Args:
            scale_factor: 基础缩放因子
            image_path: 图像路径，用于横纵比检测优化

        Returns:
            tuple: (width, height) 目标尺寸
        """
        try:
            view_frame = self.main_window.image_view.frame()
            view_w = view_frame.size.width
            view_h = view_frame.size.height

            # 自适应缩放因子：竖向图片使用更保守的缩放
            adaptive_scale = scale_factor

            if image_path:
                try:
                    # 检测图像是否为竖向
                    if self._is_portrait_image(image_path):
                        # 竖向图片降低缩放因子，减少解码负载
                        adaptive_scale = max(1.2, scale_factor * 0.75)
                        logger.debug(f"竖向图片优化：缩放因子 {scale_factor} -> {adaptive_scale}")
                except Exception:
                    pass

            return (int(view_w * adaptive_scale), int(view_h * adaptive_scale))

        except Exception:
            logger.debug("_get_target_size_for_view fallback", exc_info=True)
            return (
                IMAGE_PROCESSING_CONFIG["max_preview_resolution"],
                IMAGE_PROCESSING_CONFIG["max_preview_resolution"],
            )

    def _get_dynamic_target_size(self):
        """根据当前视图尺寸与缩放比动态确定目标尺寸"""
        try:
            zoom = 1.0
            if hasattr(self.main_window, "image_view") and self.main_window.image_view:
                zoom = getattr(self.main_window.image_view, "zoom_scale", 1.0) or 1.0
            base_w, base_h = self._get_target_size_for_view(scale_factor=1)
            if zoom <= 1.0:
                return (base_w, base_h)
            max_os = 1.5
            eff = min(max(1.0, float(zoom)), max_os)
            return (int(base_w * eff), int(base_h * eff))
        except Exception:
            return self._get_target_size_for_view(scale_factor=1)

    def _is_portrait_image(self, image_path):
        """检测图像是否为竖向（高度>宽度）

        Args:
            image_path: 图像文件路径

        Returns:
            bool: True表示竖向图片，False表示横向或方形
        """
        try:
            # 优先使用缓存的图像尺寸信息
            if hasattr(self, "_image_dimensions_cache"):
                if image_path in self._image_dimensions_cache:
                    w, h = self._image_dimensions_cache[image_path]
                    return h > w

            # 快速检测：使用Quartz获取图像尺寸（不解码完整图像）
            try:
                from Foundation import NSURL
                from Quartz import CGImageSourceCopyPropertiesAtIndex, CGImageSourceCreateWithURL

                url = NSURL.fileURLWithPath_(image_path)
                source = CGImageSourceCreateWithURL(url, None)
                if source:
                    properties = CGImageSourceCopyPropertiesAtIndex(source, 0, None)
                    if properties:
                        width = properties.get("PixelWidth", 0)
                        height = properties.get("PixelHeight", 0)

                        # 缓存尺寸信息
                        if not hasattr(self, "_image_dimensions_cache"):
                            self._image_dimensions_cache = {}
                        self._image_dimensions_cache[image_path] = (width, height)

                        return height > width
            except Exception:
                pass

            # 回退：基于文件名推测（不够准确但快速）
            # 这是最后的回退方案，实际使用中应该很少触发
            return False

        except Exception:
            return False

    def _should_use_progressive(self, file_size_mb: float) -> bool:
        """判断是否应该使用渐进式加载

        Args:
            file_size_mb: 文件大小（MB）

        Returns:
            bool: 是否使用渐进式加载
        """
        try:
            threshold = IMAGE_PROCESSING_CONFIG.get("progressive_load_threshold")
            return bool(self.progressive_loading_enabled and file_size_mb >= threshold)
        except Exception as e:
            logger.debug(f"_should_use_progressive failed: {e}")
            return False

    def _display_image_immediate(self, image):
        """立即在图片视图中显示图片

        Args:
            image: 图像对象
        """
        # 通过图像视图控制器显示图像
        if hasattr(self.main_window, "image_view_controller"):
            self.main_window.image_view_controller.display_image(image)
        # 回退到直接设置图像
        elif hasattr(self.main_window, "image_view"):
            self.main_window.image_view.setImage_(image)
            self.main_window.image_view.setNeedsDisplay_(True)

    def _start_background_load(self, image_path, target_size):
        """启动后台图像加载

        Args:
            image_path: 图像文件路径
            target_size: 目标尺寸
        """

        def background_load():
            try:
                image = self._load_image_with_concurrency(image_path, target_size)
                if image:
                    self._post_to_main(lambda: self._display_image_immediate(image))
                else:
                    self._post_to_main(lambda: self.main_window.image_view.setImage_(None))
            except Exception:
                logger.exception("background_load failed for %s", image_path)

        threading.Thread(target=background_load, daemon=True).start()

    def _load_image_with_concurrency(self, image_path: str, target_size):
        try:
            # 并发控制
            if not hasattr(self, "_decode_semaphore"):
                self._decode_semaphore = threading.BoundedSemaphore(value=2)
            with self._decode_semaphore:
                return self._load_image_optimized(image_path, target_size=target_size)
        except Exception:
            logger.exception("_load_image_with_concurrency failed for %s", image_path)
            return None

    def _try_display_next_ready(self, image_path: str) -> bool:
        """若 next-ready 缓冲与当前路径匹配，则瞬时显示并清空缓冲"""
        try:
            with self._decode_lock:
                if self._next_ready_path == image_path and self._next_ready_image is not None:
                    image = self._next_ready_image
                    self._next_ready_image = None
                    self._next_ready_path = None
            if "image" in locals() and image is not None:
                self._display_image_immediate(image)
                return True
        except Exception:
            logger.debug("_try_display_next_ready failed", exc_info=True)
        return False

    def _prepare_next_image_async(self, current_path: str, target_size: tuple):
        """后台准备下一张图片并写入 next-ready 缓冲（可取消）

        改进：
        - 根据最近导航方向选择相邻方向（左/右）
        - 预取解码优先使用视图级目标尺寸，避免在全分辨率模式下预取过大图片
        """
        try:
            # 推断最近一次非零方向（默认向右）
            direction = +1
            try:
                for _, d in reversed(self._nav_history):
                    if d != 0:
                        direction = 1 if d > 0 else -1
                        break
            except Exception:
                pass

            next_path = self._get_adjacent_path(current_path, direction=direction)
            if not next_path:
                return

            gen = self._load_generation

            def worker(path: str, expected_gen: int):
                try:
                    # 若代次已变化，则取消
                    if expected_gen != self._load_generation:
                        return
                    # 使用更安全的预取尺寸：当目标尺寸为None（全分辨率）时，改用视图级动态尺寸
                    prefetch_target = target_size if target_size else self._get_dynamic_target_size()
                    img = self._load_image_optimized(path, target_size=prefetch_target)
                    if img is None:
                        return
                    # 写入缓冲（仍需检查代次）
                    with self._decode_lock:
                        if expected_gen != self._load_generation:
                            return
                        self._next_ready_image = img
                        self._next_ready_path = path
                except Exception:
                    logger.debug("_prepare_next_image_async worker failed", exc_info=True)

            threading.Thread(target=worker, args=(next_path, gen), daemon=True).start()
        except Exception:
            logger.debug("_prepare_next_image_async failed", exc_info=True)

    def _get_adjacent_path(self, current_path: str, direction: int = +1) -> str:
        """获取相邻图片路径（direction=+1 下一张，-1 上一张）"""
        try:
            if not self.main_window.images:
                return None
            try:
                idx = self.main_window.images.index(current_path)
            except ValueError:
                return None
            nxt = idx + (1 if direction >= 0 else -1)
            if 0 <= nxt < len(self.main_window.images):
                return self.main_window.images[nxt]
            return None
        except Exception:
            return None

    # —— 自适应预取 ——
    def _update_navigation_stats(self, direction: int) -> None:
        try:
            now = time.time()
            self._nav_history.append((now, direction))
            # 只保留最近 8 条
            if len(self._nav_history) > 8:
                self._nav_history = self._nav_history[-8:]
        except Exception:
            pass

    def _compute_prefetch_window(self, current_image_path=None) -> int:
        """计算预取窗口大小（支持竖向图片优化）

        Args:
            current_image_path: 当前图像路径，用于检测是否为竖向图片

        Returns:
            int: 预取窗口大小
        """
        try:
            if not self._nav_history:
                return 1
            # 统计最近导航的速度（时间间隔）与一致方向性
            timestamps = [t for (t, d) in self._nav_history]
            dirs = [d for (t, d) in self._nav_history if d != 0]
            if len(timestamps) >= 2:
                dt = max(0.01, timestamps[-1] - timestamps[-2])
            else:
                dt = 0.5
            same_dir_ratio = 0.0
            if dirs:
                last_dir = dirs[-1]
                same_dir_ratio = sum(1 for d in dirs if d == last_dir) / float(len(dirs))

            # 简单的启发式：更快的切换（dt小）和更一致的方向 → 更大窗口
            window = 1
            if (dt < 0.25 and same_dir_ratio > 0.6) or (dt < 0.5 and same_dir_ratio > 0.5):
                window = 2

            # 竖向图片优化：减少预取窗口，优先保证当前图片流畅性
            if current_image_path and self._is_portrait_image(current_image_path):
                window = max(1, int(window * 0.7))  # 竖向图片预取窗口减小30%
                logger.debug(f"竖向图片预取优化：窗口大小 {window}")

            # 受内存与系统策略影响，可进一步收缩（与现有水位策略协同，此处先保守返回）
            return window
        except Exception:
            return 1

    def _schedule_adaptive_prefetch(self, current_path: str, target_size: tuple) -> None:
        try:
            window = self._compute_prefetch_window(current_path)
            # 推断方向（使用最近一次非零方向），默认向前
            direction = 1
            for _, d in reversed(self._nav_history):
                if d != 0:
                    direction = 1 if d > 0 else -1
                    break

            # 生成预取候选：next1 优先，其次 next2；若方向明确，再加 prev1
            candidates = []
            if window >= 1:
                p1 = self._get_path_by_offset(current_path, +1 if direction >= 0 else -1)
                if p1:
                    candidates.append((p1, 1))
            if window >= 2:
                p2 = self._get_path_by_offset(current_path, +2 if direction >= 0 else -2)
                if p2:
                    candidates.append((p2, 2))
            # 反向提升仅限最近1张
            opp = self._get_path_by_offset(current_path, -1 if direction >= 0 else +1)
            if opp:
                candidates.append((opp, 2))

            gen = self._load_generation

            for path, priority in candidates:
                threading.Thread(
                    target=self._prefetch_worker, args=(path, target_size, gen, priority), daemon=True
                ).start()
        except Exception:
            logger.debug("_schedule_adaptive_prefetch failed", exc_info=True)

    def _prefetch_worker(self, path: str, target_size: tuple, expected_gen: int, priority: int) -> None:
        try:
            # 开始前检查是否仍是最新一代
            if expected_gen != self._load_generation:
                return
            # 先检查缓存避免重复工作
            if self.image_cache.get(path, target_size=target_size):
                return
            img = self._load_image_with_concurrency(path, target_size)
            if img is None:
                return
            # 放入预加载缓存层
            if expected_gen != self._load_generation:
                return
            try:
                self.image_cache.put_new(path, img, layer="preload")
            except Exception:
                pass
        except Exception:
            logger.debug("_prefetch_worker failed", exc_info=True)

    def _cancel_stale_prefetches(self) -> None:
        # 基于代次的软取消，线程会在开始/结束前检查 expected_gen
        # 此处仅提升代次已在 show_current_image 中完成
        pass

    def _get_path_by_offset(self, current_path: str, offset: int) -> str:
        try:
            if not self.main_window.images:
                return None
            try:
                idx = self.main_window.images.index(current_path)
            except ValueError:
                return None
            tgt = idx + offset
            if 0 <= tgt < len(self.main_window.images):
                return self.main_window.images[tgt]
            return None
        except Exception:
            return None

    def _load_and_display_progressive(self, image_path, target_size):
        """渐进式加载和显示大图片

        Args:
            image_path: 图像文件路径
            target_size: 目标尺寸
        """
        if getattr(self.main_window, "_shutting_down", False):
            return

        def progressive_load_worker():
            try:
                local_target_size = self._resolve_progressive_target_size(target_size)
                preview_size = (max(1, local_target_size[0] // 4), max(1, local_target_size[1] // 4))

                # 第一阶段：快速加载低质量预览
                preview_image = self._load_image_optimized(image_path, prefer_preview=True, target_size=preview_size)
                if preview_image:
                    self._post_to_main(lambda: self._display_image_immediate(preview_image))

                    # 第二阶段：延迟加载完整质量图片
                    time.sleep(0.1)
                    full_image = self._load_image_optimized(image_path, target_size=local_target_size)
                    if full_image:
                        self._post_to_main(lambda: self._display_image_immediate(full_image))
            except Exception:
                logger.exception("Progressive load failed for %s", image_path)

        progressive_thread = threading.Thread(target=progressive_load_worker, daemon=True)
        progressive_thread.start()
        self.current_progressive_task = progressive_thread

    def _maybe_two_stage_for_ultra(self, image_path: str, target_size: tuple) -> bool:
        """根据文件大小阈值决定是否采用两阶段显示（预览→全清晰度）"""
        try:
            ultra_mb = IMAGE_PROCESSING_CONFIG.get("ultra_image_threshold_mb", 120)
            file_size_mb = self._get_file_size_safely(image_path)
            if file_size_mb >= float(ultra_mb):
                self._load_and_display_progressive(image_path, target_size)
                return True
        except Exception:
            pass
        return False

    def _resolve_progressive_target_size(self, target_size):
        """解析渐进式加载的目标尺寸

        Args:
            target_size: 原始目标尺寸

        Returns:
            tuple: 解析后的有效目标尺寸
        """
        if target_size is None or target_size[0] <= 0 or target_size[1] <= 0:
            try:
                vf = self.main_window.image_view.frame()
                target_w = max(1, int(vf.size.width))
                target_h = max(1, int(vf.size.height))
                return (target_w, target_h)
            except Exception:
                return (
                    IMAGE_PROCESSING_CONFIG["max_preview_resolution"],
                    IMAGE_PROCESSING_CONFIG["max_preview_resolution"],
                )
        return target_size

    def _load_image_optimized(self, img_path, prefer_preview=False, target_size=None):
        """优化的图像加载方法（支持竖向图片专门优化）

        Args:
            img_path: 图像文件路径
            prefer_preview: 是否偏好预览模式
            target_size: 目标尺寸

        Returns:
            图像对象或None
        """
        try:
            # 检测是否为竖向图片，应用专门策略
            is_portrait = self._is_portrait_image(img_path)

            # 为竖向图片调整目标尺寸，减少内存占用
            adjusted_target_size = target_size
            if is_portrait and target_size:
                multiplier = self._portrait_cache_config["memory_multiplier"]
                adjusted_target_size = (int(target_size[0] * multiplier), int(target_size[1] * multiplier))
                logger.debug(f"竖向图片目标尺寸优化: {target_size} -> {adjusted_target_size}")

            file_size_mb = self.image_cache.get_file_size_mb(img_path)
            strategy, eff_target = self._select_load_strategy(file_size_mb, prefer_preview, adjusted_target_size)
            if strategy == "fast" and self.image_processor:
                return self.image_processor.load_image_optimized(img_path, strategy="fast")
            return self.image_cache.load_image_with_strategy(img_path, strategy, eff_target)
        except Exception:
            logger.exception("_load_image_optimized failed for %s", img_path)
            return None

    def _select_load_strategy(self, file_size_mb: float, prefer_preview: bool, target_size):
        """根据文件大小和偏好选择最优加载策略

        Args:
            file_size_mb: 文件大小（MB）
            prefer_preview: 是否偏好预览模式
            target_size: 目标加载尺寸

        Returns:
            tuple: (策略标识, 有效目标尺寸)
        """
        fast_enabled = IMAGE_PROCESSING_CONFIG.get("fast_load_enabled", True)
        fast_threshold = IMAGE_PROCESSING_CONFIG.get("fast_load_threshold", 50)
        progressive_threshold = IMAGE_PROCESSING_CONFIG.get("progressive_load_threshold")

        # 策略1：快速加载（小文件，≤50MB）
        if fast_enabled and file_size_mb <= fast_threshold:
            return "fast", None

        # 策略2：渐进式加载（已收敛，默认禁用；仅在开关允许时启用）
        if (not get_config("feature.disable_progressive_layer", True)) and file_size_mb >= progressive_threshold:
            return "progressive", target_size

        # 策略3：预览模式（中等文件且偏好预览）
        if prefer_preview and file_size_mb > fast_threshold:
            if not target_size:
                target_size = (
                    IMAGE_PROCESSING_CONFIG["max_preview_resolution"],
                    IMAGE_PROCESSING_CONFIG["max_preview_resolution"],
                )
            return "preview", target_size

        # 策略4：自动模式（默认策略）
        return "auto", target_size

    def _post_to_main(self, func):
        """将函数调度到主线程执行

        Args:
            func: 需要在主线程执行的函数
        """
        try:
            if getattr(self.main_window, "_shutting_down", False):
                return
            # 使用 NSOperationQueue 主队列派发，避免在后台线程调用 AppKit API
            from Foundation import NSOperationQueue

            NSOperationQueue.mainQueue().addOperationWithBlock_(func)
        except Exception:
            try:
                # 兜底：若无法获取主队列，直接调用（可能已在主线程）
                func()
            except Exception:
                logger.debug("_post_to_main failed", exc_info=True)

    def _ensure_hot3_residency(self, current_path: str, target_size: tuple) -> None:
        """确保 当前/上一张/下一张 常驻（尽力而为，受内存水位制约）"""
        try:
            neighbors = [current_path]
            prev_path = self._get_adjacent_path(current_path, -1)
            next_path = self._get_adjacent_path(current_path, +1)
            if prev_path:
                neighbors.append(prev_path)
            if next_path:
                neighbors.append(next_path)

            gen = self._load_generation

            def promote(path: str, expected_gen: int):
                try:
                    if expected_gen != self._load_generation:
                        return
                    # 已在主缓存则跳过
                    cached = self.image_cache.get(path)
                    if cached:
                        return
                    img = self._load_image_with_concurrency(path, None)
                    if img is None:
                        return
                    if expected_gen != self._load_generation:
                        return
                    # 放入主缓存层
                    try:
                        self.image_cache.put_new(path, img, layer="main")
                    except Exception:
                        pass
                except Exception:
                    logger.debug("promote hot3 failed", exc_info=True)

            for p in neighbors:
                threading.Thread(target=promote, args=(p, gen), daemon=True).start()
        except Exception:
            logger.debug("_ensure_hot3_residency failed", exc_info=True)

    def _schedule_background_tasks(self):
        """调度后台任务执行"""
        if getattr(self.main_window, "_shutting_down", False):
            return

        def background_worker():
            try:
                time.sleep(0.2)
                self._check_memory_usage()
                time.sleep(0.3)
                self.main_window._save_task_progress()
            except Exception:
                logger.exception("background_worker failed")

        bg_thread = threading.Thread(target=background_worker, daemon=True)
        bg_thread.start()

    def _check_memory_usage(self):
        """检查内存使用情况"""
        memory_status = self.monitor.get_memory_status()
        memory_info = {
            "available_mb": memory_status.available_mb,
            "used_mb": memory_status.used_mb,
        }
        cache_stats = self.image_cache.get_stats()

        # 从各层缓存统计中获取内存使用量
        total_cache_memory = 0
        if "layers" in cache_stats:
            for layer_stats in cache_stats["layers"].values():
                if "memory_mb" in layer_stats:
                    total_cache_memory += layer_stats["memory_mb"]

        # 记录内存使用情况
        logger.debug(
            f"Memory usage - Available: {memory_info.get('available_mb', 0):.1f}MB, Cache: {total_cache_memory:.1f}MB"
        )

        # 获取可用内存
        available_mb = memory_info.get("available_mb", 0)

        # 如果缓存内存使用过高，触发清理
        if total_cache_memory > 3000:  # 3GB阈值，适配4GB总预算
            logger.info("High cache memory usage, triggering cleanup")
            self.image_cache.trim_to_budget()

        # 统一的缓存收缩
        self._trim_preload_if_needed()
        self._trim_main_caches_if_needed()

        # 层级策略
        if available_mb < 500:  # 提升到500MB
            self._emergency_memory_cleanup()
        elif available_mb < 1000:  # 提升到1000MB
            self._aggressive_memory_cleanup()
        elif memory_status.pressure_level in ("high", "critical") or total_cache_memory > 400:  # 提升到400MB
            self._moderate_memory_cleanup()
        elif total_cache_memory > 300:  # 提升到300MB
            self._preventive_memory_cleanup()

        self._start_background_memory_monitor()

    def _emergency_memory_cleanup(self):
        """紧急内存清理"""
        self.image_cache.preview_cache.clear()
        self.image_cache.preview_memory_mb = 0
        try:
            if hasattr(self.image_cache, "preload_cache") and self.image_cache.preload_cache is not None:
                self.image_cache.preload_cache.clear()
            if hasattr(self.image_cache, "preload_memory_mb"):
                self.image_cache.preload_memory_mb = 0
        except Exception:
            pass

        current_path = (
            self.main_window.images[self.main_window.current_index]
            if self.main_window.images and (0 <= self.main_window.current_index < len(self.main_window.images))
            else None
        )
        current_img = None
        if current_path:
            current_img = self.image_cache.get(current_path)

        self.image_cache.clear()
        self.image_cache.estimated_memory_mb = 0

        if current_path and current_img:
            try:
                self.image_cache.put_new(current_path, current_img, layer="main")
            except Exception:
                pass

        # 强制垃圾回收
        import gc

        gc.collect()

    def _aggressive_memory_cleanup(self):
        """激进内存清理"""
        self.image_cache.preview_cache.clear()
        self.image_cache.preview_memory_mb = 0

        preload_size = (
            len(self.image_cache.preload_cache) if getattr(self.image_cache, "preload_cache", None) is not None else 0
        )
        if preload_size > 2:
            items_to_remove = preload_size - 2
            for _ in range(items_to_remove):
                try:
                    if (
                        getattr(self.image_cache, "preload_cache", None) is not None
                        and len(self.image_cache.preload_cache) > 2
                    ):
                        self.image_cache._evict_oldest_preload()
                except Exception:
                    break
        # 预加载内存使用更新已移除（统一监控自动管理）

        cache_size = self.image_cache.get_size()
        if cache_size > 3:
            items_to_remove = cache_size - 3
            for _ in range(items_to_remove):
                if self.image_cache.get_size() > 3:
                    self.image_cache._evict_oldest()

        # 强制垃圾回收
        import gc

        gc.collect()

    def _moderate_memory_cleanup(self):
        """适度内存清理"""
        preview_size = len(self.image_cache.preview_cache)
        if preview_size > 2:
            items_to_remove = preview_size // 2
            for _ in range(items_to_remove):
                if self.image_cache.preview_cache:
                    self.image_cache._evict_oldest_preview()

        preload_size = (
            len(self.image_cache.preload_cache) if getattr(self.image_cache, "preload_cache", None) is not None else 0
        )
        if preload_size > 4:
            items_to_remove = preload_size - 4
            for _ in range(items_to_remove):
                try:
                    if (
                        getattr(self.image_cache, "preload_cache", None) is not None
                        and len(self.image_cache.preload_cache) > 4
                    ):
                        self.image_cache._evict_oldest_preload()
                except Exception:
                    break
        # 预加载内存使用更新已移除（统一监控自动管理）

        cache_size = self.image_cache.get_size()
        if cache_size > 5:
            items_to_remove = cache_size - 5
            for _ in range(items_to_remove):
                if self.image_cache.get_size() > 5:
                    self.image_cache._evict_oldest()

    def _preventive_memory_cleanup(self):
        """预防性内存清理"""
        preview_size = len(self.image_cache.preview_cache)
        if preview_size > 5:
            items_to_remove = preview_size - 5
            for _ in range(items_to_remove):
                if self.image_cache.preview_cache:
                    self.image_cache._evict_oldest_preview()

        preload_size = (
            len(self.image_cache.preload_cache) if getattr(self.image_cache, "preload_cache", None) is not None else 0
        )
        if preload_size > 6:
            items_to_remove = preload_size - 6
            for _ in range(items_to_remove):
                try:
                    if (
                        getattr(self.image_cache, "preload_cache", None) is not None
                        and len(self.image_cache.preload_cache) > 6
                    ):
                        self.image_cache._evict_oldest_preload()
                except Exception:
                    break
        # 预加载内存使用更新已移除（统一监控自动管理）

        cache_size = self.image_cache.get_size()
        if cache_size > 8:
            items_to_remove = cache_size - 8
            for _ in range(items_to_remove):
                if self.image_cache.get_size() > 8:
                    self.image_cache._evict_oldest()

    def _trim_preload_if_needed(self):
        """根据需要修剪预加载缓存"""
        memory_status = self.monitor.get_memory_status()
        if memory_status.pressure_level in ("high", "critical"):
            preload_size = (
                len(self.image_cache.preload_cache)
                if getattr(self.image_cache, "preload_cache", None) is not None
                else 0
            )
            if preload_size > 3:
                items_to_remove = preload_size - 3
                for _ in range(items_to_remove):
                    try:
                        if (
                            getattr(self.image_cache, "preload_cache", None) is not None
                            and len(self.image_cache.preload_cache) > 3
                        ):
                            self.image_cache._evict_oldest_preload()
                    except Exception:
                        break
                if hasattr(self.memory_monitor, "update_preload_memory_usage"):
                    self.memory_monitor.update_preload_memory_usage(getattr(self.image_cache, "preload_memory_mb", 0))

    def _trim_main_caches_if_needed(self):
        """根据需要修剪主缓存"""
        memory_status = self.monitor.get_memory_status()
        if memory_status.pressure_level in ("high", "critical"):
            preview_size = len(self.image_cache.preview_cache)
            if preview_size > 3:
                items_to_remove = preview_size - 3
                for _ in range(items_to_remove):
                    if self.image_cache.preview_cache:
                        self.image_cache._evict_oldest_preview()
            cache_size = self.image_cache.get_size()
            if cache_size > 5:
                items_to_remove = cache_size - 5
                for _ in range(items_to_remove):
                    if self.image_cache.get_size() > 5:
                        self.image_cache._evict_oldest()

    def _start_background_memory_monitor(self):
        """启动后台内存监控线程"""
        if getattr(self.main_window, "_shutting_down", False):
            return
        if self._memory_monitor_running:
            return

        def _monitor_once():
            self._trim_preload_if_needed()
            self._trim_main_caches_if_needed()
            self._apply_background_policy()

        def memory_monitor_worker():
            self._memory_monitor_running = True
            try:
                while self._memory_monitor_running:
                    time.sleep(10)
                    if not self._memory_monitor_running:
                        break
                    _monitor_once()
            except Exception:
                pass
            finally:
                self._memory_monitor_running = False

        self._memory_monitor_running = True
        threading.Thread(target=memory_monitor_worker, daemon=True).start()

    def _apply_background_policy(self):
        """应用后台策略"""
        memory_status = self.monitor.get_memory_status()
        if memory_status.available_mb < 800:  # 提升到800MB，适配4GB内存预算
            self._moderate_memory_cleanup()

        # 根据性能评分与建议进行轻量自适应调参（非破坏性）
        try:
            stats = self.monitor.get_stats()
            if stats["total_operations"] > 0:
                score = stats.get("success_rate", 1.0)
                suggestions = []
                tuning = (
                    suggestions[-1]["tuning"]
                    if suggestions and isinstance(suggestions[-1], dict) and "tuning" in suggestions[-1]
                    else {}
                )

                # 统一的tier与回拨逻辑
                # 默认：并发2，预取5；差时降级，优时回拨
                desired_conc = tuning.get("suggested_decode_concurrency", 2)
                desired_preload = tuning.get("suggested_preload_window", 5)
                if score >= 85:
                    desired_conc = 2
                    desired_preload = 5
                elif score < 70:
                    desired_conc = 1
                    desired_preload = max(2, min(desired_preload, 4))

                # 应用并发
                if desired_conc in (1, 2):
                    if (
                        not hasattr(self, "_decode_semaphore")
                        or getattr(self._decode_semaphore, "_value", None) != desired_conc
                    ):
                        self._decode_semaphore = threading.BoundedSemaphore(value=desired_conc)

                # 应用预取窗口
                if hasattr(self, "bidi_pool") and self.bidi_pool:
                    if isinstance(desired_preload, int) and 1 <= desired_preload <= 8:
                        try:
                            self.bidi_pool.set_preload_window(preload_count=desired_preload)
                        except Exception:
                            pass
        except Exception:
            pass

    def sync_bidi_sequence(self, images):
        """同步双向缓存池序列（优化版本）

        Args:
            images: 图像列表
        """
        try:
            # 清空旧序列
            self.bidi_pool.clear()

            # 设置新序列
            self.bidi_pool.set_sequence(images)

            # 记录同步时间，用于后续预加载优化
            self._last_sequence_sync = time.time()

            logger.debug(f"双向缓存池已同步，图像数量: {len(images)}")

            # 立即触发预加载重建，确保后续导航流畅
            self._trigger_immediate_preload_rebuild()

        except Exception as e:
            logger.warning(f"同步双向缓存池失败: {e}")

    def _trigger_immediate_preload_rebuild(self):
        """立即触发预加载重建

        在序列同步后立即重建预加载缓存，确保后续导航的流畅性。
        """
        try:
            if not self.main_window.images or self.main_window.current_index >= len(self.main_window.images):
                return

            current_path = self.main_window.images[self.main_window.current_index]

            # 使用小延迟避免与当前图像显示冲突
            def delayed_preload_rebuild():
                try:
                    # 获取视图尺寸用于预加载
                    if hasattr(self.main_window, "image_view"):
                        view_frame = self.main_window.image_view.frame()
                        target_size = (int(view_frame.size.width), int(view_frame.size.height))
                    else:
                        target_size = (1200, 800)  # 默认尺寸

                    # 启动预加载
                    self._prepare_next_image_async(current_path, target_size)

                    logger.debug("预加载重建已启动")

                except Exception as e:
                    logger.debug(f"预加载重建失败: {e}")

            # 使用定时器延迟执行
            try:
                from Foundation import NSTimer

                NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                    0.05, self, "_execute_delayed_preload_rebuild:", None, False
                )
                self._delayed_preload_func = delayed_preload_rebuild
            except Exception:
                # 备选方案：直接执行
                delayed_preload_rebuild()

        except Exception as e:
            logger.debug(f"触发预加载重建失败: {e}")

    def _execute_delayed_preload_rebuild_(self, timer):
        """执行延迟的预加载重建（NSTimer回调）"""
        try:
            if hasattr(self, "_delayed_preload_func"):
                self._delayed_preload_func()
                delattr(self, "_delayed_preload_func")
        except Exception as e:
            logger.debug(f"执行延迟预加载重建失败: {e}")

    def request_high_quality_image(self):
        """请求加载当前图像的高质量版本"""
        if getattr(self.main_window, "_shutting_down", False):
            return
        if not self.main_window.images or self.main_window.current_index >= len(self.main_window.images):
            return

        image_path = self.main_window.images[self.main_window.current_index]

        def load_high_quality():
            try:
                view_frame = self.main_window.image_view.frame()
                target_size = (int(view_frame.size.width * 4), int(view_frame.size.height * 4))

                high_quality_image = self.image_cache.load_image_with_strategy(
                    image_path, "auto", target_size, force_reload=True
                )

                if high_quality_image:
                    if getattr(self.main_window, "_shutting_down", False):
                        return

                    def update_image():
                        self.main_window.image_view.setImage_(high_quality_image)
                        self.main_window.image_view.setNeedsDisplay_(True)

                    self._post_to_main(update_image)

            except Exception:
                logger.exception("High quality load failed for %s", image_path)

        threading.Thread(target=load_high_quality, daemon=True).start()

    def cleanup(self):
        """清理图像管理器资源"""
        try:
            self._memory_monitor_running = False
            if self.hybrid_processor:
                stopper = getattr(self.hybrid_processor, "stop_processing", None)
                if callable(stopper):
                    stopper(wait=False)
            if self.bidi_pool:
                self.bidi_pool.shutdown()
        except Exception:
            pass
