#!/usr/bin/env python3
"""
版本号自动提升工具

用于自动提升项目版本号，确保版本号管理的一致性。

使用方法:
    python scripts/bump_version.py major    # 主版本号 +1 (不兼容更新)
    python scripts/bump_version.py minor    # 次版本号 +1 (功能新增)
    python scripts/bump_version.py patch    # 修订号 +1 (Bug修复)
    python scripts/bump_version.py 1.8.0    # 指定版本号

特性:
- 自动更新 plookingII/__version__.py
- 自动验证版本号格式
- 自动生成版本更新说明
- 可选择是否自动提交

Author: PlookingII Team
Date: 2025-10-06
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


class VersionBumper:
    """版本号提升管理器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.version_file = project_root / "plookingII" / "__version__.py"

    def get_current_version(self) -> tuple[int, int, int]:
        """读取当前版本号"""
        if not self.version_file.exists():
            raise FileNotFoundError(f"版本文件不存在: {self.version_file}")

        content = self.version_file.read_text(encoding="utf-8")
        match = re.search(r'__version__\s*=\s*["\'](\d+)\.(\d+)\.(\d+)["\']', content)

        if not match:
            raise ValueError("无法从版本文件中解析版本号")

        return tuple(map(int, match.groups()))

    def bump_version(
        self, bump_type: str
    ) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        """提升版本号

        Args:
            bump_type: 'major', 'minor', 'patch' 或具体版本号

        Returns:
            (旧版本, 新版本)
        """
        current = self.get_current_version()
        major, minor, patch = current

        if bump_type == "major":
            new_version = (major + 1, 0, 0)
        elif bump_type == "minor":
            new_version = (major, minor + 1, 0)
        elif bump_type == "patch":
            new_version = (major, minor, patch + 1)
        else:
            # 尝试解析为具体版本号
            match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", bump_type)
            if not match:
                raise ValueError(
                    f"无效的版本提升类型: {bump_type}\n"
                    "支持: major, minor, patch 或具体版本号 (如 1.8.0)"
                )
            new_version = tuple(map(int, match.groups()))

        return current, new_version

    def update_version_file(self, new_version: tuple[int, int, int]) -> None:
        """更新版本文件"""
        content = self.version_file.read_text(encoding="utf-8")
        version_str = ".".join(map(str, new_version))

        # 更新 __version__
        content = re.sub(
            r'(__version__\s*=\s*["\'])\d+\.\d+\.\d+(["\'])',
            rf"\g<1>{version_str}\g<2>",
            content,
        )

        # 更新 RELEASE_DATE
        today = datetime.now().strftime("%Y-%m-%d")
        content = re.sub(
            r'(RELEASE_DATE\s*=\s*["\'])\d{4}-\d{2}-\d{2}(["\'])',
            rf"\g<1>{today}\g<2>",
            content,
        )

        self.version_file.write_text(content, encoding="utf-8")

    def verify_version_consistency(self) -> bool:
        """验证版本号一致性"""
        try:
            # 导入验证脚本
            verify_script = self.project_root / "scripts" / "verify_version_consistency.py"
            if verify_script.exists():
                import subprocess

                result = subprocess.run(
                    [sys.executable, str(verify_script)],
                    capture_output=True,
                    text=True,
                )
                return result.returncode == 0
        except Exception as e:
            print(f"⚠️  验证失败: {e}")
            return False
        return True


def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="PlookingII 版本号自动提升工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s major       提升主版本号 (1.7.0 -> 2.0.0)
  %(prog)s minor       提升次版本号 (1.7.0 -> 1.8.0)
  %(prog)s patch       提升修订号 (1.7.0 -> 1.7.1)
  %(prog)s 1.8.0       设置为指定版本号
        """,
    )

    parser.add_argument(
        "bump_type",
        nargs="?",
        default=None,
        help="版本提升类型 (major/minor/patch) 或具体版本号 (如 1.8.0)",
    )

    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="跳过版本一致性验证",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅显示将要执行的操作，不实际修改",
    )

    args = parser.parse_args()

    # 确定提升类型
    bump_type = args.bump_type
    if not bump_type:
        parser.print_help()
        return 1

    # 初始化
    project_root = Path(__file__).parent.parent
    bumper = VersionBumper(project_root)

    try:
        # 获取版本变化
        old_version, new_version = bumper.bump_version(bump_type)
        old_str = ".".join(map(str, old_version))
        new_str = ".".join(map(str, new_version))

        print("=" * 70)
        print("🔄 PlookingII 版本号提升")
        print("=" * 70)
        print(f"当前版本: {old_str}")
        print(f"新版本:   {new_str}")
        print()

        if args.dry_run:
            print("🔍 试运行模式 - 不会实际修改文件")
            return 0

        # 确认
        confirm = input("是否继续? [Y/n] ").strip().lower()
        if confirm and confirm not in ("y", "yes"):
            print("❌ 已取消")
            return 0

        # 更新版本文件
        print(f"📝 更新版本文件: {bumper.version_file.name}")
        bumper.update_version_file(new_version)
        print("✅ 版本文件已更新")

        # 验证一致性
        if not args.no_verify:
            print()
            print("🔍 验证版本号一致性...")
            if bumper.verify_version_consistency():
                print("✅ 版本号一致性验证通过")
            else:
                print("⚠️  版本号验证有警告，请检查")

        print()
        print("=" * 70)
        print(f"✅ 版本号已从 {old_str} 提升到 {new_str}")
        print("=" * 70)
        print()
        print("下一步操作:")
        print(f"  1. 更新 CHANGELOG.md，记录版本 {new_str} 的变更")
        print("  2. 提交更改: git add -A && git commit -m 'chore: bump version to {new_str}'")
        print(f"  3. 创建标签: git tag -a v{new_str} -m 'Release v{new_str}'")
        print("  4. 推送到远程: git push origin main && git push origin v{new_str}")
        print()

        return 0

    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

