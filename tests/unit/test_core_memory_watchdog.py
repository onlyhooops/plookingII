"""
测试 core/memory_watchdog.py

覆盖：RSS 采样回退链、物理内存探测、清理等级判定（含配置覆盖）。
"""

from unittest.mock import patch

from plookingII.core.memory_watchdog import (
    LEVEL_AGGRESSIVE,
    LEVEL_EMERGENCY,
    LEVEL_MODERATE,
    LEVEL_NONE,
    LEVEL_PREVENTIVE,
    choose_cleanup_level,
    get_physical_memory_mb,
    get_process_rss_mb,
)


class TestGetProcessRssMb:
    def test_psutil_primary(self):
        """psutil 可用时优先使用 psutil"""
        with patch("plookingII.core.memory_watchdog._rss_via_psutil", return_value=1234.5):
            assert get_process_rss_mb() == 1234.5

    def test_falls_back_to_mach_task_info(self):
        """psutil 失败时回退 mach task_info"""
        with (
            patch("plookingII.core.memory_watchdog._rss_via_psutil", return_value=None),
            patch("plookingII.core.memory_watchdog._rss_via_mach_task_info", return_value=567.0),
        ):
            assert get_process_rss_mb() == 567.0

    def test_falls_back_to_resource(self):
        """psutil 与 mach 均失败时回退 resource.ru_maxrss"""
        with (
            patch("plookingII.core.memory_watchdog._rss_via_psutil", return_value=None),
            patch("plookingII.core.memory_watchdog._rss_via_mach_task_info", return_value=None),
            patch("plookingII.core.memory_watchdog._rss_via_resource", return_value=88.0),
        ):
            assert get_process_rss_mb() == 88.0

    def test_all_fail_returns_none(self):
        """全部采样失败返回 None（调用方跳过本周期）"""
        with (
            patch("plookingII.core.memory_watchdog._rss_via_psutil", return_value=None),
            patch("plookingII.core.memory_watchdog._rss_via_mach_task_info", return_value=None),
            patch("plookingII.core.memory_watchdog._rss_via_resource", return_value=None),
        ):
            assert get_process_rss_mb() is None

    def test_zero_or_negative_ignored(self):
        """非正采样值视为失败，继续回退"""
        with (
            patch("plookingII.core.memory_watchdog._rss_via_psutil", return_value=0.0),
            patch("plookingII.core.memory_watchdog._rss_via_mach_task_info", return_value=-1.0),
            patch("plookingII.core.memory_watchdog._rss_via_resource", return_value=200.0),
        ):
            assert get_process_rss_mb() == 200.0

    def test_mach_task_info_sampler_safe(self):
        """mach task_info 采样器在异常环境下不抛异常（返回 None）"""
        with patch("plookingII.core.memory_watchdog.ctypes.CDLL", side_effect=OSError("no libSystem")):
            from plookingII.core.memory_watchdog import _rss_via_mach_task_info

            assert _rss_via_mach_task_info() is None


class TestGetPhysicalMemoryMb:
    def test_psutil_primary(self):
        """psutil 可用时优先返回物理内存"""
        with patch("plookingII.core.memory_watchdog._physical_memory_via_psutil", return_value=16384.0):
            assert get_physical_memory_mb() == 16384.0

    def test_sysctl_fallback(self):
        """psutil 失败时回退 sysctl hw.memsize"""
        with (
            patch("plookingII.core.memory_watchdog._physical_memory_via_psutil", return_value=None),
            patch("plookingII.core.memory_watchdog._physical_memory_via_sysctl", return_value=8192.0),
        ):
            assert get_physical_memory_mb() == 8192.0

    def test_default_floor(self):
        """全部失败按 8GB 兜底"""
        with (
            patch("plookingII.core.memory_watchdog._physical_memory_via_psutil", return_value=None),
            patch("plookingII.core.memory_watchdog._physical_memory_via_sysctl", return_value=None),
        ):
            assert get_physical_memory_mb() == 8192.0


class TestChooseCleanupLevel:
    """16GB 物理内存下各等级阈值：
    preventive=max(4915,1024)=4915  moderate=max(6554,1536)=6554
    aggressive=max(9011,2048)=9011  emergency=max(11469,3072)=11469
    """

    PHYS = 16384.0

    def test_below_preventive_is_none(self):
        assert choose_cleanup_level(512.0, self.PHYS) == LEVEL_NONE
        assert choose_cleanup_level(4000.0, self.PHYS) == LEVEL_NONE

    def test_preventive(self):
        assert choose_cleanup_level(5000.0, self.PHYS) == LEVEL_PREVENTIVE

    def test_moderate(self):
        assert choose_cleanup_level(7000.0, self.PHYS) == LEVEL_MODERATE

    def test_aggressive(self):
        assert choose_cleanup_level(9500.0, self.PHYS) == LEVEL_AGGRESSIVE

    def test_emergency(self):
        assert choose_cleanup_level(12000.0, self.PHYS) == LEVEL_EMERGENCY

    def test_boundary_exact_threshold(self):
        """恰等于阈值时命中该等级"""
        assert choose_cleanup_level(9011.2, self.PHYS) == LEVEL_AGGRESSIVE

    def test_invalid_rss_returns_none(self):
        assert choose_cleanup_level(None, self.PHYS) == LEVEL_NONE
        assert choose_cleanup_level(0, self.PHYS) == LEVEL_NONE
        assert choose_cleanup_level(-5, self.PHYS) == LEVEL_NONE

    def test_small_machine_floor_applies(self):
        """4GB 小内存机：预防阈值受绝对下限 1024MB 保护"""
        # 0.30 * 4096 = 1228MB > 1024 → 按比例
        assert choose_cleanup_level(1100.0, 4096.0) == LEVEL_NONE
        assert choose_cleanup_level(1300.0, 4096.0) == LEVEL_PREVENTIVE

    def test_absolute_floor_when_ratio_low(self):
        """极小物理内存时受绝对下限保护（比例可能低于下限）"""
        # 0.30 * 2048 = 614 < 1024 → 下限 1024 生效
        assert choose_cleanup_level(800.0, 2048.0) == LEVEL_NONE
        assert choose_cleanup_level(1100.0, 2048.0) == LEVEL_PREVENTIVE

    def test_physical_mb_auto_detected(self):
        """physical_mb=None 时自动探测"""
        with patch("plookingII.core.memory_watchdog.get_physical_memory_mb", return_value=self.PHYS):
            assert choose_cleanup_level(7000.0) == LEVEL_MODERATE

    def test_config_override(self):
        """配置覆盖阈值（memory.rss_emergency_mb=6000）"""
        with patch(
            "plookingII.core.memory_watchdog._get_config",
            side_effect=lambda key, default: 6000.0 if key == "memory.rss_emergency_mb" else default,
        ):
            # 6000 仅覆盖 emergency：低于该值仍按比例判定 → 5500 为 preventive
            assert choose_cleanup_level(5500.0, self.PHYS) == LEVEL_PREVENTIVE
            # ≥6000 直接命中 emergency
            assert choose_cleanup_level(6500.0, self.PHYS) == LEVEL_EMERGENCY
