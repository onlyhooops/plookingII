def make_event(chars, modifiers=0, keycode=0):
    class E:
        def characters(self):
            return chars
        def modifierFlags(self):
            return modifiers
        def keyCode(self):
            return keycode
    return E()


def test_down_triggers_keep_current_image():
    from plookingII.ui.controllers.navigation_controller import NavigationController

    class W:
        def __init__(self):
            self.kept = False
        def keep_current_image(self):
            self.kept = True

    w = W()
    nav = NavigationController(w)
    assert nav.handle_key_event(make_event("\uf701")) is True
    assert w.kept is True


def test_up_triggers_overlay_toggle_path():
    from plookingII.ui.controllers.navigation_controller import NavigationController

    class W:
        def __init__(self):
            self.toggled = False
        # overlay toggle is a no-op currently; just ensure True returned

    nav = NavigationController(W())
    assert nav.handle_key_event(make_event("\uf700")) is True
