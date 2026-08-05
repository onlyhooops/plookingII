"""
配置模块单元测试
演示基本的单元测试模式
"""

import pytest


@pytest.mark.unit
class TestConfigManager:
    """配置管理器测试"""

    def test_config_imports(self):
        """测试配置模块导入"""
        try:
            from plookingII.config import constants, manager
            assert hasattr(constants, "VERSION")
        except ImportError as e:
            pytest.fail(f"配置模块导入失败: {e}")

    def test_version_format(self):
        """测试版本号格式"""
        from plookingII.config import constants

        assert hasattr(constants, "VERSION")
        version = constants.VERSION
        assert isinstance(version, str)
        assert len(version) > 0

        # 版本号应该是 x.y.z 格式
        parts = version.split(".")
        assert len(parts) >= 2, "版本号应该至少包含主版本和次版本"


@pytest.mark.unit
class TestUIStrings:
    """UI字符串配置测试"""

    def test_ui_strings_import(self):
        """测试UI字符串模块导入"""
        try:
            from plookingII.config import ui_strings
            assert ui_strings is not None
        except ImportError as e:
            pytest.fail(f"UI字符串模块导入失败: {e}")

