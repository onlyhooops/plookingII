"""
单元测试：轻量性能监测跟踪器 perf_tracker

覆盖：
- 关闭时的零开销行为
- 聚合统计、分位数、元数据分布
- 采样、慢事件捕获
- 上下文管理器 / 装饰器
- 会话报告落盘（JSON + Markdown）与轮转
"""

import json
import os

from plookingII.monitor.perf_tracker import PerfTracker, perf_timed


class TestPerfTrackerBasic:
    def test_disabled_tracker_is_noop(self):
        """关闭时 record 不产生任何统计"""
        tracker = PerfTracker(enabled=False)
        tracker.record("image_display", 123.4, method="cache_hit")
        assert tracker.get_summary()["operations"] == {}
        assert tracker.flush_report(reason="test") is None

    def test_tracker_tolerates_mock_constructor_values(self):
        """畸形构造参数（如测试中的 Mock）不导致跟踪器崩溃"""
        from unittest.mock import MagicMock

        tracker = PerfTracker(
            enabled=MagicMock(),
            sample_rate=MagicMock(),
            report_dir=MagicMock(),
            max_report_files=MagicMock(),
            auto_flush_seconds=0,
        )
        assert tracker.enabled is True
        assert tracker._sample_rate == 1
        assert tracker._max_report_files == 20
        assert tracker._auto_flush_seconds == 0
        tracker.record("x", 1.0)
        assert tracker.get_summary()["operations"]["x"]["count"] == 1

    def test_tracker_tolerates_polluted_get_config(self):
        """全局 get_config 被 mock 污染时，跟踪器仍可安全创建"""
        from unittest.mock import MagicMock, patch

        with patch("plookingII.monitor.perf_tracker.get_config", return_value=MagicMock()):
            tracker = PerfTracker(auto_flush_seconds=0)
        assert tracker.enabled is True
        assert tracker._sample_rate == 1
        assert tracker._report_dir.endswith("perf")
        tracker.record("y", 1.0)
        assert tracker.get_summary()["operations"]["y"]["count"] == 1

    def test_record_aggregates_stats(self):
        """聚合 count / avg / min / max 与元数据分布"""
        tracker = PerfTracker(enabled=True, auto_flush_seconds=0)
        tracker.record("image_display", 10.0, method="cache_hit")
        tracker.record("image_display", 30.0, method="cache_hit")
        tracker.record("image_display", 50.0, method="next_ready")

        ops = tracker.get_summary()["operations"]
        stat = ops["image_display"]
        assert stat["count"] == 3
        assert stat["avg_ms"] == 30.0
        assert stat["min_ms"] == 10.0
        assert stat["max_ms"] == 50.0
        assert stat["meta_counts"]["method"]["cache_hit"] == 2
        assert stat["meta_counts"]["method"]["next_ready"] == 1

    def test_percentiles(self):
        """p50 / p95 / p99 分位数估算"""
        tracker = PerfTracker(enabled=True, auto_flush_seconds=0)
        for i in range(1, 101):
            tracker.record("op", float(i))
        stat = tracker.get_summary()["operations"]["op"]
        assert stat["p50_ms"] == 50.5
        assert 94.0 < stat["p95_ms"] < 96.5
        assert 98.9 < stat["p99_ms"] < 99.2

    def test_negative_duration_clamped(self):
        """负耗时被钳制为 0"""
        tracker = PerfTracker(enabled=True, auto_flush_seconds=0)
        tracker.record("nav", -5.0)
        assert tracker.get_summary()["operations"]["nav"]["min_ms"] == 0.0

    def test_sampling_rate(self):
        """采样率生效：每 N 次记录 1 次"""
        tracker = PerfTracker(enabled=True, sample_rate=10, auto_flush_seconds=0)
        for _ in range(100):
            tracker.record("nav", 1.0)
        assert tracker.get_summary()["operations"]["nav"]["count"] == 10

    def test_slow_event_capture(self):
        """超过阈值的操作进入慢事件列表"""
        tracker = PerfTracker(enabled=True, auto_flush_seconds=0)
        tracker.record("folder_scan", 1500.0, folders=3)
        tracker.record("image_display", 5.0)
        slow = tracker.get_summary()["slow_events"]
        assert len(slow) == 1
        assert slow[0]["op"] == "folder_scan"
        assert slow[0]["meta"]["folders"] == "3"


class TestPerfTrackerTiming:
    def test_timeit_context_manager(self):
        """timeit 上下文管理器记录耗时"""
        import time

        tracker = PerfTracker(enabled=True, auto_flush_seconds=0)
        with tracker.timeit("ctx_op"):
            time.sleep(0.005)
        stat = tracker.get_summary()["operations"]["ctx_op"]
        assert stat["count"] == 1
        assert stat["avg_ms"] >= 4.0

    def test_timed_decorator_records_success(self):
        """实例级 timed 装饰器记录成功调用"""
        tracker = PerfTracker(enabled=True, auto_flush_seconds=0)

        @tracker.timed("bound_op")
        def fn():
            return 42

        assert fn() == 42
        stat = tracker.get_summary()["operations"]["bound_op"]
        assert stat["count"] == 1
        assert stat["success_rate"] == 1.0

    def test_timed_decorator_records_failure(self):
        """异常调用被标记为失败且异常继续抛出"""
        tracker = PerfTracker(enabled=True, auto_flush_seconds=0)

        @tracker.timed("fail_op")
        def fn():
            raise ValueError("boom")

        try:
            fn()
        except ValueError:
            pass
        stat = tracker.get_summary()["operations"]["fail_op"]
        assert stat["count"] == 1
        assert stat["success_rate"] == 0.0

    def test_module_level_decorator_uses_singleton(self):
        """模块级 perf_timed 装饰器写入全局跟踪器"""
        from plookingII.monitor import shutdown_perf_tracker

        @perf_timed("module_op")
        def fn():
            return 1

        try:
            from plookingII.monitor.perf_tracker import get_perf_tracker

            fn()
            assert get_perf_tracker().get_summary()["operations"]["module_op"]["count"] == 1
        finally:
            shutdown_perf_tracker()


class TestPerfTrackerReport:
    def test_flush_report_writes_json_and_markdown(self, tmp_path):
        """落盘生成 JSON + Markdown，JSON 可解析"""
        tracker = PerfTracker(enabled=True, report_dir=str(tmp_path), auto_flush_seconds=0)
        tracker.record("image_display", 12.0, method="cache_hit")
        path = tracker.flush_report(reason="test")

        assert path is not None
        assert os.path.exists(path)
        md_path = os.path.splitext(path)[0] + ".md"
        assert os.path.exists(md_path)

        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["operations"]["image_display"]["count"] == 1
        with open(md_path, encoding="utf-8") as f:
            assert "## 操作统计" in f.read()

    def test_report_rotation_keeps_max_files(self, tmp_path):
        """轮转仅保留最近 max_report_files 份报告"""
        tracker = PerfTracker(enabled=True, report_dir=str(tmp_path), max_report_files=2, auto_flush_seconds=0)
        for i in range(5):
            tracker.record("x", 1.0)
            tracker.flush_report(reason=f"r{i}")

        jsons = [f for f in os.listdir(str(tmp_path)) if f.endswith(".json")]
        mds = [f for f in os.listdir(str(tmp_path)) if f.endswith(".md")]
        assert len(jsons) == 2
        assert len(mds) == 2

    def test_report_includes_session_info(self, tmp_path):
        """报告包含会话元信息"""
        tracker = PerfTracker(enabled=True, report_dir=str(tmp_path), auto_flush_seconds=0)
        tracker.record("nav", 1.0)
        summary = tracker.get_summary()
        assert summary["app"] == "PlookingII"
        assert summary["version"]
        assert summary["session_duration_s"] >= 0
