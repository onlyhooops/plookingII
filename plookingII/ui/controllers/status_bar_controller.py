import os

import objc
from AppKit import (
    NSColor,
    NSFont,
    NSRect,
    NSSmallControlSize,
    NSTextField,
    NSTimer,
    NSView,
)

"""
状态栏控制器

负责处理状态栏显示、更新和消息提示等逻辑。
集成会话管理器和趣味提示系统，提供有趣且有用的状态信息。

Author: PlookingII Team
"""

import logging

from ...config.constants import APP_NAME
from ...core.session_manager import SessionManager

# pyright: reportUndefinedVariable=false

logger = logging.getLogger(APP_NAME)


class StatusBarController:
    """状态栏控制器，负责状态栏显示和更新"""

    def __init__(self, main_window):
        """初始化状态栏控制器

        Args:
            main_window: MainWindow实例
        """
        self.main_window = main_window
        self.status_bar_view = None
        self.image_seq_label = None
        self.folder_seq_label = None
        self.center_status_label = None
        self._status_timer = None
        self.update_indicator = None  # 图片更新状态指示器

        # 会话管理器
        self.session_manager = SessionManager()

        # 状态更新定时器
        self._session_update_timer = None

        # 状态消息类型 - 趣味功能已移除
        # self._current_message_type = "fun"  # 已移除
        # self._fun_message_display_time = 0  # 已移除
        # self._fun_message_duration = 8.0  # 已移除

    def setup_ui(self, content_view, frame):
        """设置状态栏UI组件

        Args:
            content_view: 窗口内容视图
            frame: 窗口框架
        """
        status_bar_height = 30  # 保持原来的高度
        w = frame.size.width

        # 创建底部状态栏
        status_bar_frame = NSRect((0, 0), (w, status_bar_height))
        self.status_bar_view = NSView.alloc().initWithFrame_(status_bar_frame)
        self.status_bar_view.setWantsLayer_(True)
        # 使用系统窗口背景色（回滚透明度调整）
        self.status_bar_view.setBackgroundColor_(NSColor.windowBackgroundColor())
        content_view.addSubview_(self.status_bar_view)

        # 不再创建左下角文件指示器；左侧用于显示详细状态指示器

        # 定义右侧标签相关变量
        slider_width = 80  # 缩放滑块宽度
        slider_margin = 10  # 缩放滑块边距
        right_label_width = 80  # 右侧标签宽度
        right_margin = slider_width + slider_margin + 10  # 右侧边距

        # 创建缩放滑块 - 在最右侧
        from AppKit import NSSlider, NSSliderTypeLinear

        self.zoom_slider = NSSlider.alloc().initWithFrame_(((w - slider_width - slider_margin, 7), (slider_width, 16)))
        self.zoom_slider.setControlSize_(NSSmallControlSize)  # 小尺寸控件
        self.zoom_slider.setSliderType_(NSSliderTypeLinear)  # 线性滑块
        self.zoom_slider.setMinValue_(1.0)  # 最小缩放：100%
        self.zoom_slider.setMaxValue_(10.0)  # 最大缩放：1000%
        self.zoom_slider.setDoubleValue_(1.0)  # 默认缩放：100%
        self.zoom_slider.setContinuous_(True)  # 连续更新
        self.zoom_slider.setTarget_(self.main_window)  # 设置目标对象
        self.zoom_slider.setAction_(
            objc.selector(self.main_window.zoomSliderChanged_, signature=b"v@:@")
        )  # 设置回调方法
        self.status_bar_view.addSubview_(self.zoom_slider)

        # 创建状态指示器：放置于左下角（恢复靠左对齐）
        left_inset = 10
        center_label_width = w - (right_label_width + right_margin) - (left_inset + 10)
        center_label_width = max(center_label_width, 120)
        self.center_status_label = NSTextField.alloc().initWithFrame_(((left_inset, 5), (center_label_width, 20)))
        self.center_status_label.setEditable_(False)
        self.center_status_label.setBordered_(False)
        self.center_status_label.setDrawsBackground_(False)
        self.center_status_label.setFont_(NSFont.systemFontOfSize_(12))
        self.center_status_label.setAlignment_(0)
        self.center_status_label.setStringValue_("准备开始照片筛选...")
        self.status_bar_view.addSubview_(self.center_status_label)

        # 创建更新状态指示器（在右侧标签前）
        update_indicator_width = 20
        update_indicator_x = w - right_label_width - right_margin - update_indicator_width - 5

        self.update_indicator = NSTextField.alloc().initWithFrame_(
            ((update_indicator_x, 5), (update_indicator_width, 20))
        )
        self.update_indicator.setEditable_(False)
        self.update_indicator.setBordered_(False)
        self.update_indicator.setDrawsBackground_(False)
        self.update_indicator.setFont_(NSFont.systemFontOfSize_(14))
        self.update_indicator.setAlignment_(1)  # 居中对齐
        self.update_indicator.setStringValue_("")  # 初始为空
        self.update_indicator.setHidden_(True)  # 初始隐藏
        self.status_bar_view.addSubview_(self.update_indicator)

        # 创建右侧标签：显示文件夹序号
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

        # 启动会话状态更新定时器
        self.start_session_updates()

    def start_session_updates(self):
        """启动会话状态更新定时器"""
        if self._session_update_timer:
            self._session_update_timer.invalidate()

        # 每5秒更新一次会话状态
        self._session_update_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            5.0, self, "updateSessionStatus:", None, True
        )

    def updateSessionStatus_(self, timer):
        """定时器回调：更新会话状态 - 趣味功能已移除

        Args:
            timer: 定时器对象
        """
        try:
            # 趣味功能已移除，只保留基础状态更新
            # 可以在这里添加其他基础状态更新逻辑
            pass
        except Exception:
            logger.exception("更新会话状态时发生错误")

    def update_fun_status(self):
        """更新基础状态消息 - 趣味功能已移除"""
        if not self.center_status_label:
            return

        try:
            # 获取基础状态消息（不包含趣味内容）
            status_message = self.session_manager.get_fun_message()
            if status_message:
                self.center_status_label.setStringValue_(status_message)

        except Exception:
            logger.exception("更新状态时发生错误")

    def check_milestones(self):
        """检查里程碑并显示提示 - 趣味功能已移除"""
        try:
            # 趣味里程碑功能已移除，不再检查
            pass

        except Exception:
            logger.exception("检查里程碑时发生错误")

    def show_milestone_message(self, message):
        """显示里程碑消息 - 趣味功能已移除

        Args:
            message (str): 里程碑消息
        """
        try:
            # 趣味里程碑功能已移除，不再显示
            pass

        except Exception:
            logger.exception("显示里程碑消息时发生错误")

    def update_frame(self, frame):
        """更新状态栏框架

        Args:
            frame: 新的窗口框架
        """
        status_bar_height = 30  # 保持原来的高度
        width = frame.size.width

        # 更新状态栏框架
        self.status_bar_view.setFrame_(NSRect((0, 0), (width, status_bar_height)))

        # 重新布局状态栏标签
        slider_width = 80  # 缩放滑块宽度
        slider_margin = 10  # 缩放滑块边距
        right_label_width = 80  # 右侧标签宽度
        right_margin = slider_width + slider_margin + 10  # 右侧边距

        # 更新缩放滑块位置
        if hasattr(self, "zoom_slider") and self.zoom_slider:
            self.zoom_slider.setFrame_(((width - slider_width - slider_margin, 7), (slider_width, 16)))

        # 右侧标签位置保持不变
        self.folder_seq_label.setFrame_(((width - right_label_width - right_margin, 5), (right_label_width, 20)))

        # 左下角状态指示器占据左侧区域（恢复靠左对齐）
        left_inset = 10
        center_label_width = width - (right_label_width + right_margin) - (left_inset + 10)
        center_label_width = max(center_label_width, 120)
        self.center_status_label.setFrame_(((left_inset, 5), (center_label_width, 20)))

    def update_status_display(self, current_folder, images, current_index, subfolders, current_subfolder_index):
        """更新状态栏显示信息

        Args:
            current_folder: 当前文件夹路径
            images: 当前文件夹的图片列表
            current_index: 当前图片索引
            subfolders: 子文件夹列表
            current_subfolder_index: 当前子文件夹索引
        """
        # 获取当前文件夹名称
        folder_name = os.path.basename(current_folder) if current_folder else ""

        # 获取当前图片文件名
        current_image_name = (
            os.path.basename(images[current_index]) if images and 0 <= current_index < len(images) else ""
        )

        # 计算分辨率与体积（MB）
        resolution_text = ""
        size_mb_text = ""
        try:
            if current_image_name:
                img_path = images[current_index]
                # 分辨率（安全路径）
                try:
                    from ...core.functions import get_image_dimensions_safe

                    dims = get_image_dimensions_safe(img_path)
                    if dims:
                        resolution_text = f"{dims[0]}x{dims[1]}"
                    else:
                        resolution_text = ""
                except Exception:
                    resolution_text = ""
                # 体积
                try:
                    sz = os.path.getsize(img_path)
                    size_mb_text = f"{sz / (1024 * 1024):.2f}MB"
                except Exception:
                    size_mb_text = ""
        except Exception:
            pass

        # 将文件指示器信息显示在窗口标题栏
        try:
            parts = [folder_name, current_image_name]
            if resolution_text:
                parts.append(resolution_text)
            if size_mb_text:
                parts.append(size_mb_text)
            left_text = "/".join([p for p in parts if p])
            title_text = f"{left_text} | {current_index + 1}/{len(images)}"
            if hasattr(self.main_window, "setTitle_"):
                self.main_window.setTitle_(title_text)
        except Exception:
            pass

        # 更新文件夹序列标签
        self.folder_seq_label.setStringValue_(f"{current_subfolder_index + 1}/{len(subfolders)}")

        # 更新会话管理器状态
        self.update_session_data(images, subfolders, current_index, current_subfolder_index)

        # 状态栏中/左区域：无实时消息时常驻显示“当前所在路径”
        try:
            if not self._status_timer:
                self._set_current_path_text(current_folder)
        except Exception:
            pass

    def update_session_data(self, images, subfolders, current_index, current_subfolder_index):
        """更新会话管理器数据

        Args:
            images: 当前文件夹的图片列表
            subfolders: 子文件夹列表
            current_index: 当前图片索引
            current_subfolder_index: 当前子文件夹索引
        """
        try:
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
            if hasattr(self, "_last_folder_index"):
                if current_subfolder_index > self._last_folder_index:
                    self.session_manager.folder_processed()

            self._last_folder_index = current_subfolder_index

        except Exception:
            logger.exception("更新会话数据时发生错误")

    def set_status_message(self, msg):
        """设置状态消息

        Args:
            msg: 要显示的消息
        """
        self.center_status_label.setStringValue_(msg)

        # 先取消已有定时器
        if self._status_timer:
            self._status_timer.invalidate()
            self._status_timer = None

        # 启动新定时器
        self._status_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            2.0, self.main_window, "clearStatusMessage:", None, False
        )

    def clear_status_message(self):
        """清空状态消息后恢复显示当前路径"""
        self._status_timer = None
        try:
            # 恢复当前路径
            if hasattr(self.main_window, "current_folder"):
                self._set_current_path_text(self.main_window.current_folder)
            else:
                self.center_status_label.setStringValue_("")
        except Exception:
            self.center_status_label.setStringValue_("")

    def _set_current_path_text(self, current_folder):
        """在状态栏中/左区域常驻显示当前所在路径"""
        try:
            text = current_folder or ""
            self.center_status_label.setStringValue_(text)
        except Exception:
            pass

    def set_completion_status(self):
        """设置任务完成状态"""
        try:
            if hasattr(self.main_window, "setTitle_"):
                self.main_window.setTitle_("任务完成 0/0")
        except Exception:
            pass
        self.folder_seq_label.setStringValue_("0/0")

        # 结束会话
        self.session_manager.end_session()

    def set_empty_status(self):
        """设置空状态"""
        try:
            if hasattr(self.main_window, "setTitle_"):
                self.main_window.setTitle_("无图片 0/0")
        except Exception:
            pass
        self.folder_seq_label.setStringValue_("0/0")

    def start_work_session(self):
        """开始工作会话"""
        self.session_manager.start_session()

        # 更新状态标签 - 移除emoji
        if self.center_status_label:
            self.center_status_label.setStringValue_("开始专注工作，保持高效！")

    def end_work_session(self):
        """结束工作会话"""
        self.session_manager.end_session()

        # 显示工作摘要
        self.show_work_summary()

    def show_work_summary(self):
        """显示工作摘要 - 移除emoji"""
        try:
            summary = self.session_manager.get_work_summary()
            summary_text = f"本次工作: {summary['session_duration']} | 总计: {summary['total_work_time']} | 效率: {summary['efficiency']}"

            if self.center_status_label:
                self.center_status_label.setStringValue_(summary_text)

        except Exception:
            logger.exception("显示工作摘要时发生错误")

    def update_zoom_slider(self, scale):
        """更新缩放滑块的值（不触发回调）

        Args:
            scale: 新的缩放比例
        """
        if hasattr(self, "zoom_slider") and self.zoom_slider:
            # 防止缩放滑块回调循环调用
            old_target = self.zoom_slider.target()
            self.zoom_slider.setTarget_(None)
            self.zoom_slider.setDoubleValue_(scale)
            self.zoom_slider.setTarget_(old_target)

    def set_update_indicator(self, has_update: bool):
        """设置图片更新状态指示器

        Args:
            has_update: 是否有更新待处理
        """
        try:
            if not hasattr(self, "update_indicator") or not self.update_indicator:
                return

            if has_update:
                # 显示更新指示（橙色圆点）
                self.update_indicator.setStringValue_("●")
                self.update_indicator.setTextColor_(NSColor.systemOrangeColor())
                self.update_indicator.setHidden_(False)
                self.update_indicator.setToolTip_("图片已更新，点击重新加载")
            else:
                # 隐藏指示器
                self.update_indicator.setHidden_(True)
                self.update_indicator.setStringValue_("")

        except Exception as e:
            logger.error(f"设置更新指示器失败: {e}")

    def cleanup(self):
        """清理资源"""
        if self._session_update_timer:
            self._session_update_timer.invalidate()
            self._session_update_timer = None

        if self._status_timer:
            self._status_timer.invalidate()
            self._status_timer = None

        # 结束会话
        self.session_manager.end_session()
