#!/usr/bin/env python3
"""
测试 config/fun_messages_config.py

Author: PlookingII Team
"""

from plookingII.config.fun_messages_config import (
    ENCOURAGEMENT_MESSAGES,
    IMAGE_COUNT_MILESTONES,
    MESSAGE_DISPLAY_CONFIG,
    PROGRESS_MESSAGES,
    PROGRESS_MILESTONES,
    REST_REMINDER_CONFIG,
    REST_REMINDER_MESSAGES,
    TIME_BASED_MESSAGES,
    TIME_MILESTONES,
)


class TestFunMessagesConfigConstants:
    """测试趣味消息配置常量"""

    def test_milestones_are_lists(self):
        """测试里程碑配置为空列表（向后兼容）"""
        assert isinstance(TIME_MILESTONES, list)
        assert isinstance(PROGRESS_MILESTONES, list)
        assert isinstance(IMAGE_COUNT_MILESTONES, list)
        assert len(TIME_MILESTONES) == 0
        assert len(PROGRESS_MILESTONES) == 0
        assert len(IMAGE_COUNT_MILESTONES) == 0

    def test_messages_are_lists(self):
        """测试消息配置为空列表（向后兼容）"""
        assert isinstance(ENCOURAGEMENT_MESSAGES, list)
        assert isinstance(REST_REMINDER_MESSAGES, list)
        assert isinstance(PROGRESS_MESSAGES, list)
        assert len(ENCOURAGEMENT_MESSAGES) == 0
        assert len(REST_REMINDER_MESSAGES) == 0
        assert len(PROGRESS_MESSAGES) == 0

    def test_time_based_messages_structure(self):
        """测试时间消息结构"""
        assert isinstance(TIME_BASED_MESSAGES, dict)
        assert "early" in TIME_BASED_MESSAGES
        assert "warming" in TIME_BASED_MESSAGES
        assert "stable" in TIME_BASED_MESSAGES
        assert "intense" in TIME_BASED_MESSAGES
        assert "extended" in TIME_BASED_MESSAGES
        assert "marathon" in TIME_BASED_MESSAGES

    def test_time_based_messages_values_are_empty_lists(self):
        """测试时间消息值为空列表"""
        for key, value in TIME_BASED_MESSAGES.items():
            assert isinstance(value, list)
            assert len(value) == 0


class TestRestReminderConfig:
    """测试休息提醒配置"""

    def test_rest_reminder_config_structure(self):
        """测试休息提醒配置结构"""
        assert isinstance(REST_REMINDER_CONFIG, dict)
        assert "interval" in REST_REMINDER_CONFIG
        assert "min_work_time" in REST_REMINDER_CONFIG
        assert "rest_duration" in REST_REMINDER_CONFIG
        assert "eye_rest_interval" in REST_REMINDER_CONFIG
        assert "stretch_interval" in REST_REMINDER_CONFIG

    def test_rest_reminder_config_values(self):
        """测试休息提醒配置值"""
        assert REST_REMINDER_CONFIG["interval"] == 1800  # 30分钟
        assert REST_REMINDER_CONFIG["min_work_time"] == 1800  # 30分钟
        assert REST_REMINDER_CONFIG["rest_duration"] == 300  # 5分钟
        assert REST_REMINDER_CONFIG["eye_rest_interval"] == 1200  # 20分钟
        assert REST_REMINDER_CONFIG["stretch_interval"] == 900  # 15分钟

    def test_rest_reminder_config_value_types(self):
        """测试休息提醒配置值类型"""
        for key, value in REST_REMINDER_CONFIG.items():
            assert isinstance(value, int)
            assert value > 0

    def test_rest_reminder_intervals_logical(self):
        """测试休息提醒间隔逻辑合理"""
        # 最短间隔应该是伸展运动
        min_interval = min(
            REST_REMINDER_CONFIG["stretch_interval"],
            REST_REMINDER_CONFIG["eye_rest_interval"],
            REST_REMINDER_CONFIG["interval"],
        )
        assert min_interval == REST_REMINDER_CONFIG["stretch_interval"]

        # 休息时间应该少于工作时间
        assert REST_REMINDER_CONFIG["rest_duration"] < REST_REMINDER_CONFIG["min_work_time"]


class TestMessageDisplayConfig:
    """测试消息显示配置"""

    def test_message_display_config_structure(self):
        """测试消息显示配置结构"""
        assert isinstance(MESSAGE_DISPLAY_CONFIG, dict)
        assert "update_interval" in MESSAGE_DISPLAY_CONFIG

    def test_message_display_config_values(self):
        """测试消息显示配置值"""
        assert MESSAGE_DISPLAY_CONFIG["update_interval"] == 1.0

    def test_message_display_config_value_type(self):
        """测试消息显示配置值类型"""
        assert isinstance(MESSAGE_DISPLAY_CONFIG["update_interval"], float)
        assert MESSAGE_DISPLAY_CONFIG["update_interval"] > 0


class TestBackwardCompatibility:
    """测试向后兼容性"""

    def test_all_required_exports_exist(self):
        """测试所有必需的导出项存在"""
        # 确保所有旧的配置项仍然可导入
        from plookingII.config import fun_messages_config

        assert hasattr(fun_messages_config, "TIME_MILESTONES")
        assert hasattr(fun_messages_config, "PROGRESS_MILESTONES")
        assert hasattr(fun_messages_config, "IMAGE_COUNT_MILESTONES")
        assert hasattr(fun_messages_config, "ENCOURAGEMENT_MESSAGES")
        assert hasattr(fun_messages_config, "REST_REMINDER_MESSAGES")
        assert hasattr(fun_messages_config, "PROGRESS_MESSAGES")
        assert hasattr(fun_messages_config, "TIME_BASED_MESSAGES")
        assert hasattr(fun_messages_config, "REST_REMINDER_CONFIG")
        assert hasattr(fun_messages_config, "MESSAGE_DISPLAY_CONFIG")

    def test_empty_lists_are_safe_to_iterate(self):
        """测试空列表可以安全迭代"""
        # 确保旧代码可以安全地迭代这些空列表
        for _ in TIME_MILESTONES:
            pass
        for _ in PROGRESS_MILESTONES:
            pass
        for _ in IMAGE_COUNT_MILESTONES:
            pass
        for _ in ENCOURAGEMENT_MESSAGES:
            pass
        for _ in REST_REMINDER_MESSAGES:
            pass
        for _ in PROGRESS_MESSAGES:
            pass

    def test_time_based_messages_safe_to_access(self):
        """测试时间消息可以安全访问"""
        for category in ["early", "warming", "stable", "intense", "extended", "marathon"]:
            messages = TIME_BASED_MESSAGES.get(category, [])
            assert isinstance(messages, list)
            # 可以安全迭代
            for _ in messages:
                pass
