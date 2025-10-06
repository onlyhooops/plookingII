#!/usr/bin/env python3
"""
测试 core/base_classes.py

Author: PlookingII Team
"""

import logging
import time

import pytest

from plookingII.core.base_classes import (
    BaseComponent,
    ComponentConfig,
    ComponentRegistry,
    ConfigurationMixin,
    ErrorHandlingMixin,
    LoggingMixin,
    StatisticsMixin,
    component_registry,
)


class TestComponentConfig:
    """测试 ComponentConfig 数据类"""

    def test_default_values(self):
        """测试默认值"""
        config = ComponentConfig(name="test")
        assert config.name == "test"
        assert config.enabled is True
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.custom_params == {}

    def test_custom_values(self):
        """测试自定义值"""
        config = ComponentConfig(
            name="custom", enabled=False, timeout=60.0, max_retries=5, custom_params={"key": "value"}
        )
        assert config.name == "custom"
        assert config.enabled is False
        assert config.timeout == 60.0
        assert config.max_retries == 5
        assert config.custom_params == {"key": "value"}


class TestStatisticsMixin:
    """测试 StatisticsMixin"""

    class MockComponent(StatisticsMixin):
        def __init__(self):
            super().__init__()

    def test_initialization(self):
        """测试初始化"""
        component = self.MockComponent()
        stats = component.get_stats()
        assert stats["operations"] == 0
        assert stats["successes"] == 0
        assert stats["failures"] == 0

    def test_record_successful_operation(self):
        """测试记录成功操作"""
        component = self.MockComponent()
        component._record_operation(True, 1.0)

        stats = component.get_stats()
        assert stats["operations"] == 1
        assert stats["successes"] == 1
        assert stats["failures"] == 0
        assert stats["last_operation_time"] == 1.0

    def test_record_failed_operation(self):
        """测试记录失败操作"""
        component = self.MockComponent()
        component._record_operation(False, 2.0)

        stats = component.get_stats()
        assert stats["operations"] == 1
        assert stats["successes"] == 0
        assert stats["failures"] == 1

    def test_average_time_calculation(self):
        """测试平均时间计算"""
        component = self.MockComponent()
        component._record_operation(True, 1.0)
        component._record_operation(True, 3.0)

        stats = component.get_stats()
        assert stats["avg_time"] == 2.0

    def test_update_stats_alias(self):
        """测试update_stats别名方法"""
        component = self.MockComponent()
        component.update_stats(True, 1.5)

        stats = component.get_stats()
        assert stats["operations"] == 1
        assert stats["last_operation_time"] == 1.5

    def test_reset_stats(self):
        """测试重置统计"""
        component = self.MockComponent()
        component._record_operation(True, 1.0)
        component.reset_stats()

        stats = component.get_stats()
        assert stats["operations"] == 0
        assert stats["successes"] == 0
        assert stats["failures"] == 0

    def test_success_rate_calculation(self):
        """测试成功率计算"""
        component = self.MockComponent()
        component._record_operation(True, 1.0)
        component._record_operation(True, 1.0)
        component._record_operation(False, 1.0)

        stats = component.get_stats()
        assert stats["success_rate"] == pytest.approx(66.67, rel=0.01)


class TestConfigurationMixin:
    """测试 ConfigurationMixin"""

    class MockComponent(ConfigurationMixin):
        def __init__(self):
            super().__init__()

    def test_initialization(self):
        """测试初始化"""
        component = self.MockComponent()
        config = component.get_config()
        assert isinstance(config, ComponentConfig)
        assert config.name == "MockComponent"

    def test_update_config_builtin_field(self):
        """测试更新内置配置字段"""
        component = self.MockComponent()
        component.update_config(enabled=False, timeout=60.0)

        config = component.get_config()
        assert config.enabled is False
        assert config.timeout == 60.0

    def test_update_config_custom_field(self):
        """测试更新自定义字段"""
        component = self.MockComponent()
        component.update_config(custom_field="value")

        config = component.get_config()
        assert config.custom_params["custom_field"] == "value"

    def test_is_enabled(self):
        """测试is_enabled方法"""
        component = self.MockComponent()
        assert component.is_enabled() is True

        component.update_config(enabled=False)
        assert component.is_enabled() is False


class TestErrorHandlingMixin:
    """测试 ErrorHandlingMixin"""

    class MockComponent(ErrorHandlingMixin, LoggingMixin):
        def __init__(self):
            LoggingMixin.__init__(self)
            ErrorHandlingMixin.__init__(self)

    def test_initialization(self):
        """测试初始化"""
        component = self.MockComponent()
        assert hasattr(component, "_error_handlers")
        assert hasattr(component, "error_handler")

    def test_register_error_handler(self):
        """测试注册错误处理器"""
        component = self.MockComponent()

        def custom_handler(error, context):
            return "handled"

        component.register_error_handler(ValueError, custom_handler)
        assert ValueError in component._error_handlers

    def test_handle_error_with_registered_handler(self):
        """测试使用已注册的错误处理器"""
        component = self.MockComponent()

        handled_errors = []

        def custom_handler(error, context):
            handled_errors.append((error, context))
            return "handled"

        component.register_error_handler(ValueError, custom_handler)
        result = component.handle_error(ValueError("test"), "test_context")

        assert result == "handled"
        assert len(handled_errors) == 1

    def test_retry_operation_success(self):
        """测试重试操作成功"""
        component = self.MockComponent()

        def operation():
            return "success"

        result = component.retry_operation(operation)
        assert result == "success"

    def test_retry_operation_eventual_success(self):
        """测试重试操作最终成功"""
        component = self.MockComponent()
        component._retry_config["delay"] = 0.01  # 减少测试时间

        attempts = [0]

        def operation():
            attempts[0] += 1
            if attempts[0] < 3:
                raise ValueError("not yet")
            return "success"

        result = component.retry_operation(operation)
        assert result == "success"
        assert attempts[0] == 3


class TestLoggingMixin:
    """测试 LoggingMixin"""

    class MockComponent(LoggingMixin):
        def __init__(self):
            super().__init__()

    def test_logger_initialization(self):
        """测试日志器初始化"""
        component = self.MockComponent()
        assert hasattr(component, "logger")
        assert isinstance(component.logger, logging.Logger)

    def test_log_operation(self):
        """测试记录操作日志"""
        component = self.MockComponent()
        # 应该不抛出异常
        component.log_operation("test_operation", level=logging.INFO)
        component.log_operation("test_operation", key1="value1", key2="value2")


class TestBaseComponent:
    """测试 BaseComponent"""

    class TestComponent(BaseComponent):
        """测试用组件"""

        def initialize(self) -> bool:
            return True

        def cleanup(self):
            pass

    def test_initialization(self):
        """测试初始化"""
        component = self.TestComponent(name="test")
        assert component.get_config().name == "test"
        assert hasattr(component, "logger")
        assert hasattr(component, "_stats")

    def test_initialization_with_config(self):
        """测试使用配置初始化"""
        config = ComponentConfig(name="custom", timeout=60.0)
        component = self.TestComponent(config=config)
        assert component.get_config().name == "custom"
        assert component.get_config().timeout == 60.0

    def test_is_healthy_no_operations(self):
        """测试无操作时的健康检查"""
        component = self.TestComponent()
        assert component.is_healthy() is True

    def test_is_healthy_mostly_successful(self):
        """测试大多数成功时的健康检查"""
        component = self.TestComponent()
        component._record_operation(True, 1.0)
        component._record_operation(True, 1.0)
        component._record_operation(False, 1.0)
        assert component.is_healthy() is True

    def test_is_healthy_mostly_failed(self):
        """测试大多数失败时的健康检查"""
        component = self.TestComponent()
        component._record_operation(False, 1.0)
        component._record_operation(False, 1.0)
        component._record_operation(True, 1.0)
        assert component.is_healthy() is False

    def test_is_healthy_when_disabled(self):
        """测试禁用时的健康检查"""
        component = self.TestComponent()
        component.update_config(enabled=False)
        assert component.is_healthy() is False

    def test_operation_context_success(self):
        """测试操作上下文成功"""
        component = self.TestComponent()

        with component.operation_context("test_op"):
            time.sleep(0.01)

        stats = component.get_stats()
        assert stats["operations"] == 1
        assert stats["successes"] == 1

    def test_operation_context_failure(self):
        """测试操作上下文失败"""
        component = self.TestComponent()

        with pytest.raises(ValueError), component.operation_context("test_op"):
            raise ValueError("test error")

        stats = component.get_stats()
        assert stats["operations"] == 1
        assert stats["failures"] == 1


class TestComponentRegistry:
    """测试 ComponentRegistry"""

    class TestComponent(BaseComponent):
        def initialize(self) -> bool:
            return True

        def cleanup(self):
            self.cleaned = True

    def test_register_component(self):
        """测试注册组件"""
        registry = ComponentRegistry()
        component = self.TestComponent(name="test1")

        registry.register(component, "test1")
        assert registry.get("test1") == component

    def test_register_component_default_name(self):
        """测试使用默认名称注册组件"""
        registry = ComponentRegistry()
        component = self.TestComponent(name="test2")

        registry.register(component)
        assert registry.get("TestComponent") is not None

    def test_get_nonexistent_component(self):
        """测试获取不存在的组件"""
        registry = ComponentRegistry()
        assert registry.get("nonexistent") is None

    def test_unregister_component(self):
        """测试注销组件"""
        registry = ComponentRegistry()
        component = self.TestComponent(name="test3")
        component.cleaned = False

        registry.register(component, "test3")
        registry.unregister("test3")

        assert registry.get("test3") is None
        assert component.cleaned is True

    def test_get_all_components(self):
        """测试获取所有组件"""
        registry = ComponentRegistry()
        comp1 = self.TestComponent(name="comp1")
        comp2 = self.TestComponent(name="comp2")

        registry.register(comp1, "comp1")
        registry.register(comp2, "comp2")

        all_components = registry.get_all()
        assert len(all_components) == 2
        assert "comp1" in all_components
        assert "comp2" in all_components

    def test_cleanup_all(self):
        """测试清理所有组件"""
        registry = ComponentRegistry()
        comp1 = self.TestComponent(name="comp1")
        comp2 = self.TestComponent(name="comp2")
        comp1.cleaned = False
        comp2.cleaned = False

        registry.register(comp1, "comp1")
        registry.register(comp2, "comp2")

        registry.cleanup_all()

        assert len(registry.get_all()) == 0
        assert comp1.cleaned is True
        assert comp2.cleaned is True


class TestGlobalComponentRegistry:
    """测试全局组件注册表"""

    def test_global_registry_exists(self):
        """测试全局注册表存在"""
        assert component_registry is not None
        assert isinstance(component_registry, ComponentRegistry)
