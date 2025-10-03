def test_history_save_failure_is_handled(monkeypatch, tmp_path):
    from plookingII.core.history import TaskHistoryManager

    root = tmp_path / "root"
    root.mkdir()
    m = TaskHistoryManager(str(root))

    class DummyCursor:
        def execute(self, *a, **k):
            raise RuntimeError("db fail")
    class DummyConn:
        def cursor(self):
            return DummyCursor()
        def commit(self):
            pass
        def close(self):
            pass

    def bad_connect(path):
        return DummyConn()

    monkeypatch.setattr("plookingII.core.history.connect_db", bad_connect)
    ok = m.save_task_progress({"subfolders": [], "current_subfolder_index": 0, "current_index": 0, "keep_folder": ""})
    assert ok is False
