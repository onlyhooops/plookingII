"""
测试延迟初始化模块

测试覆盖：
- LazyProperty 类
- lazy_init 函数
- ComponentPool 类
- StartupProfiler 类
- profile_startup 装饰器
"""

import threading
import time
from unittest.mock import patch

import pytest

from plookingII.core.lazy_initialization import (
    ComponentPool,
    LazyProperty,
    StartupProfiler,
    component_pool,
    lazy_init,
    profile_startup,
    startup_profiler,
)


class TestLazyProperty:
    """测试LazyProperty类"""

    def test_init(self):
        """测试初始化"""
        factory = lambda: "value"
        prop = LazyProperty(factory, name="test_prop")

        assert prop.factory == factory
        assert prop.name == "test_prop"
        assert not prop._initialized

    def test_init_with_default_name(self):
        """测试默认名称"""

        def my_factory():
            return "value"

        prop = LazyProperty(my_factory)
        assert prop.name == "my_factory"

    def test_get_creates_value_on_first_access(self):
        """测试第一次访问时创建值"""
        call_count = {"count": 0}

        def factory():
            call_count["count"] += 1
            return "created_value"

        prop = LazyProperty(factory)

        # 第一次访问应该调用factory
        result = prop.__get__(None, None)
        assert result == "created_value"
        assert call_count["count"] == 1
        assert prop._initialized

    def test_get_caches_value(self):
        """测试值被缓存"""
        call_count = {"count": 0}

        def factory():
            call_count["count"] += 1
            return "value"

        prop = LazyProperty(factory)

        # 多次访问应该只调用一次factory
        result1 = prop.__get__(None, None)
        result2 = prop.__get__(None, None)
        result3 = prop.__get__(None, None)

        assert result1 == result2 == result3 == "value"
        assert call_count["count"] == 1

    def test_get_handles_factory_exception(self):
        """测试工厂函数抛出异常"""

        def failing_factory():
            raise ValueError("Factory failed")

        prop = LazyProperty(failing_factory, name="failing")

        with pytest.raises(ValueError, match="Factory failed"):
            prop.__get__(None, None)

        assert not prop._initialized

    def test_set_value(self):
        """测试设置值"""
        prop = LazyProperty(lambda: "original")

        # 直接设置值
        prop.__set__(None, "new_value")

        assert prop._initialized
        assert prop.__get__(None, None) == "new_value"

    def test_set_overrides_factory(self):
        """测试设置值覆盖工厂"""
        call_count = {"count": 0}

        def factory():
            call_count["count"] += 1
            return "factory_value"

        prop = LazyProperty(factory)

        # 先设置值
        prop.__set__(None, "manual_value")

        # 获取值应该返回手动设置的值，不调用factory
        result = prop.__get__(None, None)
        assert result == "manual_value"
        assert call_count["count"] == 0

    def test_reset(self):
        """测试重置"""
        call_count = {"count": 0}

        def factory():
            call_count["count"] += 1
            return f"value_{call_count['count']}"

        prop = LazyProperty(factory)

        # 第一次获取
        result1 = prop.__get__(None, None)
        assert result1 == "value_1"

        # 重置
        prop.reset()
        assert not prop._initialized

        # 第二次获取应该重新创建
        result2 = prop.__get__(None, None)
        assert result2 == "value_2"
        assert call_count["count"] == 2

    def test_thread_safety(self):
        """测试线程安全"""
        call_count = {"count": 0}

        def factory():
            time.sleep(0.01)  # 模拟耗时操作
            call_count["count"] += 1
            return "value"

        prop = LazyProperty(factory)
        results = []

        def access_property():
            results.append(prop.__get__(None, None))

        # 多线程同时访问
        threads = [threading.Thread(target=access_property) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 应该只创建一次
        assert call_count["count"] == 1
        assert all(r == "value" for r in results)


class TestLazyInit:
    """测试lazy_init函数"""

    def test_lazy_init_creates_lazy_property(self):
        """测试创建LazyProperty"""

        def factory():
            return "test_value"

        prop = lazy_init(factory)

        assert isinstance(prop, LazyProperty)
        assert prop.factory == factory

    def test_lazy_init_functional(self):
        """测试功能正常"""
        call_count = {"count": 0}

        def factory():
            call_count["count"] += 1
            return "lazy_value"

        prop = lazy_init(factory)

        result = prop.__get__(None, None)
        assert result == "lazy_value"
        assert call_count["count"] == 1


class TestComponentPool:
    """测试ComponentPool类"""

    def test_init(self):
        """测试初始化"""
        pool = ComponentPool(max_size=5)

        assert pool.max_size == 5
        assert len(pool._pool) == 0
        assert len(pool._creation_times) == 0

    def test_default_max_size(self):
        """测试默认最大大小"""
        pool = ComponentPool()
        assert pool.max_size == 10

    def test_get_or_create_creates_on_first_call(self):
        """测试第一次调用时创建"""
        pool = ComponentPool()
        call_count = {"count": 0}

        def factory():
            call_count["count"] += 1
            return f"component_{call_count['count']}"

        result = pool.get_or_create("key1", factory)

        assert result == "component_1"
        assert call_count["count"] == 1
        assert "key1" in pool._pool

    def test_get_or_create_reuses_existing(self):
        """测试复用已存在的组件"""
        pool = ComponentPool()
        call_count = {"count": 0}

        def factory():
            call_count["count"] += 1
            return "component"

        result1 = pool.get_or_create("key1", factory)
        result2 = pool.get_or_create("key1", factory)

        assert result1 == result2
        assert call_count["count"] == 1  # 只创建一次

    def test_get_or_create_different_keys(self):
        """测试不同键创建不同组件"""
        pool = ComponentPool()

        result1 = pool.get_or_create("key1", lambda: "value1")
        result2 = pool.get_or_create("key2", lambda: "value2")

        assert result1 == "value1"
        assert result2 == "value2"
        assert len(pool._pool) == 2

    def test_cleanup_oldest_when_max_size_reached(self):
        """测试达到最大大小时清理最旧组件"""
        pool = ComponentPool(max_size=3)

        # 添加3个组件
        pool.get_or_create("key1", lambda: "value1")
        time.sleep(0.01)
        pool.get_or_create("key2", lambda: "value2")
        time.sleep(0.01)
        pool.get_or_create("key3", lambda: "value3")

        # 添加第4个，应该清理key1
        pool.get_or_create("key4", lambda: "value4")

        assert len(pool._pool) == 3
        assert "key1" not in pool._pool
        assert "key2" in pool._pool
        assert "key3" in pool._pool
        assert "key4" in pool._pool

    def test_factory_exception_handling(self):
        """测试工厂函数异常处理"""
        pool = ComponentPool()

        def failing_factory():
            raise ValueError("Creation failed")

        with pytest.raises(ValueError, match="Creation failed"):
            pool.get_or_create("failing_key", failing_factory)

        # 失败的组件不应该被添加到池中
        assert "failing_key" not in pool._pool

    def test_clear(self):
        """测试清空池"""
        pool = ComponentPool()

        pool.get_or_create("key1", lambda: "value1")
        pool.get_or_create("key2", lambda: "value2")

        assert len(pool._pool) == 2

        pool.clear()

        assert len(pool._pool) == 0
        assert len(pool._creation_times) == 0

    def test_thread_safety(self):
        """测试线程安全"""
        pool = ComponentPool()
        call_counts = {}

        def factory(key):
            def create():
                call_counts[key] = call_counts.get(key, 0) + 1
                time.sleep(0.001)
                return f"value_{key}"

            return create

        def worker(key):
            pool.get_or_create(key, factory(key))

        # 多线程访问同一个键
        threads = [threading.Thread(target=worker, args=("shared_key",)) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 应该只创建一次
        assert call_counts.get("shared_key", 0) == 1


class TestStartupProfiler:
    """测试StartupProfiler类"""

    def test_init(self):
        """测试初始化"""
        profiler = StartupProfiler()

        assert len(profiler._timings) == 0
        assert isinstance(profiler._start_time, float)

    def test_start_timing(self):
        """测试开始计时"""
        profiler = StartupProfiler()

        profiler.start_timing("component1")

        assert "component1_start" in profiler._timings

    def test_end_timing(self):
        """测试结束计时"""
        profiler = StartupProfiler()

        profiler.start_timing("component1")
        time.sleep(0.01)
        profiler.end_timing("component1")

        assert "component1" in profiler._timings
        assert "component1_start" not in profiler._timings
        assert profiler._timings["component1"] >= 0.01

    def test_end_timing_without_start(self):
        """测试未开始就结束"""
        profiler = StartupProfiler()

        # 应该不会崩溃
        profiler.end_timing("non_existent")

        assert "non_existent" not in profiler._timings

    def test_multiple_timings(self):
        """测试多个计时"""
        profiler = StartupProfiler()

        profiler.start_timing("comp1")
        time.sleep(0.01)
        profiler.end_timing("comp1")

        profiler.start_timing("comp2")
        time.sleep(0.02)
        profiler.end_timing("comp2")

        assert "comp1" in profiler._timings
        assert "comp2" in profiler._timings
        assert profiler._timings["comp2"] > profiler._timings["comp1"]

    def test_get_total_time(self):
        """测试获取总时间"""
        profiler = StartupProfiler()

        time.sleep(0.01)
        total_time = profiler.get_total_time()

        assert total_time >= 0.01

    def test_get_report(self):
        """测试获取报告"""
        profiler = StartupProfiler()

        profiler.start_timing("comp1")
        time.sleep(0.01)
        profiler.end_timing("comp1")

        report = profiler.get_report()

        assert "comp1" in report
        assert "total_startup_time" in report
        assert report["total_startup_time"] >= 0.01

    def test_get_report_is_copy(self):
        """测试报告是副本"""
        profiler = StartupProfiler()
        profiler.start_timing("comp1")
        profiler.end_timing("comp1")

        report1 = profiler.get_report()
        report2 = profiler.get_report()

        # 修改报告不应影响原始数据
        report1["modified"] = True
        assert "modified" not in report2

    def test_log_report(self):
        """测试记录报告"""
        profiler = StartupProfiler()

        profiler.start_timing("comp1")
        profiler.end_timing("comp1")

        # 应该不会崩溃
        profiler.log_report()


class TestProfileStartup:
    """测试profile_startup装饰器"""

    def test_decorator_basic(self):
        """测试基本装饰器功能"""
        profiler = StartupProfiler()

        @profile_startup("test_component")
        def test_function():
            time.sleep(0.01)
            return "result"

        # 替换全局profiler
        with patch("plookingII.core.lazy_initialization.startup_profiler", profiler):
            result = test_function()

        assert result == "result"
        # 注意：由于使用的是全局startup_profiler，这里不会记录到我们的profiler
        # 这是装饰器的设计，使用全局实例

    def test_decorator_with_args(self):
        """测试带参数的函数"""

        @profile_startup("func_with_args")
        def add(a, b):
            return a + b

        result = add(2, 3)
        assert result == 5

    def test_decorator_with_exception(self):
        """测试异常处理"""

        @profile_startup("failing_func")
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()

        # 即使异常，也应该记录计时

    def test_decorator_preserves_function_name(self):
        """测试保留函数名"""

        @profile_startup("test")
        def my_function():
            pass

        assert my_function.__name__ == "my_function"


class TestGlobalInstances:
    """测试全局实例"""

    def test_startup_profiler_is_instance(self):
        """测试全局startup_profiler"""
        assert isinstance(startup_profiler, StartupProfiler)

    def test_component_pool_is_instance(self):
        """测试全局component_pool"""
        assert isinstance(component_pool, ComponentPool)


class TestIntegration:
    """集成测试"""

    def test_lazy_property_in_class(self):
        """测试在类中使用LazyProperty"""

        class MyClass:
            def __init__(self):
                self.call_count = 0

            def create_resource(self):
                self.call_count += 1
                return f"resource_{self.call_count}"

        obj = MyClass()
        prop = LazyProperty(obj.create_resource, name="resource")

        # 多次访问
        result1 = prop.__get__(obj, MyClass)
        result2 = prop.__get__(obj, MyClass)

        assert result1 == result2 == "resource_1"
        assert obj.call_count == 1

    def test_component_pool_with_profiler(self):
        """测试组件池与性能分析器结合"""
        pool = ComponentPool(max_size=5)
        profiler = StartupProfiler()

        def create_component(name):
            profiler.start_timing(name)
            time.sleep(0.001)
            component = f"component_{name}"
            profiler.end_timing(name)
            return component

        # 创建多个组件
        pool.get_or_create("comp1", lambda: create_component("comp1"))
        pool.get_or_create("comp2", lambda: create_component("comp2"))

        report = profiler.get_report()
        assert "comp1" in report
        assert "comp2" in report

    def test_real_world_usage_pattern(self):
        """测试真实使用场景"""

        # 模拟应用启动过程
        class Application:
            def __init__(self):
                self.initialized = False

            @profile_startup("app_init")
            def initialize(self):
                time.sleep(0.01)
                self.initialized = True
                return True

        app = Application()
        result = app.initialize()

        assert result is True
        assert app.initialized is True
