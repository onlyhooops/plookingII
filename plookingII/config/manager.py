#!/usr/bin/env python3
"""
统一配置管理器

整合分散的配置模块，提供统一的配置接口，支持环境变量覆盖和配置验证。

主要功能：
- 统一配置访问接口
- 环境变量覆盖支持
- 配置验证和类型检查
- 配置热更新
- 配置持久化

Author: PlookingII Team
"""

import json
import logging
import os
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .constants import APP_NAME, VERSION

logger = logging.getLogger(APP_NAME)


class ConfigType(Enum):
    """配置类型枚举"""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"


@dataclass
class ConfigSchema:
    """配置项模式定义"""

    key: str
    default_value: Any
    config_type: ConfigType
    description: str = ""
    validator: Callable | None = None
    env_var: str | None = None  # 对应的环境变量名
    user_configurable: bool = True  # 是否允许用户配置


class ConfigManager:
    """统一配置管理器

    提供统一的配置管理功能，整合所有分散的配置模块。
    """

    def __init__(self):
        """初始化配置管理器"""
        self._configs: dict[str, Any] = {}
        self._schemas: dict[str, ConfigSchema] = {}
        self._lock = threading.RLock()
        self._observers: list[callable] = []

        # 初始化配置模式
        self._init_config_schemas()

        # 加载配置
        self._load_all_configs()

        logger.info("统一配置管理器已初始化")

    def _init_config_schemas(self):
        """初始化配置模式定义"""
        # 应用基础配置
        self._register_schema("app.name", APP_NAME, ConfigType.STRING, "应用程序名称", user_configurable=False)
        self._register_schema("app.version", VERSION, ConfigType.STRING, "应用程序版本", user_configurable=False)

        # UI配置
        self._register_schema(
            "ui.window.width", 1200, ConfigType.INTEGER, "窗口默认宽度", env_var="PLOOKINGII_WINDOW_WIDTH"
        )
        self._register_schema(
            "ui.window.height", 800, ConfigType.INTEGER, "窗口默认高度", env_var="PLOOKINGII_WINDOW_HEIGHT"
        )
        self._register_schema("ui.status_bar.height", 30, ConfigType.INTEGER, "状态栏高度")

        # 图像处理配置
        self._register_schema(
            "image.max_dimension", 4096, ConfigType.INTEGER, "最大图像尺寸", env_var="PLOOKINGII_MAX_DIMENSION"
        )
        self._register_schema("image.jpeg_quality", 0.92, ConfigType.FLOAT, "JPEG质量", self._validate_quality)
        self._register_schema("image.supported_formats", [".jpg", ".jpeg", ".png"], ConfigType.LIST, "支持的图像格式")

        # 缓存配置
        self._register_schema(
            "cache.max_memory_mb", 512, ConfigType.INTEGER, "最大缓存内存(MB)", env_var="PLOOKINGII_CACHE_MAX_MB"
        )
        self._register_schema(
            "cache.max_images", 100, ConfigType.INTEGER, "最大缓存图片数", env_var="PLOOKINGII_CACHE_MAX_IMAGES"
        )
        self._register_schema("cache.preview_max_mb", 128, ConfigType.INTEGER, "预览缓存最大内存(MB)")

        # 性能配置
        self._register_schema(
            "performance.preload_enabled", True, ConfigType.BOOLEAN, "启用预加载", env_var="PLOOKINGII_PRELOAD_ENABLED"
        )
        self._register_schema(
            "performance.concurrent_loads", 2, ConfigType.INTEGER, "并发加载数", env_var="PLOOKINGII_CONCURRENT_LOADS"
        )
        self._register_schema(
            "performance.debounce_ms", 20, ConfigType.INTEGER, "按键防抖时间(毫秒)", env_var="PLOOKINGII_DEBOUNCE_MS"
        )

        # 监控配置
        self._register_schema("monitor.enabled", True, ConfigType.BOOLEAN, "启用性能监控")
        self._register_schema("monitor.interval_seconds", 5.0, ConfigType.FLOAT, "监控间隔(秒)")
        self._register_schema("monitor.history_size", 1000, ConfigType.INTEGER, "监控历史记录数")

        # 文件监听配置
        self._register_schema("file_watcher.enabled", True, ConfigType.BOOLEAN, "启用文件监听")
        self._register_schema(
            "file_watcher.strategy", "auto", ConfigType.STRING, "文件监听策略", self._validate_watcher_strategy
        )
        self._register_schema("file_watcher.debounce_seconds", 1.0, ConfigType.FLOAT, "文件监听防抖时间")

        # 日志配置
        self._register_schema(
            "logging.level", "INFO", ConfigType.STRING, "日志级别", self._validate_log_level, "PLOOKINGII_LOG_LEVEL"
        )
        self._register_schema("logging.file_enabled", False, ConfigType.BOOLEAN, "启用日志文件")

    def _register_schema(
        self,
        key: str,
        default_value: Any,
        config_type: ConfigType,
        description: str = "",
        validator: Callable | None = None,
        env_var: str | None = None,
        user_configurable: bool = True,
    ):
        """注册配置模式

        Args:
            key: 配置键
            default_value: 默认值
            config_type: 配置类型
            description: 描述
            validator: 验证函数
            env_var: 环境变量名
            user_configurable: 是否允许用户配置
        """
        schema = ConfigSchema(
            key=key,
            default_value=default_value,
            config_type=config_type,
            description=description,
            validator=validator,
            env_var=env_var,
            user_configurable=user_configurable,
        )
        self._schemas[key] = schema

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值

        优先级: 环境变量 > 用户配置 > 默认配置

        Args:
            key: 配置键
            default: 默认值（如果配置不存在）

        Returns:
            Any: 配置值
        """
        with self._lock:
            # 1. 检查环境变量
            if key in self._schemas:
                schema = self._schemas[key]
                if schema.env_var:
                    env_value = os.environ.get(schema.env_var)
                    if env_value is not None:
                        try:
                            return self._convert_value(env_value, schema.config_type)
                        except Exception as e:
                            logger.warning("环境变量%s转换失败: {e}", schema.env_var)

            # 2. 检查用户配置
            if key in self._configs:
                return self._configs[key]

            # 3. 检查默认配置
            if key in self._schemas:
                return self._schemas[key].default_value

            # 4. 返回提供的默认值
            return default

    def set(self, key: str, value: Any, persist: bool = False) -> bool:
        """设置配置值

        Args:
            key: 配置键
            value: 配置值
            persist: 是否持久化到文件

        Returns:
            bool: 设置是否成功
        """
        with self._lock:
            # 验证配置
            if not self._validate_config(key, value):
                return False

            old_value = self._configs.get(key)
            self._configs[key] = value

            # 通知观察者
            self._notify_observers(key, old_value, value)

            # 持久化
            if persist:
                self._save_user_config()

            logger.debug("配置已更新: %s = {value}", key)
            return True

    def get_all_configs(self) -> dict[str, Any]:
        """获取所有配置"""
        with self._lock:
            result = {}
            for key in self._schemas:
                result[key] = self.get(key)
            return result

    def get_user_configurable_items(self) -> dict[str, ConfigSchema]:
        """获取用户可配置的项目"""
        return {k: v for k, v in self._schemas.items() if v.user_configurable}

    def reset_to_defaults(self, keys: list[str] | None = None):
        """重置配置为默认值

        Args:
            keys: 要重置的配置键列表，None表示重置所有
        """
        with self._lock:
            keys_to_reset = keys or list(self._schemas.keys())

            for key in keys_to_reset:
                if key in self._schemas:
                    old_value = self._configs.get(key)
                    default_value = self._schemas[key].default_value
                    self._configs[key] = default_value
                    self._notify_observers(key, old_value, default_value)

            logger.info("已重置%s个配置项为默认值", len(keys_to_reset))

    def add_observer(self, callback: callable):
        """添加配置变更观察者

        Args:
            callback: 回调函数 (key, old_value, new_value) -> None
        """
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback: callable):
        """移除配置变更观察者"""
        if callback in self._observers:
            self._observers.remove(callback)

    def _load_all_configs(self):
        """加载所有配置"""
        # 加载用户配置文件
        self._load_user_config()

        # 应用环境变量覆盖
        self._apply_env_overrides()

    def _load_user_config(self):
        """加载用户配置文件"""
        try:
            config_file = self._get_config_file_path()
            if os.path.exists(config_file):
                with open(config_file, encoding="utf-8") as f:
                    user_config = json.load(f)
                    self._configs.update(user_config)
                logger.info("已加载用户配置: %s", config_file)
        except Exception as e:
            logger.warning("加载用户配置失败: %s", e)

    def _save_user_config(self):
        """保存用户配置到文件"""
        try:
            config_file = self._get_config_file_path()
            os.makedirs(os.path.dirname(config_file), exist_ok=True)

            # 只保存用户可配置的项目
            user_config = {}
            for key, value in self._configs.items():
                if key in self._schemas and self._schemas[key].user_configurable:
                    user_config[key] = value

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(user_config, f, indent=2, ensure_ascii=False)

            logger.info("用户配置已保存: %s", config_file)
        except Exception as e:
            logger.exception("保存用户配置失败: %s", e)

    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        for key, schema in self._schemas.items():
            if schema.env_var:
                env_value = os.environ.get(schema.env_var)
                if env_value is not None:
                    try:
                        converted_value = self._convert_value(env_value, schema.config_type)
                        self._configs[key] = converted_value
                        logger.debug("环境变量覆盖: %s = {converted_value}", key)
                    except Exception as e:
                        logger.warning("环境变量%s转换失败: {e}", schema.env_var)

    def _get_config_file_path(self) -> str:
        """获取配置文件路径"""
        home_dir = os.path.expanduser("~")
        app_data_dir = os.path.join(home_dir, f".{APP_NAME.lower()}")
        return os.path.join(app_data_dir, "config.json")

    def _convert_value(self, value: str, config_type: ConfigType) -> Any:
        """转换配置值类型"""
        if config_type == ConfigType.STRING:
            return str(value)
        if config_type == ConfigType.INTEGER:
            return int(value)
        if config_type == ConfigType.FLOAT:
            return float(value)
        if config_type == ConfigType.BOOLEAN:
            return value.lower() in ("true", "1", "yes", "on")
        if config_type == ConfigType.LIST:
            return json.loads(value) if value.startswith("[") else value.split(",")
        if config_type == ConfigType.DICT:
            return json.loads(value)
        return value

    def _validate_config(self, key: str, value: Any) -> bool:
        """验证配置值"""
        if key not in self._schemas:
            logger.warning("未知配置项: %s", key)
            return False

        schema = self._schemas[key]

        # 类型验证
        try:
            if schema.config_type == ConfigType.INTEGER and not isinstance(value, int):
                int(value)  # 尝试转换
            elif schema.config_type == ConfigType.FLOAT and not isinstance(value, (int, float)):
                float(value)  # 尝试转换
            elif schema.config_type == ConfigType.BOOLEAN and not isinstance(value, bool):
                # 允许字符串形式的布尔值
                if isinstance(value, str):
                    value.lower() in ("true", "false", "1", "0", "yes", "no")
        except (ValueError, TypeError):
            logger.exception("配置值类型错误: %s = {value}", key)
            return False

        # 自定义验证
        if schema.validator:
            try:
                if not schema.validator(value):
                    logger.error("配置值验证失败: %s = {value}", key)
                    return False
            except Exception as e:
                logger.exception("配置验证器执行失败: %s", e)
                return False

        return True

    def _notify_observers(self, key: str, old_value: Any, new_value: Any):
        """通知配置变更观察者"""
        for observer in self._observers:
            try:
                observer(key, old_value, new_value)
            except Exception as e:
                logger.exception("配置观察者通知失败: %s", e)

    # 配置验证器
    @staticmethod
    def _validate_quality(value: float) -> bool:
        """验证质量参数"""
        return 0.0 <= value <= 1.0

    @staticmethod
    def _validate_log_level(value: str) -> bool:
        """验证日志级别"""
        return value.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    @staticmethod
    def _validate_watcher_strategy(value: str) -> bool:
        """验证文件监听策略"""
        return value in ["auto", "watchdog", "polling"]


# 全局配置管理器实例
_config_manager: ConfigManager | None = None
_config_lock = threading.Lock()


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    with _config_lock:
        if _config_manager is None:
            _config_manager = ConfigManager()
        return _config_manager


def get_config(key: str, default: Any = None) -> Any:
    """便捷的配置获取函数

    Args:
        key: 配置键
        default: 默认值

    Returns:
        Any: 配置值
    """
    return get_config_manager().get(key, default)


def set_config(key: str, value: Any, persist: bool = False) -> bool:
    """便捷的配置设置函数

    Args:
        key: 配置键
        value: 配置值
        persist: 是否持久化

    Returns:
        bool: 设置是否成功
    """
    return get_config_manager().set(key, value, persist)


# 便捷的配置访问接口
class Config:
    """便捷的配置访问类"""

    @staticmethod
    def get_window_size() -> tuple:
        """获取窗口大小"""
        width = get_config("ui.window.width", 1200)
        height = get_config("ui.window.height", 800)
        return (width, height)

    @staticmethod
    def get_cache_config() -> dict[str, Any]:
        """获取缓存配置"""
        return {
            "max_memory_mb": get_config("cache.max_memory_mb", 512),
            "max_images": get_config("cache.max_images", 100),
            "preview_max_mb": get_config("cache.preview_max_mb", 128),
        }

    @staticmethod
    def get_performance_config() -> dict[str, Any]:
        """获取性能配置"""
        return {
            "preload_enabled": get_config("performance.preload_enabled", True),
            "concurrent_loads": get_config("performance.concurrent_loads", 2),
            "debounce_ms": get_config("performance.debounce_ms", 80),
        }

    @staticmethod
    def get_monitor_config() -> dict[str, Any]:
        """获取监控配置"""
        return {
            "enabled": get_config("monitor.enabled", True),
            "interval": get_config("monitor.interval_seconds", 5.0),
            "history_size": get_config("monitor.history_size", 1000),
        }
