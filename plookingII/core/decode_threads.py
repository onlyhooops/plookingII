"""
临时线程解码（v2.9.0 内存架构核心）

背景（实机验证，6000×4000 JPEG，见 docs/reports/display-pipeline-research-2026-08-20.md）：
- PyObjC 为每个线程懒创建 autorelease pool，且只在**线程退出**时 drain。
- 主线程与 ThreadPoolExecutor 常驻线程永不退出 → 池内解码缓冲永不释放
  （实测：主线程/常驻池线程 NSImage +10~11MB/张，线性增长）；
  **新建线程**解码 30 张仅 +0.1MB（线程退出 → 池被 drain）。
- 懒解码 CGImage 代理（ShouldCache=False）缓冲归 CGImage 自身、随包装器
  释放，任意线程安全 → 主加载路径无需本模块。

本模块：把一切**会产生 ObjC 对象**的辅助解码（NSImage 回退、内嵌预览
NSData 等）放入"新建线程、任务结束即退出"的执行模型：
- run_decode()：同步等待结果。返回的 ObjC 对象由 Python 包装器持有
  （retain），线程退出后依然有效，且随包装器释放可回收。
- run_decode_async()：异步 fire-and-forget，线程退出自动回收。

并发限制由调用方既有机制负责（BoundedExecutor 队列、_no_mpf_cache 去重
等），本模块不重复实现。线程创建开销 ~50µs，远小于解码耗时。

Author: PlookingII Team
"""

import logging
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def run_decode(fn: Callable[..., Any], *args, timeout: float | None = None, **kwargs) -> Any:
    """在新建线程中执行解码并等待结果（线程退出 → autorelease pool 被 drain）

    Args:
        fn: 解码函数（内部会创建 NSImage/NSData 等 ObjC 对象）
        timeout: 等待超时（秒）；超时返回 None（不中断解码线程）
        **kwargs: 透传给 fn

    Returns:
        fn(*args, **kwargs) 的结果；fn 抛异常时向调用方传播

    Note:
        返回的 ObjC 对象由 Python 包装器持有（PyObjC retain），线程退出
        后依然有效；调用方丢弃引用后即可回收（不再依赖池生命周期）。
    """
    box: dict[str, Any] = {"result": None, "error": None}

    def _worker() -> None:
        try:
            box["result"] = fn(*args, **kwargs)
        except BaseException as exc:  # 需向调用方原样传播
            box["error"] = exc

    thread = threading.Thread(target=_worker, name="decode-ephemeral", daemon=True)
    thread.start()
    thread.join(timeout)
    if box["error"] is not None:
        raise box["error"]
    return box["result"]


def run_decode_async(fn: Callable[..., Any], *args, **kwargs) -> threading.Thread:
    """在新建线程中异步执行解码（fire-and-forget，线程退出自动回收）

    Args:
        fn: 解码函数
        *args/**kwargs: 透传给 fn

    Returns:
        已启动的线程对象（供调用方在需要时 join 或检查存活）
    """

    def _worker() -> None:
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception("异步解码任务失败")

    thread = threading.Thread(target=_worker, name="decode-ephemeral", daemon=True)
    thread.start()
    return thread


__all__ = ["run_decode", "run_decode_async"]
