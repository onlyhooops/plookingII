#!/usr/bin/env python3
"""
macOS 最近项目记录清理工具

清除 macOS 系统及 PlookingII 应用的最近打开项目记录，
用于开发环境下保护隐私（避免调试会话的文件夹路径出现在系统菜单中）。

用法:
    python scripts/clear_recent_items.py

说明:
    - 仅建议在开发环境运行；正式使用时由应用在退出时自动清理
    - 清理范围：系统"最近文档"记录 + 应用最近文档记录
"""

import sys
from pathlib import Path

# 允许从项目根目录直接运行（无需先安装包）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    try:
        from plookingII.utils.macos_cleanup import clear_macos_recent_items

        print("🧹 清理 macOS 最近项目记录...")
        clear_macos_recent_items()
        print("✅ 清理完成")
        return 0
    except Exception as e:
        print(f"❌ 清理失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
