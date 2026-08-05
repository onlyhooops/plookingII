"""
测试加载统计模块

测试覆盖：
- LoadingStats 数据类
- 记录成功/失败
- 统计查询
- 重置功能
"""


from plookingII.core.loading.stats import LoadingStats


class TestLoadingStatsInit:
    """测试LoadingStats初始化"""

    def test_default_initialization(self):
        """测试默认初始化"""
        stats = LoadingStats()
        assert stats.total_requests == 0
        assert stats.successful_loads == 0
        assert stats.failed_loads == 0
        assert stats.total_time == 0.0
        assert stats.nsimage_loads == 0
        assert stats.quartz_loads == 0
        assert stats.memory_map_loads == 0
        assert stats.fast_loads == 0

    def test_custom_initialization(self):
        """测试自定义初始化"""
        stats = LoadingStats(total_requests=10, successful_loads=8, failed_loads=2, total_time=5.0)
        assert stats.total_requests == 10
        assert stats.successful_loads == 8
        assert stats.failed_loads == 2
        assert stats.total_time == 5.0


class TestRecordSuccess:
    """测试记录成功加载"""

    def test_record_nsimage_success(self):
        """测试记录NSImage加载成功"""
        stats = LoadingStats()
        stats.record_success("nsimage", 0.5)

        assert stats.total_requests == 1
        assert stats.successful_loads == 1
        assert stats.failed_loads == 0
        assert stats.total_time == 0.5
        assert stats.nsimage_loads == 1
        assert stats.quartz_loads == 0

    def test_record_quartz_success(self):
        """测试记录Quartz加载成功"""
        stats = LoadingStats()
        stats.record_success("quartz", 0.3)

        assert stats.quartz_loads == 1
        assert stats.total_time == 0.3

    def test_record_memory_map_success(self):
        """测试记录内存映射加载成功"""
        stats = LoadingStats()
        stats.record_success("memory_map", 0.1)

        assert stats.memory_map_loads == 1
        assert stats.total_time == 0.1

    def test_record_fast_success(self):
        """测试记录快速加载成功"""
        stats = LoadingStats()
        stats.record_success("fast", 0.05)

        assert stats.fast_loads == 1
        assert stats.total_time == 0.05

    def test_record_unknown_method(self):
        """测试记录未知方法（不应影响分类统计）"""
        stats = LoadingStats()
        stats.record_success("unknown_method", 0.2)

        assert stats.total_requests == 1
        assert stats.successful_loads == 1
        assert stats.total_time == 0.2
        # 分类统计不变
        assert stats.nsimage_loads == 0
        assert stats.quartz_loads == 0
        assert stats.memory_map_loads == 0
        assert stats.fast_loads == 0

    def test_record_multiple_successes(self):
        """测试记录多次成功"""
        stats = LoadingStats()
        stats.record_success("nsimage", 0.5)
        stats.record_success("quartz", 0.3)
        stats.record_success("nsimage", 0.4)

        assert stats.total_requests == 3
        assert stats.successful_loads == 3
        assert stats.nsimage_loads == 2
        assert stats.quartz_loads == 1
        # 使用近似比较以避免浮点数精度问题
        assert abs(stats.total_time - 1.2) < 0.001


class TestRecordFailure:
    """测试记录失败加载"""

    def test_record_single_failure(self):
        """测试记录单次失败"""
        stats = LoadingStats()
        stats.record_failure()

        assert stats.total_requests == 1
        assert stats.successful_loads == 0
        assert stats.failed_loads == 1

    def test_record_multiple_failures(self):
        """测试记录多次失败"""
        stats = LoadingStats()
        for _ in range(5):
            stats.record_failure()

        assert stats.total_requests == 5
        assert stats.failed_loads == 5

    def test_mixed_success_and_failure(self):
        """测试混合记录成功和失败"""
        stats = LoadingStats()
        stats.record_success("nsimage", 0.5)
        stats.record_failure()
        stats.record_success("quartz", 0.3)
        stats.record_failure()

        assert stats.total_requests == 4
        assert stats.successful_loads == 2
        assert stats.failed_loads == 2


class TestGetStats:
    """测试获取统计信息"""

    def test_get_empty_stats(self):
        """测试获取空统计"""
        stats = LoadingStats()
        result = stats.get_stats()

        assert result["total_requests"] == 0
        assert result["successful_loads"] == 0
        assert result["failed_loads"] == 0
        assert result["total_time"] == 0.0
        assert result["avg_time"] == 0.0
        assert result["total_loads"] == 0  # 兼容字段

    def test_get_stats_with_data(self):
        """测试获取有数据的统计"""
        stats = LoadingStats()
        stats.record_success("nsimage", 0.5)
        stats.record_success("quartz", 0.3)
        stats.record_failure()

        result = stats.get_stats()

        assert result["total_requests"] == 3
        assert result["successful_loads"] == 2
        assert result["failed_loads"] == 1
        assert result["total_time"] == 0.8
        assert abs(result["avg_time"] - 0.8 / 3) < 0.001
        assert result["nsimage_loads"] == 1
        assert result["quartz_loads"] == 1

    def test_average_time_calculation(self):
        """测试平均时间计算"""
        stats = LoadingStats()
        stats.record_success("nsimage", 1.0)
        stats.record_success("quartz", 2.0)
        stats.record_success("fast", 3.0)

        result = stats.get_stats()
        assert abs(result["avg_time"] - 2.0) < 0.001

    def test_backward_compatibility_field(self):
        """测试向后兼容字段"""
        stats = LoadingStats()
        stats.record_success("nsimage", 0.5)

        result = stats.get_stats()
        # total_loads 应该等于 total_requests
        assert result["total_loads"] == result["total_requests"]


class TestReset:
    """测试重置统计"""

    def test_reset_empty_stats(self):
        """测试重置空统计"""
        stats = LoadingStats()
        stats.reset()

        assert stats.total_requests == 0
        assert stats.successful_loads == 0

    def test_reset_with_data(self):
        """测试重置有数据的统计"""
        stats = LoadingStats()
        stats.record_success("nsimage", 0.5)
        stats.record_success("quartz", 0.3)
        stats.record_failure()

        stats.reset()

        assert stats.total_requests == 0
        assert stats.successful_loads == 0
        assert stats.failed_loads == 0
        assert stats.total_time == 0.0
        assert stats.nsimage_loads == 0
        assert stats.quartz_loads == 0
        assert stats.memory_map_loads == 0
        assert stats.fast_loads == 0

    def test_reset_and_reuse(self):
        """测试重置后重新使用"""
        stats = LoadingStats()
        stats.record_success("nsimage", 0.5)
        stats.reset()
        stats.record_success("quartz", 0.3)

        assert stats.total_requests == 1
        assert stats.successful_loads == 1
        assert stats.quartz_loads == 1
        assert stats.nsimage_loads == 0


class TestStringRepresentation:
    """测试字符串表示"""

    def test_str_empty_stats(self):
        """测试空统计的字符串表示"""
        stats = LoadingStats()
        result = str(stats)

        assert "requests=0" in result
        assert "success=0" in result
        assert "failed=0" in result
        assert "avg_time=0.000s" in result

    def test_str_with_data(self):
        """测试有数据的统计字符串表示"""
        stats = LoadingStats()
        stats.record_success("nsimage", 0.5)
        stats.record_success("quartz", 0.3)
        stats.record_failure()

        result = str(stats)

        assert "requests=3" in result
        assert "success=2" in result
        assert "failed=1" in result
        assert "avg_time=" in result


class TestEdgeCases:
    """测试边缘情况"""

    def test_very_large_numbers(self):
        """测试非常大的数字"""
        stats = LoadingStats()
        for i in range(10000):
            stats.record_success("nsimage", 0.001)

        assert stats.total_requests == 10000
        assert stats.successful_loads == 10000
        assert abs(stats.total_time - 10.0) < 0.1

    def test_very_small_durations(self):
        """测试非常小的耗时"""
        stats = LoadingStats()
        stats.record_success("fast", 0.000001)

        result = stats.get_stats()
        assert result["avg_time"] > 0

    def test_zero_duration(self):
        """测试零耗时"""
        stats = LoadingStats()
        stats.record_success("fast", 0.0)

        assert stats.total_time == 0.0
        result = stats.get_stats()
        assert result["avg_time"] == 0.0

    def test_all_methods_combination(self):
        """测试所有方法的组合"""
        stats = LoadingStats()
        stats.record_success("nsimage", 0.5)
        stats.record_success("quartz", 0.3)
        stats.record_success("memory_map", 0.1)
        stats.record_success("fast", 0.05)
        stats.record_failure()

        result = stats.get_stats()
        assert result["total_requests"] == 5
        assert result["successful_loads"] == 4
        assert result["failed_loads"] == 1
        assert result["nsimage_loads"] == 1
        assert result["quartz_loads"] == 1
        assert result["memory_map_loads"] == 1
        assert result["fast_loads"] == 1


class TestDataclassFunctionality:
    """测试数据类功能"""

    def test_equality(self):
        """测试相等性比较"""
        stats1 = LoadingStats(total_requests=5, successful_loads=3)
        stats2 = LoadingStats(total_requests=5, successful_loads=3)
        stats3 = LoadingStats(total_requests=4, successful_loads=3)

        assert stats1 == stats2
        assert stats1 != stats3

    def test_repr(self):
        """测试repr"""
        stats = LoadingStats(total_requests=5, successful_loads=3)
        repr_str = repr(stats)

        assert "LoadingStats" in repr_str
        assert "total_requests=5" in repr_str
        assert "successful_loads=3" in repr_str
