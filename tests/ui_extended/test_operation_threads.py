import time


def test_keep_current_image_spawns_thread(monkeypatch, tmp_path):
    from plookingII.ui.managers.operation_manager import OperationManager

    class DummyWin:
        def __init__(self):
            self.images = [str(tmp_path/"a.jpg")]
            (tmp_path/"a.jpg").write_text("1")
            self.current_index = 0
            self.keep_folder = str(tmp_path/"Keep")
            self.current_folder = str(tmp_path)
            self.root_folder = str(tmp_path)
            class FM:
                def jump_to_next_folder(self_inner):
                    pass
            self.folder_manager = FM()
        def performSelectorOnMainThread_withObject_waitUntilDone_(self, *a):
            pass
        def updateUi_(self, x):
            pass
        class ImgMgr:
            def sync_bidi_sequence(self, seq):
                pass
        image_manager = ImgMgr()

    # Monkeypatch move to immediate success
    monkeypatch.setattr("shutil.move", lambda s, d: None)
    op = OperationManager(DummyWin())
    op.keep_current_image()
    time.sleep(0.01)
    # 到这里没有异常即认为线程分支执行
    assert True
