import os


def test_execute_pending_navigation_calls_jump_next():
    from plookingII.ui.controllers.navigation_controller import NavigationController

    class DummyWin:
        def __init__(self):
            self.images = ["a"]
            self.current_index = 0
            self.jump_next_called = False
        def _show_current_image_optimized(self):
            pass
        def _jump_to_next_folder(self):
            self.jump_next_called = True
        def _jump_to_previous_folder(self):
            pass

    win = DummyWin()
    nav = NavigationController(win)
    nav._pending_navigation = "right"
    nav.execute_pending_navigation()
    assert win.jump_next_called is True


def test_execute_rotation_safely_invokes_window_methods():
    from plookingII.ui.controllers.navigation_controller import NavigationController

    class DummyWin:
        def __init__(self):
            self.called = []
        def rotate_image_clockwise(self):
            self.called.append("cw")
        def rotate_image_counterclockwise(self):
            self.called.append("ccw")

    win = DummyWin()
    nav = NavigationController(win)
    # 调用私有方法，验证委托
    nav._execute_rotation_safely("clockwise")
    nav._execute_rotation_safely("counterclockwise")
    # 由于后台线程调用，简单宽松断言：方法最终应被调用
    import time
    time.sleep(0.05)
    assert "cw" in win.called and "ccw" in win.called


def test_move_with_retry_eventual_success(monkeypatch, tmp_path):
    from plookingII.ui.managers.operation_manager import OperationManager

    moves = {"n": 0}
    def fake_move(src, dst):
        moves["n"] += 1
        # 前两次失败，第三次成功
        if moves["n"] < 3:
            raise OSError("busy")
        # 创建目标父目录并模拟移动
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(src):
            os.replace(src, dst)

    monkeypatch.setattr("shutil.move", fake_move)

    class DummyWin:
        pass

    op = OperationManager(DummyWin())
    src = tmp_path / "a.txt"
    dst = tmp_path / "out" / "a.txt"
    src.write_text("1")
    ok = op._move_with_retry(str(src), str(dst), max_retries=3, initial_delay=0.001)
    assert ok is True
    assert moves["n"] == 3


def test_build_keep_target_path_numbering(tmp_path):
    from plookingII.ui.managers.operation_manager import OperationManager

    class DummyWin:
        def __init__(self, keep_folder, current_folder):
            self.keep_folder = str(keep_folder)
            self.current_folder = str(current_folder)
            self.root_folder = str(current_folder)
            self.images = []
            self.current_index = 0

    base = tmp_path / "Foo"
    base.mkdir()
    keep = base / f"{base.name} 精选"
    keep.mkdir()
    # 已存在同名文件
    (keep / "Foo img.jpg").write_text("x")

    op = OperationManager(DummyWin(keep, base))
    target, orig = op._build_keep_target_path(str(base / "img.jpg"))
    assert os.path.basename(target).startswith("Foo img_") and target.endswith(".jpg")
