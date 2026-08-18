#!/usr/bin/env python3
"""
版本号统一工具

将项目各处的版本号统一到唯一真源 `plookingII/__version__.py` 的当前版本，
修复发布时因手动修改导致的版本漂移（README / setup.py / 测试断言等）。

同步范围:
1. `setup.py` 的 CFBundleVersion / CFBundleShortVersionString / CFBundleGetInfoString
2. `README.md` 的「当前版本」行
3. `CHANGELOG.md` 最新版本条目（若与当前版本不一致则插入占位条目）
4. `tests/unit/test_config_constants.py` 的版本断言

用法:
    python scripts/unify_version.py            # 同步所有文件
    python scripts/unify_version.py --dry-run  # 仅显示将要执行的修改

退出码:
    0 - 成功（全部已同步或同步完成）
    1 - 失败
"""

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "plookingII" / "__version__.py"
VERSION_RE = re.compile(r'__version__\s*=\s*["\'](\d+\.\d+\.\d+)["\']')

# (文件名, 匹配模式, 替换模板) —— 替换模板中的 {version} 会被替换为当前版本
SYNC_TARGETS = [
    (
        "setup.py",
        r"CFBundleVersion'\s*:\s*'[^']*'",
        "CFBundleVersion': '{version}'",
    ),
    (
        "setup.py",
        r"CFBundleShortVersionString'\s*:\s*'[^']*'",
        "CFBundleShortVersionString': '{version}'",
    ),
    (
        "setup.py",
        r"CFBundleGetInfoString'\s*:\s*'PlookingII [^']*'",
        "CFBundleGetInfoString': 'PlookingII {version}'",
    ),
    (
        "README.md",
        r"\*\*当前版本\*\*:\s*v?\d+\.\d+\.\d+",
        "**当前版本**: v{version}",
    ),
    (
        "tests/unit/test_config_constants.py",
        r'assert constants\.VERSION == "\d+\.\d+\.\d+"',
        'assert constants.VERSION == "{version}"',
    ),
]


def get_source_version() -> str | None:
    """从 __version__.py 读取当前版本号"""
    content = VERSION_FILE.read_text(encoding="utf-8")
    match = VERSION_RE.search(content)
    return match.group(1) if match else None


def sync_file(rel_path: str, version: str, dry_run: bool) -> bool:
    """同步单个文件，返回是否发生了修改"""
    file_path = PROJECT_ROOT / rel_path
    if not file_path.exists():
        print(f"⚠️  跳过（不存在）: {rel_path}")
        return False

    content = file_path.read_text(encoding="utf-8")
    changed = False

    for filename, pattern, template in SYNC_TARGETS:
        # 匹配目标文件名（支持相对路径与 basename 两种写法）
        target_name = Path(filename).name
        if target_name != Path(rel_path).name:
            continue
        new_content = re.sub(pattern, template.format(version=version), content)
        if new_content != content:
            content = new_content
            changed = True

    if not changed:
        print(f"ℹ️  无需修改: {rel_path}")
        return False

    if dry_run:
        print(f"🔍 [dry-run] 将更新: {rel_path}")
    else:
        file_path.write_text(content, encoding="utf-8")
        print(f"✅ 已更新: {rel_path}")
    return True


def sync_changelog(version: str, dry_run: bool) -> bool:
    """确保 CHANGELOG.md 最新条目与当前版本一致

    兼容两种版本条目格式：
    - 本地手动格式：`## [2.5.1] - 2026-08-15`
    - semantic-release 生成格式：`## v2.5.1 (2026-08-15)`
    """
    changelog_file = PROJECT_ROOT / "CHANGELOG.md"
    if not changelog_file.exists():
        return False
    content = changelog_file.read_text(encoding="utf-8")
    # 已存在对应版本的条目（兼容 "## [x.y.z]"、"## vx.y.z" 两种格式）则不插入
    exists = re.search(rf"^## \[?v?{re.escape(version)}\]?", content, re.MULTILINE)
    if exists:
        print(f"ℹ️  CHANGELOG.md 最新条目已是最新版本 {version}")
        return False

    today = datetime.now(UTC).date().isoformat()
    entry = f"## [{version}] - {today}\n\n### ✨ 新特性\n\n- （待补充）\n\n"
    if "<!--next-version-->" in content:
        new_content = content.replace("<!--next-version-->", "<!--next-version-->\n\n" + entry, 1)
    else:
        # 插入到第一个版本条目之前（兼容 "## [" 与 "## v" 两种开头）
        lines = content.splitlines()
        insert_at = next(
            (i for i, line in enumerate(lines) if line.startswith(("## [", "## v"))),
            len(lines),
        )
        lines.insert(insert_at, entry.rstrip("\n"))
        new_content = "\n".join(lines)

    if dry_run:
        print("🔍 [dry-run] 将在 CHANGELOG.md 插入新版本条目")
    else:
        changelog_file.write_text(new_content, encoding="utf-8")
        print(f"✅ 已更新: CHANGELOG.md（插入 {version} 条目）")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="PlookingII 版本号统一工具")
    parser.add_argument("--dry-run", action="store_true", help="仅显示将要执行的修改")
    args = parser.parse_args()

    version = get_source_version()
    if version is None:
        print("❌ 无法从 plookingII/__version__.py 解析版本号")
        return 1

    print(f"📌 唯一真源版本号: {version}")
    print("=" * 70)

    any_change = False
    for rel_path in ("setup.py", "README.md", "tests/unit/test_config_constants.py"):
        if sync_file(rel_path, version, args.dry_run):
            any_change = True

    if sync_changelog(version, args.dry_run):
        any_change = True

    print("=" * 70)
    if any_change:
        print("✅ 版本号已统一。建议运行 verify_version_consistency.py 复核")
    else:
        print("ℹ️  所有文件版本号均已一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
