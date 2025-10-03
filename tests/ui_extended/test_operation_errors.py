def test_undo_keep_action_dst_missing(monkeypatch, tmp_path):
    from plookingII.ui.managers.operation_manager import OperationManager

    class Status:
        def __init__(self):
            self.last = ""
        def set_status_message(self, m):
            self.last = m

    class W:
        def __init__(self):
            self.status_bar_controller = Status()

    op = OperationManager(W())
    # 伪造操作栈
    op._keep_action_stack = [{"src": str(tmp_path/"a.jpg"), "dst": str(tmp_path/"Keep"/"a.jpg"), "orig_index": 0, "orig_folder": str(tmp_path), "orig_filename": "a.jpg", "active": True}]
    op.undo_keep_action()
    assert "不存在" in op.main_window.status_bar_controller.last
