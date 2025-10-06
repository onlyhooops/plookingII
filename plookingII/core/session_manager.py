"""
会话管理器模块

提供PlookingII应用程序的会话状态跟踪、进度管理和趣味提示功能。
跟踪用户的工作时长、浏览进度，并提供有趣的里程碑提示和休息建议。

主要功能：
    - 会话时长跟踪
    - 进度里程碑管理
    - 趣味提示文本生成
    - 智能休息提醒
    - 工作统计信息

核心组件：
    - SessionManager: 主要的会话管理器
    - MilestoneTracker: 里程碑跟踪器
    - FunMessageGenerator: 趣味消息生成器

技术特点：
    - 实时状态跟踪：使用定时器持续更新状态
    - 智能提示：根据工作模式生成个性化提示
    - 里程碑系统：在关键节点提供鼓励
    - 休息提醒：基于工作时长提供健康建议

使用方式：
    from plookingII.core.session_manager import SessionManager

Author: PlookingII Team
"""

import time

from ..config.constants import APP_NAME
from ..config.fun_messages_config import (
    IMAGE_COUNT_MILESTONES,
    MESSAGE_DISPLAY_CONFIG,
    PROGRESS_MILESTONES,
    REST_REMINDER_CONFIG,
    TIME_MILESTONES,
)
from ..imports import _NSTimer as NSTimer
from ..imports import logging

logger = logging.getLogger(APP_NAME)


class MilestoneTracker:
    """里程碑跟踪器，管理各种工作进度里程碑"""

    def __init__(self):
        self.milestones = {
            # 时间里程碑（分钟）
            "time": TIME_MILESTONES,
            # 进度里程碑（百分比）
            "progress": PROGRESS_MILESTONES,
            # 图片数量里程碑
            "images": IMAGE_COUNT_MILESTONES,
        }
        self.achieved_milestones = set()

    def check_milestone(self, milestone_type, value):
        """检查是否达到新的里程碑

        Args:
            milestone_type (str): 里程碑类型 ('time', 'progress', 'images')
            value (int/float): 当前值

        Returns:
            tuple or None: (里程碑值, 提示消息) 或 None
        """
        if milestone_type not in self.milestones:
            return None

        for milestone_value, message in self.milestones[milestone_type]:
            milestone_key = f"{milestone_type}_{milestone_value}"
            if milestone_key not in self.achieved_milestones and value >= milestone_value:
                self.achieved_milestones.add(milestone_key)
                return (milestone_value, message)
        return None


# FunMessageGenerator类已移除 - 趣味功能已禁用


class SessionManager:
    """会话管理器，跟踪用户工作状态和提供趣味提示"""

    def __init__(self):
        self.session_start_time = None
        self.last_activity_time = None
        self.total_work_time = 0  # 累计工作时长（秒）
        self.current_session_time = 0  # 当前会话时长（秒）
        self.images_viewed = 0  # 已浏览图片数量
        self.total_images = 0  # 总图片数量
        self.folders_processed = 0  # 已处理文件夹数量
        self.total_folders = 0  # 总文件夹数量

        # 子组件
        self.milestone_tracker = MilestoneTracker()
        # fun_generator已移除 - 趣味功能已禁用

        # 状态更新定时器
        self._update_timer = None
        self._last_milestone_check = 0

        # 休息提醒状态
        self.last_rest_reminder = 0
        self.rest_reminder_interval = REST_REMINDER_CONFIG["interval"]

    def start_session(self):
        """开始新的工作会话"""
        current_time = time.time()
        self.session_start_time = current_time
        self.last_activity_time = current_time
        self.current_session_time = 0
        self.images_viewed = 0
        self.folders_processed = 0

        logger.info("开始新的工作会话")

    def end_session(self):
        """结束当前工作会话"""
        if self.session_start_time:
            session_duration = time.time() - self.session_start_time
            self.total_work_time += session_duration
            logger.info(f"结束工作会话，本次时长: {session_duration / 60:.1f}分钟")

        self.session_start_time = None
        self.current_session_time = 0

        # 停止定时器
        if self._update_timer:
            self._update_timer.invalidate()
            self._update_timer = None

    def update_activity(self):
        """更新用户活动时间"""
        self.last_activity_time = time.time()

    def set_image_count(self, total_images):
        """设置总图片数量

        Args:
            total_images (int): 总图片数量
        """
        self.total_images = total_images

    def set_folder_count(self, total_folders):
        """设置总文件夹数量

        Args:
            total_folders (int): 总文件夹数量
        """
        self.total_folders = total_folders

    def image_viewed(self):
        """标记图片已浏览"""
        self.images_viewed += 1
        self.update_activity()

    def folder_processed(self):
        """标记文件夹已处理"""
        self.folders_processed += 1
        self.update_activity()

    def get_session_stats(self):
        """获取会话统计信息

        Returns:
            dict: 包含各种统计信息的字典
        """
        current_time = time.time()

        if self.session_start_time:
            self.current_session_time = current_time - self.session_start_time

        session_minutes = self.current_session_time / 60
        total_minutes = self.total_work_time / 60

        # 计算进度百分比
        image_progress = (self.images_viewed / self.total_images * 100) if self.total_images > 0 else 0
        folder_progress = (self.folders_processed / self.total_folders * 100) if self.total_folders > 0 else 0

        return {
            "session_minutes": session_minutes,
            "total_minutes": total_minutes,
            "images_viewed": self.images_viewed,
            "total_images": self.total_images,
            "image_progress": image_progress,
            "folders_processed": self.folders_processed,
            "total_folders": self.total_folders,
            "folder_progress": folder_progress,
            "current_time": current_time,
        }

    def check_milestones(self):
        """检查是否达到新的里程碑 - 趣味功能已移除

        Returns:
            list: 空列表（趣味里程碑已禁用）
        """
        # 趣味里程碑功能已移除，返回空列表
        return []

    def get_status_message(self):
        """获取当前状态消息 - 移除emoji，保留基础信息

        Returns:
            str: 状态消息文本
        """
        stats = self.get_session_stats()

        # 基础状态信息（移除emoji）
        if stats["total_images"] > 0:
            progress_text = f"进度: {stats['image_progress']:.1f}% ({stats['images_viewed']}/{stats['total_images']})"
        else:
            progress_text = "准备中..."

        # 时间信息（移除emoji）
        if stats["session_minutes"] > 0:
            time_text = f"时长: {stats['session_minutes']:.0f}分钟"
        else:
            time_text = "刚开始"

        # 组合状态消息
        status_parts = [progress_text, time_text]

        # 添加文件夹进度（移除emoji）
        if stats["total_folders"] > 0:
            folder_text = (
                f"文件夹: {stats['folder_progress']:.1f}% ({stats['folders_processed']}/{stats['total_folders']})"
            )
            status_parts.append(folder_text)

        return " | ".join(status_parts)

    def get_fun_message(self):
        """获取基础状态消息 - 趣味功能已移除

        Returns:
            str: 基础状态消息
        """
        stats = self.get_session_stats()

        # 返回基础状态信息，不包含趣味内容
        if stats["total_images"] > 0:
            return f"进度: {stats['image_progress']:.1f}% | 时长: {stats['session_minutes']:.0f}分钟"
        return f"工作时长: {stats['session_minutes']:.0f}分钟"

    def start_update_timer(self, callback, interval=None):
        """启动状态更新定时器

        Args:
            callback: 定时器回调函数
            interval (float): 更新间隔（秒），默认使用配置值
        """
        if self._update_timer:
            self._update_timer.invalidate()

        if interval is None:
            interval = MESSAGE_DISPLAY_CONFIG["update_interval"]

        self._update_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            interval, callback, "updateSessionStatus:", None, True
        )

    def stop_update_timer(self):
        """停止状态更新定时器"""
        if self._update_timer:
            self._update_timer.invalidate()
            self._update_timer = None

    def get_work_summary(self):
        """获取工作摘要信息 - 移除趣味内容，保留基础统计

        Returns:
            dict: 工作摘要数据
        """
        stats = self.get_session_stats()

        return {
            "session_duration": f"{stats['session_minutes']:.1f}分钟",
            "total_work_time": f"{stats['total_minutes']:.1f}分钟",
            "images_processed": f"{stats['images_viewed']}/{stats['total_images']}",
            "folders_processed": f"{stats['folders_processed']}/{stats['total_folders']}",
            "progress": f"{stats['image_progress']:.1f}%",
            "efficiency": f"{stats['images_viewed'] / max(stats['session_minutes'], 1):.1f}张/分钟"
            if stats["session_minutes"] > 0
            else "0张/分钟",
        }

    def get_session_summary(self):
        """获取会话摘要信息 - 为兼容性添加的方法

        Returns:
            dict: 会话摘要数据，包含显示消息
        """
        stats = self.get_session_stats()

        # 生成显示消息
        if stats["total_images"] > 0:
            display_message = f"进度: {stats['image_progress']:.1f}% | 时长: {stats['session_minutes']:.0f}分钟"
        else:
            display_message = f"工作时长: {stats['session_minutes']:.0f}分钟"

        return {"display_message": display_message, "session_stats": stats, "work_summary": self.get_work_summary()}
