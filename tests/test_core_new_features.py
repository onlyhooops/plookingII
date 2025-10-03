import os
import types
import subprocess

import pytest


def test_history_keep_folder_migration(tmp_path):
    from plookingII.core.history import TaskHistoryManager
    db_root = tmp_path / "root"
    db_root.mkdir()

    # 初始化并保存一次带旧 keep_folder 的数据
    m = TaskHistoryManager(str(db_root))
    # 直接写入数据库当前会话
    data = {
        "subfolders": [str(db_root / "A")],
        "current_subfolder_index": 0,
        "current_index": 0,
        "keep_folder": os.path.join(str(db_root), "保留"),
    }
    assert m.save_task_progress(data)

    # 读取并验证迁移为 "[根名] 精选"
    loaded = m.load_task_progress()
    assert loaded is not None
    expected = os.path.join(str(db_root), f"{db_root.name} 精选")
    assert loaded["keep_folder"].endswith(f"{db_root.name} 精选")
    assert loaded["keep_folder"] == expected


def test_selection_folder_migration_and_creation(tmp_path):
    from plookingII.ui.managers.folder_manager import FolderManager
    from plookingII.ui.window import MainWindow

    # 构造窗口与管理器
    win = MainWindow.alloc().init()
    fm = FolderManager(win)

    # base 目录包含旧“保留”
    base = tmp_path / "相册"
    old_keep = base / "保留"
    base.mkdir()
    old_keep.mkdir()

    # 触发 ensure 逻辑
    selection_dir = fm._ensure_selection_folder(str(base))
    assert selection_dir == os.path.join(str(base), f"{base.name} 精选")
    assert os.path.isdir(selection_dir)
    assert not os.path.exists(old_keep)  # 旧目录应被迁移/重命名


def test_scan_skips_selection_dir(tmp_path):
    from plookingII.ui.managers.folder_manager import FolderManager
    from plookingII.ui.window import MainWindow

    root = tmp_path / "根"
    root.mkdir()
    # 构造两个含图片的文件夹与一个“精选”
    (root / "A").mkdir()
    (root / "B").mkdir()
    (root / f"{root.name} 精选").mkdir()
    for d in (root / "A", root / "B"):
        with open(d / "1.jpg", "wb") as f:
            f.write(b"\x00")

    win = MainWindow.alloc().init()
    fm = FolderManager(win)
    subfolders = fm._scan_subfolders(str(root))
    # 不应包含 “根 精选”
    names = {os.path.basename(p) for p in subfolders}
    assert f"{root.name} 精选" not in names
    assert names == {"A", "B"}


def test_sibling_order_is_case_insensitive_ascending(tmp_path):
    from plookingII.ui.managers.folder_manager import FolderManager
    from plookingII.ui.window import MainWindow

    parent = tmp_path / "parent"
    parent.mkdir()
    for name in ["b_folder", "A_folder", "c_folder"]:
        (parent / name).mkdir()

    win = MainWindow.alloc().init()
    fm = FolderManager(win)
    parent_dir, siblings = fm._get_parent_sibling_folders(str(parent / "A_folder"))
    assert [os.path.basename(p) for p in siblings] == ["A_folder", "b_folder", "c_folder"]


def test_navigation_next_folder_only_in_single_folder_mode(tmp_path, monkeypatch):
    from plookingII.ui.managers.folder_manager import FolderManager
    from plookingII.ui.window import MainWindow

    root = tmp_path / "root"
    a = root / "A"
    b = root / "B"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    for d in (a, b):
        with open(d / "1.jpg", "wb") as f:
            f.write(b"\x00")

    win = MainWindow.alloc().init()
    fm = FolderManager(win)
    win._folder_manager = fm
    # 设置模拟的 image_manager
    win._image_manager = types.SimpleNamespace(
        sync_bidi_sequence=lambda seq: None,
        show_current_image=lambda: None,
        image_cache=types.SimpleNamespace(get_file_size_mb=lambda p: 1),
        _get_target_size_for_view=lambda scale_factor=2: (100, 100),
        _load_image_optimized=lambda *args, **kwargs: None,
    )
    # 加载根，设定为单文件夹模式（只包含根）
    # 强制 single_folder_mode 为 True 以验证限制逻辑
    fm.single_folder_mode = True
    win.subfolders = [str(a), str(b)]
    win.current_subfolder_index = 0
    win.current_folder = str(a)
    win.images = [str(a / "1.jpg")]
    win.current_index = 0

    # 跳到下一个
    fm.jump_to_next_folder()
    assert win.current_folder == str(b)


def test_titlebar_format_contains_resolution_and_size(tmp_path, monkeypatch):
    from plookingII.ui.controllers.status_bar_controller import StatusBarController
    from plookingII.ui.window import MainWindow

    # 生成一张小图片
    img_path = tmp_path / "img.png"
    try:
        from PIL import Image
        Image.new("RGB", (10, 20)).save(str(img_path), format="PNG")
    except Exception:
        # 若 PIL 不可用，跳过该测试
        pytest.skip("PIL not available in test env")

    win = MainWindow.alloc().init()
    sb = StatusBarController(win)
    # 伪造必要 UI 对象
    from AppKit import NSView, NSRect
    content = NSView.alloc().initWithFrame_(NSRect((0, 0), (800, 600)))
    win.setContentView_(content)
    sb.setup_ui(content, content.frame())

    # 捕获 setTitle_ 文本
    captured = {}

    def _set_title(text):
        captured["title"] = text

    win.setTitle_ = _set_title  # type: ignore

    current_folder = str(tmp_path)
    images = [str(img_path)]
    sb.update_status_display(current_folder, images, 0, ["f1"], 0)

    assert "| 1/1" in captured.get("title", "")
    assert os.path.basename(current_folder) in captured.get("title", "")
    assert os.path.basename(str(img_path)) in captured.get("title", "")
    # 分辨率与尺寸
    assert "10x20" in captured.get("title", "")
    assert "MB" in captured.get("title", "")


def test_lossless_jpeg_rotation_invokes_jpegtran(monkeypatch, tmp_path):
    from plookingII.core.image_rotation import ImageRotationProcessor

    # 生成一个假 JPEG 文件
    jpg = tmp_path / "a.jpg"
    jpg.write_bytes(b"not a real jpg but ok for subprocess call")

    # 伪造 which 与 subprocess 行为
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/jpegtran")

    class DummyCompleted:
        def __init__(self, returncode=0):
            self.returncode = returncode
            self.stdout = b""
            self.stderr = b""

    calls = {"count": 0}

    def fake_run(cmd, stdout=None, stderr=None):
        calls["count"] += 1
        # 第一次带 -perfect 认为失败，第二次成功
        if calls["count"] == 1 and "-perfect" in cmd:
            return DummyCompleted(returncode=1)
        return DummyCompleted(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    p = ImageRotationProcessor()
    ok = p._rotate_jpeg_lossless(str(jpg), "clockwise")
    assert ok is True
    # 至少调用了两次（一次 -perfect 失败回退）
    assert calls["count"] >= 2
