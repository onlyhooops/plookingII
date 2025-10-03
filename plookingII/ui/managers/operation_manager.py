import os

"""
操作管理器

负责处理文件操作、撤销、保留等业务逻辑。
"""

import logging
import shutil
import subprocess
import threading
import time

from AppKit import NSURL, NSAlert, NSModalResponseOK, NSOpenPanel, NSPopUpButton

from ...config.constants import APP_NAME
from ...config.ui_strings import get_ui_string

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

        # 旋转操作撤销栈
        self._rotation_action_stack = []

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

        # 同步执行文件移动，避免测试环境中后台线程导致的资源占用与竞态
        success = self._move_with_retry(current_image_path, target_path)
        if not success:
            if self._keep_action_stack and (self._keep_action_stack[-1].get("dst") == target_path):
                self._keep_action_stack.pop()
        # 刷新UI（在有主线程队列时尽量使用）
        try:
            from Foundation import NSOperationQueue

            NSOperationQueue.mainQueue().addOperationWithBlock_(lambda: self.main_window.updateUi_(None))
        except Exception:
            self.main_window.updateUi_(None)

        # 立即导航到下一张或下一个文件夹
        self._navigate_after_removal()

    def _get_source_folder_name(self):
        """获取源文件夹名称

        Returns:
            str: 源文件夹名称
        """
        if self.main_window.current_folder == self.main_window.root_folder:
            folder_name = (
                os.path.basename(self.main_window.root_folder) if self.main_window.root_folder else "根目录"
            )
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
        if self.main_window.images and (
            0 <= self.main_window.current_index < len(self.main_window.images)
        ):
            self.main_window.images.pop(self.main_window.current_index)
        if hasattr(self.main_window, "image_manager") and self.main_window.image_manager:
            try:
                self.main_window.image_manager.sync_bidi_sequence(self.main_window.images)
            except Exception:
                pass

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
            try:
                self.main_window.image_manager.start_preload()
            except Exception:
                pass

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
            if self.main_window.current_folder == orig_folder:
                self.main_window.images.insert(orig_index, src)
                self.main_window.current_index = orig_index

                # 同步双向缓存池序列（撤回插回后更新序列）
                if hasattr(self.main_window, "image_manager") and self.main_window.image_manager:
                    try:
                        self.main_window.image_manager.sync_bidi_sequence(self.main_window.images)
                    except Exception:
                        pass

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
                        try:
                            self.main_window.image_manager.start_preload()
                        except Exception:
                            pass

            self.main_window.status_bar_controller.set_status_message(
                self.main_window.ui_strings["selection_undone"]
            )
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
        alert.runModal()

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
            self.main_window.image_manager.memory_monitor.force_garbage_collection()

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
            alert.runModal()

    def goto_keep_folder(self):
        """跳转到保留文件夹"""
        if not self.main_window.root_folder:
            self._show_info_(get_ui_string("status_messages", "no_directory_for_selection", "未选择图片目录，无法打开精选文件夹。"))
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

        if alert.runModal() == 1000:
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
        result = alert.runModal()

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
                            self.main_window.current_subfolder_index
                        )

                    logger.info(f"跳转到文件: {target_index + 1}/{len(self.main_window.images)}")
                else:
                    self._show_info_(f"序号超出范围，请输入 1-{len(self.main_window.images)} 之间的数字。")

            except ValueError:
                self._show_info_("请输入有效的数字。")
            except Exception as e:
                logger.error(f"跳转到文件失败: {e}")
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
        alert.runModal()

    def clear_cache(self):
        """清除任务历史记录与缓存"""
        # 同步清理双向预加载窗口
        try:
            if hasattr(self.main_window, "image_manager") and self.main_window.image_manager:
                self.main_window.image_manager.bidi_pool.clear()
        except Exception:
            pass

        if hasattr(self.main_window, "folder_manager") and (
            self.main_window.folder_manager.task_history_manager
        ):
            self.main_window.folder_manager.task_history_manager.clear_history()
        else:
            self._show_info_("当前没有活动的历史记录。")

    def get_keep_action_stack(self):
        """获取保留操作栈

        Returns:
            list: 保留操作栈
        """
        return self._keep_action_stack

    def clear_keep_action_stack(self):
        """清空保留操作栈"""
        self._keep_action_stack = []

    def rotate_current_image(self, direction):
        """旋转当前图像

        Args:
            direction: 旋转方向 ("clockwise" 或 "counterclockwise")
        """
        if not self.main_window.images or self.main_window.current_index >= len(self.main_window.images):
            self.main_window.status_bar_controller.set_status_message("没有可旋转的图像")
            return

        current_image_path = self.main_window.images[self.main_window.current_index]
        if not os.path.exists(current_image_path):
            self.main_window.status_bar_controller.set_status_message("图像文件不存在")
            return

        # 记录旋转操作
        self._record_rotation_action(current_image_path, direction)

        # 显示旋转状态
        direction_text = "向右" if direction == "clockwise" else "向左"
        self.main_window.status_bar_controller.set_status_message(f"正在{direction_text}旋转90°...")

        def rotation_thread():
            try:
                # 执行旋转
                success = self._execute_rotation(current_image_path, direction)

                # 主线程更新UI
                if success:
                    try:
                        from Foundation import NSOperationQueue

                        NSOperationQueue.mainQueue().addOperationWithBlock_(
                            lambda: self.main_window.onRotationCompleted_({"success": True, "direction": direction})
                        )
                    except Exception:
                        self.main_window.onRotationCompleted_({"success": True, "direction": direction})
                else:
                    try:
                        from Foundation import NSOperationQueue

                        NSOperationQueue.mainQueue().addOperationWithBlock_(
                            lambda: self.main_window.onRotationCompleted_({"success": False, "direction": direction})
                        )
                    except Exception:
                        self.main_window.onRotationCompleted_({"success": False, "direction": direction})

            except Exception as e:
                logger.error(f"旋转操作失败: {e}")
                try:
                    from Foundation import NSOperationQueue

                    NSOperationQueue.mainQueue().addOperationWithBlock_(
                        lambda: self.main_window.onRotationCompleted_({"success": False, "direction": direction, "error": str(e)})
                    )
                except Exception:
                    self.main_window.onRotationCompleted_({"success": False, "direction": direction, "error": str(e)})

        # 启动旋转线程
        t = threading.Thread(target=rotation_thread, daemon=True)
        t.start()

    def _record_rotation_action(self, image_path, direction):
        """记录旋转操作

        Args:
            image_path: 图像文件路径
            direction: 旋转方向
        """
        action = {
            "image_path": image_path,
            "direction": direction,
            "timestamp": time.time(),
            "active": True,
        }
        self._rotation_action_stack.append(action)

        # 限制栈大小
        if len(self._rotation_action_stack) > 10:
            self._rotation_action_stack.pop(0)

    def _execute_rotation(self, image_path, direction):
        """执行旋转操作

        Args:
            image_path: 图像文件路径
            direction: 旋转方向

        Returns:
            bool: 操作是否成功
        """
        try:
            # 使用图像处理器的旋转功能
            if hasattr(self.main_window, "image_manager") and self.main_window.image_manager:
                if hasattr(self.main_window.image_manager, "hybrid_processor"):
                    return self.main_window.image_manager.hybrid_processor.rotate_image(
                        image_path, direction, self._on_rotation_callback
                    )

            # 备用方案：直接使用旋转处理器
            from ...core.image_rotation import ImageRotationProcessor

            processor = ImageRotationProcessor()
            return processor.rotate_image(image_path, direction, self._on_rotation_callback)

        except Exception as e:
            logger.error(f"执行旋转失败 {image_path}: {e}")
            return False

    def _on_rotation_callback(self, image_path, direction):
        """旋转完成回调

        Args:
            image_path: 图像文件路径
            direction: 旋转方向
        """
        try:
            # 清除相关缓存
            if hasattr(self.main_window, "image_manager") and self.main_window.image_manager:
                # 清除当前图像的缓存
                if hasattr(self.main_window.image_manager, "image_cache"):
                    try:
                        # 兼容旧方法名；优先使用新API
                        cache = self.main_window.image_manager.image_cache
                        if hasattr(cache, "remove"):
                            cache.remove(image_path)
                        elif hasattr(cache, "remove_from_cache"):
                            cache.remove_from_cache(image_path)
                    except Exception:
                        logger.debug("清理图像缓存失败", exc_info=True)

                # 清除双向缓存池中的相关缓存
                if hasattr(self.main_window.image_manager, "bidi_pool"):
                    self.main_window.image_manager.bidi_pool.clear_image_cache(image_path)

            # 重新加载当前图像
            self.main_window.image_manager.show_current_image()

        except Exception as e:
            logger.warning(f"旋转回调处理失败: {e}")

    def undo_rotation_action(self):
        """撤销旋转操作"""
        if not self._rotation_action_stack:
            self.main_window.status_bar_controller.set_status_message("无可撤销的旋转操作")
            return

        action = self._rotation_action_stack.pop()
        image_path = action["image_path"]
        original_direction = action["direction"]

        # 计算相反方向
        opposite_direction = (
            "counterclockwise" if original_direction == "clockwise" else "clockwise"
        )

        if not os.path.exists(image_path):
            self.main_window.status_bar_controller.set_status_message("无法撤销，图像文件不存在")
            return

        try:
            # 执行相反方向的旋转
            success = self._execute_rotation(image_path, opposite_direction)

            if success:
                self.main_window.status_bar_controller.set_status_message("已撤销旋转操作")
                # 重新加载图像
                self.main_window.image_manager.show_current_image()
            else:
                self.main_window.status_bar_controller.set_status_message("撤销旋转操作失败")

        except Exception as e:
            self.main_window.status_bar_controller.set_status_message(f"撤销失败: {e}")

    def get_rotation_action_stack(self):
        """获取旋转操作栈

        Returns:
            list: 旋转操作栈
        """
        return self._rotation_action_stack.copy()

    def clear_rotation_action_stack(self):
        """清空旋转操作栈"""
        self._rotation_action_stack = []
