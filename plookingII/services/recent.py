from ..config.constants import APP_NAME
from ..db.connection import connect_db
from ..imports import os
from ..utils.path_utils import PathUtils
from ..utils.validation_utils import ValidationUtils


class RecentFoldersManager:
    def __init__(self, db_path=None, max_count=10):
        if db_path is None:
            app_support_dir = (
                os.path.expanduser(os.path.join("~", "Library", "Application Support", APP_NAME))
            )
            db_path = os.path.join(app_support_dir, "recent_folders.db")
        self.db_path = db_path
        self.max_count = max_count
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = connect_db(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recent_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_path TEXT NOT NULL UNIQUE,
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        conn.commit()
        conn.close()

    def add(self, folder_path):
        # 验证并规范化路径
        if not self._validate_folder_path(folder_path):
            return

        # 规范化路径，解决路径编码和特殊字符问题
        normalized_path = self._normalize_folder_path(folder_path)

        conn = connect_db(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO recent_folders (folder_path, opened_at)
            VALUES (?, CURRENT_TIMESTAMP)
            ON CONFLICT(folder_path) DO UPDATE SET opened_at=CURRENT_TIMESTAMP
        """,
            (normalized_path,),
        )
        cursor.execute(
            """
            DELETE FROM recent_folders WHERE id NOT IN (
                SELECT id FROM recent_folders ORDER BY opened_at DESC LIMIT ?
            )
        """,
            (self.max_count,),
        )
        conn.commit()
        conn.close()

    def get(self):
        conn = connect_db(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT folder_path FROM recent_folders ORDER BY opened_at DESC LIMIT ?", (self.max_count,))
        raw_result = [row[0] for row in cursor.fetchall()]
        conn.close()

        # 过滤并验证路径，移除无效或不存在的路径
        valid_paths = []
        invalid_paths = []

        for path in raw_result:
            if self._validate_folder_path(path):
                valid_paths.append(path)
            else:
                invalid_paths.append(path)

        # 如果有无效路径，从数据库中清理
        if invalid_paths:
            self._remove_invalid_paths(invalid_paths)

        return valid_paths

    def clear(self):
        conn = connect_db(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM recent_folders")
        conn.commit()
        conn.close()

    def cleanup_invalid_entries(self):
        """清理数据库中的无效条目

        移除不存在、不是文件夹、或是精选文件夹的路径记录
        """
        try:
            conn = connect_db(self.db_path)
            cursor = conn.cursor()

            # 获取所有记录
            cursor.execute("SELECT folder_path FROM recent_folders")
            all_paths = [row[0] for row in cursor.fetchall()]

            # 找出无效路径
            invalid_paths = []
            for path in all_paths:
                if not self._validate_folder_path(path):
                    invalid_paths.append(path)

            # 删除无效路径
            if invalid_paths:
                placeholders = ",".join(["?" for _ in invalid_paths])
                delete_query = f"DELETE FROM recent_folders WHERE folder_path IN ({placeholders})"
                cursor.execute(delete_query, invalid_paths)
                conn.commit()

                # 记录清理结果
                import logging

                from ..config.constants import APP_NAME
                logger = logging.getLogger(APP_NAME)
                logger.info(f"清理了 {len(invalid_paths)} 个无效的最近文件夹记录")

            conn.close()
            return len(invalid_paths)

        except Exception as e:
            # 清理失败时记录错误但不抛出异常
            try:
                import logging

                from ..config.constants import APP_NAME
                logger = logging.getLogger(APP_NAME)
                logger.warning(f"清理无效最近文件夹记录失败: {e}")
            except Exception:
                pass
            return 0

    def _validate_folder_path(self, folder_path):
        """验证文件夹路径是否有效

        Args:
            folder_path: 文件夹路径

        Returns:
            bool: 路径是否有效
        """
        return ValidationUtils.validate_recent_folder_path(folder_path)

    def _normalize_folder_path(self, folder_path):
        """规范化文件夹路径

        Args:
            folder_path: 原始文件夹路径

        Returns:
            str: 规范化后的路径
        """
        return PathUtils.normalize_folder_path(folder_path, resolve_symlinks=False)

    def _remove_invalid_paths(self, invalid_paths):
        """从数据库中移除无效路径

        Args:
            invalid_paths: 无效路径列表
        """
        if not invalid_paths:
            return

        try:
            conn = connect_db(self.db_path)
            cursor = conn.cursor()

            # 构建删除查询
            placeholders = ",".join(["?" for _ in invalid_paths])
            query = f"DELETE FROM recent_folders WHERE folder_path IN ({placeholders})"

            cursor.execute(query, invalid_paths)
            conn.commit()
            conn.close()

        except Exception:
            # 清理失败时静默处理，不影响主流程
            pass
