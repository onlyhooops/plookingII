"""数据库连接模块

提供优化的SQLite数据库连接功能，包含性能优化配置和错误处理。
主要用于PlookingII应用的数据持久化需求，如历史记录、缓存索引等。

特性：
    - WAL模式：提升并发性能
    - 外键约束：保证数据完整性
    - 连接池优化：支持自定义超时和线程安全
    - 异常处理：完善的错误恢复机制

Author: PlookingII Team
"""

from ..config.constants import APP_NAME
from ..imports import _sqlite3, logging

# 日志记录器：用于数据库操作的调试和错误追踪
logger = logging.getLogger(APP_NAME)


def _configure_sqlite_pragmas(conn):
    """配置SQLite数据库的PRAGMA设置

    为数据库连接应用性能优化和安全配置，包括WAL模式、
    同步设置和外键约束等。

    Args:
        conn (sqlite3.Connection): 数据库连接对象

    配置项：
        - WAL模式：Write-Ahead Logging，提升并发读写性能
        - NORMAL同步：平衡性能和数据安全性
        - 外键约束：确保引用完整性

    Note:
        配置失败不会抛出异常，仅记录警告日志，确保连接可用性
    """
    cur = None
    try:
        cur = conn.cursor()

        # 启用WAL模式：Write-Ahead Logging，允许并发读取
        # 优势：读操作不会被写操作阻塞，提升多线程性能
        cur.execute("PRAGMA journal_mode=WAL;")

        # 设置同步模式为NORMAL：平衡性能和数据安全
        # NORMAL模式在关键时刻同步，比FULL模式快但仍保证数据完整性
        cur.execute("PRAGMA synchronous=NORMAL;")

        # 启用外键约束：确保引用完整性
        # 防止孤立记录和数据不一致问题
        cur.execute("PRAGMA foreign_keys=ON;")

    except Exception as e:
        # PRAGMA设置失败不应阻止连接使用，记录警告继续执行
        logger.warning("Failed to set SQLite PRAGMAs: %s", e)
    finally:
        # 安全关闭游标，避免资源泄漏
        if cur is not None:
            try:
                cur.close()
            except Exception as close_err:
                # 游标关闭失败通常不影响连接使用，记录警告即可
                logger.warning("sqlite cursor close failed: %s", close_err)


def connect_db(database, timeout=30.0, detect_types=0, isolation_level=None, check_same_thread=False, **kwargs):
    """创建优化的SQLite数据库连接

    建立SQLite数据库连接并应用性能优化配置。自动启用WAL模式、
    外键约束和同步优化，提供高性能的数据库访问能力。

    Args:
        database (str): 数据库文件路径，支持内存数据库(':memory:')
        timeout (float): 连接超时时间（秒），默认30秒
        detect_types (int): 类型检测标志，0=禁用，sqlite3.PARSE_*组合
        isolation_level (str|None): 事务隔离级别，None=自动提交模式
        check_same_thread (bool): 是否检查线程安全，False=允许跨线程
        **kwargs: 传递给sqlite3.connect的其他参数

    Returns:
        sqlite3.Connection: 已优化配置的数据库连接对象

    Raises:
        sqlite3.Error: 数据库连接失败时抛出

    示例:
        >>> conn = connect_db('app.db')
        >>> cursor = conn.cursor()
        >>> cursor.execute('SELECT * FROM users')
        >>> conn.close()
    """
    # 建立基础数据库连接
    conn = _sqlite3.connect(
        database,
        timeout=timeout,
        detect_types=detect_types,
        isolation_level=isolation_level,
        check_same_thread=check_same_thread,
        **kwargs,
    )

    # 应用性能优化配置
    _configure_sqlite_pragmas(conn)

    return conn
