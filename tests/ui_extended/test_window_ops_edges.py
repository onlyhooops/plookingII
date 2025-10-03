def test_goto_keep_folder_not_exist_shows_info(monkeypatch, tmp_path):
    from plookingII.ui.managers.operation_manager import OperationManager

    class DummyOp(OperationManager):
        def __init__(self):
            class W:
                def __init__(self):
                    self.root_folder = str(tmp_path / "Root")
            super().__init__(W())
            self.infos = []
        def _show_info_(self, msg):
            self.infos.append(msg)

    op = DummyOp()
    op.goto_keep_folder()
    # 根不存在或精选不存在时应提示
    assert op.infos and any("不存在" in m or "未选择" in m for m in op.infos)
