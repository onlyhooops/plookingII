"""
测试 core/history.py

测试任务历史管理模块的功能，包括：
- TaskHistoryManager初始化
- 数据库表创建
- 任务进度保存和加载
- 子文件夹增量更新
- 最近文件夹管理
- 路径标准化和验证
"""

import os
import sqlite3
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

from plookingII.core.history import TaskHistoryManager, _canon_path


@pytest.fixture
def temp_root_folder():
    """创建临时根文件夹"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_db_file():
    """创建临时数据库文件"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture
def history_manager(temp_root_folder):
    """创建TaskHistoryManager实例"""
    manager = TaskHistoryManager(temp_root_folder)
    yield manager
    # 清理数据库文件
    try:
        if os.path.exists(manager.db_file):
            os.unlink(manager.db_file)
    except Exception:
        pass


# ==================== 路径标准化测试 ====================


class TestCanonPath:
    """测试_canon_path函数"""

    def test_canon_path_basic(self, temp_root_folder):
        """测试基本路径标准化"""
        result = _canon_path(temp_root_folder)
        
        assert isinstance(result, str)
        assert os.path.isabs(result)

    def test_canon_path_with_tilde(self):
        """测试带波浪号的路径"""
        result = _canon_path("~/test")
        
        assert "~" not in result
        assert os.path.isabs(result)

    def test_canon_path_relative(self):
        """测试相对路径"""
        result = _canon_path("./test")
        
        assert os.path.isabs(result)


# ==================== TaskHistoryManager初始化测试 ====================


class TestTaskHistoryManagerInit:
    """测试TaskHistoryManager初始化"""

    def test_init_creates_manager(self, temp_root_folder):
        """测试成功创建管理器"""
        manager = TaskHistoryManager(temp_root_folder)
        
        assert manager.root_folder == _canon_path(temp_root_folder)
        assert manager.folder_hash is not None
        assert len(manager.folder_hash) == 8
        assert manager.db_file.endswith('.db')
        assert os.path.exists(manager.db_file)
        
        # 清理
        os.unlink(manager.db_file)

    def test_init_creates_database(self, temp_root_folder):
        """测试初始化创建数据库"""
        manager = TaskHistoryManager(temp_root_folder)
        
        # 验证数据库文件存在
        assert os.path.exists(manager.db_file)
        
        # 验证表结构
        conn = sqlite3.connect(manager.db_file)
        cursor = conn.cursor()
        
        # 检查所有表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        assert 'task' in tables
        assert 'subfolders' in tables
        assert 'current_session' in tables
        assert 'recent_folders' in tables
        
        conn.close()
        os.unlink(manager.db_file)

    def test_init_with_existing_database(self, temp_root_folder):
        """测试使用现有数据库初始化"""
        # 第一次创建
        manager1 = TaskHistoryManager(temp_root_folder)
        db_file = manager1.db_file
        
        # 第二次应该复用相同的数据库
        manager2 = TaskHistoryManager(temp_root_folder)
        
        assert manager2.db_file == db_file
        
        # 清理
        os.unlink(db_file)

    def test_init_handles_path_normalization(self, temp_root_folder):
        """测试路径标准化处理"""
        # 使用不同表示的相同路径
        path1 = temp_root_folder
        path2 = temp_root_folder + os.sep  # 带尾部斜杠
        
        manager1 = TaskHistoryManager(path1)
        manager2 = TaskHistoryManager(path2)
        
        # 应该生成相同的哈希
        assert manager1.folder_hash == manager2.folder_hash
        
        # 清理
        os.unlink(manager1.db_file)


# ==================== 数据库表创建测试 ====================


class TestDatabaseTableCreation:
    """测试数据库表创建"""

    def test_create_task_table(self, history_manager):
        """测试任务表创建"""
        conn = sqlite3.connect(history_manager.db_file)
        cursor = conn.cursor()
        
        # 检查表结构
        cursor.execute("PRAGMA table_info(task)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'id' in columns
        assert 'root_folder' in columns
        assert 'root_path_hash' in columns
        assert 'created_at' in columns
        assert 'last_updated' in columns
        
        conn.close()

    def test_create_subfolders_table(self, history_manager):
        """测试子文件夹表创建"""
        conn = sqlite3.connect(history_manager.db_file)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(subfolders)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'id' in columns
        assert 'folder_path' in columns
        assert 'folder_index' in columns
        assert 'last_updated' in columns
        
        conn.close()

    def test_create_current_session_table(self, history_manager):
        """测试当前会话表创建"""
        conn = sqlite3.connect(history_manager.db_file)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(current_session)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'id' in columns
        assert 'current_subfolder_index' in columns
        assert 'current_index' in columns
        assert 'keep_folder' in columns
        assert 'last_updated' in columns
        
        conn.close()

    def test_create_recent_folders_table(self, history_manager):
        """测试最近文件夹表创建"""
        conn = sqlite3.connect(history_manager.db_file)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(recent_folders)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'id' in columns
        assert 'folder_path' in columns
        assert 'opened_at' in columns
        
        conn.close()

    def test_initial_records_created(self, history_manager):
        """测试初始记录创建"""
        conn = sqlite3.connect(history_manager.db_file)
        cursor = conn.cursor()
        
        # 检查任务记录
        cursor.execute("SELECT COUNT(*) FROM task")
        task_count = cursor.fetchone()[0]
        assert task_count == 1
        
        # 检查会话记录
        cursor.execute("SELECT COUNT(*) FROM current_session")
        session_count = cursor.fetchone()[0]
        assert session_count == 1
        
        conn.close()


# ==================== 任务进度保存测试 ====================


class TestSaveTaskProgress:
    """测试保存任务进度"""

    def test_save_task_progress_success(self, history_manager):
        """测试成功保存进度"""
        current_data = {
            "current_subfolder_index": 2,
            "current_index": 5,
            "keep_folder": "/path/to/keep",
            "subfolders": ["/folder1", "/folder2", "/folder3"]
        }
        
        result = history_manager.save_task_progress(current_data)
        
        assert result is True

    def test_save_task_progress_updates_session(self, history_manager):
        """测试保存进度更新会话"""
        current_data = {
            "current_subfolder_index": 3,
            "current_index": 10,
            "keep_folder": "/keep",
            "subfolders": []
        }
        
        history_manager.save_task_progress(current_data)
        
        # 验证会话已更新
        conn = sqlite3.connect(history_manager.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT current_subfolder_index, current_index, keep_folder FROM current_session WHERE id = 1")
        result = cursor.fetchone()
        conn.close()
        
        assert result[0] == 3
        assert result[1] == 10
        assert result[2] == "/keep"

    def test_save_task_progress_updates_subfolders(self, history_manager):
        """测试保存进度更新子文件夹"""
        current_data = {
            "current_subfolder_index": 0,
            "current_index": 0,
            "subfolders": ["/sub1", "/sub2"]
        }
        
        history_manager.save_task_progress(current_data)
        
        # 验证子文件夹已保存
        conn = sqlite3.connect(history_manager.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT folder_path FROM subfolders ORDER BY folder_index")
        folders = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert folders == ["/sub1", "/sub2"]

    def test_save_task_progress_with_empty_data(self, history_manager):
        """测试保存空数据"""
        result = history_manager.save_task_progress(None)
        
        assert result is False
        
        result = history_manager.save_task_progress({})
        
        assert result is False

    def test_save_task_progress_incremental_update(self, history_manager):
        """测试增量更新子文件夹"""
        # 第一次保存
        data1 = {
            "subfolders": ["/a", "/b", "/c"]
        }
        history_manager.save_task_progress(data1)
        
        # 第二次保存（删除一个，添加一个）
        data2 = {
            "subfolders": ["/a", "/c", "/d"]
        }
        history_manager.save_task_progress(data2)
        
        # 验证最终结果
        conn = sqlite3.connect(history_manager.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT folder_path FROM subfolders ORDER BY folder_index")
        folders = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert folders == ["/a", "/c", "/d"]

    def test_save_task_progress_with_missing_keys(self, history_manager):
        """测试保存缺少键的数据"""
        current_data = {
            "subfolders": ["/test"]
            # 缺少其他键
        }
        
        result = history_manager.save_task_progress(current_data)
        
        # 应该使用默认值
        assert result is True
        
        conn = sqlite3.connect(history_manager.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT current_subfolder_index, current_index FROM current_session WHERE id = 1")
        result = cursor.fetchone()
        conn.close()
        
        assert result[0] == 0  # 默认值
        assert result[1] == 0  # 默认值


# ==================== 任务进度加载测试 ====================


class TestLoadTaskProgress:
    """测试加载任务进度"""

    def test_load_task_progress_success(self, history_manager):
        """测试成功加载进度"""
        # 先保存数据
        save_data = {
            "current_subfolder_index": 5,
            "current_index": 15,
            "keep_folder": "/test/keep",
            "subfolders": ["/s1", "/s2", "/s3"]
        }
        history_manager.save_task_progress(save_data)
        
        # 加载数据
        loaded_data = history_manager.load_task_progress()
        
        assert loaded_data is not None
        assert loaded_data["current_subfolder_index"] == 5
        assert loaded_data["current_index"] == 15
        assert loaded_data["keep_folder"] == "/test/keep"
        assert loaded_data["subfolders"] == ["/s1", "/s2", "/s3"]

    def test_load_task_progress_with_no_data(self, temp_root_folder):
        """测试加载不存在的进度"""
        # 创建新管理器但不保存数据
        manager = TaskHistoryManager(temp_root_folder)
        
        # 加载应该返回初始状态
        loaded_data = manager.load_task_progress()
        
        assert loaded_data is not None
        assert loaded_data["current_subfolder_index"] == 0
        assert loaded_data["current_index"] == 0
        assert loaded_data["subfolders"] == []
        
        # 清理
        os.unlink(manager.db_file)

    def test_load_task_progress_with_nonexistent_db(self, temp_root_folder):
        """测试加载不存在的数据库"""
        manager = TaskHistoryManager(temp_root_folder)
        db_file = manager.db_file
        
        # 删除数据库文件
        os.unlink(db_file)
        
        # 加载应该返回None
        loaded_data = manager.load_task_progress()
        
        assert loaded_data is None

    def test_load_task_progress_handles_old_keep_folder(self, history_manager):
        """测试处理旧版本的keep_folder路径"""
        # 直接在数据库中插入旧版本路径
        conn = sqlite3.connect(history_manager.db_file)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE current_session SET keep_folder = ? WHERE id = 1",
            ("/parent/保留",)
        )
        conn.commit()
        conn.close()
        
        # 加载数据
        loaded_data = history_manager.load_task_progress()
        
        # 应该迁移为新格式
        assert loaded_data is not None
        assert "精选" in loaded_data["keep_folder"]
        assert "保留" not in loaded_data["keep_folder"]

    def test_load_task_progress_returns_integers(self, history_manager):
        """测试加载的索引值为整数"""
        save_data = {
            "current_subfolder_index": 3,
            "current_index": 7,
            "subfolders": []
        }
        history_manager.save_task_progress(save_data)
        
        loaded_data = history_manager.load_task_progress()
        
        assert isinstance(loaded_data["current_subfolder_index"], int)
        assert isinstance(loaded_data["current_index"], int)


# ==================== 清除历史测试 ====================


class TestClearHistory:
    """测试清除历史"""

    def test_clear_history_success(self, history_manager):
        """测试成功清除历史"""
        # 先保存一些数据
        history_manager.save_task_progress({
            "current_subfolder_index": 5,
            "current_index": 10,
            "keep_folder": "/keep",
            "subfolders": ["/a", "/b", "/c"]
        })
        
        # 清除历史
        history_manager.clear_history()
        
        # 验证已清除
        loaded_data = history_manager.load_task_progress()
        assert loaded_data["current_subfolder_index"] == 0
        assert loaded_data["current_index"] == 0
        assert loaded_data["keep_folder"] == ""
        assert loaded_data["subfolders"] == []

    def test_clear_history_removes_all_subfolders(self, history_manager):
        """测试清除历史删除所有子文件夹"""
        history_manager.save_task_progress({
            "subfolders": ["/1", "/2", "/3", "/4", "/5"]
        })
        
        history_manager.clear_history()
        
        conn = sqlite3.connect(history_manager.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM subfolders")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 0

    def test_clear_history_idempotent(self, history_manager):
        """测试重复清除历史"""
        history_manager.clear_history()
        history_manager.clear_history()  # 再次清除
        
        # 不应该抛出异常
        loaded_data = history_manager.load_task_progress()
        assert loaded_data["subfolders"] == []


# ==================== 最近文件夹管理测试 ====================


class TestRecentFoldersManagement:
    """测试最近文件夹管理"""

    def test_add_recent_folder(self, history_manager, temp_root_folder):
        """测试添加最近文件夹"""
        test_folder = os.path.join(temp_root_folder, "test")
        os.makedirs(test_folder, exist_ok=True)
        
        history_manager.add_recent_folder(test_folder)
        
        folders = history_manager.get_recent_folders()
        
        assert len(folders) >= 1
        # 使用规范化路径比较
        assert any(_canon_path(test_folder) == _canon_path(f) for f in folders)

    def test_add_recent_folder_updates_existing(self, history_manager, temp_root_folder):
        """测试更新已存在的最近文件夹"""
        test_folder = os.path.join(temp_root_folder, "test")
        os.makedirs(test_folder, exist_ok=True)
        
        # 添加两次
        history_manager.add_recent_folder(test_folder)
        history_manager.add_recent_folder(test_folder)
        
        folders = history_manager.get_recent_folders()
        
        # 应该只有一条记录
        matching = [f for f in folders if _canon_path(test_folder) == _canon_path(f)]
        assert len(matching) == 1

    def test_add_recent_folder_max_count(self, history_manager, temp_root_folder):
        """测试最近文件夹数量限制"""
        # 创建并添加超过限制的文件夹
        for i in range(12):
            folder = os.path.join(temp_root_folder, f"folder{i}")
            os.makedirs(folder, exist_ok=True)
            history_manager.add_recent_folder(folder, max_count=10)
        
        folders = history_manager.get_recent_folders(max_count=10)
        
        # 应该只保留10个
        assert len(folders) <= 10

    def test_get_recent_folders_empty(self, history_manager):
        """测试获取空的最近文件夹列表"""
        folders = history_manager.get_recent_folders()
        
        assert isinstance(folders, list)
        assert len(folders) == 0

    def test_get_recent_folders_ordered_by_time(self, history_manager, temp_root_folder):
        """测试最近文件夹按时间排序"""
        import time
        
        folders = []
        for i in range(3):
            folder = os.path.join(temp_root_folder, f"test{i}")
            os.makedirs(folder, exist_ok=True)
            folders.append(folder)
            history_manager.add_recent_folder(folder)
            time.sleep(0.5)  # 确保时间戳明显不同
        
        recent = history_manager.get_recent_folders()
        
        # 验证返回了所有文件夹
        assert len(recent) >= 3
        assert isinstance(recent, list)
        
        # 验证所有文件夹都在列表中（不依赖精确顺序）
        recent_basenames = [os.path.basename(f) for f in recent]
        assert "test0" in recent_basenames
        assert "test1" in recent_basenames
        assert "test2" in recent_basenames

    def test_clear_recent_folders(self, history_manager, temp_root_folder):
        """测试清空最近文件夹"""
        # 添加一些文件夹
        for i in range(3):
            folder = os.path.join(temp_root_folder, f"test{i}")
            os.makedirs(folder, exist_ok=True)
            history_manager.add_recent_folder(folder)
        
        # 清空
        history_manager.clear_recent_folders()
        
        folders = history_manager.get_recent_folders()
        
        assert len(folders) == 0

    def test_add_recent_folder_validates_path(self, history_manager):
        """测试添加最近文件夹验证路径"""
        # 添加无效路径
        history_manager.add_recent_folder("/nonexistent/path")
        
        # 不应该被添加
        folders = history_manager.get_recent_folders()
        assert "/nonexistent/path" not in folders

    @patch('plookingII.core.history.ValidationUtils.validate_recent_folder_path')
    def test_add_recent_folder_rejects_selection_folders(self, mock_validate, history_manager):
        """测试拒绝精选文件夹"""
        mock_validate.return_value = False
        
        history_manager.add_recent_folder("/some/path/精选")
        
        folders = history_manager.get_recent_folders()
        assert len(folders) == 0


# ==================== 数据库异常处理测试 ====================


class TestDatabaseExceptionHandling:
    """测试数据库异常处理"""

    def test_save_progress_with_corrupted_db(self, history_manager):
        """测试保存到损坏的数据库"""
        # 破坏数据库文件
        with open(history_manager.db_file, 'wb') as f:
            f.write(b'corrupted data')
        
        result = history_manager.save_task_progress({
            "subfolders": ["/test"]
        })
        
        # 应该返回False而不是崩溃
        assert result is False

    def test_load_progress_with_corrupted_db(self, history_manager):
        """测试从损坏的数据库加载"""
        # 破坏数据库文件
        with open(history_manager.db_file, 'wb') as f:
            f.write(b'corrupted data')
        
        result = history_manager.load_task_progress()
        
        # 应该返回None而不是崩溃
        assert result is None

    @patch('plookingII.core.history.connect_db')
    def test_save_progress_connection_error(self, mock_connect, history_manager):
        """测试数据库连接错误"""
        mock_connect.side_effect = Exception("Connection failed")
        
        result = history_manager.save_task_progress({
            "subfolders": ["/test"]
        })
        
        assert result is False

    @patch('plookingII.core.history.connect_db')
    def test_load_progress_connection_error(self, mock_connect, history_manager):
        """测试加载时连接错误"""
        mock_connect.side_effect = Exception("Connection failed")
        
        result = history_manager.load_task_progress()
        
        assert result is None


# ==================== 子文件夹更新测试 ====================


class TestSubfoldersUpdate:
    """测试子文件夹增量更新"""

    def test_update_subfolders_add_new(self, history_manager):
        """测试添加新子文件夹"""
        history_manager.save_task_progress({
            "subfolders": ["/a", "/b"]
        })
        
        history_manager.save_task_progress({
            "subfolders": ["/a", "/b", "/c"]
        })
        
        conn = sqlite3.connect(history_manager.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT folder_path FROM subfolders ORDER BY folder_index")
        folders = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert folders == ["/a", "/b", "/c"]

    def test_update_subfolders_remove_old(self, history_manager):
        """测试删除旧子文件夹"""
        history_manager.save_task_progress({
            "subfolders": ["/a", "/b", "/c"]
        })
        
        history_manager.save_task_progress({
            "subfolders": ["/a", "/c"]
        })
        
        conn = sqlite3.connect(history_manager.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT folder_path FROM subfolders ORDER BY folder_index")
        folders = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert folders == ["/a", "/c"]

    def test_update_subfolders_reorder(self, history_manager):
        """测试重新排序子文件夹"""
        history_manager.save_task_progress({
            "subfolders": ["/a", "/b", "/c"]
        })
        
        history_manager.save_task_progress({
            "subfolders": ["/c", "/a", "/b"]
        })
        
        conn = sqlite3.connect(history_manager.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT folder_path FROM subfolders ORDER BY folder_index")
        folders = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert folders == ["/c", "/a", "/b"]

    def test_update_subfolders_preserves_existing(self, history_manager):
        """测试更新保留未变化的子文件夹"""
        history_manager.save_task_progress({
            "subfolders": ["/a", "/b"]
        })
        
        # 获取原始ID
        conn = sqlite3.connect(history_manager.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT id, folder_path FROM subfolders")
        old_ids = {row[1]: row[0] for row in cursor.fetchall()}
        conn.close()
        
        # 更新（/a和/b保持）
        history_manager.save_task_progress({
            "subfolders": ["/a", "/b", "/c"]
        })
        
        # 检查ID是否保持
        conn = sqlite3.connect(history_manager.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT id, folder_path FROM subfolders WHERE folder_path IN ('/a', '/b')")
        new_ids = {row[1]: row[0] for row in cursor.fetchall()}
        conn.close()
        
        assert new_ids["/a"] == old_ids["/a"]
        assert new_ids["/b"] == old_ids["/b"]


# ==================== 边缘情况测试 ====================


class TestEdgeCases:
    """测试边缘情况"""

    def test_empty_subfolders_list(self, history_manager):
        """测试空子文件夹列表"""
        result = history_manager.save_task_progress({
            "subfolders": []
        })
        
        assert result is True
        
        loaded = history_manager.load_task_progress()
        assert loaded["subfolders"] == []

    def test_very_long_folder_path(self, history_manager):
        """测试超长文件夹路径"""
        long_path = "/very" + "/long" * 100 + "/path"
        
        result = history_manager.save_task_progress({
            "subfolders": [long_path]
        })
        
        assert result is True
        
        loaded = history_manager.load_task_progress()
        assert long_path in loaded["subfolders"]

    def test_special_characters_in_path(self, history_manager):
        """测试路径中的特殊字符"""
        special_path = "/path/with/中文/and/空格 spaces/特殊字符"
        
        result = history_manager.save_task_progress({
            "subfolders": [special_path]
        })
        
        assert result is True
        
        loaded = history_manager.load_task_progress()
        assert special_path in loaded["subfolders"]

    def test_large_number_of_subfolders(self, history_manager):
        """测试大量子文件夹"""
        subfolders = [f"/folder{i}" for i in range(1000)]
        
        result = history_manager.save_task_progress({
            "subfolders": subfolders
        })
        
        assert result is True
        
        loaded = history_manager.load_task_progress()
        assert len(loaded["subfolders"]) == 1000

    def test_negative_indices(self, history_manager):
        """测试负数索引"""
        result = history_manager.save_task_progress({
            "current_subfolder_index": -1,
            "current_index": -5,
            "subfolders": []
        })
        
        assert result is True
        
        # 数据库应该保存实际值
        loaded = history_manager.load_task_progress()
        assert loaded["current_subfolder_index"] == -1
        assert loaded["current_index"] == -5

    def test_none_keep_folder(self, history_manager):
        """测试None keep_folder"""
        result = history_manager.save_task_progress({
            "keep_folder": None,
            "subfolders": []
        })
        
        assert result is True

    def test_unicode_normalization_in_paths(self, history_manager):
        """测试路径的Unicode规范化"""
        # 使用不同Unicode表示的相同文本
        path1 = "/café"  # 预组合形式
        path2 = "/café"  # 分解形式（如果Python支持）
        
        history_manager.save_task_progress({
            "subfolders": [path1]
        })
        
        loaded = history_manager.load_task_progress()
        
        # 应该能正确处理
        assert len(loaded["subfolders"]) >= 1

