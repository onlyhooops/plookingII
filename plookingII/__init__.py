"""
PlookingII - macOS 原生图片浏览器

一个专为摄影爱好者设计的高性能图片浏览器，采用现代化的 MVC 架构，
提供智能缓存、渐进式加载、文件夹管理等核心功能。

主要特性：
    - 智能图片浏览：支持多种格式，自适应缩放
    - 性能优化：多层缓存，后台处理，内存管理
    - 文件夹管理：批量浏览，智能跳过，历史记录
    - 快捷键操作：高效导航，一键保留，撤销操作

架构设计：
    - MVC 模式：清晰的职责分离
    - 模块化设计：低耦合，高内聚
    - 异常安全：完善的错误处理
    - 性能优化：智能缓存和后台处理

主要模块：
    - config: 配置管理
    - core: 核心功能
    - ui: 用户界面
    - services: 服务层
    - db: 数据存储
    - monitor: 系统监控

Author: PlookingII Team
Version: See plookingII.config.constants.VERSION
License: MIT
"""

# Package initializer that re-exports the original public API.
import logging
import sys

from .config.constants import (
    APP_NAME,
    AUTHOR,
    COPYRIGHT,
    HISTORY_FILE_NAME,
    ICON_ICNS,
    ICON_SVG,
    IMAGE_PROCESSING_CONFIG,
    MAX_CACHE_SIZE,
    MEMORY_THRESHOLD_MB,
    SUPPORTED_IMAGE_EXTS,
    VERSION,
)
from .imports import QUARTZ_AVAILABLE
from .imports import _objc as _objc_bridge

logger = logging.getLogger(APP_NAME)


def _safe_imports_for_env():
    mac_env = (sys.platform == "darwin") and bool(QUARTZ_AVAILABLE) and (_objc_bridge is not None)
    # always-safe modules
    for mod in (
        ".core.cache",
        ".core.functions",
        ".core.globals",
        ".core.history",
        ".core.image_processing",
        ".core.threading",
        ".db.connection",
        ".services.recent",
    ):
        try:
            __import__(__name__ + mod, fromlist=["*"])
        except Exception:
            logger.exception("Failed to import %s", mod)

    # mac-only modules
    if mac_env:
        for mod in (".app.main", ".ui.views", ".ui.window"):
            try:
                __import__(__name__ + mod, fromlist=["*"])
            except Exception:
                logger.exception("Failed to import %s", mod)


_safe_imports_for_env()
__all__ = [
    "APP_NAME",
    "AUTHOR",
    "COPYRIGHT",
    "HISTORY_FILE_NAME",
    "ICON_ICNS",
    "ICON_SVG",
    "IMAGE_PROCESSING_CONFIG",
    "MAX_CACHE_SIZE",
    "MEMORY_THRESHOLD_MB",
    "SUPPORTED_IMAGE_EXTS",
    "VERSION",
    "AdaptiveImageView",
    "AdvancedImageCache",
    "AppDelegate",
    "HybridImageProcessor",
    "MainWindow",
    "MemoryMonitor",
    "OverlayView",
    "RecentFoldersManager",
    "TaskHistoryManager",
    "_PatchedThreadPoolExecutor",
    "_env_int",
    "apply_safe_performance_tweaks",
    "build_menu",
    "connect_db",
    "force_gc",
    "simple_thumbnail_cache",
]
