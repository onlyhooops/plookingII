"""
核心模块单元测试
演示复杂模块的测试策略
"""


import pytest


@pytest.mark.unit
class TestCoreImports:
    """核心模块导入测试"""

    def test_functions_import(self):
        """测试函数模块导入"""
        try:
            from plookingII.core import functions

            assert functions is not None
        except ImportError as e:
            pytest.fail(f"函数模块导入失败: {e}")

    def test_globals_import(self):
        """测试全局变量模块导入"""
        try:
            from plookingII.core import globals

            assert globals is not None
        except ImportError as e:
            pytest.fail(f"全局变量模块导入失败: {e}")


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestCacheModules:
    """缓存模块测试 - 带超时保护"""

    def test_simple_cache_import(self):
        """测试简化缓存导入"""
        try:
            from plookingII.core import simple_cache

            assert simple_cache is not None
            # 测试关键类
            from plookingII.core.simple_cache import (
                AdvancedImageCache,
                BidirectionalCachePool,
                SimpleImageCache,
            )

            assert SimpleImageCache is not None
            assert AdvancedImageCache is not None
            assert BidirectionalCachePool is not None
        except ImportError as e:
            pytest.fail(f"简化缓存模块导入失败: {e}")

    def test_loading_module_import(self):
        """测试加载模块导入"""
        try:
            from plookingII.core import loading

            assert loading is not None
            from plookingII.core.loading import get_loader

            assert get_loader is not None
        except ImportError as e:
            pytest.fail(f"加载模块导入失败: {e}")

@pytest.mark.unit
class TestImageProcessing:
    """图像处理测试"""

    def test_image_processing_import(self):
        """测试图像处理模块导入"""
        try:
            from plookingII.core import image_processing

            assert image_processing is not None
        except ImportError as e:
            pytest.fail(f"图像处理模块导入失败: {e}")

@pytest.mark.unit
@pytest.mark.network
@pytest.mark.timeout(10)
class TestNetworkModules:
    """网络模块测试 - 带超时和网络标记"""

    def test_network_cache_import(self):
        """测试网络缓存导入"""
        try:
            from plookingII.core import network_cache

            assert network_cache is not None
        except ImportError as e:
            pytest.fail(f"网络缓存模块导入失败: {e}")

    def test_remote_file_detector_import(self):
        """测试远程文件检测器导入"""
        try:
            from plookingII.core import remote_file_detector

            assert remote_file_detector is not None
        except ImportError as e:
            pytest.fail(f"远程文件检测器模块导入失败: {e}")

    def test_remote_file_manager_import(self):
        """测试远程文件管理器导入"""
        try:
            from plookingII.core import remote_file_manager

            assert remote_file_manager is not None
        except ImportError as e:
            pytest.fail(f"远程文件管理器模块导入失败: {e}")

    @pytest.mark.external
    def test_smb_optimizer_import(self):
        """测试SMB优化器导入 - 需要外部依赖"""
        try:
            from plookingII.core import smb_optimizer

            assert smb_optimizer is not None
        except ImportError as e:
            pytest.fail(f"SMB优化器模块导入失败: {e}")
