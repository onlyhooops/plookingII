import os

"""
文件夹管理器

负责处理文件夹扫描、导航、历史记录等逻辑。
"""

import concurrent.futures
import contextlib
import logging
import shutil
import threading

from AppKit import NSAlert, NSApplication

from ...config.constants import APP_NAME, IMAGE_PROCESSING_CONFIG, SUPPORTED_IMAGE_EXTS
from ...config.ui_strings import get_ui_string
from ...core.history import TaskHistoryManager
from ...core.simple_cache import estimate_image_memory_mb
from ...imports import logging, os, threading, time
from ...monitor import get_perf_tracker, perf_timed
from ...services.recent import RecentFoldersManager

logger = logging.getLogger(APP_NAME)


class FolderManager:
    """文件夹管理器，负责文件夹扫描、导航和历史记录"""

    def __init__(self, main_window):
        """初始化文件夹管理器

        Args:
            main_window: MainWindow实例
        """
        self.main_window = main_window

        # 任务历史管理器
        self.task_history_manager = None

        # 最近文件夹管理器
        self.recent_folders_manager = RecentFoldersManager()

        # 启动时清理无效的最近文件夹记录
        try:
            cleaned_count = self.recent_folders_manager.cleanup_invalid_entries()
            if cleaned_count > 0:
                logger.info("启动时清理了 %s 个无效的最近文件夹记录", cleaned_count)
        except Exception:
            logger.debug("启动时清理最近文件夹记录失败", exc_info=True)

        # 文件夹倒序浏览开关
        self.reverse_folder_order = False

        # 跳过文件夹历史记录机制
        self._skipped_folders_history = []
        self._max_skip_history = 10

        # 是否为“单文件夹模式”：仅当选择的根路径不包含任何子目录（os.walk 只返回根目录本身）
        self.single_folder_mode = False

        # 根目录异步加载代次：防止连续拖放/打开时过期扫描结果覆盖新状态
        self._load_root_generation = 0

        # 文件夹跳转异步加载代次：防止快速跨界翻页时过期结果覆盖新状态
        self._folder_jump_generation = 0

        # 当前正在展示的历史恢复弹窗（sheet 模式需要持有引用，避免被释放）
        self._active_history_alert = None

        # 轻量性能跟踪（聚合统计 + 会话报告）
        self.perf = get_perf_tracker()

    def _load_images_without_history_dialog(self, root_folder):
        """从根文件夹加载图像（不显示历史记录恢复对话框）

        用于侧栏导航，避免每次切换目录都弹出历史记录恢复对话框

        Args:
            root_folder: 根文件夹路径
        """
        self._load_root_async(root_folder, restore_history=False)

    def load_images_from_root(self, root_folder):
        """从根文件夹加载图像

        Args:
            root_folder: 根文件夹路径
        """
        self._load_root_async(root_folder, restore_history=True)

    def _load_root_async(self, root_folder, restore_history):
        """异步从根文件夹加载图像（两阶段惰性扫描）

        阶段1（快速首帧）：仅扫描根目录直系子文件夹，立即显示首个有图片的文件夹。
        阶段2（深度补全）：后台完成整棵目录树的深层遍历，追加/更新 subfolders 列表。

        主线程只做轻量状态更新并立即返回；目录树扫描、数据库写入在后台
        线程执行，完成后投递回主线程继续加载首个子文件夹。

        Args:
            root_folder: 根文件夹路径
            restore_history: 是否检查并提示恢复历史记录
        """
        self.main_window.root_folder = root_folder
        self._load_root_generation += 1
        gen = self._load_root_generation

        # 立即反馈，窗口保持可交互
        try:
            folder_name = os.path.basename(root_folder)
            self.main_window.status_bar_controller.set_status_message(f"正在扫描: {folder_name} ...")
        except Exception:
            pass

        def scan_worker():
            """后台线程：两阶段扫描"""
            thm = None
            try:
                # 初始化任务历史管理器（SQLite 建库/建表，I/O 操作）
                thm = TaskHistoryManager(root_folder)
                thm.add_recent_folder(root_folder)
                self.recent_folders_manager.add(root_folder)

                # 阶段1：快速扫描 —— 仅根目录 + 直系子文件夹（单层 os.listdir）
                exts = SUPPORTED_IMAGE_EXTS
                shallow_subfolders = self._shallow_scan(root_folder, exts)
                self._last_scanned_dir_count = len(shallow_subfolders) if shallow_subfolders else 1
                single_folder_mode = self._last_scanned_dir_count == 1

                if shallow_subfolders:
                    # 阶段1路径同样需要检查历史记录：
                    # 若此处跳过，快速路径将始终从第一个文件夹/第一张图片开始，
                    # 历史进度恢复功能形同虚设。这里在后台线程预读，避免阻塞主线程。
                    history_data = thm.load_task_progress() if restore_history else None

                    # 立即在后台线程加载首个子文件夹的图片，投递到主线程显示
                    first_folder = shallow_subfolders[0]
                    first_images = self._load_folder_images(first_folder)

                    def show_first_then_scan_deep():
                        if gen != self._load_root_generation:
                            return
                        # 快速路径同样绑定任务历史管理器，否则浏览进度不会被保存
                        self.task_history_manager = thm
                        self.main_window.subfolders = shallow_subfolders
                        self.single_folder_mode = single_folder_mode

                        # 存在有效历史记录时，优先询问是否恢复
                        # （与 _finish_load_from_root 的完整扫描路径行为保持一致）
                        if restore_history and history_data and self._validate_task_history(history_data):
                            self.main_window.current_subfolder_index = 0
                            self.main_window.current_index = 0
                            # 阶段2：后台深度扫描照常进行，用户做出选择后再合并完整列表
                            threading.Thread(target=deep_scan_completion, daemon=True).start()
                            self._show_task_history_restore_dialog(history_data)
                            return

                        # 设置首帧状态
                        self.main_window.current_subfolder_index = 0
                        self.main_window.current_folder = first_folder
                        self.main_window.images = first_images
                        self.main_window.current_index = 0
                        # 惰性记录 keep_folder 路径
                        base_dir = first_folder or root_folder or ""
                        self.main_window.keep_folder = (
                            os.path.join(base_dir, self._compute_selection_folder_name(base_dir)) if base_dir else ""
                        )
                        # 触发图片显示（self.load_current_subfolder 是 FolderManager 方法）
                        self.load_current_subfolder(restore_index=0, async_first_load=False)
                        self.main_window.status_bar_controller.set_status_message(
                            f"已加载: {os.path.basename(first_folder)} （深度扫描中...）"
                        )
                        # 阶段2：后台深度扫描
                        threading.Thread(target=deep_scan_completion, daemon=True).start()

                    # 阶段2：深度遍历整棵目录树，完成后合并 subfolders
                    def deep_scan_completion():
                        try:
                            if gen != self._load_root_generation:
                                return
                            full_subfolders = self._scan_subfolders(root_folder)
                            self._last_scanned_dir_count = len(self._gather_directories_to_scan(root_folder))
                            full_single_mode = self._last_scanned_dir_count == 1

                            if full_subfolders:
                                full_subfolders = self._filter_selection_folders(full_subfolders)

                            def merge_results():
                                if gen != self._load_root_generation:
                                    return
                                # 合并：保留当前浏览进度，更新 subfolders
                                old_index = getattr(self.main_window, "current_subfolder_index", 0)
                                old_path = getattr(self.main_window, "current_folder", "")
                                self.main_window.subfolders = full_subfolders
                                self.single_folder_mode = full_single_mode
                                # 尝试恢复当前浏览位置
                                try:
                                    if old_path and old_path in full_subfolders:
                                        self.main_window.current_subfolder_index = full_subfolders.index(old_path)
                                    else:
                                        self.main_window.current_subfolder_index = min(
                                            old_index, len(full_subfolders) - 1
                                        )
                                except Exception:
                                    self.main_window.current_subfolder_index = 0
                                self.main_window.status_bar_controller.set_status_message(
                                    f"扫描完成: {len(full_subfolders)} 个文件夹"
                                )
                                try:
                                    self.main_window._update_status_display_immediate()
                                except Exception:
                                    pass
                                # 合并完成后持久化完整文件夹列表，保证下次打开时进度可恢复
                                self._save_task_progress_immediate()

                            self._post_to_main(merge_results)
                        except Exception:
                            logger.exception("深度扫描补全失败")

                    self._post_to_main(show_first_then_scan_deep)
                else:
                    # 直系无图片，走完整扫描路径
                    subfolders = self._scan_subfolders(root_folder)
                    single_folder_mode = getattr(self, "_last_scanned_dir_count", 0) == 1
                    self._post_to_main(
                        lambda: self._finish_load_from_root(
                            gen, root_folder, subfolders, single_folder_mode, restore_history, thm
                        )
                    )
            except Exception:
                logger.exception("后台扫描文件夹失败: %s", root_folder)
                subfolders = []
                single_folder_mode = False
                self._post_to_main(
                    lambda: self._finish_load_from_root(
                        gen, root_folder, subfolders, single_folder_mode, restore_history, thm
                    )
                )

        threading.Thread(target=scan_worker, daemon=True).start()

    def _finish_load_from_root(
        self, gen, root_folder, subfolders, single_folder_mode, restore_history, task_history_manager=None
    ):
        """后台扫描完成后在主线程执行的收尾逻辑

        Args:
            gen: 发起扫描时的代次，过期结果直接丢弃
            root_folder: 根文件夹路径
            subfolders: 扫描到的含图片子文件夹列表
            single_folder_mode: 是否单文件夹模式
            restore_history: 是否检查并提示恢复历史记录
            task_history_manager: 后台线程创建的任务历史管理器
        """
        # 过期结果（用户已拖入/打开新文件夹）直接丢弃
        if gen != self._load_root_generation or root_folder != self.main_window.root_folder:
            logger.debug("丢弃过期的文件夹扫描结果: %s", root_folder)
            return

        self.task_history_manager = task_history_manager

        # 更新最近打开菜单（主线程 UI 操作）
        self.main_window.updateRecentMenu_()

        # 统一过滤：移除任意层级的"精选"目录，确保导航不会跳入精选文件夹
        subfolders = self._filter_selection_folders(subfolders)
        self.main_window.subfolders = subfolders
        self.single_folder_mode = single_folder_mode

        if not self.main_window.subfolders:
            self.main_window.image_view.setImage_(None)
            if hasattr(self.main_window, "image_seq_label") and self.main_window.image_seq_label:
                self.main_window.image_seq_label.setStringValue_("无图片 0/0")
            if hasattr(self.main_window, "folder_seq_label") and self.main_window.folder_seq_label:
                self.main_window.folder_seq_label.setStringValue_("0/0")
            return

        # 启动工作会话
        self._start_work_session()

        if restore_history and self.task_history_manager is not None:
            # 检查历史记录
            history_data = self.task_history_manager.load_task_progress()
            if history_data and self._validate_task_history(history_data):
                self._show_task_history_restore_dialog(history_data)
                return

        # 无历史记录/不恢复历史：从第一个文件夹开始（首图后台异步加载）
        self.main_window.current_subfolder_index = 0
        self.main_window.current_index = 0
        self.load_current_subfolder(async_first_load=True)

    @staticmethod
    def _post_to_main(func):
        """将函数调度到主线程执行"""
        try:
            from Foundation import NSOperationQueue

            NSOperationQueue.mainQueue().addOperationWithBlock_(func)
        except Exception:
            try:
                func()
            except Exception:
                logger.debug("_post_to_main failed", exc_info=True)

    def _start_work_session(self):
        """启动工作会话"""
        try:
            if hasattr(self.main_window, "status_bar_controller") and (self.main_window.status_bar_controller):
                # 启动状态栏控制器的会话管理
                self.main_window.status_bar_controller.start_work_session()

                # 设置会话数据 - 保留基础会话跟踪
                if self.main_window.subfolders:
                    self.main_window.status_bar_controller.session_manager.set_folder_count(
                        len(self.main_window.subfolders)
                    )

                logger.info("工作会话已启动")

        except Exception:
            logger.exception("启动工作会话时发生错误")

    def _end_work_session(self):
        """结束工作会话"""
        try:
            if hasattr(self.main_window, "status_bar_controller") and (self.main_window.status_bar_controller):
                self.main_window.status_bar_controller.end_work_session()
                logger.info("工作会话已结束")

        except Exception:
            logger.exception("结束工作会话时发生错误")

    def _scan_subfolders(self, root_folder):
        """并行化扫描所有包含图片的子文件夹

        Args:
            root_folder: 根文件夹路径

        Returns:
            list: 包含图片的子文件夹列表
        """
        scan_start = time.perf_counter()
        exts = SUPPORTED_IMAGE_EXTS
        subfolders = []
        scan_lock = threading.Lock()
        scan_success = True

        try:
            directories_to_scan = self._gather_directories_to_scan(root_folder)
            # 记录目录总数，供调用方判断单文件夹模式（避免再次 os.walk 整棵树）
            self._last_scanned_dir_count = len(directories_to_scan)
            if not directories_to_scan:
                return []

            # 执行并行扫描
            self._execute_parallel_scan(directories_to_scan, exts, subfolders, scan_lock)

            # 排序并返回结果（按文件夹名升序，不区分大小写）
            try:
                subfolders.sort(key=lambda p: os.path.basename(p).lower(), reverse=self.reverse_folder_order)
            except Exception:
                subfolders.sort(reverse=self.reverse_folder_order)
            return subfolders
        except Exception:
            scan_success = False
            raise
        finally:
            # 轻量性能跟踪：整棵目录树扫描耗时
            self.perf.record(
                "folder_scan",
                (time.perf_counter() - scan_start) * 1000,
                success=scan_success,
                folders=len(subfolders),
            )

    def _execute_parallel_scan(self, directories_to_scan, exts, subfolders, scan_lock):
        """执行并行目录扫描

        Args:
            directories_to_scan: 要扫描的目录列表
            exts: 支持的图片扩展名
            subfolders: 结果列表
            scan_lock: 线程锁
        """

        def scan_directory(dirpath):
            try:
                if self._dir_contains_images(dirpath, exts):
                    with scan_lock:
                        subfolders.append(dirpath)
            except Exception:
                # 忽略无法访问或扫描失败的目录
                pass

        max_workers = min(16, len(directories_to_scan))
        if max_workers > 1:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                executor.map(scan_directory, directories_to_scan)
        else:
            for dirpath in directories_to_scan:
                scan_directory(dirpath)

    def _gather_directories_to_scan(self, root_folder):
        """收集所有需要扫描的目录（跳过当前层级的“精选”目录）

        Args:
            root_folder: 根文件夹路径

        Returns:
            list: 需要扫描的目录列表
        """
        directories_to_scan = []
        for dirpath, dirnames, _ in os.walk(root_folder):
            # 跳过与当前父级目录名匹配的精选目录，例如 父/父 精选
            parent_name = os.path.basename(dirpath) if dirpath else ""
            selection_name = f"{parent_name} 精选" if parent_name else "精选"
            # 双层过滤：精确匹配 + 通用“精选/精選”后缀（覆盖简繁变体）
            dirnames[:] = [d for d in dirnames if d != selection_name and not d.endswith(("精选", "精選"))]
            directories_to_scan.append(dirpath)
        return directories_to_scan

    def _shallow_scan(self, root_folder: str, exts: tuple) -> list:
        """快速浅层扫描：仅检查根目录及直系子文件夹（单层，不递归）

        用于两阶段扫描的阶段1，在大目录树下提供毫秒级首帧。
        跳过的深层子文件夹在阶段2的完整 os.walk 中补全。

        Args:
            root_folder: 根文件夹路径
            exts: 支持的图片扩展名

        Returns:
            包含图片的文件夹列表（含根目录自身，若有图片）
        """
        result = []
        # 1. 检查根目录自身
        if self._dir_contains_images(root_folder, exts):
            result.append(root_folder)
        # 2. 检查直系子文件夹（单层，使用 os.scandir 极快）
        try:
            with os.scandir(root_folder) as entries:
                for entry in entries:
                    if not entry.is_dir() or entry.name.startswith("."):
                        continue
                    # 跳过精选目录（与精選，覆盖简繁变体）
                    if entry.name.endswith(("精选", "精選")):
                        continue
                    if self._dir_contains_images(entry.path, exts):
                        result.append(entry.path)
        except (OSError, PermissionError):
            pass
        # 排序以保证确定顺序
        result.sort(key=lambda p: os.path.basename(p).lower())
        return result

    def _dir_contains_images(self, dirpath, exts):
        """判断目录是否包含图片

        优先走目录级布尔缓存：深度扫描阶段每个目录只枚举一次，
        重复判断（浅扫/深扫重叠、邻目录预扫描）直接命中缓存，
        避免对同一目录反复全量枚举。

        Args:
            dirpath: 目录路径
            exts: 支持的图片扩展名

        Returns:
            bool: 是否包含图片
        """
        try:
            # 使用批量文件信息加载器优化 I/O（含目录级含图布尔缓存）
            from ...core.file_info_batch_loader import get_file_info_loader

            loader = get_file_info_loader()
            return loader.directory_contains_images(dirpath, filter_exts=exts)
        except (OSError, PermissionError):
            return False
        except Exception:
            # 回退到旧方法
            try:
                return any(f.lower().endswith(exts) for f in os.listdir(dirpath))
            except (OSError, PermissionError):
                return False

    def load_current_subfolder(self, restore_index=None, async_first_load=False):
        """加载当前子文件夹的图片，支持恢复到指定图片索引

        Args:
            restore_index: 要恢复的图片索引
            async_first_load: 首图是否强制后台异步加载（拖放/打开文件夹后
                首图必然缓存未命中，异步可避免主线程同步解码卡顿）
        """
        if (
            not self.main_window.subfolders
            or self.main_window.current_subfolder_index >= len(self.main_window.subfolders)
            or self.main_window.current_subfolder_index < 0
        ):
            return

        # 如果是恢复历史记录，直接使用当前文件夹和图片列表，不重新扫描
        if restore_index is not None:
            # 恢复模式：使用已有的current_folder和images
            if hasattr(self.main_window, "current_folder") and self.main_window.current_folder:
                # 验证当前文件夹是否仍然存在
                if not os.path.exists(self.main_window.current_folder):
                    # 文件夹不存在，回退到正常加载模式
                    if not self._move_to_next_nonempty_folder():
                        return
                else:
                    # 文件夹存在，重新加载图片列表以确保一致性
                    self.main_window.images = self._load_folder_images(self.main_window.current_folder)
                    if not self.main_window.images:
                        # 当前文件夹没有图片，寻找下一个非空文件夹
                        if not self._move_to_next_nonempty_folder():
                            return
            # 没有current_folder信息，使用正常加载模式
            elif not self._move_to_next_nonempty_folder():
                return
        # 正常模式：寻找下一个非空子文件夹
        elif not self._move_to_next_nonempty_folder():
            return

        # 惰性创建：不在加载文件夹时创建“精选”目录，仅记录预期路径
        base_dir = self.main_window.current_folder or self.main_window.root_folder or ""
        self.main_window.keep_folder = (
            os.path.join(base_dir, self._compute_selection_folder_name(base_dir)) if base_dir else ""
        )

        # 恢复历史索引，否则始终从第一张图片开始
        if restore_index is not None and 0 <= restore_index < len(self.main_window.images):
            self.main_window.current_index = restore_index
        else:
            self.main_window.current_index = 0

        # 同步双向缓存池序列（切换文件夹时重置窗口）
        self.main_window.image_manager.sync_bidi_sequence(self.main_window.images)

        # 预热尺寸元数据（后台，不阻塞 UI）
        with contextlib.suppress(Exception):
            self.main_window.image_manager.prewarm_dimensions(self.main_window.images)

        # 预热相邻文件夹图片列表，跨界跳转直接命中目录缓存
        self._prefetch_neighbor_folder_lists()

        # 优化：预加载第一张图片到缓存，减少显示延迟
        if self.main_window.images and (self.main_window.current_index < len(self.main_window.images)):
            first_image_path = self.main_window.images[self.main_window.current_index]
            try:
                file_size_mb = self.main_window.image_manager.image_cache.get_file_size_mb(first_image_path)
                fast_threshold = IMAGE_PROCESSING_CONFIG.get("fast_load_threshold", 50)
                if file_size_mb <= fast_threshold and (IMAGE_PROCESSING_CONFIG.get("fast_load_enabled", True)):
                    # 小文件预加载到缓存
                    def preload_first_image():
                        try:
                            image = self.main_window.image_manager._load_image_optimized(
                                first_image_path, target_size=None
                            )
                            if image:
                                # 将图片放入缓存，供后续显示使用
                                self.main_window.image_manager._get_target_size_for_view(scale_factor=2)
                                size_mb = estimate_image_memory_mb(image)
                                self.main_window.image_manager.image_cache.put(first_image_path, image, size_mb=size_mb)
                        except Exception:
                            logger.debug("Preload first image failed", exc_info=True)

                    # 后台预加载，不阻塞UI
                    threading.Thread(target=preload_first_image, daemon=True).start()
            except Exception:
                logger.debug("Failed to check file size for preload", exc_info=True)

        self.main_window.image_manager.show_current_image(async_first_load=async_first_load)
        self._save_task_progress_immediate()

    def _move_to_next_nonempty_folder(self):
        """推进到下一个包含图片的子文件夹

        子文件夹列表已按浏览顺序排序（升序或降序取决于 reverse_folder_order），
        因此始终向前（+1方向）查找。

        Returns:
            bool: 找到非空文件夹返回True，否则返回False
        """
        idx = self.main_window.current_subfolder_index
        n = len(self.main_window.subfolders)

        # 循环查找包含图片的文件夹（跳过精选目录）
        while 0 <= idx < n:
            folder = self.main_window.subfolders[idx]
            if self._is_selection_folder(folder):
                idx += 1
                continue
            images = self._load_folder_images(folder)
            if images:  # 找到包含图片的文件夹
                self.main_window.current_subfolder_index = idx
                self.main_window.current_folder = folder
                self.main_window.images = images
                return True
            idx += 1
        return False

    def _load_folder_images(self, folder_path):
        """加载指定文件夹中的所有图片文件

        Args:
            folder_path: 文件夹路径

        Returns:
            list: 图片文件的完整路径列表，按文件名排序
        """
        exts = SUPPORTED_IMAGE_EXTS
        images = []

        try:
            # 使用批量文件信息加载器优化 I/O 性能（含目录级列表缓存，
            # 跳转/跳过/回退文件夹时避免重复枚举与排序）
            from ...core.file_info_batch_loader import get_file_info_loader

            loader = get_file_info_loader()
            return loader.get_directory_images(folder_path, filter_exts=exts)
        except Exception:
            # 文件夹访问失败时返回空列表
            # 回退到旧方法（兼容性）
            try:
                for filename in os.listdir(folder_path):
                    if filename.lower().endswith(exts):
                        image_path = os.path.join(folder_path, filename)
                        images.append(image_path)
                images.sort()
                return images
            except Exception:
                return []

    def _is_selection_folder(self, folder_path: str) -> bool:
        """检测给定路径是否为“精选”目录（不应作为导航目标）

        Args:
            folder_path: 目录路径

        Returns:
            bool: True 表示该目录为精选目录，应跳过
        """
        try:
            name = os.path.basename(folder_path.rstrip(os.sep))
            # 覆盖简/繁中日韩变体
            return name.endswith(("精选", "精選"))
        except Exception:
            return False

    def jump_to_next_folder(self, _recursion_depth: int = 0):
        """跳转到下一个文件夹的第一张图片，支持父级目录同级文件夹切换"""
        if _recursion_depth > 100:
            logger.warning("jump_to_next_folder: 递归深度超限(%s)，终止跳转", _recursion_depth)
            return

        if not self.main_window.subfolders:
            return

        # 首先尝试在当前根目录的子文件夹中切换
        if self.reverse_folder_order:
            next_folder_idx = self.main_window.current_subfolder_index - 1
        else:
            next_folder_idx = self.main_window.current_subfolder_index + 1

        if 0 <= next_folder_idx < len(self.main_window.subfolders):
            # 后台异步加载目标文件夹图片列表，避免大文件夹/网络盘在主线程全量枚举
            self._start_async_folder_load(
                next_folder_idx,
                direction=-1 if self.reverse_folder_order else +1,
                start_from_last=False,
            )
            return

        # 如果当前根目录没有更多文件夹，尝试切换到父级目录的同级文件夹（仅在单文件夹模式启用）
        current_folder = self.main_window.current_folder
        if current_folder and self.single_folder_mode:
            success, next_folder, parent_dir = self._move_to_next_sibling_folder(current_folder)
            if success:
                # 切换到同级文件夹
                self._load_sibling_folder(next_folder, parent_dir)
            elif parent_dir:
                # 没有更多同级文件夹，显示完成消息
                self._show_completion_message(parent_dir)
        # 非单文件夹模式不启用同级跳转
        elif current_folder:
            parent_dir = os.path.dirname(current_folder)
            self._show_completion_message(parent_dir)

    def _start_async_folder_load(self, start_index: int, direction: int, start_from_last: bool = False):
        """后台异步加载目标文件夹（含自动跳过空文件夹），完成后投递回主线程

        将原本在主线程同步执行的 _load_folder_images 全量枚举+排序移到后台线程，
        大文件夹/网络盘场景下跨界翻页不再冻结 UI。代次保护防止快速连续
        跳转时过期结果覆盖新状态。

        Args:
            start_index: 起始文件夹索引
            direction: 跳过空文件夹的搜索方向（+1/-1）
            start_from_last: True 表示进入文件夹后从最后一张图片开始（向前跳转）
        """
        self._folder_jump_generation += 1
        gen = self._folder_jump_generation

        def scan_worker():
            jump_start = time.perf_counter()
            try:
                subfolders = list(self.main_window.subfolders or [])
                idx = start_index
                found = None
                while 0 <= idx < len(subfolders):
                    if gen != self._folder_jump_generation:
                        return  # 过期跳转，丢弃
                    folder = subfolders[idx]
                    if not self._is_selection_folder(folder):
                        images = self._load_folder_images(folder)
                        if images:
                            found = (idx, folder, images)
                            break
                    idx += direction

                def apply():
                    if gen != self._folder_jump_generation:
                        return
                    if found is None:
                        # 轻量性能跟踪：边界处理（完成消息/同级切换）
                        self.perf.record("folder_jump", (time.perf_counter() - jump_start) * 1000, found=False)
                        # 当前根目录内无更多含图文件夹：沿用原有边界逻辑
                        self._handle_folder_jump_boundary()
                        return
                    target_idx, folder, images = found
                    self.main_window.current_subfolder_index = target_idx
                    self.main_window.current_folder = folder
                    self.main_window.images = images
                    self.main_window.current_index = len(images) - 1 if start_from_last else 0
                    # 惰性创建：仅记录预期“精选”目录路径，不落盘创建
                    base_dir = folder or self.main_window.root_folder or ""
                    self.main_window.keep_folder = (
                        os.path.join(base_dir, self._compute_selection_folder_name(base_dir)) if base_dir else ""
                    )
                    # 同步双向缓存池序列
                    self.main_window.image_manager.sync_bidi_sequence(self.main_window.images)
                    # 预热尺寸元数据（后台，不阻塞 UI）
                    with contextlib.suppress(Exception):
                        self.main_window.image_manager.prewarm_dimensions(self.main_window.images)
                    # 跨文件夹首图使用后台异步加载，避免主线程阻塞
                    self.main_window.image_manager.show_current_image(async_first_load=True)
                    self._save_task_progress_immediate()
                    # 预热相邻文件夹图片列表，下次跨界跳转直接命中目录缓存
                    self._prefetch_neighbor_folder_lists()
                    # 轻量性能跟踪：跨文件夹跳转端到端耗时（按键 → 首图显示）
                    self.perf.record("folder_jump", (time.perf_counter() - jump_start) * 1000, found=True)

                self._post_to_main(apply)
            except Exception:
                logger.exception("后台加载文件夹失败")

        threading.Thread(target=scan_worker, daemon=True).start()

    def _handle_folder_jump_boundary(self):
        """文件夹跳转边界处理（沿用原有同步逻辑：同级文件夹或完成消息）"""
        current_folder = self.main_window.current_folder
        if current_folder and self.single_folder_mode:
            success, next_folder, parent_dir = self._move_to_next_sibling_folder(current_folder)
            if success:
                self._load_sibling_folder(next_folder, parent_dir)
            elif parent_dir:
                self._show_completion_message(parent_dir)
        elif current_folder:
            parent_dir = os.path.dirname(current_folder)
            self._show_completion_message(parent_dir)

    def _prefetch_neighbor_folder_lists(self):
        """后台预热相邻文件夹的图片列表（写入目录级缓存）

        进入某文件夹后立即在后台扫描上一个/下一个同级文件夹的图片列表，
        使跨界翻页时 _load_folder_images 直接命中 DirectoryImageListCache，
        跳过全量枚举与排序。
        """
        try:
            subfolders = getattr(self.main_window, "subfolders", None) or []
            if len(subfolders) <= 1:
                return
            cur_idx = getattr(self.main_window, "current_subfolder_index", 0)
            targets = []
            if 0 <= cur_idx - 1 < len(subfolders):
                targets.append(subfolders[cur_idx - 1])
            if 0 <= cur_idx + 1 < len(subfolders):
                targets.append(subfolders[cur_idx + 1])
            if not targets:
                return

            def warm_worker():
                for folder in targets:
                    if self._is_selection_folder(folder):
                        continue
                    try:
                        self._load_folder_images(folder)
                    except Exception:
                        pass

            threading.Thread(target=warm_worker, daemon=True).start()
        except Exception:
            pass

    @perf_timed("folder_sibling", direction="next")
    def _load_sibling_folder(self, folder_path, parent_dir):
        """加载同级文件夹

        Args:
            folder_path: 文件夹路径
            parent_dir: 父级目录路径
        """
        # 防御性检查：确保不会加载精选目录
        if self._is_selection_folder(folder_path):
            logger.warning("_load_sibling_folder: 拒绝加载精选目录 %s，跳过", folder_path)
            success, next_folder, _ = self._move_to_next_sibling_folder(folder_path)
            if success:
                self._load_sibling_folder(next_folder, parent_dir)
            else:
                self._show_completion_message(parent_dir)
            return

        # 扫描新文件夹中的图片
        images = self._load_folder_images(folder_path)
        if not images:
            # 如果新文件夹没有图片，继续寻找下一个
            success, next_folder, _ = self._move_to_next_sibling_folder(folder_path)
            if success:
                self._load_sibling_folder(next_folder, parent_dir)
            else:
                self._show_completion_message(parent_dir)
            return

        # 更新状态
        self.main_window.current_folder = folder_path
        self.main_window.images = images
        self.main_window.current_index = 0
        # 惰性创建：仅记录预期“精选”目录路径
        self.main_window.keep_folder = os.path.join(folder_path, self._compute_selection_folder_name(folder_path))
        # 同步双向缓存池序列
        self.main_window.image_manager.sync_bidi_sequence(self.main_window.images)
        # 跨文件夹首图使用后台异步加载，避免主线程阻塞
        self.main_window.image_manager.show_current_image(async_first_load=True)
        self._save_task_progress_immediate()

        # 更新状态栏显示
        folder_name = os.path.basename(folder_path)
        self.main_window.status_bar_controller.set_status_message(f"已切换到同级文件夹: {folder_name}")

    def _show_completion_message(self, parent_dir):
        """显示任务完成消息

        Args:
            parent_dir: 父级目录路径
        """
        parent_name = os.path.basename(parent_dir) if parent_dir else "目录"
        self.main_window.status_bar_controller.set_status_message(f"{parent_name} 下的所有文件夹已浏览完毕！")

        # 清空图片列表
        self.main_window.images = []
        self.main_window.current_index = 0
        self.main_window.image_view.setImage_(None)

    def jump_to_previous_folder(self, _recursion_depth: int = 0):
        """跳转到上一个文件夹的最后一张图片，支持父级目录同级文件夹切换"""
        if _recursion_depth > 100:
            logger.warning("jump_to_previous_folder: 递归深度超限(%s)，终止跳转", _recursion_depth)
            return

        if not self.main_window.subfolders:
            return

        # 首先尝试在当前根目录的子文件夹中切换
        if self.reverse_folder_order:
            prev_folder_idx = self.main_window.current_subfolder_index + 1
        else:
            prev_folder_idx = self.main_window.current_subfolder_index - 1

        if 0 <= prev_folder_idx < len(self.main_window.subfolders):
            # 后台异步加载目标文件夹图片列表，避免大文件夹/网络盘在主线程全量枚举
            self._start_async_folder_load(
                prev_folder_idx,
                direction=+1 if self.reverse_folder_order else -1,
                start_from_last=True,
            )
            return

        # 如果当前根目录没有更多文件夹，尝试切换到父级目录的同级文件夹（仅在单文件夹模式启用）
        current_folder = self.main_window.current_folder
        if current_folder and self.single_folder_mode:
            success, prev_folder, parent_dir = self._move_to_previous_sibling_folder(current_folder)
            if success:
                # 切换到同级文件夹
                self._load_previous_sibling_folder(prev_folder, parent_dir)
        # 非单文件夹模式不启用同级跳转
        elif current_folder:
            parent_dir = os.path.dirname(current_folder)
            self._show_completion_message(parent_dir)

    def _move_to_previous_sibling_folder(self, current_folder):
        """移动到当前文件夹的上一个同级文件夹

        Args:
            current_folder: 当前文件夹路径

        Returns:
            tuple: (是否成功, 上一个同级文件夹路径, 父级目录路径)
        """
        parent_dir, sibling_folders = self._get_parent_sibling_folders(current_folder)
        if not sibling_folders:
            return False, None, None

        # 找到当前文件夹在同级列表中的位置
        try:
            current_index = sibling_folders.index(current_folder)
        except ValueError:
            return False, None, None

        # 计算上一个索引
        prev_index = current_index - 1
        if prev_index < 0:
            return False, None, parent_dir  # 没有上一个，但返回父级目录

        prev_folder = sibling_folders[prev_index]
        return True, prev_folder, parent_dir

    @perf_timed("folder_sibling", direction="prev")
    def _load_previous_sibling_folder(self, folder_path, parent_dir):
        """加载上一个同级文件夹

        Args:
            folder_path: 文件夹路径
            parent_dir: 父级目录路径
        """
        # 防御性检查：确保不会加载精选目录
        if self._is_selection_folder(folder_path):
            logger.warning("_load_previous_sibling_folder: 拒绝加载精选目录 %s，跳过", folder_path)
            success, prev_folder, _ = self._move_to_previous_sibling_folder(folder_path)
            if success:
                self._load_previous_sibling_folder(prev_folder, parent_dir)
            return

        # 扫描新文件夹中的图片
        images = self._load_folder_images(folder_path)
        if not images:
            # 如果新文件夹没有图片，继续寻找上一个
            success, prev_folder, _ = self._move_to_previous_sibling_folder(folder_path)
            if success:
                self._load_previous_sibling_folder(prev_folder, parent_dir)
            return

        # 更新状态
        self.main_window.current_folder = folder_path
        self.main_window.images = images
        # 从最后一张图片开始浏览
        self.main_window.current_index = len(images) - 1
        # 统一惰性策略：仅记录“精选”目录路径
        self.main_window.keep_folder = os.path.join(folder_path, self._compute_selection_folder_name(folder_path))
        # 同步双向缓存池序列
        self.main_window.image_manager.sync_bidi_sequence(self.main_window.images)
        # 跨文件夹首图使用后台异步加载，避免主线程阻塞
        self.main_window.image_manager.show_current_image(async_first_load=True)
        self._save_task_progress_immediate()

        # 更新状态栏显示
        folder_name = os.path.basename(folder_path)
        self.main_window.status_bar_controller.set_status_message(f"已切换到上一个同级文件夹: {folder_name}")

    def skip_current_folder(self):
        """跳过当前文件夹"""
        if not self.main_window.subfolders or len(self.main_window.subfolders) <= 1:
            self.main_window.status_bar_controller.set_status_message("无可跳过的文件夹")
            return

        # 记录当前文件夹到跳过历史
        current_folder_info = {
            "folder_index": self.main_window.current_subfolder_index,
            "folder_path": self.main_window.current_folder,
            "image_index": self.main_window.current_index,
        }

        # 添加到历史记录
        self._skipped_folders_history.append(current_folder_info)

        # 维护历史记录大小限制
        if len(self._skipped_folders_history) > self._max_skip_history:
            self._skipped_folders_history.pop(0)

        # 跳转到下一个文件夹
        folder_name = (
            os.path.basename(self.main_window.current_folder) if self.main_window.current_folder else "当前文件夹"
        )
        self.jump_to_next_folder()

        # 提供用户反馈
        self.main_window.status_bar_controller.set_status_message(f"已跳过文件夹: {folder_name}")

    def undo_skip_folder(self):
        """撤销跳过文件夹操作"""
        if not self._skipped_folders_history:
            self.main_window.status_bar_controller.set_status_message("无可撤销的跳过操作")
            return

        # 获取最近的跳过记录
        last_skipped = self._skipped_folders_history.pop()

        # 验证目标文件夹是否仍然存在
        target_folder_index = last_skipped["folder_index"]
        if target_folder_index >= len(self.main_window.subfolders):
            self.main_window.status_bar_controller.set_status_message("跳过的文件夹已不存在，无法撤销")
            return

        target_folder_path = self.main_window.subfolders[target_folder_index]
        if not os.path.exists(target_folder_path):
            self.main_window.status_bar_controller.set_status_message("跳过的文件夹已不存在，无法撤销")
            return

        # 恢复到跳过前的状态
        self.main_window.current_subfolder_index = target_folder_index
        self.main_window.current_folder = target_folder_path
        self.main_window.images = self._load_folder_images(self.main_window.current_folder)

        # 恢复图片索引（确保不超出范围）
        target_image_index = last_skipped["image_index"]
        if self.main_window.images and target_image_index < len(self.main_window.images):
            self.main_window.current_index = target_image_index
        else:
            self.main_window.current_index = 0

        # 更新精选文件夹路径（惰性记录）
        base_dir = self.main_window.current_folder or self.main_window.root_folder or ""
        self.main_window.keep_folder = (
            os.path.join(base_dir, self._compute_selection_folder_name(base_dir)) if base_dir else ""
        )

        # 同步双向缓存池序列
        self.main_window.image_manager.sync_bidi_sequence(self.main_window.images)

        # 显示恢复的图片
        self.main_window.image_manager.show_current_image()
        self._save_task_progress_immediate()

        # 提供用户反馈
        folder_name = os.path.basename(self.main_window.current_folder) if self.main_window.current_folder else "文件夹"
        self.main_window.status_bar_controller.set_status_message(f"已撤销跳过，返回到: {folder_name}")

    def _compute_selection_folder_name(self, base_dir: str) -> str:
        """计算“精选”目录的名称

        规则："[base_dir 的最后一段] 精选"
        """
        try:
            base_name = os.path.basename(base_dir.rstrip(os.sep)) if base_dir else ""
            return f"{base_name} 精选" if base_name else "精选"
        except Exception:
            return "精选"

    def _ensure_selection_folder(self, base_dir: str) -> str:
        """确保在 base_dir 下存在“精选”目录，包含从旧“保留”目录的迁移。

        - 如果存在旧目录 base_dir/保留，则迁移为 base_dir/[basename(base_dir) 精选]
        - 如果目标已存在，尝试将旧目录内容合并迁移，名称冲突自动编号
        - 若均不存在，则创建新“精选”目录
        返回：最终“精选”目录的绝对路径
        """
        try:
            if not base_dir:
                return ""
            selection_name = self._compute_selection_folder_name(base_dir)
            selection_dir = os.path.join(base_dir, selection_name)
            old_dir = os.path.join(base_dir, "保留")

            # 如果精选目录已存在
            if os.path.isdir(selection_dir):
                # 若旧目录仍存在，则尝试合并后删除
                if os.path.isdir(old_dir):
                    self._merge_and_remove_old_dir(old_dir, selection_dir)
                return selection_dir

            # 精选目录不存在，若旧目录存在则重命名/迁移
            if os.path.isdir(old_dir):
                try:
                    os.rename(old_dir, selection_dir)
                    return selection_dir
                except Exception:
                    # 回退为逐文件迁移
                    self._merge_and_remove_old_dir(old_dir, selection_dir)
                    return selection_dir

            # 两者都不存在，创建精选目录
            os.makedirs(selection_dir, exist_ok=True)
            return selection_dir
        except Exception:
            # 失败时返回预期路径（上层应容错）
            selection_name = self._compute_selection_folder_name(base_dir)
            return os.path.join(base_dir, selection_name)

    def _merge_and_remove_old_dir(self, src_dir: str, dst_dir: str) -> None:
        """将旧“保留”目录内容合并到“精选”目录，并删除旧目录。

        文件名冲突时对文件进行自动编号： name.ext -> name_1.ext, name_2.ext ...
        """
        try:
            os.makedirs(dst_dir, exist_ok=True)
            for name in os.listdir(src_dir):
                src = os.path.join(src_dir, name)
                dst = os.path.join(dst_dir, name)
                if os.path.isdir(src):
                    # 子目录整体迁移：冲突时编号
                    final_dst = dst
                    if os.path.exists(final_dst):
                        counter = 1
                        base, ext = os.path.splitext(name)
                        while os.path.exists(final_dst):
                            final_dst = os.path.join(dst_dir, f"{base}_{counter}{ext}")
                            counter += 1
                    shutil.move(src, final_dst)
                else:
                    # 文件迁移：冲突时编号
                    final_dst = dst
                    if os.path.exists(final_dst):
                        counter = 1
                        base, ext = os.path.splitext(name)
                        while os.path.exists(final_dst):
                            final_dst = os.path.join(dst_dir, f"{base}_{counter}{ext}")
                            counter += 1
                    shutil.move(src, final_dst)
            # 尝试删除空的旧目录
            with contextlib.suppress(Exception):
                os.rmdir(src_dir)
        except Exception:
            logger.debug("合并旧'保留'目录到'精选'目录失败", exc_info=True)

    def _validate_task_history(self, history_data):
        """验证任务历史记录是否有效

        Args:
            history_data: 历史记录数据

        Returns:
            bool: 历史记录是否有效
        """
        try:
            # 检查必要字段
            required_fields = ["subfolders", "current_subfolder_index", "current_index"]
            for field in required_fields:
                if field not in history_data:
                    return False

            # 过滤历史记录中可能残留的精选目录（旧版本/竞态写入）
            subfolders = history_data["subfolders"]
            if isinstance(subfolders, list):
                subfolders = self._filter_selection_folders(subfolders)
                history_data["subfolders"] = subfolders

            # 检查索引是否有效，同时修正因过滤精选目录导致的索引偏移
            current_subfolder_index = history_data["current_subfolder_index"]
            if 0 <= current_subfolder_index < len(subfolders):
                return True
            # 索引指向的文件夹可能已被过滤，调整到最近的有效位置
            if current_subfolder_index >= len(subfolders) and len(subfolders) > 0:
                current_subfolder_index = max(0, len(subfolders) - 1)
                history_data["current_subfolder_index"] = current_subfolder_index
                return True

            return False

        except Exception:
            return False

    @staticmethod
    def _filter_selection_folders(folders):
        """统一过滤：从文件夹列表中移除任意层级的精选目录

        精选目录以 "精选" / "精選" 结尾（繁/简/日韩变体），
        无论处于哪一级目录层级均应被排除，确保文件夹间导航不会跳入。

        Args:
            folders: 文件夹路径列表

        Returns:
            list: 过滤后的文件夹路径列表
        """
        if not folders:
            return []
        # 覆盖所有常见 CJK 变体：简中(精选) / 繁中(精選) / 日文(精選)
        selection_suffixes = ("精选", "精選")
        result = []
        for p in folders:
            try:
                name = os.path.basename(p.rstrip(os.sep))
                # 直接后缀匹配（覆盖绝大多数场景）
                if name.endswith(selection_suffixes):
                    continue
                # Unicode 规范化后再次检查（NFKC 覆盖全角/半角等边缘场景）
                import unicodedata

                normalized = unicodedata.normalize("NFKC", name)
                if normalized.endswith(selection_suffixes):
                    continue
                result.append(p)
            except Exception:
                result.append(p)
        return result

    def _show_task_history_restore_dialog(self, history_data):
        """显示任务历史记录恢复对话框

        Args:
            history_data: 历史记录数据

        使用附着在主窗口上的 sheet 弹窗展示，避免应用级模态弹窗在应用
        不在最前端时无法获得焦点，导致按钮无法点选、界面停摆。
        """
        try:
            alert = NSAlert.alloc().init()
            alert.setMessageText_("发现历史记录")

            current_subfolder_index = history_data["current_subfolder_index"]
            current_index = history_data["current_index"]
            subfolders = history_data["subfolders"]

            alert.setInformativeText_(
                f"发现上次浏览记录：\n"
                f"• 文件夹进度：第 {current_subfolder_index + 1} 个，共 {len(subfolders)} 个\n"
                f"• 图片进度：第 {current_index + 1} 张\n"
                f"• 是否恢复上次的浏览位置？"
            )

            alert.addButtonWithTitle_(get_ui_string("buttons", "restore", "恢复"))
            alert.addButtonWithTitle_(get_ui_string("buttons", "restart", "重新开始"))
            alert.addButtonWithTitle_(get_ui_string("buttons", "clear_history", "清除历史"))

            # 确保应用处于激活状态、主窗口位于最前端，
            # 避免弹窗（或 sheet）出现后无法聚焦、按钮无法点选
            try:
                NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            except Exception:
                pass
            try:
                self.main_window.makeKeyAndOrderFront_(None)
                self.main_window.orderFrontRegardless()
                if self.main_window.isMiniaturized():
                    self.main_window.deminiaturize_(None)
            except Exception:
                pass

            def _restart_from_dialog_error():
                """弹窗异常时的兜底：默认重新开始浏览"""
                try:
                    self.main_window.current_subfolder_index = 0
                    self.main_window.current_index = 0
                    self.load_current_subfolder()
                except Exception:
                    logger.exception("历史恢复对话框兜底失败")

            def _on_sheet_end(response):
                """sheet 关闭后的回调（主线程执行）"""
                self._active_history_alert = None
                try:
                    self._handle_task_history_dialog_result(response, history_data)
                except Exception as e:
                    logger.exception("处理历史恢复对话框结果失败: %s", e)
                    _restart_from_dialog_error()

            # 优先使用 sheet 模式：弹窗附着在主窗口上，始终位于窗口前端，
            # 且不会阻塞整个应用；失败时回退到应用级模态弹窗
            try:
                self._active_history_alert = alert
                alert.beginSheetModalForWindow_completionHandler_(self.main_window, _on_sheet_end)
            except Exception as e:
                logger.exception("显示历史恢复 sheet 失败，回退到 modal: %s", e)
                self._active_history_alert = None
                try:
                    result = alert.runModal()
                    self._handle_task_history_dialog_result(result, history_data)
                except Exception as e2:
                    logger.exception("显示历史恢复对话框失败: %s", e2)
                    _restart_from_dialog_error()

        except Exception:
            # 出错时默认重新开始
            try:
                self.main_window.current_subfolder_index = 0
                self.main_window.current_index = 0
                self.load_current_subfolder()
            except Exception:
                logger.exception("历史恢复对话框兜底失败")

    def _handle_task_history_dialog_result(self, result, history_data):
        """处理任务历史记录对话框结果

        Args:
            result: 对话框结果
            history_data: 历史记录数据
        """
        try:
            current_subfolder_index = history_data["current_subfolder_index"]
            current_index = history_data["current_index"]
            subfolders = history_data["subfolders"]

            if result == 1000:  # 恢复
                # 统一过滤：防御历史记录中残留的精选目录（旧版本/竞态写入）
                subfolders = self._filter_selection_folders(subfolders)
                if not subfolders:
                    # 过滤后无有效文件夹，回退到重新开始
                    self.main_window.current_subfolder_index = 0
                    self.main_window.current_index = 0
                    self.load_current_subfolder()
                    return
                # 修正 current_subfolder_index 以匹配过滤后的列表
                # 优先按持久化的 current_folder 路径定位（列表变化时更稳健），
                # 路径不在列表中再回退到序号
                restore_folder = history_data.get("current_folder")
                if restore_folder and restore_folder in subfolders:
                    current_subfolder_index = subfolders.index(restore_folder)
                if current_subfolder_index >= len(subfolders):
                    current_subfolder_index = max(0, len(subfolders) - 1)
                self.main_window.subfolders = subfolders
                self.main_window.current_subfolder_index = current_subfolder_index
                self.main_window.current_index = current_index
                self.main_window.keep_folder = history_data.get("keep_folder", "")
                self.main_window.current_folder = history_data.get("current_folder", None)
                self.load_current_subfolder(restore_index=current_index, async_first_load=True)
            elif result == 1001:  # 重新开始
                self.main_window.current_subfolder_index = 0
                self.main_window.current_index = 0
                self.load_current_subfolder()
            elif result == 1002:  # 清除历史
                if self.task_history_manager is not None:
                    self.task_history_manager.clear_history()
                self.main_window.current_subfolder_index = 0
                self.main_window.current_index = 0
                self.load_current_subfolder()
        except Exception:
            # 出错时默认重新开始
            self.main_window.current_subfolder_index = 0
            self.main_window.current_index = 0
            self.load_current_subfolder()

    def _save_task_progress_immediate(self):
        """立即保存任务进度 - 用于重要操作"""
        if self.task_history_manager is not None:
            current_data = {
                "subfolders": self.main_window.subfolders,
                "current_subfolder_index": self.main_window.current_subfolder_index,
                "current_index": self.main_window.current_index,
                "keep_folder": self.main_window.keep_folder,
                "current_folder": getattr(self.main_window, "current_folder", None),
            }
            # 重要操作使用同步保存确保数据完整性
            self.task_history_manager.save_task_progress(current_data)
            self.main_window._last_save_time = time.time()

    def set_reverse_folder_order(self, reverse):
        """设置文件夹倒序浏览

        Args:
            reverse: 是否倒序浏览
        """
        self.reverse_folder_order = reverse

    def get_recent_folders(self):
        """获取最近打开的文件夹列表

        Returns:
            list: 最近打开的文件夹列表
        """
        return self.recent_folders_manager.get()

    def add_recent_folder(self, folder_path):
        """添加最近打开的文件夹

        Args:
            folder_path: 文件夹路径
        """
        self.recent_folders_manager.add(folder_path)

    def clear_recent_folders(self):
        """清空最近打开的文件夹记录"""
        self.recent_folders_manager.clear()

    def clear_history(self):
        """清空历史记录"""
        if self.task_history_manager:
            self.task_history_manager.clear_history()

    def _get_parent_sibling_folders(self, current_folder):
        """获取当前文件夹的父级目录下的所有同级子文件夹

        Args:
            current_folder: 当前文件夹路径

        Returns:
            tuple: (父级目录路径, 同级子文件夹列表)
        """
        parent_dir = os.path.dirname(current_folder)
        if not parent_dir or parent_dir == current_folder:
            return None, []

        sibling_folders = []
        try:
            # 使用 os.scandir 直接获取子目录（scan_directory 只返回文件，不返回目录）
            with os.scandir(parent_dir) as entries:
                for entry in entries:
                    if entry.is_dir() and not entry.name.startswith("."):
                        # 排除“精选/精選”目录（覆盖简繁变体）
                        if entry.name.endswith(("精选", "精選")):
                            continue
                        sibling_folders.append(entry.path)
        except (OSError, PermissionError):
            pass

        # 按文件夹名升序排序（不区分大小写）
        try:
            sibling_folders.sort(key=lambda p: os.path.basename(p).lower())
        except Exception:
            sibling_folders.sort()

        return parent_dir, sibling_folders

    def _move_to_next_sibling_folder(self, current_folder):
        """移动到当前文件夹的下一个同级文件夹

        Args:
            current_folder: 当前文件夹路径

        Returns:
            tuple: (是否成功, 下一个同级文件夹路径, 父级目录路径)
        """
        parent_dir, sibling_folders = self._get_parent_sibling_folders(current_folder)
        if not sibling_folders:
            return False, None, None

        # 找到当前文件夹在同级列表中的位置
        try:
            current_index = sibling_folders.index(current_folder)
        except ValueError:
            return False, None, None

        # 计算下一个索引
        next_index = current_index + 1
        if next_index >= len(sibling_folders):
            return False, None, parent_dir  # 没有下一个，但返回父级目录

        next_folder = sibling_folders[next_index]
        return True, next_folder, parent_dir
