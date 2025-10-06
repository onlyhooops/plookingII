"""
向后兼容层 - 图片加载策略

本文件提供向后兼容接口，将请求重定向到新的 loading 模块。

⚠️ 此文件已被重构：
   - 原文件: 1,118 行 (单一大文件)
   - 新模块: 945 行 (5个模块化文件)
   - 减少: 173 行 (15.5%)

新模块结构:
    plookingII/core/loading/
    ├── __init__.py          (接口导出)
    ├── strategies.py        (核心策略)
    ├── helpers.py           (辅助函数)
    ├── config.py            (配置管理)
    └── stats.py             (统计管理)

迁移指南:
    旧代码:
        from plookingII.core.optimized_loading_strategies import OptimizedLoadingStrategy
        loader = OptimizedLoadingStrategy()
        
    新代码 (推荐):
        from plookingII.core.loading import OptimizedStrategy
        loader = OptimizedStrategy()
        
    或使用工厂函数:
        from plookingII.core.loading import get_loader
        loader = get_loader('optimized')

Author: PlookingII Team
Date: 2025-10-06 (重构)
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# 重定向到新模块
from .loading import (
    AutoStrategy,
    LoadingConfig,
    LoadingStats,
    OptimizedStrategy,
    PreviewStrategy,
    create_loader,
    get_loader,
)

# 向后兼容的类名映射
OptimizedLoadingStrategy = OptimizedStrategy
PreviewLoadingStrategy = PreviewStrategy
AutoLoadingStrategy = AutoStrategy


class OptimizedLoadingStrategyFactory:
    """
    向后兼容的工厂类
    
    ⚠️ 已废弃: 建议使用 get_loader() 函数
    
    示例:
        # 旧代码
        loader = OptimizedLoadingStrategyFactory.create('optimized')
        
        # 新代码 (推荐)
        from plookingII.core.loading import get_loader
        loader = get_loader('optimized')
    """

    @staticmethod
    def create(strategy: str = "auto") -> Any:
        """创建加载器实例（兼容方法）

        Args:
            strategy: 策略名称 ('auto', 'optimized', 'preview')

        Returns:
            加载器实例
        """
        logger.warning(
            "OptimizedLoadingStrategyFactory.create() 已废弃，"
            "请使用 plookingII.core.loading.get_loader()"
        )
        return get_loader(strategy)

    @staticmethod
    def create_strategy(strategy: str = "auto") -> Any:
        """创建加载器实例（兼容别名）

        Args:
            strategy: 策略名称 ('auto', 'optimized', 'preview', 'fast')

        Returns:
            加载器实例
        """
        # fast 策略映射到 optimized
        if strategy == "fast":
            strategy = "optimized"
        return OptimizedLoadingStrategyFactory.create(strategy)

    @staticmethod
    def get_available_strategies() -> list[str]:
        """获取可用策略列表"""
        return ["auto", "optimized", "preview", "fast"]


# 导出所有兼容接口
__all__ = [
    # 新模块导出
    "AutoStrategy",
    "LoadingConfig",
    "LoadingStats",
    "OptimizedStrategy",
    "PreviewStrategy",
    "create_loader",
    "get_loader",
    # 兼容性导出
    "AutoLoadingStrategy",
    "OptimizedLoadingStrategy",
    "OptimizedLoadingStrategyFactory",
    "PreviewLoadingStrategy",
]

# 模块初始化日志
logger.info(
    "optimized_loading_strategies 兼容层已加载 - "
    "建议迁移到 plookingII.core.loading 新模块"
)
