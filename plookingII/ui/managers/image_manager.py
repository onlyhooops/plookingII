"""
图像管理器

负责处理图像加载、缓存、处理策略和内存管理。
"""

import contextlib
import logging
import os
import threading
import time
from collections import OrderedDict, deque
from concurrent.futures import ThreadPoolExecutor

from ...config.constants import APP_NAME, IMAGE_PROCESSING_CONFIG
from ...config.manager import get_config, set_config
from ...core.bounded_executor import BoundedExecutor
from ...core.image_processing import HybridImageProcessor
from ...core.simple_cache import (
    AdvancedImageCache,
    BidirectionalCachePool,
    estimate_image_memory_mb,
    image_pixel_dimensions,
)

# 使用统一监控系统
from ...monitor import get_perf_tracker, get_unified_monitor

logger = logging.getLogger(APP_NAME)

# 快速导航像素阈值：文件虽小（<12MB）但像素超过此值仍需后台异步加载
# 高度压缩的 24MP JPEG 可能仅 6MB，但主线程解码需 80-150ms
_FAST_SYNC_MAX_PIXELS = 12_000_000  # 12MP


class ImageManager:
    """图像管理器，负责图像加载、缓存和处理策略"""

    # 图像尺寸缓存最大条目数（LRU 淘汰）
    _MAX_DIMENSIONS_CACHE = 2000
    # 后台任务节流：连续导航时后台任务的最小间隔（秒）
    _BG_TASK_THROTTLE_SEC = 0.5
    # 扩展预取节流：连续导航时不每次都触发 hot3 和自适应预取
    _PREFETCH_THROTTLE_SEC = 0.3

    def __init__(self, main_window):
        """初始化图像管理器

        Args:
            main_window: MainWindow实例
        """
        self.main_window = main_window

        # 统一监控器
        self.monitor = get_unified_monitor()
        # 轻量性能跟踪器（聚合统计 + 会话报告，供后续分析）
        self.perf = get_perf_tracker()
        self.slim_mode = get_config("feature.slim_mode", False)
        # 热路径配置缓存：full_res_browse 在每次显示/升级路径读取，
        # 配置启动时加载、运行期不变，构造时快照避免热路径重复 RLock 查询
        self._full_res_browse = get_config("feature.full_res_browse", True)

        # 高级图像缓存（max_items 自适应物理内存）
        adaptive_max_items, adaptive_max_memory = self._compute_cache_params()
        self.image_cache = AdvancedImageCache(max_items=adaptive_max_items, max_memory_mb=adaptive_max_memory)

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
        with contextlib.suppress(Exception):
            self.image_cache.image_processor = self.hybrid_processor
        self.processing_mode = "auto"

        # 渐进式加载控制（已收敛为默认禁用，兼容旧逻辑保留开关）
        self.progressive_loading_enabled = not get_config("feature.disable_progressive_layer", True)
        self.current_progressive_task = None

        # 双向缓存池（跟随主缓存的自适应参数）
        self.bidi_pool = BidirectionalCachePool(
            max_items=adaptive_max_items,
            max_memory_mb=adaptive_max_memory,
            preload_count=5,
            keep_previous=3,
            image_processor=self.hybrid_processor,
            advanced_cache=self.image_cache,
        )

        # 后台线程池：限制并发线程数，防止导航时大量创建线程导致性能下降
        # 关键路径（当前图加载/下一张预读/元信息/内存检查）
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="imgmgr")
        # 关键池队列深度上限：快速导航时非关键后台任务（缓存升级、内存检查等）
        # 超过该上限即丢弃新提交，防止过期任务无限积压挤占关键解码资源
        # （关键路径任务带代次检查，即使被丢弃，下一次导航也会重新调度）
        self._KEY_EXECUTOR_MAX_QUEUED = 8
        # 扩展预取线程池（自适应预取 + HOT3 常驻）
        # 与关键路径分离，避免快速导航时过期预取任务挤占当前图解码线程；
        # 外层有界队列保证快速连按时过期任务被优先丢弃，不无限积压
        self._prefetch_executor = BoundedExecutor(
            ThreadPoolExecutor(max_workers=2, thread_name_prefix="prefetch"), max_queued=6
        )

        # 内存监控线程
        self._memory_monitor_running = False
        self._memory_warning_observer = None

        # 响应系统内存警告（如其他应用占满内存时 macOS 发出的通知）：
        # 及时降级缓存，避免进程被系统强杀
        try:
            from AppKit import NSApplicationDidReceiveMemoryWarningNotification
            from Foundation import NSNotificationCenter

            self._memory_warning_observer = (
                NSNotificationCenter.defaultCenter().addObserverForName_object_queue_usingBlock_(
                    NSApplicationDidReceiveMemoryWarningNotification,
                    None,
                    None,
                    lambda _note: self._on_system_memory_warning(),
                )
            )
        except Exception:
            self._memory_warning_observer = None

        # 双缓冲：下一张就绪缓冲与代次控制（用于取消过时任务）
        self._next_ready_image = None
        self._next_ready_path = None
        self._load_generation = 0
        self._decode_lock = threading.Lock()
        self._last_index = None
        self._nav_history = []  # [(timestamp, direction)] 最近导航事件
        self._last_sequence_sync = 0  # 上次序列同步时间

        # 图片路径 -> 索引 O(1) 映射（懒构建，文件夹切换时重建）
        # 避免 _get_adjacent_path / _get_path_by_offset 每次导航 O(n) list.index()
        self._path_index: dict[str, int] | None = None
        self._images_snapshot = None

        # HOT3 强引用锁：保证当前/上一张/下一张不被 NSCache 驱逐
        # NSCache 在内存压力下由系统控制淘汰，无法保证 HOT3 常驻；
        # 使用独立 dict 强引用确保导航回退永远零延迟
        self._hot3_lock: dict[str, object] = {}

        # 当前图片元信息缓存（避免 status_bar 重复 I/O）
        self._current_image_resolution = None  # "WxH" 字符串或空字符串
        self._current_image_size_mb = None  # "X.XXMB" 字符串或空字符串

        # 内嵌预览（MPF）异步提取状态：无 MPF 结果缓存（LRU，防重复 I/O）
        self._no_mpf_cache: OrderedDict[str, bool] = OrderedDict()
        self._MAX_NO_MPF_CACHE = 500
        # 最近一次“全分辨率已显示”的代次：防止异步预览覆盖已显示的全分辨率画面
        self._full_shown_generation = -1

        # 解码耗时经验表（P2-1）：按文件大小分档记录近 N 次实测解码耗时，
        # 用于"自适应两阶段显示"——同一规格文件实测解码慢时自动降级为先显示
        # 预览再懒解码全分辨率，改善中低端机器首帧体验。
        # 结构: {size_bucket: deque(maxlen=RECENT_N)}，LRU 上限防长期运行无界增长。
        self._decode_experience: OrderedDict[str, deque] = OrderedDict()
        self._DECODE_EXPERIENCE_MAX_BUCKETS = 64
        self._DECODE_EXPERIENCE_RECENT_N = 5
        self._DECODE_EXPERIENCE_SLOW_MS = 150.0

        # 渲染节流守卫：确保所有渲染路径（缓存命中/预加载/后台解码）的最小显示间隔一致
        # 静态场景 80ms (12.5fps)，快速导航时自适应降低至 30ms (33fps)
        self.MIN_RENDER_INTERVAL = 0.08  # 静态默认值
        self.MIN_RENDER_INTERVAL_FAST = 0.03  # 快速导航时 30ms ≈ 33fps
        self._RENDER_THROTTLE_SPEED_THRESHOLD = 5  # 速度 > 5 张/秒时切换到快速节流
        self._scheduled_display_time = 0.0  # 下次允许显示的最早时间戳
        self._pending_image = None  # 待延迟显示的图片
        self._pending_timer = None  # threading.Timer 引用

        # 后台任务节流时间戳
        self._last_bg_task_time = 0.0
        self._last_prefetch_time = 0.0
        self._bg_task_submitted = False  # 防止重复提交后台任务

    def show_current_image(self, async_first_load=False):
        """显示当前图像

        Args:
            async_first_load: 当为True时，跳过同步快速加载路径，直接使用后台异步加载。
                             用于跨文件夹导航等首张图片必然缓存未命中的场景。
        """
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

        # 缓存当前图片元信息（供 status_bar 直接读取，避免重复 I/O）
        self._cache_current_image_meta(image_path)

        self._show_image_common(image_path, async_first_load=async_first_load)

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

    def _cache_current_image_meta(self, image_path: str):
        """缓存当前图片的元信息（分辨率、文件体积），供状态栏直接读取，避免重复磁盘 I/O。

        优先读取已有缓存（尺寸 LRU + 文件信息加载器），不触发新的磁盘 I/O；
        提交到独立的 prefetch 线程池，避免与当前图解码/next-ready 抢占关键解码线程。

        Args:
            image_path: 图像文件路径
        """
        gen = self._load_generation

        def meta_worker():
            try:
                dims = self._get_cached_dimensions_only(image_path)
                resolution = f"{dims[0]}x{dims[1]}" if dims else ""
                try:
                    from ...core.file_info_batch_loader import get_file_info_loader

                    size_mb_float = get_file_info_loader().get_file_size_mb(image_path, use_cache=True)
                    size_mb = f"{size_mb_float:.2f}MB"
                except Exception:
                    size_mb = ""
            except Exception:
                resolution = ""
                size_mb = ""

            # 仅当代次未变时回填，避免过期导航的元信息覆盖当前图片
            if gen == self._load_generation:
                self._current_image_resolution = resolution
                self._current_image_size_mb = size_mb

        try:
            # 元信息读取（缓存命中时零 I/O）放入 prefetch 池，不与关键解码竞争
            self._prefetch_executor.submit(meta_worker)
        except Exception:
            self._current_image_resolution = ""
            self._current_image_size_mb = ""

    def _show_image_common(self, image_path: str, async_first_load=False):
        """通用图像显示方法

        Args:
            image_path: 图像文件路径
            async_first_load: 是否强制后台异步加载
        """
        # 检查是否正在关闭应用
        if getattr(self.main_window, "_shutting_down", False):
            return

        # 执行图像显示流程
        self._execute_image_display_flow(image_path, async_first_load=async_first_load)

    def _execute_image_display_flow(self, image_path: str, async_first_load=False):
        """执行图像显示流程（重构版：消除重复，提升可读性）

        Args:
            image_path: 图像文件路径
            async_first_load: 是否强制后台异步加载
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
        #    MPF 内嵌预览图在后台异步提取（不阻塞主线程，见 _schedule_embedded_preview_async）
        self._schedule_embedded_preview_async(image_path)
        self._execute_loading_with_strategy(image_path, target_size, async_first_load=async_first_load)
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
        if self._full_res_browse:
            return None
        return self._get_dynamic_target_size()

    def _record_cache_hit(self):
        """记录缓存命中"""
        with contextlib.suppress(Exception):
            self.monitor.record_operation("cache_hit", 0, cache_hit=True)

    def _post_display_tasks(self, image_path: str, target_size, t_start: float, method: str):
        """图像显示后的后台任务（节流版：快速导航时跳过昂贵的扩展预取）

        Args:
            image_path: 图像文件路径
            target_size: 目标尺寸
            t_start: 开始时间
            method: 显示方法
        """
        now = time.time()

        # 后台任务（内存检查 + 进度保存）—— 节流：避免每次导航都提交
        if now - self._last_bg_task_time >= self._BG_TASK_THROTTLE_SEC:
            self._last_bg_task_time = now
            self._bg_task_submitted = False
            self._schedule_background_tasks()

        # 下一张预读：始终提交（关键路径，代次机制保证可取消）
        self._prepare_next_image_async(image_path, target_size)

        # 非精简模式：扩展预取（hot3 + 自适应）—— 节流
        if not self.slim_mode and now - self._last_prefetch_time >= self._PREFETCH_THROTTLE_SEC:
            self._last_prefetch_time = now
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
        # 轻量性能跟踪：图片显示端到端耗时（含缓存命中方法分布）
        try:
            self.perf.record("image_display", max(0.0, time.time() - t_start) * 1000, method=method)
        except Exception:
            pass

    def _execute_loading_with_strategy(self, image_path: str, target_size, async_first_load=False):
        """使用策略执行加载

        Args:
            image_path: 图像文件路径
            target_size: 目标尺寸
            async_first_load: 是否强制后台异步加载
        """
        if self.slim_mode:
            # 精简模式：直接执行加载策略
            self._execute_loading_strategy(image_path, target_size, async_first_load=async_first_load)
        else:
            # 完整模式：尝试两阶段加载
            if not self._maybe_two_stage_for_ultra(image_path, target_size):
                self._execute_loading_strategy(image_path, target_size, async_first_load=async_first_load)
            self._schedule_background_tasks()

    def _notify_bidirectional_cache(self, image_path: str):
        """通知双向缓存池当前图片

        Args:
            image_path: 图像文件路径
        """
        try:
            self.bidi_pool.set_current_image_sync(image_path, image_path)
        except Exception as e:
            logger.debug("bidi_pool.set_current_image_sync failed: %s", e)

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
            logger.debug("image_cache.get failed: %s", e)

        if cached_image:
            # 缓存命中，立即显示
            self._display_image_immediate(cached_image)
            self._schedule_background_tasks()
            # 全分辨率浏览模式下，命中低分辨率条目时后台升级（代次保护）
            self._maybe_upgrade_cached_image(image_path, cached_image)
            return True

        return False

    def _maybe_upgrade_cached_image(self, image_path: str, cached_image) -> None:
        """缓存命中但条目为低分辨率时，后台加载全分辨率版本并升级显示

        预取/下一张缓冲写入的是视图级分辨率；在全分辨率浏览模式下
        （full_res_browse），命中这类条目后仅显示会"偏软"。此处按代次
        保护地调度一次全分辨率后台加载，完成后无缝替换显示并更新缓存。

        Args:
            image_path: 图像文件路径
            cached_image: 当前缓存条目对应的图像对象
        """
        if not self._full_res_browse:
            return
        try:
            file_dims = self._get_cached_dimensions(image_path)
            if not file_dims or file_dims[0] <= 0 or file_dims[1] <= 0:
                return
            img_dims = image_pixel_dimensions(cached_image)
            if img_dims is None:
                return
            # 已接近全分辨率（≥90% 像素量）则无需重复加载
            if img_dims[0] * img_dims[1] >= int(file_dims[0] * file_dims[1] * 0.9):
                return

            gen = self._load_generation

            def upgrade():
                try:
                    if gen != self._load_generation:
                        return
                    img = self._load_image_with_concurrency(image_path, None)
                    if img is None:
                        return
                    if gen != self._load_generation:
                        return
                    self._post_to_main(lambda: self._display_image_immediate(img))
                    with contextlib.suppress(Exception):
                        size_mb = estimate_image_memory_mb(img)
                        self.image_cache.put(image_path, img, size_mb=size_mb)
                except Exception:
                    logger.debug("_maybe_upgrade_cached_image failed", exc_info=True)

            # 非关键后台任务：队列积压超限时丢弃（快速导航时升级任务很快过期）
            self._submit_noncritical(upgrade)
        except Exception:
            logger.debug("_maybe_upgrade_cached_image check failed", exc_info=True)

    def _execute_loading_strategy(self, image_path: str, target_size: tuple, async_first_load=False):
        """执行加载策略

        Args:
            image_path: 图像文件路径
            target_size: 目标尺寸
            async_first_load: 当为True时，跳过同步快速加载，
                             直接走后台异步路径，避免跨文件夹跳转时主线程阻塞
        """
        # 获取文件大小以决定加载策略
        file_size_mb = self._get_file_size_safely(image_path)

        # 跨文件夹首张加载：强制后台异步，禁止主线程同步解码
        if async_first_load:
            target_size = self._get_target_size_for_view(scale_factor=2, image_path=image_path)
            self._start_background_load(image_path, target_size)
            self._schedule_background_tasks()
            return

        # 智能加载策略选择：根据文件大小选择最优加载方式
        if self._should_use_fast_loading(file_size_mb, image_path):
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
            logger.debug("get_file_size_mb failed, fallback to 0: %s", e)
            return 0

    def _should_use_fast_loading(self, file_size_mb: float, image_path: str = "") -> bool:
        """判断是否应该使用主线程同步快速加载

        同步加载虽能省一次线程切换，但解码发生在主线程：20-50MB 的
        RAW/HEIC/JPEG 解码需要数百毫秒，会造成按键导航卡顿。因此使用
        独立的、更保守的同步阈值（fast_sync_threshold_mb，默认 12MB），
        超过该阈值的文件一律走后台异步解码。

        额外保护：高度压缩的大像素文件（如 24MP 但仅 6MB 的 JPEG）
        也走后台异步，通过像素数阈值（默认 12MP）二次过滤。

        Args:
            file_size_mb: 文件大小（MB）
            image_path: 图片路径，用于像素数检查

        Returns:
            bool: 是否应该使用主线程同步快速加载
        """
        sync_threshold = IMAGE_PROCESSING_CONFIG.get("fast_sync_threshold_mb", 12)
        if file_size_mb > sync_threshold or not IMAGE_PROCESSING_CONFIG.get("fast_load_enabled", True):
            return False
        # 像素数保护：文件虽小但像素过大的仍走后台。
        # 仅读尺寸缓存（主线程不触发元数据 I/O）；尺寸未知时保守走后台异步，
        # 避免高度压缩的大像素文件在主线程同步解码造成卡顿。
        if image_path:
            dims = self._get_cached_dimensions_only(image_path)
            if dims is None:
                return False
            if dims[0] * dims[1] > _FAST_SYNC_MAX_PIXELS:
                return False
        return True

    def _execute_fast_loading(self, image_path: str):
        """执行快速加载

        Args:
            image_path: 图像文件路径
        """
        try:
            image = self._load_image_optimized(image_path, target_size=None)
            if image:
                self._display_image_immediate(image)
                # 快速显示后仅提交后台任务和下一张预读（扩展预取由 _post_display_tasks 统一节流）
                self._schedule_background_tasks()
                target_size = self._get_target_size_for_view(scale_factor=2, image_path=image_path)
                self._prepare_next_image_async(image_path, target_size)
        except Exception as e:
            logger.debug("Fast sync load failed, fallback to background: %s", e)
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
                    # 主线程热路径：仅读尺寸缓存，未知时不触发元数据 I/O
                    portrait_hint = self._portrait_hint_from_cache(image_path)
                    if portrait_hint:
                        # 竖向图片降低缩放因子，减少解码负载
                        adaptive_scale = max(1.2, scale_factor * 0.75)
                        logger.debug("竖向图片优化：缩放因子 %s -> %s", scale_factor, adaptive_scale)

                    # PNG 格式优化：PNG 解码更重，降低目标分辨率
                    if self._is_png_image(image_path):
                        adaptive_scale = max(1.2, adaptive_scale * 0.85)
                        logger.debug("PNG 优化：缩放因子 -> %s", adaptive_scale)
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

        注意：本方法可能触发同步元数据 I/O（CGImageSourceCopyPropertiesAtIndex），
        仅供后台线程调用；主线程热路径请使用 _portrait_hint_from_cache
        （仅读缓存，不触碰文件系统）。

        Args:
            image_path: 图像文件路径

        Returns:
            bool: True表示竖向图片，False表示横向或方形
        """
        try:
            dims = self._get_cached_dimensions(image_path)
            return bool(dims and dims[1] > dims[0])
        except Exception:
            return False

    def _portrait_hint_from_cache(self, image_path: str) -> bool | None:
        """仅读缓存的竖向判定（主线程热路径使用，不触发任何 I/O）

        Returns:
            True/False 当尺寸信息已在缓存中；None 表示未知
        """
        try:
            dims = self._get_cached_dimensions_only(image_path)
            if dims:
                return dims[1] > dims[0]
            return None
        except Exception:
            return None

    def _cache_image_dimensions(self, image_path: str, dims: tuple[int, int]) -> None:
        """写入尺寸缓存（LRU：命中移动到末尾，超限逐出最久未访问项）"""
        try:
            cache = getattr(self, "_image_dimensions_cache", None)
            if cache is None:
                cache = OrderedDict()
                self._image_dimensions_cache = cache
            if image_path in cache:
                cache.move_to_end(image_path)
            cache[image_path] = dims
            while len(cache) > self._MAX_DIMENSIONS_CACHE:
                cache.popitem(last=False)
        except Exception:
            pass

    def _get_cached_dimensions_only(self, image_path: str) -> tuple[int, int] | None:
        """仅读尺寸缓存（不触发任何 I/O；命中时更新 LRU 顺序）"""
        try:
            cache = getattr(self, "_image_dimensions_cache", None)
            if cache and image_path in cache:
                dims = cache[image_path]
                if hasattr(cache, "move_to_end"):
                    cache.move_to_end(image_path)
                return dims
            return None
        except Exception:
            return None

    def _is_png_image(self, image_path: str) -> bool:
        """检测图像是否为PNG格式

        PNG 使用 DEFLATE 无损压缩，解码开销显著高于 JPEG DCT 解压，
        需要差异化处理策略（更低的阈值、更窄的预加载窗口等）。

        Args:
            image_path: 图像文件路径

        Returns:
            bool: True if PNG
        """
        try:
            return os.path.splitext(image_path)[1].lower() == ".png"
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
            logger.debug("_should_use_progressive failed: %s", e)
            return False

    def _display_image_immediate(self, image, is_preview=False):
        """在图片视图中显示图片（带自适应渲染节流）

        所有渲染路径（缓存命中、预加载缓冲、后台解码完成）统一经过此方法。
        静态场景 80ms (12.5fps)，快速连续导航 (>5张/秒) 时降至 30ms (33fps)，
        确保快速浏览时画面跟手。

        Args:
            image: 图像对象
            is_preview: 是否为内嵌预览图（预览图不计入节流，预期瞬时显示）
        """
        now = time.time()

        # 取消当前的待定延迟显示，新请求覆盖旧请求
        if self._pending_timer is not None:
            self._pending_timer.cancel()
            self._pending_timer = None
            self._pending_image = None

        # 自适应节流间隔：根据导航速度选择
        velocity = self._compute_nav_velocity()
        if velocity > self._RENDER_THROTTLE_SPEED_THRESHOLD and not is_preview:
            effective_interval = self.MIN_RENDER_INTERVAL_FAST
        else:
            effective_interval = self.MIN_RENDER_INTERVAL

        # 计算允许显示的最早时间
        target_time = max(now, self._scheduled_display_time)
        remaining = target_time - now

        if remaining > 0 and not is_preview:
            # 距离上次显示太近，延迟到 target_time 再显示
            self._pending_image = image
            self._pending_timer = threading.Timer(remaining, self._on_delayed_display)
            self._pending_timer.daemon = True
            self._pending_timer.start()
        else:
            # 已超过最小间隔，直接显示
            self._apply_display(image)
            self._scheduled_display_time = now + effective_interval

    def _on_delayed_display(self):
        """延迟显示回调（在 Timer 线程中执行，需投递到主线程）"""
        image = self._pending_image
        self._pending_image = None
        self._pending_timer = None
        if image is not None:
            self._post_to_main(lambda img=image: self._apply_display(img))

    def _apply_display(self, image, is_preview=False):
        """实际执行图像显示（必须在主线程调用）

        Args:
            image: 图像对象
            is_preview: 是否为内嵌预览图（仅占位，不标记全分辨率已显示）
        """
        if not is_preview:
            # 全分辨率/缓存图已显示：后续异步预览不得覆盖当前画面
            self._full_shown_generation = self._load_generation
        # 通过图像视图控制器显示图像
        if hasattr(self.main_window, "image_view_controller"):
            self.main_window.image_view_controller.display_image(image)
        # 回退到直接设置图像
        elif hasattr(self.main_window, "image_view"):
            self.main_window.image_view.setImage_(image)
            self.main_window.image_view.setNeedsDisplay_(True)
        # 更新调度时间戳（线程安全：仅主线程写入）
        self._scheduled_display_time = time.time() + self.MIN_RENDER_INTERVAL

    def _start_background_load(self, image_path, target_size):
        """启动后台图像加载（代次保护：快速导航时丢弃过时解码结果）"""

        gen = self._load_generation

        def background_load():
            try:
                image = self._load_image_with_concurrency(image_path, target_size)
                if gen != self._load_generation:
                    # 已导航到新图片，丢弃过时结果，避免旧图覆盖当前显示
                    return
                if image:
                    self._post_to_main(lambda: self._display_image_immediate(image))
                else:
                    self._post_to_main(lambda: self.main_window.image_view.setImage_(None))
            except Exception:
                logger.exception("background_load failed for %s", image_path)

        self._executor.submit(background_load)

    def _submit_noncritical(self, fn, *args, **kwargs):
        """提交非关键后台任务（有界：队列积压超限时丢弃新任务）

        用于缓存升级、内存检查等可重入/可跳过的后台任务：
        快速导航时这些任务很快过期（代次检查会提前退出），
        队列深度超过上限时直接丢弃新提交，避免过期任务无限积压
        挤占关键解码线程。

        Args:
            fn: 后台任务函数
            *args, **kwargs: 传递给 fn 的参数

        Returns:
            Future 或 None（队列满被丢弃时）
        """
        try:
            work_queue = getattr(self._executor, "_work_queue", None)
            if work_queue is not None and work_queue.qsize() >= self._KEY_EXECUTOR_MAX_QUEUED:
                logger.debug("关键池队列已满(%s)，丢弃非关键任务", self._KEY_EXECUTOR_MAX_QUEUED)
                return None
            return self._executor.submit(fn, *args, **kwargs)
        except Exception:
            logger.debug("提交非关键任务失败", exc_info=True)
            return None

    def _load_image_with_concurrency(self, image_path: str, target_size):
        try:
            # 动态并发控制：根据 CPU 核心数自适应，多核 Mac 上充分利用解码能力
            if not hasattr(self, "_decode_semaphore"):
                cpu_count = getattr(os, "cpu_count", None)
                cpu_count = cpu_count() if cpu_count else 4
                # Quartz 懒代理不解码像素，信号量等待是不必要的；
                # 实际解码主要发生在缩略图/全分辨率路径，保守设置为 cores//2
                self._decode_semaphore = threading.BoundedSemaphore(value=max(2, cpu_count // 2))
            start = time.time()
            with self._decode_semaphore:
                result = self._load_image_optimized(image_path, target_size=target_size)
            # 归档实际解码耗时到经验表（供 P2-1 自适应两阶段消费）
            if result is not None:
                self._record_decode_experience(image_path, (time.time() - start) * 1000)
            return result
        except Exception:
            logger.exception("_load_image_with_concurrency failed for %s", image_path)
            return None

    # ------------------------------------------------------------------
    # 解码耗时经验表（P2-1 自适应两阶段）
    # ------------------------------------------------------------------
    @staticmethod
    def _decode_size_bucket(file_size_mb: float) -> str:
        """按文件大小分档（对数近似）：小档更细，大档更粗"""
        thresholds = [
            (1.0, "0-1MB"),
            (5.0, "1-5MB"),
            (12.0, "5-12MB"),
            (30.0, "12-30MB"),
            (80.0, "30-80MB"),
        ]
        for limit, label in thresholds:
            if file_size_mb < limit:
                return label
        return "80MB+"

    def _record_decode_experience(self, image_path: str, duration_ms: float) -> None:
        """归档一次解码耗时到经验表（按文件大小分档）"""
        try:
            file_size_mb = self._get_file_size_safely(image_path)
            bucket = self._decode_size_bucket(file_size_mb)
            samples = self._decode_experience.get(bucket)
            if samples is None:
                # LRU：超出上限时淘汰最久未更新的分档
                if len(self._decode_experience) >= self._DECODE_EXPERIENCE_MAX_BUCKETS:
                    self._decode_experience.popitem(last=False)
                samples = deque(maxlen=self._DECODE_EXPERIENCE_RECENT_N)
                self._decode_experience[bucket] = samples
            else:
                # LRU 提升：最近更新的分档移到末尾
                self._decode_experience.move_to_end(bucket)
            samples.append(duration_ms)
        except Exception:
            logger.debug("record_decode_experience failed", exc_info=True)

    def _is_decode_slow_by_experience(self, image_path: str) -> bool:
        """按经验表判断该规格文件解码是否偏慢

        同规格（文件大小分档）近 N 次实测耗时均值超过阈值时返回 True，
        触发自适应两阶段显示。数据不足（样本 < 2）时不误判。
        """
        try:
            file_size_mb = self._get_file_size_safely(image_path)
            bucket = self._decode_size_bucket(file_size_mb)
            samples = self._decode_experience.get(bucket)
            if samples is None or len(samples) < 2:
                return False
            avg_ms = sum(samples) / len(samples)
            return avg_ms >= self._DECODE_EXPERIENCE_SLOW_MS
        except Exception:
            return False

    def reset_decode_experience(self) -> None:
        """重置解码经验表（公开入口，供测试与长期运行维护）"""
        try:
            self._decode_experience.clear()
        except Exception:
            pass

    def get_decode_experience_stats(self) -> dict:
        """导出经验表统计（调试/监控用）"""
        return {
            "buckets": {k: list(v) for k, v in self._decode_experience.items()},
            "slow_threshold_ms": self._DECODE_EXPERIENCE_SLOW_MS,
            "recent_n": self._DECODE_EXPERIENCE_RECENT_N,
        }

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

    def _schedule_embedded_preview_async(self, image_path: str) -> None:
        """后台异步提取 JPEG/HEIC 内嵌预览图（Instant First Frame，不阻塞主线程）

        缓存未命中时提交到 prefetch 线程池：提取成功且全分辨率尚未显示时，
        投递到主线程作为占位首帧；文件无 MPF 则记录结果，避免重复读取。
        所有显示路径均带代次与“全分辨率已显示”双重保护，不会降级画面。

        Args:
            image_path: 图像文件路径
        """
        try:
            if image_path in self._no_mpf_cache:
                return
            gen = self._load_generation

            def worker():
                try:
                    if gen != self._load_generation:
                        return
                    from plookingII.core.loading.helpers import extract_embedded_preview

                    preview = extract_embedded_preview(image_path)
                    if preview is None:
                        self._remember_no_mpf(image_path)
                        return
                    if gen != self._load_generation:
                        return

                    def show():
                        if gen != self._load_generation:
                            return
                        if getattr(self, "_full_shown_generation", -1) == gen:
                            return
                        self._display_image_immediate(preview, is_preview=True)

                    self._post_to_main(show)
                except Exception:
                    pass

            self._prefetch_executor.submit(worker)
        except Exception:
            pass

    def _remember_no_mpf(self, image_path: str) -> None:
        """记录“该文件无 MPF 内嵌预览”，避免后续导航重复打开文件检查"""
        try:
            self._no_mpf_cache[image_path] = True
            while len(self._no_mpf_cache) > self._MAX_NO_MPF_CACHE:
                self._no_mpf_cache.popitem(last=False)
        except Exception:
            pass

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

            self._executor.submit(worker, next_path, gen)
        except Exception:
            logger.debug("_prepare_next_image_async failed", exc_info=True)

    def _get_path_index(self, path: str) -> int | None:
        """返回图片路径在当前 images 列表中的索引（O(1) 缓存查找）

        images 列表在文件夹切换时整体重新赋值（身份变化）或长度变化，
        检测到变化时一次性重建 O(n) 的 path->index 映射，
        之后所有相邻查找均为 O(1)，避免每次导航在主线程做 O(n) index()。

        Args:
            path: 图片文件路径

        Returns:
            索引值，路径不存在时返回 None
        """
        try:
            images = getattr(self.main_window, "images", None) or []
            if (
                self._path_index is None
                or self._images_snapshot is not images
                or len(self._images_snapshot) != len(images)
            ):
                self._path_index = {p: i for i, p in enumerate(images)}
                self._images_snapshot = images
            return self._path_index.get(path)
        except Exception:
            return None

    def _get_adjacent_path(self, current_path: str, direction: int = +1) -> str:
        """获取相邻图片路径（direction=+1 下一张，-1 上一张）"""
        try:
            idx = self._get_path_index(current_path)
            if idx is None:
                return None
            images = getattr(self.main_window, "images", None) or []
            nxt = idx + (1 if direction >= 0 else -1)
            if 0 <= nxt < len(images):
                return images[nxt]
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
        """计算预取窗口大小（速度+内存自适应）

        基于导航速度、方向一致性和系统可用内存综合计算。
        快速连续浏览 + 充足内存时扩大窗口，内存紧张时收缩。

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
            dt = max(0.01, timestamps[-1] - timestamps[-2]) if len(timestamps) >= 2 else 0.5
            same_dir_ratio = 0.0
            if dirs:
                last_dir = dirs[-1]
                same_dir_ratio = sum(1 for d in dirs if d == last_dir) / float(len(dirs))

            # 速度启发式：更快切换 + 一致方向 → 更大窗口
            window = 1
            if dt < 0.15 and same_dir_ratio > 0.7:
                window = 3  # 极快连续浏览
            elif (dt < 0.25 and same_dir_ratio > 0.6) or (dt < 0.5 and same_dir_ratio > 0.5):
                window = 2

            # 内存自适应：可用内存充裕时扩大窗口，紧张时收缩
            try:
                mem_status = self.monitor.get_memory_status()
                available_mb = mem_status.available_mb
                if available_mb > 4000:
                    window += 1  # 内存充裕，多预取一张
                elif available_mb < 800:
                    window = max(1, window - 1)  # 内存紧张，收缩窗口
            except Exception:
                pass

            # 竖向图片优化：减少预取窗口，优先保证当前图片流畅性
            if current_image_path and self._is_portrait_image(current_image_path):
                window = max(1, int(window * 0.7))
                logger.debug("竖向图片预取优化：窗口大小 %s", window)

            # PNG 格式优化：PNG 解码更重，缩窄预加载窗口减少 CPU 竞争
            if current_image_path and self._is_png_image(current_image_path):
                png_factor = IMAGE_PROCESSING_CONFIG.get("png_optimization", {}).get("prefetch_window_factor", 0.7)
                window = max(1, int(window * png_factor))
                logger.debug("PNG 预取优化：窗口大小 %s (factor=%s)", window, png_factor)

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
                # 扩展预取走独立线程池，避免挤占当前图/下一张的关键解码线程
                self._prefetch_executor.submit(self._prefetch_worker, path, target_size, gen, priority)
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
            # 预取使用视图级目标尺寸：预加载目的是加速下一次导航，
            # 只需视图分辨率（~2000-3000px），全分辨率浪费 4x 内存和时间
            prefetch_target = target_size if target_size else self._get_dynamic_target_size()
            img = self._load_image_with_concurrency(path, prefetch_target)
            if img is None:
                return
            # 放入预加载缓存层
            if expected_gen != self._load_generation:
                return
            with contextlib.suppress(Exception):
                size_mb = estimate_image_memory_mb(img)
                self.image_cache.put(path, img, size_mb=size_mb)
        except Exception:
            logger.debug("_prefetch_worker failed", exc_info=True)

    def _cancel_stale_prefetches(self) -> None:
        # 基于代次的软取消，线程会在开始/结束前检查 expected_gen
        # 此处仅提升代次已在 show_current_image 中完成
        pass

    def _get_path_by_offset(self, current_path: str, offset: int) -> str:
        try:
            idx = self._get_path_index(current_path)
            if idx is None:
                return None
            images = getattr(self.main_window, "images", None) or []
            tgt = idx + offset
            if 0 <= tgt < len(images):
                return images[tgt]
            return None
        except Exception:
            return None

    def _load_and_display_progressive(self, image_path, target_size):
        """渐进式加载和显示大图片（Preview.app风格两阶段）

        阶段1: 立即创建缩略图→即刻显示（用户看到预览）
        阶段2: 创建懒解码CGImage代理→在GPU空闲时decode→无缝替换

        Args:
            image_path: 图像文件路径
            target_size: 目标尺寸
        """
        if getattr(self.main_window, "_shutting_down", False):
            return

        gen = self._load_generation

        def progressive_load_worker():
            try:
                if gen != self._load_generation:
                    return
                local_target_size = self._resolve_progressive_target_size(target_size)
                preview_size = (max(1, local_target_size[0] // 3), max(1, local_target_size[1] // 3))

                # 阶段1：快速缩略图→立即显示
                preview_image = self._load_image_optimized(image_path, prefer_preview=True, target_size=preview_size)
                if preview_image and gen == self._load_generation:
                    self._post_to_main(lambda: self._display_image_immediate(preview_image, is_preview=True))

                    # 阶段2：懒解码代理CGImage（毫秒级创建）→替换预览
                    if gen != self._load_generation:
                        return
                    full_image = self.image_cache.load_image_with_strategy(image_path, "quartz", local_target_size)
                    if full_image is None:
                        full_image = self._load_image_optimized(image_path, target_size=local_target_size)
                    if full_image and gen == self._load_generation:
                        self._post_to_main(lambda: self._display_image_immediate(full_image))
            except Exception:
                logger.exception("Progressive load failed for %s", image_path)

        self.current_progressive_task = self._executor.submit(progressive_load_worker)

    def _get_cached_dimensions(self, image_path: str) -> tuple[int, int] | None:
        """获取缓存的图像像素尺寸（不解码完整图像）

        缓存命中直接返回；未命中时读取文件元数据（可能触发 I/O），
        仅供后台线程调用，主线程请使用 _get_cached_dimensions_only。

        Args:
            image_path: 图像文件路径

        Returns:
            (width, height) 或 None
        """
        try:
            cached = self._get_cached_dimensions_only(image_path)
            if cached:
                return cached
            dims = None
            try:
                from Foundation import NSURL
                from Quartz import CGImageSourceCopyPropertiesAtIndex, CGImageSourceCreateWithURL

                url = NSURL.fileURLWithPath_(image_path)
                source = CGImageSourceCreateWithURL(url, None)
                if source:
                    props = CGImageSourceCopyPropertiesAtIndex(source, 0, None)
                    if props:
                        dims = (props.get("PixelWidth", 0), props.get("PixelHeight", 0))
            except Exception:
                pass
            if dims and dims[0] > 0:
                self._cache_image_dimensions(image_path, dims)
            return dims
        except Exception:
            return None

    def prewarm_dimensions(self, image_paths, limit: int = 600) -> None:
        """后台批量预热图片尺寸元数据（不解码像素）

        文件夹加载完成后调用，将整目录的宽高信息提前写入 LRU 缓存，
        使后续导航热路径的竖向检测 / 像素阈值判断全部命中缓存，
        主线程不再触碰元数据 I/O。

        跨启动加速（P3-4）：优先命中目录级持久化尺寸缓存（以目录 mtime
        失效），二次打开同一目录直接批量回填内存缓存，跳过逐文件元数据
        读取；未命中则逐个读取并顺带写回持久化缓存。

        Args:
            image_paths: 图片路径列表
            limit: 单次预热上限（大文件夹只预热前 N 张，其余按需回填）
        """
        try:
            if getattr(self.main_window, "_shutting_down", False):
                return
            paths = list(image_paths or [])[:limit]
            if not paths:
                return

            # 目录级持久化缓存键：以 paths 所在目录 + mtime 为失效依据
            dir_path = os.path.dirname(paths[0]) if paths else ""
            dir_mtime = -1.0
            try:
                if dir_path:
                    dir_mtime = os.stat(dir_path).st_mtime
            except OSError:
                dir_mtime = -1.0

            def worker():
                try:
                    if not dir_path:
                        return
                    # P3-4：先查目录级持久化缓存
                    try:
                        from ...core.dimension_cache import get_dimension_cache

                        persisted = get_dimension_cache().load(dir_path, dir_mtime)
                    except Exception:
                        persisted = None

                    if persisted:
                        # 命中：批量回填内存 LRU，跳过逐文件元数据 I/O
                        for p in paths:
                            name = os.path.basename(p)
                            dims = persisted.get(name)
                            if dims:
                                self._cache_image_dimensions(p, dims)
                        return

                    # 未命中：逐个读取并收集，顺带写回持久化缓存
                    collected: dict[str, tuple[int, int]] = {}
                    for p in paths:
                        if getattr(self.main_window, "_shutting_down", False):
                            return
                        if self._get_cached_dimensions_only(p) is not None:
                            continue
                        dims = self._get_cached_dimensions(p)
                        if dims and dims[0] > 0:
                            collected[os.path.basename(p)] = dims
                    try:
                        if collected:
                            get_dimension_cache().save(dir_path, dir_mtime, collected)
                    except Exception:
                        pass
                except Exception:
                    pass

            self._prefetch_executor.submit(worker)
        except Exception:
            pass

    def _maybe_two_stage_for_ultra(self, image_path: str, target_size: tuple) -> bool:
        """根据文件大小/像素数/解码经验决定是否采用两阶段显示（预览→全清晰度）

        触发条件：
        1. 文件大小 >= ultra_image_threshold_mb (默认80MB)
        2. 像素数 >= ultra_pixel_threshold (默认24MP = 6000×4000)
        3. 解码经验表：同规格文件实测解码偏慢（P2-1 自适应）——
           中低端机器上文件不大但解码慢（外置盘、高压缩 JPEG）时，
           自动降级为先显示预览再懒解码全分辨率，改善首帧体验
        """
        try:
            ultra_mb = IMAGE_PROCESSING_CONFIG.get("ultra_image_threshold_mb", 80)
            ultra_pixels = IMAGE_PROCESSING_CONFIG.get("ultra_pixel_threshold", 24_000_000)
            file_size_mb = self._get_file_size_safely(image_path)

            if file_size_mb >= float(ultra_mb):
                self._load_and_display_progressive(image_path, target_size)
                return True

            # 额外检查：像素数超过阈值也启用两阶段（压缩率高的大图文件可能不大）
            # 仅读尺寸缓存：主线程不触发元数据 I/O，未知时依赖文件大小阈值
            dims = self._get_cached_dimensions_only(image_path)
            if dims and dims[0] * dims[1] >= ultra_pixels:
                self._load_and_display_progressive(image_path, target_size)
                return True

            # P2-1 自适应：经验表显示该规格解码偏慢 → 两阶段
            if self._is_decode_slow_by_experience(image_path):
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
                logger.debug("竖向图片目标尺寸优化: %s -> %s", target_size, adjusted_target_size)

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
        if self.progressive_loading_enabled and file_size_mb >= progressive_threshold:
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
        """确保 当前/上一张/下一张 常驻（HOT3 强引用保护）

        机制：
        1. 主缓存层（NSCache/OrderedDict LRU）—— 正常缓存淘汰
        2. HOT3 强引用锁（_hot3_lock dict）—— 保证当前+邻居永不驱逐

        NSCache 在内存压力下由系统控制淘汰，即使有 LRU 记账也无法阻止
        系统驱逐当前正在显示的图片。独立的 dict 强引用确保：
        - 左右方向键回退永远零延迟
        - 仅在切换文件夹时主动清理 _hot3_lock
        """
        try:
            neighbors = [current_path]
            prev_path = self._get_adjacent_path(current_path, -1)
            next_path = self._get_adjacent_path(current_path, +1)
            if prev_path:
                neighbors.append(prev_path)
            if next_path:
                neighbors.append(next_path)

            # 清理过期 HOT3 条目（不在邻居列表中的）
            stale = [p for p in self._hot3_lock if p not in neighbors]
            for p in stale:
                del self._hot3_lock[p]

            gen = self._load_generation

            def promote_and_lock(path: str, expected_gen: int):
                try:
                    if expected_gen != self._load_generation:
                        return
                    # 已在 HOT3 锁中则跳过
                    if path in self._hot3_lock:
                        return
                    # 先查主缓存
                    cached = self.image_cache.get(path)
                    if cached is not None:
                        self._hot3_lock[path] = cached
                        return
                    # 加载并双重存储：主缓存 + HOT3 锁
                    img = self._load_image_with_concurrency(path, None)
                    if img is None:
                        return
                    if expected_gen != self._load_generation:
                        return
                    self._hot3_lock[path] = img
                    with contextlib.suppress(Exception):
                        size_mb = estimate_image_memory_mb(img)
                        self.image_cache.put(path, img, size_mb=size_mb)
                except Exception:
                    logger.debug("promote_and_lock hot3 failed", exc_info=True)

            for p in neighbors:
                # HOT3 常驻走独立预取线程池，与关键解码路径隔离
                self._prefetch_executor.submit(promote_and_lock, p, gen)
        except Exception:
            logger.debug("_ensure_hot3_residency failed", exc_info=True)

    def _schedule_background_tasks(self):
        """调度后台任务执行（防重复提交）"""
        if getattr(self.main_window, "_shutting_down", False):
            return
        if self._bg_task_submitted:
            return
        self._bg_task_submitted = True

        def background_worker():
            try:
                time.sleep(0.2)
                self._check_memory_usage()
                time.sleep(0.3)
                self.main_window._save_task_progress()
            except Exception:
                logger.exception("background_worker failed")
            finally:
                self._bg_task_submitted = False

        # 非关键后台任务：队列积压超限时丢弃（快速导航时过期任务不挤占关键解码）
        if self._submit_noncritical(background_worker) is None:
            self._bg_task_submitted = False

    def _check_memory_usage(self):
        """检查内存使用情况"""
        # 先对账 NSCache 记账，确保统计反映实际状态
        with contextlib.suppress(Exception):
            self.image_cache.reconcile()
        memory_status = self.monitor.get_memory_status()
        cache_stats = self.image_cache.get_stats()
        total_cache_memory = cache_stats.get("memory_mb", 0)

        logger.debug(
            "Memory - Available: %.1fMB, Cache: %.1fMB",
            memory_status.available_mb,
            total_cache_memory,
        )

        available_mb = memory_status.available_mb
        pressure_level = memory_status.pressure_level

        if available_mb < 500:
            self._emergency_memory_cleanup()
        elif available_mb < 1000:
            self._aggressive_memory_cleanup()
        elif pressure_level in ("high", "critical") or total_cache_memory > 1500:
            self._moderate_memory_cleanup()
        elif total_cache_memory > 1000:
            self._preventive_memory_cleanup()

        self._start_background_memory_monitor()

    def _on_system_memory_warning(self):
        """系统内存警告回调：切回主线程执行紧急清理"""
        try:
            self._post_to_main(self._emergency_memory_cleanup)
        except Exception:
            with contextlib.suppress(Exception):
                self._emergency_memory_cleanup()

    def _emergency_memory_cleanup(self):
        """紧急内存清理：只保留当前图片"""
        cache_size = len(self.image_cache)
        if cache_size > 1:
            self.image_cache.evict_oldest(cache_size - 1)
        import gc

        gc.collect()

    def _aggressive_memory_cleanup(self):
        """激进内存清理：保留当前+邻居"""
        cache_size = len(self.image_cache)
        if cache_size > 3:
            self.image_cache.evict_oldest(cache_size - 3)
        import gc

        gc.collect()

    def _moderate_memory_cleanup(self):
        """适度内存清理：减半"""
        cache_size = len(self.image_cache)
        if cache_size > 5:
            self.image_cache.evict_oldest(cache_size // 2)

    def _preventive_memory_cleanup(self):
        """预防性内存清理：不超过8项"""
        cache_size = len(self.image_cache)
        if cache_size > 8:
            self.image_cache.evict_oldest(cache_size - 8)

    def _trim_preload_if_needed(self):
        pass

    def _trim_main_caches_if_needed(self):
        pass

    def _start_background_memory_monitor(self):
        """启动后台内存监控线程（防重复启动 + 崩溃保护）"""
        if getattr(self.main_window, "_shutting_down", False):
            return
        if self._memory_monitor_running:
            return

        # 崩溃保护：如果短时间内反复触发启动，说明上次线程崩溃了，延长重试间隔
        now = time.time()
        crash_guard_key = "_last_monitor_start_attempt"
        last_attempt = getattr(self, crash_guard_key, 0.0)
        if now - last_attempt < 5.0:
            return  # 5 秒内不重复启动，防止崩溃-重启循环
        setattr(self, crash_guard_key, now)

        def _monitor_once():
            self._trim_preload_if_needed()
            self._trim_main_caches_if_needed()
            self._apply_background_policy()

        def memory_monitor_worker():
            self._memory_monitor_running = True
            try:
                while self._memory_monitor_running:
                    time.sleep(10)
                    if not self._memory_monitor_running or getattr(self.main_window, "_shutting_down", False):
                        break
                    try:
                        _monitor_once()
                    except Exception:
                        logger.debug("Memory monitor cycle failed", exc_info=True)
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
                if desired_conc in (1, 2) and (
                    not hasattr(self, "_decode_semaphore")
                    or getattr(self._decode_semaphore, "_value", None) != desired_conc
                ):
                    self._decode_semaphore = threading.BoundedSemaphore(value=desired_conc)

                # 应用预取窗口
                if hasattr(self, "bidi_pool") and self.bidi_pool:
                    if isinstance(desired_preload, int) and 1 <= desired_preload <= 8:
                        with contextlib.suppress(Exception):
                            self.bidi_pool.set_preload_window(preload_count=desired_preload)
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

            # 清空 HOT3 强引用锁（切换文件夹时主动释放）
            self._hot3_lock.clear()

            # 设置新序列
            self.bidi_pool.set_sequence(images)

            # 记录同步时间，用于后续预加载优化
            self._last_sequence_sync = time.time()

            logger.debug("双向缓存池已同步，图像数量: %s", len(images))

            # 立即触发预加载重建，确保后续导航流畅
            self._trigger_immediate_preload_rebuild()

        except Exception as e:
            logger.warning("同步双向缓存池失败: %s", e)

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
                    logger.debug("预加载重建失败: %s", e)

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
            logger.debug("触发预加载重建失败: %s", e)

    def _execute_delayed_preload_rebuild_(self, timer):
        """执行延迟的预加载重建（NSTimer回调）"""
        try:
            if hasattr(self, "_delayed_preload_func"):
                self._delayed_preload_func()
                delattr(self, "_delayed_preload_func")
        except Exception as e:
            logger.debug("执行延迟预加载重建失败: %s", e)

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
        self.shutdown()

    def shutdown(self):
        """关闭图像管理器并释放资源"""
        try:
            # 取消渲染节流待定定时器
            if self._pending_timer is not None:
                self._pending_timer.cancel()
                self._pending_timer = None
                self._pending_image = None
            # 清空 HOT3 强引用锁
            self._hot3_lock.clear()
            self._memory_monitor_running = False
            if hasattr(self, "_executor"):
                self._executor.shutdown(wait=False)
            if hasattr(self, "_prefetch_executor"):
                self._prefetch_executor.shutdown(wait=False)
            if self.hybrid_processor:
                stopper = getattr(self.hybrid_processor, "stop_processing", None)
                if callable(stopper):
                    stopper(wait=False)
            if self.bidi_pool:
                self.bidi_pool.shutdown()
        except Exception:
            pass

    def __del__(self):
        with contextlib.suppress(Exception):
            if hasattr(self, "_executor"):
                self._executor.shutdown(wait=False)
            if hasattr(self, "_prefetch_executor"):
                self._prefetch_executor.shutdown(wait=False)

    @staticmethod
    def _compute_cache_params() -> tuple[int, float]:
        """根据系统物理内存自适应计算缓存参数

        规则：
        - 预算 = 物理内存 × 30%，下限 2048MB，上限 4096MB
        - max_items = 预算 ÷ 96MB（单张 6000×4000 照片像素内存）
        - 低功耗模式削减 25%

        Returns:
            (max_items, max_memory_mb)
        """
        try:
            from Foundation import NSProcessInfo

            process_info = NSProcessInfo.processInfo()
            phys_mb = process_info.physicalMemory() / (1024 * 1024)
        except Exception:
            phys_mb = 8192  # 默认 8GB

        budget = phys_mb * 0.30
        budget = max(2048.0, min(4096.0, budget))

        try:
            if process_info.isLowPowerModeEnabled():
                budget *= 0.75
        except Exception:
            pass

        max_items = max(20, int(budget / 96))  # 96MB ≈ 6000×4000 × 4 bytes
        logger.info(
            "物理内存 %.0fMB → 缓存预算 %.0fMB, max_items=%d",
            phys_mb,
            budget,
            max_items,
        )
        return max_items, budget

    def _compute_nav_velocity(self) -> float:
        """计算最近导航速度（张/秒）

        基于最近 5 次导航事件的时间间隔计算加权速度。
        用于自适应渲染节流和预取窗口。

        Returns:
            速度（张/秒），无历史数据时返回 0
        """
        try:
            if len(self._nav_history) < 2:
                return 0.0
            # 取最近 5 个时间戳（最多）
            recent = [t for t, _ in self._nav_history[-6:]]
            if len(recent) < 2:
                return 0.0
            # 时间跨度 / 间隔数
            total_dt = recent[-1] - recent[0]
            if total_dt <= 0:
                return 0.0
            return (len(recent) - 1) / total_dt
        except Exception:
            return 0.0
