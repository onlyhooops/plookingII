"""
ObjC 自动释放池管理工具（内存修复核心）

背景（见 docs/reports/memory-analysis-2026-08-18.md）：
PyObjC 桥接下，解码产生的 ObjC 中间对象（TIFF 数据、位图缓冲）默认进入
全局 NSAutoreleasePool，而该 pool 从不被 drain。Python 侧 del/gc/缓存驱逐
都无法触发 ObjC dealloc，导致解码内存（实测 160-255MB/张）永久残留、
长会话线性增长至数 GB。

修复：在解码/图像操作外围创建并立即 drain 局部 NSAutoreleasePool，
使中间对象随 pool drain 确定性回收（实测 15 张解码净增从 ~2.4GB 降至 0.3MB）。

用法:
    from ..core.autorelease import objc_autorelease_pool

    with objc_autorelease_pool():
        image = loader.load(path)   # 解码产生的中间对象随 with 块结束回收

注意:
    - 返回值（image）在 with 块结束后仍有效：图像对象本身被 Python 引用
      计数持有，drain 只回收自动释放的中间对象
    - 在无 AppKit 的环境（CI 单元测试）下自动降级为空操作
    - 嵌套 with 安全：各层独立创建/销毁自己的 pool
"""

import contextlib
import logging
from typing import Literal

logger = logging.getLogger(__name__)

try:
    from Foundation import NSAutoreleasePool

    _AUTORELEASE_AVAILABLE = True
except Exception:  # pragma: no cover - 非 macOS 环境
    NSAutoreleasePool = None  # type: ignore[assignment]
    _AUTORELEASE_AVAILABLE = False


class _AutoreleasePoolGuard:
    """NSAutoreleasePool 生命周期守卫（上下文管理器）"""

    __slots__ = ("_pool",)

    def __init__(self) -> None:
        self._pool = None

    def __enter__(self):
        if _AUTORELEASE_AVAILABLE:
            try:
                self._pool = NSAutoreleasePool.alloc().init()  # type: ignore[union-attr]
            except Exception:
                self._pool = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> Literal[False]:
        pool = self._pool
        self._pool = None
        if pool is not None:
            try:
                pool.drain()
            except Exception:
                logger.debug("NSAutoreleasePool drain 失败", exc_info=True)
        return False


@contextlib.contextmanager
def objc_autorelease_pool():
    """解码/图像操作使用的局部自动释放池上下文管理器

    用法:
        with objc_autorelease_pool():
            image = loader.load(path)
    """
    guard = _AutoreleasePoolGuard()
    with guard:
        yield


__all__ = ["objc_autorelease_pool"]
