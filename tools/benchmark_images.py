#!/usr/bin/env python3
import argparse
import csv
import os
import sys
import time
import tracemalloc
from statistics import median

from plookingII.core.image_processing import HybridImageProcessor


def iter_images(root: str):
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in (".jpg", ".jpeg", ".png"):
                yield os.path.join(dirpath, fn)


def size_bucket(file_path: str) -> str:
    try:
        sz = os.path.getsize(file_path) / (1024 * 1024)
    except Exception:
        return "unknown"
    if sz < 10:
        return "small"
    if sz < 100:
        return "medium"
    return "large"


def run_once(p: HybridImageProcessor, path: str):
    t0 = time.perf_counter()
    img = p.load_image_optimized(path)
    dt = (time.perf_counter() - t0) * 1000.0
    ok = img is not None
    return ok, dt


def main():
    ap = argparse.ArgumentParser(description="Benchmark JPG/PNG loading latency and RSS (local only)")
    ap.add_argument("root", help="root directory of images")
    ap.add_argument("--warmups", type=int, default=1, help="warmup runs per file")
    ap.add_argument("--runs", type=int, default=3, help="measured runs per file")
    ap.add_argument("--out", default="benchmark_results.csv", help="output CSV path")
    args = ap.parse_args()

    p = HybridImageProcessor()

    tracemalloc.start()
    peak_kb = 0

    rows = []
    for path in iter_images(args.root):
        bucket = size_bucket(path)

        # warmups
        for _ in range(args.warmups):
            _ok, _ = run_once(p, path)

        # measured runs
        latencies = []
        ok_count = 0
        for _ in range(args.runs):
            ok, dt = run_once(p, path)
            latencies.append(dt)
            ok_count += int(ok)
            _cur, _peak = tracemalloc.get_traced_memory()
            if _peak > peak_kb:
                peak_kb = _peak

        if latencies:
            latencies.sort()
            p50 = median(latencies)
            p95 = latencies[int(max(0, len(latencies) * 0.95 - 1))]
        else:
            p50 = p95 = 0.0

        rows.append({
            "file": path,
            "bucket": bucket,
            "ok_runs": ok_count,
            "runs": args.runs,
            "p50_ms": f"{p50:.2f}",
            "p95_ms": f"{p95:.2f}",
        })

    # write csv
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "bucket", "ok_runs", "runs", "p50_ms", "p95_ms"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Total files: {len(rows)}")
    print(f"Peak RSS (approx, tracemalloc peak): {peak_kb/1024:.1f} MB")
    print(f"CSV written: {args.out}")


if __name__ == "__main__":
    sys.exit(main())
