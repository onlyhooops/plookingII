"""
测试统一监控器模块

测试覆盖：
- MonitoringLevel 枚举
- PerformanceMetrics 数据类
- MemoryStatus 数据类
- UnifiedMonitor 类
- 全局单例函数
- monitor_performance 装饰器
"""

import threading
import time

import pytest

from plookingII.monitor.unified_monitor import (
    HAS_PSUTIL,
    MemoryStatus,
    MonitoringLevel,
    PerformanceMetrics,
    UnifiedMonitor,
    get_unified_monitor,
    monitor_performance,
    reset_unified_monitor,
)


class TestMonitoringLevel:
    """测试监控级别枚举"""

    def test_monitoring_levels_exist(self):
        """测试所有监控级别存在"""
        assert hasattr(MonitoringLevel, "MINIMAL")
        assert hasattr(MonitoringLevel, "STANDARD")
        assert hasattr(MonitoringLevel, "DETAILED")

    def test_monitoring_level_values(self):
        """测试监控级别的值"""
        assert MonitoringLevel.MINIMAL.value == "minimal"
        assert MonitoringLevel.STANDARD.value == "standard"
        assert MonitoringLevel.DETAILED.value == "detailed"

    def test_monitoring_level_comparison(self):
        """测试监控级别可以比较"""
        minimal = MonitoringLevel.MINIMAL
        standard = MonitoringLevel.STANDARD

        assert minimal == MonitoringLevel.MINIMAL
        assert minimal != standard


class TestPerformanceMetrics:
    """测试性能指标数据类"""

    def test_init_basic(self):
        """测试基本初始化"""
        metric = PerformanceMetrics(timestamp=1234567890.0, operation_name="test_op", duration_ms=100.5)

        assert metric.timestamp == 1234567890.0
        assert metric.operation_name == "test_op"
        assert metric.duration_ms == 100.5
        assert metric.memory_usage_mb == 0.0
        assert metric.cpu_usage_percent == 0.0
        assert metric.cache_hit is None
        assert metric.success is True
        assert metric.error_msg is None
        assert metric.metadata == {}

    def test_init_with_all_fields(self):
        """测试完整初始化"""
        metadata = {"key": "value"}
        metric = PerformanceMetrics(
            timestamp=1234567890.0,
            operation_name="test_op",
            duration_ms=100.5,
            memory_usage_mb=50.0,
            cpu_usage_percent=25.5,
            cache_hit=True,
            success=False,
            error_msg="Test error",
            metadata=metadata,
        )

        assert metric.memory_usage_mb == 50.0
        assert metric.cpu_usage_percent == 25.5
        assert metric.cache_hit is True
        assert metric.success is False
        assert metric.error_msg == "Test error"
        assert metric.metadata == metadata

    def test_to_dict(self):
        """测试转换为字典"""
        metric = PerformanceMetrics(timestamp=1234567890.0, operation_name="test_op", duration_ms=100.5, cache_hit=True)

        result = metric.to_dict()

        assert isinstance(result, dict)
        assert result["timestamp"] == 1234567890.0
        assert result["operation_name"] == "test_op"
        assert result["duration_ms"] == 100.5
        assert result["cache_hit"] is True


class TestMemoryStatus:
    """测试内存状态数据类"""

    def test_init_basic(self):
        """测试基本初始化"""
        status = MemoryStatus(used_mb=1000.0, available_mb=2000.0, total_mb=3000.0, percent=33.3, pressure_level="low")

        assert status.used_mb == 1000.0
        assert status.available_mb == 2000.0
        assert status.total_mb == 3000.0
        assert status.percent == 33.3
        assert status.pressure_level == "low"
        assert status.cache_usage_mb == 0.0
        assert status.recommendations == []

    def test_init_with_all_fields(self):
        """测试完整初始化"""
        recommendations = ["清理缓存", "关闭应用"]
        status = MemoryStatus(
            used_mb=1000.0,
            available_mb=2000.0,
            total_mb=3000.0,
            percent=33.3,
            pressure_level="high",
            cache_usage_mb=100.0,
            recommendations=recommendations,
        )

        assert status.cache_usage_mb == 100.0
        assert status.recommendations == recommendations

    def test_to_dict(self):
        """测试转换为字典"""
        status = MemoryStatus(used_mb=1000.0, available_mb=2000.0, total_mb=3000.0, percent=33.3, pressure_level="low")

        result = status.to_dict()

        assert isinstance(result, dict)
        assert result["used_mb"] == 1000.0
        assert result["percent"] == 33.3
        assert result["pressure_level"] == "low"


class TestUnifiedMonitorInit:
    """测试UnifiedMonitor初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        monitor = UnifiedMonitor()

        assert monitor.level == MonitoringLevel.STANDARD
        assert monitor.max_history == 500
        assert not monitor.is_monitoring
        assert monitor.monitor_thread is None
        assert len(monitor.performance_history) == 0
        assert len(monitor.memory_history) == 0

    def test_init_minimal_level(self):
        """测试最小监控级别"""
        monitor = UnifiedMonitor(level=MonitoringLevel.MINIMAL, max_history=200)

        assert monitor.level == MonitoringLevel.MINIMAL
        assert monitor.max_history == 100  # 被限制为最大100

    def test_init_detailed_level(self):
        """测试详细监控级别"""
        monitor = UnifiedMonitor(level=MonitoringLevel.DETAILED, max_history=500)

        assert monitor.level == MonitoringLevel.DETAILED
        assert monitor.max_history == 1000  # 被扩展为最小1000

    def test_init_stats(self):
        """测试初始统计数据"""
        monitor = UnifiedMonitor()

        assert monitor.stats["total_operations"] == 0
        assert monitor.stats["successful_operations"] == 0
        assert monitor.stats["failed_operations"] == 0
        assert monitor.stats["avg_response_time"] == 0.0
        assert monitor.stats["cache_hits"] == 0
        assert monitor.stats["cache_misses"] == 0

    def test_init_thresholds(self):
        """测试内存阈值配置"""
        monitor = UnifiedMonitor()

        assert "cleanup" in monitor.memory_thresholds
        assert "warning" in monitor.memory_thresholds
        assert "critical" in monitor.memory_thresholds

    @pytest.mark.skipif(not HAS_PSUTIL, reason="需要 psutil")
    def test_init_with_auto_monitoring(self):
        """测试自动启动监控"""
        monitor = UnifiedMonitor(enable_auto_monitoring=True)
        time.sleep(0.1)  # 等待线程启动

        assert monitor.is_monitoring

        # 清理
        monitor.stop_monitoring()


class TestRecordOperation:
    """测试记录操作"""

    def test_record_basic_operation(self):
        """测试记录基本操作"""
        monitor = UnifiedMonitor()

        monitor.record_operation("test_op", 100.0)

        assert monitor.stats["total_operations"] == 1
        assert monitor.stats["successful_operations"] == 1
        assert monitor.stats["avg_response_time"] == 100.0

    def test_record_failed_operation(self):
        """测试记录失败操作"""
        monitor = UnifiedMonitor()

        monitor.record_operation("test_op", 100.0, success=False)

        assert monitor.stats["total_operations"] == 1
        assert monitor.stats["successful_operations"] == 0
        assert monitor.stats["failed_operations"] == 1

    def test_record_with_cache_hit(self):
        """测试记录缓存命中"""
        monitor = UnifiedMonitor()

        monitor.record_operation("test_op", 50.0, cache_hit=True)

        assert monitor.stats["cache_hits"] == 1
        assert monitor.stats["cache_misses"] == 0

    def test_record_with_cache_miss(self):
        """测试记录缓存未命中"""
        monitor = UnifiedMonitor()

        monitor.record_operation("test_op", 150.0, cache_hit=False)

        assert monitor.stats["cache_hits"] == 0
        assert monitor.stats["cache_misses"] == 1

    def test_record_multiple_operations(self):
        """测试记录多个操作"""
        monitor = UnifiedMonitor()

        monitor.record_operation("op1", 100.0)
        monitor.record_operation("op2", 200.0)
        monitor.record_operation("op3", 300.0)

        assert monitor.stats["total_operations"] == 3
        assert monitor.stats["avg_response_time"] == 200.0

    def test_record_stores_in_history(self):
        """测试操作被存储到历史"""
        monitor = UnifiedMonitor()

        monitor.record_operation("test_op", 100.0)

        assert len(monitor.performance_history) == 1
        metric = monitor.performance_history[0]
        assert metric.operation_name == "test_op"
        assert metric.duration_ms == 100.0

    def test_record_minimal_level_no_history(self):
        """测试最小级别不记录历史"""
        monitor = UnifiedMonitor(level=MonitoringLevel.MINIMAL)

        monitor.record_operation("test_op", 100.0)

        # 统计仍然更新
        assert monitor.stats["total_operations"] == 1
        # 但历史不记录
        assert len(monitor.performance_history) == 0

    def test_record_with_metadata(self):
        """测试记录带元数据的操作"""
        monitor = UnifiedMonitor()

        monitor.record_operation("test_op", 100.0, user="admin", path="/test")

        metric = monitor.performance_history[0]
        assert metric.metadata["user"] == "admin"
        assert metric.metadata["path"] == "/test"


class TestGetMemoryStatus:
    """测试获取内存状态"""

    @pytest.mark.skipif(not HAS_PSUTIL, reason="需要 psutil")
    def test_get_memory_status_with_psutil(self):
        """测试使用psutil获取内存状态"""
        monitor = UnifiedMonitor()

        status = monitor.get_memory_status()

        assert isinstance(status, MemoryStatus)
        assert status.total_mb > 0
        assert 0 <= status.percent <= 100
        assert status.pressure_level in ["low", "medium", "high", "critical"]

    @pytest.mark.skipif(HAS_PSUTIL, reason="测试没有psutil的情况")
    def test_get_memory_status_without_psutil(self):
        """测试没有psutil时获取内存状态"""
        monitor = UnifiedMonitor()

        status = monitor.get_memory_status()

        assert status.pressure_level == "unknown"
        assert "psutil 未安装" in status.recommendations[0]

    @pytest.mark.skipif(not HAS_PSUTIL, reason="需要 psutil")
    def test_get_memory_status_detailed_level(self):
        """测试详细级别记录内存历史"""
        monitor = UnifiedMonitor(level=MonitoringLevel.DETAILED)

        monitor.get_memory_status()

        assert len(monitor.memory_history) == 1

    @pytest.mark.skipif(not HAS_PSUTIL, reason="需要 psutil")
    def test_get_memory_status_standard_level_no_history(self):
        """测试标准级别不记录内存历史"""
        monitor = UnifiedMonitor(level=MonitoringLevel.STANDARD)

        monitor.get_memory_status()

        assert len(monitor.memory_history) == 0


class TestPressureLevel:
    """测试压力级别判断"""

    def test_pressure_level_low(self):
        """测试低压力级别"""
        monitor = UnifiedMonitor()

        level = monitor._get_pressure_level(50.0)
        assert level == "low"

    def test_pressure_level_medium(self):
        """测试中等压力级别"""
        monitor = UnifiedMonitor()

        level = monitor._get_pressure_level(75.0)
        assert level == "medium"

    def test_pressure_level_high(self):
        """测试高压力级别"""
        monitor = UnifiedMonitor()

        level = monitor._get_pressure_level(85.0)
        assert level == "high"

    def test_pressure_level_critical(self):
        """测试临界压力级别"""
        monitor = UnifiedMonitor()

        level = monitor._get_pressure_level(96.0)
        assert level == "critical"

    def test_pressure_level_boundaries(self):
        """测试边界值"""
        monitor = UnifiedMonitor()

        assert monitor._get_pressure_level(69.9) == "low"
        assert monitor._get_pressure_level(70.0) == "medium"
        assert monitor._get_pressure_level(79.9) == "medium"
        assert monitor._get_pressure_level(80.0) == "high"


class TestGenerateRecommendations:
    """测试生成建议"""

    def test_recommendations_low(self):
        """测试低压力建议"""
        monitor = UnifiedMonitor()

        recs = monitor._generate_recommendations("low", 50.0)
        assert len(recs) == 0

    def test_recommendations_medium(self):
        """测试中等压力建议"""
        monitor = UnifiedMonitor()

        recs = monitor._generate_recommendations("medium", 75.0)
        assert len(recs) > 0
        assert "监控" in recs[0]

    def test_recommendations_high(self):
        """测试高压力建议"""
        monitor = UnifiedMonitor()

        recs = monitor._generate_recommendations("high", 85.0)
        assert len(recs) > 0
        assert "清理缓存" in recs[0]

    def test_recommendations_critical(self):
        """测试临界压力建议"""
        monitor = UnifiedMonitor()

        recs = monitor._generate_recommendations("critical", 96.0)
        assert len(recs) > 0
        assert "立即" in recs[0] or "极高" in recs[0]


class TestMonitoringControl:
    """测试监控控制"""

    @pytest.mark.skipif(not HAS_PSUTIL, reason="需要 psutil")
    def test_start_monitoring(self):
        """测试启动监控"""
        monitor = UnifiedMonitor()

        monitor.start_monitoring(interval=0.1)
        time.sleep(0.15)

        assert monitor.is_monitoring
        assert monitor.monitor_thread is not None
        assert monitor.monitor_thread.is_alive()

        # 清理
        monitor.stop_monitoring()

    @pytest.mark.skipif(not HAS_PSUTIL, reason="需要 psutil")
    def test_stop_monitoring(self):
        """测试停止监控"""
        monitor = UnifiedMonitor()

        monitor.start_monitoring(interval=0.1)
        time.sleep(0.15)
        monitor.stop_monitoring()

        assert not monitor.is_monitoring

    @pytest.mark.skipif(HAS_PSUTIL, reason="测试没有psutil的情况")
    def test_start_monitoring_without_psutil(self):
        """测试没有psutil时启动监控"""
        monitor = UnifiedMonitor()

        monitor.start_monitoring()

        # 不应该启动
        assert not monitor.is_monitoring

    def test_start_monitoring_already_running(self):
        """测试重复启动监控"""
        monitor = UnifiedMonitor()
        monitor.is_monitoring = True

        # 应该不会崩溃
        monitor.start_monitoring()

    def test_stop_monitoring_not_running(self):
        """测试停止未运行的监控"""
        monitor = UnifiedMonitor()

        # 应该不会崩溃
        monitor.stop_monitoring()


class TestGetStats:
    """测试获取统计"""

    def test_get_stats_empty(self):
        """测试获取空统计"""
        monitor = UnifiedMonitor()

        stats = monitor.get_stats()

        assert stats["total_operations"] == 0
        assert stats["cache_hit_ratio"] == 0.0
        assert stats["success_rate"] == 0.0

    def test_get_stats_with_data(self):
        """测试获取有数据的统计"""
        monitor = UnifiedMonitor()

        monitor.record_operation("op1", 100.0, cache_hit=True)
        monitor.record_operation("op2", 200.0, cache_hit=False)

        stats = monitor.get_stats()

        assert stats["total_operations"] == 2
        assert stats["cache_hit_ratio"] == 0.5
        assert stats["success_rate"] == 1.0

    def test_get_stats_with_failures(self):
        """测试包含失败的统计"""
        monitor = UnifiedMonitor()

        monitor.record_operation("op1", 100.0, success=True)
        monitor.record_operation("op2", 200.0, success=False)

        stats = monitor.get_stats()

        assert stats["success_rate"] == 0.5

    def test_get_stats_returns_copy(self):
        """测试返回的是副本"""
        monitor = UnifiedMonitor()

        stats1 = monitor.get_stats()
        stats1["modified"] = True
        stats2 = monitor.get_stats()

        assert "modified" not in stats2


class TestGetRecentOperations:
    """测试获取最近操作"""

    def test_get_recent_operations_empty(self):
        """测试空历史"""
        monitor = UnifiedMonitor()

        recent = monitor.get_recent_operations()
        assert len(recent) == 0

    def test_get_recent_operations_few(self):
        """测试少量操作"""
        monitor = UnifiedMonitor()

        for i in range(5):
            monitor.record_operation(f"op{i}", 100.0)

        recent = monitor.get_recent_operations(10)
        assert len(recent) == 5

    def test_get_recent_operations_many(self):
        """测试大量操作"""
        monitor = UnifiedMonitor()

        for i in range(20):
            monitor.record_operation(f"op{i}", 100.0)

        recent = monitor.get_recent_operations(10)
        assert len(recent) == 10
        # 应该是最后10个
        assert recent[-1].operation_name == "op19"

    def test_get_recent_operations_order(self):
        """测试操作顺序"""
        monitor = UnifiedMonitor()

        monitor.record_operation("first", 100.0)
        monitor.record_operation("second", 200.0)
        monitor.record_operation("third", 300.0)

        recent = monitor.get_recent_operations(2)
        assert len(recent) == 2
        assert recent[0].operation_name == "second"
        assert recent[1].operation_name == "third"


class TestClearAndReset:
    """测试清除和重置"""

    def test_clear_history(self):
        """测试清除历史"""
        monitor = UnifiedMonitor()

        monitor.record_operation("op1", 100.0)
        monitor.clear_history()

        assert len(monitor.performance_history) == 0
        assert len(monitor.memory_history) == 0

    def test_reset_stats(self):
        """测试重置统计"""
        monitor = UnifiedMonitor()

        monitor.record_operation("op1", 100.0, cache_hit=True)
        monitor.reset_stats()

        assert monitor.stats["total_operations"] == 0
        assert monitor.stats["cache_hits"] == 0

    def test_reset_stats_preserves_history(self):
        """测试重置统计不影响历史"""
        monitor = UnifiedMonitor()

        monitor.record_operation("op1", 100.0)
        history_len = len(monitor.performance_history)

        monitor.reset_stats()

        assert len(monitor.performance_history) == history_len


class TestGlobalSingleton:
    """测试全局单例"""

    def test_get_unified_monitor_creates_instance(self):
        """测试获取全局监控器"""
        reset_unified_monitor()  # 先重置

        monitor = get_unified_monitor()

        assert isinstance(monitor, UnifiedMonitor)

    def test_get_unified_monitor_singleton(self):
        """测试单例模式"""
        reset_unified_monitor()

        monitor1 = get_unified_monitor()
        monitor2 = get_unified_monitor()

        assert monitor1 is monitor2

    def test_get_unified_monitor_with_level(self):
        """测试指定级别创建"""
        reset_unified_monitor()

        monitor = get_unified_monitor(level=MonitoringLevel.MINIMAL)

        assert monitor.level == MonitoringLevel.MINIMAL

    def test_reset_unified_monitor(self):
        """测试重置全局监控器"""
        monitor1 = get_unified_monitor()
        reset_unified_monitor()
        monitor2 = get_unified_monitor()

        assert monitor1 is not monitor2

    @pytest.mark.skipif(not HAS_PSUTIL, reason="需要 psutil")
    def test_reset_stops_monitoring(self):
        """测试重置会停止监控"""
        reset_unified_monitor()
        monitor = get_unified_monitor(enable_auto_monitoring=True)
        time.sleep(0.1)

        assert monitor.is_monitoring

        reset_unified_monitor()

        # 监控应该已经停止


class TestMonitorPerformanceDecorator:
    """测试性能监控装饰器"""

    def test_decorator_basic(self):
        """测试基本装饰器功能"""
        reset_unified_monitor()

        @monitor_performance("test_func")
        def test_function():
            time.sleep(0.01)
            return "result"

        result = test_function()

        assert result == "result"

        monitor = get_unified_monitor()
        assert monitor.stats["total_operations"] == 1

    def test_decorator_records_success(self):
        """测试装饰器记录成功"""
        reset_unified_monitor()

        @monitor_performance("test_func")
        def test_function():
            return "ok"

        test_function()

        monitor = get_unified_monitor()
        assert monitor.stats["successful_operations"] == 1

    def test_decorator_records_failure(self):
        """测试装饰器记录失败"""
        reset_unified_monitor()

        @monitor_performance("test_func")
        def test_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            test_function()

        monitor = get_unified_monitor()
        assert monitor.stats["failed_operations"] == 1

    def test_decorator_records_duration(self):
        """测试装饰器记录时长"""
        reset_unified_monitor()

        @monitor_performance("test_func")
        def test_function():
            time.sleep(0.01)

        test_function()

        monitor = get_unified_monitor()
        assert monitor.stats["avg_response_time"] >= 10.0  # 至少10ms

    def test_decorator_with_args(self):
        """测试装饰器处理参数"""
        reset_unified_monitor()

        @monitor_performance("add")
        def add(a, b):
            return a + b

        result = add(2, 3)

        assert result == 5

        monitor = get_unified_monitor()
        assert monitor.stats["total_operations"] == 1

    def test_decorator_preserves_function_name(self):
        """测试装饰器保留函数名"""

        @monitor_performance("test")
        def my_function():
            pass

        assert my_function.__name__ == "my_function"


class TestThreadSafety:
    """测试线程安全"""

    def test_concurrent_record_operations(self):
        """测试并发记录操作"""
        monitor = UnifiedMonitor()

        def record_many():
            for i in range(100):
                monitor.record_operation(f"op{i}", 100.0)

        threads = [threading.Thread(target=record_many) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert monitor.stats["total_operations"] == 500

    def test_concurrent_get_stats(self):
        """测试并发获取统计"""
        monitor = UnifiedMonitor()
        monitor.record_operation("op1", 100.0)

        results = []

        def get_stats_many():
            for _ in range(50):
                results.append(monitor.get_stats())

        threads = [threading.Thread(target=get_stats_many) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 应该成功获取所有统计
        assert len(results) == 150


class TestEdgeCases:
    """测试边缘情况"""

    def test_max_history_limit(self):
        """测试历史记录限制"""
        monitor = UnifiedMonitor(max_history=10)

        for i in range(20):
            monitor.record_operation(f"op{i}", 100.0)

        # 应该只保留最后10个
        assert len(monitor.performance_history) == 10

    def test_zero_operations(self):
        """测试零操作的统计"""
        monitor = UnifiedMonitor()

        stats = monitor.get_stats()

        # 不应该有除零错误
        assert stats["avg_response_time"] == 0.0
        assert stats["success_rate"] == 0.0
        assert stats["cache_hit_ratio"] == 0.0

    def test_very_large_duration(self):
        """测试非常大的时长"""
        monitor = UnifiedMonitor()

        monitor.record_operation("slow_op", 999999.0)

        assert monitor.stats["avg_response_time"] == 999999.0

    def test_negative_duration(self):
        """测试负数时长"""
        monitor = UnifiedMonitor()

        # 应该接受但可能不符合预期
        monitor.record_operation("strange_op", -10.0)

        assert monitor.stats["total_operations"] == 1


class TestIntegration:
    """集成测试"""

    def test_complete_workflow(self):
        """测试完整工作流"""
        monitor = UnifiedMonitor(level=MonitoringLevel.STANDARD)

        # 记录一些操作
        monitor.record_operation("load_image", 150.0, cache_hit=False)  # success=True (默认)
        monitor.record_operation("load_image", 50.0, cache_hit=True)  # success=True (默认)
        monitor.record_operation("save_image", 200.0, success=True)
        monitor.record_operation("delete_image", 100.0, success=False)

        # 获取统计
        stats = monitor.get_stats()
        assert stats["total_operations"] == 4
        assert stats["successful_operations"] == 3  # 前3个都成功
        assert stats["failed_operations"] == 1
        assert stats["cache_hit_ratio"] == 0.5

        # 获取最近操作
        recent = monitor.get_recent_operations(2)
        assert len(recent) == 2

        # 清除历史
        monitor.clear_history()
        assert len(monitor.performance_history) == 0

        # 重置统计
        monitor.reset_stats()
        assert monitor.stats["total_operations"] == 0

    @pytest.mark.skipif(not HAS_PSUTIL, reason="需要 psutil")
    def test_monitoring_workflow(self):
        """测试监控工作流"""
        monitor = UnifiedMonitor()

        # 启动监控
        monitor.start_monitoring(interval=0.1)
        time.sleep(0.15)

        # 获取内存状态
        status = monitor.get_memory_status()
        assert status.total_mb > 0

        # 停止监控
        monitor.stop_monitoring()
        assert not monitor.is_monitoring
