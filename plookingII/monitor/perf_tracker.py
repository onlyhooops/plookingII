"""
轻量性能监测跟踪器

在真实使用场景中低开销地聚合、记录项目的关键性能指标，供后续分析与优化：

- 聚合统计：按操作名累计 count / min / avg / p50 / p95 / p99 / max
- 采样控制：支持按操作频率抽样，高频率路径（翻页、图片显示）可配置为
  每 N 次记录 1 次，将开销压到微秒级
- 慢事件捕获：超过阈值的操作（如大文件夹扫描、网络盘跳转）单独留存
- 内存采样：后台线程定期采样当前进程 RSS，报告会话内存走势与峰值
- 会话报告：应用退出（或定期）时输出 JSON + Markdown 报告，自动轮转
  保留最近 N 份，供后续离线分析

设计原则：
- 关闭时（monitor.enabled=false）所有 record 只做一次布尔判断，零开销
- 开启时每次 record 只做一次加锁 + 若干字典更新（微秒级）
- 不存储每条事件，只保留每操作的有限样本（默认 256 个）用于分位数估算

Author: PlookingII Team
"""

import contextlib
import functools
import json
import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Literal, Self

from ..config.constants import APP_NAME, VERSION
from ..config.manager import get_config

logger = logging.getLogger(APP_NAME)

# 可选依赖：进程内存采样需要 psutil（应用发布包已内置）
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:  # pragma: no cover - 取决于运行环境
    psutil = None  # type: ignore[assignment]
    HAS_PSUTIL = False

# 默认输出目录：~/Library/Logs/PlookingII/perf
DEFAULT_REPORT_DIR = os.path.join(os.path.expanduser("~"), "Library", "Logs", APP_NAME, "perf")

# 慢操作阈值（毫秒）：超过该值单独留存事件详情
SLOW_OP_THRESHOLD_MS = 500.0
# 每个操作保留的样本数（用于分位数估算，不存储全部事件）
DEFAULT_SAMPLE_BUDGET = 256
# 内存采样间隔（秒）
MEMORY_SAMPLE_INTERVAL_S = 60.0
# 慢事件留存条数
SLOW_EVENT_BUDGET = 50


def _coerce_bool(value: Any, default: bool) -> bool:
    """安全布尔转换（配置可能来自用户文件/环境变量，甚至是测试中的 Mock）"""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    try:
        return bool(value)
    except Exception:
        return default


def _coerce_int(value: Any, default: int) -> int:
    """安全整数转换，畸形值回退默认"""
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        return default
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def _coerce_str(value: Any, default: str) -> str:
    """安全字符串转换，非字符串（如 Mock）回退默认"""
    return value if isinstance(value, str) else default


def _percentile(sorted_values: list[float], p: float) -> float:
    """线性插值分位数（sorted_values 已升序）"""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


@dataclass
class _OpStats:
    """单个操作名的聚合统计"""

    count: int = 0
    success_count: int = 0
    sum_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    last_ms: float = 0.0
    samples: deque = field(default_factory=lambda: deque(maxlen=DEFAULT_SAMPLE_BUDGET))
    meta_counts: dict[str, dict[str, int]] = field(default_factory=dict)

    def update(self, duration_ms: float, success: bool, meta: dict[str, Any]) -> None:
        """累计一次采样（调用方需持有锁）"""
        self.count += 1
        self.sum_ms += duration_ms
        self.last_ms = duration_ms
        if self.count == 1 or duration_ms < self.min_ms:
            self.min_ms = duration_ms
        self.max_ms = max(self.max_ms, duration_ms)
        if success:
            self.success_count += 1
        self.samples.append(duration_ms)
        for key, value in meta.items():
            if value is None:
                continue
            bucket = self.meta_counts.setdefault(key, {})
            label = str(value)
            bucket[label] = bucket.get(label, 0) + 1

    def to_dict(self) -> dict[str, Any]:
        """导出报告用字典"""
        samples = sorted(self.samples)
        return {
            "count": self.count,
            "success_rate": (self.success_count / self.count) if self.count else 0.0,
            "avg_ms": round(self.sum_ms / self.count, 2) if self.count else 0.0,
            "min_ms": round(self.min_ms, 2) if self.count else 0.0,
            "p50_ms": round(_percentile(samples, 0.50), 2) if samples else 0.0,
            "p95_ms": round(_percentile(samples, 0.95), 2) if samples else 0.0,
            "p99_ms": round(_percentile(samples, 0.99), 2) if samples else 0.0,
            "max_ms": round(self.max_ms, 2) if self.count else 0.0,
            "last_ms": round(self.last_ms, 2) if self.count else 0.0,
            "meta_counts": self.meta_counts,
        }


class PerfTimer:
    """低开销计时上下文管理器

    用法:
        with perf.timeit("folder_scan"):
            do_scan()
    """

    __slots__ = ("_meta", "_op", "_start", "_tracker")

    def __init__(self, tracker: "PerfTracker", op: str, **meta: Any) -> None:
        self._tracker = tracker
        self._op = op
        self._meta = meta
        self._start = 0.0

    def __enter__(self) -> Self:
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> Literal[False]:
        duration_ms = (time.perf_counter() - self._start) * 1000
        self._tracker.record(self._op, duration_ms, success=exc_type is None, **self._meta)
        return False


def perf_timed(op: str, **meta: Any):
    """模块级计时装饰器（在调用时解析全局跟踪器，避免导入期副作用）

    用法:
        @perf_timed("folder_sibling", direction="next")
        def _load_sibling_folder(self, folder_path, parent_dir):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            success = True
            try:
                return func(*args, **kwargs)
            except Exception:
                success = False
                raise
            finally:
                get_perf_tracker().record(op, (time.perf_counter() - start) * 1000, success=success, **meta)

        return wrapper

    return decorator


class PerfTracker:
    """轻量性能监测跟踪器（会话级聚合 + 落盘报告）"""

    def __init__(
        self,
        enabled: bool | None = None,
        sample_rate: int = 1,
        report_dir: str = "",
        max_report_files: int = 20,
        auto_flush_seconds: int = 300,
    ) -> None:
        # 关闭时所有 record 只走一次布尔判断，保持热路径零成本
        if enabled is None:
            enabled = get_config("monitor.enabled", True)
        self._enabled = _coerce_bool(enabled, True)
        self._sample_rate = max(1, _coerce_int(sample_rate, 1))
        self._report_dir = _coerce_str(report_dir, "") or DEFAULT_REPORT_DIR
        self._max_report_files = max(1, _coerce_int(max_report_files, 20))
        self._auto_flush_seconds = max(0, _coerce_int(auto_flush_seconds, 300))

        self._lock = threading.Lock()
        self._ops: dict[str, _OpStats] = {}
        self._op_seq: dict[str, int] = {}
        self._slow_events: deque = deque(maxlen=SLOW_EVENT_BUDGET)
        self._memory_samples: deque = deque(maxlen=1024)
        self._session_start = time.time()
        self._last_memory_sample_at = 0.0
        self._last_flush_at = 0.0
        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None

        if self._enabled:
            self._start_worker()
            logger.debug(
                "PerfTracker 已启用: sample_rate=%s report_dir=%s auto_flush=%ss",
                self._sample_rate,
                self._report_dir,
                self._auto_flush_seconds,
            )

    @property
    def enabled(self) -> bool:
        return self._enabled

    # ------------------------------------------------------------------
    # 记录接口
    # ------------------------------------------------------------------
    def record(self, op: str, duration_ms: float, success: bool = True, **meta: Any) -> None:
        """记录一次操作耗时（热路径安全：关闭时近乎零开销）"""
        if not self._enabled:
            return
        if duration_ms < 0:
            duration_ms = 0.0

        with self._lock:
            # 频率采样：高频率操作按 sample_rate 抽记，计数不影响聚合准确性
            seq = self._op_seq.get(op, 0) + 1
            self._op_seq[op] = seq
            if seq % self._sample_rate != 0:
                return

            stats = self._ops.get(op)
            if stats is None:
                stats = _OpStats()
                self._ops[op] = stats
            stats.update(duration_ms, success, meta)

            if duration_ms >= SLOW_OP_THRESHOLD_MS:
                self._slow_events.append(
                    {
                        "ts": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                        "op": op,
                        "ms": round(duration_ms, 1),
                        "meta": {k: (str(v) if v is not None else None) for k, v in meta.items()},
                    }
                )

            # 会话较长时顺带做一次内存采样（避免单独依赖后台线程的节拍）
            now = time.time()
            if HAS_PSUTIL and (now - self._last_memory_sample_at) >= MEMORY_SAMPLE_INTERVAL_S:
                self._last_memory_sample_at = now
                self._sample_memory_locked(now)

    def timeit(self, op: str, **meta: Any) -> PerfTimer:
        """计时上下文管理器"""
        return PerfTimer(self, op, **meta)

    def timed(self, op: str, **meta: Any):
        """计时装饰器"""

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                success = True
                try:
                    return func(*args, **kwargs)
                except Exception:
                    success = False
                    raise
                finally:
                    self.record(op, (time.perf_counter() - start) * 1000, success=success, **meta)

            return wrapper

        return decorator

    # ------------------------------------------------------------------
    # 内存采样
    # ------------------------------------------------------------------
    def sample_memory(self) -> None:
        """手动触发一次当前进程内存采样"""
        if not self._enabled or not HAS_PSUTIL:
            return
        now = time.time()
        with self._lock:
            self._sample_memory_locked(now)

    def _sample_memory_locked(self, now: float) -> None:
        try:
            rss = psutil.Process().memory_info().rss / (1024 * 1024)
            self._memory_samples.append((now, round(rss, 1)))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 会话报告
    # ------------------------------------------------------------------
    def get_summary(self) -> dict[str, Any]:
        """导出当前会话聚合摘要（不落盘）"""
        with self._lock:
            ops = {name: stats.to_dict() for name, stats in sorted(self._ops.items())}
            memory_mb = self._memory_summary_locked()
            slow = list(self._slow_events)
            return {
                "app": APP_NAME,
                "version": VERSION,
                "enabled": self._enabled,
                "sample_rate": self._sample_rate,
                "session_start": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self._session_start)),
                "session_duration_s": round(time.time() - self._session_start, 1),
                "operations": ops,
                "slow_events": slow,
                "memory_mb": memory_mb,
            }

    def _memory_summary_locked(self) -> dict[str, Any]:
        if not self._memory_samples:
            return {"samples": []}
        values = [v for _, v in self._memory_samples]
        return {
            "start_mb": values[0],
            "peak_mb": max(values),
            "end_mb": values[-1],
            "sample_count": len(values),
            "samples": list(self._memory_samples),
        }

    def flush_report(self, reason: str = "auto") -> str | None:
        """将当前会话摘要写入 JSON + Markdown 报告，返回报告文件路径（失败返回 None）"""
        if not self._enabled:
            return None
        report_dir = self._ensure_report_dir()
        if not report_dir:
            logger.debug("性能报告目录均不可写，跳过落盘")
            return None

        summary = self.get_summary()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base_name = f"perf_{timestamp}_{reason}"
        json_path = os.path.join(report_dir, f"{base_name}.json")
        md_path = os.path.join(report_dir, f"{base_name}.md")

        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(self._render_markdown(summary))
            self._rotate_reports()
            self._last_flush_at = time.time()
            logger.info("性能报告已写入: %s", json_path)
            return json_path
        except Exception:
            logger.debug("写入性能报告失败", exc_info=True)
            return None

    def _ensure_report_dir(self) -> str | None:
        """获取可写的报告目录：配置目录 → 默认日志目录 → 系统临时目录"""
        import tempfile

        candidates = [self._report_dir]
        if self._report_dir != DEFAULT_REPORT_DIR:
            candidates.append(DEFAULT_REPORT_DIR)
        candidates.append(os.path.join(tempfile.gettempdir(), "PlookingII-perf"))

        for candidate in candidates:
            try:
                os.makedirs(candidate, exist_ok=True)
                probe = os.path.join(candidate, ".perf_probe")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("")
                os.remove(probe)
                return candidate
            except OSError:
                continue
        return None

    @staticmethod
    def _render_markdown(summary: dict[str, Any]) -> str:
        """将摘要渲染为人类可读的 Markdown 报告"""
        lines = [
            "# PlookingII 性能报告",
            "",
            f"- 版本: {summary.get('version', '')}",
            f"- 会话开始: {summary.get('session_start', '')}",
            f"- 会话时长: {summary.get('session_duration_s', 0)} 秒",
            f"- 采样频率: 每 {summary.get('sample_rate', 1)} 次记录 1 次",
            "",
            "## 操作统计（毫秒）",
            "",
            "| 操作 | 次数 | 成功率 | avg | p50 | p95 | p99 | min | max |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        ops = summary.get("operations", {})
        if not ops:
            lines.append("| （无记录） | - | - | - | - | - | - | - | - |")
        else:
            for name, s in ops.items():
                lines.append(
                    f"| {name} | {s['count']} | {s['success_rate']:.0%} | {s['avg_ms']} "
                    f"| {s['p50_ms']} | {s['p95_ms']} | {s['p99_ms']} | {s['min_ms']} | {s['max_ms']} |"
                )

        memory = summary.get("memory_mb", {})
        if memory.get("samples"):
            lines += [
                "",
                "## 进程内存（MB）",
                "",
                f"- 起始: {memory['start_mb']} / 峰值: {memory['peak_mb']} / 结束: {memory['end_mb']}",
                f"- 采样点数: {memory['sample_count']}",
            ]

        slow = summary.get("slow_events", [])
        if slow:
            lines += [
                "",
                "## 慢事件（>500ms）",
                "",
                "| 时间 | 操作 | 耗时(ms) | 附加信息 |",
                "| --- | --- | --- | --- |",
            ]
            for ev in slow:
                meta = ev.get("meta") or {}
                meta_str = ", ".join(f"{k}={v}" for k, v in meta.items() if v is not None) or "-"
                lines.append(f"| {ev['ts']} | {ev['op']} | {ev['ms']} | {meta_str} |")

        lines.append("")
        return "\n".join(lines)

    def _rotate_reports(self) -> None:
        """按数量轮转报告：仅保留最近 max_report_files 份 JSON（连同对应 MD）"""
        try:
            report_dir = self._ensure_report_dir()
            if not report_dir:
                return
            candidates = [
                os.path.join(report_dir, name)
                for name in os.listdir(report_dir)
                if name.startswith("perf_") and name.endswith(".json")
            ]
            candidates.sort(key=os.path.getmtime)
            excess = len(candidates) - self._max_report_files
            for path in candidates[:excess]:
                with contextlib.suppress(OSError):
                    os.remove(path)
                md = os.path.splitext(path)[0] + ".md"
                with contextlib.suppress(OSError):
                    os.remove(md)
        except Exception:
            logger.debug("性能报告轮转失败", exc_info=True)

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def _start_worker(self) -> None:
        """后台线程：定期内存采样 + 自动落盘（仅在启用自动落盘时启动）"""
        if self._auto_flush_seconds <= 0:
            return

        def worker_loop():
            while not self._stop_event.wait(10.0):
                now = time.time()
                if HAS_PSUTIL and (now - self._last_memory_sample_at) >= MEMORY_SAMPLE_INTERVAL_S:
                    self.sample_memory()
                if (
                    self._auto_flush_seconds > 0
                    and self._ops
                    and (now - self._last_flush_at) >= self._auto_flush_seconds
                ):
                    self.flush_report(reason="auto")

        self._worker_thread = threading.Thread(target=worker_loop, daemon=True, name="perf-tracker")
        self._worker_thread.start()

    def shutdown(self) -> None:
        """停止后台线程并落盘最终报告"""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
            self._worker_thread = None
        if self._enabled:
            self.sample_memory()
            self.flush_report(reason="quit")


# 全局单例（与 UnifiedMonitor 并行：前者用于运行时自适应，本跟踪器用于离线分析）
_global_tracker: PerfTracker | None = None
_tracker_lock = threading.Lock()


def get_perf_tracker() -> PerfTracker:
    """获取全局性能跟踪器单例"""
    global _global_tracker  # noqa: PLW0603
    with _tracker_lock:
        if _global_tracker is None:
            from ..config.manager import Config

            cfg = Config.get_perf_tracker_config()
            _global_tracker = PerfTracker(
                enabled=cfg["enabled"],
                sample_rate=cfg["sample_rate"],
                report_dir=cfg["report_dir"],
                max_report_files=cfg["max_report_files"],
                auto_flush_seconds=cfg["auto_flush_seconds"],
            )
        return _global_tracker


def shutdown_perf_tracker() -> None:
    """应用退出时调用：停止跟踪器并输出最终报告"""
    global _global_tracker  # noqa: PLW0603
    with _tracker_lock:
        tracker = _global_tracker
        _global_tracker = None
    if tracker is not None:
        tracker.shutdown()
