"""
测试 core/optimized_algorithms.py

测试优化算法模块功能，包括：
- OptimizedAlgorithms类的各种优化算法
- CircularBuffer循环缓冲区
- PerformanceOptimizer性能优化器
"""

from unittest.mock import MagicMock, Mock, patch
import time

import pytest

from plookingII.core.optimized_algorithms import (
    OptimizedAlgorithms,
    CircularBuffer,
    PerformanceOptimizer,
)


# ==================== OptimizedAlgorithms 批量处理测试 ====================


class TestBatchProcess:
    """测试批量处理算法"""

    def test_batch_process_basic(self):
        """测试基本批量处理"""
        items = list(range(25))
        result = OptimizedAlgorithms.optimized_batch_process(
            items, batch_size=10, processor_func=lambda x: x * 2
        )
        
        assert len(result) == 25
        assert result == [x * 2 for x in range(25)]

    def test_batch_process_empty_list(self):
        """测试空列表"""
        result = OptimizedAlgorithms.optimized_batch_process(
            [], batch_size=10, processor_func=lambda x: x
        )
        
        assert result == []

    def test_batch_process_no_processor(self):
        """测试无处理函数"""
        result = OptimizedAlgorithms.optimized_batch_process(
            [1, 2, 3], batch_size=10, processor_func=None
        )
        
        assert result == []

    def test_batch_process_small_batch(self):
        """测试小批量"""
        items = list(range(10))
        result = OptimizedAlgorithms.optimized_batch_process(
            items, batch_size=3, processor_func=lambda x: x + 1
        )
        
        assert result == [x + 1 for x in range(10)]


# ==================== OptimizedAlgorithms 分组测试 ====================


class TestGroupBy:
    """测试分组算法"""

    def test_group_by_condition_even_odd(self):
        """测试偶数奇数分组"""
        items = [1, 2, 3, 4, 5, 6]
        result = OptimizedAlgorithms.group_by_condition(
            items, predicate=lambda x: x % 2 == 0
        )
        
        assert result["even"] == [2, 4, 6]
        assert result["odd"] == [1, 3, 5]

    def test_group_by_empty(self):
        """测试空列表分组"""
        result = OptimizedAlgorithms.group_by_condition([], lambda x: x > 0)
        
        assert result == {"even": [], "odd": []}

    def test_optimized_group_by_basic(self):
        """测试优化分组"""
        items = ["apple", "banana", "apricot", "blueberry"]
        result = OptimizedAlgorithms.optimized_group_by(
            items, key_func=lambda x: x[0]
        )
        
        assert result["a"] == ["apple", "apricot"]
        assert result["b"] == ["banana", "blueberry"]

    def test_optimized_group_by_empty(self):
        """测试空列表优化分组"""
        result = OptimizedAlgorithms.optimized_group_by([], key_func=lambda x: x)
        
        assert result == {}

    def test_optimized_group_by_no_key_func(self):
        """测试无键函数"""
        result = OptimizedAlgorithms.optimized_group_by([1, 2, 3], key_func=None)
        
        assert result == {}


# ==================== OptimizedAlgorithms 最佳匹配测试 ====================


class TestBestMatch:
    """测试最佳匹配算法"""

    def test_find_best_match_basic(self):
        """测试基本最佳匹配"""
        target = 10
        candidates = [5, 8, 12, 15]
        
        def similarity(t, c):
            return -abs(t - c)
        
        result = OptimizedAlgorithms.optimized_find_best_match(
            target, candidates, similarity_func=similarity
        )
        
        assert result == 8  # 最接近10

    def test_find_best_match_empty(self):
        """测试空候选列表"""
        result = OptimizedAlgorithms.optimized_find_best_match(
            10, [], similarity_func=lambda t, c: -abs(t - c)
        )
        
        assert result is None

    def test_find_best_match_no_similarity(self):
        """测试无相似度函数"""
        result = OptimizedAlgorithms.optimized_find_best_match(
            10, [1, 2, 3], similarity_func=None
        )
        
        assert result is None


# ==================== OptimizedAlgorithms 优先级队列测试 ====================


class TestPriorityQueue:
    """测试优先级队列算法"""

    def test_priority_queue_basic(self):
        """测试基本优先级队列"""
        items = [3, 1, 4, 1, 5, 9, 2, 6]
        result = OptimizedAlgorithms.optimized_priority_queue(
            items, priority_func=lambda x: x
        )
        
        assert result == sorted(items, reverse=True)

    def test_priority_queue_with_max_size(self):
        """测试带最大大小的优先级队列"""
        items = [3, 1, 4, 1, 5, 9, 2, 6]
        result = OptimizedAlgorithms.optimized_priority_queue(
            items, priority_func=lambda x: x, max_size=3
        )
        
        assert len(result) == 3
        assert result == [9, 6, 5]

    def test_priority_queue_empty(self):
        """测试空列表"""
        result = OptimizedAlgorithms.optimized_priority_queue(
            [], priority_func=lambda x: x
        )
        
        assert result == []

    def test_priority_queue_no_priority_func(self):
        """测试无优先级函数"""
        result = OptimizedAlgorithms.optimized_priority_queue(
            [1, 2, 3], priority_func=None
        )
        
        assert result == []


# ==================== OptimizedAlgorithms 滑动窗口测试 ====================


class TestSlidingWindow:
    """测试滑动窗口算法"""

    def test_sliding_window_basic(self):
        """测试基本滑动窗口"""
        items = [1, 2, 3, 4, 5]
        result = list(OptimizedAlgorithms.optimized_window_sliding(items, 3))
        
        assert result == [[1, 2, 3], [2, 3, 4], [3, 4, 5]]

    def test_sliding_window_size_one(self):
        """测试窗口大小为1"""
        items = [1, 2, 3]
        result = list(OptimizedAlgorithms.optimized_window_sliding(items, 1))
        
        assert result == [[1], [2], [3]]

    def test_sliding_window_empty(self):
        """测试空列表"""
        result = list(OptimizedAlgorithms.optimized_window_sliding([], 3))
        
        assert result == []

    def test_sliding_window_zero_size(self):
        """测试窗口大小为0"""
        result = list(OptimizedAlgorithms.optimized_window_sliding([1, 2, 3], 0))
        
        assert result == []

    def test_sliding_window_larger_than_list(self):
        """测试窗口大小大于列表"""
        items = [1, 2]
        result = list(OptimizedAlgorithms.optimized_window_sliding(items, 5))
        
        # 窗口大小大于列表，不会产生完整窗口
        assert result == []


# ==================== OptimizedAlgorithms 内存高效迭代器测试 ====================


class TestMemoryEfficientIter:
    """测试内存高效迭代器"""

    def test_memory_efficient_iter_with_processor(self):
        """测试带处理函数的迭代器"""
        items = [1, 2, 3, 4, 5]
        result = list(OptimizedAlgorithms.optimized_memory_efficient_iter(
            items, processor_func=lambda x: x ** 2
        ))
        
        assert result == [1, 4, 9, 16, 25]

    def test_memory_efficient_iter_no_processor(self):
        """测试无处理函数的迭代器"""
        items = [1, 2, 3]
        result = list(OptimizedAlgorithms.optimized_memory_efficient_iter(
            items, processor_func=None
        ))
        
        assert result == items

    def test_memory_efficient_iter_empty(self):
        """测试空列表"""
        result = list(OptimizedAlgorithms.optimized_memory_efficient_iter(
            [], processor_func=lambda x: x
        ))
        
        assert result == []


# ==================== OptimizedAlgorithms 条件过滤测试 ====================


class TestConditionalFilter:
    """测试条件过滤算法"""

    def test_conditional_filter_basic(self):
        """测试基本条件过滤"""
        items = [1, 2, 3, 4, 5, 6]
        result = OptimizedAlgorithms.optimized_conditional_filter(
            items, condition_func=lambda x: x % 2 == 0
        )
        
        assert result == [2, 4, 6]

    def test_conditional_filter_no_condition(self):
        """测试无条件函数"""
        items = [1, 2, 3]
        result = OptimizedAlgorithms.optimized_conditional_filter(
            items, condition_func=None
        )
        
        assert result == items

    def test_conditional_filter_empty(self):
        """测试空列表"""
        result = OptimizedAlgorithms.optimized_conditional_filter(
            [], condition_func=lambda x: x > 0
        )
        
        assert result == []


# ==================== OptimizedAlgorithms 去重测试 ====================


class TestDuplicateRemoval:
    """测试去重算法"""

    def test_duplicate_removal_simple(self):
        """测试简单去重"""
        items = [1, 2, 2, 3, 1, 4, 3, 5]
        result = OptimizedAlgorithms.optimized_duplicate_removal(items)
        
        assert result == [1, 2, 3, 4, 5]

    def test_duplicate_removal_with_key(self):
        """测试基于键的去重"""
        items = [("a", 1), ("b", 2), ("a", 3), ("c", 4)]
        result = OptimizedAlgorithms.optimized_duplicate_removal(
            items, key_func=lambda x: x[0]
        )
        
        assert len(result) == 3
        assert result[0][0] == "a"
        assert result[1][0] == "b"
        assert result[2][0] == "c"

    def test_duplicate_removal_empty(self):
        """测试空列表"""
        result = OptimizedAlgorithms.optimized_duplicate_removal([])
        
        assert result == []


# ==================== OptimizedAlgorithms 合并有序列表测试 ====================


class TestMergeSortedLists:
    """测试有序列表合并"""

    def test_merge_sorted_lists_basic(self):
        """测试基本合并"""
        lists = [[1, 3, 5], [2, 4, 6], [0, 7, 8]]
        result = OptimizedAlgorithms.optimized_merge_sorted_lists(lists)
        
        assert result == [0, 1, 2, 3, 4, 5, 6, 7, 8]

    def test_merge_sorted_lists_with_key(self):
        """测试带键函数的合并"""
        lists = [[(1, 'a'), (3, 'c')], [(2, 'b'), (4, 'd')]]
        result = OptimizedAlgorithms.optimized_merge_sorted_lists(
            lists, key_func=lambda x: x[0]
        )
        
        assert len(result) == 4
        assert result[0][0] == 1

    def test_merge_sorted_lists_empty(self):
        """测试空列表"""
        result = OptimizedAlgorithms.optimized_merge_sorted_lists([])
        
        assert result == []

    def test_merge_sorted_lists_single(self):
        """测试单个列表"""
        lists = [[1, 2, 3]]
        result = OptimizedAlgorithms.optimized_merge_sorted_lists(lists)
        
        assert result == [1, 2, 3]

    def test_merge_sorted_lists_with_empty(self):
        """测试包含空列表"""
        lists = [[1, 3], [], [2, 4], []]
        result = OptimizedAlgorithms.optimized_merge_sorted_lists(lists)
        
        assert result == [1, 2, 3, 4]


# ==================== CircularBuffer 测试 ====================


class TestCircularBuffer:
    """测试循环缓冲区"""

    def test_circular_buffer_init(self):
        """测试初始化"""
        buffer = CircularBuffer(5)
        
        assert buffer.max_size == 5
        assert len(buffer) == 0

    def test_circular_buffer_append(self):
        """测试添加项"""
        buffer = CircularBuffer(3)
        
        buffer.append(1)
        buffer.append(2)
        
        assert len(buffer) == 2
        assert buffer.get_all() == [1, 2]

    def test_circular_buffer_overflow(self):
        """测试溢出"""
        buffer = CircularBuffer(3)
        
        buffer.append(1)
        buffer.append(2)
        buffer.append(3)
        buffer.append(4)  # 溢出，移除1
        
        assert len(buffer) == 3
        assert buffer.get_all() == [2, 3, 4]

    def test_circular_buffer_get_latest(self):
        """测试获取最新N项"""
        buffer = CircularBuffer(5)
        
        for i in range(5):
            buffer.append(i)
        
        assert buffer.get_latest(3) == [2, 3, 4]

    def test_circular_buffer_get_latest_zero(self):
        """测试获取0项"""
        buffer = CircularBuffer(5)
        buffer.append(1)
        
        assert buffer.get_latest(0) == []

    def test_circular_buffer_clear(self):
        """测试清空"""
        buffer = CircularBuffer(5)
        buffer.append(1)
        buffer.append(2)
        
        buffer.clear()
        
        assert len(buffer) == 0
        assert buffer.get_all() == []

    def test_circular_buffer_is_full(self):
        """测试是否已满"""
        buffer = CircularBuffer(3)
        
        assert buffer.is_full() is False
        
        buffer.append(1)
        buffer.append(2)
        buffer.append(3)
        
        assert buffer.is_full() is True

    def test_optimized_circular_buffer_factory(self):
        """测试工厂方法"""
        buffer = OptimizedAlgorithms.optimized_circular_buffer(10)
        
        assert isinstance(buffer, CircularBuffer)
        assert buffer.max_size == 10


# ==================== PerformanceOptimizer 测试 ====================


class TestPerformanceOptimizer:
    """测试性能优化器"""

    def test_measure_execution_time(self):
        """测试执行时间测量"""
        def test_func():
            time.sleep(0.1)
            return "result"
        
        result, execution_time = PerformanceOptimizer.measure_execution_time(test_func)
        
        assert result == "result"
        assert execution_time >= 0.1

    def test_measure_execution_time_with_args(self):
        """测试带参数的执行时间测量"""
        def test_func(a, b):
            return a + b
        
        result, execution_time = PerformanceOptimizer.measure_execution_time(
            test_func, 5, 3
        )
        
        assert result == 8
        assert execution_time >= 0

    def test_optimize_loop_structure(self):
        """测试循环结构优化"""
        items = [1, 2, 3, 4, 5]
        result = PerformanceOptimizer.optimize_loop_structure(
            items, processor_func=lambda x: x * 2
        )
        
        assert result == [2, 4, 6, 8, 10]

    def test_optimize_loop_structure_empty(self):
        """测试空列表"""
        result = PerformanceOptimizer.optimize_loop_structure(
            [], processor_func=lambda x: x
        )
        
        assert result == []

    def test_optimize_loop_structure_no_processor(self):
        """测试无处理函数"""
        result = PerformanceOptimizer.optimize_loop_structure(
            [1, 2, 3], processor_func=None
        )
        
        assert result == []

    def test_cache_function_results(self):
        """测试函数结果缓存"""
        call_count = {"count": 0}
        
        def expensive_func(x):
            call_count["count"] += 1
            return x ** 2
        
        cached_func = PerformanceOptimizer.cache_function_results(expensive_func)
        
        # 首次调用
        result1 = cached_func(5)
        assert result1 == 25
        assert call_count["count"] == 1
        
        # 第二次调用相同参数，应该使用缓存
        result2 = cached_func(5)
        assert result2 == 25
        assert call_count["count"] == 1  # 没有增加

    def test_cache_function_results_max_size(self):
        """测试缓存大小限制"""
        def test_func(x):
            return x
        
        cached_func = PerformanceOptimizer.cache_function_results(
            test_func, max_cache_size=2
        )
        
        # 添加3个不同的调用
        cached_func(1)
        cached_func(2)
        cached_func(3)
        
        # 缓存应该只保留最后2个
        # （这个测试主要验证不会崩溃）
        result = cached_func(2)
        assert result == 2


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    def test_complete_workflow(self):
        """测试完整工作流"""
        # 批量处理
        items = list(range(20))
        processed = OptimizedAlgorithms.optimized_batch_process(
            items, batch_size=5, processor_func=lambda x: x * 2
        )
        
        # 过滤
        filtered = OptimizedAlgorithms.optimized_conditional_filter(
            processed, condition_func=lambda x: x > 10
        )
        
        # 去重
        unique = OptimizedAlgorithms.optimized_duplicate_removal(filtered)
        
        assert len(unique) > 0
        assert all(x > 10 for x in unique)

    def test_circular_buffer_with_optimization(self):
        """测试循环缓冲区与优化算法结合"""
        buffer = OptimizedAlgorithms.optimized_circular_buffer(10)
        
        items = list(range(15))
        for item in items:
            buffer.append(item)
        
        # 应该只保留最后10个
        assert len(buffer) == 10
        assert buffer.get_all() == list(range(5, 15))

