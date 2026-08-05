"""
弹窗展示工具

统一应用内 NSAlert 的展示策略，根治“应用不在最前端时模态弹窗无法聚焦、
按钮不可点、界面停摆”的问题：
1. 展示前激活应用并把窗口置前；
2. 优先使用附着窗口的 sheet（不阻塞整个应用）；
3. sheet 不可用时回退到模态弹窗。
"""

import logging

from AppKit import NSApplication

from ...config.constants import APP_NAME

logger = logging.getLogger(APP_NAME)


def activate_app_and_front(window=None) -> None:
    """激活应用并把主窗口置前（含最小化恢复）"""
    try:
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
    except Exception:
        pass

    if window is None:
        return
    try:
        window.makeKeyAndOrderFront_(None)
        window.orderFrontRegardless()
        if hasattr(window, "isMiniaturized") and window.isMiniaturized():
            window.deminiaturize_(None)
    except Exception:
        pass


def present_alert_sheet(alert, window=None, completion=None) -> bool:
    """以 sheet 形式展示弹窗。

    Args:
        alert: NSAlert 实例
        window: 宿主窗口；为 None 或展示失败时返回 False
        completion: 关闭回调（接收按钮结果），默认空操作

    Returns:
        bool: 是否成功以 sheet 展示
    """
    activate_app_and_front(window)
    if window is None:
        return False
    try:
        alert.beginSheetModalForWindow_completionHandler_(window, completion or (lambda response: None))
        return True
    except Exception:
        logger.debug("sheet 展示失败，回退到模态弹窗", exc_info=True)
        return False


def run_modal(alert, window=None) -> int:
    """激活置前后运行模态弹窗并返回按钮结果（0 表示异常/取消）"""
    activate_app_and_front(window)
    try:
        return alert.runModal()
    except Exception as e:
        logger.debug("模态弹窗运行失败: %s", e)
        return 0
