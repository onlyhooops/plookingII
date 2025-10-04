"""
测试 core/lightweight_monitor.py

测试轻量级监控系统功能，包括：
- LightweightMonitor类初始化和基本功能
- 缓存命中率记录和计算
- 加载时间记录和统计
- 内存使用量记录
- 请求计数
- 指标获取和历史记录
- 性能摘要和报告
- 性能评估和建议
- PerformanceTracker上下文管理器
- 全局实例和装饰器
"""

from unittest.mock import MagicMock, Mock, patch
import time
import threading

import pytest

from plookingII.core.lightweight_monitor import (
    LightweightMonitor,
    PerformanceTracker,
    get_monitor,
    track_performance,
)


# ==================== LightweightMonitor 初始化测试 ====================


class TestLightweightMonitorInit:
    """测试LightweightMonitor初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        monitor = LightweightMonitor()
        
        assert monitor.max_history == 100
        assert monitor.metrics["cache_hit_rate"] == 0.0
        assert monitor.metrics["total_requests"] == 0
        assert len(monitor.history["load_times"]) == 0

    def test_init_custom_max_history(self):
        """测试自定义max_history"""
        monitor = LightweightMonitor(max_history=50)
        
        assert monitor.max_history == 50
        assert monitor.history["load_times"].maxlen == 50

    def test_init_creates_lock(self):
        """测试初始化创建锁"""
        monitor = LightweightMonitor()
        
        assert hasattr(monitor, 'lock')
        # 验证lock有acquire和release方法
        assert hasattr(monitor.lock, 'acquire')
        assert hasattr(monitor.lock, 'release')

    def test_init_metrics_structure(self):
        """测试metrics结构"""
        monitor = LightweightMonitor()
        
        assert "cache_hit_rate" in monitor.metrics
        assert "avg_load_time" in monitor.metrics
        assert "memory_usage_mb" in monitor.metrics
        assert "total_requests" in monitor.metrics
        assert "error_count" in monitor.metrics
        assert "last_update_time" in monitor.metrics


# ==================== 缓存命中率测试 ====================


class TestCacheHitRate:
    """测试缓存命中率记录"""

    def test_record_cache_hit(self):
        """测试记录缓存命中"""
        monitor = LightweightMonitor()
        
        monitor.record_cache_hit()
        
        assert monitor.counters["cache_hits"] == 1
        assert monitor.metrics["cache_hit_rate"] == 1.0

    def test_record_cache_miss(self):
        """测试记录缓存未命中"""
        monitor = LightweightMonitor()
        
        monitor.record_cache_miss()
        
        assert monitor.counters["cache_misses"] == 1
        assert monitor.metrics["cache_hit_rate"] == 0.0

    def test_cache_hit_rate_calculation(self):
        """测试缓存命中率计算"""
        monitor = LightweightMonitor()
        
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_miss()
        
        # 3/4 = 0.75
        assert monitor.metrics["cache_hit_rate"] == 0.75

    def test_cache_hit_rate_history(self):
        """测试缓存命中率历史记录"""
        monitor = LightweightMonitor()
        
        monitor.record_cache_hit()
        monitor.record_cache_miss()
        monitor.record_cache_hit()
        
        # 应该有3个记录点
        assert len(monitor.history["cache_hit_rates"]) == 3

    def test_multiple_cache_operations(self):
        """测试多次缓存操作"""
        monitor = LightweightMonitor()
        
        for _ in range(70):
            monitor.record_cache_hit()
        for _ in range(30):
            monitor.record_cache_miss()
        
        # 70/100 = 0.7
        assert monitor.metrics["cache_hit_rate"] == 0.7
        assert monitor.counters["cache_hits"] == 70
        assert monitor.counters["cache_misses"] == 30


# ==================== 加载时间测试 ====================


class TestLoadTime:
    """测试加载时间记录"""

    def test_record_load_time_success(self):
        """测试记录成功的加载时间"""
        monitor = LightweightMonitor()
        
        monitor.record_load_time(1.5, success=True)
        
        assert len(monitor.history["load_times"]) == 1
        assert monitor.metrics["avg_load_time"] == 1.5
        assert monitor.counters["successful_loads"] == 1
        assert monitor.counters["failed_loads"] == 0

    def test_record_load_time_failure(self):
        """测试记录失败的加载时间"""
        monitor = LightweightMonitor()
        
        monitor.record_load_time(2.0, success=False)
        
        assert len(monitor.history["load_times"]) == 1
        assert monitor.counters["successful_loads"] == 0
        assert monitor.counters["failed_loads"] == 1
        assert monitor.metrics["error_count"] == 1

    def test_avg_load_time_calculation(self):
        """测试平均加载时间计算"""
        monitor = LightweightMonitor()
        
        monitor.record_load_time(1.0)
        monitor.record_load_time(2.0)
        monitor.record_load_time(3.0)
        
        # (1 + 2 + 3) / 3 = 2.0
        assert monitor.metrics["avg_load_time"] == 2.0

    def test_load_time_max_history(self):
        """测试加载时间历史记录上限"""
        monitor = LightweightMonitor(max_history=5)
        
        for i in range(10):
            monitor.record_load_time(float(i))
        
        # 只保留最后5个
        assert len(monitor.history["load_times"]) == 5
        # 平均值应该是最后5个的平均 (5+6+7+8+9)/5 = 7.0
        assert monitor.metrics["avg_load_time"] == 7.0


# ==================== 内存使用量测试 ====================


class TestMemoryUsage:
    """测试内存使用量记录"""

    def test_record_memory_usage(self):
        """测试记录内存使用量"""
        monitor = LightweightMonitor()
        
        monitor.record_memory_usage(150.5)
        
        assert monitor.metrics["memory_usage_mb"] == 150.5
        assert len(monitor.history["memory_usage"]) == 1

    def test_multiple_memory_records(self):
        """测试多次内存记录"""
        monitor = LightweightMonitor()
        
        monitor.record_memory_usage(100.0)
        monitor.record_memory_usage(200.0)
        monitor.record_memory_usage(150.0)
        
        # 最后一次记录的值
        assert monitor.metrics["memory_usage_mb"] == 150.0
        assert len(monitor.history["memory_usage"]) == 3


# ==================== 请求计数测试 ====================


class TestRequestCount:
    """测试请求计数"""

    def test_record_request(self):
        """测试记录请求"""
        monitor = LightweightMonitor()
        
        monitor.record_request()
        
        assert monitor.metrics["total_requests"] == 1

    def test_multiple_requests(self):
        """测试多次请求"""
        monitor = LightweightMonitor()
        
        for _ in range(100):
            monitor.record_request()
        
        assert monitor.metrics["total_requests"] == 100


# ==================== 指标获取测试 ====================


class TestGetMetrics:
    """测试获取指标"""

    def test_get_metrics(self):
        """测试获取指标"""
        monitor = LightweightMonitor()
        
        monitor.record_cache_hit()
        monitor.record_load_time(1.5)
        
        metrics = monitor.get_metrics()
        
        assert isinstance(metrics, dict)
        assert "cache_hit_rate" in metrics
        assert "avg_load_time" in metrics
        assert "last_update_time" in metrics

    def test_get_metrics_updates_time(self):
        """测试获取指标更新时间"""
        monitor = LightweightMonitor()
        
        before_time = time.time()
        metrics = monitor.get_metrics()
        after_time = time.time()
        
        assert before_time <= metrics["last_update_time"] <= after_time

    def test_get_metrics_returns_copy(self):
        """测试获取指标返回副本"""
        monitor = LightweightMonitor()
        
        metrics1 = monitor.get_metrics()
        metrics1["cache_hit_rate"] = 999.0
        
        metrics2 = monitor.get_metrics()
        assert metrics2["cache_hit_rate"] != 999.0


# ==================== 历史记录测试 ====================


class TestGetHistory:
    """测试获取历史记录"""

    def test_get_history(self):
        """测试获取历史记录"""
        monitor = LightweightMonitor()
        
        monitor.record_load_time(1.0)
        monitor.record_memory_usage(100.0)
        monitor.record_cache_hit()
        
        history = monitor.get_history()
        
        assert isinstance(history, dict)
        assert "load_times" in history
        assert "memory_usage" in history
        assert "cache_hit_rates" in history
        assert len(history["load_times"]) == 1
        assert len(history["memory_usage"]) == 1

    def test_get_history_returns_list(self):
        """测试历史记录返回列表"""
        monitor = LightweightMonitor()
        
        monitor.record_load_time(1.0)
        
        history = monitor.get_history()
        
        assert isinstance(history["load_times"], list)


# ==================== 性能摘要测试 ====================


class TestGetSummary:
    """测试获取性能摘要"""

    def test_get_summary_basic(self):
        """测试基本性能摘要"""
        monitor = LightweightMonitor()
        
        summary = monitor.get_summary()
        
        assert isinstance(summary, dict)
        assert "cache_hit_rate" in summary
        assert "avg_load_time" in summary
        assert "success_rate" in summary
        assert "total_loads" in summary

    def test_get_summary_success_rate(self):
        """测试成功率计算"""
        monitor = LightweightMonitor()
        
        monitor.record_load_time(1.0, success=True)
        monitor.record_load_time(1.5, success=True)
        monitor.record_load_time(2.0, success=False)
        
        summary = monitor.get_summary()
        
        # 2/3 ≈ 0.6667
        assert summary["success_rate"] == pytest.approx(0.6667, rel=0.01)
        assert summary["total_loads"] == 3

    def test_get_summary_zero_loads(self):
        """测试没有加载时的摘要"""
        monitor = LightweightMonitor()
        
        summary = monitor.get_summary()
        
        assert summary["success_rate"] == 0.0
        assert summary["total_loads"] == 0


# ==================== 重置测试 ====================


class TestReset:
    """测试重置功能"""

    def test_reset_metrics(self):
        """测试重置指标"""
        monitor = LightweightMonitor()
        
        monitor.record_cache_hit()
        monitor.record_load_time(1.5)
        monitor.record_memory_usage(100.0)
        
        monitor.reset()
        
        assert monitor.metrics["cache_hit_rate"] == 0.0
        assert monitor.metrics["avg_load_time"] == 0.0
        assert monitor.metrics["total_requests"] == 0

    def test_reset_history(self):
        """测试重置历史记录"""
        monitor = LightweightMonitor()
        
        monitor.record_load_time(1.0)
        monitor.record_memory_usage(100.0)
        
        monitor.reset()
        
        assert len(monitor.history["load_times"]) == 0
        assert len(monitor.history["memory_usage"]) == 0

    def test_reset_counters(self):
        """测试重置计数器"""
        monitor = LightweightMonitor()
        
        monitor.record_cache_hit()
        monitor.record_cache_miss()
        
        monitor.reset()
        
        assert monitor.counters["cache_hits"] == 0
        assert monitor.counters["cache_misses"] == 0


# ==================== 性能报告测试 ====================


class TestPerformanceReport:
    """测试性能报告"""

    def test_get_performance_report(self):
        """测试获取性能报告"""
        monitor = LightweightMonitor()
        
        monitor.record_cache_hit()
        monitor.record_load_time(1.5)
        
        report = monitor.get_performance_report()
        
        assert isinstance(report, str)
        assert "PlookingII Performance Report" in report
        assert "Cache Hit Rate" in report
        assert "Average Load Time" in report

    def test_performance_report_formatting(self):
        """测试性能报告格式"""
        monitor = LightweightMonitor()
        
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_miss()
        
        report = monitor.get_performance_report()
        
        # 应该包含百分比格式
        assert "%" in report


# ==================== 性能评估测试 ====================


class TestPerformanceEvaluation:
    """测试性能评估"""

    def test_is_performance_good_true(self):
        """测试性能良好"""
        monitor = LightweightMonitor()
        
        # 设置良好的性能指标
        for _ in range(8):
            monitor.record_cache_hit()
        for _ in range(2):
            monitor.record_cache_miss()
        
        monitor.record_load_time(0.5, success=True)
        monitor.record_load_time(1.0, success=True)
        
        assert monitor.is_performance_good() is True

    def test_is_performance_good_false(self):
        """测试性能不良"""
        monitor = LightweightMonitor()
        
        # 设置不良的性能指标
        monitor.record_cache_miss()
        monitor.record_load_time(5.0, success=False)
        
        assert monitor.is_performance_good() is False

    def test_get_recommendations_low_cache(self):
        """测试低缓存命中率建议"""
        monitor = LightweightMonitor()
        
        for _ in range(5):
            monitor.record_cache_miss()
        
        recommendations = monitor.get_recommendations()
        
        assert len(recommendations) > 0
        assert any("缓存" in r for r in recommendations)

    def test_get_recommendations_slow_load(self):
        """测试慢加载建议"""
        monitor = LightweightMonitor()
        
        monitor.record_load_time(5.0)
        
        recommendations = monitor.get_recommendations()
        
        assert any("加载时间" in r for r in recommendations)

    def test_get_recommendations_high_memory(self):
        """测试高内存使用建议"""
        monitor = LightweightMonitor()
        
        monitor.record_memory_usage(1500.0)
        
        recommendations = monitor.get_recommendations()
        
        assert any("内存" in r for r in recommendations)

    def test_get_recommendations_empty(self):
        """测试无建议情况"""
        monitor = LightweightMonitor()
        
        # 设置良好的指标
        for _ in range(10):
            monitor.record_cache_hit()
        monitor.record_load_time(0.5, success=True)
        monitor.record_memory_usage(100.0)
        
        recommendations = monitor.get_recommendations()
        
        assert len(recommendations) == 0


# ==================== PerformanceTracker 测试 ====================


class TestPerformanceTracker:
    """测试PerformanceTracker"""

    def test_tracker_init(self):
        """测试跟踪器初始化"""
        monitor = LightweightMonitor()
        tracker = PerformanceTracker(monitor)
        
        assert tracker.monitor is monitor
        assert tracker.start_time is None

    def test_tracker_context_manager_success(self):
        """测试上下文管理器成功场景"""
        monitor = LightweightMonitor()
        
        with PerformanceTracker(monitor):
            time.sleep(0.1)
        
        # 应该记录了加载时间
        assert len(monitor.history["load_times"]) == 1
        assert monitor.counters["successful_loads"] == 1

    def test_tracker_context_manager_failure(self):
        """测试上下文管理器失败场景"""
        monitor = LightweightMonitor()
        
        try:
            with PerformanceTracker(monitor):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # 应该记录了失败
        assert monitor.counters["failed_loads"] == 1
        assert monitor.metrics["error_count"] == 1

    def test_set_operation_name(self):
        """测试设置操作名称"""
        monitor = LightweightMonitor()
        tracker = PerformanceTracker(monitor)
        
        tracker.set_operation_name("test_operation")
        
        assert tracker.operation_name == "test_operation"


# ==================== 全局实例和装饰器测试 ====================


class TestGlobalAndDecorator:
    """测试全局实例和装饰器"""

    def test_get_monitor(self):
        """测试获取全局监控实例"""
        monitor = get_monitor()
        
        assert isinstance(monitor, LightweightMonitor)

    def test_get_monitor_returns_same_instance(self):
        """测试多次调用返回同一实例"""
        monitor1 = get_monitor()
        monitor2 = get_monitor()
        
        assert monitor1 is monitor2

    def test_track_performance_decorator(self):
        """测试性能跟踪装饰器"""
        monitor = get_monitor()
        initial_count = len(monitor.history["load_times"])
        
        @track_performance("test_operation")
        def test_func():
            time.sleep(0.05)
            return "success"
        
        result = test_func()
        
        assert result == "success"
        assert len(monitor.history["load_times"]) > initial_count

    def test_track_performance_decorator_no_name(self):
        """测试无操作名称的装饰器"""
        @track_performance()
        def test_func():
            return "test"
        
        # 不应该抛出异常
        result = test_func()
        assert result == "test"


# ==================== 线程安全测试 ====================


class TestThreadSafety:
    """测试线程安全"""

    def test_concurrent_cache_hits(self):
        """测试并发缓存命中记录"""
        monitor = LightweightMonitor()
        
        def record_hits():
            for _ in range(100):
                monitor.record_cache_hit()
        
        threads = [threading.Thread(target=record_hits) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 应该准确记录500次
        assert monitor.counters["cache_hits"] == 500

    def test_concurrent_load_times(self):
        """测试并发加载时间记录"""
        monitor = LightweightMonitor()
        
        def record_loads():
            for i in range(10):
                monitor.record_load_time(float(i) * 0.1)
        
        threads = [threading.Thread(target=record_loads) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 应该记录30次
        assert len(monitor.history["load_times"]) == 30


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    def test_complete_monitoring_workflow(self):
        """测试完整监控工作流"""
        monitor = LightweightMonitor(max_history=50)
        
        # 模拟实际使用场景
        for i in range(20):
            if i % 3 == 0:
                monitor.record_cache_miss()
            else:
                monitor.record_cache_hit()
            
            monitor.record_load_time(0.5 + i * 0.1, success=(i % 5 != 0))
            monitor.record_memory_usage(100.0 + i * 10)
            monitor.record_request()
        
        # 获取各种报告
        metrics = monitor.get_metrics()
        summary = monitor.get_summary()
        history = monitor.get_history()
        report = monitor.get_performance_report()
        is_good = monitor.is_performance_good()
        recommendations = monitor.get_recommendations()
        
        # 验证所有数据都正确
        assert metrics["total_requests"] == 20
        assert len(history["load_times"]) == 20
        assert isinstance(report, str)
        assert isinstance(is_good, bool)
        assert isinstance(recommendations, list)

    def test_monitor_reset_and_reuse(self):
        """测试监控重置和重用"""
        monitor = LightweightMonitor()
        
        # 第一轮数据
        monitor.record_cache_hit()
        monitor.record_load_time(1.0)
        
        first_summary = monitor.get_summary()
        
        # 重置
        monitor.reset()
        
        # 第二轮数据
        monitor.record_cache_miss()
        monitor.record_load_time(2.0)
        
        second_summary = monitor.get_summary()
        
        # 两轮数据应该不同
        assert first_summary != second_summary
        assert second_summary["total_loads"] == 1

