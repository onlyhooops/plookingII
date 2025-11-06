"""
基本集成测试
演示多模块协作测试
"""

import pytest


@pytest.mark.integration()
@pytest.mark.timeout(30)
class TestConfigIntegration:
    """配置集成测试"""

    def test_config_manager_initialization(self, mock_logger):
        """测试配置管理器初始化"""
        try:
            from plookingII.config import manager

            # 测试模块可以被导入和使用
            assert manager is not None
        except Exception as e:
            pytest.fail(f"配置管理器初始化失败: {e}")


@pytest.mark.integration()
@pytest.mark.timeout(30)
class TestCacheIntegration:
    """缓存集成测试"""

    def test_cache_system_integration(self, mock_config):
        """测试缓存系统集成"""
        try:
            from plookingII.core import network_cache, simple_cache

            # 验证模块可以协同工作
            assert simple_cache is not None
            assert network_cache is not None
        except Exception as e:
            pytest.fail(f"缓存系统集成测试失败: {e}")


@pytest.mark.integration()
@pytest.mark.slow()
@pytest.mark.timeout(60)
class TestImageLoadingPipeline:
    """图像加载管道集成测试 - 慢测试"""

    def test_image_loading_components(self, sample_image_path):
        """测试图像加载组件"""
        assert sample_image_path.exists()

        try:
            from PIL import Image

            img = Image.open(sample_image_path)
            assert img is not None
            assert img.size == (100, 100)
        except Exception as e:
            pytest.fail(f"图像加载失败: {e}")

    @pytest.mark.skip_ci()
    def test_full_image_pipeline(self, sample_image_path, mock_config):
        """测试完整图像处理管道 - 在CI中跳过"""
        # 这个测试需要完整的GUI环境，在CI中跳过
        try:
            from plookingII.core import image_processing

            # 测试图像处理模块
            assert image_processing is not None
        except Exception as e:
            pytest.fail(f"图像管道测试失败: {e}")


@pytest.mark.integration()
@pytest.mark.db()
@pytest.mark.timeout(20)
class TestDatabaseIntegration:
    """数据库集成测试"""

    def test_db_connection_module(self):
        """测试数据库连接模块"""
        try:
            from plookingII.db import connection

            assert connection is not None
        except Exception as e:
            pytest.fail(f"数据库连接模块导入失败: {e}")


@pytest.mark.integration()
@pytest.mark.ui()
@pytest.mark.timeout(30)
@pytest.mark.skip_ci()
class TestUIIntegration:
    """UI集成测试 - 在CI中跳过"""

    def test_ui_controllers_import(self):
        """测试UI控制器导入"""
        try:
            from plookingII.ui.controllers import image_view_controller, navigation_controller

            assert navigation_controller is not None
            assert image_view_controller is not None
        except Exception as e:
            pytest.fail(f"UI控制器导入失败: {e}")

    def test_ui_managers_import(self):
        """测试UI管理器导入"""
        try:
            from plookingII.ui.managers import folder_manager, image_manager

            assert folder_manager is not None
            assert image_manager is not None
        except Exception as e:
            pytest.fail(f"UI管理器导入失败: {e}")


@pytest.mark.integration()
@pytest.mark.timeout(20)
class TestServiceIntegration:
    """服务集成测试"""

    def test_background_task_manager(self):
        """测试后台任务管理器"""
        try:
            from plookingII.services import background_task_manager

            assert background_task_manager is not None
        except Exception as e:
            pytest.fail(f"后台任务管理器导入失败: {e}")

    def test_history_manager(self):
        """测试历史管理器"""
        try:
            from plookingII.services import history_manager

            assert history_manager is not None
        except Exception as e:
            pytest.fail(f"历史管理器导入失败: {e}")
