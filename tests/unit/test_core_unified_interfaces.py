"""
测试 core/unified_interfaces.py

测试统一接口模块功能，包括：
- 抽象接口定义
- UnifiedCacheManager
- UnifiedStatusManager
- 全局单例函数
"""

from unittest.mock import MagicMock, Mock, patch
import time

import pytest

from plookingII.core.unified_interfaces import (
    CacheInterface,
    StatusInterface,
    ConfigInterface,
    MonitorInterface,
    UnifiedCacheManager,
    UnifiedStatusManager,
    get_unified_cache_manager,
    get_unified_status_manager,
    clear_all_caches,
    set_global_status,
)


# ==================== 抽象接口测试 ====================


class TestAbstractInterfaces:
    """测试抽象接口定义"""

    def test_cache_interface_is_abstract(self):
        """测试CacheInterface是抽象类"""
        with pytest.raises(TypeError):
            CacheInterface()

    def test_status_interface_is_abstract(self):
        """测试StatusInterface是抽象类"""
        with pytest.raises(TypeError):
            StatusInterface()

    def test_config_interface_is_abstract(self):
        """测试ConfigInterface是抽象类"""
        with pytest.raises(TypeError):
            ConfigInterface()

    def test_monitor_interface_is_abstract(self):
        """测试MonitorInterface是抽象类"""
        with pytest.raises(TypeError):
            MonitorInterface()


# ==================== Mock实现类 ====================


class MockCacheProvider(CacheInterface):
    """Mock缓存提供者"""

    def __init__(self):
        self.cleared = False
        self.stats = {"items": 0}

    def clear_cache(self, cache_type: str | None = None) -> bool:
        self.cleared = True
        return True

    def get_cache_stats(self):
        return self.stats


class MockStatusProvider(StatusInterface):
    """Mock状态提供者"""

    def __init__(self):
        self.message = ""
        self.timeout = None
        self.status = {}

    def set_status_message(self, message: str, timeout: float | None = None) -> None:
        self.message = message
        self.timeout = timeout

    def update_status_display(self, **kwargs) -> None:
        self.status.update(kwargs)

    def get_current_status(self):
        return {"message": self.message, "status": self.status}


# ==================== UnifiedCacheManager测试 ====================


class TestUnifiedCacheManager:
    """测试UnifiedCacheManager"""

    def test_init(self):
        """测试初始化"""
        manager = UnifiedCacheManager()
        
        assert manager._cache_providers == {}
        assert manager._stats["total_clears"] == 0
        assert manager._stats["last_clear_time"] is None
        assert manager._stats["cache_types"] == []

    def test_register_cache_provider(self):
        """测试注册缓存提供者"""
        manager = UnifiedCacheManager()
        provider = MockCacheProvider()
        
        manager.register_cache_provider("test", provider)
        
        assert "test" in manager._cache_providers
        assert manager._cache_providers["test"] == provider
        assert "test" in manager._stats["cache_types"]

    def test_register_multiple_providers(self):
        """测试注册多个提供者"""
        manager = UnifiedCacheManager()
        provider1 = MockCacheProvider()
        provider2 = MockCacheProvider()
        
        manager.register_cache_provider("cache1", provider1)
        manager.register_cache_provider("cache2", provider2)
        
        assert len(manager._cache_providers) == 2
        assert len(manager._stats["cache_types"]) == 2

    def test_clear_cache_all(self):
        """测试清理所有缓存"""
        manager = UnifiedCacheManager()
        provider1 = MockCacheProvider()
        provider2 = MockCacheProvider()
        
        manager.register_cache_provider("cache1", provider1)
        manager.register_cache_provider("cache2", provider2)
        
        result = manager.clear_cache()
        
        assert result is True
        assert provider1.cleared is True
        assert provider2.cleared is True
        assert manager._stats["total_clears"] == 2

    def test_clear_cache_specific_type(self):
        """测试清理特定类型的缓存"""
        manager = UnifiedCacheManager()
        provider1 = MockCacheProvider()
        provider2 = MockCacheProvider()
        
        manager.register_cache_provider("cache1", provider1)
        manager.register_cache_provider("cache2", provider2)
        
        result = manager.clear_cache("cache1")
        
        assert result is True
        assert provider1.cleared is True
        assert provider2.cleared is False
        assert manager._stats["total_clears"] == 1

    def test_clear_cache_nonexistent_type(self):
        """测试清理不存在的缓存类型"""
        manager = UnifiedCacheManager()
        provider = MockCacheProvider()
        
        manager.register_cache_provider("cache1", provider)
        
        result = manager.clear_cache("nonexistent")
        
        assert result is False
        assert provider.cleared is False

    def test_clear_cache_updates_timestamp(self):
        """测试清理缓存更新时间戳"""
        manager = UnifiedCacheManager()
        provider = MockCacheProvider()
        
        manager.register_cache_provider("test", provider)
        
        before_time = time.time()
        manager.clear_cache()
        after_time = time.time()
        
        assert manager._stats["last_clear_time"] is not None
        assert before_time <= manager._stats["last_clear_time"] <= after_time

    def test_clear_cache_provider_exception(self):
        """测试清理缓存时提供者异常"""
        manager = UnifiedCacheManager()
        
        failing_provider = MockCacheProvider()
        failing_provider.clear_cache = Mock(side_effect=Exception("Clear failed"))
        
        working_provider = MockCacheProvider()
        
        manager.register_cache_provider("failing", failing_provider)
        manager.register_cache_provider("working", working_provider)
        
        with patch('plookingII.core.unified_interfaces.logger'):
            result = manager.clear_cache()
        
        # 一个成功，一个失败，所以返回False
        assert result is False
        assert working_provider.cleared is True

    def test_get_cache_stats_basic(self):
        """测试获取缓存统计"""
        manager = UnifiedCacheManager()
        provider = MockCacheProvider()
        provider.stats = {"items": 10, "size": 1024}
        
        manager.register_cache_provider("test", provider)
        
        stats = manager.get_cache_stats()
        
        assert "total_clears" in stats
        assert "cache_types" in stats
        assert "providers" in stats
        assert "test" in stats["providers"]
        assert stats["providers"]["test"]["items"] == 10

    def test_get_cache_stats_provider_exception(self):
        """测试获取统计时提供者异常"""
        manager = UnifiedCacheManager()
        
        failing_provider = MockCacheProvider()
        failing_provider.get_cache_stats = Mock(side_effect=Exception("Stats failed"))
        
        manager.register_cache_provider("failing", failing_provider)
        
        stats = manager.get_cache_stats()
        
        assert "providers" in stats
        assert "failing" in stats["providers"]
        assert "error" in stats["providers"]["failing"]

    def test_clear_cache_exception_handling(self):
        """测试清理缓存的异常处理"""
        manager = UnifiedCacheManager()
        
        # 模拟内部异常
        with patch.object(manager, '_cache_providers', new_callable=lambda: {}):
            with patch('plookingII.core.unified_interfaces.logger'):
                # 强制触发异常
                manager._cache_providers = Mock(side_effect=Exception("Internal error"))
                result = manager.clear_cache()
                
                assert result is False


# ==================== UnifiedStatusManager测试 ====================


class TestUnifiedStatusManager:
    """测试UnifiedStatusManager"""

    def test_init(self):
        """测试初始化"""
        manager = UnifiedStatusManager()
        
        assert manager._status_providers == {}
        assert manager._current_message == ""
        assert manager._current_status == {}

    def test_register_status_provider(self):
        """测试注册状态提供者"""
        manager = UnifiedStatusManager()
        provider = MockStatusProvider()
        
        manager.register_status_provider("test", provider)
        
        assert "test" in manager._status_providers
        assert manager._status_providers["test"] == provider

    def test_register_multiple_providers(self):
        """测试注册多个提供者"""
        manager = UnifiedStatusManager()
        provider1 = MockStatusProvider()
        provider2 = MockStatusProvider()
        
        manager.register_status_provider("status1", provider1)
        manager.register_status_provider("status2", provider2)
        
        assert len(manager._status_providers) == 2

    def test_set_status_message_basic(self):
        """测试设置状态消息"""
        manager = UnifiedStatusManager()
        provider = MockStatusProvider()
        
        manager.register_status_provider("test", provider)
        
        manager.set_status_message("Test message", 5.0)
        
        assert manager._current_message == "Test message"
        assert provider.message == "Test message"
        assert provider.timeout == 5.0

    def test_set_status_message_broadcast(self):
        """测试消息广播到多个提供者"""
        manager = UnifiedStatusManager()
        provider1 = MockStatusProvider()
        provider2 = MockStatusProvider()
        
        manager.register_status_provider("status1", provider1)
        manager.register_status_provider("status2", provider2)
        
        manager.set_status_message("Broadcast message")
        
        assert provider1.message == "Broadcast message"
        assert provider2.message == "Broadcast message"

    def test_set_status_message_provider_exception(self):
        """测试设置消息时提供者异常"""
        manager = UnifiedStatusManager()
        
        failing_provider = MockStatusProvider()
        failing_provider.set_status_message = Mock(side_effect=Exception("Set failed"))
        
        working_provider = MockStatusProvider()
        
        manager.register_status_provider("failing", failing_provider)
        manager.register_status_provider("working", working_provider)
        
        with patch('plookingII.core.unified_interfaces.logger'):
            manager.set_status_message("Test")
        
        assert manager._current_message == "Test"
        assert working_provider.message == "Test"

    def test_update_status_display_basic(self):
        """测试更新状态显示"""
        manager = UnifiedStatusManager()
        provider = MockStatusProvider()
        
        manager.register_status_provider("test", provider)
        
        manager.update_status_display(progress=50, total=100)
        
        assert manager._current_status["progress"] == 50
        assert manager._current_status["total"] == 100
        assert provider.status["progress"] == 50

    def test_update_status_display_broadcast(self):
        """测试状态更新广播"""
        manager = UnifiedStatusManager()
        provider1 = MockStatusProvider()
        provider2 = MockStatusProvider()
        
        manager.register_status_provider("status1", provider1)
        manager.register_status_provider("status2", provider2)
        
        manager.update_status_display(value=42)
        
        assert provider1.status["value"] == 42
        assert provider2.status["value"] == 42

    def test_update_status_display_provider_exception(self):
        """测试更新显示时提供者异常"""
        manager = UnifiedStatusManager()
        
        failing_provider = MockStatusProvider()
        failing_provider.update_status_display = Mock(side_effect=Exception("Update failed"))
        
        working_provider = MockStatusProvider()
        
        manager.register_status_provider("failing", failing_provider)
        manager.register_status_provider("working", working_provider)
        
        with patch('plookingII.core.unified_interfaces.logger'):
            manager.update_status_display(test=123)
        
        assert manager._current_status["test"] == 123
        assert working_provider.status["test"] == 123

    def test_get_current_status(self):
        """测试获取当前状态"""
        manager = UnifiedStatusManager()
        provider = MockStatusProvider()
        
        manager.register_status_provider("test", provider)
        manager.set_status_message("Status message")
        manager.update_status_display(key="value")
        
        status = manager.get_current_status()
        
        assert status["message"] == "Status message"
        assert status["status"]["key"] == "value"
        assert "test" in status["providers"]

    def test_set_status_message_exception_handling(self):
        """测试设置消息的异常处理"""
        manager = UnifiedStatusManager()
        
        # 模拟内部异常
        with patch.object(manager, '_status_providers', new_callable=lambda: {}):
            with patch('plookingII.core.unified_interfaces.logger'):
                manager._status_providers = Mock(side_effect=Exception("Internal error"))
                # 应该不抛出异常
                try:
                    manager.set_status_message("Test")
                except Exception:
                    pytest.fail("set_status_message应该捕获异常")

    def test_update_status_display_exception_handling(self):
        """测试更新显示的异常处理"""
        manager = UnifiedStatusManager()
        
        # 模拟内部异常
        with patch.object(manager, '_status_providers', new_callable=lambda: {}):
            with patch('plookingII.core.unified_interfaces.logger'):
                manager._status_providers = Mock(side_effect=Exception("Internal error"))
                # 应该不抛出异常
                try:
                    manager.update_status_display(test=1)
                except Exception:
                    pytest.fail("update_status_display应该捕获异常")


# ==================== 全局单例测试 ====================


class TestGlobalSingletons:
    """测试全局单例函数"""

    def test_get_unified_cache_manager_singleton(self):
        """测试缓存管理器单例"""
        # 重置全局变量
        import plookingII.core.unified_interfaces as ui_module
        ui_module._unified_cache_manager = None
        
        manager1 = get_unified_cache_manager()
        manager2 = get_unified_cache_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, UnifiedCacheManager)

    def test_get_unified_status_manager_singleton(self):
        """测试状态管理器单例"""
        # 重置全局变量
        import plookingII.core.unified_interfaces as ui_module
        ui_module._unified_status_manager = None
        
        manager1 = get_unified_status_manager()
        manager2 = get_unified_status_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, UnifiedStatusManager)


# ==================== 便捷函数测试 ====================


class TestConvenienceFunctions:
    """测试便捷函数"""

    @patch('plookingII.core.unified_interfaces.get_unified_cache_manager')
    def test_clear_all_caches(self, mock_get_manager):
        """测试清理所有缓存便捷函数"""
        mock_manager = MagicMock()
        mock_manager.clear_cache.return_value = True
        mock_get_manager.return_value = mock_manager
        
        result = clear_all_caches()
        
        assert result is True
        mock_manager.clear_cache.assert_called_once_with()

    @patch('plookingII.core.unified_interfaces.get_unified_status_manager')
    def test_set_global_status(self, mock_get_manager):
        """测试设置全局状态便捷函数"""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        
        set_global_status("Test message", 10.0)
        
        mock_manager.set_status_message.assert_called_once_with("Test message", 10.0)

    @patch('plookingII.core.unified_interfaces.get_unified_status_manager')
    def test_set_global_status_no_timeout(self, mock_get_manager):
        """测试设置全局状态无超时"""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        
        set_global_status("Test message")
        
        mock_manager.set_status_message.assert_called_once_with("Test message", None)


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    def test_cache_manager_workflow(self):
        """测试缓存管理器完整工作流"""
        manager = UnifiedCacheManager()
        
        # 注册多个提供者
        provider1 = MockCacheProvider()
        provider2 = MockCacheProvider()
        manager.register_cache_provider("cache1", provider1)
        manager.register_cache_provider("cache2", provider2)
        
        # 清理所有
        result = manager.clear_cache()
        assert result is True
        
        # 获取统计
        stats = manager.get_cache_stats()
        assert stats["total_clears"] == 2
        assert len(stats["providers"]) == 2

    def test_status_manager_workflow(self):
        """测试状态管理器完整工作流"""
        manager = UnifiedStatusManager()
        
        # 注册多个提供者
        provider1 = MockStatusProvider()
        provider2 = MockStatusProvider()
        manager.register_status_provider("status1", provider1)
        manager.register_status_provider("status2", provider2)
        
        # 设置消息
        manager.set_status_message("Working...")
        assert provider1.message == "Working..."
        assert provider2.message == "Working..."
        
        # 更新显示
        manager.update_status_display(progress=75)
        assert provider1.status["progress"] == 75
        assert provider2.status["progress"] == 75
        
        # 获取状态
        status = manager.get_current_status()
        assert status["message"] == "Working..."
        assert status["status"]["progress"] == 75

    def test_mixed_success_and_failure(self):
        """测试混合成功和失败的场景"""
        cache_manager = UnifiedCacheManager()
        
        # 一个正常提供者，一个失败提供者
        working_provider = MockCacheProvider()
        failing_provider = MockCacheProvider()
        failing_provider.clear_cache = Mock(side_effect=Exception("Failed"))
        
        cache_manager.register_cache_provider("working", working_provider)
        cache_manager.register_cache_provider("failing", failing_provider)
        
        with patch('plookingII.core.unified_interfaces.logger'):
            result = cache_manager.clear_cache()
        
        # 部分失败，返回False
        assert result is False
        # 但working_provider应该成功
        assert working_provider.cleared is True


# ==================== 边界情况测试 ====================


class TestEdgeCases:
    """测试边界情况"""

    def test_clear_cache_no_providers(self):
        """测试无提供者时清理缓存"""
        manager = UnifiedCacheManager()
        
        result = manager.clear_cache()
        
        # 0/0 == True (所有提供者都成功)
        assert result is True

    def test_get_stats_no_providers(self):
        """测试无提供者时获取统计"""
        manager = UnifiedCacheManager()
        
        stats = manager.get_cache_stats()
        
        assert stats["total_clears"] == 0
        assert stats["providers"] == {}

    def test_set_status_no_providers(self):
        """测试无提供者时设置状态"""
        manager = UnifiedStatusManager()
        
        # 应该不抛出异常
        try:
            manager.set_status_message("Test")
            manager.update_status_display(test=1)
        except Exception:
            pytest.fail("应该处理无提供者的情况")

    def test_register_same_provider_twice(self):
        """测试重复注册同名提供者"""
        manager = UnifiedCacheManager()
        provider1 = MockCacheProvider()
        provider2 = MockCacheProvider()
        
        manager.register_cache_provider("test", provider1)
        manager.register_cache_provider("test", provider2)
        
        # 第二个应该覆盖第一个
        assert manager._cache_providers["test"] == provider2
        # cache_types应该只有一个
        assert manager._stats["cache_types"].count("test") == 1

