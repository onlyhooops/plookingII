from unittest import mock
from contextlib import ExitStack
import sys
import os
import pytest

# Skip entirely in Release CI to accelerate packaging
if os.environ.get("PLOOKINGII_RELEASE_CI") == "1":
    pytest.skip("skip in release CI", allow_module_level=True)

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only Quartz/AppKit pipeline")

from plookingII.core.optimized_loading_strategies import (
    OptimizedLoadingStrategy,
    PreviewLoadingStrategy,
    AutoLoadingStrategy,
)


def test_optimized_strategy_selects_path_by_file_size(tmp_path):
    f_small = tmp_path / "small.jpg"
    f_small.write_bytes(b"0" * (5 * 1024))  # ~5KB
    f_medium = tmp_path / "medium.jpg"
    f_medium.write_bytes(b"0" * (15 * 1024 * 1024))  # 15MB
    f_large = tmp_path / "large.jpg"
    f_large.write_bytes(b"0" * (120 * 1024 * 1024))  # 120MB

    strat = OptimizedLoadingStrategy()

    # stub NSImage/CG pipeline to avoid macOS deps, just return a truthy object
    with ExitStack() as stack:
        fast = stack.enter_context(mock.patch.object(strat, "_load_with_fast_nsimage", return_value=object()))
        quartz = stack.enter_context(mock.patch.object(strat, "_load_with_quartz", return_value=object()))
        mm = stack.enter_context(mock.patch.object(strat, "_load_with_memory_mapping", return_value=object()))

        assert strat.load(str(f_small)) is not None
        assert fast.called

        fast.reset_mock(); quartz.reset_mock(); mm.reset_mock()
        assert strat.load(str(f_medium)) is not None
        assert quartz.called

        fast.reset_mock(); quartz.reset_mock(); mm.reset_mock()
        assert strat.load(str(f_large)) is not None
        assert mm.called


def test_optimized_strategy_fallback_on_fail(tmp_path):
    f = tmp_path / "x.jpg"
    f.write_bytes(b"123")
    strat = OptimizedLoadingStrategy()
    with mock.patch.object(strat, "_get_file_size_mb", return_value=1.0), \
         mock.patch.object(strat, "_load_with_fast_nsimage", return_value=None), \
         mock.patch.object(strat, "_fallback_load", return_value=object()) as fb:
        assert strat.load(str(f)) is not None
        assert fb.called


def test_preview_strategy_generates_thumbnail(tmp_path):
    f = tmp_path / "x.jpg"
    f.write_bytes(b"123")
    strat = PreviewLoadingStrategy()
    # stub quartz, return truthy
    with mock.patch.object(strat, "_generate_thumbnail_with_quartz", return_value=object()) as gen:
        assert strat.load(str(f), target_size=(128, 128)) is not None
        assert gen.called


def test_auto_strategy_prefers_preview_when_target_size(tmp_path):
    f = tmp_path / "x.jpg"
    f.write_bytes(b"0" * 1024)
    auto = AutoLoadingStrategy()

    # replace strategies with spies
    preview = PreviewLoadingStrategy()
    optimized = OptimizedLoadingStrategy()
    with mock.patch.object(preview, "load", return_value=object()) as p_load, \
         mock.patch.object(optimized, "load", return_value=object()) as o_load:
        auto.strategies = [optimized, preview]
        img = auto.load(str(f), target_size=(256, 256))
        assert img is not None
        assert p_load.called  # preview chosen first when target_size is provided
