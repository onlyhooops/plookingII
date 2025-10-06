import os

from AppKit import NSApplication, NSApplicationActivationPolicyRegular

from plookingII.app.main import AppDelegate
from plookingII.config.constants import APP_NAME
from plookingII.core.error_handling import install_global_exception_hook, setup_error_logging
from plookingII.imports import logging

"""PlookingII 应用程序主入口模块

这是 PlookingII 图像查看器的主启动模块，负责应用程序的初始化、
日志配置和 macOS Cocoa 应用程序的启动流程。

主要功能：
    - 配置应用程序日志系统
    - 初始化 NSApplication 实例
    - 设置应用程序委托 (AppDelegate)
    - 启动 macOS 应用程序主循环

使用方式：
    python3 -m plookingII
    或
    python3 plookingII/__main__.py

Author: PlookingII Team
"""


def _configure_logging():
    """配置应用程序日志系统

    设置全局日志级别和格式，支持通过环境变量动态调整日志级别。
    同时优化第三方库的日志输出，避免过多的调试信息。

    环境变量：
        PLOOKINGII_LOG_LEVEL: 设置日志级别 (DEBUG, INFO, WARNING, ERROR)
                              默认为 INFO 级别

    日志格式：
        时间戳 [级别] 模块名: 消息内容
        例如: 2024-01-15 10:30:45,123 [INFO] plookingII.core.cache: 缓存初始化完成

    Note:
        - PIL 库的日志级别被设置为 WARNING，减少图像处理的调试信息
        - 异常安全：日志配置失败不会影响应用程序启动
    """
    # 从环境变量获取日志级别，默认为 INFO
    level_name = os.getenv(f"{APP_NAME.upper()}_LOG_LEVEL", "INFO")

    # 将字符串转换为 logging 模块的级别常量
    level = getattr(logging, level_name.upper(), logging.INFO)

    # 配置全局日志格式和级别
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # 初始化轮转日志与全局异常钩子
    try:
        setup_error_logging()
        install_global_exception_hook()
    except Exception:
        # 不影响主流程
        pass

    try:
        # 降低 PIL 库的日志级别，避免过多的图像处理调试信息
        logging.getLogger("PIL").setLevel(logging.WARNING)
    except Exception:
        # 忽略 PIL 日志配置失败，不影响应用程序启动
        pass


def main():
    """应用程序主函数

    执行 PlookingII 应用程序的完整启动流程，包括日志配置、
    Cocoa 应用程序初始化和主事件循环启动。

    启动流程：
        1. 配置日志系统
        2. 获取 NSApplication 共享实例
        3. 创建并设置应用程序委托
        4. 配置应用程序激活策略
        5. 激活应用程序窗口
        6. 启动主事件循环

    Note:
        - 主窗口的创建由 AppDelegate.applicationDidFinishLaunching_ 负责
        - 使用 NSApplicationActivationPolicyRegular 确保应用程序在 Dock 中可见
        - 异常安全：关键配置失败不会导致应用程序崩溃
    """
    # 第一步：配置应用程序日志系统
    _configure_logging()

    # 第二步：获取 macOS 应用程序的共享实例
    app = NSApplication.sharedApplication()

    # 第三步：创建应用程序委托实例并设置
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)

    # 注意：主窗口由 AppDelegate 在 applicationDidFinishLaunching_ 中创建并展示
    # 这符合 macOS 应用程序的标准生命周期管理模式

    try:
        # 第四步：设置应用程序激活策略为常规模式
        # NSApplicationActivationPolicyRegular: 应用程序在 Dock 中可见，可以有菜单栏
        app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    except Exception:
        # 忽略激活策略设置失败，使用默认策略
        pass

    # 第五步：激活应用程序，忽略其他应用程序的状态
    # 确保应用程序窗口显示在最前面
    app.activateIgnoringOtherApps_(True)

    # 第六步：启动应用程序主事件循环
    # 这个调用会阻塞，直到应用程序退出
    app.run()


if __name__ == "__main__":
    # 当模块作为主程序运行时，启动应用程序
    # 支持以下启动方式：
    # - python3 -m plookingII
    # - python3 plookingII/__main__.py
    main()
