"""
UI控制器模块

提供PlookingII应用程序的用户界面控制器类，负责处理用户界面逻辑和交互。
这些控制器类管理UI组件的生命周期、用户输入处理和界面状态更新。

主要控制器：
    - ImageViewController: 图像视图控制，管理图像显示、缩放、覆盖层等
    - UnifiedStatusController: 统一状态控制，管理状态栏和标题栏
    - NavigationController: 导航控制，处理键盘输入和导航操作

v1.1.0 架构简化：
    - 合并StatusBarController和TitlebarController为UnifiedStatusController
    - 减少控制器数量，简化UI层架构
    - 保持向后兼容的别名

设计特点：
    - MVC架构：控制器负责协调模型和视图
    - 事件驱动：响应用户输入和系统事件
    - 状态管理：维护UI组件的状态一致性
    - 委托模式：通过委托与主窗口通信

Author: PlookingII Team
Version: 1.1.0
"""

import logging

from .drag_drop_controller import DragDropController
from .image_view_controller import ImageViewController
from .menu_controller import MenuController
from .navigation_controller import NavigationController
from .rotation_controller import RotationController
from .system_controller import SystemController

logger = logging.getLogger("PlookingII")

# 导入原始控制器 - 恢复原始实现
try:
    from .status_bar_controller import StatusBarController
except ImportError as e:
    logger.warning(f"Failed to import StatusBarController: {e}")
    from .unified_status_controller import UnifiedStatusController as StatusBarController

# TitlebarController已合并到UnifiedStatusController
from .unified_status_controller import UnifiedStatusController as TitlebarController

__all__ = [
    "ImageViewController",
    "UnifiedStatusController",
    "NavigationController",
    "DragDropController",
    "MenuController",
    "SystemController",
    "RotationController",
    # 向后兼容
    "StatusBarController",
    "TitlebarController",
]
