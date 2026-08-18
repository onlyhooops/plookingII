"""
测试 core/autorelease.py

覆盖 objc_autorelease_pool 上下文管理器：
- 在可用环境下创建并 drain 自动释放池（可用时验证对象仍可访问）
- 异常传播：with 内抛异常不吞
- 嵌套使用安全
"""

import pytest

from plookingII.core.autorelease import _AUTORELEASE_AVAILABLE, objc_autorelease_pool


class TestAutoreleasePool:
    def test_context_manager_runs(self):
        """with 块正常执行"""
        ran = []

        with objc_autorelease_pool():
            ran.append(1)

        assert ran == [1]

    def test_exception_propagates(self):
        """with 内异常不被吞掉"""
        with pytest.raises(ValueError, match="boom"):
            with objc_autorelease_pool():
                raise ValueError("boom")

    def test_nested_pools_safe(self):
        """嵌套使用不冲突"""
        order = []

        with objc_autorelease_pool():
            order.append("outer-in")
            with objc_autorelease_pool():
                order.append("inner-in")
            order.append("outer-out")

        assert order == ["outer-in", "inner-in", "outer-out"]

    @pytest.mark.skipif(not _AUTORELEASE_AVAILABLE, reason="Foundation 不可用")
    def test_objects_usable_after_pool(self):
        """pool 内创建的对象在 with 结束后仍可访问（不被误释放）"""
        from Foundation import NSDictionary

        with objc_autorelease_pool():
            obj = NSDictionary.dictionaryWithObject_forKey_("value", "key")

        # 对象仍有效（Python 引用计数持有）
        assert obj.objectForKey_("key") == "value"
