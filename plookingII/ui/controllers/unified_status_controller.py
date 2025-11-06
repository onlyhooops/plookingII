#!/usr/bin/env python3
"""
统一状态控制器

将StatusBarController和TitlebarController合并为单一控制器，
简化UI层架构，减少组件数量和维护复杂度。

主要功能：
- 状态栏管理和显示
- 标题栏管理和更新
- 统一的状态信息更新
- 会话管理集成
- 简化的消息提示

Author: PlookingII Team
"""

import objc
from AppKit import NSColor, NSFont, NSRect, NSTextField, NSTitlebarAccessoryViewController, NSView

from ...config.constants import APP_NAME
from ...core.session_manager import SessionManager
from ...imports import logging, objc

# pyright: reportUndefinedVariable=false

logger = logging.getLogger(APP_NAME)


class UnifiedStatusController:
    """统一状态控制器

    合并了状态栏和标题栏的管理功能，提供统一的状态显示和更新接口。
    减少了组件数量，简化了UI层架构。
    """

    def __init__(self, main_window):
        """初始化统一状态控制器

        Args:
            main_window: MainWindow实例
        """
        self.main_window = main_window

        # 状态栏组件
        self.status_bar_view = None
        self.image_seq_label = None
        self.folder_seq_label = None
        self.center_status_label = None
        self.zoom_slider = None  # 添加缩放滑块引用

        # 标题栏组件
        self.window = main_window
        self.titlebar_accessory = None
        self.titlebar_container = None
        self.titlebar_info_label = None
        self._tracking_area = None
        self._hide_timer = None
        self._overlay_height = 36

        # 定时器
        self._status_timer = None
        self._session_update_timer = None

        # 会话管理器
        self.session_manager = SessionManager()

        logger.info("UnifiedStatusController initialized")

    def setup_ui(self, content_view, frame):
        """设置用户界面组件

        Args:
            content_view: 内容视图
            frame: 窗口框架
        """
        try:
            self._setup_status_bar(content_view, frame)
            self._setup_titlebar()
            self._start_session_updates()
            logger.info("UnifiedStatusController UI setup completed")
        except Exception as e:
            logger.exception("Failed to setup UI: %s", e)

    def _setup_status_bar(self, content_view, frame):
        """设置状态栏 - 与原始StatusBarController保持一致"""
        try:
            # 使用与原版相同的高度和布局
            status_bar_height = 30  # 保持原来的高度
            w = frame.size.width

            # 创建底部状态栏
            status_bar_frame = NSRect((0, 0), (w, status_bar_height))
            self.status_bar_view = NSView.alloc().initWithFrame_(status_bar_frame)
            self.status_bar_view.setWantsLayer_(True)
            # 使用系统窗口背景色
            self.status_bar_view.setBackgroundColor_(NSColor.windowBackgroundColor())
            content_view.addSubview_(self.status_bar_view)

            # 创建状态标签 - 使用原版布局
            self._create_status_labels_original_layout(w, status_bar_height)

            # 启动会话状态更新定时器
            self._start_session_updates()

            logger.debug("Status bar setup completed")

        except Exception as e:
            logger.exception("Failed to setup status bar: %s", e)

    def _create_status_labels_original_layout(self, w, status_bar_height):
        """创建状态标签 - 完全按照原版StatusBarController的布局"""
        try:
            # 定义右侧标签相关变量（与原版完全一致）
            slider_width = 80  # 缩放滑块宽度
            slider_margin = 10  # 缩放滑块边距
            right_label_width = 80  # 右侧标签宽度
            right_margin = slider_width + slider_margin + 10  # 右侧边距

            # 创建缩放滑块 - 在最右侧（与原版完全一致）
            from AppKit import NSSlider, NSSliderTypeLinear, NSSmallControlSize

            self.zoom_slider = NSSlider.alloc().initWithFrame_(
                ((w - slider_width - slider_margin, 7), (slider_width, 16))
            )
            self.zoom_slider.setControlSize_(NSSmallControlSize)  # 小尺寸控件
            self.zoom_slider.setSliderType_(NSSliderTypeLinear)  # 线性滑块
            self.zoom_slider.setMinValue_(1.0)  # 最小缩放：100%
            self.zoom_slider.setMaxValue_(10.0)  # 最大缩放：1000%
            self.zoom_slider.setDoubleValue_(1.0)  # 默认缩放：100%
            self.zoom_slider.setContinuous_(True)  # 连续更新

            # 设置目标和动作 - 连接到主窗口的缩放方法
            if hasattr(self.main_window, "zoomSliderChanged_"):
                self.zoom_slider.setTarget_(self.main_window)
                self.zoom_slider.setAction_(objc.selector(self.main_window.zoomSliderChanged_, signature=b"v@:@"))

            self.status_bar_view.addSubview_(self.zoom_slider)

            # 创建状态指示器：放置于左下角（与原版一致）
            center_label_width = w - (right_label_width + right_margin) - 20
            center_label_width = max(center_label_width, 120)
            self.center_status_label = NSTextField.alloc().initWithFrame_(((10, 5), (center_label_width, 20)))
            self.center_status_label.setEditable_(False)
            self.center_status_label.setBordered_(False)
            self.center_status_label.setDrawsBackground_(False)
            self.center_status_label.setFont_(NSFont.systemFontOfSize_(12))
            self.center_status_label.setAlignment_(0)
            self.center_status_label.setStringValue_("准备开始照片筛选...")
            self.status_bar_view.addSubview_(self.center_status_label)

            # 创建右侧标签：显示文件夹序号（与原版一致）
            self.folder_seq_label = NSTextField.alloc().initWithFrame_(
                ((w - right_label_width - right_margin, 5), (right_label_width, 20))
            )
            self.folder_seq_label.setEditable_(False)
            self.folder_seq_label.setBordered_(False)
            self.folder_seq_label.setDrawsBackground_(False)
            self.folder_seq_label.setFont_(NSFont.systemFontOfSize_(12))
            self.folder_seq_label.setAlignment_(2)
            self.folder_seq_label.setStringValue_("0/0")
            self.status_bar_view.addSubview_(self.folder_seq_label)

            # 为了兼容性，创建image_seq_label的引用
            self.image_seq_label = self.folder_seq_label  # 指向同一个标签

        except Exception as e:
            logger.exception("Failed to create status labels: %s", e)

    def _create_status_labels(self, frame):
        """创建状态标签 - 废弃方法，保留以防兼容性问题"""
        logger.warning("_create_status_labels is deprecated, use _create_status_labels_original_layout instead")

    def _create_label(self, frame, text, font, alignment=0):
        """创建标签组件"""
        label = NSTextField.alloc().initWithFrame_(frame)
        label.setStringValue_(text)
        label.setFont_(font)
        label.setAlignment_(alignment)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        label.setTextColor_(NSColor.secondaryLabelColor())
        return label

    def _setup_titlebar(self):
        """设置标题栏"""
        try:
            self._create_titlebar_accessory()
            self._setup_titlebar_views()
            logger.debug("Titlebar setup completed")
        except Exception as e:
            logger.exception("Failed to setup titlebar: %s", e)

    def _create_titlebar_accessory(self):
        """创建标题栏附件"""
        try:
            AVC = NSTitlebarAccessoryViewController
            self.titlebar_accessory = AVC.alloc().init()
            self.titlebar_accessory.setLayoutAttribute_(1)  # NSLayoutAttributeTop

            # 创建容器视图
            from AppKit import (
                NSVisualEffectBlendingModeBehindWindow,
                NSVisualEffectMaterialTitlebar,
                NSVisualEffectView,
            )

            self.titlebar_container = NSVisualEffectView.alloc().init()
            self.titlebar_container.setMaterial_(NSVisualEffectMaterialTitlebar)
            self.titlebar_container.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
            self.titlebar_container.setAutoresizingMask_(2)  # NSViewWidthSizable

            self.titlebar_accessory.setView_(self.titlebar_container)

            # 添加到窗口
            if hasattr(self.window, "addTitlebarAccessoryViewController_"):
                self.window.addTitlebarAccessoryViewController_(self.titlebar_accessory)

        except Exception as e:
            logger.exception("Failed to create titlebar accessory: %s", e)

    def _setup_titlebar_views(self):
        """设置标题栏视图"""
        try:
            if not self.titlebar_container:
                return

            # 创建信息标签
            self.titlebar_info_label = NSTextField.alloc().init()
            self.titlebar_info_label.setStringValue_("PlookingII")
            self.titlebar_info_label.setFont_(NSFont.systemFontOfSize_(13))
            self.titlebar_info_label.setAlignment_(1)  # NSTextAlignmentCenter
            self.titlebar_info_label.setBezeled_(False)
            self.titlebar_info_label.setDrawsBackground_(False)
            self.titlebar_info_label.setEditable_(False)
            self.titlebar_info_label.setSelectable_(False)
            self.titlebar_info_label.setTextColor_(NSColor.secondaryLabelColor())

            # 使用Auto Layout
            self.titlebar_info_label.setTranslatesAutoresizingMaskIntoConstraints_(False)
            self.titlebar_container.addSubview_(self.titlebar_info_label)

            # 设置约束
            self._setup_titlebar_constraints()

        except Exception as e:
            logger.exception("Failed to setup titlebar views: %s", e)

    def _setup_titlebar_constraints(self):
        """设置标题栏约束"""
        try:
            if not self.titlebar_info_label or not self.titlebar_container:
                return

            from AppKit import (
                NSLayoutAttributeCenterX,
                NSLayoutAttributeCenterY,
                NSLayoutAttributeHeight,
                NSLayoutConstraint,
                NSLayoutRelationEqual,
            )

            # 水平居中
            center_x = NSLayoutConstraint.constraintWithItem_attribute_relatedBy_toItem_attribute_multiplier_constant_(
                self.titlebar_info_label,
                NSLayoutAttributeCenterX,
                NSLayoutRelationEqual,
                self.titlebar_container,
                NSLayoutAttributeCenterX,
                1.0,
                0.0,
            )

            # 垂直居中
            center_y = NSLayoutConstraint.constraintWithItem_attribute_relatedBy_toItem_attribute_multiplier_constant_(
                self.titlebar_info_label,
                NSLayoutAttributeCenterY,
                NSLayoutRelationEqual,
                self.titlebar_container,
                NSLayoutAttributeCenterY,
                1.0,
                0.0,
            )

            # 设置高度
            height = NSLayoutConstraint.constraintWithItem_attribute_relatedBy_toItem_attribute_multiplier_constant_(
                self.titlebar_container,
                NSLayoutAttributeHeight,
                NSLayoutRelationEqual,
                None,
                0,
                1.0,
                self._overlay_height,
            )

            # 激活约束
            self.titlebar_container.addConstraints_([center_x, center_y, height])

        except Exception as e:
            logger.exception("Failed to setup titlebar constraints: %s", e)

    def _start_session_updates(self):
        """启动会话更新定时器"""
        try:
            if hasattr(self, "_session_update_timer_active"):
                self._session_update_timer_active = False

            # 简化的定时器实现，使用Python threading代替NSTimer
            import threading

            def update_timer():
                while hasattr(self, "_session_update_timer_active") and self._session_update_timer_active:
                    try:
                        self.updateSessionStatus_(None)
                    except Exception:
                        logger.debug("Session status update failed", exc_info=True)
                    threading.Event().wait(5.0)

            self._session_update_timer_active = True
            self._session_update_timer = threading.Thread(target=update_timer, daemon=True)
            self._session_update_timer.start()

            logger.debug("Session update timer started")

        except Exception as e:
            logger.exception("Failed to start session updates: %s", e)

    def updateSessionStatus_(self, timer):
        """更新会话状态"""
        try:
            if not self.session_manager or not self.center_status_label:
                return

            # 获取会话信息
            session_info = self.session_manager.get_session_summary()
            if session_info and "display_message" in session_info:
                self.center_status_label.setStringValue_(session_info["display_message"])

        except Exception as e:
            logger.exception("Failed to update session status: %s", e)

    def update_image_sequence(self, current, total):
        """更新图像序列信息

        Args:
            current: 当前图像索引
            total: 总图像数量
        """
        try:
            if self.image_seq_label:
                text = f"图像: {current}/{total}"
                self.image_seq_label.setStringValue_(text)
        except Exception as e:
            logger.exception("Failed to update image sequence: %s", e)

    def update_folder_sequence(self, current, total):
        """更新文件夹序列信息

        Args:
            current: 当前文件夹索引
            total: 总文件夹数量
        """
        try:
            if self.folder_seq_label:
                text = f"文件夹: {current}/{total}"
                self.folder_seq_label.setStringValue_(text)
        except Exception as e:
            logger.exception("Failed to update folder sequence: %s", e)

    def update_status_message(self, message):
        """更新状态消息

        Args:
            message: 要显示的消息
        """
        try:
            if self.center_status_label:
                self.center_status_label.setStringValue_(str(message))
        except Exception as e:
            logger.exception("Failed to update status message: %s", e)

    def update_titlebar_text(self, text):
        """更新标题栏文本

        Args:
            text: 要显示的文本
        """
        try:
            if self.titlebar_info_label:
                self.titlebar_info_label.setStringValue_(str(text))
        except Exception as e:
            logger.exception("Failed to update titlebar text: %s", e)

    def show_temporary_message(self, message, duration=3.0):
        """显示临时消息

        Args:
            message: 消息内容
            duration: 显示时长（秒）
        """
        try:
            self.update_status_message(message)

            # 设置定时器恢复原状态
            if self._status_timer:
                self._status_timer.cancel()

            # 使用Python threading.Timer代替NSTimer
            import threading

            self._status_timer = threading.Timer(duration, self.restoreStatusMessage_, [None])
            self._status_timer.start()

        except Exception as e:
            logger.exception("Failed to show temporary message: %s", e)

    def restoreStatusMessage_(self, timer):
        """恢复状态消息"""
        try:
            self.update_status_message("就绪")
        except Exception as e:
            logger.exception("Failed to restore status message: %s", e)

    def get_session_stats(self):
        """获取会话统计信息

        Returns:
            dict: 会话统计数据
        """
        try:
            if self.session_manager:
                return self.session_manager.get_session_summary()
            return {}
        except Exception as e:
            logger.exception("Failed to get session stats: %s", e)
            return {}

    def update_session_data(self, images, subfolders, current_index, current_subfolder_index):
        """更新会话管理器数据 - 兼容原版StatusBarController

        Args:
            images: 当前文件夹的图片列表
            subfolders: 子文件夹列表
            current_index: 当前图片索引
            current_subfolder_index: 当前子文件夹索引
        """
        try:
            if not self.session_manager:
                return

            # 设置图片和文件夹总数
            if images:
                self.session_manager.set_image_count(len(images))

            if subfolders:
                self.session_manager.set_folder_count(len(subfolders))

            # 标记图片已浏览（如果索引发生变化）
            if hasattr(self, "_last_image_index"):
                if current_index > self._last_image_index:
                    self.session_manager.image_viewed()
                elif current_index < self._last_image_index:
                    # 向后浏览，重置计数
                    self.session_manager.images_viewed = current_index

            self._last_image_index = current_index

            # 标记文件夹已处理
            if hasattr(self, "_last_folder_index") and current_subfolder_index > self._last_folder_index:
                self.session_manager.folder_processed()

            self._last_folder_index = current_subfolder_index

        except Exception as e:
            logger.exception("Failed to update session data: %s", e)

    def set_status_message(self, message):
        """设置状态消息 - 兼容原版StatusBarController"""
        self.update_status_message(message)

    def update_folder_label(self, current, total):
        """更新文件夹标签 - 兼容原版StatusBarController"""
        self.update_folder_sequence(current, total)

    def update_image_label(self, current, total):
        """更新图像标签 - 兼容原版StatusBarController"""
        self.update_image_sequence(current, total)

    def update_frame(self, frame):
        """更新窗口框架尺寸 - 兼容原版StatusBarController"""
        try:
            if self.status_bar_view:
                # 更新状态栏视图的宽度
                current_frame = self.status_bar_view.frame()
                new_frame = ((0, 0), (frame.size.width, current_frame.size.height))
                self.status_bar_view.setFrame_(new_frame)

                # 更新右侧组件的位置
                if self.zoom_slider:
                    slider_width = 80
                    slider_margin = 10
                    slider_frame = ((frame.size.width - slider_width - slider_margin, 7), (slider_width, 16))
                    self.zoom_slider.setFrame_(slider_frame)

                if self.folder_seq_label:
                    right_label_width = 80
                    right_margin = 90 + 10  # slider_width + slider_margin + 10
                    folder_frame = ((frame.size.width - right_label_width - right_margin, 5), (right_label_width, 20))
                    self.folder_seq_label.setFrame_(folder_frame)

                if self.center_status_label:
                    # 更新中央标签的宽度
                    center_label_width = frame.size.width - 200 - 20  # 左右留出空间
                    center_label_width = max(center_label_width, 120)
                    center_frame = ((10, 5), (center_label_width, 20))
                    self.center_status_label.setFrame_(center_frame)

        except Exception as e:
            logger.exception("Failed to update frame: %s", e)

    def start_work_session(self):
        """启动工作会话 - 兼容原版StatusBarController"""
        try:
            if self.session_manager:
                self.session_manager.start_session()
                logger.debug("Work session started")
        except Exception as e:
            logger.exception("Failed to start work session: %s", e)

    def stop_work_session(self):
        """停止工作会话 - 兼容原版StatusBarController"""
        try:
            if self.session_manager:
                self.session_manager.stop_session()
                logger.debug("Work session stopped")
        except Exception as e:
            logger.exception("Failed to stop work session: %s", e)

    def update_current_image_path(self, image_path):
        """更新当前图片路径显示

        Args:
            image_path: 图片完整路径
        """
        try:
            if self.center_status_label and image_path:
                # 只显示路径，不显示文件名
                import os

                directory_path = os.path.dirname(image_path)
                if directory_path:
                    self.center_status_label.setStringValue_(directory_path)
                else:
                    self.center_status_label.setStringValue_("当前目录")
        except Exception as e:
            logger.exception("Failed to update current image path: %s", e)

    def update_zoom_slider(self, scale):
        """更新缩放滑块 - 兼容性方法

        Args:
            scale: 缩放比例
        """
        try:
            if self.zoom_slider:
                # 更新缩放滑块的值
                self.zoom_slider.setFloatValue_(scale)
                logger.debug("Updated zoom slider to scale: %s", scale)
        except Exception as e:
            logger.exception("Failed to update zoom slider: %s", e)

    def cleanup(self):
        """清理资源"""
        try:
            # 停止定时器
            if self._status_timer:
                self._status_timer.cancel()
                self._status_timer = None

            if hasattr(self, "_session_update_timer_active"):
                self._session_update_timer_active = False
                self._session_update_timer = None

            if self._hide_timer:
                self._hide_timer.cancel()
                self._hide_timer = None

            # 清理会话管理器
            if self.session_manager:
                self.session_manager = None

            logger.info("UnifiedStatusController cleanup completed")

        except Exception as e:
            logger.exception("Failed to cleanup: %s", e)

    def __del__(self):
        """析构函数"""
        self.cleanup()


# 向后兼容的别名
StatusBarController = UnifiedStatusController
TitlebarController = UnifiedStatusController
