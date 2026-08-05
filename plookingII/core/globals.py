"""
全局变量和常量模块

提供PlookingII应用程序的全局变量、常量和配置项。
这个模块作为配置系统的入口点，集中管理应用程序级别的设置。

主要功能：
    - 导入和重新导出核心配置常量
    - 提供全局可访问的应用程序设置
    - 确保配置的一致性和可维护性

使用方式：
    from plookingII.core.globals import *

    或

    from plookingII.core import globals

Author: PlookingII Team
"""

# 重新导出所有配置常量，确保全局可访问
# 这些常量包括：
# - APP_NAME: 应用程序名称
# - VERSION: 版本号
# - AUTHOR: 作者信息
# - COPYRIGHT: 版权信息
# - SUPPORTED_IMAGE_EXTS: 支持的图像格式
# - MAX_CACHE_SIZE: 最大缓存大小
# - MEMORY_THRESHOLD_MB: 内存阈值
# - IMAGE_PROCESSING_CONFIG: 图像处理配置
