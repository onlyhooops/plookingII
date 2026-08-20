"""
测试 ui/views.py 的 TiledImageView（P3-1 CATiledLayer 分片渲染原型）

覆盖：
- _rect_intersection 交集计算（含无交集/部分重叠）
- _get_display_rect 显示区域几何（居中/边距/缩放平移）
- setCGImage_ 的路由逻辑：默认关闭时不路由；开启且超阈值时路由
- 路由失败回退普通 CGImage 直通
"""

from unittest.mock import MagicMock, patch

import pytest

from plookingII.ui.views import AdaptiveImageView, TiledImageView


class TestRectIntersection:
    """测试 _rect_intersection 静态方法"""

    def _rect(self, x, y, w, h):
        from AppKit import NSMakeRect

        return NSMakeRect(x, y, w, h)

    def test_full_overlap(self):
        """完全重叠返回较小矩形"""
        a = self._rect(0, 0, 100, 100)
        b = self._rect(10, 10, 50, 50)
        inter = TiledImageView._rect_intersection(a, b)
        assert (inter.origin.x, inter.origin.y) == (10, 10)
        assert (inter.size.width, inter.size.height) == (50, 50)

    def test_partial_overlap(self):
        """部分重叠返回交集区域"""
        a = self._rect(0, 0, 100, 100)
        b = self._rect(50, 50, 100, 100)
        inter = TiledImageView._rect_intersection(a, b)
        assert (inter.origin.x, inter.origin.y) == (50, 50)
        assert (inter.size.width, inter.size.height) == (50, 50)

    def test_no_overlap_returns_none(self):
        """无交集返回 None"""
        a = self._rect(0, 0, 10, 10)
        b = self._rect(100, 100, 10, 10)
        assert TiledImageView._rect_intersection(a, b) is None

    def test_edge_touching_returns_none(self):
        """仅边缘相接（零面积交集）返回 None"""
        a = self._rect(0, 0, 10, 10)
        b = self._rect(10, 0, 10, 10)
        assert TiledImageView._rect_intersection(a, b) is None


class TestTiledDisplayRect:
    """测试 _get_display_rect 显示区域几何"""

    @pytest.fixture
    def tiled_view(self):
        from AppKit import NSMakeRect

        view = TiledImageView.alloc().initWithFrame_(NSMakeRect(0, 0, 800, 600))
        view._tile_layer = None  # 避免真实 CATiledLayer（无 GUI 环境）
        view._cgimage = MagicMock()
        return view

    def test_centered_with_margins(self, tiled_view):
        """常规图片居中显示，带自适应边距"""
        with patch("Quartz.CGImageGetWidth", return_value=400), patch("Quartz.CGImageGetHeight", return_value=300):
            rect = tiled_view._get_display_rect()
            assert rect.size.width > 0
            assert rect.size.height > 0
            # 居中：水平方向左右边距相等
            view_w = 800.0
            margin_l = rect.origin.x
            margin_r = view_w - (rect.origin.x + rect.size.width)
            assert abs(margin_l - margin_r) < 1e-6

    def test_zoom_and_offset_applied(self, tiled_view):
        """缩放与平移应用到显示区域"""
        with patch("Quartz.CGImageGetWidth", return_value=100), patch("Quartz.CGImageGetHeight", return_value=100):
            # 基准：无缩放时的显示宽度（100px 图适配 800x600 视图）
            base_rect = tiled_view._get_display_rect()
            base_w = base_rect.size.width

            tiled_view.zoom_scale = 2.0
            tiled_view.offset_x = 10.0
            tiled_view.offset_y = 20.0
            rect = tiled_view._get_display_rect()
            # 缩放后宽度 = 基础宽度 × 2
            assert rect.size.width == pytest.approx(base_w * 2.0, rel=0.01)
            # 平移叠加到原点
            assert rect.origin.x == pytest.approx(base_rect.origin.x + 10.0, rel=0.01)
            assert rect.origin.y == pytest.approx(base_rect.origin.y + 20.0, rel=0.01)

    def test_no_cgimage_returns_none(self, tiled_view):
        """无源图时返回 None"""
        tiled_view._cgimage = None
        assert tiled_view._get_display_rect() is None


class TestAdaptiveImageViewMemory:
    """v2.8.1 防回归：图像视图不使用图层后备（显示泄漏修复）"""

    def test_image_view_not_layer_backed(self):
        """AdaptiveImageView 默认非图层后备（避免每次显示泄漏视图尺寸后备位图）"""
        from AppKit import NSMakeRect

        view = AdaptiveImageView.alloc().initWithFrame_(NSMakeRect(0, 0, 800, 600))
        try:
            assert view.wantsLayer() is False
        finally:
            view = None


class TestTiledRouting:
    """测试 setCGImage_ 的分片路由逻辑"""

    @pytest.fixture
    def image_view(self):
        from AppKit import NSMakeRect

        return AdaptiveImageView.alloc().initWithFrame_(NSMakeRect(0, 0, 800, 600))

    def test_routing_disabled_by_default(self, image_view):
        """开关默认关闭：超高分辨率图也不路由，走普通 CGImage 直通"""
        image_view.setNeedsDisplay_ = MagicMock()  # 实例级覆盖 selector
        with (
            patch("plookingII.ui.views.TILED_RENDERING_ENABLED", False),
            patch("plookingII.ui.views.AdaptiveImageView._route_to_tiled") as route,
            patch("Quartz.CGImageGetWidth", return_value=8000),
            patch("Quartz.CGImageGetHeight", return_value=6000),
        ):
            image_view.setCGImage_(MagicMock())
            route.assert_not_called()

    def test_routing_enabled_but_small_image(self, image_view):
        """开关开启但图片未超阈值：不路由"""
        image_view.setNeedsDisplay_ = MagicMock()
        with (
            patch("plookingII.ui.views.TILED_RENDERING_ENABLED", True),
            patch("plookingII.ui.views.AdaptiveImageView._route_to_tiled") as route,
            patch("Quartz.CGImageGetWidth", return_value=1920),
            patch("Quartz.CGImageGetHeight", return_value=1080),
        ):
            image_view.setCGImage_(MagicMock())
            route.assert_not_called()

    def test_routing_enabled_ultra_image(self, image_view):
        """开关开启且图片超阈值：路由到 TiledImageView"""
        with (
            patch("plookingII.ui.views.TILED_RENDERING_ENABLED", True),
            patch("plookingII.ui.views.AdaptiveImageView._route_to_tiled") as route,
            patch("Quartz.CGImageGetWidth", return_value=8000),
            patch("Quartz.CGImageGetHeight", return_value=6000),
        ):
            image_view.setCGImage_(MagicMock())
            route.assert_called_once()

    def test_routing_fallback_on_exception(self, image_view):
        """路由异常时回退普通 CGImage 直通（不崩溃）"""
        image_view.setNeedsDisplay_ = MagicMock()
        with (
            patch("plookingII.ui.views.TILED_RENDERING_ENABLED", True),
            patch(
                "plookingII.ui.views.AdaptiveImageView._route_to_tiled",
                side_effect=Exception("routing failed"),
            ),
            patch("Quartz.CGImageGetWidth", return_value=8000),
            patch("Quartz.CGImageGetHeight", return_value=6000),
        ):
            cg = MagicMock()
            image_view.setCGImage_(cg)  # 不应抛异常
            assert image_view._cgimage is cg
