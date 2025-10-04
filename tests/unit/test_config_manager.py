"""
测试 config/manager.py 模块

测试目标：达到90%+覆盖率
"""

import json
import os
import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open

import pytest

from plookingII.config.manager import (
    ConfigManager,
    ConfigType,
    ConfigSchema,
    get_config_manager,
    get_config,
    set_config,
    Config,
)


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestConfigType:
    """测试ConfigType枚举"""

    def test_config_type_values(self):
        """测试配置类型枚举值"""
        assert ConfigType.STRING.value == "string"
        assert ConfigType.INTEGER.value == "integer"
        assert ConfigType.FLOAT.value == "float"
        assert ConfigType.BOOLEAN.value == "boolean"
        assert ConfigType.LIST.value == "list"
        assert ConfigType.DICT.value == "dict"

    def test_config_type_enum(self):
        """测试枚举成员"""
        assert isinstance(ConfigType.STRING, ConfigType)
        assert ConfigType.STRING == ConfigType.STRING
        assert ConfigType.STRING != ConfigType.INTEGER


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestConfigSchema:
    """测试ConfigSchema数据类"""

    def test_config_schema_creation(self):
        """测试创建配置模式"""
        schema = ConfigSchema(
            key="test.key",
            default_value=42,
            config_type=ConfigType.INTEGER,
            description="Test config"
        )
        assert schema.key == "test.key"
        assert schema.default_value == 42
        assert schema.config_type == ConfigType.INTEGER
        assert schema.description == "Test config"
        assert schema.validator is None
        assert schema.env_var is None
        assert schema.user_configurable is True

    def test_config_schema_with_validator(self):
        """测试带验证器的配置模式"""
        validator = lambda x: x > 0
        schema = ConfigSchema(
            key="test.key",
            default_value=10,
            config_type=ConfigType.INTEGER,
            validator=validator
        )
        assert schema.validator is not None
        assert schema.validator(10) is True
        assert schema.validator(-1) is False

    def test_config_schema_with_env_var(self):
        """测试带环境变量的配置模式"""
        schema = ConfigSchema(
            key="test.key",
            default_value="default",
            config_type=ConfigType.STRING,
            env_var="TEST_ENV_VAR"
        )
        assert schema.env_var == "TEST_ENV_VAR"


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestConfigManagerInit:
    """测试ConfigManager初始化"""

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_init_creates_instance(self, mock_load):
        """测试创建实例"""
        manager = ConfigManager()
        assert manager._configs == {}
        assert isinstance(manager._schemas, dict)
        assert isinstance(manager._observers, list)
        assert mock_load.called

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_init_has_lock(self, mock_load):
        """测试有线程锁"""
        manager = ConfigManager()
        assert hasattr(manager, '_lock')
        assert isinstance(manager._lock, type(threading.RLock()))

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_init_schemas_registered(self, mock_load):
        """测试默认配置模式已注册"""
        manager = ConfigManager()
        # 检查一些关键配置是否注册
        assert "app.name" in manager._schemas
        assert "app.version" in manager._schemas
        assert "ui.window.width" in manager._schemas


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestConfigManagerGet:
    """测试ConfigManager.get方法"""

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_get_default_value(self, mock_load):
        """测试获取默认值"""
        manager = ConfigManager()
        value = manager.get("app.name")
        assert value == "PlookingII"

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_get_user_config(self, mock_load):
        """测试获取用户配置值"""
        manager = ConfigManager()
        manager._configs["ui.window.width"] = 1600
        value = manager.get("ui.window.width")
        assert value == 1600

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_get_nonexistent_key(self, mock_load):
        """测试获取不存在的键"""
        manager = ConfigManager()
        value = manager.get("nonexistent.key", "default")
        assert value == "default"

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_get_with_env_override(self, mock_load):
        """测试环境变量覆盖"""
        manager = ConfigManager()
        with patch.dict(os.environ, {"PLOOKINGII_WINDOW_WIDTH": "1920"}):
            value = manager.get("ui.window.width")
            assert value == 1920

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_get_env_conversion_failure(self, mock_load):
        """测试环境变量转换失败"""
        manager = ConfigManager()
        with patch.dict(os.environ, {"PLOOKINGII_WINDOW_WIDTH": "invalid"}):
            # 转换失败，应该返回默认值或用户配置
            value = manager.get("ui.window.width")
            assert isinstance(value, int)


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestConfigManagerSet:
    """测试ConfigManager.set方法"""

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_set_valid_config(self, mock_load):
        """测试设置有效配置"""
        manager = ConfigManager()
        result = manager.set("ui.window.width", 1920)
        assert result is True
        assert manager.get("ui.window.width") == 1920

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_set_invalid_config(self, mock_load):
        """测试设置无效配置"""
        manager = ConfigManager()
        result = manager.set("nonexistent.key", 123)
        assert result is False

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    @patch('plookingII.config.manager.ConfigManager._save_user_config')
    def test_set_with_persist(self, mock_save, mock_load):
        """测试持久化配置"""
        manager = ConfigManager()
        result = manager.set("ui.window.width", 1920, persist=True)
        assert result is True
        assert mock_save.called

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_set_notifies_observers(self, mock_load):
        """测试通知观察者"""
        manager = ConfigManager()
        observer_called = []

        def observer(key, old, new):
            observer_called.append((key, old, new))

        manager.add_observer(observer)
        manager.set("ui.window.width", 1920)

        assert len(observer_called) == 1
        assert observer_called[0][0] == "ui.window.width"
        assert observer_called[0][2] == 1920


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestConfigManagerObservers:
    """测试配置观察者"""

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_add_observer(self, mock_load):
        """测试添加观察者"""
        manager = ConfigManager()
        observer = Mock()
        manager.add_observer(observer)
        assert observer in manager._observers

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_add_duplicate_observer(self, mock_load):
        """测试添加重复观察者"""
        manager = ConfigManager()
        observer = Mock()
        manager.add_observer(observer)
        manager.add_observer(observer)
        assert manager._observers.count(observer) == 1

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_remove_observer(self, mock_load):
        """测试移除观察者"""
        manager = ConfigManager()
        observer = Mock()
        manager.add_observer(observer)
        manager.remove_observer(observer)
        assert observer not in manager._observers

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_observer_called_on_set(self, mock_load):
        """测试设置时调用观察者"""
        manager = ConfigManager()
        observer = Mock()
        manager.add_observer(observer)
        manager.set("ui.window.width", 1920)
        assert observer.called

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_observer_exception_handling(self, mock_load):
        """测试观察者异常处理"""
        manager = ConfigManager()
        bad_observer = Mock(side_effect=Exception("Observer error"))
        good_observer = Mock()

        manager.add_observer(bad_observer)
        manager.add_observer(good_observer)

        # 设置配置不应因观察者异常而失败
        result = manager.set("ui.window.width", 1920)
        assert result is True
        assert good_observer.called


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestConfigManagerReset:
    """测试配置重置"""

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_reset_single_key(self, mock_load):
        """测试重置单个配置"""
        manager = ConfigManager()
        manager.set("ui.window.width", 1920)
        manager.reset_to_defaults(["ui.window.width"])
        value = manager.get("ui.window.width")
        assert value == 1200  # 默认值

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_reset_all_keys(self, mock_load):
        """测试重置所有配置"""
        manager = ConfigManager()
        manager.set("ui.window.width", 1920)
        manager.set("ui.window.height", 1080)
        manager.reset_to_defaults()
        assert manager.get("ui.window.width") == 1200
        assert manager.get("ui.window.height") == 800

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_reset_notifies_observers(self, mock_load):
        """测试重置时通知观察者"""
        manager = ConfigManager()
        observer = Mock()
        manager.add_observer(observer)
        manager.set("ui.window.width", 1920)
        observer.reset_mock()
        manager.reset_to_defaults(["ui.window.width"])
        assert observer.called


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestConfigManagerValidation:
    """测试配置验证"""

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_validate_integer_type(self, mock_load):
        """测试整数类型验证"""
        manager = ConfigManager()
        # 有效的整数
        assert manager._validate_config("ui.window.width", 1920) is True
        # 可转换的字符串
        assert manager._validate_config("ui.window.width", "1920") is True
        # 无效的值
        assert manager._validate_config("ui.window.width", "invalid") is False

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_validate_float_type(self, mock_load):
        """测试浮点数类型验证"""
        manager = ConfigManager()
        assert manager._validate_config("image.jpeg_quality", 0.92) is True
        # 字符串会在类型检查时尝试转换，但自定义验证器可能在转换前运行
        # 因此字符串形式可能失败 - 这是预期行为
        assert manager._validate_config("image.jpeg_quality", "invalid") is False

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_validate_boolean_type(self, mock_load):
        """测试布尔类型验证"""
        manager = ConfigManager()
        assert manager._validate_config("performance.preload_enabled", True) is True
        assert manager._validate_config("performance.preload_enabled", "true") is True
        assert manager._validate_config("performance.preload_enabled", "yes") is True

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_validate_with_custom_validator(self, mock_load):
        """测试自定义验证器"""
        manager = ConfigManager()
        # image.jpeg_quality有质量验证器 (0.0-1.0)
        assert manager._validate_config("image.jpeg_quality", 0.5) is True
        assert manager._validate_config("image.jpeg_quality", 1.5) is False
        assert manager._validate_config("image.jpeg_quality", -0.1) is False

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_validate_unknown_key(self, mock_load):
        """测试未知配置键"""
        manager = ConfigManager()
        result = manager._validate_config("unknown.key", 123)
        assert result is False


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestConfigManagerConversion:
    """测试配置值转换"""

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_convert_string(self, mock_load):
        """测试字符串转换"""
        manager = ConfigManager()
        result = manager._convert_value("test", ConfigType.STRING)
        assert result == "test"
        assert isinstance(result, str)

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_convert_integer(self, mock_load):
        """测试整数转换"""
        manager = ConfigManager()
        result = manager._convert_value("42", ConfigType.INTEGER)
        assert result == 42
        assert isinstance(result, int)

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_convert_float(self, mock_load):
        """测试浮点数转换"""
        manager = ConfigManager()
        result = manager._convert_value("3.14", ConfigType.FLOAT)
        assert result == 3.14
        assert isinstance(result, float)

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_convert_boolean_true(self, mock_load):
        """测试布尔值转换 - true"""
        manager = ConfigManager()
        for value in ["true", "TRUE", "1", "yes", "on"]:
            result = manager._convert_value(value, ConfigType.BOOLEAN)
            assert result is True

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_convert_boolean_false(self, mock_load):
        """测试布尔值转换 - false"""
        manager = ConfigManager()
        for value in ["false", "FALSE", "0", "no", "off"]:
            result = manager._convert_value(value, ConfigType.BOOLEAN)
            assert result is False

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_convert_list_json(self, mock_load):
        """测试列表转换 - JSON格式"""
        manager = ConfigManager()
        result = manager._convert_value('["a", "b", "c"]', ConfigType.LIST)
        assert result == ["a", "b", "c"]

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_convert_list_comma_separated(self, mock_load):
        """测试列表转换 - 逗号分隔"""
        manager = ConfigManager()
        result = manager._convert_value("a,b,c", ConfigType.LIST)
        assert result == ["a", "b", "c"]

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_convert_dict(self, mock_load):
        """测试字典转换"""
        manager = ConfigManager()
        result = manager._convert_value('{"key": "value"}', ConfigType.DICT)
        assert result == {"key": "value"}


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestConfigManagerPersistence:
    """测试配置持久化"""

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_get_config_file_path(self, mock_load):
        """测试获取配置文件路径"""
        manager = ConfigManager()
        path = manager._get_config_file_path()
        assert "plookingii" in path.lower()
        assert "config.json" in path
        assert os.path.isabs(path)

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    @patch('builtins.open', new_callable=mock_open, read_data='{"ui.window.width": 1920}')
    @patch('os.path.exists', return_value=True)
    def test_load_user_config(self, mock_exists, mock_file, mock_load):
        """测试加载用户配置"""
        manager = ConfigManager()
        manager._load_user_config()
        # 配置应该已加载
        assert "ui.window.width" in manager._configs

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    @patch('os.path.exists', return_value=False)
    def test_load_user_config_no_file(self, mock_exists, mock_load):
        """测试加载不存在的用户配置"""
        manager = ConfigManager()
        # 不应该抛出异常
        manager._load_user_config()

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_save_user_config(self, mock_makedirs, mock_file, mock_load):
        """测试保存用户配置"""
        manager = ConfigManager()
        manager._configs["ui.window.width"] = 1920
        manager._save_user_config()
        assert mock_file.called
        assert mock_makedirs.called

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    @patch('builtins.open', side_effect=Exception("Write error"))
    @patch('os.makedirs')
    def test_save_user_config_exception(self, mock_makedirs, mock_file, mock_load):
        """测试保存配置异常处理"""
        manager = ConfigManager()
        # 不应该抛出异常
        manager._save_user_config()


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestConfigManagerValidators:
    """测试配置验证器"""

    def test_validate_quality(self):
        """测试质量参数验证器"""
        assert ConfigManager._validate_quality(0.0) is True
        assert ConfigManager._validate_quality(0.5) is True
        assert ConfigManager._validate_quality(1.0) is True
        assert ConfigManager._validate_quality(-0.1) is False
        assert ConfigManager._validate_quality(1.1) is False

    def test_validate_log_level(self):
        """测试日志级别验证器"""
        assert ConfigManager._validate_log_level("DEBUG") is True
        assert ConfigManager._validate_log_level("INFO") is True
        assert ConfigManager._validate_log_level("WARNING") is True
        assert ConfigManager._validate_log_level("ERROR") is True
        assert ConfigManager._validate_log_level("CRITICAL") is True
        assert ConfigManager._validate_log_level("info") is True  # 大小写
        assert ConfigManager._validate_log_level("INVALID") is False

    def test_validate_watcher_strategy(self):
        """测试文件监听策略验证器"""
        assert ConfigManager._validate_watcher_strategy("auto") is True
        assert ConfigManager._validate_watcher_strategy("watchdog") is True
        assert ConfigManager._validate_watcher_strategy("polling") is True
        assert ConfigManager._validate_watcher_strategy("invalid") is False


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestGlobalConfigManager:
    """测试全局配置管理器"""

    @patch('plookingII.config.manager.ConfigManager')
    def test_get_config_manager_singleton(self, mock_manager_class):
        """测试全局配置管理器是单例"""
        # 重置全局变量
        import plookingII.config.manager as manager_module
        manager_module._config_manager = None

        mock_instance = Mock()
        mock_manager_class.return_value = mock_instance

        manager1 = manager_module.get_config_manager()
        manager2 = manager_module.get_config_manager()

        assert manager1 is manager2
        assert mock_manager_class.call_count == 1


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestConvenienceFunctions:
    """测试便捷函数"""

    @patch('plookingII.config.manager.get_config_manager')
    def test_get_config_function(self, mock_get_manager):
        """测试get_config便捷函数"""
        mock_manager = Mock()
        mock_manager.get.return_value = 1920
        mock_get_manager.return_value = mock_manager

        value = get_config("ui.window.width", 1200)
        assert value == 1920
        mock_manager.get.assert_called_once_with("ui.window.width", 1200)

    @patch('plookingII.config.manager.get_config_manager')
    def test_set_config_function(self, mock_get_manager):
        """测试set_config便捷函数"""
        mock_manager = Mock()
        mock_manager.set.return_value = True
        mock_get_manager.return_value = mock_manager

        result = set_config("ui.window.width", 1920, persist=True)
        assert result is True
        mock_manager.set.assert_called_once_with("ui.window.width", 1920, True)


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestConfigClass:
    """测试Config便捷类"""

    @patch('plookingII.config.manager.get_config')
    def test_get_window_size(self, mock_get_config):
        """测试获取窗口大小"""
        mock_get_config.side_effect = lambda key, default: {
            "ui.window.width": 1920,
            "ui.window.height": 1080
        }.get(key, default)

        width, height = Config.get_window_size()
        assert width == 1920
        assert height == 1080

    @patch('plookingII.config.manager.get_config')
    def test_get_cache_config(self, mock_get_config):
        """测试获取缓存配置"""
        mock_get_config.side_effect = lambda key, default: {
            "cache.max_memory_mb": 512,
            "cache.max_images": 100,
            "cache.preview_max_mb": 128
        }.get(key, default)

        config = Config.get_cache_config()
        assert config["max_memory_mb"] == 512
        assert config["max_images"] == 100
        assert config["preview_max_mb"] == 128

    @patch('plookingII.config.manager.get_config')
    def test_get_performance_config(self, mock_get_config):
        """测试获取性能配置"""
        mock_get_config.side_effect = lambda key, default: {
            "performance.preload_enabled": True,
            "performance.concurrent_loads": 2,
            "performance.debounce_ms": 80
        }.get(key, default)

        config = Config.get_performance_config()
        assert config["preload_enabled"] is True
        assert config["concurrent_loads"] == 2
        assert config["debounce_ms"] == 80

    @patch('plookingII.config.manager.get_config')
    def test_get_monitor_config(self, mock_get_config):
        """测试获取监控配置"""
        mock_get_config.side_effect = lambda key, default: {
            "monitor.enabled": True,
            "monitor.interval_seconds": 5.0,
            "monitor.history_size": 1000
        }.get(key, default)

        config = Config.get_monitor_config()
        assert config["enabled"] is True
        assert config["interval"] == 5.0
        assert config["history_size"] == 1000


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestConfigManagerThreadSafety:
    """测试线程安全"""

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_concurrent_get(self, mock_load):
        """测试并发获取配置"""
        manager = ConfigManager()
        results = []

        def get_config():
            for _ in range(100):
                results.append(manager.get("ui.window.width"))

        threads = [threading.Thread(target=get_config) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有结果应该一致
        assert all(r == results[0] for r in results)

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_concurrent_set(self, mock_load):
        """测试并发设置配置"""
        manager = ConfigManager()

        def set_config(value):
            manager.set("ui.window.width", value)

        threads = [threading.Thread(target=set_config, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 应该有一个值被设置
        value = manager.get("ui.window.width")
        assert isinstance(value, int)
        assert 0 <= value < 10


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestConfigManagerGetAllConfigs:
    """测试获取所有配置"""

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_get_all_configs(self, mock_load):
        """测试获取所有配置"""
        manager = ConfigManager()
        all_configs = manager.get_all_configs()

        assert isinstance(all_configs, dict)
        assert "app.name" in all_configs
        assert "app.version" in all_configs
        assert len(all_configs) > 0

    @patch('plookingII.config.manager.ConfigManager._load_all_configs')
    def test_get_user_configurable_items(self, mock_load):
        """测试获取用户可配置项"""
        manager = ConfigManager()
        user_items = manager.get_user_configurable_items()

        assert isinstance(user_items, dict)
        # app.name和app.version不应该是用户可配置的
        assert "app.name" not in user_items
        assert "app.version" not in user_items
        # 其他配置应该是用户可配置的
        assert "ui.window.width" in user_items

