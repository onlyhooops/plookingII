def make_event(chars, modifiers=0, keycode=None):
    class E:
        def characters(self):
            return chars
        def modifierFlags(self):
            return modifiers
        def keyCode(self):
            return keycode if keycode is not None else 0
    return E()


def test_handle_key_event_arrows_update_index():
    from plookingII.ui.controllers.navigation_controller import NavigationController
    # Use AppKit constants

    class DummyNavWin:
        def __init__(self):
            self.images = ["a", "b"]
            self.current_index = 0
            self._pending_navigation = None
        def _update_status_display_immediate(self):
            pass
        def executePendingNavigation_(self, t):
            pass

    win = DummyNavWin()
    nav = NavigationController(win)
    # Right arrow
    assert nav.handle_key_event(make_event("\uf703")) is True
    # schedule will set pending and timer, we directly call internal to simulate
    nav._update_pending_navigation("right")
    assert win.current_index == 1 or nav._pending_navigation == "jump_next"
    # Left arrow
    assert nav.handle_key_event(make_event("\uf702")) is True
    nav._update_pending_navigation("left")
    assert nav._pending_navigation in (None, "left", "jump_prev")


def test_handle_key_event_rotation_shortcuts_threaded():
    from plookingII.ui.controllers.navigation_controller import NavigationController
    from AppKit import NSEventModifierFlagCommand, NSEventModifierFlagOption

    class W:
        def __init__(self):
            self.called = []
        def rotate_image_clockwise(self):
            self.called.append("cw")
        def rotate_image_counterclockwise(self):
            self.called.append("ccw")

    w = W()
    nav = NavigationController(w)
    e1 = make_event("r", modifiers=(NSEventModifierFlagCommand | NSEventModifierFlagOption))
    e2 = make_event("l", modifiers=(NSEventModifierFlagCommand | NSEventModifierFlagOption))
    assert nav.handle_key_event(e1) is True
    assert nav.handle_key_event(e2) is True
    import time
    time.sleep(0.05)
    assert "cw" in w.called and "ccw" in w.called
