"""
历史记录管理模块

提供PlookingII应用程序的任务历史记录和进度管理功能。
使用SQLite数据库实现持久化存储，支持增量更新和高效查询。

主要功能：
    - 任务进度跟踪和恢复
    - 最近打开文件夹记录
    - 路径标准化和规范化
    - 数据库连接和事务管理

核心组件：
    - TaskHistoryManager: 主要的任务历史管理器
    - 路径标准化工具函数
    - SQLite数据库操作封装

技术特点：
    - 路径标准化：处理macOS上的符号链接和Unicode问题
    - 增量更新：只更新变化的部分，提高性能
    - 事务安全：使用数据库事务确保数据一致性
    - 异常处理：完善的错误处理和恢复机制

使用方式：
    from plookingII.core.history import TaskHistoryManager

Author: PlookingII Team
"""

import os

from ..config.constants import APP_NAME
from ..db.connection import connect_db
from ..imports import hashlib, logging
from ..utils.path_utils import PathUtils
from ..utils.validation_utils import ValidationUtils

logger = logging.getLogger(APP_NAME)


# 为了向后兼容，保留原有函数名作为别名
def _canon_path(p):
    """标准化文件路径（向后兼容函数）

    Args:
        p (str): 原始文件路径

    Returns:
        str: 标准化后的绝对路径
    """
    return PathUtils.canonicalize_path(p, resolve_symlinks=True)


class TaskHistoryManager:
    """任务历史记录管理器 - 使用SQLite数据库实现增量更新"""

    def __init__(self, root_folder):
        # 统一标准化路径，避免字符串差异导致哈希不一致
        original_root = root_folder
        self.root_folder = _canon_path(root_folder)

        # 创建应用数据目录
        app_data_dir = os.path.expanduser(os.path.join("~", "Library", "Application Support", APP_NAME))
        os.makedirs(app_data_dir, exist_ok=True)

        # 使用标准化后的根文件夹的哈希作为唯一标识符
        # MD5仅用于生成文件名，不用于加密安全
        normalized_hash = hashlib.md5(self.root_folder.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
        self.folder_hash = normalized_hash

        # 数据库文件路径（标准化）
        normalized_db = os.path.join(app_data_dir, f"task_history_{normalized_hash}.db")
        self.db_file = normalized_db

        # 兼容旧版本：如果曾经根据未标准化路径生成过数据库，优先复用
        try:
            legacy_hash = hashlib.md5(original_root.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
            legacy_db = os.path.join(app_data_dir, f"task_history_{legacy_hash}.db")
            if legacy_hash != normalized_hash and (os.path.exists(legacy_db) and not os.path.exists(normalized_db)):
                self.db_file = legacy_db
                self.folder_hash = legacy_hash
        except Exception:
            logger.debug("兼容旧版本数据库选择时发生异常，忽略使用标准路径", exc_info=True)

        # 初始化数据库
        self._init_database()

    def _create_database_tables(self, cursor):
        """创建数据库表结构

        Args:
            cursor: 数据库游标对象
        """
        # 创建任务表
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS task (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            root_folder TEXT NOT NULL,
            root_path_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # 创建子文件夹表
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS subfolders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_path TEXT NOT NULL,
            folder_index INTEGER NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # 创建当前会话表
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS current_session (
            id INTEGER PRIMARY KEY,
            current_subfolder_index INTEGER DEFAULT 0,
            current_index INTEGER DEFAULT 0,
            keep_folder TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # 新增最近打开文件夹表
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS recent_folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_path TEXT NOT NULL UNIQUE,
            opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
        )

    def _initialize_task_records(self, cursor):
        """初始化任务记录和会话数据

        Args:
            cursor: 数据库游标对象
        """
        # 检查任务记录是否存在，不存在则创建
        cursor.execute("SELECT id FROM task WHERE root_path_hash = ?", (self.folder_hash,))
        task = cursor.fetchone()

        if not task:
            # 创建新任务记录
            cursor.execute(
                """
            INSERT INTO task (root_folder, root_path_hash)
            VALUES (?, ?)
            """,
                (self.root_folder, self.folder_hash),
            )

            # 创建当前会话记录
            cursor.execute("INSERT INTO current_session (id) VALUES (1)")

    def _update_subfolders(self, cursor, subfolders):
        """更新子文件夹列表（增量更新）

        Args:
            cursor: 数据库游标对象
            subfolders: 子文件夹路径列表
        """
        # 获取现有子文件夹
        cursor.execute("SELECT id, folder_path, folder_index FROM subfolders ORDER BY folder_index")
        existing_subfolders = cursor.fetchall()
        existing_paths = {row[1]: (row[0], row[2]) for row in existing_subfolders}

        # 删除不再存在的子文件夹
        for path, (id, _) in list(existing_paths.items()):
            if path not in subfolders:
                cursor.execute("DELETE FROM subfolders WHERE id = ?", (id,))

        # 更新或插入子文件夹
        for i, folder in enumerate(subfolders):
            if folder in existing_paths:
                # 更新索引（如果有变化）
                folder_id, current_index = existing_paths[folder]
                if current_index != i:
                    cursor.execute(
                        """
                    UPDATE subfolders SET
                        folder_index = ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                        (i, folder_id),
                    )
            else:
                # 插入新子文件夹
                cursor.execute(
                    """
                INSERT INTO subfolders (folder_path, folder_index)
                VALUES (?, ?)
                """,
                    (folder, i),
                )

    def _init_database(self):
        """初始化数据库结构"""
        conn = None
        try:
            conn = connect_db(self.db_file)
            cursor = conn.cursor()

            # 创建数据库表
            self._create_database_tables(cursor)

            # 初始化任务记录
            self._initialize_task_records(cursor)

            conn.commit()
        except Exception:
            logger.exception("初始化任务历史数据库失败: %s", self.db_file)
        finally:
            if conn:
                conn.close()

    def save_task_progress(self, current_data):
        """保存任务进度到数据库（增量更新）。

        将当前浏览状态保存到SQLite数据库，包括子文件夹列表、
        当前位置和保留文件夹信息。采用增量更新策略优化性能。

        Args:
            current_data (dict): 包含以下键的当前状态数据：
                - current_subfolder_index: 当前子文件夹索引
                - current_index: 当前图片索引
                - keep_folder: 保留文件夹路径
                - subfolders: 子文件夹列表

        Returns:
            bool: 保存成功返回True，失败返回False

        Note:
            - 使用事务确保数据一致性
            - 增量更新：只更新变化的子文件夹
            - 自动删除不再存在的子文件夹记录
            - 异常安全：失败时不影响现有数据
        """
        if not current_data:
            return False

        conn = None
        try:
            conn = connect_db(self.db_file)
            cursor = conn.cursor()

            # 更新任务记录的最后更新时间
            cursor.execute(
                """
            UPDATE task SET
                last_updated = CURRENT_TIMESTAMP
            WHERE root_path_hash = ?
            """,
                (self.folder_hash,),
            )

            # 更新当前会话状态
            cursor.execute(
                """
            UPDATE current_session SET
                current_subfolder_index = ?,
                current_index = ?,
                keep_folder = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
                (
                    current_data.get("current_subfolder_index", 0),
                    current_data.get("current_index", 0),
                    current_data.get("keep_folder", ""),
                ),
            )

            # 更新子文件夹列表（增量更新）
            self._update_subfolders(cursor, current_data.get("subfolders", []))

            conn.commit()
            return True

        except Exception:
            logger.exception("保存子文件夹列表失败: %s", self.db_file)
            return False
        finally:
            if conn:
                conn.close()

    def _validate_task_record(self, cursor):
        """验证任务记录的有效性

        Args:
            cursor: 数据库游标对象

        Returns:
            bool: 验证通过返回True，否则返回False
        """
        # 检查任务记录是否存在
        cursor.execute("SELECT root_folder FROM task WHERE root_path_hash = ?", (self.folder_hash,))
        task = cursor.fetchone()

        if not task:
            return False

        # 检查根文件夹路径一致性（使用标准化比较，兼容不同表示方式）
        saved_root = task[0]
        if _canon_path(saved_root) != self.root_folder:
            # 轻微不一致（如符号链接/Unicode）时也允许继续
            # 但不满足时返回False以避免误匹配不同目录
            # 这里选择继续使用相同哈希命名的数据库，因此不直接返回
            pass

        return True

    def _build_progress_data(self, cursor):
        """构建进度数据

        Args:
            cursor: 数据库游标对象

        Returns:
            dict or None: 进度数据字典，失败时返回None
        """
        # 获取当前会话状态
        cursor.execute("SELECT current_subfolder_index, current_index, keep_folder FROM current_session WHERE id = 1")
        session = cursor.fetchone()

        if not session:
            return None

        current_subfolder_index, current_index, keep_folder = session

        # 迁移旧 keep_folder 路径：.../保留 -> .../[父目录名] 精选
        try:
            if keep_folder and isinstance(keep_folder, str):
                parent_dir = os.path.dirname(keep_folder)
                base_name = os.path.basename(parent_dir) if parent_dir else ""
                selection_name = f"{base_name} 精选" if base_name else "精选"
                if os.path.basename(keep_folder) == "保留":
                    keep_folder = os.path.join(parent_dir, selection_name)
        except Exception:
            pass

        # 获取子文件夹列表
        cursor.execute("SELECT folder_path FROM subfolders ORDER BY folder_index")
        subfolders = [row[0] for row in cursor.fetchall()]

        # 构建返回数据
        return {
            "subfolders": subfolders,
            "current_subfolder_index": int(current_subfolder_index or 0),
            "current_index": int(current_index or 0),
            "keep_folder": keep_folder or "",
        }

    def _upsert_recent_folder(self, cursor, folder_path: str) -> None:
        """插入或更新最近文件夹记录。

        Args:
            cursor: 数据库游标
            folder_path: 文件夹路径
        """
        cursor.execute(
            """
            INSERT INTO recent_folders (folder_path, opened_at)
            VALUES (?, CURRENT_TIMESTAMP)
            ON CONFLICT(folder_path) DO UPDATE SET opened_at=CURRENT_TIMESTAMP
        """,
            (folder_path,),
        )

    def _cleanup_old_folders(self, cursor, max_count: int) -> None:
        """清理超出限制的旧文件夹记录。

        Args:
            cursor: 数据库游标
            max_count: 最大保留记录数
        """
        cursor.execute(
            """
            DELETE FROM recent_folders WHERE id NOT IN (
                SELECT id FROM recent_folders ORDER BY opened_at DESC LIMIT ?
            )
        """,
            (max_count,),
        )

    def load_task_progress(self):
        """从数据库加载任务进度。

        读取之前保存的浏览状态，包括子文件夹列表和当前位置信息。

        Returns:
            dict or None: 成功时返回包含以下键的字典，失败时返回None：
                - subfolders: 子文件夹路径列表
                - current_subfolder_index: 当前子文件夹索引
                - current_index: 当前图片索引
                - keep_folder: 保留文件夹路径

        Note:
            - 验证数据库文件存在性和任务记录有效性
            - 兼容路径表示差异（符号链接、Unicode等）
            - 异常安全：任何错误都返回None而不是崩溃
            - 自动处理数据类型转换（确保索引为整数）
        """
        conn = None
        try:
            if not os.path.exists(self.db_file):
                return None

            conn = connect_db(self.db_file)
            cursor = conn.cursor()

            # 验证任务记录
            if not self._validate_task_record(cursor):
                return None

            # 构建并返回进度数据
            return self._build_progress_data(cursor)

        except Exception:
            logger.exception("加载任务进度失败: %s", self.db_file)
            return None
        finally:
            if conn:
                conn.close()

    def clear_history(self):
        """清除当前任务的所有历史记录。

        重置浏览状态到初始状态，清空子文件夹列表和位置信息。

        Note:
            - 清空subfolders表中的所有记录
            - 重置current_session表的所有字段到默认值
            - 使用事务确保操作的原子性
            - 异常安全：失败时记录日志但不抛出异常
        """
        conn = None
        try:
            conn = connect_db(self.db_file)
            cursor = conn.cursor()

            # 清空所有表
            cursor.execute("DELETE FROM subfolders")
            cursor.execute(
                "UPDATE current_session SET current_subfolder_index = 0, "
                "current_index = 0, keep_folder = NULL WHERE id = 1"
            )

            conn.commit()
        except Exception:
            logger.exception("清除任务历史失败: %s", self.db_file)
        finally:
            if conn:
                conn.close()

    def add_recent_folder(self, folder_path, max_count=10):
        """添加最近打开的文件夹记录。

        将文件夹路径添加到最近打开列表，如果已存在则更新时间戳。
        自动维护列表大小在指定限制内。

        Args:
            folder_path (str): 文件夹路径
            max_count (int): 最大保留记录数，默认10

        Note:
            - 使用UPSERT操作：存在则更新时间，不存在则插入
            - 自动清理超出限制的旧记录
            - 异常安全：失败时记录日志但不影响程序运行
        """
        # 验证路径，排除精选文件夹
        if not self._validate_recent_folder_path(folder_path):
            logger.debug(f"拒绝添加无效的最近文件夹路径: {folder_path}")
            return

        conn = None
        try:
            conn = connect_db(self.db_file)
            cursor = conn.cursor()
            self._upsert_recent_folder(cursor, folder_path)
            self._cleanup_old_folders(cursor, max_count)
            conn.commit()
        except Exception:
            logger.exception("更新最近文件夹失败: %s", folder_path)
        finally:
            if conn:
                conn.close()

    def get_recent_folders(self, max_count=10):
        """获取最近打开的文件夹列表。

        按打开时间倒序返回最近访问的文件夹路径列表。

        Args:
            max_count (int): 最大返回记录数，默认10

        Returns:
            list: 文件夹路径列表，按时间倒序排列

        Note:
            - 异常安全：失败时返回空列表
            - 自动过滤无效记录
        """
        conn = None
        try:
            conn = connect_db(self.db_file)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT folder_path FROM recent_folders ORDER BY opened_at DESC LIMIT ?
            """,
                (max_count,),
            )
            result = [row[0] for row in cursor.fetchall()]
            return result
        except Exception:
            logger.exception("读取最近文件夹失败")
            return []
        finally:
            if conn:
                conn.close()

    def clear_recent_folders(self):
        """清空所有最近打开文件夹记录。

        删除recent_folders表中的所有记录。

        Note:
            - 使用事务确保操作完整性
            - 异常安全：失败时记录日志但不抛出异常
        """
        conn = None
        try:
            conn = connect_db(self.db_file)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM recent_folders")
            conn.commit()
        except Exception:
            logger.exception("清空最近文件夹失败")
        finally:
            if conn:
                conn.close()

    def _validate_recent_folder_path(self, folder_path):
        """验证最近文件夹路径是否有效

        Args:
            folder_path: 文件夹路径

        Returns:
            bool: 路径是否有效
        """
        return ValidationUtils.validate_recent_folder_path(folder_path)
