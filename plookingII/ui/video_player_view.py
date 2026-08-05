"""
VideoPlayerView - 视频播放器视图

基于 AVPlayer + AVPlayerLayer 的视频播放组件。
支持：播放/暂停、双击快进/快退（5s步长）、标准播放器控件（进度条、音量、时间）。

Author: PlookingII Team
Version: 2.3.0
"""

import logging

import objc
from AppKit import (
    NSButton,
    NSColor,
    NSFont,
    NSMakeRect,
    NSSlider,
    NSSliderTypeLinear,
    NSTextField,
    NSTimer,
    NSView,
)
from Foundation import NSURL, NSKeyValueObservingOptionNew

from ...config.constants import APP_NAME

logger = logging.getLogger(APP_NAME)

# 安全导入 AVFoundation / CoreMedia
try:
    from AVFoundation import (
        AVLayerVideoGravityResizeAspect,
        AVPlayer,
        AVPlayerItem,
        AVPlayerLayer,
    )
    from CoreMedia import CMTimeGetSeconds, CMTimeMakeWithSeconds

    AVFOUNDATION_AVAIL = True
except Exception:
    AVFOUNDATION_AVAIL = False
    AVPlayer = None
    AVPlayerItem = None
    AVPlayerLayer = None
    CMTimeGetSeconds = None
    CMTimeMakeWithSeconds = None

# KVO 上下文标识
_KVO_CONTEXT = "plookingII_video_kvo"


class VideoPlayerView(NSView):
    """视频播放器视图

    基于 AVPlayer + AVPlayerLayer，提供视频播放、快进/快退、控件等功能。
    """

    SEEK_STEP = 5.0  # 快进/快退步长（秒）

    def initWithFrame_(self, frame):
        self = objc.super(VideoPlayerView, self).initWithFrame_(frame)
        if self is None:
            return None

        self._setup_player()
        self._setup_controls()
        self._kvo_registered = False
        self._current_filepath = None

        return self

    # ── 播放器初始化 ──────────────────────────────────

    def _setup_player(self):
        """初始化 AVPlayer 和 AVPlayerLayer"""
        if not AVFOUNDATION_AVAIL:
            logger.warning("AVFoundation 不可用，VideoPlayerView 将无法工作")
            self.player = None
            self.player_layer = None
            return

        self.setWantsLayer_(True)

        self.player = AVPlayer.alloc().init()
        self.player_layer = AVPlayerLayer.playerLayerWithPlayer_(self.player)
        self.player_layer.setVideoGravity_(AVLayerVideoGravityResizeAspect)
        self.player_layer.setFrame_(self.bounds())
        self.layer().addSublayer_(self.player_layer)

        # 播放进度更新定时器
        self._progress_timer = None

    def _setup_controls(self):
        """初始化播放控件（进度条、播放/暂停、音量、时间标签）"""
        self._controls_visible = True
        controls_height = 36
        margin = 8

        # 控件容器（半透明背景）
        frame = self.bounds()
        controls_frame = NSMakeRect(0, 0, frame.size.width, controls_height)
        self.controls_container = NSView.alloc().initWithFrame_(controls_frame)
        self.controls_container.setWantsLayer_(True)
        self.controls_container.layer().setBackgroundColor_(NSColor.colorWithWhite_alpha_(0.0, 0.55).CGColor())
        self.addSubview_(self.controls_container)

        # 播放/暂停按钮
        btn_x = margin
        btn_y = 6
        btn_w, btn_h = 24, 24
        self.play_pause_btn = NSButton.alloc().initWithFrame_(NSMakeRect(btn_x, btn_y, btn_w, btn_h))
        self.play_pause_btn.setTitle_("▶")
        self.play_pause_btn.setBordered_(False)
        self.play_pause_btn.setFont_(NSFont.systemFontOfSize_(12))
        self.play_pause_btn.setTarget_(self)
        self.play_pause_btn.setAction_("togglePlayPause:")
        self.controls_container.addSubview_(self.play_pause_btn)

        # 时间标签
        time_x = btn_x + btn_w + margin
        time_w = 100
        self.time_label = NSTextField.alloc().initWithFrame_(NSMakeRect(time_x, btn_y + 2, time_w, 20))
        self.time_label.setEditable_(False)
        self.time_label.setBordered_(False)
        self.time_label.setDrawsBackground_(False)
        self.time_label.setFont_(NSFont.monospacedDigitSystemFontOfSize_weight_(11, 0))
        self.time_label.setTextColor_(NSColor.whiteColor())
        self.time_label.setStringValue_("00:00 / 00:00")
        self.controls_container.addSubview_(self.time_label)

        # 进度条
        progress_x = time_x + time_w + margin
        progress_w = frame.size.width - progress_x - margin
        self.progress_slider = NSSlider.alloc().initWithFrame_(NSMakeRect(progress_x, btn_y + 1, progress_w, 20))
        self.progress_slider.setSliderType_(NSSliderTypeLinear)
        self.progress_slider.setMinValue_(0.0)
        self.progress_slider.setMaxValue_(1.0)
        self.progress_slider.setDoubleValue_(0.0)
        self.progress_slider.setTarget_(self)
        self.progress_slider.setAction_("progressSliderChanged:")
        self.controls_container.addSubview_(self.progress_slider)

        # 初始隐藏控件容器，鼠标进入时显示
        self.controls_container.setHidden_(True)

    # ── 布局 ──────────────────────────────────────────

    def setFrame_(self, frame):
        """视图尺寸变化时更新 layer 和控件布局"""
        objc.super(VideoPlayerView, self).setFrame_(frame)
        if self.player_layer:
            self.player_layer.setFrame_(self.bounds())

        if hasattr(self, "controls_container") and self.controls_container:
            controls_height = 36
            margin = 8
            new_frame = NSMakeRect(0, 0, frame.size.width, controls_height)
            self.controls_container.setFrame_(new_frame)

            # 重新布局进度条
            btn_x, btn_y, btn_w = margin, 6, 24
            time_x = btn_x + btn_w + margin
            time_w = 100
            progress_x = time_x + time_w + margin
            progress_w = max(frame.size.width - progress_x - margin, 60)
            self.progress_slider.setFrame_(NSMakeRect(progress_x, btn_y + 1, progress_w, 20))

    # ── 视频加载 ──────────────────────────────────────

    def load_video_(self, filepath: str):
        """加载视频文件

        Args:
            filepath: 视频文件路径
        """
        if not AVFOUNDATION_AVAIL or not self.player:
            logger.warning("AVFoundation 不可用，无法加载视频")
            return

        # 清理上一个视频的 KVO
        self._unregister_kvo()

        self._current_filepath = filepath
        url = NSURL.fileURLWithPath_(filepath)
        player_item = AVPlayerItem.playerItemWithURL_(url)

        # 注册 KVO 监听播放项状态
        player_item.addObserver_forKeyPath_options_context_(self, "status", NSKeyValueObservingOptionNew, None)
        self._kvo_item = player_item
        self._kvo_registered = True

        self.player.replaceCurrentItemWithPlayerItem_(player_item)

        # 注册 player 状态 KVO
        self.player.addObserver_forKeyPath_options_context_(self, "status", NSKeyValueObservingOptionNew, None)
        self.player.addObserver_forKeyPath_options_context_(self, "rate", NSKeyValueObservingOptionNew, None)
        self._kvo_player = self.player

        # 开始进度更新
        self._start_progress_timer()

    # ── 播放控制 ──────────────────────────────────────

    def play(self):
        """开始播放"""
        if self.player:
            self.player.play()
            self._update_play_pause_button()

    def pause(self):
        """暂停播放"""
        if self.player:
            self.player.pause()
            self._update_play_pause_button()

    def toggle_play_pause(self):
        """切换播放/暂停状态"""
        if not self.player:
            return
        if self.is_playing():
            self.pause()
        else:
            # 如果播放到末尾，从头开始
            if self._is_at_end():
                self.seek_to(0.0)
            self.play()

    def togglePlayPause_(self, sender):
        """播放/暂停按钮回调（ObjC selector）"""
        self.toggle_play_pause()

    def seek_forward(self, seconds: float = 5.0):
        """快进指定秒数"""
        if not self.player or not self.player.currentItem():
            return
        current = CMTimeGetSeconds(self.player.currentTime())
        duration = self.duration()
        new_time = min(current + seconds, duration)
        self.seek_to(new_time)

    def seek_backward(self, seconds: float = 5.0):
        """快退指定秒数"""
        if not self.player or not self.player.currentItem():
            return
        current = CMTimeGetSeconds(self.player.currentTime())
        new_time = max(current - seconds, 0.0)
        self.seek_to(new_time)

    def seek_to(self, seconds: float):
        """跳转到指定时间"""
        if not self.player:
            return
        cmtime = CMTimeMakeWithSeconds(seconds, 600)
        self.player.seekToTime_(cmtime)
        self._update_progress_ui()

    def is_playing(self) -> bool:
        """返回是否正在播放"""
        if not self.player:
            return False
        return self.player.rate() != 0.0

    def current_time(self) -> float:
        """返回当前播放时间（秒）"""
        if not self.player or not self.player.currentItem():
            return 0.0
        return CMTimeGetSeconds(self.player.currentTime())

    def duration(self) -> float:
        """返回视频总时长（秒）"""
        if not self.player or not self.player.currentItem():
            return 0.0
        item = self.player.currentItem()
        if item.status() != 1:  # AVPlayerItemStatusReadyToPlay
            return 0.0
        duration_cm = item.duration()
        if duration_cm.isIndefinite():
            return 0.0
        return CMTimeGetSeconds(duration_cm)

    # ── 鼠标交互 ──────────────────────────────────────

    def mouseDown_(self, event):
        """处理鼠标点击：单击切换播放/暂停，双击快进/快退"""
        if event.clickCount() == 2:
            self._handle_double_click(event)
        elif event.clickCount() == 1:
            self.toggle_play_pause()

    def _handle_double_click(self, event):
        """双击处理：左侧快退5s，右侧快进5s"""
        mouse_loc = self.convertPoint_fromView_(event.locationInWindow(), None)
        mid_x = self.bounds().size.width / 2.0

        if mouse_loc.x < mid_x:
            self.seek_backward(self.SEEK_STEP)
        else:
            self.seek_forward(self.SEEK_STEP)

    def mouseMoved_(self, event):
        """鼠标移动时显示控件栏"""
        self._show_controls()

    def mouseEntered_(self, event):
        """鼠标进入视图时显示控件栏"""
        self._show_controls()

    def mouseExited_(self, event):
        """鼠标离开视图时隐藏控件栏"""
        self._hide_controls()

    def _show_controls(self):
        """显示控件栏并重置自动隐藏定时器"""
        if hasattr(self, "controls_container") and self.controls_container:
            self.controls_container.setHidden_(False)
            # 3秒后自动隐藏
            if hasattr(self, "_controls_hide_timer") and self._controls_hide_timer:
                self._controls_hide_timer.invalidate()
            self._controls_hide_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                3.0, self, "_autoHideControls:", None, False
            )

    def _hide_controls(self):
        """隐藏控件栏"""
        if hasattr(self, "controls_container") and self.controls_container:
            self.controls_container.setHidden_(True)

    def _autoHideControls_(self, timer):
        """自动隐藏控件栏定时器回调"""
        self._controls_hide_timer = None
        self._hide_controls()

    # ── 进度条交互 ────────────────────────────────────

    def progressSliderChanged_(self, sender):
        """进度条拖动回调"""
        if not self.player or not self.player.currentItem():
            return
        duration = self.duration()
        if duration <= 0:
            return
        target_seconds = sender.doubleValue() * duration
        self.seek_to(target_seconds)

    # ── KVO ───────────────────────────────────────────

    def observeValueForKeyPath_ofObject_change_context_(self, keyPath, obj, change, context):
        """KVO 回调：监听播放器状态变化"""
        if keyPath == "status":
            if obj == self.player:
                status = self.player.status()
                if status == 1:  # AVPlayerStatusReadyToPlay
                    logger.debug("AVPlayer 就绪")
            elif hasattr(self, "_kvo_item") and obj == self._kvo_item:
                status = obj.status()
                if status == 1:  # AVPlayerItemStatusReadyToPlay
                    logger.debug("AVPlayerItem 就绪，开始播放")
                    self.play()
                elif status == 2:  # AVPlayerItemStatusFailed
                    error = obj.error()
                    logger.warning("视频加载失败: %s", error)
        elif keyPath == "rate":
            self._update_play_pause_button()

    def _unregister_kvo(self):
        """取消所有 KVO 注册"""
        try:
            if self._kvo_registered and hasattr(self, "_kvo_item") and self._kvo_item:
                try:
                    self._kvo_item.removeObserver_forKeyPath_(self, "status")
                except Exception:
                    pass
            if hasattr(self, "_kvo_player") and self._kvo_player:
                try:
                    self._kvo_player.removeObserver_forKeyPath_(self, "status")
                except Exception:
                    pass
                try:
                    self._kvo_player.removeObserver_forKeyPath_(self, "rate")
                except Exception:
                    pass
        except Exception as e:
            logger.debug("KVO 清理异常: %s", e)
        self._kvo_item = None
        self._kvo_player = None
        self._kvo_registered = False

    # ── UI 更新 ───────────────────────────────────────

    def _start_progress_timer(self):
        """启动进度更新定时器（0.25s 间隔）"""
        self._stop_progress_timer()
        self._progress_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.25, self, "_updateProgressTick:", None, True
        )

    def _stop_progress_timer(self):
        """停止进度更新定时器"""
        if self._progress_timer:
            self._progress_timer.invalidate()
            self._progress_timer = None

    def _updateProgressTick_(self, timer):
        """定时器回调：更新进度条和时间标签"""
        self._update_progress_ui()

    def _update_progress_ui(self):
        """更新进度条和时间标签"""
        if not self.player or not self.player.currentItem():
            return

        current = self.current_time()
        duration = self.duration()

        if duration > 0:
            # 更新进度条
            if not self.progress_slider.window() or not self.progress_slider.window().isKeyWindow():
                pass  # 避免在未聚焦窗口更新
            try:
                self.progress_slider.setDoubleValue_(current / duration)
            except Exception:
                pass

        # 更新时间标签
        current_str = self._format_time(current)
        duration_str = self._format_time(duration) if duration > 0 else "--:--"
        self.time_label.setStringValue_(f"{current_str} / {duration_str}")

    def _update_play_pause_button(self):
        """更新播放/暂停按钮状态"""
        if not hasattr(self, "play_pause_btn") or not self.play_pause_btn:
            return
        if self.is_playing():
            self.play_pause_btn.setTitle_("⏸")
        else:
            self.play_pause_btn.setTitle_("▶")

    def _is_at_end(self) -> bool:
        """检查是否播放到末尾"""
        duration = self.duration()
        if duration <= 0:
            return False
        return self.current_time() >= duration - 0.5

    @staticmethod
    def _format_time(seconds: float) -> str:
        """格式化时间（秒 → MM:SS）"""
        total_seconds = int(seconds)
        minutes = total_seconds // 60
        secs = total_seconds % 60
        return f"{minutes:02d}:{secs:02d}"

    # ── 资源清理 ──────────────────────────────────────

    def cleanup(self):
        """清理播放器资源"""
        self._stop_progress_timer()

        if hasattr(self, "_controls_hide_timer") and self._controls_hide_timer:
            self._controls_hide_timer.invalidate()
            self._controls_hide_timer = None

        if self.player:
            self.player.pause()
            self._unregister_kvo()
            self.player.replaceCurrentItemWithPlayerItem_(None)
            self.player = None

        if self.player_layer:
            self.player_layer.removeFromSuperlayer()
            self.player_layer = None

        self._current_filepath = None

    def dealloc(self):
        """析构时清理"""
        self.cleanup()
        objc.super(VideoPlayerView, self).dealloc()
