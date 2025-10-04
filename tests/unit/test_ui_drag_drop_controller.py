"""
测试 ui/controllers/drag_drop_controller.py

测试拖拽控制器功能，包括：
- 拖拽进入/离开/更新事件
- 文件夹验证（同步/异步）
- 拖拽反馈和视觉效果
"""

from unittest.mock import MagicMock, Mock, patch, call
import os
import threading
import time

import pytest

from plookingII.ui.controllers.drag_drop_controller import DragDropController
from plookingII.core.error_handling import DragDropError, FolderValidationError


# ==================== 夹具（Fixtures） ====================


@pytest.fixture
def mock_window():
    """创建模拟窗口"""
    window = MagicMock()
    window.image_view = MagicMock()
    window.status_bar_controller = MagicMock()
    window.folder_manager = MagicMock()
    window.operation_manager = MagicMock()
    window.updateRecentMenu_ = MagicMock()
    return window


@pytest.fixture
def drag_drop_controller(mock_window):
    """创建拖拽控制器实例"""
    return DragDropController(mock_window)


@pytest.fixture
def mock_drag_sender():
    """创建模拟拖拽发送者"""
    sender = MagicMock()
    pasteboard = MagicMock()
    sender.draggingPasteboard.return_value = pasteboard
    return sender


# ==================== 初始化测试 ====================


class TestDragDropControllerInit:
    """测试DragDropController初始化"""

    def test_init_basic(self, mock_window):
        """测试基本初始化"""
        controller = DragDropController(mock_window)
        
        assert controller.window == mock_window
        assert isinstance(controller._drag_validation_cache, dict)
        assert len(controller._drag_validation_cache) == 0
        assert controller._drag_validation_timer is None
        assert controller._last_drag_path is None

    def test_init_creates_empty_cache(self, drag_drop_controller):
        """测试创建空缓存"""
        assert drag_drop_controller._drag_validation_cache == {}


# ==================== 设置测试 ====================


class TestSetup:
    """测试设置拖拽接收功能"""

    @patch('plookingII.ui.controllers.drag_drop_controller.NSFilenamesPboardType')
    def test_setup_success(self, mock_pbtype, drag_drop_controller):
        """测试成功设置"""
        mock_pbtype.return_value = "NSFilenamesPboardType"
        
        drag_drop_controller.setup()
        
        drag_drop_controller.window.registerForDraggedTypes_.assert_called_once()

    @patch('plookingII.ui.controllers.drag_drop_controller.NSFilenamesPboardType')
    def test_setup_exception(self, mock_pbtype, drag_drop_controller):
        """测试设置异常"""
        drag_drop_controller.window.registerForDraggedTypes_.side_effect = Exception("Setup failed")
        
        # 应该不抛出异常
        try:
            drag_drop_controller.setup()
        except Exception:
            pytest.fail("setup应该捕获异常")


# ==================== 拖拽进入测试 ====================


class TestDraggingEntered:
    """测试拖拽进入事件"""

    def test_dragging_entered_no_files(self, drag_drop_controller, mock_drag_sender):
        """测试无文件拖入"""
        with patch('plookingII.ui.controllers.drag_drop_controller.NSDragOperationNone', 0):
            mock_drag_sender.draggingPasteboard().propertyListForType_.return_value = None
            
            result = drag_drop_controller.dragging_entered(mock_drag_sender)
            
            assert result == 0

    def test_dragging_entered_with_cached_folder(self, drag_drop_controller, mock_drag_sender):
        """测试缓存文件夹拖入"""
        with patch('plookingII.ui.controllers.drag_drop_controller.NSDragOperationCopy', 1):
            with patch('plookingII.ui.controllers.drag_drop_controller.os.path.isdir', return_value=True):
                test_folder = "/test/folder"
                mock_drag_sender.draggingPasteboard().propertyListForType_.return_value = [test_folder]
                
                # 设置缓存
                drag_drop_controller._drag_validation_cache[test_folder] = True
                
                with patch.object(drag_drop_controller, '_show_drag_feedback') as mock_feedback:
                    result = drag_drop_controller.dragging_entered(mock_drag_sender)
                    
                    assert result == 1
                    mock_feedback.assert_called_with(test_folder)

    def test_dragging_entered_quick_check_success(self, drag_drop_controller, mock_drag_sender):
        """测试快速检查成功"""
        with patch('plookingII.ui.controllers.drag_drop_controller.NSDragOperationCopy', 1):
            with patch('plookingII.ui.controllers.drag_drop_controller.os.path.isdir', return_value=True):
                test_folder = "/test/folder"
                mock_drag_sender.draggingPasteboard().propertyListForType_.return_value = [test_folder]
                
                with patch.object(drag_drop_controller, '_quick_folder_check', return_value=True):
                    with patch.object(drag_drop_controller, '_show_drag_feedback'):
                        with patch.object(drag_drop_controller, '_start_async_validation'):
                            result = drag_drop_controller.dragging_entered(mock_drag_sender)
                            
                            assert result == 1
                            assert drag_drop_controller._drag_validation_cache[test_folder] is True

    def test_dragging_entered_drag_drop_error(self, drag_drop_controller, mock_drag_sender):
        """测试拖拽错误"""
        with patch('plookingII.ui.controllers.drag_drop_controller.NSDragOperationNone', 0):
            mock_drag_sender.draggingPasteboard().propertyListForType_.side_effect = DragDropError("Failed")
            
            result = drag_drop_controller.dragging_entered(mock_drag_sender)
            
            assert result == 0


# ==================== 拖拽更新测试 ====================


class TestDraggingUpdated:
    """测试拖拽更新事件"""

    def test_dragging_updated_with_cached_path(self, drag_drop_controller, mock_drag_sender):
        """测试使用缓存路径"""
        with patch('plookingII.ui.controllers.drag_drop_controller.NSDragOperationCopy', 1):
            test_folder = "/test/folder"
            drag_drop_controller._last_drag_path = test_folder
            drag_drop_controller._drag_validation_cache[test_folder] = True
            
            result = drag_drop_controller.dragging_updated(mock_drag_sender)
            
            assert result == 1

    def test_dragging_updated_path_changed(self, drag_drop_controller, mock_drag_sender):
        """测试路径变化"""
        with patch('plookingII.ui.controllers.drag_drop_controller.os.path.isdir', return_value=True):
            old_folder = "/old/folder"
            new_folder = "/new/folder"
            
            drag_drop_controller._last_drag_path = old_folder
            mock_drag_sender.draggingPasteboard().propertyListForType_.return_value = [new_folder]
            
            with patch.object(drag_drop_controller, 'dragging_entered', return_value=1) as mock_entered:
                result = drag_drop_controller.dragging_updated(mock_drag_sender)
                
                mock_entered.assert_called_with(mock_drag_sender)

    def test_dragging_updated_exception(self, drag_drop_controller, mock_drag_sender):
        """测试更新异常"""
        with patch('plookingII.ui.controllers.drag_drop_controller.NSDragOperationNone', 0):
            mock_drag_sender.draggingPasteboard.side_effect = Exception("Failed")
            
            result = drag_drop_controller.dragging_updated(mock_drag_sender)
            
            assert result == 0


# ==================== 拖拽离开测试 ====================


class TestDraggingExited:
    """测试拖拽离开事件"""

    def test_dragging_exited_clears_highlight(self, drag_drop_controller, mock_drag_sender):
        """测试清除高亮"""
        drag_drop_controller.window.image_view.setDragHighlight_ = MagicMock()
        drag_drop_controller._last_drag_path = "/test/folder"
        
        with patch.object(drag_drop_controller, '_cancel_async_validation'):
            drag_drop_controller.dragging_exited(mock_drag_sender)
            
            drag_drop_controller.window.image_view.setDragHighlight_.assert_called_with(False)
            assert drag_drop_controller._last_drag_path is None

    def test_dragging_exited_no_image_view(self, drag_drop_controller, mock_drag_sender):
        """测试无图像视图"""
        drag_drop_controller.window.image_view = None
        
        # 应该不抛出异常
        try:
            drag_drop_controller.dragging_exited(mock_drag_sender)
        except Exception:
            pytest.fail("dragging_exited应该处理无image_view的情况")

    def test_dragging_exited_exception(self, drag_drop_controller, mock_drag_sender):
        """测试离开异常"""
        drag_drop_controller.window.image_view.setDragHighlight_.side_effect = Exception("Failed")
        
        # 应该不抛出异常
        try:
            drag_drop_controller.dragging_exited(mock_drag_sender)
        except Exception:
            pytest.fail("dragging_exited应该捕获异常")


# ==================== 执行拖拽操作测试 ====================


class TestPerformDragOperation:
    """测试执行拖拽操作"""

    @patch('plookingII.ui.controllers.drag_drop_controller.os.path.isdir')
    @patch('plookingII.ui.controllers.drag_drop_controller.os.path.basename')
    @patch('plookingII.ui.controllers.drag_drop_controller.NSFilenamesPboardType')
    def test_perform_drag_operation_success(self, mock_pbtype, mock_basename, mock_isdir,
                                           drag_drop_controller, mock_drag_sender):
        """测试成功执行拖拽"""
        mock_pbtype.return_value = "NSFilenamesPboardType"
        mock_isdir.return_value = True
        mock_basename.return_value = "test_folder"
        
        test_folder = "/test/folder"
        mock_drag_sender.draggingPasteboard().propertyListForType_.return_value = [test_folder]
        
        with patch.object(drag_drop_controller, '_folder_contains_images', return_value=True):
            with patch.object(drag_drop_controller, '_clear_drag_highlight'):
                result = drag_drop_controller.perform_drag_operation(mock_drag_sender)
                
                assert result is True
                drag_drop_controller.window.folder_manager.load_images_from_root.assert_called_with(test_folder)

    @patch('plookingII.ui.controllers.drag_drop_controller.NSFilenamesPboardType')
    def test_perform_drag_operation_no_files(self, mock_pbtype, drag_drop_controller, mock_drag_sender):
        """测试无文件"""
        mock_pbtype.return_value = "NSFilenamesPboardType"
        mock_drag_sender.draggingPasteboard().propertyListForType_.return_value = None
        
        result = drag_drop_controller.perform_drag_operation(mock_drag_sender)
        
        assert result is False

    @patch('plookingII.ui.controllers.drag_drop_controller.os.path.isdir')
    @patch('plookingII.ui.controllers.drag_drop_controller.NSFilenamesPboardType')
    @patch('plookingII.ui.controllers.drag_drop_controller.show_error')
    def test_perform_drag_operation_no_valid_folder(self, mock_show_error, mock_pbtype, mock_isdir,
                                                    drag_drop_controller, mock_drag_sender):
        """测试无有效文件夹"""
        mock_pbtype.return_value = "NSFilenamesPboardType"
        mock_isdir.return_value = True
        
        test_folder = "/test/folder"
        mock_drag_sender.draggingPasteboard().propertyListForType_.return_value = [test_folder]
        
        with patch.object(drag_drop_controller, '_folder_contains_images', return_value=False):
            with patch.object(drag_drop_controller, '_clear_drag_highlight'):
                result = drag_drop_controller.perform_drag_operation(mock_drag_sender)
                
                assert result is False
                mock_show_error.assert_called_once()

    @patch('plookingII.ui.controllers.drag_drop_controller.os.path.isdir')
    @patch('plookingII.ui.controllers.drag_drop_controller.NSFilenamesPboardType')
    @patch('plookingII.ui.controllers.drag_drop_controller.show_error')
    def test_perform_drag_operation_exception(self, mock_show_error, mock_pbtype, mock_isdir,
                                             drag_drop_controller, mock_drag_sender):
        """测试操作异常"""
        mock_pbtype.return_value = "NSFilenamesPboardType"
        mock_isdir.return_value = True
        
        test_folder = "/test/folder"
        mock_drag_sender.draggingPasteboard().propertyListForType_.return_value = [test_folder]
        
        with patch.object(drag_drop_controller, '_folder_contains_images', return_value=True):
            drag_drop_controller.window.folder_manager.load_images_from_root.side_effect = Exception("Failed")
            
            with patch.object(drag_drop_controller, '_clear_drag_highlight'):
                result = drag_drop_controller.perform_drag_operation(mock_drag_sender)
                
                assert result is False
                mock_show_error.assert_called()


# ==================== 辅助方法测试 ====================


class TestHelperMethods:
    """测试辅助方法"""

    def test_clear_drag_highlight(self, drag_drop_controller):
        """测试清除拖拽高亮"""
        drag_drop_controller.window.image_view.setDragHighlight_ = MagicMock()
        
        drag_drop_controller._clear_drag_highlight()
        
        drag_drop_controller.window.image_view.setDragHighlight_.assert_called_with(False)

    def test_clear_drag_highlight_no_image_view(self, drag_drop_controller):
        """测试无图像视图时清除"""
        drag_drop_controller.window.image_view = None
        
        # 应该不抛出异常
        try:
            drag_drop_controller._clear_drag_highlight()
        except Exception:
            pytest.fail("_clear_drag_highlight应该处理无image_view的情况")

    @patch('plookingII.ui.controllers.drag_drop_controller.FileUtils.folder_contains_images')
    def test_folder_contains_images(self, mock_file_utils, drag_drop_controller):
        """测试检查文件夹是否包含图片"""
        mock_file_utils.return_value = True
        
        result = drag_drop_controller._folder_contains_images("/test/folder")
        
        assert result is True
        mock_file_utils.assert_called_with("/test/folder", recursive_depth=1)

    @patch('plookingII.ui.controllers.drag_drop_controller.SUPPORTED_IMAGE_EXTS', ('.jpg', '.png'))
    @patch('plookingII.ui.controllers.drag_drop_controller.os.listdir')
    def test_quick_folder_check_success(self, mock_listdir, drag_drop_controller):
        """测试快速检查成功"""
        mock_listdir.return_value = ['image1.jpg', 'image2.png', 'doc.txt']
        
        result = drag_drop_controller._quick_folder_check("/test/folder")
        
        assert result is True

    @patch('plookingII.ui.controllers.drag_drop_controller.os.listdir')
    def test_quick_folder_check_no_images(self, mock_listdir, drag_drop_controller):
        """测试快速检查无图片"""
        mock_listdir.return_value = ['doc.txt', 'readme.md']
        
        result = drag_drop_controller._quick_folder_check("/test/folder")
        
        assert result is False

    @patch('plookingII.ui.controllers.drag_drop_controller.os.listdir')
    def test_quick_folder_check_exception(self, mock_listdir, drag_drop_controller):
        """测试快速检查异常"""
        mock_listdir.side_effect = Exception("Failed")
        
        result = drag_drop_controller._quick_folder_check("/test/folder")
        
        assert result is False

    @patch('plookingII.ui.controllers.drag_drop_controller.os.path.basename')
    def test_show_drag_feedback(self, mock_basename, drag_drop_controller):
        """测试显示拖拽反馈"""
        mock_basename.return_value = "test_folder"
        drag_drop_controller.window.image_view.setDragHighlight_ = MagicMock()
        
        drag_drop_controller._show_drag_feedback("/test/folder")
        
        drag_drop_controller.window.image_view.setDragHighlight_.assert_called_with(True)
        drag_drop_controller.window.status_bar_controller.set_status_message.assert_called()

    def test_show_drag_feedback_exception(self, drag_drop_controller):
        """测试显示反馈异常"""
        drag_drop_controller.window.image_view.setDragHighlight_.side_effect = Exception("Failed")
        
        # 应该不抛出异常
        try:
            drag_drop_controller._show_drag_feedback("/test/folder")
        except Exception:
            pytest.fail("_show_drag_feedback应该捕获异常")


# ==================== 异步验证测试 ====================


class TestAsyncValidation:
    """测试异步验证"""

    def test_start_async_validation(self, drag_drop_controller):
        """测试启动异步验证"""
        with patch.object(drag_drop_controller, '_cancel_async_validation'):
            with patch.object(drag_drop_controller, '_folder_contains_images', return_value=True):
                drag_drop_controller._start_async_validation("/test/folder")
                
                assert drag_drop_controller._drag_validation_timer is not None
                assert drag_drop_controller._drag_validation_timer.daemon is True

    def test_start_async_validation_cancels_previous(self, drag_drop_controller):
        """测试取消之前的验证"""
        mock_cancel = MagicMock()
        
        with patch.object(drag_drop_controller, '_cancel_async_validation', mock_cancel):
            drag_drop_controller._start_async_validation("/test/folder")
            
            mock_cancel.assert_called_once()

    def test_cancel_async_validation(self, drag_drop_controller):
        """测试取消异步验证"""
        mock_timer = MagicMock()
        mock_timer.is_alive.return_value = True
        drag_drop_controller._drag_validation_timer = mock_timer
        
        drag_drop_controller._cancel_async_validation()
        
        mock_timer.cancel.assert_called_once()
        assert drag_drop_controller._drag_validation_timer is None

    def test_cancel_async_validation_no_timer(self, drag_drop_controller):
        """测试无定时器时取消"""
        drag_drop_controller._drag_validation_timer = None
        
        # 应该不抛出异常
        try:
            drag_drop_controller._cancel_async_validation()
        except Exception:
            pytest.fail("_cancel_async_validation应该处理无定时器的情况")

    def test_async_validation_success(self, drag_drop_controller):
        """测试异步验证成功"""
        test_folder = "/test/folder"
        
        with patch.object(drag_drop_controller, '_folder_contains_images', return_value=True):
            drag_drop_controller._start_async_validation(test_folder)
            
            # 等待异步验证完成
            time.sleep(0.2)
            
            assert drag_drop_controller._drag_validation_cache.get(test_folder) is True

    def test_async_validation_failure(self, drag_drop_controller):
        """测试异步验证失败"""
        test_folder = "/test/folder"
        
        with patch.object(drag_drop_controller, '_folder_contains_images', side_effect=Exception("Failed")):
            drag_drop_controller._start_async_validation(test_folder)
            
            # 等待异步验证完成
            time.sleep(0.2)
            
            assert drag_drop_controller._drag_validation_cache.get(test_folder) is False


# ==================== 关闭测试 ====================


class TestShutdown:
    """测试关闭"""

    def test_shutdown(self, drag_drop_controller):
        """测试关闭控制器"""
        drag_drop_controller._drag_validation_cache["/test/folder"] = True
        
        with patch.object(drag_drop_controller, '_cancel_async_validation') as mock_cancel:
            drag_drop_controller.shutdown()
            
            mock_cancel.assert_called_once()
            assert len(drag_drop_controller._drag_validation_cache) == 0

    def test_shutdown_with_active_timer(self, drag_drop_controller):
        """测试关闭时有活动定时器"""
        mock_timer = MagicMock()
        mock_timer.is_alive.return_value = True
        drag_drop_controller._drag_validation_timer = mock_timer
        
        drag_drop_controller.shutdown()
        
        mock_timer.cancel.assert_called_once()


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    def test_complete_drag_workflow(self, drag_drop_controller, mock_drag_sender):
        """测试完整拖拽工作流"""
        with patch('plookingII.ui.controllers.drag_drop_controller.NSDragOperationCopy', 1):
            with patch('plookingII.ui.controllers.drag_drop_controller.os.path.isdir', return_value=True):
                with patch('plookingII.ui.controllers.drag_drop_controller.os.path.basename', return_value="test_folder"):
                    test_folder = "/test/folder"
                    mock_drag_sender.draggingPasteboard().propertyListForType_.return_value = [test_folder]
                    
                    with patch.object(drag_drop_controller, '_quick_folder_check', return_value=True):
                        with patch.object(drag_drop_controller, '_show_drag_feedback'):
                            with patch.object(drag_drop_controller, '_start_async_validation'):
                                # 1. 拖拽进入
                                result1 = drag_drop_controller.dragging_entered(mock_drag_sender)
                                assert result1 == 1
                                
                                # 2. 拖拽更新
                                result2 = drag_drop_controller.dragging_updated(mock_drag_sender)
                                assert result2 == 1
                                
                                # 3. 执行拖拽
                                with patch.object(drag_drop_controller, '_folder_contains_images', return_value=True):
                                    with patch.object(drag_drop_controller, '_clear_drag_highlight'):
                                        result3 = drag_drop_controller.perform_drag_operation(mock_drag_sender)
                                        assert result3 is True
                                
                                # 4. 拖拽离开
                                with patch.object(drag_drop_controller, '_cancel_async_validation'):
                                    drag_drop_controller.dragging_exited(mock_drag_sender)
                                    assert drag_drop_controller._last_drag_path is None

    def test_cache_persistence(self, drag_drop_controller):
        """测试缓存持久性"""
        test_folder1 = "/test/folder1"
        test_folder2 = "/test/folder2"
        
        # 设置缓存
        drag_drop_controller._drag_validation_cache[test_folder1] = True
        drag_drop_controller._drag_validation_cache[test_folder2] = False
        
        # 验证缓存
        assert drag_drop_controller._drag_validation_cache[test_folder1] is True
        assert drag_drop_controller._drag_validation_cache[test_folder2] is False
        
        # 关闭后应清空
        drag_drop_controller.shutdown()
        assert len(drag_drop_controller._drag_validation_cache) == 0

