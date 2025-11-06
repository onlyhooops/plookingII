"""
测试遥测模块

测试覆盖：
- 遥测开关检测
- 默认目录逻辑
- 事件记录功能
- 环境变量控制
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

from plookingII.monitor.telemetry import (
    _default_dir,
    _enabled,
    is_telemetry_enabled,
    record_event,
)


class TestEnabled:
    """测试_enabled函数"""

    def test_enabled_with_1(self, monkeypatch):
        """测试环境变量为1时启用"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "1")
        assert _enabled() is True

    def test_enabled_with_true(self, monkeypatch):
        """测试环境变量为true时启用"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "true")
        assert _enabled() is True

    def test_enabled_with_TRUE(self, monkeypatch):
        """测试环境变量为TRUE时启用"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "TRUE")
        assert _enabled() is True

    def test_disabled_with_0(self, monkeypatch):
        """测试环境变量为0时禁用"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "0")
        assert _enabled() is False

    def test_disabled_with_false(self, monkeypatch):
        """测试环境变量为false时禁用"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "false")
        assert _enabled() is False

    def test_disabled_by_default(self, monkeypatch):
        """测试默认禁用"""
        monkeypatch.delenv("PLOOKINGII_TELEMETRY", raising=False)
        assert _enabled() is False

    def test_disabled_with_empty_string(self, monkeypatch):
        """测试空字符串时禁用"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "")
        assert _enabled() is False


class TestDefaultDir:
    """测试_default_dir函数"""

    def test_custom_dir_via_env(self, tmp_path, monkeypatch):
        """测试通过环境变量指定目录"""
        custom_dir = str(tmp_path / "custom_telemetry")
        monkeypatch.setenv("PLOOKINGII_TELEMETRY_DIR", custom_dir)

        result = _default_dir()
        assert result == custom_dir
        assert Path(custom_dir).exists()

    def test_custom_dir_already_exists(self, tmp_path, monkeypatch):
        """测试自定义目录已存在"""
        custom_dir = str(tmp_path / "existing_dir")
        os.makedirs(custom_dir)
        monkeypatch.setenv("PLOOKINGII_TELEMETRY_DIR", custom_dir)

        result = _default_dir()
        assert result == custom_dir

    def test_custom_dir_creation_failure(self, monkeypatch):
        """测试自定义目录创建失败时回退"""
        # 使用一个无效的路径
        monkeypatch.setenv("PLOOKINGII_TELEMETRY_DIR", "/nonexistent/invalid/path")

        # 应该回退到默认目录
        result = _default_dir()
        assert result is not None
        # 应该是Library/Logs/PlookingII或临时目录
        assert "PlookingII" in result or "PlookingII-logs" in result

    def test_default_macos_dir(self, monkeypatch, tmp_path):
        """测试macOS默认目录"""
        monkeypatch.delenv("PLOOKINGII_TELEMETRY_DIR", raising=False)

        # Mock expanduser to use temp directory
        def mock_expanduser(path):
            if path.startswith("~"):
                return str(tmp_path / path[2:])
            return path

        with patch("os.path.expanduser", side_effect=mock_expanduser):
            result = _default_dir()
            assert "Library/Logs/PlookingII" in result or "PlookingII-logs" in result

    def test_fallback_to_temp(self, monkeypatch):
        """测试回退到临时目录"""
        monkeypatch.delenv("PLOOKINGII_TELEMETRY_DIR", raising=False)

        # Mock expanduser to fail
        with patch("os.path.expanduser", side_effect=Exception("Test error")):
            result = _default_dir()
            assert "PlookingII-logs" in result


class TestIsTelemetryEnabled:
    """测试is_telemetry_enabled函数"""

    def test_returns_true_when_enabled(self, monkeypatch):
        """测试启用时返回True"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "1")
        assert is_telemetry_enabled() is True

    def test_returns_false_when_disabled(self, monkeypatch):
        """测试禁用时返回False"""
        monkeypatch.delenv("PLOOKINGII_TELEMETRY", raising=False)
        assert is_telemetry_enabled() is False


class TestRecordEvent:
    """测试record_event函数"""

    def test_record_when_disabled(self, monkeypatch):
        """测试禁用时不记录"""
        monkeypatch.delenv("PLOOKINGII_TELEMETRY", raising=False)

        result = record_event("test_event")
        assert result is False

    def test_record_simple_event(self, tmp_path, monkeypatch):
        """测试记录简单事件"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "1")
        monkeypatch.setenv("PLOOKINGII_TELEMETRY_DIR", str(tmp_path))

        result = record_event("app_start")
        assert result is True

        # 验证文件被创建
        telemetry_file = tmp_path / "telemetry.jsonl"
        assert telemetry_file.exists()

        # 验证内容
        with open(telemetry_file, encoding="utf-8") as f:
            line = f.readline()
            data = json.loads(line)
            assert data["event"] == "app_start"
            assert "ts" in data
            assert data["properties"] == {}

    def test_record_event_with_properties(self, tmp_path, monkeypatch):
        """测试记录带属性的事件"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "1")
        monkeypatch.setenv("PLOOKINGII_TELEMETRY_DIR", str(tmp_path))

        properties = {"version": "1.0.0", "platform": "macos"}
        result = record_event("app_start", properties)
        assert result is True

        telemetry_file = tmp_path / "telemetry.jsonl"
        with open(telemetry_file, encoding="utf-8") as f:
            line = f.readline()
            data = json.loads(line)
            assert data["event"] == "app_start"
            assert data["properties"]["version"] == "1.0.0"
            assert data["properties"]["platform"] == "macos"

    def test_record_multiple_events(self, tmp_path, monkeypatch):
        """测试记录多个事件"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "1")
        monkeypatch.setenv("PLOOKINGII_TELEMETRY_DIR", str(tmp_path))

        record_event("event1")
        record_event("event2")
        record_event("event3")

        telemetry_file = tmp_path / "telemetry.jsonl"
        with open(telemetry_file, encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 3

            events = [json.loads(line)["event"] for line in lines]
            assert events == ["event1", "event2", "event3"]

    def test_record_with_unicode(self, tmp_path, monkeypatch):
        """测试记录包含Unicode的事件"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "1")
        monkeypatch.setenv("PLOOKINGII_TELEMETRY_DIR", str(tmp_path))

        properties = {"message": "测试中文", "emoji": "🎉"}
        result = record_event("unicode_test", properties)
        assert result is True

        telemetry_file = tmp_path / "telemetry.jsonl"
        with open(telemetry_file, encoding="utf-8") as f:
            line = f.readline()
            data = json.loads(line)
            assert data["properties"]["message"] == "测试中文"
            assert data["properties"]["emoji"] == "🎉"

    def test_record_appends_to_existing_file(self, tmp_path, monkeypatch):
        """测试追加到已存在的文件"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "1")
        monkeypatch.setenv("PLOOKINGII_TELEMETRY_DIR", str(tmp_path))

        # 先创建一个事件
        record_event("first_event")

        # 再添加一个
        record_event("second_event")

        telemetry_file = tmp_path / "telemetry.jsonl"
        with open(telemetry_file, encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 2

    def test_record_handles_write_error(self, monkeypatch):
        """测试处理写入错误"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "1")
        monkeypatch.setenv("PLOOKINGII_TELEMETRY_DIR", "/invalid/readonly/path")

        # Mock open to raise exception
        with patch("builtins.open", side_effect=PermissionError("No write permission")):
            result = record_event("test_event")
            assert result is False

    def test_record_timestamp_is_unix_epoch(self, tmp_path, monkeypatch):
        """测试时间戳是Unix纪元"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "1")
        monkeypatch.setenv("PLOOKINGII_TELEMETRY_DIR", str(tmp_path))

        import time

        before = int(time.time())
        record_event("timestamp_test")
        after = int(time.time())

        telemetry_file = tmp_path / "telemetry.jsonl"
        with open(telemetry_file, encoding="utf-8") as f:
            data = json.loads(f.readline())
            assert before <= data["ts"] <= after

    def test_record_empty_properties(self, tmp_path, monkeypatch):
        """测试空属性字典"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "1")
        monkeypatch.setenv("PLOOKINGII_TELEMETRY_DIR", str(tmp_path))

        result = record_event("test", {})
        assert result is True

        telemetry_file = tmp_path / "telemetry.jsonl"
        with open(telemetry_file, encoding="utf-8") as f:
            data = json.loads(f.readline())
            assert data["properties"] == {}

    def test_record_complex_properties(self, tmp_path, monkeypatch):
        """测试复杂的属性结构"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "1")
        monkeypatch.setenv("PLOOKINGII_TELEMETRY_DIR", str(tmp_path))

        properties = {
            "nested": {"level1": {"level2": "value"}},
            "list": [1, 2, 3],
            "boolean": True,
            "null": None,
            "number": 42.5,
        }
        result = record_event("complex", properties)
        assert result is True

        telemetry_file = tmp_path / "telemetry.jsonl"
        with open(telemetry_file, encoding="utf-8") as f:
            data = json.loads(f.readline())
            assert data["properties"]["nested"]["level1"]["level2"] == "value"
            assert data["properties"]["list"] == [1, 2, 3]
            assert data["properties"]["boolean"] is True
            assert data["properties"]["null"] is None
            assert data["properties"]["number"] == 42.5


class TestIntegration:
    """集成测试"""

    def test_full_workflow(self, tmp_path, monkeypatch):
        """测试完整工作流"""
        # 1. 默认禁用
        monkeypatch.delenv("PLOOKINGII_TELEMETRY", raising=False)
        assert not is_telemetry_enabled()
        assert not record_event("disabled_event")

        # 2. 启用遥测
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "1")
        monkeypatch.setenv("PLOOKINGII_TELEMETRY_DIR", str(tmp_path))
        assert is_telemetry_enabled()

        # 3. 记录多个事件
        assert record_event("app_start", {"version": "1.0"})
        assert record_event("user_action", {"action": "click"})
        assert record_event("app_stop")

        # 4. 验证所有事件被记录
        telemetry_file = tmp_path / "telemetry.jsonl"
        assert telemetry_file.exists()

        with open(telemetry_file, encoding="utf-8") as f:
            events = [json.loads(line)["event"] for line in f]
            assert events == ["app_start", "user_action", "app_stop"]

    def test_switches_between_enabled_and_disabled(self, tmp_path, monkeypatch):
        """测试在启用和禁用之间切换"""
        monkeypatch.setenv("PLOOKINGII_TELEMETRY_DIR", str(tmp_path))

        # 启用并记录
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "1")
        assert record_event("enabled_event")

        # 禁用
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "0")
        assert not record_event("disabled_event")

        # 再次启用
        monkeypatch.setenv("PLOOKINGII_TELEMETRY", "true")
        assert record_event("enabled_again")

        # 验证只记录了启用时的事件
        telemetry_file = tmp_path / "telemetry.jsonl"
        with open(telemetry_file, encoding="utf-8") as f:
            events = [json.loads(line)["event"] for line in f]
            assert "disabled_event" not in events
            assert "enabled_event" in events
            assert "enabled_again" in events
