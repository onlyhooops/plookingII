"""
PlookingII 共享导入模块

提供应用程序所需的所有第三方库和系统框架的导入。
采用异常安全的设计，确保在缺少某些依赖时应用程序仍能正常运行。

主要功能：
    - 系统库导入：os, logging, threading, time 等基础库
    - 第三方库导入：PIL, psutil 等可选依赖
    - macOS 框架导入：AppKit, Foundation 等（按需）
    - 安全别名：提供下划线前缀的别名以避免命名冲突

设计原则：
    - 异常安全：所有导入都使用 try-except 包装
    - 向后兼容：为历史代码暴露所需符号
    - 模块化：按功能分组导入语句

Author: PlookingII Team
"""

import hashlib as hashlib  # 公开 hashlib  # noqa: PLC0414
import logging as logging  # 公开 logging 以供 "from ..imports import logging"  # noqa: PLC0414
import os
import shutil as shutil  # 公开 shutil 以供历史代码引入  # noqa: PLC0414
import subprocess as subprocess  # 公开 subprocess  # noqa: PLC0414
import threading as threading  # 公开 threading  # noqa: PLC0414
import time as time  # 公开 time  # noqa: PLC0414

# ==================== 第三方库导入 ====================
try:
    import psutil  # 系统监控库
except Exception:
    psutil = None

# ==================== 系统库别名 ====================
_os = os

# SQLite3 别名
try:
    import sqlite3

    _sqlite3 = sqlite3
except Exception:
    _sqlite3 = None

try:
    from PIL import Image  # Pillow 可选

    try:
        # 提升像素阈值，减少超大图告警（仍保留 DOS 保护）
        Image.MAX_IMAGE_PIXELS = 150_000_000
    except Exception:
        pass
except Exception:
    Image = None

# ==================== PyObjC 桥接 ====================
try:
    import objc as objc  # noqa: PLC0414

    _objc = objc
except Exception:
    objc = None
    _objc = None

# ==================== macOS 框架导入 ====================
QUARTZ_AVAILABLE = False

try:
    # AppKit 精选导入（避免 *）
    from AppKit import (
        NSApplication,
        NSColor,
        NSEventModifierFlagCommand,
        NSEventModifierFlagOption,
        NSFont,
        NSImage,
        NSMenu,
        NSMenuItem,
        NSObject,
        NSScreen,
        NSTextField,
        NSTimer,
        NSView,
        NSWindow,
    )

    # Foundation 精选导入
    from Foundation import (
        NSURL,
    )
    from Foundation import NSDefaultRunLoopMode as _NSDefaultRunLoopMode
    from Foundation import NSRunLoop as _NSRunLoop
    from Foundation import NSTimer as _NSTimer  # 别名保留

    QUARTZ_AVAILABLE = True
except Exception:
    QUARTZ_AVAILABLE = False
    # 在非 macOS 环境下，保持符号可用但不崩溃
    NSApplication = None
    NSWindow = None
    NSView = None
    NSImage = None
    NSColor = None
    NSTextField = None
    NSFont = None
    NSTimer = None
    NSObject = None
    NSScreen = None
    NSMenu = None
    NSMenuItem = None
    NSEventModifierFlagCommand = None
    NSEventModifierFlagOption = None
    NSURL = None
    _NSTimer = None
    _NSRunLoop = None
    _NSDefaultRunLoopMode = None

# Re-export commonly used helpers from submodules（按需延迟导入）
try:
    from .db.connection import connect_db  # noqa: F401
except Exception:
    pass

__all__ = [name for name in globals().keys() if not name.startswith("_")]
for name in (
    "_gc",
    "_sqlite3",
    "_cf",
    "_os",
    "_lru_cache",
    "_NSTimer",
    "_NSRunLoop",
    "_NSDefaultRunLoopMode",
    "_objc",
):
    if name not in __all__:
        __all__.append(name)
