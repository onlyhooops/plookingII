"""
测试 ui/managers/folder_manager.py

测试文件夹管理器功能，包括：
- 初始化和配置
- 文件夹扫描
- 导航功能
- 历史记录管理
- 最近文件夹管理
"""

from unittest.mock import MagicMock, patch

import pytest

from plookingII.ui.managers.folder_manager import FolderManager

# ==================== 夹具（Fixtures） ====================


@pytest.fixture
def mock_window():
    """创建模拟窗口"""
    window = MagicMock()
    window.root_folder = None
    window.subfolders = []
    window.current_folder = None
    window.current_subfolder_index = 0
    window.images = []
    window.current_index = 0
    window.image_view = MagicMock()
    window.image_seq_label = MagicMock()
    window.folder_seq_label = MagicMock()
    window.updateRecentMenu_ = MagicMock()
    return window


@pytest.fixture
def folder_manager(mock_window):
    """创建文件夹管理器实例"""
    with patch("plookingII.ui.managers.folder_manager.RecentFoldersManager"):
        return FolderManager(mock_window)


@pytest.fixture
def temp_folder_with_images(tmp_path):
    """创建包含测试图片的临时文件夹"""
    # 创建主文件夹
    main_folder = tmp_path / "test_photos"
    main_folder.mkdir()

    # 创建子文件夹
    subfolder1 = main_folder / "folder1"
    subfolder1.mkdir()
    (subfolder1 / "img1.jpg").touch()
    (subfolder1 / "img2.jpg").touch()

    subfolder2 = main_folder / "folder2"
    subfolder2.mkdir()
    (subfolder2 / "img3.png").touch()

    return str(main_folder)


# ==================== 初始化测试 ====================


class TestFolderManagerInit:
    """测试FolderManager初始化"""

    @patch("plookingII.ui.managers.folder_manager.RecentFoldersManager")
    def test_init_basic(self, mock_recent_manager_class, mock_window):
        """测试基本初始化"""
        mock_recent_manager = MagicMock()
        mock_recent_manager_class.return_value = mock_recent_manager
        mock_recent_manager.cleanup_invalid_entries.return_value = 0

        manager = FolderManager(mock_window)

        assert manager.main_window == mock_window
        assert manager.task_history_manager is None
        assert manager.recent_folders_manager == mock_recent_manager
        assert manager.reverse_folder_order is False
        assert manager.single_folder_mode is False

    @patch("plookingII.ui.managers.folder_manager.RecentFoldersManager")
    def test_init_cleanup_invalid_entries(self, mock_recent_manager_class, mock_window):
        """测试初始化时清理无效条目"""
        mock_recent_manager = MagicMock()
        mock_recent_manager_class.return_value = mock_recent_manager
        mock_recent_manager.cleanup_invalid_entries.return_value = 5

        manager = FolderManager(mock_window)

        mock_recent_manager.cleanup_invalid_entries.assert_called_once()

    @patch("plookingII.ui.managers.folder_manager.RecentFoldersManager")
    def test_init_cleanup_exception(self, mock_recent_manager_class, mock_window):
        """测试初始化时清理异常"""
        mock_recent_manager = MagicMock()
        mock_recent_manager_class.return_value = mock_recent_manager
        mock_recent_manager.cleanup_invalid_entries.side_effect = Exception("Cleanup failed")

        # 应该不抛出异常
        try:
            manager = FolderManager(mock_window)
            assert manager is not None
        except Exception:
            pytest.fail("初始化时清理异常应该被捕获")


# ==================== 文件夹扫描测试 ====================


class TestFolderScanning:
    """测试文件夹扫描"""

    def test_scan_subfolders_method_exists(self, folder_manager):
        """测试_scan_subfolders方法存在"""
        assert hasattr(folder_manager, "_scan_subfolders")
        assert callable(folder_manager._scan_subfolders)

    def test_dir_contains_images_method_exists(self, folder_manager):
        """测试_dir_contains_images方法存在"""
        assert hasattr(folder_manager, "_dir_contains_images")
        assert callable(folder_manager._dir_contains_images)

    def test_gather_directories_to_scan_method_exists(self, folder_manager):
        """测试_gather_directories_to_scan方法存在"""
        assert hasattr(folder_manager, "_gather_directories_to_scan")
        assert callable(folder_manager._gather_directories_to_scan)

    @patch("plookingII.ui.managers.folder_manager.SUPPORTED_IMAGE_EXTS", (".jpg", ".png"))
    @patch("plookingII.core.file_info_batch_loader.get_file_info_loader")
    def test_dir_contains_images_true(self, mock_get_loader, folder_manager):
        """测试目录包含图片"""
        from unittest.mock import MagicMock

        from plookingII.core.file_info_batch_loader import FileInfo

        # Mock loader 返回包含图片的文件信息
        mock_loader = MagicMock()
        mock_loader.scan_directory.return_value = [
            FileInfo(path="/test/folder/img1.jpg", extension="jpg", exists=True, is_file=True),
            FileInfo(path="/test/folder/img2.png", extension="png", exists=True, is_file=True),
        ]
        mock_get_loader.return_value = mock_loader

        result = folder_manager._dir_contains_images("/test/folder", (".jpg", ".png"))

        assert result is True

    @patch("plookingII.ui.managers.folder_manager.os.listdir")
    def test_dir_contains_images_false(self, mock_listdir, folder_manager):
        """测试目录不包含图片"""
        mock_listdir.return_value = ["doc.txt", "readme.md"]

        result = folder_manager._dir_contains_images("/test/folder", (".jpg", ".png"))

        assert result is False

    @patch("plookingII.ui.managers.folder_manager.os.listdir")
    def test_dir_contains_images_exception(self, mock_listdir, folder_manager):
        """测试目录扫描异常"""
        mock_listdir.side_effect = PermissionError("Access denied")

        result = folder_manager._dir_contains_images("/test/folder", (".jpg", ".png"))

        assert result is False


# ==================== 导航功能测试 ====================


class TestNavigation:
    """测试导航功能"""

    def test_jump_to_next_folder_method_exists(self, folder_manager):
        """测试jump_to_next_folder方法存在"""
        assert hasattr(folder_manager, "jump_to_next_folder")
        assert callable(folder_manager.jump_to_next_folder)

    def test_jump_to_previous_folder_method_exists(self, folder_manager):
        """测试jump_to_previous_folder方法存在"""
        assert hasattr(folder_manager, "jump_to_previous_folder")
        assert callable(folder_manager.jump_to_previous_folder)

    def test_load_current_subfolder_method_exists(self, folder_manager):
        """测试load_current_subfolder方法存在"""
        assert hasattr(folder_manager, "load_current_subfolder")
        assert callable(folder_manager.load_current_subfolder)

    def test_skip_current_folder_method_exists(self, folder_manager):
        """测试skip_current_folder方法存在"""
        assert hasattr(folder_manager, "skip_current_folder")
        assert callable(folder_manager.skip_current_folder)

    def test_undo_skip_folder_method_exists(self, folder_manager):
        """测试undo_skip_folder方法存在"""
        assert hasattr(folder_manager, "undo_skip_folder")
        assert callable(folder_manager.undo_skip_folder)


# ==================== 历史记录管理测试 ====================


class TestHistoryManagement:
    """测试历史记录管理"""

    def test_task_history_manager_initially_none(self, folder_manager):
        """测试任务历史管理器初始为None"""
        assert folder_manager.task_history_manager is None

    def test_save_task_progress_immediate_is_single_source(self, folder_manager):
        """进度保存已单源化：FolderManager 仅保留立即保存路径，
        节流/异步保存统一由 HistoryManager 负责（移除重复实现后）"""
        assert hasattr(folder_manager, "_save_task_progress_immediate")
        assert callable(folder_manager._save_task_progress_immediate)
        # 旧的重复节流实现已移除，避免双轨保存
        assert not hasattr(folder_manager, "_save_task_progress")
        assert not hasattr(folder_manager, "_async_save_progress")

    def test_save_task_progress_immediate_method_exists(self, folder_manager):
        """测试_save_task_progress_immediate方法存在"""
        assert hasattr(folder_manager, "_save_task_progress_immediate")
        assert callable(folder_manager._save_task_progress_immediate)

    def test_validate_task_history_method_exists(self, folder_manager):
        """测试_validate_task_history方法存在"""
        assert hasattr(folder_manager, "_validate_task_history")
        assert callable(folder_manager._validate_task_history)

    def test_clear_history_method_exists(self, folder_manager):
        """测试clear_history方法存在"""
        assert hasattr(folder_manager, "clear_history")
        assert callable(folder_manager.clear_history)


# ==================== 最近文件夹管理测试 ====================


class TestRecentFolders:
    """测试最近文件夹管理"""

    def test_recent_folders_manager_initialized(self, folder_manager):
        """测试最近文件夹管理器已初始化"""
        assert folder_manager.recent_folders_manager is not None

    def test_get_recent_folders_method_exists(self, folder_manager):
        """测试get_recent_folders方法存在"""
        assert hasattr(folder_manager, "get_recent_folders")
        assert callable(folder_manager.get_recent_folders)

    def test_add_recent_folder_method_exists(self, folder_manager):
        """测试add_recent_folder方法存在"""
        assert hasattr(folder_manager, "add_recent_folder")
        assert callable(folder_manager.add_recent_folder)

    def test_clear_recent_folders_method_exists(self, folder_manager):
        """测试clear_recent_folders方法存在"""
        assert hasattr(folder_manager, "clear_recent_folders")
        assert callable(folder_manager.clear_recent_folders)

    def test_get_recent_folders(self, folder_manager):
        """测试获取最近文件夹"""
        folder_manager.recent_folders_manager.get.return_value = ["/folder1", "/folder2"]

        result = folder_manager.get_recent_folders()

        assert result == ["/folder1", "/folder2"]
        folder_manager.recent_folders_manager.get.assert_called_once()

    def test_add_recent_folder(self, folder_manager):
        """测试添加最近文件夹"""
        folder_manager.add_recent_folder("/test/folder")

        folder_manager.recent_folders_manager.add.assert_called_with("/test/folder")

    def test_clear_recent_folders(self, folder_manager):
        """测试清空最近文件夹"""
        folder_manager.clear_recent_folders()

        folder_manager.recent_folders_manager.clear.assert_called_once()


# ==================== 文件夹顺序测试 ====================


class TestFolderOrder:
    """测试文件夹顺序"""

    def test_reverse_folder_order_default(self, folder_manager):
        """测试倒序标志默认值"""
        assert folder_manager.reverse_folder_order is False

    def test_set_reverse_folder_order_method_exists(self, folder_manager):
        """测试set_reverse_folder_order方法存在"""
        assert hasattr(folder_manager, "set_reverse_folder_order")
        assert callable(folder_manager.set_reverse_folder_order)

    def test_set_reverse_folder_order_true(self, folder_manager):
        """测试设置倒序为True"""
        folder_manager.set_reverse_folder_order(True)

        assert folder_manager.reverse_folder_order is True

    def test_set_reverse_folder_order_false(self, folder_manager):
        """测试设置倒序为False"""
        folder_manager.reverse_folder_order = True
        folder_manager.set_reverse_folder_order(False)

        assert folder_manager.reverse_folder_order is False


# ==================== 单文件夹模式测试 ====================


class TestSingleFolderMode:
    """测试单文件夹模式"""

    def test_single_folder_mode_default(self, folder_manager):
        """测试单文件夹模式默认值"""
        assert folder_manager.single_folder_mode is False

    def test_single_folder_mode_attribute(self, folder_manager):
        """测试single_folder_mode属性存在"""
        assert hasattr(folder_manager, "single_folder_mode")


# ==================== 跳过文件夹历史测试 ====================


class TestSkipFolderHistory:
    """测试跳过文件夹历史"""

    def test_skipped_folders_history_initialized(self, folder_manager):
        """测试跳过文件夹历史已初始化"""
        assert hasattr(folder_manager, "_skipped_folders_history")
        assert folder_manager._skipped_folders_history == []

    def test_max_skip_history_value(self, folder_manager):
        """测试最大跳过历史值"""
        assert folder_manager._max_skip_history == 10


# ==================== 工作会话测试 ====================


class TestWorkSession:
    """测试工作会话"""

    def test_start_work_session_method_exists(self, folder_manager):
        """测试_start_work_session方法存在"""
        assert hasattr(folder_manager, "_start_work_session")
        assert callable(folder_manager._start_work_session)

    def test_end_work_session_method_exists(self, folder_manager):
        """测试_end_work_session方法存在"""
        assert hasattr(folder_manager, "_end_work_session")
        assert callable(folder_manager._end_work_session)


# ==================== 选择文件夹测试 ====================


class TestSelectionFolder:
    """测试选择文件夹"""

    def test_compute_selection_folder_name_method_exists(self, folder_manager):
        """测试_compute_selection_folder_name方法存在"""
        assert hasattr(folder_manager, "_compute_selection_folder_name")
        assert callable(folder_manager._compute_selection_folder_name)

    def test_ensure_selection_folder_method_exists(self, folder_manager):
        """测试_ensure_selection_folder方法存在"""
        assert hasattr(folder_manager, "_ensure_selection_folder")
        assert callable(folder_manager._ensure_selection_folder)


# ==================== 加载方法测试 ====================


class TestLoadMethods:
    """测试加载方法"""

    def test_load_images_from_root_method_exists(self, folder_manager):
        """测试load_images_from_root方法存在"""
        assert hasattr(folder_manager, "load_images_from_root")
        assert callable(folder_manager.load_images_from_root)

    def test_load_images_without_history_dialog_method_exists(self, folder_manager):
        """测试_load_images_without_history_dialog方法存在"""
        assert hasattr(folder_manager, "_load_images_without_history_dialog")
        assert callable(folder_manager._load_images_without_history_dialog)

    def test_load_folder_images_method_exists(self, folder_manager):
        """测试_load_folder_images方法存在"""
        assert hasattr(folder_manager, "_load_folder_images")
        assert callable(folder_manager._load_folder_images)


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    @patch("plookingII.ui.managers.folder_manager.RecentFoldersManager")
    def test_complete_lifecycle(self, mock_recent_manager_class, mock_window):
        """测试完整生命周期"""
        mock_recent_manager = MagicMock()
        mock_recent_manager_class.return_value = mock_recent_manager
        mock_recent_manager.cleanup_invalid_entries.return_value = 0
        mock_recent_manager.get.return_value = []

        # 1. 创建管理器
        manager = FolderManager(mock_window)
        assert manager.main_window == mock_window

        # 2. 添加最近文件夹
        manager.add_recent_folder("/test/folder1")
        mock_recent_manager.add.assert_called_with("/test/folder1")

        # 3. 获取最近文件夹
        manager.get_recent_folders()
        mock_recent_manager.get.assert_called()

        # 4. 清空最近文件夹
        manager.clear_recent_folders()
        mock_recent_manager.clear.assert_called()

    def test_folder_order_workflow(self, folder_manager):
        """测试文件夹顺序工作流"""
        # 1. 初始为正序
        assert folder_manager.reverse_folder_order is False

        # 2. 设置为倒序
        folder_manager.set_reverse_folder_order(True)
        assert folder_manager.reverse_folder_order is True

        # 3. 恢复正序
        folder_manager.set_reverse_folder_order(False)
        assert folder_manager.reverse_folder_order is False


# ==================== 边界情况测试 ====================


class TestEdgeCases:
    """测试边界情况"""

    @patch("plookingII.ui.managers.folder_manager.os.listdir")
    def test_dir_contains_images_empty_folder(self, mock_listdir, folder_manager):
        """测试空文件夹"""
        mock_listdir.return_value = []

        result = folder_manager._dir_contains_images("/empty/folder", (".jpg", ".png"))

        assert result is False

    def test_add_recent_folder_multiple_times(self, folder_manager):
        """测试多次添加同一文件夹"""
        folder_manager.add_recent_folder("/test/folder")
        folder_manager.add_recent_folder("/test/folder")
        folder_manager.add_recent_folder("/test/folder")

        # 应该调用3次
        assert folder_manager.recent_folders_manager.add.call_count == 3


# ==================== 属性测试 ====================


class TestAttributes:
    """测试属性"""

    def test_all_required_attributes_exist(self, folder_manager):
        """测试所有必需属性存在"""
        required_attrs = [
            "main_window",
            "task_history_manager",
            "recent_folders_manager",
            "reverse_folder_order",
            "single_folder_mode",
            "_skipped_folders_history",
            "_max_skip_history",
        ]

        for attr in required_attrs:
            assert hasattr(folder_manager, attr), f"Missing attribute: {attr}"


# ==================== 异步文件夹跳转测试（P1-5） ====================


class TestAsyncFolderLoad:
    """测试文件夹跳转后台异步加载"""

    def test_start_async_folder_load_applies(self, folder_manager, tmp_path):
        """后台加载目标文件夹图片并应用到主窗口状态"""
        import time

        main = tmp_path / "root"
        (main / "f1").mkdir(parents=True)
        (main / "f2").mkdir()
        img = main / "f2" / "a.jpg"
        img.touch()

        folder_manager.main_window.subfolders = [str(main / "f1"), str(main / "f2")]
        folder_manager.main_window.current_subfolder_index = 0
        folder_manager.main_window.current_folder = str(main / "f1")

        # 测试环境无 RunLoop，将 post_to_main 改为同步执行
        folder_manager._post_to_main = lambda f: f()
        folder_manager._start_async_folder_load(1, +1, start_from_last=False)

        deadline = time.time() + 5
        while time.time() < deadline and folder_manager.main_window.current_subfolder_index != 1:
            time.sleep(0.02)
        assert folder_manager.main_window.current_subfolder_index == 1
        assert folder_manager.main_window.current_folder == str(main / "f2")
        assert folder_manager.main_window.images == [str(img)]
        assert folder_manager.main_window.current_index == 0

    def test_start_async_folder_load_start_from_last(self, folder_manager, tmp_path):
        """向前跳转时从最后一张图片开始"""
        import time

        main = tmp_path / "root"
        (main / "f1").mkdir(parents=True)
        (main / "f2").mkdir()
        (main / "f1" / "a.jpg").touch()
        (main / "f1" / "b.jpg").touch()
        (main / "f2" / "a.jpg").touch()
        (main / "f2" / "b.jpg").touch()

        folder_manager.main_window.subfolders = [str(main / "f1"), str(main / "f2")]
        folder_manager.main_window.current_subfolder_index = 1
        folder_manager.main_window.current_folder = str(main / "f2")

        folder_manager._post_to_main = lambda f: f()
        folder_manager._start_async_folder_load(0, -1, start_from_last=True)

        deadline = time.time() + 5
        while time.time() < deadline and folder_manager.main_window.current_subfolder_index != 0:
            time.sleep(0.02)
        assert folder_manager.main_window.current_index == 1  # 最后一张

    def test_jump_to_next_folder_uses_async(self, folder_manager):
        """jump_to_next_folder 走异步加载路径"""
        folder_manager.main_window.subfolders = ["/a", "/b"]
        folder_manager.main_window.current_subfolder_index = 0
        with patch.object(folder_manager, "_start_async_folder_load") as m:
            folder_manager.jump_to_next_folder()
        m.assert_called_once_with(1, direction=+1, start_from_last=False)

    def test_jump_to_previous_folder_uses_async_reverse(self, folder_manager):
        """倒序浏览时 jump_to_previous_folder 的索引与方向正确"""
        folder_manager.main_window.subfolders = ["/a", "/b", "/c"]
        folder_manager.main_window.current_subfolder_index = 1
        folder_manager.reverse_folder_order = True
        with patch.object(folder_manager, "_start_async_folder_load") as m:
            folder_manager.jump_to_previous_folder()
        m.assert_called_once_with(2, direction=+1, start_from_last=True)


class TestNeighborFolderPrefetch:
    """测试相邻文件夹预扫描（P1-5）"""

    def test_prefetch_neighbor_folder_lists(self, folder_manager, tmp_path):
        """后台预热前后相邻文件夹图片列表"""
        import time

        main = tmp_path / "root"
        for name in ("f1", "f2", "f3"):
            (main / name).mkdir(parents=True)
        folder_manager.main_window.subfolders = [str(main / "f1"), str(main / "f2"), str(main / "f3")]
        folder_manager.main_window.current_subfolder_index = 1

        with patch.object(folder_manager, "_load_folder_images") as load:
            folder_manager._prefetch_neighbor_folder_lists()
            deadline = time.time() + 5
        while time.time() < deadline and load.call_count < 2:
            time.sleep(0.02)
        assert load.call_count == 2


class TestHistoryRestoreFastPath:
    """回归测试：两阶段快速扫描路径必须保留历史记录的保存与恢复能力

    此前快速路径（根目录直系子文件夹含图片）跳过了历史恢复对话框，
    也没有绑定 task_history_manager，导致浏览历史始终从第一张图片开始。
    """

    @patch("plookingII.ui.managers.folder_manager.FolderManager._show_task_history_restore_dialog")
    @patch("plookingII.ui.managers.folder_manager.TaskHistoryManager")
    def test_load_root_async_fast_path_restores_history(
        self, mock_thm_class, mock_show_dialog, folder_manager, tmp_path
    ):
        """存在历史记录时，快速路径应弹出恢复对话框并绑定历史管理器"""
        import time

        root = tmp_path / "root"
        (root / "f1").mkdir(parents=True)
        (root / "f1" / "a.jpg").touch()

        history_data = {
            "subfolders": [str(root / "f1")],
            "current_subfolder_index": 0,
            "current_index": 1,
            "keep_folder": "",
        }
        mock_thm = mock_thm_class.return_value
        mock_thm.load_task_progress.return_value = history_data

        # 测试环境无 RunLoop，将 post_to_main 改为同步执行
        folder_manager._post_to_main = staticmethod(lambda f: f())
        folder_manager.load_images_from_root(str(root))

        deadline = time.time() + 5
        while time.time() < deadline and not mock_show_dialog.called:
            time.sleep(0.02)

        mock_show_dialog.assert_called_once_with(history_data)
        # 快速路径也必须绑定任务历史管理器，否则后续进度无法保存
        assert folder_manager.task_history_manager is mock_thm

    @patch("plookingII.ui.managers.folder_manager.TaskHistoryManager")
    def test_load_root_async_fast_path_saves_progress(
        self, mock_thm_class, folder_manager, tmp_path
    ):
        """无历史记录时，快速路径应正常加载并立即保存进度"""
        import time

        root = tmp_path / "root"
        (root / "f1").mkdir(parents=True)
        (root / "f1" / "a.jpg").touch()

        mock_thm = mock_thm_class.return_value
        mock_thm.load_task_progress.return_value = None

        folder_manager._post_to_main = staticmethod(lambda f: f())
        folder_manager.load_images_from_root(str(root))

        deadline = time.time() + 5
        while time.time() < deadline and not mock_thm.save_task_progress.called:
            time.sleep(0.02)

        assert folder_manager.task_history_manager is mock_thm
        mock_thm.save_task_progress.assert_called()
        assert folder_manager.main_window.current_subfolder_index == 0


class TestHistoryRestoreDialog:
    """回归测试：历史恢复确认弹窗的展示方式

    此前使用应用级 runModal 模态弹窗，应用不在最前端时弹窗无法获得焦点，
    按钮无法点选且阻塞整个应用交互，只能强杀进程。
    修复后应优先使用附着在主窗口上的 sheet，并先激活应用、置前主窗口。
    """

    @staticmethod
    def _history_data():
        return {
            "subfolders": ["/a", "/b"],
            "current_subfolder_index": 1,
            "current_index": 2,
            "keep_folder": "",
        }

    @patch("plookingII.ui.managers.folder_manager.NSApplication")
    @patch("plookingII.ui.managers.folder_manager.NSAlert")
    @patch("plookingII.ui.managers.folder_manager.get_ui_string")
    def test_uses_sheet_instead_of_app_modal(
        self, mock_get_ui_string, mock_ns_alert, mock_ns_app, folder_manager
    ):
        """优先使用 sheet 模式，而非阻塞整个应用的应用级模态"""
        mock_get_ui_string.side_effect = lambda *args, **kwargs: args[-1]
        mock_alert = MagicMock()
        mock_ns_alert.alloc.return_value.init.return_value = mock_alert

        folder_manager._show_task_history_restore_dialog(self._history_data())

        mock_alert.runModal.assert_not_called()
        mock_alert.beginSheetModalForWindow_completionHandler_.assert_called_once()

    @patch("plookingII.ui.managers.folder_manager.NSApplication")
    @patch("plookingII.ui.managers.folder_manager.NSAlert")
    @patch("plookingII.ui.managers.folder_manager.get_ui_string")
    def test_activates_app_and_fronts_window_before_dialog(
        self, mock_get_ui_string, mock_ns_alert, mock_ns_app, folder_manager
    ):
        """展示弹窗前应激活应用并将主窗口置前，避免弹窗无法聚焦"""
        mock_get_ui_string.side_effect = lambda *args, **kwargs: args[-1]
        mock_alert = MagicMock()
        mock_ns_alert.alloc.return_value.init.return_value = mock_alert
        folder_manager.main_window.isMiniaturized.return_value = True

        folder_manager._show_task_history_restore_dialog(self._history_data())

        mock_ns_app.sharedApplication.return_value.activateIgnoringOtherApps_.assert_called_once_with(True)
        folder_manager.main_window.makeKeyAndOrderFront_.assert_called_once_with(None)
        folder_manager.main_window.orderFrontRegardless.assert_called_once()
        folder_manager.main_window.deminiaturize_.assert_called_once_with(None)

    @patch("plookingII.ui.managers.folder_manager.NSApplication")
    @patch("plookingII.ui.managers.folder_manager.NSAlert")
    @patch("plookingII.ui.managers.folder_manager.get_ui_string")
    def test_sheet_completion_handles_result(
        self, mock_get_ui_string, mock_ns_alert, mock_ns_app, folder_manager
    ):
        """sheet 关闭回调应将按钮结果交给历史处理逻辑"""
        mock_get_ui_string.side_effect = lambda *args, **kwargs: args[-1]
        mock_alert = MagicMock()
        mock_ns_alert.alloc.return_value.init.return_value = mock_alert

        captured = {}

        def side_effect(window, handler):
            captured["handler"] = handler

        mock_alert.beginSheetModalForWindow_completionHandler_.side_effect = side_effect

        history_data = self._history_data()
        with patch.object(folder_manager, "_handle_task_history_dialog_result") as handle:
            folder_manager._show_task_history_restore_dialog(history_data)
            handler = captured["handler"]
            assert handler is not None
            handler(1000)
            handle.assert_called_once_with(1000, history_data)

    @patch("plookingII.ui.managers.folder_manager.NSApplication")
    @patch("plookingII.ui.managers.folder_manager.NSAlert")
    @patch("plookingII.ui.managers.folder_manager.get_ui_string")
    def test_fallback_to_modal_when_sheet_fails(
        self, mock_get_ui_string, mock_ns_alert, mock_ns_app, folder_manager
    ):
        """sheet 展示失败时回退到应用级模态，且不丢失按钮结果"""
        mock_get_ui_string.side_effect = lambda *args, **kwargs: args[-1]
        mock_alert = MagicMock()
        mock_alert.beginSheetModalForWindow_completionHandler_.side_effect = Exception("Sheet failed")
        mock_alert.runModal.return_value = 1001
        mock_ns_alert.alloc.return_value.init.return_value = mock_alert

        history_data = self._history_data()
        with patch.object(folder_manager, "_handle_task_history_dialog_result") as handle:
            folder_manager._show_task_history_restore_dialog(history_data)
            mock_alert.runModal.assert_called_once()
            handle.assert_called_once_with(1001, history_data)

    @patch("plookingII.ui.managers.folder_manager.NSApplication")
    @patch("plookingII.ui.managers.folder_manager.NSAlert")
    @patch("plookingII.ui.managers.folder_manager.get_ui_string")
    def test_sheet_failure_restarts_browsing(
        self, mock_get_ui_string, mock_ns_alert, mock_ns_app, folder_manager
    ):
        """sheet 与 modal 均失败时，兜底重新开始浏览而不是停摆"""
        mock_get_ui_string.side_effect = lambda *args, **kwargs: args[-1]
        mock_alert = MagicMock()
        mock_alert.beginSheetModalForWindow_completionHandler_.side_effect = Exception("Sheet failed")
        mock_alert.runModal.side_effect = Exception("Modal failed")
        mock_ns_alert.alloc.return_value.init.return_value = mock_alert

        with patch.object(folder_manager, "load_current_subfolder") as load:
            folder_manager._show_task_history_restore_dialog(self._history_data())
            load.assert_called_once()
        assert folder_manager.main_window.current_subfolder_index == 0
        assert folder_manager.main_window.current_index == 0

    def test_restore_resolves_folder_by_path(self, folder_manager):
        """恢复时优先按 current_folder 路径定位，而非仅依赖序号"""
        history_data = {
            "subfolders": ["/photos/album1", "/photos/album2", "/photos/album3"],
            "current_subfolder_index": 0,  # 旧序号指向 album1
            "current_index": 3,
            "keep_folder": "",
            "current_folder": "/photos/album3",
        }

        folder_manager._handle_task_history_dialog_result(1000, history_data)

        assert folder_manager.main_window.current_folder == "/photos/album3"
        assert folder_manager.main_window.current_subfolder_index == 2
