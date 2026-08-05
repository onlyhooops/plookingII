import os

"""
操作管理器

负责处理文件操作、撤销、保留等业务逻辑。
"""

import contextlib
import logging
import shutil
import subprocess
import threading
import time

from AppKit import NSURL, NSAlert, NSModalResponseOK, NSOpenPanel, NSPopUpButton

from ...config.constants import APP_NAME
from ...config.ui_strings import get_ui_string
from ...ui.utils.alert_utils import present_alert_sheet, run_modal

# 使用标准库与直接 AppKit 导入，避免通过项目 imports 的重复别名

logger = logging.getLogger(APP_NAME)


class OperationManager:
    """操作管理器，负责文件操作、撤销和保留功能"""

    def __init__(self, main_window):
        """初始化操作管理器

        Args:
            main_window: MainWindow实例
        """
        self.main_window = main_window

        # 保存操作撤销栈
        self._keep_action_stack = []
        self._last_keep_action = None

        # 精选计数内存缓存：避免每次导航在主线程 os.scandir 精选目录
        # 键为 keep_folder 路径；文件夹切换时自动失效，首次访问时同步扫描一次
        self._keep_count_cache: int | None = None
        self._keep_count_folder: str = ""
        self._keep_count_time: float = 0.0
        # 外部（Finder 等）修改精选文件夹时兜底：超过该间隔触发后台重校
        self._KEEP_COUNT_SYNC_INTERVAL = 30.0

    def keep_current_image(self):
        """保留当前图像"""
        if not self.main_window.images or self.main_window.current_index >= len(self.main_window.images):
            return

        current_image_path = self.main_window.images[self.main_window.current_index]
        if not os.path.exists(current_image_path):
            return

        # 惰性创建：仅在实际保留行为发生时创建“精选”目录
        try:
            os.makedirs(self.main_window.keep_folder, exist_ok=True)
        except Exception:
            return
        target_path, original_filename = self._build_keep_target_path(current_image_path)
        self._record_keep_action(current_image_path, target_path, original_filename)
        self._remove_current_image_from_sequences()
        # 乐观计数：文件移动在后台完成，失败时 _move_worker 回滚计数
        self._bump_keep_count(+1)

        # 后台线程执行文件移动（含重试），避免主线程在失败重试时 sleep 假死
        threading.Thread(
            target=self._move_worker,
            args=(current_image_path, target_path),
            daemon=True,
        ).start()

        # 刷新UI（在有主线程队列时尽量使用）
        try:
            from Foundation import NSOperationQueue

            NSOperationQueue.mainQueue().addOperationWithBlock_(lambda: self.main_window.updateUi_(None))
        except Exception:
            self.main_window.updateUi_(None)

        # 立即导航到下一张或下一个文件夹
        self._navigate_after_removal()

    def _move_worker(self, src, dst):
        """后台执行文件移动，失败时回滚撤销栈并在主线程提示

        Args:
            src: 源文件路径
            dst: 目标文件路径
        """
        success = self._move_with_retry(src, dst)
        if success:
            return

        def rollback():
            if self._keep_action_stack and (self._keep_action_stack[-1].get("dst") == dst):
                self._keep_action_stack.pop()
            # 移动失败，回滚乐观计数
            self._bump_keep_count(-1)
            try:
                self.main_window.status_bar_controller.set_status_message(f"移动文件失败: {os.path.basename(src)}")
            except Exception:
                pass

        try:
            from Foundation import NSOperationQueue

            NSOperationQueue.mainQueue().addOperationWithBlock_(rollback)
        except Exception:
            rollback()

    def _get_source_folder_name(self):
        """获取源文件夹名称

        Returns:
            str: 源文件夹名称
        """
        if self.main_window.current_folder == self.main_window.root_folder:
            folder_name = os.path.basename(self.main_window.root_folder) if self.main_window.root_folder else "根目录"
            return folder_name or "根目录"
        return os.path.basename(self.main_window.current_folder) if self.main_window.current_folder else "未知文件夹"

    def _build_keep_target_path(self, current_image_path):
        """构建保留目标路径

        Args:
            current_image_path: 当前图像路径

        Returns:
            tuple: (目标路径, 原始文件名)
        """
        original_filename = os.path.basename(current_image_path)
        base_name, ext = os.path.splitext(original_filename)
        folder_name = self._get_source_folder_name()
        new_filename = f"{folder_name} {original_filename}"
        target_path = os.path.join(str(self.main_window.keep_folder), new_filename)
        if os.path.exists(target_path):
            counter = 1
            while os.path.exists(target_path):
                numbered = f"{folder_name} {base_name}_{counter}{ext}"
                target_path = os.path.join(str(self.main_window.keep_folder), numbered)
                counter += 1
        return target_path, original_filename

    def _record_keep_action(self, src, dst, original_filename):
        """记录保留操作

        Args:
            src: 源文件路径
            dst: 目标文件路径
            original_filename: 原始文件名
        """
        action = {
            "src": src,
            "dst": dst,
            "orig_index": self.main_window.current_index,
            "orig_folder": self.main_window.current_folder,
            "orig_filename": original_filename,
            "active": True,
        }
        self._keep_action_stack.append(action)
        if len(self._keep_action_stack) > 5:
            self._keep_action_stack.pop(0)

    def _remove_current_image_from_sequences(self):
        """从序列中移除当前图像"""
        if self.main_window.images and (0 <= self.main_window.current_index < len(self.main_window.images)):
            self.main_window.images.pop(self.main_window.current_index)
        if hasattr(self.main_window, "image_manager") and self.main_window.image_manager:
            with contextlib.suppress(Exception):
                self.main_window.image_manager.sync_bidi_sequence(self.main_window.images)

    def _move_with_retry(self, src, dst, max_retries=3, initial_delay=1):
        """带重试的文件移动操作

        Args:
            src: 源文件路径
            dst: 目标文件路径
            max_retries: 最大重试次数
            initial_delay: 初始延迟时间

        Returns:
            bool: 操作是否成功
        """
        delay = initial_delay
        for attempt in range(max_retries):
            try:
                shutil.move(src, dst)
                return True
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                else:
                    return False
        return None

    def _navigate_after_removal(self):
        """移除图像后的导航逻辑（优化版本）"""
        if not self.main_window.images:
            # 当前文件夹没有图片了，跳转到下一个文件夹
            self.main_window.folder_manager.jump_to_next_folder()
            return
        if self.main_window.current_index >= len(self.main_window.images):
            self.main_window.current_index = len(self.main_window.images) - 1

        # 显示当前图像并立即启动预加载，确保后续导航流畅
        self.main_window.image_manager.show_current_image()

        # 延迟启动预加载，避免与当前图像显示冲突
        try:
            from Foundation import NSTimer

            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.1, self.main_window.image_manager, "start_preload", None, False
            )
        except Exception:
            # 备选方案：直接启动预加载
            with contextlib.suppress(Exception):
                self.main_window.image_manager.start_preload()

    def undo_keep_action(self):
        """撤销保留操作"""
        if not self._keep_action_stack:
            self.main_window.status_bar_controller.set_status_message("无可撤回的精选操作")
            return
        action = self._keep_action_stack.pop()
        src = action["src"]
        dst = action["dst"]
        orig_index = action["orig_index"]
        orig_folder = action["orig_folder"]
        action["orig_filename"]
        if not os.path.exists(dst):
            self.main_window.status_bar_controller.set_status_message("无法撤回，目标文件不存在")
            return
        try:
            shutil.move(dst, src)
            self._bump_keep_count(-1)
            if self.main_window.current_folder == orig_folder:
                self.main_window.images.insert(orig_index, src)
                self.main_window.current_index = orig_index

                # 同步双向缓存池序列（撤回插回后更新序列）
                if hasattr(self.main_window, "image_manager") and self.main_window.image_manager:
                    with contextlib.suppress(Exception):
                        self.main_window.image_manager.sync_bidi_sequence(self.main_window.images)

                    # 显示撤回的图像
                    self.main_window.image_manager.show_current_image()

                    # 立即重建预加载，确保后续导航流畅
                    try:
                        from Foundation import NSTimer

                        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                            0.15, self.main_window.image_manager, "start_preload", None, False
                        )
                    except Exception:
                        # 备选方案：直接启动预加载
                        with contextlib.suppress(Exception):
                            self.main_window.image_manager.start_preload()

            self.main_window.status_bar_controller.set_status_message(self.main_window.ui_strings["selection_undone"])
        except Exception as e:
            self.main_window.status_bar_controller.set_status_message(
                self.main_window.ui_strings["undo_failed"].format(e)
            )

    def show_completion(self):
        """显示任务完成对话框"""
        # 清空图片列表和当前图片
        self.main_window.images = []
        self.main_window.current_index = 0
        self.main_window.image_view.setImage_(None)

        # 重置状态
        self.main_window.status_bar_controller.set_completion_status()

        # 清理双向缓存池
        if hasattr(self.main_window, "image_manager") and self.main_window.image_manager:
            try:
                self.main_window.image_manager.bidi_pool.clear()
                self.main_window.image_manager.bidi_pool.set_sequence([])
            except Exception:
                pass

        # 显示完成对话框
        alert = NSAlert.alloc().init()
        alert.setMessageText_(get_ui_string("status_messages", "task_completed", "任务完成"))
        alert.setInformativeText_(get_ui_string("status_messages", "all_folders_viewed", "所有图片文件夹已浏览完毕！"))
        alert.addButtonWithTitle_(get_ui_string("buttons", "ok", "确定"))
        if not present_alert_sheet(alert, self.main_window):
            run_modal(alert, self.main_window)

    def exit_current_folder(self):
        """退出当前文件夹"""
        self.main_window.folder_manager._save_task_progress_immediate()

        # 清理缓存
        if hasattr(self.main_window, "image_manager") and self.main_window.image_manager:
            self.main_window.image_manager.image_cache.clear()

            # 清理双向缓存池
            try:
                self.main_window.image_manager.bidi_pool.clear()
                self.main_window.image_manager.bidi_pool.set_sequence([])
            except Exception:
                pass

        # 清理状态消息
        self.main_window.status_bar_controller.clear_status_message()

        # 重置基础数据
        self.main_window.global_image_list = []
        self.main_window.current_global_index = 0
        self.main_window.folder_list = []
        self.main_window.image_view.setImage_(None)
        self.main_window.status_bar_controller.set_empty_status()

        # 重置覆盖层状态
        if self.main_window.overlay is not None:
            self.main_window.overlay.setNeedsDisplay_(True)

        # 强制垃圾回收
        if hasattr(self.main_window, "image_manager") and self.main_window.image_manager:
            try:
                self.main_window.image_manager.memory_monitor.force_garbage_collection()
            except AttributeError:
                pass

        # 显示退出消息
        self._keep_action_stack = []  # 离开时清空撤回栈

    def open_folder(self):
        """打开文件夹选择对话框"""
        self.main_window.folder_manager._save_task_progress_immediate()

        # 选择文件夹前确保窗口可见
        self.main_window.makeKeyAndOrderFront_(None)
        self.main_window.orderFrontRegardless()

        try:
            panel = NSOpenPanel.openPanel()
            panel.setCanChooseFiles_(False)
            panel.setCanChooseDirectories_(True)
            panel.setAllowsMultipleSelection_(False)
            panel.setTitle_("选择图片文件夹或多层级目录")

            last_dir = self._get_last_dir()
            if last_dir and os.path.exists(last_dir):
                panel.setDirectoryURL_(NSURL.fileURLWithPath_(last_dir))

            result = panel.runModal()
            try:
                ok_code = NSModalResponseOK
            except NameError:
                ok_code = 1

            if result == ok_code:
                urls = panel.URLs()
                if urls and len(urls) > 0:
                    folder = urls[0].path()
                    if folder and os.path.exists(folder):
                        self._save_last_dir(folder)
                        self.main_window.folder_manager.add_recent_folder(folder)
                        self.main_window.updateRecentMenu_()
                        self.main_window.folder_manager.load_images_from_root(folder)
        except Exception as e:
            alert = NSAlert.alloc().init()
            alert.setMessageText_("打开文件夹失败")
            alert.setInformativeText_(str(e))
            alert.addButtonWithTitle_("确定")
            if not present_alert_sheet(alert, self.main_window):
                run_modal(alert, self.main_window)

    def goto_keep_folder(self):
        """跳转到保留文件夹"""
        if not self.main_window.root_folder:
            self._show_info_(
                get_ui_string("status_messages", "no_directory_for_selection", "未选择图片目录，无法打开精选文件夹。")
            )
            return

        # 计算“精选”目录名：[根目录名] 精选
        root_name = os.path.basename(self.main_window.root_folder.rstrip(os.sep))
        selection_name = f"{root_name} 精选" if root_name else "精选"
        keep_dir = os.path.join(self.main_window.root_folder, selection_name)
        if not os.path.exists(keep_dir):
            self._show_info_(get_ui_string("status_messages", "selection_folder_not_exist", "精选文件夹不存在。"))
            return

        # 使用系统默认方式打开保留文件夹
        subprocess.call(["open", keep_dir])

    def jump_to_folder(self):
        """跳转到指定文件夹"""
        self.main_window.folder_manager._save_task_progress_immediate()

        if not self.main_window.subfolders:
            self._show_info_(get_ui_string("status_messages", "no_directory_selected", "未选择图片目录，无法跳转。"))
            return

        alert = NSAlert.alloc().init()
        alert.setMessageText_("跳转文件夹")
        alert.setInformativeText_("请选择要跳转的图片文件夹：")
        popup = NSPopUpButton.alloc().initWithFrame_(((0, 0), (300, 24)))

        for folder in self.main_window.subfolders:
            popup.addItemWithTitle_(os.path.basename(folder))

        alert.setAccessoryView_(popup)
        alert.addButtonWithTitle_("跳转")
        alert.addButtonWithTitle_("取消")

        if run_modal(alert, self.main_window) == 1000:
            idx = popup.indexOfSelectedItem()
            if 0 <= idx < len(self.main_window.subfolders):
                # 跳转到选中的文件夹
                self.main_window.current_subfolder_index = idx
                self.main_window.current_index = 0
                self.main_window.folder_manager.load_current_subfolder()

    def goto_file(self):
        """跳转到指定文件"""
        # 检查是否有图片列表
        if not self.main_window.images:
            self._show_info_("当前文件夹没有图片，无法跳转。")
            return

        # 创建输入对话框
        from AppKit import NSAlert, NSMakeRect, NSTextField

        alert = NSAlert.alloc().init()
        alert.setMessageText_("跳转到文件")
        alert.setInformativeText_(f"请输入要跳转的文件序号 (1-{len(self.main_window.images)})：")

        # 创建输入框
        input_field = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 200, 24))
        input_field.setStringValue_(str(self.main_window.current_index + 1))  # 显示当前序号（从1开始）
        input_field.selectText_(None)  # 选中所有文本，方便用户直接输入

        alert.setAccessoryView_(input_field)
        alert.addButtonWithTitle_("跳转")
        alert.addButtonWithTitle_("取消")

        # 显示对话框
        result = run_modal(alert, self.main_window)

        if result == 1000:  # 跳转按钮
            try:
                # 获取用户输入的序号
                input_text = input_field.stringValue().strip()
                if not input_text:
                    self._show_info_("请输入有效的文件序号。")
                    return

                # 转换为整数（从1开始）
                target_index = int(input_text) - 1

                # 验证序号范围
                if 0 <= target_index < len(self.main_window.images):
                    # 跳转到指定文件
                    self.main_window.current_index = target_index
                    self.main_window.image_manager.show_current_image()

                    # 更新状态栏
                    if hasattr(self.main_window, "status_bar_controller") and self.main_window.status_bar_controller:
                        self.main_window.status_bar_controller.update_status_display(
                            self.main_window.current_folder,
                            self.main_window.images,
                            self.main_window.current_index,
                            self.main_window.subfolders,
                            self.main_window.current_subfolder_index,
                        )

                    logger.info("跳转到文件: %s/%s", target_index + 1, len(self.main_window.images))
                else:
                    self._show_info_(f"序号超出范围，请输入 1-{len(self.main_window.images)} 之间的数字。")

            except ValueError:
                self._show_info_("请输入有效的数字。")
            except Exception as e:
                logger.exception("跳转到文件失败: %s", e)
                self._show_info_(f"跳转失败: {e!s}")

    def show_in_finder(self):
        """在Finder中显示当前图片"""
        # 当前图片路径
        if not self.main_window.images or self.main_window.current_index >= len(self.main_window.images):
            self._show_info_("无当前图片，无法定位。")
            return
        img_path = self.main_window.images[self.main_window.current_index]
        subprocess.call(["open", "-R", img_path])

    def _get_last_dir(self):
        """获取上次打开的目录

        Returns:
            str: 上次打开的目录路径
        """
        try:
            home = os.path.expanduser("~")
            hidden_name = f".{APP_NAME.lower()}_lastdir"
            path = os.path.join(home, hidden_name)
            if os.path.exists(path):
                with open(path) as f:
                    return f.read().strip()
        except Exception:
            return None

    def _save_last_dir(self, folder):
        """保存最后打开的目录

        Args:
            folder: 文件夹路径
        """
        try:
            home = os.path.expanduser("~")
            hidden_name = f".{APP_NAME.lower()}_lastdir"
            path = os.path.join(home, hidden_name)
            with open(path, "w") as f:
                f.write(folder)
        except Exception:
            pass

    def _show_info_(self, msg):
        """显示信息对话框

        Args:
            msg: 要显示的消息
        """
        alert = NSAlert.alloc().init()
        alert.setMessageText_(msg)
        alert.addButtonWithTitle_("确定")
        if not present_alert_sheet(alert, self.main_window):
            run_modal(alert, self.main_window)

    def clear_cache(self):
        """清除任务历史记录与缓存"""
        # 同步清理双向预加载窗口
        try:
            if hasattr(self.main_window, "image_manager") and self.main_window.image_manager:
                self.main_window.image_manager.bidi_pool.clear()
        except Exception:
            pass

        if hasattr(self.main_window, "folder_manager") and (self.main_window.folder_manager.task_history_manager):
            self.main_window.folder_manager.task_history_manager.clear_history()
        else:
            self._show_info_("当前没有活动的历史记录。")

    def get_keep_action_stack(self):
        """获取保留操作栈

        Returns:
            list: 保留操作栈
        """
        return self._keep_action_stack

    def get_keep_count(self) -> int:
        """获取当前会话已精选的图片数量

        优先返回内存缓存；精选目录路径变化时执行一次同步扫描并缓存，
        之后导航热路径不再触碰文件系统（外置盘/网络盘收益明显）。
        超过 _KEEP_COUNT_SYNC_INTERVAL 后由后台线程异步重校，
        覆盖外部（Finder 等）对精选目录的直接修改。

        Returns:
            int: 已精选图片数量
        """
        try:
            keep_folder = getattr(self.main_window, "keep_folder", "")
            if not keep_folder or not os.path.isdir(keep_folder):
                self._keep_count_cache = None
                self._keep_count_folder = ""
                return 0

            if self._keep_count_folder == keep_folder and self._keep_count_cache is not None:
                # 定期后台重校，兜底外部改动
                if time.time() - self._keep_count_time >= self._KEEP_COUNT_SYNC_INTERVAL:
                    self._schedule_keep_count_resync(keep_folder)
                return self._keep_count_cache

            # 首次访问当前精选目录：同步扫描一次并缓存
            count = self._scan_keep_folder(keep_folder)
            self._keep_count_cache = count
            self._keep_count_folder = keep_folder
            self._keep_count_time = time.time()
            return count
        except Exception:
            logger.debug("获取精选计数失败", exc_info=True)
            return 0

    def _scan_keep_folder(self, keep_folder: str) -> int:
        """扫描精选文件夹中的图片文件数量（仅在此处直接触碰文件系统）"""
        try:
            from ...config.constants import SUPPORTED_IMAGE_EXTS

            count = 0
            with os.scandir(keep_folder) as it:
                for entry in it:
                    if entry.is_file() and entry.name.lower().endswith(SUPPORTED_IMAGE_EXTS):
                        count += 1
            return count
        except Exception:
            return 0

    def _bump_keep_count(self, delta: int) -> None:
        """按增量调整内存精选计数（仅当缓存仍对应当前精选目录时）"""
        try:
            keep_folder = getattr(self.main_window, "keep_folder", "")
            if self._keep_count_folder == keep_folder and self._keep_count_cache is not None:
                self._keep_count_cache = max(0, self._keep_count_cache + delta)
                self._keep_count_time = time.time()
        except Exception:
            pass

    def _schedule_keep_count_resync(self, keep_folder: str) -> None:
        """后台重校精选计数，避免主线程 I/O"""

        def resync_worker():
            try:
                count = self._scan_keep_folder(keep_folder)
                # 仅当缓存仍指向同一目录时回填（文件夹已切换则丢弃）
                if self._keep_count_folder == keep_folder:
                    self._keep_count_cache = count
                    self._keep_count_time = time.time()
            except Exception:
                pass

        try:
            threading.Thread(target=resync_worker, daemon=True).start()
        except Exception:
            pass

    def clear_keep_action_stack(self):
        """清空保留操作栈"""
        self._keep_action_stack = []
