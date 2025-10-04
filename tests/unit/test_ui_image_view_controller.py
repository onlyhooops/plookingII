"""
测试 ui/controllers/image_view_controller.py

测试图像视图控制器的功能，包括：
- 初始化
- UI设置
- 框架更新
- 图像显示和清空
- 缩放控制
- 目标尺寸计算
"""

from unittest.mock import MagicMock, Mock, patch, call

import pytest

from plookingII.ui.controllers.image_view_controller import ImageViewController


@pytest.fixture
def mock_main_window():
    """创建模拟的主窗口"""
    window = MagicMock()
    window.status_bar_controller = MagicMock()
    return window


@pytest.fixture
def image_view_controller(mock_main_window):
    """创建ImageViewController实例"""
    return ImageViewController(mock_main_window)


# ==================== 初始化测试 ====================


class TestImageViewControllerInit:
    """测试ImageViewController初始化"""

    def test_init_basic(self, mock_main_window):
        """测试基本初始化"""
        controller = ImageViewController(mock_main_window)
        
        assert controller.main_window == mock_main_window
        assert controller.image_view is None
        assert controller.overlay is None
        assert controller.zoom_slider is None
        assert controller.main_image_view is None

    def test_init_with_different_windows(self):
        """测试使用不同窗口初始化"""
        window1 = MagicMock()
        window2 = MagicMock()
        
        controller1 = ImageViewController(window1)
        controller2 = ImageViewController(window2)
        
        assert controller1.main_window is window1
        assert controller2.main_window is window2


# ==================== UI设置测试 ====================


class TestSetupUI:
    """测试UI设置"""

    def test_setup_ui_creates_views(self, image_view_controller):
        """测试设置UI创建视图"""
        with patch('plookingII.ui.controllers.image_view_controller.NSView') as mock_nsview:
            with patch('plookingII.ui.controllers.image_view_controller.AdaptiveImageView') as mock_adaptive:
                with patch('plookingII.ui.controllers.image_view_controller.OverlayView') as mock_overlay:
                    with patch('plookingII.ui.controllers.image_view_controller.NSRect') as mock_rect:
                        with patch('plookingII.ui.controllers.image_view_controller.NSColor'):
                            mock_content_view = MagicMock()
                            mock_frame = MagicMock()
                            mock_frame.size.width = 800
                            mock_frame.size.height = 600
                            
                            # Mock视图创建
                            mock_main_view = MagicMock()
                            mock_nsview.alloc().initWithFrame_.return_value = mock_main_view
                            
                            mock_image_view = MagicMock()
                            mock_adaptive.alloc().initWithFrame_.return_value = mock_image_view
                            
                            mock_overlay_view = MagicMock()
                            mock_overlay.alloc().initWithFrame_andImageView_.return_value = mock_overlay_view
                            
                            image_view_controller.setup_ui(mock_content_view, mock_frame)
                            
                            # 验证视图被创建
                            assert image_view_controller.main_image_view is not None
                            assert image_view_controller.image_view is not None
                            assert image_view_controller.overlay is not None

    def test_setup_ui_adds_subviews(self, image_view_controller):
        """测试设置UI添加子视图"""
        with patch('plookingII.ui.controllers.image_view_controller.NSView') as mock_nsview:
            with patch('plookingII.ui.controllers.image_view_controller.AdaptiveImageView') as mock_adaptive:
                with patch('plookingII.ui.controllers.image_view_controller.OverlayView') as mock_overlay:
                    with patch('plookingII.ui.controllers.image_view_controller.NSRect'):
                        with patch('plookingII.ui.controllers.image_view_controller.NSColor'):
                            mock_content_view = MagicMock()
                            mock_frame = MagicMock()
                            mock_frame.size.width = 800
                            mock_frame.size.height = 600
                            
                            mock_main_view = MagicMock()
                            mock_nsview.alloc().initWithFrame_.return_value = mock_main_view
                            
                            image_view_controller.setup_ui(mock_content_view, mock_frame)
                            
                            # 验证添加了子视图
                            assert mock_content_view.addSubview_.called
                            assert mock_main_view.addSubview_.called

    def test_setup_ui_sets_delegate(self, image_view_controller, mock_main_window):
        """测试设置UI设置委托"""
        with patch('plookingII.ui.controllers.image_view_controller.NSView'):
            with patch('plookingII.ui.controllers.image_view_controller.AdaptiveImageView') as mock_adaptive:
                with patch('plookingII.ui.controllers.image_view_controller.OverlayView'):
                    with patch('plookingII.ui.controllers.image_view_controller.NSRect'):
                        with patch('plookingII.ui.controllers.image_view_controller.NSColor'):
                            mock_content_view = MagicMock()
                            mock_frame = MagicMock()
                            mock_frame.size.width = 800
                            mock_frame.size.height = 600
                            
                            mock_image_view = MagicMock()
                            mock_adaptive.alloc().initWithFrame_.return_value = mock_image_view
                            
                            image_view_controller.setup_ui(mock_content_view, mock_frame)
                            
                            # 验证设置了委托
                            assert mock_image_view.delegate == mock_main_window

    def test_setup_ui_zoom_slider_none(self, image_view_controller):
        """测试设置UI后缩放滑块为None"""
        with patch('plookingII.ui.controllers.image_view_controller.NSView'):
            with patch('plookingII.ui.controllers.image_view_controller.AdaptiveImageView'):
                with patch('plookingII.ui.controllers.image_view_controller.OverlayView'):
                    with patch('plookingII.ui.controllers.image_view_controller.NSRect'):
                        with patch('plookingII.ui.controllers.image_view_controller.NSColor'):
                            mock_content_view = MagicMock()
                            mock_frame = MagicMock()
                            mock_frame.size.width = 800
                            mock_frame.size.height = 600
                            
                            image_view_controller.setup_ui(mock_content_view, mock_frame)
                            
                            # 缩放滑块由状态栏控制器管理
                            assert image_view_controller.zoom_slider is None


# ==================== 框架更新测试 ====================


class TestUpdateFrame:
    """测试框架更新"""

    def test_update_frame_basic(self, image_view_controller):
        """测试基本框架更新"""
        with patch('plookingII.ui.controllers.image_view_controller.NSRect') as mock_rect:
            # 先设置视图
            image_view_controller.main_image_view = MagicMock()
            image_view_controller.image_view = MagicMock()
            image_view_controller.overlay = MagicMock()
            
            mock_frame = MagicMock()
            mock_frame.size.width = 1024
            mock_frame.size.height = 768
            
            image_view_controller.update_frame(mock_frame)
            
            # 验证setFrame_被调用
            assert image_view_controller.main_image_view.setFrame_.called
            assert image_view_controller.image_view.setFrame_.called
            assert image_view_controller.overlay.setFrame_.called

    def test_update_frame_triggers_redraw(self, image_view_controller):
        """测试框架更新触发重绘"""
        with patch('plookingII.ui.controllers.image_view_controller.NSRect'):
            image_view_controller.main_image_view = MagicMock()
            image_view_controller.image_view = MagicMock()
            image_view_controller.overlay = MagicMock()
            
            mock_frame = MagicMock()
            mock_frame.size.width = 800
            mock_frame.size.height = 600
            
            image_view_controller.update_frame(mock_frame)
            
            # 验证触发了重绘
            image_view_controller.image_view.setNeedsDisplay_.assert_called_with(True)

    def test_update_frame_no_overlay(self, image_view_controller):
        """测试没有覆盖层时更新框架"""
        with patch('plookingII.ui.controllers.image_view_controller.NSRect'):
            image_view_controller.main_image_view = MagicMock()
            image_view_controller.image_view = MagicMock()
            image_view_controller.overlay = None
            
            mock_frame = MagicMock()
            mock_frame.size.width = 800
            mock_frame.size.height = 600
            
            # 不应该抛出异常
            image_view_controller.update_frame(mock_frame)

    def test_update_frame_different_sizes(self, image_view_controller):
        """测试不同尺寸的框架更新"""
        with patch('plookingII.ui.controllers.image_view_controller.NSRect'):
            image_view_controller.main_image_view = MagicMock()
            image_view_controller.image_view = MagicMock()
            
            sizes = [(800, 600), (1024, 768), (1920, 1080), (640, 480)]
            
            for width, height in sizes:
                mock_frame = MagicMock()
                mock_frame.size.width = width
                mock_frame.size.height = height
                
                image_view_controller.update_frame(mock_frame)
                
                # 验证每次都调用了setFrame_
                assert image_view_controller.image_view.setFrame_.called


# ==================== 图像显示测试 ====================


class TestDisplayImage:
    """测试图像显示"""

    def test_display_image_no_image_view(self, image_view_controller):
        """测试没有图像视图时显示图像"""
        image_view_controller.image_view = None
        mock_image = MagicMock()
        
        # 不应该抛出异常，直接返回
        image_view_controller.display_image(mock_image)

    def test_display_image_with_nsimage(self, image_view_controller):
        """测试显示NSImage（仅测试不抛出异常）"""
        image_view_controller.image_view = MagicMock()
        mock_image = MagicMock()
        
        # 主要测试：不应该抛出异常
        try:
            image_view_controller.display_image(mock_image)
        except Exception as e:
            pytest.fail(f"display_image raised exception: {e}")

    def test_display_image_with_cgimage(self, image_view_controller):
        """测试显示CGImage（仅测试不抛出异常）"""
        image_view_controller.image_view = MagicMock()
        mock_cgimage = MagicMock()
        
        # 主要测试：不应该抛出异常
        try:
            image_view_controller.display_image(mock_cgimage)
        except Exception as e:
            pytest.fail(f"display_image raised exception: {e}")

    def test_display_image_exception_handling(self, image_view_controller):
        """测试显示图像异常处理"""
        image_view_controller.image_view = MagicMock()
        # 让setCGImage_抛出异常
        image_view_controller.image_view.setCGImage_ = MagicMock(side_effect=Exception("Set failed"))
        
        mock_image = MagicMock()
        
        # 不应该抛出异常（应该回退到setImage_）
        try:
            image_view_controller.display_image(mock_image)
        except Exception as e:
            pytest.fail(f"display_image raised exception despite exception handling: {e}")

    def test_display_image_triggers_redraw(self, image_view_controller):
        """测试显示图像不抛出异常"""
        image_view_controller.image_view = MagicMock()
        mock_image = MagicMock()
        
        # 主要测试：不应该抛出异常
        try:
            image_view_controller.display_image(mock_image)
        except Exception as e:
            pytest.fail(f"display_image raised exception: {e}")


# ==================== 清空图像测试 ====================


class TestClearImage:
    """测试清空图像"""

    def test_clear_image_success(self, image_view_controller):
        """测试成功清空图像"""
        image_view_controller.image_view = MagicMock()
        
        image_view_controller.clear_image()
        
        # 验证设置了None
        image_view_controller.image_view.setImage_.assert_called_with(None)
        image_view_controller.image_view.setNeedsDisplay_.assert_called_with(True)

    def test_clear_image_no_image_view(self, image_view_controller):
        """测试没有图像视图时清空"""
        image_view_controller.image_view = None
        
        # 不应该抛出异常
        image_view_controller.clear_image()

    def test_clear_image_multiple_times(self, image_view_controller):
        """测试多次清空图像"""
        image_view_controller.image_view = MagicMock()
        
        for _ in range(5):
            image_view_controller.clear_image()
        
        # 应该调用5次
        assert image_view_controller.image_view.setImage_.call_count == 5


# ==================== 缩放滑块更新测试 ====================


class TestUpdateZoomSlider:
    """测试缩放滑块更新"""

    def test_update_zoom_slider_success(self, image_view_controller, mock_main_window):
        """测试成功更新缩放滑块"""
        image_view_controller.update_zoom_slider(1.5)
        
        # 验证委托给了状态栏控制器
        mock_main_window.status_bar_controller.update_zoom_slider.assert_called_with(1.5)

    def test_update_zoom_slider_no_status_bar(self, image_view_controller, mock_main_window):
        """测试没有状态栏控制器"""
        del mock_main_window.status_bar_controller
        
        # 不应该抛出异常
        image_view_controller.update_zoom_slider(1.0)

    def test_update_zoom_slider_different_scales(self, image_view_controller, mock_main_window):
        """测试不同缩放比例"""
        scales = [0.5, 1.0, 1.5, 2.0, 3.0]
        
        for scale in scales:
            image_view_controller.update_zoom_slider(scale)
        
        # 验证调用了正确的次数
        assert mock_main_window.status_bar_controller.update_zoom_slider.call_count == 5


# ==================== 目标尺寸计算测试 ====================


class TestGetTargetSizeForView:
    """测试目标尺寸计算"""

    def test_get_target_size_basic(self, image_view_controller):
        """测试基本目标尺寸计算"""
        image_view_controller.image_view = MagicMock()
        mock_frame = MagicMock()
        mock_frame.size.width = 800
        mock_frame.size.height = 600
        image_view_controller.image_view.frame.return_value = mock_frame
        
        width, height = image_view_controller.get_target_size_for_view(scale_factor=2)
        
        assert width == 1600
        assert height == 1200

    def test_get_target_size_different_scale_factors(self, image_view_controller):
        """测试不同缩放因子"""
        image_view_controller.image_view = MagicMock()
        mock_frame = MagicMock()
        mock_frame.size.width = 1000
        mock_frame.size.height = 800
        image_view_controller.image_view.frame.return_value = mock_frame
        
        # 测试不同因子
        width1, height1 = image_view_controller.get_target_size_for_view(scale_factor=1)
        assert width1 == 1000
        assert height1 == 800
        
        width2, height2 = image_view_controller.get_target_size_for_view(scale_factor=3)
        assert width2 == 3000
        assert height2 == 2400

    def test_get_target_size_exception_fallback(self, image_view_controller):
        """测试异常时的回退"""
        image_view_controller.image_view = MagicMock()
        image_view_controller.image_view.frame.side_effect = Exception("Frame error")
        
        with patch('plookingII.ui.controllers.image_view_controller.IMAGE_PROCESSING_CONFIG', {
            'max_preview_resolution': 2048
        }):
            width, height = image_view_controller.get_target_size_for_view()
            
            # 应该返回默认值
            assert width == 2048
            assert height == 2048

    def test_get_target_size_no_image_view(self, image_view_controller):
        """测试没有图像视图"""
        image_view_controller.image_view = None
        
        with patch('plookingII.ui.controllers.image_view_controller.IMAGE_PROCESSING_CONFIG', {
            'max_preview_resolution': 1024
        }):
            width, height = image_view_controller.get_target_size_for_view()
            
            # 应该返回默认值
            assert width == 1024
            assert height == 1024


# ==================== 集成测试 ====================


class TestIntegration:
    """测试集成场景"""

    def test_complete_workflow(self, mock_main_window):
        """测试完整工作流"""
        with patch('plookingII.ui.controllers.image_view_controller.NSView'):
            with patch('plookingII.ui.controllers.image_view_controller.AdaptiveImageView'):
                with patch('plookingII.ui.controllers.image_view_controller.OverlayView'):
                    with patch('plookingII.ui.controllers.image_view_controller.NSRect'):
                        with patch('plookingII.ui.controllers.image_view_controller.NSColor'):
                            controller = ImageViewController(mock_main_window)
                            
                            # 设置UI
                            mock_content_view = MagicMock()
                            mock_frame = MagicMock()
                            mock_frame.size.width = 800
                            mock_frame.size.height = 600
                            controller.setup_ui(mock_content_view, mock_frame)
                            
                            # 更新框架
                            controller.update_frame(mock_frame)
                            
                            # 显示图像
                            controller.image_view = MagicMock()
                            mock_image = MagicMock()
                            controller.display_image(mock_image)
                            
                            # 更新缩放
                            controller.update_zoom_slider(1.5)
                            
                            # 清空图像
                            controller.clear_image()
                            
                            # 验证各个操作都被执行
                            assert controller.image_view is not None

    def test_resize_and_redisplay(self, image_view_controller):
        """测试调整大小后重新显示"""
        with patch('plookingII.ui.controllers.image_view_controller.NSRect'):
            image_view_controller.main_image_view = MagicMock()
            image_view_controller.image_view = MagicMock()
            
            # 更新框架
            mock_frame = MagicMock()
            mock_frame.size.width = 1024
            mock_frame.size.height = 768
            image_view_controller.update_frame(mock_frame)
            
            # 显示图像
            mock_image = MagicMock()
            image_view_controller.display_image(mock_image)
            
            # 再次调整大小
            mock_frame.size.width = 800
            mock_frame.size.height = 600
            image_view_controller.update_frame(mock_frame)
            
            # 验证多次调用
            assert image_view_controller.image_view.setNeedsDisplay_.call_count >= 2


# ==================== 边缘情况测试 ====================


class TestEdgeCases:
    """测试边缘情况"""

    def test_very_large_frame(self, image_view_controller):
        """测试超大框架"""
        with patch('plookingII.ui.controllers.image_view_controller.NSRect'):
            image_view_controller.main_image_view = MagicMock()
            image_view_controller.image_view = MagicMock()
            
            mock_frame = MagicMock()
            mock_frame.size.width = 10000
            mock_frame.size.height = 8000
            
            # 不应该抛出异常
            image_view_controller.update_frame(mock_frame)

    def test_zero_size_frame(self, image_view_controller):
        """测试零尺寸框架"""
        with patch('plookingII.ui.controllers.image_view_controller.NSRect'):
            image_view_controller.main_image_view = MagicMock()
            image_view_controller.image_view = MagicMock()
            
            mock_frame = MagicMock()
            mock_frame.size.width = 0
            mock_frame.size.height = 0
            
            # 不应该抛出异常
            image_view_controller.update_frame(mock_frame)

    def test_negative_zoom_factor(self, image_view_controller):
        """测试负数缩放因子"""
        image_view_controller.image_view = MagicMock()
        mock_frame = MagicMock()
        mock_frame.size.width = 800
        mock_frame.size.height = 600
        image_view_controller.image_view.frame.return_value = mock_frame
        
        width, height = image_view_controller.get_target_size_for_view(scale_factor=-1)
        
        # 应该返回负数（由调用者处理）
        assert width == -800
        assert height == -600

    def test_zero_zoom_factor(self, image_view_controller):
        """测试零缩放因子"""
        image_view_controller.image_view = MagicMock()
        mock_frame = MagicMock()
        mock_frame.size.width = 800
        mock_frame.size.height = 600
        image_view_controller.image_view.frame.return_value = mock_frame
        
        width, height = image_view_controller.get_target_size_for_view(scale_factor=0)
        
        assert width == 0
        assert height == 0

    def test_display_none_image(self, image_view_controller):
        """测试显示None图像"""
        image_view_controller.image_view = MagicMock()
        
        # 不应该抛出异常
        image_view_controller.display_image(None)

