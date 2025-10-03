import os



def test_selection_merge_conflict_numbering(tmp_path):
    from plookingII.ui.managers.folder_manager import FolderManager
    from plookingII.ui.window import MainWindow

    root = tmp_path / "相册"
    old_keep = root / "保留"
    selection = root / f"{root.name} 精选"
    root.mkdir()
    old_keep.mkdir()
    selection.mkdir()
    # 制造同名冲突文件与目录
    (old_keep / "dup.txt").write_text("old")
    (selection / "dup.txt").write_text("new")
    (old_keep / "dir").mkdir()
    (selection / "dir").mkdir()

    win = MainWindow.alloc().init()
    fm = FolderManager(win)
    out_dir = fm._ensure_selection_folder(str(root))
    assert out_dir == str(selection)
    # 旧文件应被迁移并自动编号
    names = set(os.listdir(selection))
    assert any(n.startswith("dup_") for n in names)
    assert any(n.startswith("dir_") for n in names)
    assert not os.path.exists(old_keep)


def test_lossless_jpeg_rotation_missing_tool(monkeypatch, tmp_path):
    from plookingII.core.image_rotation import ImageRotationProcessor

    jpg = tmp_path / "a.jpg"
    jpg.write_bytes(b"fake")

    # jpegtran 不存在
    monkeypatch.setattr("shutil.which", lambda name: None)
    p = ImageRotationProcessor()
    assert p._rotate_jpeg_lossless(str(jpg), "clockwise") is False


def test_status_timer_restore_current_path(tmp_path, monkeypatch):
    from plookingII.ui.controllers.status_bar_controller import StatusBarController
    from plookingII.ui.window import MainWindow
    from AppKit import NSView, NSRect

    folder = tmp_path / "F"
    folder.mkdir()

    win = MainWindow.alloc().init()
    content = NSView.alloc().initWithFrame_(NSRect((0, 0), (800, 600)))
    win.setContentView_(content)

    sb = StatusBarController(win)
    sb.setup_ui(content, content.frame())

    # 设置当前路径
    win.current_folder = str(folder)
    # 显示一次消息，随后调用 clear 恢复路径
    sb.set_status_message("hello")
    sb.clear_status_message()
    assert sb.center_status_label.stringValue() == str(folder)


def test_history_save_and_load_roundtrip(tmp_path):
    from plookingII.core.history import TaskHistoryManager

    root = tmp_path / "root"
    a = root / "A"
    root.mkdir()
    a.mkdir()

    m = TaskHistoryManager(str(root))
    data = {
        "subfolders": [str(a)],
        "current_subfolder_index": 0,
        "current_index": 0,
        "keep_folder": os.path.join(str(root), f"{root.name} 精选"),
        "current_folder": str(a),
    }
    assert m.save_task_progress(data)
    loaded = m.load_task_progress()
    assert loaded is not None
    assert loaded["subfolders"] == [str(a)]
    assert loaded["current_subfolder_index"] == 0
    assert loaded["current_index"] == 0
