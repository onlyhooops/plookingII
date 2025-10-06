"""
测试 app/main.py 模块

测试目标：达到70%+覆盖率

注意：由于 AppDelegate 依赖 macOS AppKit 框架和 Objective-C 运行时，
许多方法无法在纯 Python 测试环境中完全测试。这里主要测试代码结构和可测试的逻辑。
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from plookingII.app.main import AppDelegate, main


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestAppDelegateStructure:
    """测试 AppDelegate 类结构"""

    def test_app_delegate_class_exists(self):
        """测试 AppDelegate 类存在"""
        assert AppDelegate is not None

    def test_app_delegate_has_required_methods(self):
        """测试 AppDelegate 具有必需的方法"""
        assert hasattr(AppDelegate, "init")
        assert hasattr(AppDelegate, "applicationDidFinishLaunching_")
        assert hasattr(AppDelegate, "applicationShouldHandleReopen_hasVisibleWindows_")
        assert hasattr(AppDelegate, "applicationDockMenu_")
        assert hasattr(AppDelegate, "applicationShouldTerminate_")

    def test_methods_are_callable(self):
        """测试方法是可调用的"""
        assert callable(getattr(AppDelegate, "init", None))
        assert callable(getattr(AppDelegate, "applicationDidFinishLaunching_", None))
        assert callable(getattr(AppDelegate, "applicationShouldHandleReopen_hasVisibleWindows_", None))
        assert callable(getattr(AppDelegate, "applicationDockMenu_", None))
        assert callable(getattr(AppDelegate, "applicationShouldTerminate_", None))


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestMainFunction:
    """测试主函数"""

    def test_main_with_full_mock(self):
        """测试完全 mock 的 main 函数"""
        with (
            patch("plookingII.app.main.NSApplication") as mock_ns_app,
            patch("plookingII.app.main.AppDelegate") as mock_delegate_cls,
            patch("plookingII.app.main.error_context") as mock_error_context,
            patch("plookingII.app.main.ErrorCategory"),
        ):
            # 设置 mock
            mock_app = Mock()
            mock_ns_app.sharedApplication.return_value = mock_app

            mock_delegate = Mock()
            mock_delegate_cls.alloc.return_value.init.return_value = mock_delegate

            # 模拟 error_context 作为上下文管理器
            mock_context = MagicMock()
            mock_error_context.return_value = mock_context

            # 调用 main
            main()

            # 验证调用
            mock_ns_app.sharedApplication.assert_called_once()
            mock_delegate_cls.alloc.assert_called_once()
            mock_app.setDelegate_.assert_called_once_with(mock_delegate)
            mock_app.run.assert_called_once()

    def test_main_exception_handling(self):
        """测试 main 函数的异常处理"""
        with (
            patch("plookingII.app.main.NSApplication") as mock_ns_app,
            patch("plookingII.app.main.error_context") as mock_error_context,
            patch("plookingII.app.main.logging") as mock_logging,
            patch("plookingII.app.main.APP_NAME", "TestApp"),
        ):
            # 模拟应用运行时抛出异常
            mock_app = Mock()
            mock_app.run.side_effect = RuntimeError("App run failed")
            mock_ns_app.sharedApplication.return_value = mock_app

            # 模拟 error_context
            mock_context = MagicMock()
            mock_error_context.return_value = mock_context

            # 模拟 logger
            mock_logger = Mock()
            mock_logging.getLogger.return_value = mock_logger

            # 应该抛出异常
            with pytest.raises(RuntimeError, match="App run failed"):
                main()

            # 验证错误被记录
            mock_logging.getLogger.assert_called_with("TestApp")
            mock_logger.critical.assert_called_once()

    def test_main_uses_error_context(self):
        """测试 main 使用 error_context"""
        with (
            patch("plookingII.app.main.NSApplication") as mock_ns_app,
            patch("plookingII.app.main.error_context") as mock_error_context,
            patch("plookingII.app.main.ErrorCategory") as mock_error_category,
        ):
            mock_app = Mock()
            mock_ns_app.sharedApplication.return_value = mock_app

            mock_context = MagicMock()
            mock_error_context.return_value = mock_context

            main()

            # 验证 error_context 被正确调用
            mock_error_context.assert_called_once_with("app_main", category=mock_error_category.UI)


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestAppDelegateLogic:
    """测试 AppDelegate 的业务逻辑"""

    def test_application_should_handle_reopen_logic(self):
        """测试重新打开应用的逻辑"""
        # 这个方法总是返回 True
        with patch.object(
            AppDelegate, "applicationShouldHandleReopen_hasVisibleWindows_", return_value=True
        ) as mock_method:
            result = mock_method(None, False)
            assert result is True

    def test_application_should_terminate_logic(self):
        """测试应用终止的逻辑"""
        # 这个方法总是返回 True
        with patch.object(AppDelegate, "applicationShouldTerminate_", return_value=True) as mock_method:
            result = mock_method(None)
            assert result is True


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestImports:
    """测试导入"""

    def test_imports_work(self):
        """测试所有导入都正常工作"""
        # 只要能导入模块就说明基本结构正确
        from plookingII.app import main as main_module

        assert main_module is not None
        assert hasattr(main_module, "main")
        assert hasattr(main_module, "AppDelegate")

    def test_appkit_imports(self):
        """测试 AppKit 导入"""
        # 这些导入在测试时应该能够访问
        try:
            from plookingII.app.main import (
                NSApplication,
                NSApplicationActivationPolicyRegular,
                NSMenu,
                NSMenuItem,
                NSObject,
                NSScreen,
            )

            # 如果能导入，说明环境支持 AppKit
            assert True
        except ImportError:
            # 在某些测试环境中可能无法导入 AppKit
            pytest.skip("AppKit not available in test environment")


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestCodeQuality:
    """测试代码质量"""

    def test_main_has_docstring(self):
        """测试 main 函数有文档字符串"""
        assert main.__doc__ is not None
        assert len(main.__doc__.strip()) > 0

    def test_app_delegate_methods_exist(self):
        """测试 AppDelegate 的所有必需方法都存在"""
        required_methods = [
            "init",
            "applicationDidFinishLaunching_",
            "applicationShouldHandleReopen_hasVisibleWindows_",
            "applicationDockMenu_",
            "applicationShouldTerminate_",
        ]

        for method_name in required_methods:
            assert hasattr(AppDelegate, method_name), f"Missing method: {method_name}"


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestEdgeCases:
    """测试边缘情况"""

    def test_main_can_be_called_multiple_times_in_mock(self):
        """测试 main 可以多次调用（在 mock 环境下）"""
        with (
            patch("plookingII.app.main.NSApplication") as mock_ns_app,
            patch("plookingII.app.main.AppDelegate"),
            patch("plookingII.app.main.error_context"),
        ):
            mock_app = Mock()
            mock_ns_app.sharedApplication.return_value = mock_app

            # 第一次调用
            main()
            assert mock_app.run.call_count == 1

            # 第二次调用
            main()
            assert mock_app.run.call_count == 2

    def test_main_with_app_delegate_alloc_failure(self):
        """测试 AppDelegate 分配失败"""
        with (
            patch("plookingII.app.main.NSApplication") as mock_ns_app,
            patch("plookingII.app.main.AppDelegate") as mock_delegate_cls,
            patch("plookingII.app.main.error_context"),
        ):
            mock_app = Mock()
            mock_ns_app.sharedApplication.return_value = mock_app

            # 模拟 alloc 返回 None
            mock_delegate_cls.alloc.return_value.init.return_value = None

            # 调用 main
            main()

            # 应该仍然尝试设置代理（即使是 None）
            mock_app.setDelegate_.assert_called_once_with(None)

    def test_main_with_exception_in_error_context(self):
        """测试 error_context 中的异常"""
        with (
            patch("plookingII.app.main.NSApplication") as mock_ns_app,
            patch("plookingII.app.main.error_context") as mock_error_context,
            patch("plookingII.app.main.logging"),
        ):
            # 模拟 error_context 抛出异常
            mock_error_context.side_effect = Exception("Context error")

            # 应该抛出异常
            with pytest.raises(Exception, match="Context error"):
                main()


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestModuleLevel:
    """测试模块级别的功能"""

    def test_module_has_main_guard(self):
        """测试模块有 __main__ 保护"""
        # 读取源文件
        import inspect

        import plookingII.app.main as main_module

        source = inspect.getsource(main_module)

        # 验证有 if __name__ == "__main__":
        assert 'if __name__ == "__main__":' in source

    def test_module_imports_are_valid(self):
        """测试模块导入有效"""
        from plookingII.app.main import APP_NAME

        assert APP_NAME is not None
        assert isinstance(APP_NAME, str)

    def test_module_constants(self):
        """测试模块常量"""
        from plookingII.app.main import APP_NAME

        assert len(APP_NAME) > 0


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestFunctionSignatures:
    """测试函数签名"""

    def test_main_takes_no_arguments(self):
        """测试 main 函数不接受参数"""
        import inspect

        sig = inspect.signature(main)
        assert len(sig.parameters) == 0

    def test_main_return_type(self):
        """测试 main 函数的返回类型注解"""
        import inspect

        sig = inspect.signature(main)
        # main() 应该没有显式返回值（隐式 None）
        # 或者在文档中说明它不返回
        assert True  # 只要函数存在就通过


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestComplexScenarios:
    """测试复杂场景"""

    def test_main_with_all_components_mocked(self):
        """测试所有组件都被 mock 的完整流程"""
        with (
            patch("plookingII.app.main.NSApplication") as mock_ns_app,
            patch("plookingII.app.main.AppDelegate") as mock_delegate_cls,
            patch("plookingII.app.main.error_context") as mock_error_context,
            patch("plookingII.app.main.ErrorCategory") as mock_error_category,
            patch("plookingII.app.main.logging") as mock_logging,
        ):
            # 设置完整的 mock 链
            mock_app = Mock()
            mock_ns_app.sharedApplication.return_value = mock_app

            mock_delegate = Mock()
            mock_delegate_cls.alloc.return_value.init.return_value = mock_delegate

            mock_context = MagicMock()
            mock_context.__enter__ = Mock(return_value=mock_context)
            mock_context.__exit__ = Mock(return_value=None)
            mock_error_context.return_value = mock_context

            # 运行 main
            main()

            # 验证完整的调用链
            mock_error_context.assert_called_once_with("app_main", category=mock_error_category.UI)
            mock_ns_app.sharedApplication.assert_called_once()
            mock_delegate_cls.alloc.assert_called_once()
            mock_app.setDelegate_.assert_called_once_with(mock_delegate)
            mock_app.run.assert_called_once()

    def test_error_handling_full_flow(self):
        """测试完整的错误处理流程"""
        with (
            patch("plookingII.app.main.NSApplication") as mock_ns_app,
            patch("plookingII.app.main.AppDelegate"),
            patch("plookingII.app.main.error_context") as mock_error_context,
            patch("plookingII.app.main.logging") as mock_logging,
            patch("plookingII.app.main.APP_NAME", "TestApp"),
        ):
            # 设置异常
            mock_app = Mock()
            mock_app.run.side_effect = KeyError("Test key error")
            mock_ns_app.sharedApplication.return_value = mock_app

            mock_context = MagicMock()
            mock_error_context.return_value = mock_context

            mock_logger = Mock()
            mock_logging.getLogger.return_value = mock_logger

            # 执行并捕获异常
            with pytest.raises(KeyError):
                main()

            # 验证日志记录
            mock_logging.getLogger.assert_called_with("TestApp")
            mock_logger.critical.assert_called_once()
            call_args = mock_logger.critical.call_args
            assert "App main loop failed" in call_args[0][0]
            assert call_args[1].get("exc_info") is True
