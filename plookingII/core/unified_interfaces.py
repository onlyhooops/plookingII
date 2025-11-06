"""
统一接口 - 清理重复函数和接口的统一抽象层

该模块提供统一的接口定义，用于替代项目中的重复功能：
- 缓存清理接口
- 状态更新接口
- 配置管理接口
- 监控接口
"""

from abc import ABC, abstractmethod
from typing import Any

from ..config.constants import APP_NAME
from ..imports import logging

logger = logging.getLogger(APP_NAME)


class CacheInterface(ABC):
    """统一缓存接口 - 替代多个重复的缓存清理方法"""

    @abstractmethod
    def clear_cache(self, cache_type: str | None = None) -> bool:
        """清理缓存

        Args:
            cache_type: 缓存类型，None表示清理所有

        Returns:
            bool: 清理成功返回True
        """

    @abstractmethod
    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息

        Returns:
            Dict[str, Any]: 缓存统计信息
        """


class StatusInterface(ABC):
    """统一状态接口 - 替代多个重复的状态更新方法"""

    @abstractmethod
    def set_status_message(self, message: str, timeout: float | None = None) -> None:
        """设置状态消息

        Args:
            message: 状态消息
            timeout: 超时时间（秒），None表示永久显示
        """

    @abstractmethod
    def update_status_display(self, **kwargs) -> None:
        """更新状态显示

        Args:
            **kwargs: 状态参数
        """

    @abstractmethod
    def get_current_status(self) -> dict[str, Any]:
        """获取当前状态

        Returns:
            Dict[str, Any]: 当前状态信息
        """


class ConfigInterface(ABC):
    """统一配置接口 - 替代多个重复的配置管理方法"""

    @abstractmethod
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            Any: 配置值
        """

    @abstractmethod
    def set_config(self, key: str, value: Any) -> bool:
        """设置配置值

        Args:
            key: 配置键
            value: 配置值

        Returns:
            bool: 设置成功返回True
        """

    @abstractmethod
    def save_config(self) -> bool:
        """保存配置

        Returns:
            bool: 保存成功返回True
        """


class MonitorInterface(ABC):
    """统一监控接口 - 替代多个重复的监控方法"""

    @abstractmethod
    def start_monitoring(self) -> bool:
        """开始监控

        Returns:
            bool: 启动成功返回True
        """

    @abstractmethod
    def stop_monitoring(self) -> bool:
        """停止监控

        Returns:
            bool: 停止成功返回True
        """

    @abstractmethod
    def get_metrics(self) -> dict[str, Any]:
        """获取监控指标

        Returns:
            Dict[str, Any]: 监控指标数据
        """


class UnifiedCacheManager(CacheInterface):
    """统一缓存管理器 - 实现统一的缓存清理功能"""

    def __init__(self):
        self._cache_providers = {}
        self._stats = {"total_clears": 0, "last_clear_time": None, "cache_types": []}

    def register_cache_provider(self, name: str, provider: CacheInterface) -> None:
        """注册缓存提供者

        Args:
            name: 提供者名称
            provider: 缓存提供者实例
        """
        self._cache_providers[name] = provider
        if name not in self._stats["cache_types"]:
            self._stats["cache_types"].append(name)

    def clear_cache(self, cache_type: str | None = None) -> bool:
        """清理缓存 - 统一入口

        Args:
            cache_type: 缓存类型，None表示清理所有

        Returns:
            bool: 清理成功返回True
        """
        try:
            success_count = 0
            total_count = 0

            if cache_type:
                # 清理指定类型的缓存
                if cache_type in self._cache_providers:
                    total_count = 1
                    if self._cache_providers[cache_type].clear_cache():
                        success_count = 1
                else:
                    logger.warning("未找到缓存类型: %s", cache_type)
                    return False
            else:
                # 清理所有缓存
                total_count = len(self._cache_providers)
                for name, provider in self._cache_providers.items():
                    try:
                        if provider.clear_cache():
                            success_count += 1
                    except Exception:
                        logger.warning("清理缓存失败 %s: {e}", name)

            # 更新统计
            self._stats["total_clears"] += success_count
            import time

            self._stats["last_clear_time"] = time.time()

            logger.info("缓存清理完成: %s/{total_count}", success_count)
            return success_count == total_count

        except Exception as e:
            logger.exception("统一缓存清理失败: %s", e)
            return False

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息

        Returns:
            Dict[str, Any]: 缓存统计信息
        """
        stats = dict(self._stats)

        # 获取各个提供者的统计
        provider_stats = {}
        for name, provider in self._cache_providers.items():
            try:
                provider_stats[name] = provider.get_cache_stats()
            except Exception as e:
                provider_stats[name] = {"error": str(e)}

        stats["providers"] = provider_stats
        return stats


class UnifiedStatusManager(StatusInterface):
    """统一状态管理器 - 实现统一的状态更新功能"""

    def __init__(self):
        self._status_providers = {}
        self._current_message = ""
        self._current_status = {}

    def register_status_provider(self, name: str, provider: StatusInterface) -> None:
        """注册状态提供者

        Args:
            name: 提供者名称
            provider: 状态提供者实例
        """
        self._status_providers[name] = provider

    def set_status_message(self, message: str, timeout: float | None = None) -> None:
        """设置状态消息 - 统一入口

        Args:
            message: 状态消息
            timeout: 超时时间（秒）
        """
        try:
            self._current_message = message

            # 广播到所有状态提供者
            for name, provider in self._status_providers.items():
                try:
                    provider.set_status_message(message, timeout)
                except Exception:
                    logger.warning("设置状态消息失败 %s: {e}", name)

        except Exception as e:
            logger.exception("统一状态设置失败: %s", e)

    def update_status_display(self, **kwargs) -> None:
        """更新状态显示 - 统一入口

        Args:
            **kwargs: 状态参数
        """
        try:
            self._current_status.update(kwargs)

            # 广播到所有状态提供者
            for name, provider in self._status_providers.items():
                try:
                    provider.update_status_display(**kwargs)
                except Exception:
                    logger.warning("更新状态显示失败 %s: {e}", name)

        except Exception as e:
            logger.exception("统一状态更新失败: %s", e)

    def get_current_status(self) -> dict[str, Any]:
        """获取当前状态

        Returns:
            Dict[str, Any]: 当前状态信息
        """
        return {
            "message": self._current_message,
            "status": dict(self._current_status),
            "providers": list(self._status_providers.keys()),
        }


# 全局统一接口实例
_unified_cache_manager = None
_unified_status_manager = None


def get_unified_cache_manager() -> UnifiedCacheManager:
    """获取统一缓存管理器实例

    Returns:
        UnifiedCacheManager: 统一缓存管理器
    """
    global _unified_cache_manager  # noqa: PLW0603  # 单例模式的合理使用
    if _unified_cache_manager is None:
        _unified_cache_manager = UnifiedCacheManager()
    return _unified_cache_manager


def get_unified_status_manager() -> UnifiedStatusManager:
    """获取统一状态管理器实例

    Returns:
        UnifiedStatusManager: 统一状态管理器
    """
    global _unified_status_manager  # noqa: PLW0603  # 单例模式的合理使用
    if _unified_status_manager is None:
        _unified_status_manager = UnifiedStatusManager()
    return _unified_status_manager


def clear_all_caches() -> bool:
    """清理所有缓存 - 便捷函数

    Returns:
        bool: 清理成功返回True
    """
    return get_unified_cache_manager().clear_cache()


def set_global_status(message: str, timeout: float | None = None) -> None:
    """设置全局状态消息 - 便捷函数

    Args:
        message: 状态消息
        timeout: 超时时间（秒）
    """
    get_unified_status_manager().set_status_message(message, timeout)
