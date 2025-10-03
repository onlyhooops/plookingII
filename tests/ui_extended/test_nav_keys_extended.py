def make_event(chars, modifiers=0, keycode=0):
    class E:
        def characters(self):
            return chars
        def modifierFlags(self):
            return modifiers
        def keyCode(self):
            return keycode
    return E()


def test_handle_key_event_cmd_arrows(monkeypatch):
    from plookingII.ui.controllers.navigation_controller import NavigationController
    from AppKit import NSEventModifierFlagCommand

    logs = {"skip": False, "undo": False}

    class Win:
        def skip_current_folder(self):
            logs["skip"] = True
        def undo_skip_folder(self):
            logs["undo"] = True

    nav = NavigationController(Win())
    assert nav.handle_key_event(make_event("\uf703", modifiers=NSEventModifierFlagCommand)) is True
    assert nav.handle_key_event(make_event("\uf702", modifiers=NSEventModifierFlagCommand)) is True
    assert logs["skip"] is True and logs["undo"] is True


def test_handle_key_event_esc_calls_exit(monkeypatch):
    from plookingII.ui.controllers.navigation_controller import NavigationController

    class Win:
        def __init__(self):
            self.called = False
        def exit_current_folder(self):
            self.called = True

    w = Win()
    nav = NavigationController(w)
    assert nav.handle_key_event(make_event("", keycode=53)) is True
    assert w.called is True
