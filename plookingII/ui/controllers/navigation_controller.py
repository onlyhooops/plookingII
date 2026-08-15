"""
导航控制器

负责处理键盘导航、防抖逻辑和导航状态管理。
"""

import logging
import threading
import time

from AppKit import NSEventModifierFlagCommand, NSTimer

from ...config.constants import APP_NAME
from ...core.performance_optimizer import get_performance_optimizer
from ...imports import logging, threading, time
from ...monitor import get_perf_tracker

# pyright: reportUndefinedVariable=false

logger = logging.getLogger(APP_NAME)


class NavigationController:
    """导航控制器，负责键盘导航和防抖逻辑

    重构版本：集成性能优化器，提供极致的按键响应性能。
    """

    def __init__(self, main_window):
        """初始化导航控制器

        Args:
            main_window: MainWindow实例
        """
        self.main_window = main_window

        # 简单状态枚举
        self._state_idle = 0
        self._state_debouncing = 1
        self._state_navigating = 2
        self._state = self._state_idle

        # 按键防抖动机制
        self._key_debounce_timer = None
        self._pending_navigation = None
        self._last_key_time = 0
        self._key_debounce_delay = 0.015  # 15ms防抖延迟（默认）；快速连击时自适应至5ms
        self._navigation_lock = threading.Lock()
        self._is_navigating = False

        # 防递归机制 - 增强版
        self._processing_key_event = False
        self._recursion_depth = 0
        self._max_recursion_depth = 3

        # 队列式步进：在正在导航时累积额外步数，结束时一次性应用
        # 正数表示向右（next），负数表示向左（prev）
        self._queued_steps = 0

        # 性能优化器集成
        try:
            self._perf_optimizer = get_performance_optimizer()
            logger.debug("NavigationController integrated with PerformanceOptimizer")
        except Exception as e:
            logger.warning("Failed to initialize PerformanceOptimizer: %s", e)
            self._perf_optimizer = None

        # 导航历史记录（用于性能优化）
        self._last_index = None

        # 轻量性能跟踪：记录按键到画面响应的端到端延迟
        self.perf = get_perf_tracker()
        self._nav_press_time = None

    def handle_key_event(self, event):
        """处理键盘事件

        Args:
            event: 键盘事件对象

        Returns:
            bool: 是否已处理该事件
        """
        # 防递归检查 - 增强版
        if self._processing_key_event:
            self._recursion_depth += 1
            if self._recursion_depth > self._max_recursion_depth:
                logger.warning("键盘事件递归深度超过限制(%s)，强制停止处理", self._max_recursion_depth)
                self._recursion_depth = 0
                return False
            logger.debug("正在处理键盘事件，递归深度: %s", self._recursion_depth)
            return False

        try:
            self._processing_key_event = True
            self._recursion_depth = 0

            # 安全检查：确保事件对象有效
            if not event:
                logger.warning("收到无效的键盘事件对象")
                return False

            chars = event.characters()
            modifier_flags = event.modifierFlags()

            # 检查 Command 键组合
            if modifier_flags & NSEventModifierFlagCommand:
                if chars.lower() == "z":
                    # 允许缺少 operation_manager 的精简窗口在测试中通过
                    if hasattr(self.main_window, "operation_manager") and hasattr(
                        self.main_window.operation_manager, "undo_keep_action"
                    ):
                        self.main_window.operation_manager.undo_keep_action()
                    elif hasattr(self.main_window, "undo_keep_action"):
                        self.main_window.undo_keep_action()
                    return True
                if chars == "\uf703":  # Command + 右方向键：跳过当前文件夹
                    if hasattr(self.main_window, "folder_manager") and hasattr(
                        self.main_window.folder_manager, "skip_current_folder"
                    ):
                        self.main_window.folder_manager.skip_current_folder()
                    elif hasattr(self.main_window, "skip_current_folder"):
                        self.main_window.skip_current_folder()
                    return True
                if chars == "\uf702":  # Command + 左方向键：撤销跳过文件夹
                    if hasattr(self.main_window, "folder_manager") and hasattr(
                        self.main_window.folder_manager, "undo_skip_folder"
                    ):
                        self.main_window.folder_manager.undo_skip_folder()
                    elif hasattr(self.main_window, "undo_skip_folder"):
                        self.main_window.undo_skip_folder()
                    return True

            # 导航按键防抖动处理
            if chars == "\uf702":  # 左方向键
                self._handle_navigation_key("left")
                return True
            if chars == "\uf703":  # 右方向键
                self._handle_navigation_key("right")
                return True
            if chars == "\uf701":  # 下方向键，保留图片
                if hasattr(self.main_window, "operation_manager") and hasattr(
                    self.main_window.operation_manager, "keep_current_image"
                ):
                    self.main_window.operation_manager.keep_current_image()
                elif hasattr(self.main_window, "keep_current_image"):
                    self.main_window.keep_current_image()
                return True
            if chars == "\uf700":  # 上方向键，预留功能
                # 功能预留，当前无特殊操作
                return True
            if event.keyCode() == 53:  # ESC 键
                if hasattr(self.main_window, "operation_manager") and hasattr(
                    self.main_window.operation_manager, "exit_current_folder"
                ):
                    self.main_window.operation_manager.exit_current_folder()
                elif hasattr(self.main_window, "exit_current_folder"):
                    self.main_window.exit_current_folder()
                return True

            return False

        except Exception as e:
            logger.warning("导航控制器键盘事件处理失败: %s", e)
            return False
        finally:
            self._processing_key_event = False

    def _handle_navigation_key(self, direction):
        """处理导航按键的防抖动逻辑（性能优化版）

        Args:
            direction: 导航方向 ("left" 或 "right")
        """
        current_time = time.time()
        # 记录本次按键时刻（含队列中的后续按键，最终以最后一次按键计时）
        self._nav_press_time = time.perf_counter()

        # 如果正在导航中，直接更新目标索引，不重复触发
        with self._navigation_lock:
            if self._is_navigating:
                # 正在导航中：仅累积步进，不直接修改索引，避免"操作堆叠"产生额外跳转
                if direction == "right":
                    self._queued_steps += 1
                elif direction == "left":
                    self._queued_steps -= 1
                # 立即更新状态显示（预测性反馈）
                try:
                    predicted = self.main_window.current_index + (1 if direction == "right" else -1)
                    if self.main_window.images:
                        predicted = max(0, min(len(self.main_window.images) - 1, predicted))
                    # 注：预测索引仅用于边界计算，不在此处重复刷新状态栏；
                    # 状态栏由 _update_status_display_immediate（50ms 合并）统一更新，
                    # 避免导航中每次按键都触发整组 AppKit 控件刷新。
                except Exception:
                    pass
                return

            # 记录当前按键时间（用于自适应防抖）
            prev_time = self._last_key_time
            self._last_key_time = current_time

            # 边界检测：在文件夹首/末张图片时，标记为文件夹跳转指令
            # 使 execute_pending_navigation 能直接调用 folder_manager 的跳转方法
            images = getattr(self.main_window, "images", None)
            # 使用 is not None 而非 truthiness 检查，
            # 因为 _show_completion_message 会将 images 置为 []（falsy），
            # 导致 LEFT/RIGHT 键无法正确触发文件夹跳转
            if images is not None and direction == "left" and self.main_window.current_index <= 0:
                self._pending_navigation = "jump_prev"
            elif images is not None and direction == "right" and self.main_window.current_index >= len(images) - 1:
                self._pending_navigation = "jump_next"
            else:
                self._pending_navigation = direction

            # 取消之前的防抖定时器
            if self._key_debounce_timer:
                self._key_debounce_timer.invalidate()

            # 使用性能优化器计算最优防抖时间（轻量入口：
            # 仅计算防抖延迟，不生成按键路径上不会被消费的预加载索引）
            adaptive_delay = self._key_debounce_delay  # 默认值
            if self._perf_optimizer:
                try:
                    adaptive_delay = self._perf_optimizer.calculate_optimal_debounce(current_time)
                    logger.debug("Adaptive debounce: %.1fms", adaptive_delay * 1000)
                except Exception as e:
                    logger.debug("Failed to calculate optimal debounce: %s", e)
                    # 回退到原有的自适应逻辑
                    adaptive_delay = (
                        0.005 if (prev_time and (current_time - prev_time) < 0.12) else self._key_debounce_delay
                    )
            else:
                # 如果优化器不可用，使用原有的自适应逻辑
                adaptive_delay = (
                    0.005 if (prev_time and (current_time - prev_time) < 0.12) else self._key_debounce_delay
                )

            # 设置新的防抖定时器（selector 需带冒号，方法需接收timer参数）
            self._key_debounce_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                adaptive_delay, self.main_window, "executePendingNavigation:", None, False
            )

            # 确保计时器在 CommonModes 下也能触发（避免事件跟踪阶段阻塞）
            try:
                from Foundation import NSRunLoop, NSRunLoopCommonModes

                NSRunLoop.currentRunLoop().addTimer_forMode_(self._key_debounce_timer, NSRunLoopCommonModes)
            except Exception:
                pass
            self._state = self._state_debouncing

    def execute_pending_navigation(self):
        """执行待处理的导航操作（合并队列步进，单次渲染，性能优化版）"""
        press_time = getattr(self, "_nav_press_time", None)
        self._nav_press_time = None
        nav_start = time.perf_counter()
        nav_from_index = getattr(self.main_window, "current_index", 0)
        with self._navigation_lock:
            if not self._pending_navigation:
                return

            self._is_navigating = True
            self._state = self._state_navigating
            pending_action = self._pending_navigation
            self._pending_navigation = None
            queued = self._queued_steps
            # 清零队列，准备一次性应用
            self._queued_steps = 0

        try:
            # 计算总步进：基础一次 + 累积队列
            total_steps = (-1 if pending_action == "left" else (1 if pending_action == "right" else 0)) + queued

            # 若为文件夹跳转指令，优先处理（健壮版）
            if pending_action == "jump_prev":
                if hasattr(self.main_window, "folder_manager"):
                    self.main_window.folder_manager.jump_to_previous_folder()
                elif hasattr(self.main_window, "_jump_to_previous_folder"):
                    self.main_window._jump_to_previous_folder()
                return
            if pending_action == "jump_next":
                if hasattr(self.main_window, "folder_manager"):
                    self.main_window.folder_manager.jump_to_next_folder()
                elif hasattr(self.main_window, "_jump_to_next_folder"):
                    self.main_window._jump_to_next_folder()
                return

            # 应用步进，合并到一次显示，避免多次渲染导致的堆叠感
            if self.main_window.images and isinstance(total_steps, int) and total_steps != 0:
                cur = self.main_window.current_index
                n = len(self.main_window.images)
                target = cur + total_steps
                if target < 0:
                    # 超过左边界 → 跳转上一个文件夹
                    if hasattr(self.main_window, "folder_manager") and hasattr(
                        self.main_window.folder_manager, "jump_to_previous_folder"
                    ):
                        self.main_window.folder_manager.jump_to_previous_folder()
                    elif hasattr(self.main_window, "_jump_to_previous_folder"):
                        self.main_window._jump_to_previous_folder()
                    elif hasattr(self.main_window, "jump_to_previous_folder"):
                        self.main_window.jump_to_previous_folder()
                elif target >= n:
                    # 超过右边界 → 跳转下一个文件夹
                    if hasattr(self.main_window, "folder_manager") and hasattr(
                        self.main_window.folder_manager, "jump_to_next_folder"
                    ):
                        self.main_window.folder_manager.jump_to_next_folder()
                    elif hasattr(self.main_window, "_jump_to_next_folder"):
                        self.main_window._jump_to_next_folder()
                    elif hasattr(self.main_window, "jump_to_next_folder"):
                        self.main_window.jump_to_next_folder()
                else:
                    self.main_window.current_index = target
                    self.main_window._show_current_image_optimized()
            elif pending_action in ("left", "right"):
                # 无队列时保持原有单步行为
                if pending_action == "left":
                    if self.main_window.images and self.main_window.current_index > 0:
                        self.main_window.current_index -= 1
                        self.main_window._show_current_image_optimized()
                    elif self.main_window.images and self.main_window.current_index == 0:
                        self.main_window.folder_manager.jump_to_previous_folder()
                elif pending_action == "right":
                    if self.main_window.images and (self.main_window.current_index < len(self.main_window.images) - 1):
                        self.main_window.current_index += 1
                        self.main_window._show_current_image_optimized()
                    elif self.main_window.images and (
                        self.main_window.current_index == len(self.main_window.images) - 1
                    ):
                        self.main_window.folder_manager.jump_to_next_folder()

            self.main_window._last_keep_action = None  # 跳图后撤回失效

        finally:
            # 轻量性能跟踪：按键 → 画面响应端到端延迟
            try:
                self.perf.record("navigation", (time.perf_counter() - (press_time or nav_start)) * 1000)
            except Exception:
                pass

            # 记录导航后的索引（用于性能优化），并更新预加载方向跟踪
            try:
                current_index = self.main_window.current_index if hasattr(self.main_window, "current_index") else 0
                self._last_index = current_index
                if self._perf_optimizer:
                    self._perf_optimizer.navigation_optimizer.update_direction(nav_from_index, current_index)
            except Exception:
                pass

            # 重置导航状态
            with self._navigation_lock:
                self._is_navigating = False
                self._state = self._state_idle

    def set_debounce_delay(self, delay):
        """设置防抖延迟时间

        Args:
            delay: 延迟时间（秒）
        """
        self._key_debounce_delay = max(0.01, delay)

    def cleanup(self):
        """清理导航控制器资源"""
        if self._key_debounce_timer:
            self._key_debounce_timer.invalidate()
            self._key_debounce_timer = None
