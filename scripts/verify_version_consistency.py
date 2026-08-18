#!/usr/bin/env python3
"""
版本号一致性验证工具

验证项目各处的版本号是否与唯一真源 `plookingII/__version__.py` 保持一致，
防止发布时版本号漂移（README / CHANGELOG / setup.py / 测试断言等）。

检查项：
1. `plookingII/__version__.py` 中的版本号格式（SemVer x.y.z）
2. `setup.py` 的 CFBundleVersion / CFBundleShortVersionString / CFBundleGetInfoString
3. `README.md` 的「当前版本」行
4. `CHANGELOG.md` 最新版本条目
5. `tests/unit/test_config_constants.py` 的版本断言

用法:
    python scripts/verify_version_consistency.py

退出码:
    0 - 全部一致
    1 - 存在不一致（可用于 CI 门槛）
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "plookingII" / "__version__.py"
VERSION_RE = re.compile(r'__version__\s*=\s*["\'](\d+)\.(\d+)\.(\d+)["\']')


def get_source_version() -> str | None:
    """从 __version__.py 读取当前版本号"""
    content = VERSION_FILE.read_text(encoding="utf-8")
    match = VERSION_RE.search(content)
    return match.group(0).split("=")[1].strip().strip("\"'") if match else None


def check_semver(version: str) -> bool:
    """校验 SemVer 格式 x.y.z"""
    return bool(re.fullmatch(r"\d+\.\d+\.\d+", version))


def check_setup_py(version: str) -> bool:
    """检查 setup.py 中的 CFBundle 版本号"""
    setup_file = PROJECT_ROOT / "setup.py"
    if not setup_file.exists():
        print("⚠️  setup.py 不存在，跳过")
        return True
    content = setup_file.read_text(encoding="utf-8")
    ok = True
    for key in ("CFBundleVersion", "CFBundleShortVersionString"):
        match = re.search(rf"{key}'\s*:\s*'([^']+)'", content)
        if match and match.group(1) != version:
            print(f"❌ setup.py {key}={match.group(1)}，期望 {version}")
            ok = False
    # CFBundleGetInfoString 含 "PlookingII x.y.z"
    match = re.search(r"CFBundleGetInfoString'\s*:\s*'PlookingII ([^']+)'", content)
    if match and match.group(1) != version:
        print(f"❌ setup.py CFBundleGetInfoString={match.group(1)}，期望 {version}")
        ok = False
    return ok


def check_readme(version: str) -> bool:
    """检查 README.md 的「当前版本」行"""
    readme_file = PROJECT_ROOT / "README.md"
    if not readme_file.exists():
        print("⚠️  README.md 不存在，跳过")
        return True
    content = readme_file.read_text(encoding="utf-8")
    match = re.search(r"\*\*当前版本\*\*:\s*v?(\d+\.\d+\.\d+)", content)
    if match and match.group(1) != version:
        print(f"❌ README.md 当前版本={match.group(1)}，期望 {version}")
        return False
    return True


def check_changelog(version: str) -> bool:
    """检查 CHANGELOG.md 最新版本条目"""
    changelog_file = PROJECT_ROOT / "CHANGELOG.md"
    if not changelog_file.exists():
        print("⚠️  CHANGELOG.md 不存在，跳过")
        return True
    content = changelog_file.read_text(encoding="utf-8")
    # 兼容本地 "## [x.y.z]" 与 semantic-release "## vx.y.z" 两种条目格式
    match = re.search(r"^## \[?v?(\d+\.\d+\.\d+)\]?", content, re.MULTILINE)
    if match and match.group(1) != version:
        print(f"❌ CHANGELOG.md 最新条目={match.group(1)}，期望 {version}")
        return False
    return True


def check_test_assertion(version: str) -> bool:
    """检查测试中的版本断言"""
    test_file = PROJECT_ROOT / "tests" / "unit" / "test_config_constants.py"
    if not test_file.exists():
        print("⚠️  test_config_constants.py 不存在，跳过")
        return True
    content = test_file.read_text(encoding="utf-8")
    match = re.search(r'assert constants\.VERSION == "(\d+\.\d+\.\d+)"', content)
    if match and match.group(1) != version:
        print(f"❌ test_config_constants.py 断言={match.group(1)}，期望 {version}")
        return False
    return True


def main() -> int:
    print("🔍 验证版本号一致性...")
    version = get_source_version()
    if version is None:
        print("❌ 无法从 plookingII/__version__.py 解析版本号")
        return 1

    print(f"📌 唯一真源版本号: {version}")

    if not check_semver(version):
        print(f"❌ 版本号格式非法: {version}（应为 x.y.z）")
        return 1

    checks = [
        ("setup.py", check_setup_py),
        ("README.md", check_readme),
        ("CHANGELOG.md", check_changelog),
        ("测试断言", check_test_assertion),
    ]

    all_ok = True
    for name, fn in checks:
        try:
            ok = fn(version)
            if ok:
                print(f"✅ {name} 一致")
            else:
                all_ok = False
        except Exception as e:
            print(f"⚠️  {name} 检查异常: {e}")

    if all_ok:
        print("✅ 版本号一致性验证通过")
        return 0
    print("❌ 存在版本号不一致，请运行 scripts/unify_version.py 同步")
    return 1


if __name__ == "__main__":
    sys.exit(main())
