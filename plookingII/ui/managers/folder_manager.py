import os

"""
文件夹管理器

负责处理文件夹扫描、导航、历史记录等逻辑。
"""

import concurrent.futures
import logging
import shutil
import threading

from AppKit import NSAlert

from ...config.constants import APP_NAME, IMAGE_PROCESSING_CONFIG, SUPPORTED_IMAGE_EXTS
from ...config.ui_strings import get_ui_string
from ...core.history import TaskHistoryManager
from ...imports import logging, os, threading, time
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
                logger.info(f"启动时清理了 {cleaned_count} 个无效的最近文件夹记录")
        except Exception:
            logger.debug("启动时清理最近文件夹记录失败", exc_info=True)

        # 文件夹倒序浏览开关
        self.reverse_folder_order = False

        # 跳过文件夹历史记录机制
        self._skipped_folders_history = []
        self._max_skip_history = 10

        # 是否为“单文件夹模式”：仅当选择的根路径不包含任何子目录（os.walk 只返回根目录本身）
        self.single_folder_mode = False

    def _load_images_without_history_dialog(self, root_folder):
        """从根文件夹加载图像（不显示历史记录恢复对话框）

        用于侧栏导航，避免每次切换目录都弹出历史记录恢复对话框

        Args:
            root_folder: 根文件夹路径
        """
        self.main_window.root_folder = root_folder

        # 初始化任务历史管理器
        self.task_history_manager = TaskHistoryManager(root_folder)

        # 立即写入最近打开历史，确保数据库一致
        self.task_history_manager.add_recent_folder(root_folder)

        # 同时更新最近打开文件夹管理器的记录
        self.recent_folders_manager.add(root_folder)

        # 更新菜单显示
        self.main_window.updateRecentMenu_()

        # 扫描所有包含图片的子文件夹
        self.main_window.subfolders = self._scan_subfolders(root_folder)

        # 计算是否为"单文件夹模式"（严格：遍历目录仅包含根本身）
        try:
            dirs_for_mode = self._gather_directories_to_scan(root_folder)
            self.single_folder_mode = (len(dirs_for_mode) == 1)
        except Exception:
            self.single_folder_mode = False

        if not self.main_window.subfolders:
            self.main_window.image_view.setImage_(None)
            self.main_window.image_seq_label.setStringValue_("无图片 0/0")
            self.main_window.folder_seq_label.setStringValue_("0/0")
            return

        # 启动工作会话
        self._start_work_session()

        # 跳过历史记录检查，直接从第一个文件夹开始
        self.main_window.current_subfolder_index = 0
        self.main_window.current_index = 0
        self.load_current_subfolder()

    def load_images_from_root(self, root_folder):
        """从根文件夹加载图像

        Args:
            root_folder: 根文件夹路径
        """
        self.main_window.root_folder = root_folder

        # 初始化任务历史管理器
        self.task_history_manager = TaskHistoryManager(root_folder)

        # 立即写入最近打开历史，确保数据库一致
        self.task_history_manager.add_recent_folder(root_folder)

        # 同时更新最近打开文件夹管理器的记录
        self.recent_folders_manager.add(root_folder)

        # 更新菜单显示
        self.main_window.updateRecentMenu_()

        # 扫描所有包含图片的子文件夹
        self.main_window.subfolders = self._scan_subfolders(root_folder)

        # 计算是否为“单文件夹模式”（严格：遍历目录仅包含根本身）
        try:
            dirs_for_mode = self._gather_directories_to_scan(root_folder)
            self.single_folder_mode = (len(dirs_for_mode) == 1)
        except Exception:
            self.single_folder_mode = False

        if not self.main_window.subfolders:
            self.main_window.image_view.setImage_(None)
            self.main_window.image_seq_label.setStringValue_("无图片 0/0")
            self.main_window.folder_seq_label.setStringValue_("0/0")
            return

        # 启动工作会话
        self._start_work_session()

        # 检查历史记录
        history_data = self.task_history_manager.load_task_progress()
        if history_data and self._validate_task_history(history_data):
            self._show_task_history_restore_dialog(history_data)
        else:
            # 无历史记录或历史记录无效，从第一个文件夹开始
            self.main_window.current_subfolder_index = 0
            self.main_window.current_index = 0
            self.load_current_subfolder()

    def _start_work_session(self):
        """启动工作会话"""
        try:
            if hasattr(self.main_window, "status_bar_controller") and (
                self.main_window.status_bar_controller
            ):
                # 启动状态栏控制器的会话管理
                self.main_window.status_bar_controller.start_work_session()

                # 设置会话数据 - 保留基础会话跟踪
                if self.main_window.subfolders:
                    self.main_window.status_bar_controller.session_manager.set_folder_count(len(self.main_window.subfolders))

                logger.info("工作会话已启动")

        except Exception:
            logger.exception("启动工作会话时发生错误")

    def _end_work_session(self):
        """结束工作会话"""
        try:
            if hasattr(self.main_window, "status_bar_controller") and (
                self.main_window.status_bar_controller
            ):
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
        exts = SUPPORTED_IMAGE_EXTS
        subfolders = []
        scan_lock = threading.Lock()

        directories_to_scan = self._gather_directories_to_scan(root_folder)
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
            dirnames[:] = [d for d in dirnames if d != selection_name]
            directories_to_scan.append(dirpath)
        return directories_to_scan

    def _dir_contains_images(self, dirpath, exts):
        """判断目录是否包含图片

        Args:
            dirpath: 目录路径
            exts: 支持的图片扩展名

        Returns:
            bool: 是否包含图片
        """
        try:
            for f in os.listdir(dirpath):
                if f.lower().endswith(exts):
                    return True
            return False
        except (OSError, PermissionError):
            return False

    def load_current_subfolder(self, restore_index=None):
        """加载当前子文件夹的图片，支持恢复到指定图片索引

        Args:
            restore_index: 要恢复的图片索引
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
                    self.main_window.images = (
                        self._load_folder_images(self.main_window.current_folder)
                    )
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
        self.main_window.keep_folder = os.path.join(base_dir, self._compute_selection_folder_name(base_dir)) if base_dir else ""

        # 恢复历史索引，否则始终从第一张图片开始
        if restore_index is not None and 0 <= restore_index < len(self.main_window.images):
            self.main_window.current_index = restore_index
        else:
            self.main_window.current_index = 0

        # 同步双向缓存池序列（切换文件夹时重置窗口）
        self.main_window.image_manager.sync_bidi_sequence(self.main_window.images)

        # 优化：预加载第一张图片到缓存，减少显示延迟
        if self.main_window.images and (
            self.main_window.current_index < len(self.main_window.images)
        ):
            first_image_path = self.main_window.images[self.main_window.current_index]
            try:
                file_size_mb = (
                    self.main_window.image_manager.image_cache.get_file_size_mb(first_image_path)
                )
                fast_threshold = IMAGE_PROCESSING_CONFIG.get("fast_load_threshold", 50)
                if file_size_mb <= fast_threshold and (
                    IMAGE_PROCESSING_CONFIG.get("fast_load_enabled", True)
                ):
                    # 小文件预加载到缓存
                    def preload_first_image():
                        try:
                            image = (
                                self.main_window.image_manager._load_image_optimized(first_image_path, target_size=None)
                            )
                            if image:
                                # 将图片放入缓存，供后续显示使用
                                # 计算目标尺寸用于缓存
                                self.main_window.image_manager._get_target_size_for_view(scale_factor=2)
                                self.main_window.image_manager.image_cache.put_new(first_image_path, image, layer="main")
                        except Exception:
                            logger.debug("Preload first image failed", exc_info=True)

                    # 后台预加载，不阻塞UI
                    threading.Thread(target=preload_first_image, daemon=True).start()
            except Exception:
                logger.debug("Failed to check file size for preload", exc_info=True)

        self.main_window.image_manager.show_current_image()
        self._save_task_progress_immediate()

    def _move_to_next_nonempty_folder(self):
        """推进到下一个包含图片的子文件夹

        Returns:
            bool: 找到非空文件夹返回True，否则返回False
        """
        idx = self.main_window.current_subfolder_index
        step = -1 if self.reverse_folder_order else 1
        n = len(self.main_window.subfolders)

        # 循环查找包含图片的文件夹
        while 0 <= idx < n:
            folder = self.main_window.subfolders[idx]
            images = self._load_folder_images(folder)
            if images:  # 找到包含图片的文件夹
                self.main_window.current_subfolder_index = idx
                self.main_window.current_folder = folder
                self.main_window.images = images
                return True
            idx += step
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
            # 遍历文件夹中的所有文件
            for filename in os.listdir(folder_path):
                if filename.lower().endswith(exts):  # 检查文件扩展名
                    image_path = os.path.join(folder_path, filename)
                    images.append(image_path)

            # 图片始终按文件名正序排序，不受reverse_folder_order影响
            images.sort()
            return images
        except Exception:
            # 文件夹访问失败时返回空列表
            return []

    def jump_to_next_folder(self):
        """跳转到下一个文件夹的第一张图片，支持父级目录同级文件夹切换"""
        if not self.main_window.subfolders:
            return

        # 首先尝试在当前根目录的子文件夹中切换
        if self.reverse_folder_order:
            next_folder_idx = self.main_window.current_subfolder_index - 1
        else:
            next_folder_idx = self.main_window.current_subfolder_index + 1

        if 0 <= next_folder_idx < len(self.main_window.subfolders):
            self.main_window.current_subfolder_index = next_folder_idx
            self.main_window.images = (
                self._load_folder_images(self.main_window.subfolders[self.main_window.current_subfolder_index])
            )
            if not self.main_window.images:
                self.jump_to_next_folder()
                return
            # 无论是否倒序，都从第一张图片开始浏览
            self.main_window.current_index = 0
            self.main_window.current_folder = (
                self.main_window.subfolders[self.main_window.current_subfolder_index]
            )
            # 惰性创建：仅记录预期“精选”目录路径，不落盘创建
            base_dir = self.main_window.current_folder or self.main_window.root_folder or ""
            self.main_window.keep_folder = os.path.join(base_dir, self._compute_selection_folder_name(base_dir)) if base_dir else ""
            # 同步双向缓存池序列
            self.main_window.image_manager.sync_bidi_sequence(self.main_window.images)
            self.main_window.image_manager.show_current_image()
            self._save_task_progress_immediate()
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

    def _load_sibling_folder(self, folder_path, parent_dir):
        """加载同级文件夹

        Args:
            folder_path: 文件夹路径
            parent_dir: 父级目录路径
        """
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
        self.main_window.image_manager.show_current_image()
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

    def jump_to_previous_folder(self):
        """跳转到上一个文件夹的最后一张图片，支持父级目录同级文件夹切换"""
        if not self.main_window.subfolders:
            return

        # 首先尝试在当前根目录的子文件夹中切换
        if self.reverse_folder_order:
            prev_folder_idx = self.main_window.current_subfolder_index + 1
        else:
            prev_folder_idx = self.main_window.current_subfolder_index - 1

        if 0 <= prev_folder_idx < len(self.main_window.subfolders):
            self.main_window.current_subfolder_index = prev_folder_idx
            self.main_window.images = (
                self._load_folder_images(self.main_window.subfolders[self.main_window.current_subfolder_index])
            )
            if not self.main_window.images:
                self.jump_to_previous_folder()
                return
            # 无论是否倒序，都从最后一张图片开始浏览（向前跳转的逻辑）
            self.main_window.current_index = len(self.main_window.images) - 1
            self.main_window.current_folder = (
                self.main_window.subfolders[self.main_window.current_subfolder_index]
            )
            # 统一惰性策略：仅记录“精选”目录路径，不在此处落盘创建
            base_dir = self.main_window.current_folder or self.main_window.root_folder or ""
            self.main_window.keep_folder = (
                os.path.join(base_dir, self._compute_selection_folder_name(base_dir)) if base_dir else ""
            )
            # 同步双向缓存池序列
            self.main_window.image_manager.sync_bidi_sequence(self.main_window.images)
            self.main_window.image_manager.show_current_image()
            self._save_task_progress_immediate()
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

    def _load_previous_sibling_folder(self, folder_path, parent_dir):
        """加载上一个同级文件夹

        Args:
            folder_path: 文件夹路径
            parent_dir: 父级目录路径
        """
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
        self.main_window.keep_folder = os.path.join(
            folder_path, self._compute_selection_folder_name(folder_path)
        )
        # 同步双向缓存池序列
        self.main_window.image_manager.sync_bidi_sequence(self.main_window.images)
        self.main_window.image_manager.show_current_image()
        self._save_task_progress_immediate()

        # 更新状态栏显示
        folder_name = os.path.basename(folder_path)
        self.main_window.status_bar_controller.set_status_message(f"已切换到上一个同级文件夹: {folder_name}")

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

    def skip_current_folder(self):
        """跳过当前文件夹"""
        if not self.main_window.subfolders or len(self.main_window.subfolders) <= 1:
            self.main_window.status_bar_controller.set_status_message("无可跳过的文件夹")
            return

        # 记录当前文件夹到跳过历史
        current_folder_info = {
            "folder_index": self.main_window.current_subfolder_index,
            "folder_path": self.main_window.current_folder,
            "image_index": self.main_window.current_index
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
        self.main_window.keep_folder = os.path.join(base_dir, self._compute_selection_folder_name(base_dir)) if base_dir else ""

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
            try:
                os.rmdir(src_dir)
            except Exception:
                pass
        except Exception:
            logger.debug("合并旧‘保留’目录到‘精选’目录失败", exc_info=True)

        # 同步双向缓存池序列
        self.main_window.image_manager.sync_bidi_sequence(self.main_window.images)

        # 显示恢复的图片
        self.main_window.image_manager.show_current_image()
        self._save_task_progress_immediate()

        # 提供用户反馈
        folder_name = os.path.basename(self.folder_path) if hasattr(self, "folder_path") and self.folder_path else "文件夹"
        self.main_window.status_bar_controller.set_status_message(f"已撤销跳过，返回到: {folder_name}")

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

            # 检查索引是否有效
            current_subfolder_index = history_data["current_subfolder_index"]
            subfolders = history_data["subfolders"]

            if current_subfolder_index < 0 or current_subfolder_index >= len(subfolders):
                return False

            return True

        except Exception:
            return False

    def _show_task_history_restore_dialog(self, history_data):
        """显示任务历史记录恢复对话框

        Args:
            history_data: 历史记录数据
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

            # 使用modal模式确保按钮回调正常工作
            try:
                result = alert.runModal()
                self._handle_task_history_dialog_result(result, history_data)
            except Exception as e:
                logger.error(f"Failed to show history dialog: {e}")
                # 出错时默认重新开始
                self.main_window.current_subfolder_index = 0
                self.main_window.current_index = 0
                self.load_current_subfolder()

        except Exception:
            # 出错时默认重新开始
            self.main_window.current_subfolder_index = 0
            self.main_window.current_index = 0
            self.load_current_subfolder()

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
                self.main_window.subfolders = subfolders
                self.main_window.current_subfolder_index = current_subfolder_index
                self.main_window.current_index = current_index
                self.main_window.keep_folder = history_data.get("keep_folder", "")
                self.main_window.current_folder = history_data.get("current_folder", None)
                self.load_current_subfolder(restore_index=current_index)
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

    def _save_task_progress(self):
        """优化的任务进度保存 - 异步写入 + 节流"""
        current_time = time.time()
        if not hasattr(self.main_window, "_last_save_time"):
            self.main_window._last_save_time = 0
        if not hasattr(self.main_window, "_pending_save_data"):
            self.main_window._pending_save_data = None

        # 每3秒最多保存一次
        if current_time - self.main_window._last_save_time > 3:
            self.main_window._pending_save_data = {
                "subfolders": self.main_window.subfolders,
                "current_subfolder_index": self.main_window.current_subfolder_index,
                "current_index": self.main_window.current_index,
                "keep_folder": self.main_window.keep_folder,
                "current_folder": getattr(self.main_window, "current_folder", None),
            }
            self._async_save_progress()
            self.main_window._last_save_time = current_time

    def _async_save_progress(self):
        """异步保存进度数据"""
        if not self.main_window._pending_save_data or not self.task_history_manager:
            return

        def save_worker():
            try:
                if self.main_window._pending_save_data is not None and (
                    self.task_history_manager is not None
                ):
                    data_to_save = self.main_window._pending_save_data.copy()
                    self.task_history_manager.save_task_progress(data_to_save)
            except Exception:
                pass  # 静默处理保存错误

        # 启动异步保存线程
        save_thread = threading.Thread(target=save_worker, daemon=True)
        save_thread.start()

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

        try:
            # 获取父级目录下的所有子文件夹
            sibling_folders = []
            for item in os.listdir(parent_dir):
                item_path = os.path.join(parent_dir, item)
                if os.path.isdir(item_path):
                    sibling_folders.append(item_path)

            # 按文件夹名升序排序（不区分大小写）
            try:
                sibling_folders.sort(key=lambda p: os.path.basename(p).lower())
            except Exception:
                sibling_folders.sort()
            return parent_dir, sibling_folders
        except Exception:
            return None, []

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
