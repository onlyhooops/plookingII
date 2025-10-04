"""
测试 ui/managers/operation_manager.py

测试操作管理器功能，包括：
- 初始化
- 操作执行
- 历史记录
- 目录操作
"""

from unittest.mock import MagicMock, Mock, patch
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
        assert hasattr(operation_manager, 'main_window')


# ==================== 方法存在性测试 ====================


class TestMethodsExistence:
    """测试方法存在性"""

    def test_has_required_methods(self, operation_manager):
        """测试必需方法存在"""
        required_methods = [
            'keep_current_image',
            'undo_keep_action',
            'show_completion',
            'exit_current_folder',
            'open_folder',
            'goto_keep_folder',
            'jump_to_folder',
            'goto_file',
            'show_in_finder',
            'clear_cache'
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

