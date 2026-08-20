"""
进程内存看门狗（RSS 阈值触发 + 定期回收）

背景
----
主进程触发 ObjC 图像解码（NSImage.initWithContentsOfFile_ 等）时，解码
缓冲挂主线程全局 autorelease pool 且从不被 drain（PyObjC 结构性限制；
NSAutoreleasePool.drain / objc.autorelease_pool / objc.recycleAutoreleasePool
三种官方释放 API 均已实测崩溃，见 docs/reports/memory-analysis-*.md）。

因此长会话内存无法靠"立即释放解码缓冲"根治，只能从两方面收敛：
1. 加载侧少制造不可回收对象：优先懒解码 CGImage 代理（CF Create 语义，
   PyObjC 包装器释放即回收，见 strategies._load_small）；
2. 回收侧及时释放一切 Python 侧强引用：缓存 / HOT3 锁 / 预取双缓冲等。

本模块只负责两件纯逻辑的事（均可单测）：
- get_process_rss_mb(): 采样本进程 RSS（psutil → mach task_info → resource
  三级回退，无第三方依赖强制要求）；
- choose_cleanup_level(): 依据 RSS 与物理内存判定清理等级（纯函数）。

实际清理动作由调用方（ImageManager._run_rss_memory_check）执行。

等级设计（与 ImageManager 既有清理函数一一对应）：
- none       低于预防阈值，不动作
- preventive 缓存收缩至 ≤8 项
- moderate   缓存减半
- aggressive 缓存保留 ≤3 项（HOT3）+ 释放预取双缓冲
- emergency  缓存保留 ≤1 项 + 释放 HOT3 非当前项 + 清空小缓存 + gc

Author: PlookingII Team
"""

import ctypes
import logging
from typing import ClassVar

logger = logging.getLogger(__name__)

# 清理等级（字符串常量，避免魔法值散落调用方）
LEVEL_NONE = "none"
LEVEL_PREVENTIVE = "preventive"
LEVEL_MODERATE = "moderate"
LEVEL_AGGRESSIVE = "aggressive"
LEVEL_EMERGENCY = "emergency"

# 默认物理内存（MB）：无法探测时按 8GB 预算
_DEFAULT_PHYSICAL_MB = 8192.0

# 等级阈值默认值（相对物理内存的比例，另有绝对下限兜底，单位 MB）
_THRESHOLD_RATIOS = {
    LEVEL_PREVENTIVE: (0.30, 1024.0),
    LEVEL_MODERATE: (0.40, 1536.0),
    LEVEL_AGGRESSIVE: (0.55, 2048.0),
    LEVEL_EMERGENCY: (0.70, 3072.0),
}

# 配置键（可经 get_config 覆盖；None 表示自动按物理内存计算）
_CONFIG_KEYS = {
    LEVEL_PREVENTIVE: "memory.rss_preventive_mb",
    LEVEL_MODERATE: "memory.rss_moderate_mb",
    LEVEL_AGGRESSIVE: "memory.rss_aggressive_mb",
    LEVEL_EMERGENCY: "memory.rss_emergency_mb",
}


def _get_config(key: str, default):
    """惰性读取全局配置（模块级避免热路径依赖，失败静默回退默认值）"""
    try:
        from ..config.manager import get_config

        return get_config(key, default)
    except Exception:
        return default


def _rss_via_psutil() -> float | None:
    """psutil 采样（已声明依赖，优先使用）"""
    try:
        import psutil

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        return None


def _rss_via_mach_task_info() -> float | None:
    """macOS mach task_info 采样（无第三方依赖，纯 C ABI）"""
    try:
        libc = ctypes.CDLL(None, use_errno=True)

        # mach_task_self() 返回当前任务端口（x86_64/arm64 均为 uint32 端口号）
        mach_task_self = libc.mach_task_self_
        mach_task_self.restype = ctypes.c_uint32
        mach_task_self.argtypes = []
        task = mach_task_self()

        # struct mach_task_basic_info（mach/mach_types.defs 布局）
        class MachTaskBasicInfo(ctypes.Structure):
            _fields_: ClassVar = [
                ("virtual_size", ctypes.c_uint64),
                ("resident_size", ctypes.c_uint64),
                ("resident_size_max", ctypes.c_uint64),
                ("user_time", ctypes.c_uint64),
                ("system_time", ctypes.c_uint64),
                ("policy", ctypes.c_int32),
                ("suspend_count", ctypes.c_int32),
            ]

        MACH_TASK_BASIC_INFO = 20
        info = MachTaskBasicInfo()
        count = ctypes.c_uint(ctypes.sizeof(MachTaskBasicInfo) // ctypes.sizeof(ctypes.c_uint32))

        task_info = libc.task_info
        task_info.restype = ctypes.c_int32
        task_info.argtypes = [
            ctypes.c_uint32,
            ctypes.c_int32,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint),
        ]
        kr = task_info(task, MACH_TASK_BASIC_INFO, ctypes.byref(info), ctypes.byref(count))
        if kr == 0 and info.resident_size > 0:
            return info.resident_size / (1024 * 1024)
    except Exception:
        pass
    return None


def _rss_via_resource() -> float | None:
    """resource.ru_maxrss 兜底（峰值而非当前值，仅作保守估计）"""
    try:
        import resource

        # macOS 上 ru_maxrss 单位为字节；Linux 为 KB。此处目标平台为 macOS
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
    except Exception:
        return None


def get_process_rss_mb() -> float | None:
    """获取当前进程常驻内存（MB）

    采样顺序：psutil → mach task_info → resource.ru_maxrss。
    全部失败返回 None（调用方静默跳过本周期，不影响主流程）。

    Returns:
        float: RSS（MB），失败返回 None
    """
    for sampler in (_rss_via_psutil, _rss_via_mach_task_info, _rss_via_resource):
        rss = sampler()
        if rss is not None and rss > 0:
            return rss
    return None


def _physical_memory_via_psutil() -> float | None:
    try:
        import psutil

        return psutil.virtual_memory().total / (1024 * 1024)
    except Exception:
        return None


def _physical_memory_via_sysctl() -> float | None:
    """sysctl hw.memsize（无第三方依赖）"""
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        sysctlbyname = libc.sysctlbyname
        sysctlbyname.restype = ctypes.c_int32
        sysctlbyname.argtypes = [
            ctypes.c_char_p,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_size_t),
            ctypes.c_void_p,
            ctypes.c_size_t,
        ]

        size = ctypes.c_size_t(8)
        value = ctypes.c_uint64(0)
        kr = sysctlbyname(b"hw.memsize", ctypes.byref(value), ctypes.byref(size), None, 0)
        if kr == 0 and value.value > 0:
            return value.value / (1024 * 1024)
    except Exception:
        pass
    return None


def get_physical_memory_mb() -> float:
    """获取本机物理内存（MB），探测失败按 8GB 兜底"""
    for sampler in (_physical_memory_via_psutil, _physical_memory_via_sysctl):
        phys = sampler()
        if phys is not None and phys > 0:
            return phys
    return _DEFAULT_PHYSICAL_MB


def _threshold_for(level: str, physical_mb: float) -> float:
    """计算某等级阈值：优先读配置覆盖，否则 相对比例 + 绝对下限"""
    cfg_key = _CONFIG_KEYS.get(level)
    if cfg_key:
        override = _get_config(cfg_key, None)
        if isinstance(override, int | float) and override > 0:
            return float(override)
    ratio, floor = _THRESHOLD_RATIOS.get(level, (1.0, float("inf")))
    return max(physical_mb * ratio, floor)


def choose_cleanup_level(rss_mb: float, physical_mb: float | None = None) -> str:
    """依据 RSS 判定清理等级（纯函数，可单测）

    Args:
        rss_mb: 当前进程 RSS（MB）
        physical_mb: 物理内存（MB）；None 时自动探测

    Returns:
        LEVEL_NONE / LEVEL_PREVENTIVE / LEVEL_MODERATE /
        LEVEL_AGGRESSIVE / LEVEL_EMERGENCY
    """
    if rss_mb is None or rss_mb <= 0:
        return LEVEL_NONE
    if physical_mb is None or physical_mb <= 0:
        physical_mb = get_physical_memory_mb()

    # 由高到低逐级比较：emergency > aggressive > moderate > preventive
    for level in (LEVEL_EMERGENCY, LEVEL_AGGRESSIVE, LEVEL_MODERATE, LEVEL_PREVENTIVE):
        if rss_mb >= _threshold_for(level, physical_mb):
            return level
    return LEVEL_NONE


__all__ = [
    "LEVEL_AGGRESSIVE",
    "LEVEL_EMERGENCY",
    "LEVEL_MODERATE",
    "LEVEL_NONE",
    "LEVEL_PREVENTIVE",
    "choose_cleanup_level",
    "get_physical_memory_mb",
    "get_process_rss_mb",
]
