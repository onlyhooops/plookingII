import objc
from AppKit import (
    NSApplication,
    NSBackingStoreBuffered,
    NSColor,
    NSDistributedNotificationCenter,
    NSObject,
    NSPasteboard,
    NSRect,
    NSTimer,
    NSWindow,
    NSWindowCollectionBehaviorFullScreenPrimary,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskTitled,
)

"""
重构后的主窗口类

整合所有控制器和管理器，作为协调者角色。
"""

import logging

from ..config.constants import APP_NAME
from ..config.manager import Config
from .controllers import (
    DragDropController,
    ImageViewController,
    MenuController,
    NavigationController,
    RotationController,
    StatusBarController,
    SystemController,
)
from .managers import FolderManager, ImageManager, ImageUpdateManager, OperationManager

# pyright: reportUndefinedVariable=false

logger = logging.getLogger(APP_NAME)

try:
    # 避免在测试环境中重复定义同名 Objective-C 类
    MainWindowRestorer = objc.lookUpClass("MainWindowRestorer")  # type: ignore
except Exception:
    logger.debug("Using fallback MainWindowRestorer implementation", exc_info=True)

    class MainWindowRestorer(NSObject):
        """
        窗口恢复类，实现 NSWindowRestoration 协议

        用于应用重启后自动恢复窗口状态，包括窗口位置、大小等信息。
        macOS 系统会在应用重启时调用此类的方法来恢复之前的窗口状态。
        """

        @classmethod
        def restoreWindowWithIdentifier_state_completionHandler_(cls, identifier, state, completionHandler):
            """
            系统窗口恢复回调方法

            Args:
                identifier: 窗口标识符
                state: 窗口状态数据
                completionHandler: 完成回调，传入恢复的窗口实例或None
            """
            try:
                # 创建新的主窗口实例
                win = MainWindow.alloc().init()
                completionHandler(win)
            except Exception:
                # 恢复失败时返回None
                completionHandler(None)


class MainWindow(NSWindow):
    """
    重构后的主窗口类，继承自NSWindow

    作为各个控制器和管理器的协调者，负责：
    - 窗口基本管理和生命周期
    - 事件分发和协调
    - 系统级功能（主题、外观等）
    - 菜单和对话框管理
    """

    def init(self):
        """
        初始化主窗口

        设置窗口基本属性、样式、恢复机制和UI组件。

        Returns:
            MainWindow: 初始化后的窗口实例，失败时返回None
        """
        # 创建窗口实例，设置初始位置(150, 200)和大小(1200x800)
        self = objc.super(MainWindow, self).initWithContentRect_styleMask_backing_defer_(  # type: ignore
            NSRect((150.0, 200.0), (1200.0, 800.0)),
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
            | NSWindowStyleMaskResizable,
            NSBackingStoreBuffered,
            False,
        )
        if self is None:
            return None

        # 设置窗口标题和背景色（不在标题栏显示APP名称）
        self.setTitle_("")
        self.setBackgroundColor_(NSColor.windowBackgroundColor())

        # 启用窗口状态恢复与尺寸位置自动保存
        try:
            self.setFrameAutosaveName_("MainWindowFrame")
            self.setRestorable_(True)
            self.setRestorationClass_(MainWindowRestorer)
        except Exception:
            logger.debug("Failed to enable window restoration", exc_info=True)

        # 启用原生全屏支持
        try:
            self.setCollectionBehavior_(self.collectionBehavior() | NSWindowCollectionBehaviorFullScreenPrimary)
        except Exception:
            logger.debug("Failed to enable fullscreen primary behavior", exc_info=True)

        # 跟随系统外观
        try:
            app = NSApplication.sharedApplication()
            app.setAppearance_(None)
        except Exception:
            logger.debug("Failed to follow system appearance", exc_info=True)

        # 监听系统外观变化
        try:
            NSDistributedNotificationCenter.defaultCenter().addObserver_selector_name_object_(
                self, "systemThemeChanged:", "AppleInterfaceThemeChangedNotification", None
            )
        except Exception:
            logger.debug("Failed to register theme change observer", exc_info=True)

        # 初始化基础属性
        self._init_basic_attributes()

        # 初始化控制器和管理器
        self._init_controllers_and_managers()

        # 设置用户界面组件
        self._setup_ui()

        # 同步配置的按键防抖延迟到导航控制器（毫秒 -> 秒）
        try:
            perf_cfg = Config.get_performance_config()
            debounce_ms = perf_cfg.get("debounce_ms", 80)
            self.navigation_controller.set_debounce_delay(max(0.01, float(debounce_ms) / 1000.0))
        except Exception:
            logger.debug("Failed to apply debounce config to navigation controller", exc_info=True)

        # 初始化最近打开文件夹菜单
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.1, self, "initializeRecentMenu:", None, False
        )

        # 注册拖拽接收功能
        self._setup_drag_and_drop()

        return self

    def _init_basic_attributes(self):
        """初始化基础属性"""
        # 文件夹和图片管理
        self.root_folder = None
        self.subfolders = []
        self.current_subfolder_index = 0
        self.current_folder = ""
        self.images = []
        self.current_index = 0
        self.keep_folder = ""

        # 应用状态
        self._shutting_down = False
        self._last_save_time = 0
        self._pending_save_data = None

        # 最近菜单相关
        self.recent_menu_item = None
        self.reverse_folder_order_menu_item = None

        # 拖拽相关属性已移至 DragDropController

    def _init_controllers_and_managers(self):
        """初始化控制器和管理器"""
        # 初始化控制器
        self.image_view_controller = ImageViewController(self)
        self.status_bar_controller = StatusBarController(self)  # type: ignore[assignment]
        self.navigation_controller = NavigationController(self)
        self.drag_drop_controller = DragDropController(self)
        self.menu_controller = MenuController(self)
        self.system_controller = SystemController(self)
        self.rotation_controller = RotationController(self)

        # 初始化管理器
        self.image_manager = ImageManager(self)  # type: ignore[assignment]
        self.folder_manager = FolderManager(self)  # type: ignore[assignment]
        self.operation_manager = OperationManager(self)  # type: ignore[assignment]
        self.image_update_manager = ImageUpdateManager(self)  # type: ignore[assignment]

        # 初始化服务
        from ..services import BackgroundTaskManager, HistoryManager, ImageLoaderService

        self.image_loader_service = ImageLoaderService(self)
        self.history_manager = HistoryManager(self)
        self.background_task_manager = BackgroundTaskManager(self)

        # 连接更新状态回调
        self.image_update_manager.add_update_callback(self._on_image_update_status_changed)

        # 设置引用关系
        self.image_view = None
        self.overlay = None
        self.zoom_slider = None
        self.image_seq_label = None
        self.folder_seq_label = None
        self.center_status_label = None

    def _setup_ui(self):
        """设置用户界面组件"""
        content_view = self.contentView()
        frame = content_view.frame()

        # 设置图像视图控制器
        self.image_view_controller.setup_ui(content_view, frame)

        # 设置状态栏控制器
        self.status_bar_controller.setup_ui(content_view, frame)

        # 设置引用关系
        self.image_view = self.image_view_controller.image_view
        self.overlay = self.image_view_controller.overlay
        self.zoom_slider = self.status_bar_controller.zoom_slider
        self.image_seq_label = self.status_bar_controller.image_seq_label
        self.folder_seq_label = self.status_bar_controller.folder_seq_label
        self.center_status_label = self.status_bar_controller.center_status_label

    def windowShouldClose_(self, sender):
        """
        窗口关闭事件处理

        当用户点击窗口关闭按钮时调用。保存当前任务进度并隐藏窗口，
        而不是销毁窗口。这样用户点击 Dock 图标时可以重新显示窗口。

        Args:
            sender: 事件发送者对象

        Returns:
            bool: False 表示不销毁窗口，只隐藏
        """
        try:
            # 保存当前任务进度
            self.system_controller.save_task_progress_immediate()

            # 清理会话资源（但不销毁窗口）
            if hasattr(self, "status_bar_controller") and self.status_bar_controller:
                self.status_bar_controller.cleanup()

            # 隐藏窗口而不销毁，点击 Dock 图标可以恢复
            self.orderOut_(None)
            return False  # 不允许销毁窗口
        except Exception as e:
            logger.warning(f"窗口关闭处理失败: {e}")
            self.orderOut_(None)
            return False

    def setFrame_display_(self, frameRect, flag):
        """
        窗口尺寸改变时的回调方法

        当用户调整窗口大小时调用，负责更新所有UI组件的布局。

        Args:
            frameRect: 新的窗口框架
            flag: 显示标志
        """
        try:
            # 调用父类方法更新窗口框架
            objc.super(MainWindow, self).setFrame_display_(frameRect, flag)  # type: ignore

            # 检查控制器是否已初始化
            if not hasattr(self, "image_view_controller") or not hasattr(self, "status_bar_controller"):
                return

            content_view = self.contentView()
            frame = content_view.frame()

            # 更新控制器框架
            self.image_view_controller.update_frame(frame)
            self.status_bar_controller.update_frame(frame)
            # 侧边栏已移除，无需更新
            # 无导航工具栏更新
        except Exception as e:
            logger.warning(f"窗口尺寸更新失败: {e}")

    # 侧边栏已移除，无切换回调

    def keyDown_(self, event):
        """
        处理键盘按键事件

        响应用户的键盘输入，实现图像浏览和管理的快捷键功能。
        采用委托模式，将具体处理委托给导航控制器。

        Args:
            event: 键盘事件对象

        Note:
            - 支持方向键导航
            - 支持功能快捷键
            - 未处理的按键传递给系统处理
        """
        try:
            # 委托给导航控制器处理
            if self.navigation_controller.handle_key_event(event):
                # 如果导航控制器已处理，直接返回
                return
            # 如果导航控制器未处理，传递给系统处理
            # 使用正确的super调用方式，避免递归
            from AppKit import NSWindow

            NSWindow.keyDown_(self, event)
        except Exception as e:
            logger.warning(f"键盘事件处理失败: {e}")
            # 出错时传递给系统处理
            try:
                from AppKit import NSWindow

                NSWindow.keyDown_(self, event)
            except Exception:
                # 如果连系统调用都失败，记录错误但不继续递归
                logger.error("系统键盘事件处理也失败，停止处理")

    def zoomSliderChanged_(self, sender):
        """
        缩放滑块值改变时的回调方法

        当用户拖动缩放滑块时，实时更新图片视图的缩放比例。
        以图片中心为缩放中心，确保缩放效果自然。

        Args:
            sender: 缩放滑块控件
        """
        try:
            # 检查图片视图是否存在且已加载图片（支持CGImage直通）
            if not hasattr(self, "image_view"):
                return

            # 检查是否有图像（NSImage或CGImage）
            has_nsimage = self.image_view.image() is not None
            has_cgimage = hasattr(self.image_view, "_cgimage") and self.image_view._cgimage is not None

            if not (has_nsimage or has_cgimage):
                return

            # 获取新的缩放比例
            new_scale = sender.doubleValue()

            # 计算缩放前的图片显示区域
            img_rect = self.image_view._get_image_display_rect(self.image_view.bounds())

            # 以图片中心为缩放中心
            rel_x = 0.5  # 图片中心
            rel_y = 0.5  # 图片中心

            # 计算缩放后的偏移
            cx = img_rect.origin.x + rel_x * img_rect.size.width
            cy = img_rect.origin.y + rel_y * img_rect.size.height

            new_w = img_rect.size.width * new_scale
            new_h = img_rect.size.height * new_scale
            new_x = cx - rel_x * new_w
            new_y = cy - rel_y * new_h

            # 更新图片视图的缩放状态
            self.image_view.offset_x = new_x - img_rect.origin.x
            self.image_view.offset_y = new_y - img_rect.origin.y
            self.image_view.zoom_scale = new_scale

            # 清除缓存并重绘
            if hasattr(self.image_view, "_cached_img_rect"):
                self.image_view._cached_img_rect = None
            self.image_view.setNeedsDisplay_(True)

        except Exception as e:
            logger.warning(f"缩放滑块处理失败: {e}")

    def updateZoomSlider_(self, scale):
        """
        更新缩放滑块的值（不触发回调）

        当图片视图的缩放状态改变时，同步更新缩放滑块的值，
        确保UI状态的一致性。

        Args:
            scale: 新的缩放比例
        """
        try:
            self.image_view_controller.update_zoom_slider(scale)
        except Exception as e:
            logger.warning(f"缩放滑块更新失败: {e}")

    def executePendingNavigation_(self, timer):
        """
        执行待处理的导航操作

        执行防抖处理后的导航操作，确保用户快速按键时
        只执行最后一次有效的导航。
        """
        try:
            self.navigation_controller.execute_pending_navigation()
        except Exception as e:
            logger.warning(f"导航操作执行失败: {e}")

    def clearStatusMessage_(self, timer=None):
        """
        清空状态消息（NSTimer 回调）
        """
        try:
            self.status_bar_controller.clear_status_message()
        except Exception as e:
            logger.warning(f"状态消息清除失败: {e}")

    # 兼容旧接口（无参数调用）
    def clearStatusMessage(self):
        return self.clearStatusMessage_(None)

    def updateUi_(self, sender):
        """
        Cocoa selector hook for 'updateUi:'

        当图片操作完成后，更新UI状态并导航到下一张图片。
        """
        try:
            self.operation_manager._navigate_after_removal()
        except Exception as e:
            logger.warning(f"UI更新失败: {e}")

    def rotate_image_clockwise(self):
        """委托给 RotationController"""
        self.rotation_controller.rotate_clockwise()

    def rotate_image_counterclockwise(self):
        """委托给 RotationController"""
        self.rotation_controller.rotate_counterclockwise()

    def _scan_subfolders(self, root_folder):
        """并行化扫描所有包含图片的子文件夹（兼容旧API）"""
        import concurrent.futures
        import os
        import threading

        # 获取支持的图片扩展名
        from ..config.constants import SUPPORTED_IMAGE_EXTS

        exts = SUPPORTED_IMAGE_EXTS
        subfolders = []
        scan_lock = threading.Lock()

        def scan_directory(dirpath):
            """扫描单个目录"""
            try:
                filenames = os.listdir(dirpath)
                # 检查是否包含图片文件
                images = [f for f in filenames if f.lower().endswith(exts)]
                if images:
                    with scan_lock:
                        subfolders.append(dirpath)
            except (OSError, PermissionError):
                # 忽略无法访问的目录
                pass

        # 收集所有需要扫描的目录
        directories_to_scan = []
        for dirpath, dirnames, _ in os.walk(root_folder):
            # 跳过“精选”文件夹：名称为 "[当前目录名] 精选"
            parent_name = os.path.basename(dirpath)
            selection_name = f"{parent_name} 精选" if parent_name else "精选"
            dirnames[:] = [d for d in dirnames if d != selection_name]
            directories_to_scan.append(dirpath)

        # 使用线程池并行扫描目录
        max_workers = min(16, len(directories_to_scan))  # 限制最大线程数
        if max_workers > 1:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                executor.map(scan_directory, directories_to_scan)
        else:
            # 如果目录数量很少，直接顺序扫描
            for dirpath in directories_to_scan:
                scan_directory(dirpath)

        # 根据reverse_folder_order属性决定排序顺序
        subfolders.sort(reverse=getattr(self, "reverse_folder_order", False))
        return subfolders

    def _load_folder_images(self, folder_path):
        """加载指定文件夹的图片（委托给ImageLoaderService）"""
        return self.image_loader_service.load_folder_images(folder_path)

    def _load_and_display_progressive(self, image_path, target_size):
        """渐进式加载（委托给ImageLoaderService）"""
        self.image_loader_service.load_and_display_progressive(image_path, target_size)

    def _display_image_immediate(self, image):
        """立即显示图片（委托给ImageLoaderService）"""
        self.image_loader_service.display_image_immediate(image)

    def _schedule_background_tasks(self):
        """调度后台任务（委托给BackgroundTaskManager）"""
        self.background_task_manager.schedule_background_tasks()

    def request_high_quality_image(self):
        """请求加载当前图像的高质量版本（委托给ImageLoaderService）"""
        self.image_loader_service.request_high_quality_image()

    def _load_image_optimized(self, img_path, prefer_preview=False, target_size=None):
        """智能图片加载方法（委托给ImageLoaderService）"""
        return self.image_loader_service.load_image_optimized(img_path, prefer_preview, target_size)

    def _load_standard_image(self, img_path):
        """标准图片加载（委托给ImageLoaderService）"""
        return self.image_loader_service.load_standard_image(img_path)

    def _load_with_pil_fallback(self, img_path):
        """PIL备用加载路径（委托给ImageLoaderService）"""
        return self.image_loader_service.load_with_pil_fallback(img_path)

    def _load_preview_image(self, img_path, file_size_mb):
        """加载预览质量图片（委托给ImageLoaderService）"""
        return self.image_loader_service.load_preview_image(img_path, file_size_mb)

    def _load_large_image_progressive(self, img_path):
        """渐进式加载超大图片（委托给ImageLoaderService）"""
        return self.image_loader_service.load_large_image_progressive(img_path)

    def _load_scaled_image_with_pil(self, img_path, max_dimension=3000):
        """使用PIL加载缩放图片（委托给ImageLoaderService）"""
        return self.image_loader_service.load_scaled_image_with_pil(img_path, max_dimension)

    def _load_large_image_with_pil(self, img_path):
        """使用PIL处理超大图片（委托给ImageLoaderService）"""
        return self.image_loader_service.load_large_image_with_pil(img_path)

    # 内存管理方法已移除，使用新的智能内存管理器

    def openFolder_(self, sender):
        """打开文件夹选择对话框"""
        try:
            self.operation_manager.open_folder()
        except Exception as e:
            logger.error(f"打开文件夹失败: {e}")

    def gotoKeepFolder_(self, sender):
        """跳转到保留文件夹"""
        try:
            self.operation_manager.goto_keep_folder()
        except Exception as e:
            logger.error(f"跳转到保留文件夹失败: {e}")

    def jumpToFolder_(self, sender):
        """跳转到指定文件夹"""
        try:
            self.operation_manager.jump_to_folder()
        except Exception as e:
            logger.error(f"跳转到指定文件夹失败: {e}")

    def gotoFile_(self, sender):
        """跳转到指定文件"""
        try:
            self.operation_manager.goto_file()
        except Exception as e:
            logger.error(f"跳转到文件失败: {e}")

    def rotateImageClockwise_(self, sender):
        """菜单项：向右旋转90°"""
        try:
            self.rotate_image_clockwise()
        except Exception as e:
            logger.error(f"菜单旋转失败: {e}")

    def rotateImageCounterclockwise_(self, sender):
        """菜单项：向左旋转90°"""
        try:
            self.rotate_image_counterclockwise()
        except Exception as e:
            logger.error(f"菜单旋转失败: {e}")

    def onRotationCompleted_(self, result):
        """旋转完成回调

        Args:
            result: 包含success、direction和可能的error的字典
        """
        try:
            success = result.get("success", False)
            direction = result.get("direction", "unknown")
            error = result.get("error", None)

            if success:
                direction_text = "向右" if direction == "clockwise" else "向左"
                self.status_bar_controller.set_status_message(f"{direction_text}旋转90°完成")

                # 重新加载当前图像以显示旋转结果
                self.image_manager.show_current_image()
            else:
                error_msg = f"旋转失败: {error}" if error else "旋转操作失败"
                self.status_bar_controller.set_status_message(error_msg)

        except Exception as e:
            logger.error(f"旋转完成回调处理失败: {e}")
            self.status_bar_controller.set_status_message("旋转操作异常")

    def showInFinder_(self, sender):
        """在Finder中显示当前图片"""
        try:
            self.operation_manager.show_in_finder()
        except Exception as e:
            logger.error(f"在Finder中显示当前图片失败: {e}")

    def clearCache_(self, sender):
        """清除任务历史记录与缓存"""
        try:
            self.operation_manager.clear_cache()
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")

    def set_status_message(self, msg):
        """设置状态消息 - 使用统一接口重构版本

        ✨ 重构说明: 使用统一状态管理器替代直接委托
        """
        try:
            from ..core.unified_interfaces import set_global_status

            set_global_status(msg)
        except Exception:
            # 回退到原始实现
            if hasattr(self, "status_bar_controller") and self.status_bar_controller:
                self.status_bar_controller.set_status_message(msg)

    def _validate_history(self, history_data):
        """委托给 HistoryManager"""
        return self.history_manager.validate_history(history_data)

    def _validate_task_history(self, history_data):
        """委托给 HistoryManager"""
        return self.history_manager.validate_task_history(history_data)

    def _show_history_restore_dialog(self, history_data):
        """委托给 HistoryManager"""
        self.history_manager.show_history_restore_dialog(history_data)

    def _show_task_history_restore_dialog(self, history_data):
        """委托给 HistoryManager"""
        self.history_manager.show_task_history_restore_dialog(history_data)

    def _async_save_progress(self):
        """委托给 HistoryManager"""
        self.history_manager.async_save_progress()

    def reverseFolderOrder_(self, sender):
        """委托给 SystemController"""
        self.system_controller.reverse_folder_order(sender)

    def updateReverseFolderOrderMenu_(self, sender=None):
        """委托给 SystemController"""
        self.system_controller.update_reverse_folder_order_menu(sender)

    # ==================== 系统级功能 ====================

    def systemThemeChanged_(self, notification):
        """委托给 SystemController"""
        self.system_controller.handle_system_theme_changed(notification)

    def toggleTheme_(self, sender):
        """委托给 SystemController"""
        self.system_controller.toggle_theme(sender)

    # ==================== 菜单和对话框 ====================

    def showAbout_(self, sender):
        """委托给 MenuController"""
        self.menu_controller.show_about(sender)

    def showShortcuts_(self, sender):
        """委托给 MenuController"""
        self.menu_controller.show_shortcuts(sender)

    # ==================== 菜单动作适配（与菜单构建器一致） ====================

    def undo_(self, sender):
        """撤销保留（兼容系统标准 undo: 动作）"""
        try:
            if hasattr(self, "operation_manager") and self.operation_manager:
                self.operation_manager.undo_keep_action()
        except Exception as e:
            logger.warning(f"撤销保留失败: {e}")

    def undoSelection_(self, sender):
        """撤销精选（自定义 action，避免系统覆盖菜单标题）"""
        self.undo_(sender)

    def copy_(self, sender):
        """复制当前图片路径到剪贴板（匹配编辑菜单的 copy: 动作）"""
        try:
            if not hasattr(self, "images") or not self.images or self.current_index >= len(self.images):
                if hasattr(self, "status_bar_controller") and self.status_bar_controller:
                    self.status_bar_controller.set_status_message("无当前图片，无法复制路径")
                return
            path = self.images[self.current_index]
            try:
                pb = NSPasteboard.generalPasteboard()
                pb.clearContents()
                # 兼容常见类型标识
                pb.setString_forType_(path, "public.utf8-plain-text")
            except Exception:
                logger.debug("Pasteboard operation failed, fallback noop", exc_info=True)
                return
            if hasattr(self, "status_bar_controller") and self.status_bar_controller:
                self.status_bar_controller.set_status_message("已复制图片路径")
        except Exception as e:
            logger.warning(f"复制图片路径失败: {e}")

    # ==================== 最近文件管理 ====================

    def showRecentFiles_(self, sender):
        """委托给 MenuController"""
        self.menu_controller.show_recent_files(sender)

    def openRecentFile_(self, sender):
        """委托给 MenuController"""
        self.menu_controller.open_recent_file(sender)

    def clearRecentFiles_(self, sender):
        """委托给 MenuController"""
        self.menu_controller.clear_recent_files(sender)

    def buildRecentMenu_(self, sender):
        """委托给 MenuController"""
        return self.menu_controller.build_recent_menu(sender)

    def updateRecentMenu_(self, sender=None):
        """委托给 MenuController"""
        self.menu_controller.update_recent_menu(sender)

    def initializeRecentMenu_(self, timer):
        """委托给 MenuController"""
        self.menu_controller.initialize_recent_menu(timer)

    # ==================== 内部方法 ====================

    def _update_status_display_immediate(self):
        """
        立即更新状态栏显示信息

        更新状态栏中的图片序列信息和文件夹序列信息。
        """
        try:
            self.status_bar_controller.update_status_display(
                self.current_folder, self.images, self.current_index, self.subfolders, self.current_subfolder_index
            )
        except Exception as e:
            logger.warning(f"更新状态栏显示失败: {e}")

    def _show_current_image_optimized(self):
        """
        优化的图片显示方法

        使用优化的方式显示当前图片，提高显示性能。
        """
        try:
            self.image_manager.show_current_image()
        except Exception as e:
            logger.warning(f"显示当前图片失败: {e}")

    def _on_image_update_status_changed(self, image_path: str, has_update: bool):
        """图片更新状态变化回调

        Args:
            image_path: 图片路径
            has_update: 是否有更新
        """
        try:
            if hasattr(self, "status_bar_controller"):
                self.status_bar_controller.set_update_indicator(has_update)
        except Exception as e:
            logger.error(f"更新状态指示器失败: {e}")

    def _save_task_progress(self):
        """委托给 HistoryManager"""
        self.history_manager.save_task_progress()

    def _save_task_progress_immediate(self):
        """委托给 HistoryManager"""
        self.history_manager.save_task_progress_immediate()

    def shutdown_background_tasks(self):
        """委托给 BackgroundTaskManager"""
        self.background_task_manager.shutdown_background_tasks()

    # ==================== 拖拽功能 ====================

    def _setup_drag_and_drop(self):
        """设置拖拽接收功能

        启用窗口的拖拽接收功能，支持用户拖拽文件夹到窗口进行照片浏览。
        """
        # 委托给 DragDropController
        self.drag_drop_controller.setup()

    def draggingEntered_(self, sender):
        """
        拖拽进入窗口时的处理

        委托给 DragDropController 处理。

        Args:
            sender: 拖拽信息对象

        Returns:
            NSDragOperation: 拖拽操作类型
        """
        return self.drag_drop_controller.dragging_entered(sender)

    def draggingUpdated_(self, sender):
        """
        拖拽在窗口内移动时的处理

        委托给 DragDropController 处理。

        Args:
            sender: 拖拽信息对象

        Returns:
            NSDragOperation: 拖拽操作类型
        """
        return self.drag_drop_controller.dragging_updated(sender)

    def draggingExited_(self, sender):
        """
        拖拽离开窗口时的处理

        委托给 DragDropController 处理。

        Args:
            sender: 拖拽信息对象
        """
        self.drag_drop_controller.dragging_exited(sender)

    def performDragOperation_(self, sender):
        """
        执行拖拽操作

        委托给 DragDropController 处理。

        Args:
            sender: 拖拽信息对象

        Returns:
            bool: 操作是否成功
        """
        return self.drag_drop_controller.perform_drag_operation(sender)

    # 拖拽相关的辅助方法已移至 DragDropController
