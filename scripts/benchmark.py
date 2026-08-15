#!/usr/bin/env python3
"""
PlookingII 可重复性能基准脚本（P3-2）

合成不同尺寸/格式的图片集，度量核心性能指标并输出 JSON 基线，
用于量化优化效果与防回归。每次性能改动后运行，对比基线数值。

度量指标:
1. 首图加载延迟（ms）—— 冷启动加载第一张图
2. 连续翻图主线程阻塞（ms）—— 100 次翻图的 p50/p95/max
3. 缓存命中率（%）—— 二次遍历同一图片集
4. RSS 内存曲线（MB）—— 加载过程中的起始/峰值/结束
5. 文件夹跳转延迟（ms）—— 目录图片列表冷/热扫描

用法:
    python scripts/benchmark.py                     # 运行全量基准
    python scripts/benchmark.py --quick             # 快速模式（20 张）
    python scripts/benchmark.py --output out.json   # 指定输出文件

输出:
    默认输出 JSON 到 stdout，可指定文件。包含应用版本、时间戳与各指标。

说明:
    - 项目不处理 EXIF 方向，度量不涉及方向修正
    - macOS 环境走 Quartz 真实解码路径；非 macOS 自动降级 PIL 路径
"""

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 合成图片规格：(文件名, 尺寸, 格式, 颜色模式)
IMAGE_SPECS = [
    ("small_800.jpg", (800, 600), "JPEG", "RGB"),
    ("medium_1920.jpg", (1920, 1080), "JPEG", "RGB"),
    ("large_4000.jpg", (4000, 3000), "JPEG", "RGB"),
    ("png_1600.png", (1600, 1200), "PNG", "RGB"),
]


# 采样统计辅助
def _percentile(sorted_values, p):
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def _summary_ms(values):
    """返回耗时列表的统计摘要（毫秒）"""
    if not values:
        return {"count": 0}
    s = sorted(values)
    return {
        "count": len(s),
        "min_ms": round(s[0], 2),
        "avg_ms": round(sum(s) / len(s), 2),
        "p50_ms": round(_percentile(s, 0.50), 2),
        "p95_ms": round(_percentile(s, 0.95), 2),
        "p99_ms": round(_percentile(s, 0.99), 2),
        "max_ms": round(s[-1], 2),
    }


def _generate_images(dir_path: Path, count: int = 1) -> list[Path]:
    """合成测试图片集，返回路径列表"""
    from PIL import Image

    paths = []
    for _ in range(count):
        for name, size, fmt, mode in IMAGE_SPECS:
            img = Image.new(mode, size, color=(128, 128, 160))
            # 填充渐变避免纯色图被解码器特殊优化
            for y in range(0, size[1], 64):
                for x in range(0, size[0], 64):
                    img.paste(((x * 13 + y * 7) % 256, (x * 3) % 256, (y * 11) % 256), (x, y, x + 64, y + 64))
            path = dir_path / f"{_random_suffix()}_{name}"
            img.save(path, format=fmt)
            paths.append(path)
    return paths


def _random_suffix() -> str:
    import random

    return f"{int(time.time())}{random.randint(1000, 9999)}"


def _measure_image_load(paths: list[Path]) -> dict:
    """度量首图加载延迟 + 连续翻图主线程阻塞"""
    from plookingII.core.loading import get_loader

    loader = get_loader("optimized")

    # 首图加载（冷）
    first_start = time.perf_counter()
    loader.load(str(paths[0]))
    first_ms = (time.perf_counter() - first_start) * 1000

    # 连续翻图：每张加载计时（模拟主线程翻页阻塞）
    nav_times = []
    for p in paths[:100]:
        start = time.perf_counter()
        loader.load(str(p))
        nav_times.append((time.perf_counter() - start) * 1000)

    return {"first_load_ms": round(first_ms, 2), "navigation": _summary_ms(nav_times)}


def _measure_cache_hit_rate(paths: list[Path]) -> dict:
    """度量缓存命中率：两遍遍历，第二遍应全命中"""
    from plookingII.core.simple_cache import SimpleImageCache

    cache = SimpleImageCache(max_items=1000, max_memory_mb=2000, name="benchmark")
    from plookingII.core.loading import get_loader

    loader = get_loader("optimized")

    # 第一遍：全部 miss 并写入缓存
    for p in paths:
        img = loader.load(str(p))
        if img is not None:
            cache.put(str(p), img, size_mb=1.0)

    misses = cache.get_stats()["misses"]
    hits_before = cache.get_stats()["hits"]

    # 第二遍：应全部命中
    for p in paths:
        cache.get(str(p))

    hits = cache.get_stats()["hits"] - hits_before
    total = hits + misses
    hit_rate = (hits / total * 100) if total else 0.0
    return {"hit_rate_pct": round(hit_rate, 2), "hits": hits, "misses": misses}


def _measure_rss_curve(paths: list[Path]) -> dict:
    """度量加载过程中的 RSS 内存曲线"""
    try:
        import psutil
    except ImportError:
        return {"available": False}

    proc = psutil.Process()
    from plookingII.core.loading import get_loader

    loader = get_loader("optimized")

    samples = []
    start_mb = proc.memory_info().rss / (1024 * 1024)
    for i, p in enumerate(paths[:50]):
        loader.load(str(p))
        if i % 5 == 0:
            samples.append(round(proc.memory_info().rss / (1024 * 1024), 1))
    end_mb = proc.memory_info().rss / (1024 * 1024)

    return {
        "available": True,
        "start_mb": round(start_mb, 1),
        "end_mb": round(end_mb, 1),
        "peak_mb": max(samples) if samples else round(end_mb, 1),
        "sample_count": len(samples),
    }


def _measure_folder_scan(root: Path) -> dict:
    """度量文件夹图片列表扫描延迟（冷/热）"""
    from plookingII.core.file_info_batch_loader import FileInfoBatchLoader

    loader = FileInfoBatchLoader()

    # 冷扫描（无缓存）
    cold_start = time.perf_counter()
    loader.get_directory_images(str(root), filter_exts=(".jpg", ".png"))
    cold_ms = (time.perf_counter() - cold_start) * 1000

    # 热扫描（命中目录级缓存）
    hot_start = time.perf_counter()
    loader.get_directory_images(str(root), filter_exts=(".jpg", ".png"))
    hot_ms = (time.perf_counter() - hot_start) * 1000

    return {"cold_ms": round(cold_ms, 2), "hot_ms": round(hot_ms, 2)}


def run_benchmark(quick: bool = False) -> dict:
    """运行完整基准，返回指标字典"""
    try:
        from plookingII.__version__ import __version__
    except Exception:
        __version__ = "unknown"

    image_count = 20 if quick else 100

    with tempfile.TemporaryDirectory(prefix="plookingii_bench_") as tmp:
        root = Path(tmp) / "photos"
        root.mkdir()
        paths = _generate_images(root, count=image_count // len(IMAGE_SPECS))

        return {
            "app": "PlookingII",
            "version": __version__,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "platform": sys.platform,
            "quick_mode": quick,
            "image_count": len(paths),
            "metrics": {
                "image_load": _measure_image_load(paths),
                "cache_hit_rate": _measure_cache_hit_rate(paths),
                "rss_curve": _measure_rss_curve(paths),
                "folder_scan": _measure_folder_scan(root),
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="PlookingII 性能基准")
    parser.add_argument("--quick", action="store_true", help="快速模式（20 张图片）")
    parser.add_argument("--output", type=str, default="", help="输出 JSON 文件路径（默认 stdout）")
    args = parser.parse_args()

    print("🧪 运行 PlookingII 性能基准...")
    results = run_benchmark(quick=args.quick)

    output = json.dumps(results, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"✅ 基准结果已写入: {args.output}")
    else:
        print(output)

    # 人类可读摘要
    m = results["metrics"]
    print("\n📊 摘要:")
    print(f"  首图加载: {m['image_load']['first_load_ms']}ms")
    nav = m["image_load"]["navigation"]
    print(f"  翻页阻塞: avg={nav.get('avg_ms', 0)}ms p95={nav.get('p95_ms', 0)}ms")
    print(f"  缓存命中率: {m['cache_hit_rate']['hit_rate_pct']}%")
    rss = m["rss_curve"]
    if rss.get("available"):
        print(f"  RSS: start={rss['start_mb']}MB peak={rss['peak_mb']}MB")
    scan = m["folder_scan"]
    print(f"  文件夹扫描: cold={scan['cold_ms']}ms hot={scan['hot_ms']}ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
