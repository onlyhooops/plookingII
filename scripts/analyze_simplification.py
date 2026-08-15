#!/usr/bin/env python3
"""
架构简化成果分析工具

统计简化后的缓存/加载/监控模块代码量，输出与文档一致的简化成果对比。

用法:
    python scripts/analyze_simplification.py

说明:
    历史归档工具（对应 docs/architecture/simplification/ 的简化记录）。
    简化前的行数为文档记录的基准值；简化后行数实时统计当前源码。
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 文档记录的简化前基准（2025-10-06 架构简化归档）
BEFORE_LINES = {
    "cache": 4307,  # 缓存系统：12 文件合并为 simple_cache.py
    "loading": 1118,  # 加载策略：单文件模块化
}


def count_lines(rel_path: str) -> int:
    """统计源码文件行数"""
    file_path = PROJECT_ROOT / rel_path
    if not file_path.exists():
        return 0
    return len(file_path.read_text(encoding="utf-8").splitlines())


def main() -> int:
    cache_after = count_lines("plookingII/core/simple_cache.py")
    loading_after = (
        count_lines("plookingII/core/loading/strategies.py")
        + count_lines("plookingII/core/loading/config.py")
        + count_lines("plookingII/core/loading/helpers.py")
        + count_lines("plookingII/core/loading/stats.py")
    )

    print("📊 架构简化成果分析")
    print("=" * 50)

    for name, after in (("cache", cache_after), ("loading", loading_after)):
        before = BEFORE_LINES.get(name, 0)
        if before <= 0 or after <= 0:
            print(f"⚠️  {name}: 无法统计（源文件缺失）")
            continue
        reduction = (before - after) / before * 100
        print(f"{name}: {before} 行 (旧) -> {after} 行 (新)")
        print(f"    减少: {reduction:.1f}%")

    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
