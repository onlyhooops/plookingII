#!/usr/bin/env python3
"""
Aggregate benchmark CSV into bucket-level summary reports.

Inputs:
  - --input: path to bench csv (default: bench.csv)
  - --outdir: output directory for reports (default: reports)

Outputs (written into outdir):
  - bench_summary.csv
  - bench_summary.json
"""
import argparse
import csv
import json
import os
from statistics import median


def parse_float_safe(v: str) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def load_rows(path: str):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def aggregate(rows):
    # group by bucket
    buckets = {}
    for r in rows:
        b = r.get("bucket") or "unknown"
        buckets.setdefault(b, {"latencies": [], "ok_runs": 0, "runs": 0, "files": 0})
        buckets[b]["latencies"].append(parse_float_safe(r.get("p50_ms", "0")))
        buckets[b]["ok_runs"] += int(r.get("ok_runs", 0))
        buckets[b]["runs"] += int(r.get("runs", 0))
        buckets[b]["files"] += 1

    # compute summary
    summary = []
    for b, s in buckets.items():
        lats = s["latencies"]
        p50 = median(lats) if lats else 0.0
        p95 = sorted(lats)[int(max(0, len(lats) * 0.95 - 1))] if lats else 0.0
        ok_rate = (s["ok_runs"] / max(1, s["runs"])) * 100.0
        summary.append(
            {
                "bucket": b,
                "files": s["files"],
                "ok_rate_pct": round(ok_rate, 2),
                "p50_ms": round(p50, 2),
                "p95_ms": round(p95, 2),
            }
        )
    # stable order
    bucket_order = {"small": 0, "medium": 1, "large": 2}
    summary.sort(key=lambda x: bucket_order.get(x["bucket"], 99))
    return summary


def write_reports(summary, outdir: str):
    os.makedirs(outdir, exist_ok=True)
    # CSV
    csv_path = os.path.join(outdir, "bench_summary.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["bucket", "files", "ok_rate_pct", "p50_ms", "p95_ms"])
        w.writeheader()
        for r in summary:
            w.writerow(r)
    # JSON
    json_path = os.path.join(outdir, "bench_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary}, f, ensure_ascii=False, indent=2)
    return csv_path, json_path


def main():
    ap = argparse.ArgumentParser(description="Generate benchmark trend summary")
    ap.add_argument("--input", default="bench.csv", help="input benchmark csv path")
    ap.add_argument("--outdir", default="reports", help="output directory")
    args = ap.parse_args()

    rows = load_rows(args.input)
    summary = aggregate(rows)
    csv_path, json_path = write_reports(summary, args.outdir)
    print(f"Summary written: {csv_path}, {json_path}")


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
PACKAGE = "plookingII"
TESTS = ROOT / "tests"

REPORTS.mkdir(parents=True, exist_ok=True)


def run(cmd: list[str], outfile: Path | None = None) -> int:
    print("$", " ".join(cmd))
    try:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        stdout = proc.stdout
        stderr = proc.stderr
        if outfile:
            outfile.write_text(stdout or "")
        else:
            sys.stdout.write(stdout)
        if stderr:
            sys.stderr.write(stderr)
        return proc.returncode
    except FileNotFoundError:
        msg = f"Command not found: {cmd[0]}\n"
        if outfile:
            outfile.write_text(msg)
        sys.stderr.write(msg)
        return 127

# 1) flake8 report
run([sys.executable, "-m", "flake8", PACKAGE], REPORTS / "flake8_report.txt")

# 2) radon complexity (cc) and maintainability index (mi)
run([sys.executable, "-m", "radon", "cc", PACKAGE, "-s", "-a"], REPORTS / "radon_cc_report.txt")
run([sys.executable, "-m", "radon", "mi", PACKAGE, "-s"], REPORTS / "radon_mi_report.txt")

# 3) coverage (run tests then report)
run([sys.executable, "-m", "coverage", "erase"])  # best-effort
run([sys.executable, "-m", "coverage", "run", "-m", "pytest", str(TESTS)])
run([sys.executable, "-m", "coverage", "xml", "-o", str(ROOT / "coverage.xml")])
run([sys.executable, "-m", "coverage", "report", "-m"], REPORTS / "coverage_report.txt")

# 4) performance baseline export (best-effort)
try:
    os.environ.setdefault("PLOOKINGII_ROOT", str(ROOT))
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from plookingII.monitor import PerformanceMonitor  # type: ignore
    monitor = PerformanceMonitor()
    print(f"Performance monitor initialized: {type(monitor).__name__}")
except Exception as e:
    print(f"Skip performance monitor initialization: {e}")

print("Reports generated under:", REPORTS)
