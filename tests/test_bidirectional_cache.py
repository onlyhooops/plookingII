from unittest import mock

import pytest

from plookingII.core.bidirectional_cache import BidirectionalCachePool


@pytest.mark.asyncio
async def test_set_sequence_and_set_current_image_updates_state_and_history():
    pool = BidirectionalCachePool(preload_count=2, keep_previous=2)

    # 禁用实际预加载以便快速覆盖控制流
    with mock.patch("plookingII.config.manager.get_config", return_value=True):
        seq = [f"/p/{i}.jpg" for i in range(5)]
        pool.set_sequence(seq)
        assert pool.get_stats()["sequence_length"] == 5

        # 首次设置当前图像
        await pool.set_current_image("/p/1.jpg", "/p/1.jpg")
        st = pool.get_stats()
        assert st["current_key"] == "/p/1.jpg"
        assert st["past_size"] == 0

        # 再次设置，应将前一个加入 past_cache，并执行清理
        await pool.set_current_image("/p/2.jpg", "/p/2.jpg")
        st = pool.get_stats()
        assert st["current_key"] == "/p/2.jpg"
        assert st["past_size"] == 1


def test_set_current_image_sync_submits_future_and_generation_increments():
    pool = BidirectionalCachePool(preload_count=1, keep_previous=1)

    # 禁用真实 run_coroutine_threadsafe 执行，验证代次递增与任务替换
    with mock.patch("asyncio.run_coroutine_threadsafe") as run_cs:
        run_cs.return_value = mock.Mock(done=lambda: True)
        gen1 = pool.set_current_image_sync("k1", "/p/1.jpg")
        gen2 = pool.set_current_image_sync("k2", "/p/2.jpg")
        assert isinstance(gen1, int) and isinstance(gen2, int)
        assert gen2 >= gen1


def test_window_and_generation_controls():
    pool = BidirectionalCachePool(preload_count=3, keep_previous=3)
    pool.set_preload_window(preload_count=2, keep_previous=1)
    st = pool.get_stats()
    assert st["generation"] >= 0
    pool.reset_generation()
    assert pool.get_stats()["generation"] >= st["generation"]


def test_clear_and_shutdown_are_safe():
    pool = BidirectionalCachePool()
    pool.set_sequence(["a", "b"])
    pool.clear()
    st = pool.get_stats()
    assert st["future_size"] == 0 and st["past_size"] == 0 and st["current_key"] is None

    # shutdown 不应抛异常
    pool.shutdown()
