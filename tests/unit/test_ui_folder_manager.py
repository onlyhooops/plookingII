"""
测试 ui/managers/folder_manager.py

测试文件夹管理器功能，包括：
- 初始化和配置
- 文件夹扫描
- 导航功能
- 历史记录管理
- 最近文件夹管理
"""

from unittest.mock import MagicMock, Mock, patch, call
import os
import tempfile

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
    with patch('plookingII.ui.managers.folder_manager.RecentFoldersManager'):
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

    @patch('plookingII.ui.managers.folder_manager.RecentFoldersManager')
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

    @patch('plookingII.ui.managers.folder_manager.RecentFoldersManager')
    def test_init_cleanup_invalid_entries(self, mock_recent_manager_class, mock_window):
        """测试初始化时清理无效条目"""
        mock_recent_manager = MagicMock()
        mock_recent_manager_class.return_value = mock_recent_manager
        mock_recent_manager.cleanup_invalid_entries.return_value = 5
        
        manager = FolderManager(mock_window)
        
        mock_recent_manager.cleanup_invalid_entries.assert_called_once()

    @patch('plookingII.ui.managers.folder_manager.RecentFoldersManager')
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
        assert hasattr(folder_manager, '_scan_subfolders')
        assert callable(folder_manager._scan_subfolders)

    def test_dir_contains_images_method_exists(self, folder_manager):
        """测试_dir_contains_images方法存在"""
        assert hasattr(folder_manager, '_dir_contains_images')
        assert callable(folder_manager._dir_contains_images)

    def test_gather_directories_to_scan_method_exists(self, folder_manager):
        """测试_gather_directories_to_scan方法存在"""
        assert hasattr(folder_manager, '_gather_directories_to_scan')
        assert callable(folder_manager._gather_directories_to_scan)

    @patch('plookingII.ui.managers.folder_manager.SUPPORTED_IMAGE_EXTS', ('.jpg', '.png'))
    @patch('plookingII.ui.managers.folder_manager.os.listdir')
    def test_dir_contains_images_true(self, mock_listdir, folder_manager):
        """测试目录包含图片"""
        mock_listdir.return_value = ['img1.jpg', 'img2.png', 'doc.txt']
        
        result = folder_manager._dir_contains_images('/test/folder', ('.jpg', '.png'))
        
        assert result is True

    @patch('plookingII.ui.managers.folder_manager.os.listdir')
    def test_dir_contains_images_false(self, mock_listdir, folder_manager):
        """测试目录不包含图片"""
        mock_listdir.return_value = ['doc.txt', 'readme.md']
        
        result = folder_manager._dir_contains_images('/test/folder', ('.jpg', '.png'))
        
        assert result is False

    @patch('plookingII.ui.managers.folder_manager.os.listdir')
    def test_dir_contains_images_exception(self, mock_listdir, folder_manager):
        """测试目录扫描异常"""
        mock_listdir.side_effect = PermissionError("Access denied")
        
        result = folder_manager._dir_contains_images('/test/folder', ('.jpg', '.png'))
        
        assert result is False


# ==================== 导航功能测试 ====================


class TestNavigation:
    """测试导航功能"""

    def test_jump_to_next_folder_method_exists(self, folder_manager):
        """测试jump_to_next_folder方法存在"""
        assert hasattr(folder_manager, 'jump_to_next_folder')
        assert callable(folder_manager.jump_to_next_folder)

    def test_jump_to_previous_folder_method_exists(self, folder_manager):
        """测试jump_to_previous_folder方法存在"""
        assert hasattr(folder_manager, 'jump_to_previous_folder')
        assert callable(folder_manager.jump_to_previous_folder)

    def test_load_current_subfolder_method_exists(self, folder_manager):
        """测试load_current_subfolder方法存在"""
        assert hasattr(folder_manager, 'load_current_subfolder')
        assert callable(folder_manager.load_current_subfolder)

    def test_skip_current_folder_method_exists(self, folder_manager):
        """测试skip_current_folder方法存在"""
        assert hasattr(folder_manager, 'skip_current_folder')
        assert callable(folder_manager.skip_current_folder)

    def test_undo_skip_folder_method_exists(self, folder_manager):
        """测试undo_skip_folder方法存在"""
        assert hasattr(folder_manager, 'undo_skip_folder')
        assert callable(folder_manager.undo_skip_folder)


# ==================== 历史记录管理测试 ====================


class TestHistoryManagement:
    """测试历史记录管理"""

    def test_task_history_manager_initially_none(self, folder_manager):
        """测试任务历史管理器初始为None"""
        assert folder_manager.task_history_manager is None

    def test_save_task_progress_method_exists(self, folder_manager):
        """测试_save_task_progress方法存在"""
        assert hasattr(folder_manager, '_save_task_progress')
        assert callable(folder_manager._save_task_progress)

    def test_save_task_progress_immediate_method_exists(self, folder_manager):
        """测试_save_task_progress_immediate方法存在"""
        assert hasattr(folder_manager, '_save_task_progress_immediate')
        assert callable(folder_manager._save_task_progress_immediate)

    def test_validate_task_history_method_exists(self, folder_manager):
        """测试_validate_task_history方法存在"""
        assert hasattr(folder_manager, '_validate_task_history')
        assert callable(folder_manager._validate_task_history)

    def test_clear_history_method_exists(self, folder_manager):
        """测试clear_history方法存在"""
        assert hasattr(folder_manager, 'clear_history')
        assert callable(folder_manager.clear_history)


# ==================== 最近文件夹管理测试 ====================


class TestRecentFolders:
    """测试最近文件夹管理"""

    def test_recent_folders_manager_initialized(self, folder_manager):
        """测试最近文件夹管理器已初始化"""
        assert folder_manager.recent_folders_manager is not None

    def test_get_recent_folders_method_exists(self, folder_manager):
        """测试get_recent_folders方法存在"""
        assert hasattr(folder_manager, 'get_recent_folders')
        assert callable(folder_manager.get_recent_folders)

    def test_add_recent_folder_method_exists(self, folder_manager):
        """测试add_recent_folder方法存在"""
        assert hasattr(folder_manager, 'add_recent_folder')
        assert callable(folder_manager.add_recent_folder)

    def test_clear_recent_folders_method_exists(self, folder_manager):
        """测试clear_recent_folders方法存在"""
        assert hasattr(folder_manager, 'clear_recent_folders')
        assert callable(folder_manager.clear_recent_folders)

    def test_get_recent_folders(self, folder_manager):
        """测试获取最近文件夹"""
        folder_manager.recent_folders_manager.get.return_value = ['/folder1', '/folder2']
        
        result = folder_manager.get_recent_folders()
        
        assert result == ['/folder1', '/folder2']
        folder_manager.recent_folders_manager.get.assert_called_once()

    def test_add_recent_folder(self, folder_manager):
        """测试添加最近文件夹"""
        folder_manager.add_recent_folder('/test/folder')
        
        folder_manager.recent_folders_manager.add.assert_called_with('/test/folder')

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
        assert hasattr(folder_manager, 'set_reverse_folder_order')
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
        assert hasattr(folder_manager, 'single_folder_mode')


# ==================== 跳过文件夹历史测试 ====================


class TestSkipFolderHistory:
    """测试跳过文件夹历史"""

    def test_skipped_folders_history_initialized(self, folder_manager):
        """测试跳过文件夹历史已初始化"""
        assert hasattr(folder_manager, '_skipped_folders_history')
        assert folder_manager._skipped_folders_history == []

    def test_max_skip_history_value(self, folder_manager):
        """测试最大跳过历史值"""
        assert folder_manager._max_skip_history == 10


# ==================== 工作会话测试 ====================


class TestWorkSession:
    """测试工作会话"""

    def test_start_work_session_method_exists(self, folder_manager):
        """测试_start_work_session方法存在"""
        assert hasattr(folder_manager, '_start_work_session')
        assert callable(folder_manager._start_work_session)

    def test_end_work_session_method_exists(self, folder_manager):
        """测试_end_work_session方法存在"""
        assert hasattr(folder_manager, '_end_work_session')
        assert callable(folder_manager._end_work_session)


# ==================== 选择文件夹测试 ====================


class TestSelectionFolder:
    """测试选择文件夹"""

    def test_compute_selection_folder_name_method_exists(self, folder_manager):
        """测试_compute_selection_folder_name方法存在"""
        assert hasattr(folder_manager, '_compute_selection_folder_name')
        assert callable(folder_manager._compute_selection_folder_name)

    def test_ensure_selection_folder_method_exists(self, folder_manager):
        """测试_ensure_selection_folder方法存在"""
        assert hasattr(folder_manager, '_ensure_selection_folder')
        assert callable(folder_manager._ensure_selection_folder)


# ==================== 加载方法测试 ====================


class TestLoadMethods:
    """测试加载方法"""

    def test_load_images_from_root_method_exists(self, folder_manager):
        """测试load_images_from_root方法存在"""
        assert hasattr(folder_manager, 'load_images_from_root')
        assert callable(folder_manager.load_images_from_root)

    def test_load_images_without_history_dialog_method_exists(self, folder_manager):
        """测试_load_images_without_history_dialog方法存在"""
        assert hasattr(folder_manager, '_load_images_without_history_dialog')
        assert callable(folder_manager._load_images_without_history_dialog)

    def test_load_folder_images_method_exists(self, folder_manager):
        """测试_load_folder_images方法存在"""
        assert hasattr(folder_manager, '_load_folder_images')
        assert callable(folder_manager._load_folder_images)


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    @patch('plookingII.ui.managers.folder_manager.RecentFoldersManager')
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
        manager.add_recent_folder('/test/folder1')
        mock_recent_manager.add.assert_called_with('/test/folder1')
        
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

    @patch('plookingII.ui.managers.folder_manager.os.listdir')
    def test_dir_contains_images_empty_folder(self, mock_listdir, folder_manager):
        """测试空文件夹"""
        mock_listdir.return_value = []
        
        result = folder_manager._dir_contains_images('/empty/folder', ('.jpg', '.png'))
        
        assert result is False

    def test_add_recent_folder_multiple_times(self, folder_manager):
        """测试多次添加同一文件夹"""
        folder_manager.add_recent_folder('/test/folder')
        folder_manager.add_recent_folder('/test/folder')
        folder_manager.add_recent_folder('/test/folder')
        
        # 应该调用3次
        assert folder_manager.recent_folders_manager.add.call_count == 3


# ==================== 属性测试 ====================


class TestAttributes:
    """测试属性"""

    def test_all_required_attributes_exist(self, folder_manager):
        """测试所有必需属性存在"""
        required_attrs = [
            'main_window', 'task_history_manager', 'recent_folders_manager',
            'reverse_folder_order', 'single_folder_mode', '_skipped_folders_history',
            '_max_skip_history'
        ]
        
        for attr in required_attrs:
            assert hasattr(folder_manager, attr), f"Missing attribute: {attr}"

