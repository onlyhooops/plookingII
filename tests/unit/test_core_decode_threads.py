"""
测试 core/decode_threads.py（v2.9.0 临时线程解码）

覆盖：结果回传、异常传播、超时、异步执行、线程退出语义（新建线程）。
"""

import threading
import time

import pytest

from plookingII.core.decode_threads import run_decode, run_decode_async


class TestRunDecode:
    def test_returns_result(self):
        """同步返回 fn 的结果"""
        assert run_decode(lambda a, b: a + b, 1, 2) == 3

    def test_kwargs_passed(self):
        """透传关键字参数"""
        assert run_decode(lambda **kw: kw["x"], x=42) == 42

    def test_propagates_exception(self):
        """fn 抛异常时向调用方传播"""

        def boom():
            raise ValueError("decode failed")

        with pytest.raises(ValueError, match="decode failed"):
            run_decode(boom)

    def test_runs_in_new_thread(self):
        """解码在新建线程执行（非调用方线程）"""
        caller = threading.get_ident()
        observed: list[int] = []

        def probe():
            observed.append(threading.get_ident())
            return 1

        run_decode(probe)
        assert observed, "探针线程应已执行"
        assert observed[0] != caller

    def test_timeout_returns_none(self):
        """超时返回 None，不中断解码线程"""

        def slow():
            time.sleep(5)
            return "done"

        start = time.time()
        result = run_decode(slow, timeout=0.2)
        assert result is None
        assert time.time() - start < 2.0

    def test_no_join_block_with_fast_fn(self):
        """快速函数不阻塞调用方（线程 join 正常返回）"""
        start = time.time()
        assert run_decode(lambda: 1) == 1
        assert time.time() - start < 1.0


class TestRunDecodeAsync:
    def test_async_runs_and_completes(self):
        """异步执行并在稍后完成"""
        done: list[str] = []

        def work():
            time.sleep(0.05)
            done.append("ok")

        thread = run_decode_async(work)
        assert thread.is_alive() or thread.daemon
        thread.join(timeout=3.0)
        assert done == ["ok"]

    def test_async_exception_does_not_crash(self):
        """异步任务抛异常不向上传播（日志记录）"""

        def boom():
            raise RuntimeError("async boom")

        thread = run_decode_async(boom)
        thread.join(timeout=3.0)
        assert not thread.is_alive()
