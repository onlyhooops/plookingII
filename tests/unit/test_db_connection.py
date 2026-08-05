"""
测试 db/connection.py 模块

测试目标：达到95%+覆盖率
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from plookingII.db.connection import _configure_sqlite_pragmas, connect_db


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestConfigureSQLitePragmas:
    """测试SQLite PRAGMA配置"""

    def test_configure_pragmas_success(self):
        """测试成功配置PRAGMA"""
        # 创建临时内存数据库
        conn = sqlite3.connect(":memory:")

        # 配置PRAGMA
        _configure_sqlite_pragmas(conn)

        # 验证配置生效
        cursor = conn.cursor()

        # 检查WAL模式
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0]
        assert journal_mode.upper() in ["WAL", "DELETE", "MEMORY"]  # 内存数据库可能不支持WAL

        # 检查外键约束
        cursor.execute("PRAGMA foreign_keys;")
        foreign_keys = cursor.fetchone()[0]
        assert foreign_keys == 1

        cursor.close()
        conn.close()

    def test_configure_pragmas_exception_handling(self):
        """测试PRAGMA配置异常处理"""
        # 创建模拟连接
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("PRAGMA error")

        # 不应该抛出异常
        _configure_sqlite_pragmas(mock_conn)

        # 验证cursor.close()被调用
        mock_cursor.close.assert_called_once()

    def test_configure_pragmas_cursor_close_failure(self):
        """测试游标关闭失败"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("PRAGMA error")
        mock_cursor.close.side_effect = Exception("Close error")

        # 不应该抛出异常
        _configure_sqlite_pragmas(mock_conn)

    def test_configure_pragmas_with_real_file_db(self):
        """测试真实文件数据库的PRAGMA配置"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = sqlite3.connect(db_path)
            _configure_sqlite_pragmas(conn)

            cursor = conn.cursor()

            # WAL模式应该在文件数据库上生效
            cursor.execute("PRAGMA journal_mode;")
            journal_mode = cursor.fetchone()[0]
            assert journal_mode.upper() == "WAL"

            # 检查同步模式
            cursor.execute("PRAGMA synchronous;")
            sync_mode = cursor.fetchone()[0]
            assert sync_mode == 1  # NORMAL = 1

            cursor.close()
            conn.close()
        finally:
            # 清理临时文件
            Path(db_path).unlink(missing_ok=True)
            # WAL模式会创建额外的文件
            Path(f"{db_path}-wal").unlink(missing_ok=True)
            Path(f"{db_path}-shm").unlink(missing_ok=True)


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestConnectDB:
    """测试数据库连接函数"""

    def test_connect_memory_db(self):
        """测试连接内存数据库"""
        conn = connect_db(":memory:")

        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)

        # 验证可以执行查询
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1

        cursor.close()
        conn.close()

    def test_connect_file_db(self):
        """测试连接文件数据库"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = connect_db(db_path)

            assert conn is not None
            assert isinstance(conn, sqlite3.Connection)

            # 创建表测试
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            cursor.execute("INSERT INTO test (name) VALUES ('test')")
            conn.commit()

            # 验证数据
            cursor.execute("SELECT name FROM test")
            result = cursor.fetchone()
            assert result[0] == "test"

            cursor.close()
            conn.close()
        finally:
            Path(db_path).unlink(missing_ok=True)
            Path(f"{db_path}-wal").unlink(missing_ok=True)
            Path(f"{db_path}-shm").unlink(missing_ok=True)

    def test_connect_with_custom_timeout(self):
        """测试自定义超时"""
        conn = connect_db(":memory:", timeout=60.0)

        assert conn is not None
        conn.close()

    def test_connect_with_isolation_level(self):
        """测试自定义隔离级别"""
        conn = connect_db(":memory:", isolation_level="DEFERRED")

        assert conn is not None
        assert conn.isolation_level == "DEFERRED"
        conn.close()

    def test_connect_check_same_thread_false(self):
        """测试禁用线程检查"""
        conn = connect_db(":memory:", check_same_thread=False)

        assert conn is not None
        # 应该可以在不同线程中使用
        conn.close()

    def test_connect_with_detect_types(self):
        """测试类型检测"""
        conn = connect_db(":memory:", detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

        assert conn is not None
        conn.close()

    def test_connect_with_kwargs(self):
        """测试额外的关键字参数"""
        conn = connect_db(":memory:", timeout=30.0, check_same_thread=False, isolation_level=None)

        assert conn is not None
        conn.close()

    def test_connect_applies_pragmas(self):
        """测试连接自动应用PRAGMA配置"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = connect_db(db_path)
            cursor = conn.cursor()

            # 验证PRAGMA已应用
            cursor.execute("PRAGMA journal_mode;")
            journal_mode = cursor.fetchone()[0]
            assert journal_mode.upper() == "WAL"

            cursor.execute("PRAGMA foreign_keys;")
            foreign_keys = cursor.fetchone()[0]
            assert foreign_keys == 1

            cursor.close()
            conn.close()
        finally:
            Path(db_path).unlink(missing_ok=True)
            Path(f"{db_path}-wal").unlink(missing_ok=True)
            Path(f"{db_path}-shm").unlink(missing_ok=True)

    def test_connect_invalid_path(self):
        """测试无效路径"""
        # 尝试在不可写的目录创建数据库
        invalid_path = "/invalid/path/test.db"

        with pytest.raises(sqlite3.Error):
            connect_db(invalid_path)

    def test_connect_multiple_connections(self):
        """测试多个连接"""
        conn1 = connect_db(":memory:")
        conn2 = connect_db(":memory:")

        assert conn1 is not None
        assert conn2 is not None
        assert conn1 != conn2

        conn1.close()
        conn2.close()


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestForeignKeyConstraints:
    """测试外键约束"""

    def test_foreign_key_constraint_enabled(self):
        """测试外键约束已启用"""
        conn = connect_db(":memory:")
        cursor = conn.cursor()

        # 创建父表和子表
        cursor.execute("""
            CREATE TABLE parent (
                id INTEGER PRIMARY KEY
            )
        """)

        cursor.execute("""
            CREATE TABLE child (
                id INTEGER PRIMARY KEY,
                parent_id INTEGER,
                FOREIGN KEY (parent_id) REFERENCES parent(id)
            )
        """)

        # 插入父记录
        cursor.execute("INSERT INTO parent (id) VALUES (1)")

        # 插入有效的子记录应该成功
        cursor.execute("INSERT INTO child (id, parent_id) VALUES (1, 1)")

        # 尝试插入无效的子记录应该失败
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("INSERT INTO child (id, parent_id) VALUES (2, 999)")

        cursor.close()
        conn.close()


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestWALMode:
    """测试WAL模式"""

    def test_wal_mode_concurrent_access(self):
        """测试WAL模式下的并发访问"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # 创建第一个连接并插入数据
            conn1 = connect_db(db_path)
            cursor1 = conn1.cursor()
            cursor1.execute("CREATE TABLE test (id INTEGER, value TEXT)")
            cursor1.execute("INSERT INTO test VALUES (1, 'test')")
            conn1.commit()

            # 创建第二个连接读取数据
            conn2 = connect_db(db_path)
            cursor2 = conn2.cursor()
            cursor2.execute("SELECT value FROM test WHERE id = 1")
            result = cursor2.fetchone()
            assert result[0] == "test"

            cursor1.close()
            cursor2.close()
            conn1.close()
            conn2.close()
        finally:
            Path(db_path).unlink(missing_ok=True)
            Path(f"{db_path}-wal").unlink(missing_ok=True)
            Path(f"{db_path}-shm").unlink(missing_ok=True)


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestEdgeCases:
    """测试边缘情况"""

    def test_empty_database_path(self):
        """测试空数据库路径"""
        # SQLite实际上接受空字符串并创建临时数据库
        # 所以不应该抛出异常
        conn = connect_db("")
        assert conn is not None
        conn.close()

    def test_unicode_path(self):
        """测试Unicode路径"""
        with tempfile.NamedTemporaryFile(suffix="_测试.db", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = connect_db(db_path)
            assert conn is not None
            conn.close()
        finally:
            Path(db_path).unlink(missing_ok=True)
            Path(f"{db_path}-wal").unlink(missing_ok=True)
            Path(f"{db_path}-shm").unlink(missing_ok=True)

    def test_connection_with_all_parameters(self):
        """测试所有参数组合"""
        conn = connect_db(
            ":memory:",
            timeout=60.0,
            detect_types=sqlite3.PARSE_DECLTYPES,
            isolation_level="IMMEDIATE",
            check_same_thread=False,
        )

        assert conn is not None
        assert conn.isolation_level == "IMMEDIATE"
        conn.close()

    def test_multiple_pragma_applications(self):
        """测试多次应用PRAGMA"""
        conn = connect_db(":memory:")

        # 再次应用PRAGMA不应该出错
        _configure_sqlite_pragmas(conn)
        _configure_sqlite_pragmas(conn)

        conn.close()

    def test_connection_reuse(self):
        """测试连接重用"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # 第一次连接
            conn1 = connect_db(db_path)
            cursor = conn1.cursor()
            cursor.execute("CREATE TABLE test (id INTEGER)")
            conn1.commit()
            cursor.close()
            conn1.close()

            # 第二次连接应该能看到之前的表
            conn2 = connect_db(db_path)
            cursor = conn2.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test'")
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == "test"
            cursor.close()
            conn2.close()
        finally:
            Path(db_path).unlink(missing_ok=True)
            Path(f"{db_path}-wal").unlink(missing_ok=True)
            Path(f"{db_path}-shm").unlink(missing_ok=True)
