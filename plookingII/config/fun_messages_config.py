"""
趣味提示消息配置模块

v1.0.0: 趣味功能已移除，该模块保留基础结构以保持向后兼容性。

Author: PlookingII Team
Version: 1.0.0
"""

# 保留必需的配置变量以保持向后兼容性
TIME_MILESTONES = []
PROGRESS_MILESTONES = []
IMAGE_COUNT_MILESTONES = []
ENCOURAGEMENT_MESSAGES = []
REST_REMINDER_MESSAGES = []
PROGRESS_MESSAGES = []
TIME_BASED_MESSAGES = {
    "early": [],
    "warming": [],
    "stable": [],
    "intense": [],
    "extended": [],
    "marathon": []
}

# 休息提醒配置
REST_REMINDER_CONFIG = {
    "interval": 1800,  # 30分钟提醒一次休息（秒）
    "min_work_time": 1800,  # 最少工作30分钟才提醒休息
    "rest_duration": 300,  # 建议休息5分钟
    "eye_rest_interval": 1200,  # 20分钟提醒一次用眼休息
    "stretch_interval": 900,  # 15分钟提醒一次伸展运动
}

# 状态显示与刷新配置（兼容 SessionManager 读取）
MESSAGE_DISPLAY_CONFIG = {
    "update_interval": 1.0,  # 状态更新间隔（秒）
}
