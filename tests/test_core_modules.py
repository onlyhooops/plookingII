#!/usr/bin/env python3
"""
核心模块测试
测试核心功能模块的详细功能
"""

import unittest
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestOptimizedLoadingStrategies(unittest.TestCase):
    """测试优化加载策略"""

    def setUp(self):
        """测试前准备"""
        from plookingII.core.optimized_loading_strategies import OptimizedLoadingStrategy, PreviewLoadingStrategy, AutoLoadingStrategy
        self.optimized_strategy = OptimizedLoadingStrategy()
        self.preview_strategy = PreviewLoadingStrategy()
        self.auto_strategy = AutoLoadingStrategy()

    def test_strategy_creation(self):
        """测试策略创建"""
        from plookingII.core.optimized_loading_strategies import OptimizedLoadingStrategyFactory

        # 测试所有策略创建
        strategies = ["optimized", "preview", "auto", "fast"]
        for strategy_name in strategies:
            strategy = OptimizedLoadingStrategyFactory.create_strategy(strategy_name)
            self.assertIsNotNone(strategy)

    def test_strategy_stats(self):
        """测试策略统计"""
        # 测试统计更新
        self.optimized_strategy.update_stats(True, 0.1)
        self.optimized_strategy.update_stats(False, 0.2)

        stats = self.optimized_strategy.get_stats()
        self.assertIn("total_loads", stats)
        self.assertIn("successful_loads", stats)
        self.assertIn("failed_loads", stats)
        self.assertEqual(stats["total_loads"], 2)
        self.assertEqual(stats["successful_loads"], 1)
        self.assertEqual(stats["failed_loads"], 1)

    def test_file_size_calculation(self):
        """测试文件大小计算"""
        # 测试文件大小计算
        file_size = self.optimized_strategy._get_file_size_mb("/nonexistent/file.jpg")
        self.assertEqual(file_size, 0.0)

# TestOptimizedCacheStrategies removed - OptimizedCacheStrategies module was removed in v1.4.0

class TestBaseClasses(unittest.TestCase):
    """测试基础类"""

    def test_base_component(self):
        """测试基础组件"""
        from plookingII.core.base_classes import BaseComponent

        class TestComponent(BaseComponent):
            def __init__(self):
                super().__init__()
                self.name = "test"

        component = TestComponent()
        self.assertEqual(component.name, "test")
        self.assertIsNotNone(component.get_stats())

    def test_statistics_mixin(self):
        """测试统计混入"""
        from plookingII.core.base_classes import StatisticsMixin

        class TestStats(StatisticsMixin):
            def __init__(self):
                super().__init__()
                self.stats = {}

        obj = TestStats()
        obj.update_stats(True, 0.1)
        stats = obj.get_stats()
        self.assertIn("total_operations", stats)

    def test_error_handling_mixin(self):
        """测试错误处理混入"""
        from plookingII.core.base_classes import ErrorHandlingMixin

        class TestErrorHandler(ErrorHandlingMixin):
            def __init__(self):
                super().__init__()

        obj = TestErrorHandler()
        self.assertIsNotNone(obj.error_handler)

class TestErrorHandling(unittest.TestCase):
    """测试错误处理"""

    def test_error_categories(self):
        """测试错误类别"""
        from plookingII.core.error_handling import ErrorCategory, ErrorSeverity

        # 测试错误类别
        self.assertEqual(ErrorCategory.MEMORY.value, "memory")
        self.assertEqual(ErrorCategory.SYSTEM.value, "system")

        # 测试错误严重程度
        self.assertEqual(ErrorSeverity.LOW.value, "low")
        self.assertEqual(ErrorSeverity.HIGH.value, "high")

    def test_error_creation(self):
        """测试错误创建"""
        from plookingII.core.error_handling import PlookingIIError, ErrorCategory, ErrorSeverity

        error = PlookingIIError("Test error", ErrorCategory.MEMORY, ErrorSeverity.MEDIUM)
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.category, ErrorCategory.MEMORY)
        self.assertEqual(error.severity, ErrorSeverity.MEDIUM)

class TestUnifiedConfig(unittest.TestCase):
    """测试统一配置"""

    def test_config_creation(self):
        """测试配置创建"""
        from plookingII.config.manager import ConfigManager

        config = ConfigManager()
        self.assertIsNotNone(config)

    def test_config_schema(self):
        """测试配置模式"""
        from plookingII.config.manager import ConfigManager

        config = ConfigManager()
        self.assertIsNotNone(config._schemas)

class TestOptimizedAlgorithms(unittest.TestCase):
    """测试优化算法"""

    def test_batch_processing(self):
        """测试批处理"""
        from plookingII.core.optimized_algorithms import OptimizedAlgorithms

        data = list(range(10))
        def square(x):
            return x * x

        results = OptimizedAlgorithms.optimized_batch_process(data, batch_size=3, processor_func=square)
        self.assertEqual(len(results), 10)
        self.assertEqual(results[0], 0)
        self.assertEqual(results[1], 1)
        self.assertEqual(results[2], 4)

    def test_grouping(self):
        """测试分组"""
        from plookingII.core.optimized_algorithms import OptimizedAlgorithms

        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        groups = OptimizedAlgorithms.group_by_condition(data, lambda x: x % 2 == 0)

        self.assertIn("even", groups)
        self.assertIn("odd", groups)
        self.assertEqual(len(groups["even"]), 5)
        self.assertEqual(len(groups["odd"]), 5)

if __name__ == '__main__':
    unittest.main()
