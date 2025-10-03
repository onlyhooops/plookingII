#!/usr/bin/env python3
"""
全面清理精选文件夹记录工具

清理所有数据库中的精选文件夹记录，解决dock菜单显示问题
"""

import sys
import os
import sqlite3
import glob

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plookingII.config.constants import APP_NAME


def is_selection_folder(path):
    """判断是否为精选文件夹"""
    if not path:
        return False

    folder_name = os.path.basename(path.rstrip(os.sep))
    return folder_name.endswith(" 精选") or folder_name == "精选"


def cleanup_database(db_path):
    """清理单个数据库中的精选文件夹记录"""
    cleaned_count = 0

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查是否有recent_folders表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='recent_folders'")
        if not cursor.fetchone():
            conn.close()
            return 0

        # 获取所有记录
        cursor.execute("SELECT folder_path FROM recent_folders")
        all_paths = [row[0] for row in cursor.fetchall()]

        # 找出精选文件夹记录
        selection_paths = [path for path in all_paths if is_selection_folder(path)]

        if selection_paths:
            # 删除精选文件夹记录
            placeholders = ','.join(['?' for _ in selection_paths])
            delete_query = f"DELETE FROM recent_folders WHERE folder_path IN ({placeholders})"
            cursor.execute(delete_query, selection_paths)
            conn.commit()
            cleaned_count = len(selection_paths)

            print(f"  清理了 {cleaned_count} 个精选文件夹记录:")
            for path in selection_paths:
                print(f"    🗑️ {path}")

        conn.close()

    except Exception as e:
        print(f"  ❌ 清理失败: {e}")

    return cleaned_count


def main():
    """主函数"""
    print(f"=== {APP_NAME} 全面清理精选文件夹记录工具 ===")
    print("⚠️  这将清理所有数据库中的精选文件夹记录")
    print()

    # 查找所有数据库文件
    app_support_dir = os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")

    # 查找不同类型的数据库
    db_patterns = [
        f"{app_support_dir}/recent_folders.db",  # 主要最近文件夹数据库
        f"{app_support_dir}/task_history_*.db",  # 任务历史数据库
    ]

    all_dbs = []
    for pattern in db_patterns:
        all_dbs.extend(glob.glob(pattern))

    print(f"发现 {len(all_dbs)} 个数据库文件")

    if not all_dbs:
        print("✅ 没有发现数据库文件，无需清理")
        return 0

    total_cleaned = 0

    for db_path in all_dbs:
        db_name = os.path.basename(db_path)
        print(f"\n📂 检查: {db_name}")

        cleaned = cleanup_database(db_path)
        total_cleaned += cleaned

        if cleaned == 0:
            print("  ✅ 无精选文件夹记录")

    print(f"\n🎉 清理完成！")
    print(f"总共清理了 {total_cleaned} 个精选文件夹记录")

    if total_cleaned > 0:
        print("\n💡 建议:")
        print("1. 重启 PlookingII 应用")
        print("2. 检查dock菜单是否还显示精选文件夹")
        print("3. 如果仍有问题，可能需要重启系统以清理macOS缓存")

    return 0


if __name__ == "__main__":
    exit(main())
