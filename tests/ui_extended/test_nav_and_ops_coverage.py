

def test_navigation_right_at_end_triggers_pending_jump(monkeypatch):
    from plookingII.ui.controllers.navigation_controller import NavigationController

    class DummyWin:
        def __init__(self):
            self.images = ["a", "b"]
            self.current_index = 1
            self._pending_navigation = None
        def _update_status_display_immediate(self):
            pass

    win = DummyWin()
    nav = NavigationController(win)
    nav._update_pending_navigation("right")
    assert nav._pending_navigation == "jump_next"


def test_navigation_left_at_start_triggers_pending_prev():
    from plookingII.ui.controllers.navigation_controller import NavigationController

    class DummyWin:
        def __init__(self):
            self.images = ["a", "b"]
            self.current_index = 0
            self._pending_navigation = None
        def _update_status_display_immediate(self):
            pass

    win = DummyWin()
    nav = NavigationController(win)
    nav._update_pending_navigation("left")
    assert nav._pending_navigation == "jump_prev"


def test_operation_manager_undo_keep_no_stack_message(monkeypatch):
    from plookingII.ui.managers.operation_manager import OperationManager
    class DummyStatus:
        def set_status_message(self, msg):
            self.last = msg
    class DummyWin:
        def __init__(self):
            self.status_bar_controller = DummyStatus()
    op = OperationManager(DummyWin())
    op.undo_keep_action()
    assert "无可撤回" in op.main_window.status_bar_controller.last


def test_rotate_current_image_no_images_sets_message(monkeypatch):
    from plookingII.ui.managers.operation_manager import OperationManager
    class DummyStatus:
        def set_status_message(self, msg):
            self.last = msg
    class DummyImgMgr:
        pass
    class DummyWin:
        def __init__(self):
            self.images = []
            self.current_index = 0
            self.status_bar_controller = DummyStatus()
            self.image_manager = DummyImgMgr()
    op = OperationManager(DummyWin())
    op.rotate_current_image("clockwise")
    assert "没有可旋转" in op.main_window.status_bar_controller.last
