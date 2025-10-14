import logging
import os

import objc
from AppKit import (
    NSColor,
    NSCompositingOperationSourceOver,
    NSImageView,
    NSMakePoint,
    NSMakeRect,
    NSRectFill,
    NSTimer,
    NSView,
    NSWorkspace,
)
from Foundation import NSURL

from .context_menu_manager import ContextMenuManager

# 导入常量，使用绝对导入
try:
    from plookingII.config.constants import APP_NAME
except ImportError:
    # 如果导入失败，使用默认值
    APP_NAME = "PlookingII"

# 创建logger实例
logger = logging.getLogger(APP_NAME)

"""
PlookingII UI视图组件模块

提供PlookingII应用程序的用户界面组件，包括图像视图、覆盖层视图等。
这些组件基于macOS Cocoa框架构建，提供原生的用户体验。

主要组件：
    - AdaptiveImageView: 自适应图像视图，支持缩放、拖拽等交互
    - OverlayView: 覆盖层视图，用于显示拖拽高亮等辅助信息
    - apply_safe_performance_tweaks: 性能优化工具函数

核心特性：
    - 原生macOS Cocoa界面
    - 高性能图像渲染
    - 内存优化的缓存管理
    - 响应式用户交互

Author: PlookingII Team
"""

from ..config.constants import APP_NAME
from ..core.functions import _env_int
from ..imports import _objc, logging, objc, time

# pyright: reportUndefinedVariable=false

# 新增：模块级日志记录器
logger = logging.getLogger(APP_NAME)


def apply_safe_performance_tweaks(win):
    """应用安全的性能优化调整

    根据环境变量配置，对主窗口实例应用各种性能优化设置。
    这些调整都是非侵入性的，不会影响应用程序的核心功能。

    Args:
        win: MainWindow实例，要应用性能优化的主窗口对象

    可调参数（环境变量覆盖）：
        PLOOKINGII_CACHE_MAX_IMAGES  (默认 120): 图像缓存最大数量
        PLOOKINGII_CACHE_MAX_MB      (默认 4096): 图像缓存最大内存(MB)
        PLOOKINGII_PREVIEW_MAX_MB    (默认 512): 预览缓存最大内存(MB)
        PLOOKINGII_DEBOUNCE_MS       (默认 20): 按键防抖时间(毫秒)
        PLOOKINGII_TRIM_INTERVAL_S   (默认 30): 定时清理缓存周期(秒)

    Note:
        - 所有调整都是安全的，失败时不会影响应用程序运行
        - 环境变量可以在运行时动态调整，无需重启应用程序
        - 缓存清理是后台任务，不会阻塞用户界面

    Example:
        >>> # 设置环境变量后调用
        >>> os.environ["PLOOKINGII_CACHE_MAX_MB"] = "2048"
        >>> apply_safe_performance_tweaks(main_window)
    """
    try:
        # 从环境变量读取配置参数，使用默认值作为回退
        max_images = _env_int("PLOOKINGII_CACHE_MAX_IMAGES", 120)
        max_mb = _env_int("PLOOKINGII_CACHE_MAX_MB", 4096)
        preview_mb = _env_int("PLOOKINGII_PREVIEW_MAX_MB", 512)
        debounce_ms = _env_int("PLOOKINGII_DEBOUNCE_MS", 80)
        trim_interval = _env_int("PLOOKINGII_TRIM_INTERVAL_S", 30)

        # 1) 调整图像缓存上限（若存在）
        if hasattr(win, "image_cache") and win.image_cache:
            ic = win.image_cache
            if hasattr(ic, "max_size"):
                ic.max_size = max_images
            if hasattr(ic, "max_memory_mb"):
                ic.max_memory_mb = max_mb
            # 常见命名尝试：preview/thumbnail缓存上限
            for attr in ("preview_max_memory_mb", "preview_memory_limit_mb", "preview_memory_budget_mb"):
                if hasattr(ic, attr):
                    setattr(ic, attr, preview_mb)

        # 2) 渐进式加载与按键防抖（若存在）
        if hasattr(win, "progressive_loading_enabled"):
            win.progressive_loading_enabled = True
        # 简单的按键防抖时间（毫秒）
        if hasattr(win, "_key_debounce_interval_ms"):
            win._key_debounce_interval_ms = debounce_ms
        else:
            try:
                win._key_debounce_interval_ms = debounce_ms
            except Exception:
                logger.debug("Set _key_debounce_interval_ms failed", exc_info=True)

        # 3) 定时清理缓存（非侵入）
        def _trim_cache(_timer=None):
            """定时清理缓存的内部函数"""
            try:
                ic = getattr(win, "image_cache", None)
                if ic and hasattr(ic, "trim_to_budget"):
                    ic.trim_to_budget()
                elif ic and hasattr(ic, "clear_overflow"):
                    ic.clear_overflow()
            except Exception:
                logger.debug("_trim_cache execution failed", exc_info=True)

        if _NSTimer and _NSRunLoop and trim_interval > 0:
            try:
                # 创建并安排一个重复触发的定时器
                timer = _NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                    trim_interval,
                    win,
                    _objc.selector(lambda _self, _cmd, _arg=None: _trim_cache(), signature=b"v@:@"),
                    None,
                    True,
                )
                _NSRunLoop.currentRunLoop().addTimer_forMode_(timer, _NSDefaultRunLoopMode)
                # 触发一次立即清理
                _trim_cache()
            except Exception:
                logger.debug("Scheduling trim timer failed, run once immediately", exc_info=True)
                _trim_cache()
    except Exception:
        logger.exception("apply_safe_performance_tweaks failed")


class OverlayView(NSView):
    def initWithFrame_andImageView_(self, frame, image_view):
        self = objc.super(OverlayView, self).initWithFrame_(frame)  # type: ignore
        if self is None:
            return None
        self.image_view = image_view
        self.setWantsLayer_(True)
        self.setLayerContentsRedrawPolicy_(2)
        return self

    def drawRect_(self, rect):
        # 覆盖层绘制接口 - 当前无特殊绘制需求
        pass


class AdaptiveImageView(NSImageView):
    def initWithFrame_(self, frame):
        self = objc.super(AdaptiveImageView, self).initWithFrame_(frame)  # type: ignore
        if self is None:
            return None
        # 交互相关状态
        self.zoom_scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.is_dragging = False
        self.is_space_drag_mode = False
        self.last_mouse_pos = None
        self.last_zoom_center = None
        self.last_image_id = None
        self._hand_cursor = None
        self._default_cursor = None
        self._double_click_flag = False
        # 委托对象，用于通知主窗口重新加载原图
        self.delegate = None
        self._last_high_quality_request = 0  # 上次请求高质量图像的时间

        # 拖拽相关属性
        self._drag_highlight = False  # 拖拽高亮状态

        # 右键菜单相关属性
        self._current_image_path = None  # 当前显示的图片路径
        self._context_menu_manager = ContextMenuManager(self)  # 上下文菜单管理器

        # 启用右键事件
        self.setAcceptsTouchEvents_(False)  # 确保不会被触摸事件干扰

        # 确保视图可以接收鼠标事件（NSView没有setAcceptsFirstResponder_方法）
        # self.setAcceptsFirstResponder_(True)  # 这个方法不存在，移除

        logger.debug("AdaptiveImageView 初始化完成，视图ID: %s", id(self))

        # 性能优化相关属性
        self._last_scroll_time = 0  # 上次滚轮事件时间
        self._cached_img_rect = None  # 缓存的图片显示区域
        self._redraw_timer = None  # 重绘定时器
        self._pending_redraw = False  # 是否有待处理的重绘

        # 启用图层加速
        self.setWantsLayer_(True)
        if hasattr(self, "setLayerContentsRedrawPolicy_"):
            self.setLayerContentsRedrawPolicy_(2)  # NSViewLayerContentsRedrawOnSetNeedsDisplay

        return self

    def acceptsFirstResponder(self):
        return True

    def becomeFirstResponder(self):
        return True

    def resignFirstResponder(self):
        self.is_dragging = False
        self.is_space_drag_mode = False
        self.setNeedsDisplay_(True)
        return True

    def reset_view(self):
        self.zoom_scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.is_dragging = False
        self.is_space_drag_mode = False
        self.last_mouse_pos = None
        self.last_zoom_center = None
        self._double_click_flag = False

        # 重置拖拽高亮状态
        self._drag_highlight = False

        # 清除性能优化缓存
        self._cached_img_rect = None
        self._cancel_pending_redraw()

        # 同步更新滑块值到100%
        if self.delegate and hasattr(self.delegate, "updateZoomSlider_"):
            self.delegate.updateZoomSlider_(1.0)

        self.setNeedsDisplay_(True)

    def setImage_(self, image):
        objc.super(AdaptiveImageView, self).setImage_(image)
        # 清空CGImage直通缓存
        try:
            self._cgimage = None
        except Exception:
            pass
        # 切换图片时重置状态
        self.reset_view()
        # 记录图片唯一标识（可用id(image)或hash）
        self.last_image_id = id(image) if image else None

    def setCGImage_(self, cgimage):
        """支持CGImage直通，不创建NSImage，绘制时直接用Quartz渲染。"""
        try:
            # 清除NSImage，改走CGImage直通
            objc.super(AdaptiveImageView, self).setImage_(None)
            self._cgimage = cgimage
            self.reset_view()
            self.last_image_id = id(cgimage) if cgimage else None
            self.setNeedsDisplay_(True)
        except Exception:
            # 回退：仍可尝试使用NSImage路径
            if cgimage is not None:
                try:
                    from AppKit import NSImage

                    nsimg = NSImage.alloc().initWithCGImage_(cgimage)
                    self.setImage_(nsimg)
                except Exception:
                    pass

    def scrollWheel_(self, event):
        # 滚轮平移功能 - 仅在缩放比率大于100%时生效
        # 检查是否有图像（NSImage或CGImage）
        has_nsimage = self.image() is not None
        has_cgimage = hasattr(self, "_cgimage") and self._cgimage is not None

        if not (has_nsimage or has_cgimage):
            return

        # 只有在缩放比率大于100%时才允许滚轮平移
        if self.zoom_scale <= 1.0:
            return

        # 防抖处理 - 避免过于频繁的平移操作
        current_time = time.time()
        if hasattr(self, "_last_scroll_time") and (
            current_time - self._last_scroll_time < 0.016  # 60fps限制
        ):
            return
        self._last_scroll_time = current_time

        # 获取滚轮增量
        delta_y = event.deltaY()
        delta_x = event.deltaX() if hasattr(event, "deltaX") else 0

        # 平移灵敏度调整
        pan_sensitivity = 2.0

        # 支持精确滚轮（如Magic Mouse）和传统滚轮
        if hasattr(event, "hasPreciseScrollingDeltas") and event.hasPreciseScrollingDeltas():
            # 精确滚轮，直接使用增量值
            pan_x = delta_x * pan_sensitivity
            pan_y = delta_y * pan_sensitivity
        else:
            # 传统滚轮，放大增量值
            pan_x = delta_x * pan_sensitivity * 10
            pan_y = delta_y * pan_sensitivity * 10

        # 计算新的偏移值
        new_offset_x = self.offset_x + pan_x
        new_offset_y = self.offset_y + pan_y

        # 获取当前图片显示区域和视图边界
        view_bounds = self.bounds()
        img_rect = self._get_image_display_rect(view_bounds)

        # 计算缩放后的图片尺寸
        scaled_width = img_rect.size.width * self.zoom_scale
        scaled_height = img_rect.size.height * self.zoom_scale

        # 计算缩放后图片的实际显示区域
        scaled_x = img_rect.origin.x + new_offset_x
        img_rect.origin.y + new_offset_y

        # 边界限制 - 防止图片移出视图范围
        # 水平边界限制
        if scaled_width > view_bounds.size.width:
            # 图片宽度大于视图宽度时，限制水平移动
            min_x = view_bounds.size.width - scaled_width
            max_x = 0
            if scaled_x < min_x:
                new_offset_x = min_x - img_rect.origin.x
            elif scaled_x > max_x:
                new_offset_x = max_x - img_rect.origin.x
        else:
            # 图片宽度小于视图宽度时，保持居中
            new_offset_x = self.offset_x

        # 垂直边界限制
        if scaled_height > view_bounds.size.height:
            # 图片高度大于视图高度时，限制垂直移动
            min_y = view_bounds.size.height - scaled_height
            max_y = 0
            scaled_y_corrected = img_rect.origin.y + new_offset_y
            if scaled_y_corrected < min_y:
                new_offset_y = min_y - img_rect.origin.y
            elif scaled_y_corrected > max_y:
                new_offset_y = max_y - img_rect.origin.y
        else:
            # 图片高度小于视图高度时，保持居中
            new_offset_y = self.offset_y

        # 应用限制后的平移
        self.offset_x = new_offset_x
        self.offset_y = new_offset_y

        # 清除缓存的图片区域
        if hasattr(self, "_cached_img_rect"):
            self._cached_img_rect = None

        # 优化重绘 - 只在必要时重绘
        self._schedule_optimized_redraw()

    def mouseDown_(self, event):
        # 检查是否有图像（NSImage或CGImage）
        has_nsimage = self.image() is not None
        has_cgimage = hasattr(self, "_cgimage") and self._cgimage is not None

        if not (has_nsimage or has_cgimage):
            return
        # 检查双击
        if event.clickCount() == 2:
            # 仅在100%或1000%时响应
            if abs(self.zoom_scale - 1.0) < 1e-3:
                # 放大到10倍
                self._double_click_flag = True
                self._zoom_to_point(event, 10.0)
            elif abs(self.zoom_scale - 10.0) < 1e-3:
                # 还原
                self._double_click_flag = True
                self._zoom_to_point(event, 1.0)
            else:
                pass
            return
        # 单击时，若处于拖拽模式，记录起始点
        if self.is_space_drag_mode and self.zoom_scale > 1.0:
            self.is_dragging = True
            self.last_mouse_pos = event.locationInWindow()
            self.window().makeFirstResponder_(self)
        else:
            objc.super(AdaptiveImageView, self).mouseDown_(event)

    def mouseUp_(self, event):
        self.is_dragging = False
        self.last_mouse_pos = None
        self.setNeedsDisplay_(True)
        objc.super(AdaptiveImageView, self).mouseUp_(event)

    def rightMouseDown_(self, event):
        """处理右键点击事件，显示系统级"打开方式"菜单

        Args:
            event: 鼠标事件对象
        """
        logger.debug("右键事件触发: current_image_path=%s", self._current_image_path)

        if self._current_image_path and os.path.exists(self._current_image_path):
            logger.debug("显示右键菜单: %s", self._current_image_path)
            self._show_open_with_menu(event)
        else:
            logger.debug("没有当前图片或文件不存在，调用父类处理")
            # 如果没有当前图片，调用父类的默认处理
            objc.super(AdaptiveImageView, self).rightMouseDown_(event)

    def mouseDragged_(self, event):
        if self.is_space_drag_mode and self.zoom_scale > 1.0 and self.is_dragging:
            # 拖拽图片
            cur_pos = event.locationInWindow()
            dx = cur_pos.x - self.last_mouse_pos.x
            dy = cur_pos.y - self.last_mouse_pos.y
            self.offset_x += dx
            self.offset_y += dy
            self.last_mouse_pos = cur_pos
            self.setNeedsDisplay_(True)
        else:
            objc.super(AdaptiveImageView, self).mouseDragged_(event)

    def keyDown_(self, event):
        # 空格键激活拖拽
        if not event:
            return

        chars = event.characters()
        if chars == " ":
            if self.zoom_scale > 1.0:
                self.is_space_drag_mode = True
                self.window().makeFirstResponder_(self)
                self.resetCursorRects()
                self.setNeedsDisplay_(True)
        else:
            # 使用正确的super调用方式，避免递归
            from AppKit import NSView

            NSView.keyDown_(self, event)

    def keyUp_(self, event):
        if not event:
            return

        chars = event.characters()
        if chars == " ":
            self.is_space_drag_mode = False
            self.is_dragging = False
            self.resetCursorRects()
            self.setNeedsDisplay_(True)
        else:
            # 使用正确的super调用方式，避免递归
            from AppKit import NSView

            NSView.keyUp_(self, event)

    def resetCursorRects(self):
        self.discardCursorRects()
        if self.is_space_drag_mode and self.zoom_scale > 1.0:
            if not self._hand_cursor:
                from AppKit import NSCursor

                self._hand_cursor = NSCursor.alloc().initWithImage_hotSpot_(
                    NSImage.imageNamed_("NSOpenHandCursor"), NSMakePoint(8, 8)
                )
            self.addCursorRect_cursor_(self.bounds(), self._hand_cursor)
        else:
            from AppKit import NSCursor

            self.addCursorRect_cursor_(self.bounds(), NSCursor.arrowCursor())

    def _zoom_to_point(self, event, target_scale):
        # 以点击点为中心缩放到指定比例
        mouse_loc = self.convertPoint_fromView_(event.locationInWindow(), None)
        img_rect = self._get_image_display_rect(self.bounds())
        rel_x = (mouse_loc.x - img_rect.origin.x) / (img_rect.size.width if img_rect.size.width else 1)
        rel_y = (mouse_loc.y - img_rect.origin.y) / (img_rect.size.height if img_rect.size.height else 1)
        cx = img_rect.origin.x + rel_x * img_rect.size.width
        cy = img_rect.origin.y + rel_y * img_rect.size.height
        new_w = img_rect.size.width * target_scale
        new_h = img_rect.size.height * target_scale
        new_x = cx - rel_x * new_w
        new_y = cy - rel_y * new_h
        self.offset_x = new_x - img_rect.origin.x
        self.offset_y = new_y - img_rect.origin.y
        self.zoom_scale = target_scale

        # 同步更新滑块值
        if self.delegate and hasattr(self.delegate, "updateZoomSlider_"):
            self.delegate.updateZoomSlider_(target_scale)

        self.setNeedsDisplay_(True)

    def _get_transformed_rect(self, img_rect):
        # 返回应用缩放和平移后的图片rect
        return NSMakeRect(
            img_rect.origin.x + self.offset_x,
            img_rect.origin.y + self.offset_y,
            img_rect.size.width * self.zoom_scale,
            img_rect.size.height * self.zoom_scale,
        )

    def setDragHighlight_(self, highlight):
        """设置拖拽高亮状态

        Args:
            highlight: 是否显示拖拽高亮效果
        """
        if self._drag_highlight != highlight:
            self._drag_highlight = highlight
            self.setNeedsDisplay_(True)

    def setCurrentImagePath_(self, image_path):
        """设置当前显示的图片路径

        Args:
            image_path: 图片文件路径
        """
        self._current_image_path = image_path
        logger.debug("设置当前图片路径: %s", image_path)

    def _is_browser_app(self, app_path):
        """检查是否为浏览器应用程序

        Args:
            app_path: 应用程序路径

        Returns:
            bool: 是否为浏览器应用程序
        """
        app_name = os.path.basename(app_path).lower()

        # 浏览器应用程序黑名单
        browser_keywords = [
            "115浏览器",
            "115browser",
            "safari",
            "chrome",
            "firefox",
            "edge",
            "opera",
            "brave",
            "vivaldi",
            "arc",
            "browser",
            "浏览器",
            "webkit",
        ]

        # 检查应用程序名称是否包含浏览器关键词
        for keyword in browser_keywords:
            if keyword.lower() in app_name:
                return True

        return False

    def _show_open_with_menu(self, event):
        """显示系统级"打开方式"菜单 - 使用ContextMenuManager重构版本

        ✨ 重构说明: 原180行复杂函数已拆分为专门的ContextMenuManager类
        这个方法现在只负责协调调用，具体逻辑在context_menu_manager模块中。

        Args:
            event: 鼠标事件对象
        """
        try:
            if not self._current_image_path:
                logger.warning("当前图片路径为空，无法显示右键菜单")
                return

            # 使用ContextMenuManager显示菜单
            success = self._context_menu_manager.show_open_with_menu(event, self._current_image_path)

            if not success:
                logger.warning("显示右键菜单失败")

        except Exception as e:
            logger.exception("显示右键菜单失败: %s", e)

    def openWithDefaultApp_(self, sender):
        """使用默认应用程序打开文件

        Args:
            sender: 菜单项对象
        """
        try:
            app_url = sender.representedObject()
            workspace = NSWorkspace.sharedWorkspace()
            file_url = NSURL.fileURLWithPath_(self._current_image_path)

            # 使用正确的API方法
            result, error = workspace.openURLs_withApplicationAtURL_options_configuration_error_(
                [file_url],
                app_url,
                0,  # NSWorkspaceLaunchOptions
                {},
                None,
            )

            if error:
                logger.warning("默认应用程序打开失败: %s", error)
            else:
                # result是NSRunningApplication对象，表示成功启动的应用
                logger.info("成功使用默认应用程序打开文件")
        except Exception as e:
            logger.exception("使用默认应用程序打开文件失败: %s", e)

    def openWithApp_(self, sender):
        """使用指定应用程序打开文件

        Args:
            sender: 菜单项对象
        """
        try:
            app_url = sender.representedObject()
            workspace = NSWorkspace.sharedWorkspace()
            file_url = NSURL.fileURLWithPath_(self._current_image_path)

            # 使用正确的API方法
            result, error = workspace.openURLs_withApplicationAtURL_options_configuration_error_(
                [file_url],
                app_url,
                0,  # NSWorkspaceLaunchOptions
                {},
                None,
            )

            import os

            app_name = os.path.basename(app_url.path()).replace(".app", "")

            if error:
                logger.warning("%s 打开失败: {error}", app_name)
            else:
                # result是NSRunningApplication对象，表示成功启动的应用
                logger.info("成功使用 %s 打开文件", app_name)
        except Exception as e:
            logger.exception("使用指定应用程序打开文件失败: %s", e)

    def openWithOtherApp_(self, sender):
        """使用其他应用程序打开文件（显示文件选择对话框）

        Args:
            sender: 菜单项对象
        """
        try:
            workspace = NSWorkspace.sharedWorkspace()
            # 显示"选择应用程序"对话框
            result = workspace.openFile_withApplication_(self._current_image_path, None)

            if result:
                logger.info("成功显示应用程序选择对话框")
            else:
                logger.warning("应用程序选择对话框显示失败")
        except Exception as e:
            logger.exception("显示应用程序选择对话框失败: %s", e)

    def drawRect_(self, rect):
        NSColor.clearColor().set()
        NSRectFill(rect)

        # 绘制拖拽高亮效果
        if self._drag_highlight:
            self._draw_drag_highlight(rect)

        # 优先绘制CGImage直通
        if hasattr(self, "_cgimage") and self._cgimage is not None:
            try:
                from Quartz import CGContextDrawImage, CGImageGetHeight, CGImageGetWidth

                view_rect = rect
                img_w = float(CGImageGetWidth(self._cgimage) or 1)
                img_h = float(CGImageGetHeight(self._cgimage) or 1)

                # 计算自适应显示区域（与 _get_image_display_rect 等价）
                min_margin = 8
                max_margin = 40
                margin_ratio = 0.03
                margin = int(min(max(view_rect.size.width, view_rect.size.height) * margin_ratio, max_margin))
                margin = max(margin, min_margin)
                avail_w = max(0.0, view_rect.size.width - 2 * margin)
                avail_h = max(0.0, view_rect.size.height - 2 * margin)
                scale = min(avail_w / img_w, avail_h / img_h)
                scaled_w = img_w * scale
                scaled_h = img_h * scale
                x = view_rect.origin.x + (view_rect.size.width - scaled_w) / 2.0
                y = view_rect.origin.y + (view_rect.size.height - scaled_h) / 2.0

                # 应用缩放和平移
                if self.zoom_scale > 1.0 or self.offset_x != 0 or self.offset_y != 0:
                    # 模拟 _get_transformed_rect
                    scaled_w *= self.zoom_scale
                    scaled_h *= self.zoom_scale
                    x = x + self.offset_x
                    y = y + self.offset_y

                # 获取当前图形上下文
                try:
                    from AppKit import NSGraphicsContext

                    ctx = NSGraphicsContext.currentContext().CGContext()
                except Exception:
                    ctx = None

                if ctx is not None:
                    # 由于已启用Quartz的EXIF方向自动变换，CGImage应该已经是正确方向
                    # 直接绘制，不需要额外的坐标系变换
                    from Quartz import CGContextRestoreGState, CGContextSaveGState, CGRectMake

                    CGContextSaveGState(ctx)
                    CGContextDrawImage(ctx, CGRectMake(x, y, scaled_w, scaled_h), self._cgimage)
                    CGContextRestoreGState(ctx)
                return
            except Exception:
                # 回退到NSImage路径
                try:
                    if self._cgimage is not None:
                        from AppKit import NSImage

                        nsimg = NSImage.alloc().initWithCGImage_(self._cgimage)
                        objc.super(AdaptiveImageView, self).setImage_(nsimg)
                        self._cgimage = None
                except Exception:
                    pass

        # 默认NSImage绘制路径
        if self.image():
            img_rect = self._get_image_display_rect(rect)
            if self.zoom_scale > 1.0 or self.offset_x != 0 or self.offset_y != 0:
                img_rect = self._get_transformed_rect(img_rect)

            # 安全获取图像尺寸
            image_size = self.image().size() if self.image() else None
            if image_size is None:
                return

            self.image().drawInRect_fromRect_operation_fraction_(
                img_rect,
                NSMakeRect(0, 0, image_size.width, image_size.height),
                NSCompositingOperationSourceOver,
                1.0,
            )

    def _get_image_display_rect(self, view_rect):
        # 自适应边距 - 优化：减少边距以扩大图片显示区域
        min_margin = 8  # 从12减少到8
        max_margin = 40  # 从60减少到40
        margin_ratio = 0.03  # 从5%减少到3%
        margin = int(min(max(view_rect.size.width, view_rect.size.height) * margin_ratio, max_margin))
        margin = max(margin, min_margin)

        # 获取图像尺寸（支持NSImage和CGImage）
        image_size = None
        if self.image() is not None:
            # NSImage路径
            image_size = self.image().size()
        elif hasattr(self, "_cgimage") and self._cgimage is not None:
            # CGImage路径
            try:
                from Quartz import CGImageGetHeight, CGImageGetWidth

                width = float(CGImageGetWidth(self._cgimage) or 1)
                height = float(CGImageGetHeight(self._cgimage) or 1)
                from AppKit import NSSize

                image_size = NSSize(width, height)
            except Exception:
                # 回退到默认尺寸
                from AppKit import NSSize

                image_size = NSSize(800, 600)
        else:
            # 没有图像时的默认尺寸
            from AppKit import NSSize

            image_size = NSSize(800, 600)

        view_size = view_rect.size
        avail_width = max(0, view_size.width - 2 * margin)
        avail_height = max(0, view_size.height - 2 * margin)
        scale = min(avail_width / image_size.width, avail_height / image_size.height)
        scaled_width = image_size.width * scale
        scaled_height = image_size.height * scale
        x = view_rect.origin.x + (view_size.width - scaled_width) / 2
        y = view_rect.origin.y + (view_size.height - scaled_height) / 2
        return NSMakeRect(x, y, scaled_width, scaled_height)

    # 性能优化方法
    def _schedule_optimized_redraw(self):
        """优化重绘调度 - 防止过度重绘"""
        if self._pending_redraw:
            return

        self._pending_redraw = True

        # 取消之前的定时器
        self._cancel_pending_redraw()

        # 延迟重绘以合并多个请求
        self._redraw_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.016,
            self,
            "performOptimizedRedraw:",
            None,
            False,  # ~60fps
        )

    def performOptimizedRedraw_(self, timer):
        """执行优化重绘"""
        self._pending_redraw = False
        self._redraw_timer = None

        # 清除缓存的图片区域，强制重新计算
        self._cached_img_rect = None

        # 执行实际重绘
        self.setNeedsDisplay_(True)

    def _cancel_pending_redraw(self):
        """取消待处理的重绘"""
        if self._redraw_timer:
            self._redraw_timer.invalidate()
            self._redraw_timer = None
        self._pending_redraw = False

    def _draw_drag_highlight(self, rect):
        """绘制拖拽高亮效果（优化版本）

        使用缓存的颜色对象和优化的绘制路径。

        Args:
            rect: 绘制区域
        """
        try:
            from AppKit import NSBezierPath, NSColor, NSMakeRect

            # 使用缓存的颜色对象（避免重复创建）
            if not hasattr(self, "_highlight_border_color"):
                self._highlight_border_color = NSColor.colorWithRed_green_blue_alpha_(0.2, 0.6, 1.0, 0.8)
                self._highlight_overlay_color = NSColor.colorWithRed_green_blue_alpha_(0.2, 0.6, 1.0, 0.05)

            # 先绘制半透明覆盖层（更轻量）
            self._highlight_overlay_color.setFill()
            NSRectFill(rect)

            # 绘制边框（使用内边距，避免边框被裁切）
            inset_rect = NSMakeRect(rect.origin.x + 2, rect.origin.y + 2, rect.size.width - 4, rect.size.height - 4)

            border_path = NSBezierPath.bezierPathWithRect_(inset_rect)
            border_path.setLineWidth_(3.0)  # 稍微减少线宽
            self._highlight_border_color.setStroke()
            border_path.stroke()

        except Exception as e:
            logger.warning("绘制拖拽高亮效果失败: %s", e)
