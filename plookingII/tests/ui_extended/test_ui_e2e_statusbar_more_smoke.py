import sys

import pytest


@pytest.mark.skipif(sys.platform != "darwin", reason="仅在 macOS 下运行 UI 冒烟测试")
def test_status_bar_controller_methods_exist_smoke():
    from plookingII.ui.controllers.status_bar_controller import StatusBarController

    required_methods = [
        "set_status_message",
        "clear_status_message",
        "update_status_display",
        "update_zoom_slider",
        "update_session_data",
    ]

    for name in required_methods:
        assert hasattr(StatusBarController, name), f"StatusBarController 缺少方法: {name}"
