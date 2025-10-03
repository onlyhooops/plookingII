from AppKit import NSColor, NSRect, NSView

"""
图像视图控制器模块

提供PlookingII应用程序的图像显示和交互控制功能。
负责管理图像视图、缩放控制、覆盖层等UI组件的生命周期和状态。

主要功能：
    - 图像视图的创建和配置
    - 缩放控制和滑块管理
    - 覆盖层视图管理
    - 视图框架的动态调整
    - 图像显示和清除

核心组件：
    - ImageViewController: 主要的图像视图控制器类
    - 自适应图像视图 (AdaptiveImageView)
    - 覆盖层视图 (OverlayView)
    - 缩放滑块 (NSSlider)

Author: PlookingII Team
Version: 1.0.0
"""

# pyright: reportUndefinedVariable=false
import logging

from ...config.constants import APP_NAME, IMAGE_PROCESSING_CONFIG
from ..views import AdaptiveImageView, OverlayView

logger = logging.getLogger(APP_NAME)


class ImageViewController:
    """图像视图控制器，负责图像显示和UI交互

    管理图像视图的完整生命周期，包括创建、配置、更新和清理。
    提供统一的接口来操作图像显示相关的UI组件。

    主要职责：
        - 图像视图的初始化和配置
        - 缩放控制和用户交互
        - 视图框架的动态调整
        - 图像显示和状态管理

    Attributes:
        main_window: MainWindow实例，用于访问窗口组件
        image_view: 主要的图像显示视图
        overlay: 覆盖层视图
        zoom_slider: 缩放控制滑块
        main_image_view: 图像视图的容器视图
    """

    def __init__(self, main_window):
        """初始化图像视图控制器

        Args:
            main_window: MainWindow实例，用于访问窗口组件和设置委托关系
        """
        self.main_window = main_window
        self.image_view = None
        self.overlay = None
        self.zoom_slider = None
        self.main_image_view = None

    def setup_ui(self, content_view, frame):
        """设置图像视图相关的UI组件

        创建并配置图像显示区域、覆盖层和缩放控制等UI组件。
        这些组件构成了图像浏览的核心界面。

        Args:
            content_view: 窗口内容视图，用于添加子视图
            frame: 窗口框架，用于计算组件尺寸和位置

        Note:
            - 状态栏高度固定为30像素
            - 图像视图占据除状态栏外的所有空间
            - 覆盖层和图像视图重叠，提供辅助显示
            - 缩放滑块位于右下角，便于用户操作
        """
        status_bar_height = 30

        # 创建主图片显示区域（容器视图）
        main_image_frame = (
            NSRect((0, status_bar_height), (frame.size.width, frame.size.height - status_bar_height))
        )
        self.main_image_view = NSView.alloc().initWithFrame_(main_image_frame)
        self.main_image_view.setWantsLayer_(True)
        self.main_image_view.setBackgroundColor_(NSColor.windowBackgroundColor())
        content_view.addSubview_(self.main_image_view)

        # 创建自适应图片视图（主要的图像显示组件）
        image_view_frame = NSRect((0, 0), (frame.size.width, frame.size.height - status_bar_height))
        self.image_view = AdaptiveImageView.alloc().initWithFrame_(image_view_frame)
        self.image_view.delegate = self.main_window
        self.main_image_view.addSubview_(self.image_view)

        # 创建覆盖层（预留用于拖拽高亮等功能）
        self.overlay = (
            OverlayView.alloc().initWithFrame_andImageView_(image_view_frame, self.image_view)
        )
        self.main_image_view.addSubview_(self.overlay)

        # 缩放滑块现在在状态栏控制器中创建
        self.zoom_slider = None

    def update_frame(self, frame):
        """更新视图框架

        当窗口大小改变时，动态调整所有相关组件的尺寸和位置。
        确保UI组件始终正确填充可用空间。

        Args:
            frame: 新的窗口框架，包含更新后的尺寸信息

        Note:
            - 所有子视图都会同步更新框架
            - 保持状态栏高度不变
            - 缩放滑块位置由状态栏控制器管理
            - 更新后自动触发重绘
        """
        status_bar_height = 30
        width = frame.size.width
        height = frame.size.height

        # 更新主图片视图框架（容器视图）
        self.main_image_view.setFrame_(NSRect((0, status_bar_height), (width, height - status_bar_height)))

        # 更新图像视图框架（主要显示区域）
        self.image_view.setFrame_(NSRect((0, 0), (width, height - status_bar_height)))

        # 更新覆盖层框架（辅助显示）
        if self.overlay:
            self.overlay.setFrame_(NSRect((0, 0), (width, height - status_bar_height)))

        # 缩放滑块位置由状态栏控制器管理

        # 触发重绘，确保显示正确
        self.image_view.setNeedsDisplay_(True)

    def display_image(self, image):
        """显示图像

        Args:
            image: 要显示的图像对象
        """
        if not self.image_view:
            return

        # 兼容 CGImage 与 NSImage：优先直通CGImage到视图绘制，避免过早包装为NSImage
        try:
            from AppKit import NSImage

        except Exception:
            NSImage = None

        try:
            is_nsimage = NSImage is not None and isinstance(image, NSImage)
        except Exception:
            is_nsimage = False

        if not is_nsimage:
            # 直通CGImage
            try:
                if hasattr(self.image_view, "setCGImage_"):
                    self.image_view.setCGImage_(image)
                    return
            except Exception:
                pass
        # 默认路径：NSImage
        self.image_view.setImage_(image)
        self.image_view.setNeedsDisplay_(True)

    def clear_image(self):
        """清空图像显示"""
        if self.image_view:
            self.image_view.setImage_(None)
            self.image_view.setNeedsDisplay_(True)


    def update_zoom_slider(self, scale):
        """更新缩放滑块值（不触发回调）

        Args:
            scale: 新的缩放比例
        """
        # 委托给状态栏控制器更新缩放滑块
        if hasattr(self.main_window, "status_bar_controller"):
            self.main_window.status_bar_controller.update_zoom_slider(scale)

    def get_target_size_for_view(self, scale_factor=2):
        """获取视图的目标尺寸

        Args:
            scale_factor: 缩放因子

        Returns:
            tuple: (width, height) 目标尺寸
        """
        try:
            view_frame = self.image_view.frame()
            return (int(view_frame.size.width * scale_factor), int(view_frame.size.height * scale_factor))
        except Exception:
            logger.debug("get_target_size_for_view fallback", exc_info=True)
            return (
                IMAGE_PROCESSING_CONFIG["max_preview_resolution"],
                IMAGE_PROCESSING_CONFIG["max_preview_resolution"],
            )
