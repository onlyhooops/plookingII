"""
测试 ui/managers/operation_manager.py

测试操作管理器功能，包括：
- 初始化
- 操作执行
- 历史记录
- 目录操作
"""

from unittest.mock import MagicMock, patch

import pytest

from plookingII.ui.managers.operation_manager import OperationManager

# ==================== 夹具（Fixtures） ====================


@pytest.fixture
def mock_window():
    """创建模拟窗口"""
    window = MagicMock()
    window.images = ["/test/img1.jpg"]
    window.current_index = 0
    window.current_folder = "/test/folder"
    return window


@pytest.fixture
def operation_manager(mock_window):
    """创建操作管理器实例"""
    return OperationManager(mock_window)


# ==================== 初始化测试 ====================


class TestOperationManagerInit:
    """测试OperationManager初始化"""

    def test_init_basic(self, mock_window):
        """测试基本初始化"""
        manager = OperationManager(mock_window)

        assert manager.main_window == mock_window

    def test_init_attributes(self, operation_manager):
        """测试初始属性"""
        assert hasattr(operation_manager, "main_window")


# ==================== 方法存在性测试 ====================


class TestMethodsExistence:
    """测试方法存在性"""

    def test_has_required_methods(self, operation_manager):
        """测试必需方法存在"""
        required_methods = [
            "keep_current_image",
            "undo_keep_action",
            "show_completion",
            "exit_current_folder",
            "open_folder",
            "goto_keep_folder",
            "jump_to_folder",
            "goto_file",
            "show_in_finder",
            "clear_cache"
        ]

        for method_name in required_methods:
            assert hasattr(operation_manager, method_name)
            assert callable(getattr(operation_manager, method_name))


# ==================== 属性测试 ====================


class TestAttributes:
    """测试属性"""

    def test_window_reference(self, operation_manager):
        """测试窗口引用"""
        assert operation_manager.main_window is not None



# ==================== 精选计数内存缓存测试 ====================


class TestKeepCountCache:
    """测试精选计数内存缓存（P0-1）"""

    def test_get_keep_count_scans_once_and_caches(self, tmp_path, operation_manager):
        """首次访问扫描一次，后续读取内存缓存"""
        keep = tmp_path / "keep"
        keep.mkdir()
        (keep / "a.jpg").touch()
        (keep / "b.png").touch()
        (keep / "c.txt").touch()
        operation_manager.main_window.keep_folder = str(keep)

        with patch.object(
            operation_manager, "_scan_keep_folder", wraps=operation_manager._scan_keep_folder
        ) as scan:
            assert operation_manager.get_keep_count() == 2
            assert operation_manager.get_keep_count() == 2
            scan.assert_called_once()

    def test_get_keep_count_invalidates_on_folder_change(self, tmp_path, operation_manager):
        """keep_folder 变化时自动失效并重新扫描"""
        k1 = tmp_path / "k1"
        k1.mkdir()
        (k1 / "a.jpg").touch()
        k2 = tmp_path / "k2"
        k2.mkdir()
        (k2 / "a.jpg").touch()
        (k2 / "b.jpg").touch()

        operation_manager.main_window.keep_folder = str(k1)
        assert operation_manager.get_keep_count() == 1
        operation_manager.main_window.keep_folder = str(k2)
        assert operation_manager.get_keep_count() == 2

    def test_bump_keep_count_adjusts_cache(self, tmp_path, operation_manager):
        """保留/撤销操作通过 _bump_keep_count 增量调整计数"""
        keep = tmp_path / "keep"
        keep.mkdir()
        (keep / "a.jpg").touch()
        operation_manager.main_window.keep_folder = str(keep)
        assert operation_manager.get_keep_count() == 1

        operation_manager._bump_keep_count(+1)
        assert operation_manager.get_keep_count() == 2
        operation_manager._bump_keep_count(-2)
        assert operation_manager.get_keep_count() == 0

    def test_missing_folder_returns_zero(self, operation_manager):
        """精选目录不存在时返回 0"""
        operation_manager.main_window.keep_folder = "/nonexistent/keep"
        assert operation_manager.get_keep_count() == 0
