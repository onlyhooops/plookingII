#!/usr/bin/env python3
"""
Summarize fallback metrics for PlookingII from runtime counters and logs.

Usage:
  python -m tools.fallback_metrics_cli [--log-dir <dir>]

It reads:
- In-memory counters via lightweight import (best-effort)
- Rotating error log for keywords (best-effort when available)
"""

import argparse
import os
import re
from typing import Dict


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PlookingII fallback metrics summary")
    parser.add_argument("--log-dir", default=os.path.expanduser("~/Library/Logs/PlookingII"))
    return parser.parse_args()


def summarize_runtime_counters() -> Dict[str, int]:
    # Best-effort: construct strategies to read current counters
    metrics: Dict[str, int] = {}
    try:
        from plookingII.core.optimized_loading_strategies import OptimizedLoadingStrategy

        strat = OptimizedLoadingStrategy()
        # Only report structure keys (0 if never used in this process)
        metrics["optimized.fallback_attempts"] = int(strat.stats.get("fallback_attempts", 0))
        metrics["optimized.fallback_successes"] = int(strat.stats.get("fallback_successes", 0))
    except Exception:
        # Not critical
        pass

    try:
        from plookingII.core.image_rotation import ImageRotationProcessor

        rot = ImageRotationProcessor()
        rs = rot.get_rotation_stats()
        metrics["rotation.lossless_attempts"] = int(rs.get("lossless_attempts", 0))
        metrics["rotation.lossless_successes"] = int(rs.get("lossless_successes", 0))
        metrics["rotation.pil_fallbacks"] = int(rs.get("pil_fallbacks", 0))
    except Exception:
        pass

    return metrics


def summarize_logs(log_dir: str) -> Dict[str, int]:
    counters: Dict[str, int] = {
        "log.optimized.fallback": 0,
        "log.optimized.quartz_fail": 0,
        "log.rotation.error": 0,
    }
    try:
        re.compile(r"(Fallback load|Quartz .* failed|rotation failed)", re.IGNORECASE)
        for name in os.listdir(log_dir):
            if not name.endswith(".log"):
                continue
            path = os.path.join(log_dir, name)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if "Fallback load" in line:
                            counters["log.optimized.fallback"] += 1
                        elif "Quartz" in line and "failed" in line:
                            counters["log.optimized.quartz_fail"] += 1
                        elif "rotate" in line and "failed" in line:
                            counters["log.rotation.error"] += 1
            except Exception:
                continue
    except Exception:
        pass
    return counters


def main() -> None:
    args = parse_args()
    runtime = summarize_runtime_counters()
    logs = summarize_logs(args.log_dir)

    print("PlookingII Fallback Metrics Summary")
    print("=================================")
    for k in sorted(runtime.keys()):
        print(f"{k}: {runtime[k]}")
    for k in sorted(logs.keys()):
        print(f"{k}: {logs[k]}")


if __name__ == "__main__":
    main()
