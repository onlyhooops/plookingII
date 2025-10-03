"""
统一监控系统单元测试

测试 UnifiedMonitorV2 和监控适配器的功能。
"""

import pytest
import time
from plookingII.monitor.unified import (
    UnifiedMonitorV2,
    MonitoringLevel,
    MemoryStatus,
    get_unified_monitor,
    monitor_performance,
    LightweightPerformanceMonitorAdapter,
    SimplifiedMemoryMonitorAdapter,
    LightweightMonitorAdapter,
)
from plookingII.monitor.unified.unified_monitor_v2 import reset_unified_monitor


class TestUnifiedMonitorV2:
    """测试 UnifiedMonitorV2 核心功能"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前后重置监控器"""
        reset_unified_monitor()
        yield
        reset_unified_monitor()

    def test_basic_initialization(self):
        """测试基本初始化"""
        monitor = UnifiedMonitorV2(level=MonitoringLevel.STANDARD)
        assert monitor.level == MonitoringLevel.STANDARD
        assert not monitor.is_monitoring
        assert monitor.stats['total_operations'] == 0

    def test_monitoring_levels(self):
        """测试不同监控级别"""
        # 最小级别
        monitor_minimal = UnifiedMonitorV2(level=MonitoringLevel.MINIMAL, max_history=1000)
        assert monitor_minimal.max_history == 100  # 应该被限制

        # 标准级别
        monitor_standard = UnifiedMonitorV2(level=MonitoringLevel.STANDARD, max_history=1000)
        assert monitor_standard.max_history == 500  # 应该被限制

        # 详细级别
        monitor_detailed = UnifiedMonitorV2(level=MonitoringLevel.DETAILED, max_history=1000)
        assert monitor_detailed.max_history == 1000  # 使用完整值

    def test_record_operation(self):
        """测试记录操作"""
        monitor = UnifiedMonitorV2()

        monitor.record_operation("test_op", duration_ms=100.0, success=True)

        assert monitor.stats['total_operations'] == 1
        assert monitor.stats['successful_operations'] == 1
        assert monitor.stats['avg_duration_ms'] == 100.0

    def test_record_operation_with_cache(self):
        """测试记录带缓存的操作"""
        monitor = UnifiedMonitorV2()

        monitor.record_operation("load_image", duration_ms=50.0, cache_hit=True)
        monitor.record_operation("load_image", duration_ms=200.0, cache_hit=False)

        assert monitor.stats['cache_hits'] == 1
        assert monitor.stats['cache_misses'] == 1
        assert monitor.stats['cache_hit_rate'] == 0.5

    def test_record_operation_error(self):
        """测试记录错误操作"""
        monitor = UnifiedMonitorV2()

        monitor.record_operation(
            "failed_op",
            duration_ms=10.0,
            success=False,
            error_msg="Test error"
        )

        assert monitor.stats['failed_operations'] == 1
        assert monitor.stats['error_count'] == 1
        assert monitor.stats['error_rate'] == 1.0

    def test_cache_hit_miss_recording(self):
        """测试缓存命中/未命中记录"""
        monitor = UnifiedMonitorV2()

        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_miss()

        assert monitor.stats['cache_hits'] == 2
        assert monitor.stats['cache_misses'] == 1
        assert monitor.stats['cache_hit_rate'] == pytest.approx(0.6667, rel=1e-3)

    def test_memory_status(self):
        """测试内存状态获取"""
        monitor = UnifiedMonitorV2()
        memory_status = monitor.get_memory_status()

        assert isinstance(memory_status, MemoryStatus)
        assert memory_status.used_mb >= 0
        assert memory_status.available_mb >= 0
        assert memory_status.total_mb > 0
        assert memory_status.pressure_level in ['low', 'medium', 'high', 'critical', 'unknown']

    def test_memory_pressure_detection(self):
        """测试内存压力检测"""
        monitor = UnifiedMonitorV2()

        # 应该能够调用而不抛出异常
        is_pressure = monitor.is_memory_pressure()
        assert isinstance(is_pressure, bool)

    def test_performance_summary(self):
        """测试性能摘要"""
        monitor = UnifiedMonitorV2()

        # 记录一些操作
        for i in range(10):
            monitor.record_operation(f"op_{i}", duration_ms=50.0 + i * 10)

        summary = monitor.get_performance_summary()

        assert summary['total_operations'] == 10
        assert summary['avg_duration_ms'] > 0
        assert summary['min_duration_ms'] == 50.0
        assert summary['max_duration_ms'] == 140.0

    def test_get_stats(self):
        """测试获取统计信息"""
        monitor = UnifiedMonitorV2()

        monitor.record_operation("test", duration_ms=100.0)

        stats = monitor.get_stats()

        assert 'total_operations' in stats
        assert 'uptime_seconds' in stats
        assert 'memory_status' in stats
        assert 'recommendations' in stats

    def test_force_cleanup(self):
        """测试强制内存清理"""
        monitor = UnifiedMonitorV2()

        initial_cleanups = monitor.stats['memory_cleanups']
        monitor.force_cleanup()

        assert monitor.stats['memory_cleanups'] == initial_cleanups + 1

    def test_reset_stats(self):
        """测试重置统计"""
        monitor = UnifiedMonitorV2()

        # 记录一些数据
        monitor.record_operation("test", duration_ms=100.0)
        monitor.record_cache_hit()

        # 重置
        monitor.reset_stats()

        assert monitor.stats['total_operations'] == 0
        assert monitor.stats['cache_hits'] == 0
        assert len(monitor.performance_history) == 0

    def test_dashboard_data(self):
        """测试监控面板数据"""
        monitor = UnifiedMonitorV2()

        monitor.record_operation("test", duration_ms=100.0, cache_hit=True)

        dashboard = monitor.get_dashboard_data()

        assert 'performance' in dashboard
        assert 'memory' in dashboard
        assert 'system' in dashboard
        assert 'statistics' in dashboard
        assert 'recommendations' in dashboard

    def test_operation_type_tracking_detailed(self):
        """测试详细模式下的操作类型跟踪"""
        monitor = UnifiedMonitorV2(level=MonitoringLevel.DETAILED)

        monitor.record_operation("load_image", duration_ms=100.0)
        monitor.record_operation("load_image", duration_ms=150.0)
        monitor.record_operation("save_image", duration_ms=200.0)

        assert monitor.operation_counts['load_image'] == 2
        assert monitor.operation_counts['save_image'] == 1
        assert len(monitor.operation_durations['load_image']) == 2

    def test_slow_operation_warning(self, caplog):
        """测试慢操作警告"""
        monitor = UnifiedMonitorV2(level=MonitoringLevel.STANDARD)

        # 记录一个慢操作（超过1秒）
        monitor.record_operation("slow_op", duration_ms=1500.0)

        # 检查日志中是否有警告（如果配置了日志）
        # 注意：这个测试依赖于日志配置

    def test_monitoring_start_stop(self):
        """测试启动和停止监控"""
        monitor = UnifiedMonitorV2()

        # 启动监控
        monitor.start_monitoring(interval=0.1)
        assert monitor.is_monitoring
        time.sleep(0.3)  # 等待至少一次收集

        # 停止监控
        monitor.stop_monitoring()
        assert not monitor.is_monitoring


class TestGlobalMonitor:
    """测试全局监控器单例"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前后重置监控器"""
        reset_unified_monitor()
        yield
        reset_unified_monitor()

    def test_get_unified_monitor_singleton(self):
        """测试全局单例模式"""
        monitor1 = get_unified_monitor()
        monitor2 = get_unified_monitor()

        assert monitor1 is monitor2  # 应该是同一个实例

    def test_get_unified_monitor_with_level(self):
        """测试使用不同级别获取监控器"""
        monitor = get_unified_monitor(level=MonitoringLevel.MINIMAL)
        assert monitor.level == MonitoringLevel.MINIMAL


class TestMonitorPerformanceDecorator:
    """测试性能监控装饰器"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前后重置监控器"""
        reset_unified_monitor()
        yield
        reset_unified_monitor()

    def test_decorator_success(self):
        """测试装饰器成功情况"""
        @monitor_performance("test_function")
        def test_func():
            time.sleep(0.01)
            return "result"

        result = test_func()

        assert result == "result"

        monitor = get_unified_monitor()
        assert monitor.stats['total_operations'] == 1
        assert monitor.stats['successful_operations'] == 1

    def test_decorator_failure(self):
        """测试装饰器失败情况"""
        @monitor_performance("test_function_error")
        def test_func_error():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            test_func_error()

        monitor = get_unified_monitor()
        assert monitor.stats['total_operations'] == 1
        assert monitor.stats['failed_operations'] == 1


class TestLightweightPerformanceMonitorAdapter:
    """测试 LightweightPerformanceMonitor 适配器"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前后重置监控器"""
        reset_unified_monitor()
        yield
        reset_unified_monitor()

    def test_adapter_basic_usage(self):
        """测试适配器基本使用"""
        adapter = LightweightPerformanceMonitorAdapter(history_size=100)

        adapter.record_load_operation(load_time=0.5, cache_hit=True)
        adapter.record_load_operation(load_time=1.0, cache_hit=False, error=False)

        summary = adapter.get_performance_summary()

        assert summary['summary']['total_operations'] == 2
        assert summary['detailed']['cache_hits'] == 1
        assert summary['detailed']['cache_misses'] == 1

    def test_adapter_health_status(self):
        """测试健康状态"""
        adapter = LightweightPerformanceMonitorAdapter()

        # 记录正常操作
        adapter.record_load_operation(load_time=0.1, cache_hit=True)

        health = adapter.get_health_status()
        assert health in ['good', 'warning', 'critical']

    def test_adapter_simple_stats(self):
        """测试简化统计"""
        adapter = LightweightPerformanceMonitorAdapter()

        adapter.record_load_operation(load_time=0.5, cache_hit=True)

        stats = adapter.get_simple_stats()

        assert 'operations' in stats
        assert 'avg_time_ms' in stats
        assert 'cache_hit_rate' in stats
        assert 'health' in stats


class TestSimplifiedMemoryMonitorAdapter:
    """测试 SimplifiedMemoryMonitor 适配器"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前后重置监控器"""
        reset_unified_monitor()
        yield
        reset_unified_monitor()

    def test_adapter_memory_usage(self):
        """测试内存使用量获取"""
        adapter = SimplifiedMemoryMonitorAdapter()

        memory_usage = adapter.get_memory_usage()
        assert memory_usage >= 0

    def test_adapter_memory_pressure(self):
        """测试内存压力检测"""
        adapter = SimplifiedMemoryMonitorAdapter()

        is_pressure = adapter.is_memory_pressure()
        assert isinstance(is_pressure, bool)

    def test_adapter_memory_info(self):
        """测试内存信息获取"""
        adapter = SimplifiedMemoryMonitorAdapter()

        info = adapter.get_memory_info()

        assert 'used_mb' in info
        assert 'available_mb' in info
        assert 'pressure' in info
        assert 'recommendations' in info

    def test_adapter_memory_checks(self):
        """测试各种内存检查"""
        adapter = SimplifiedMemoryMonitorAdapter()

        assert isinstance(adapter.is_preload_memory_high(), bool)
        assert isinstance(adapter.is_main_memory_high(), bool)
        assert isinstance(adapter.is_memory_high(), bool)

    def test_adapter_force_gc(self):
        """测试强制垃圾回收"""
        adapter = SimplifiedMemoryMonitorAdapter()

        # 应该能够调用而不抛出异常
        adapter.force_garbage_collection()


class TestLightweightMonitorAdapter:
    """测试 LightweightMonitor 适配器"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前后重置监控器"""
        reset_unified_monitor()
        yield
        reset_unified_monitor()

    def test_adapter_record_load(self):
        """测试记录加载"""
        adapter = LightweightMonitorAdapter()

        adapter.record_load(load_time=0.5, cache_hit=True)
        adapter.record_load(load_time=1.0, cache_hit=False)

        stats = adapter.get_stats()

        assert stats['total_loads'] == 2
        assert stats['cache_hit_rate'] == 0.5

    def test_adapter_reset(self):
        """测试重置"""
        adapter = LightweightMonitorAdapter()

        adapter.record_load(load_time=0.5)
        adapter.reset()

        stats = adapter.get_stats()
        assert stats['total_loads'] == 0


class TestPerformanceRecommendations:
    """测试性能建议系统"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前后重置监控器"""
        reset_unified_monitor()
        yield
        reset_unified_monitor()

    def test_slow_operation_recommendation(self):
        """测试慢操作建议"""
        monitor = UnifiedMonitorV2()

        # 记录多个慢操作
        for _ in range(10):
            monitor.record_operation("slow_op", duration_ms=2000.0)

        recommendations = monitor._get_performance_recommendations()

        # 应该有关于响应时间的建议
        assert any('响应时间' in rec for rec in recommendations)

    def test_low_cache_hit_rate_recommendation(self):
        """测试低缓存命中率建议"""
        monitor = UnifiedMonitorV2()

        # 记录低命中率操作
        for _ in range(20):
            monitor.record_operation("op", duration_ms=100.0, cache_hit=False)
        monitor.record_operation("op", duration_ms=100.0, cache_hit=True)

        recommendations = monitor._get_performance_recommendations()

        # 应该有关于缓存的建议
        assert any('缓存' in rec for rec in recommendations)

    def test_high_error_rate_recommendation(self):
        """测试高错误率建议"""
        monitor = UnifiedMonitorV2()

        # 记录多个错误
        for _ in range(10):
            monitor.record_operation("op", duration_ms=100.0, success=False)

        recommendations = monitor._get_performance_recommendations()

        # 应该有关于错误的建议
        assert any('错误' in rec for rec in recommendations)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
