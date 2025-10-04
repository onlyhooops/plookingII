"""
pytest配置文件 - 包含全局fixtures和测试保护机制
"""
import os
import sys
import threading
import time
import signal
from pathlib import Path
from typing import Generator, Any
from unittest.mock import Mock, MagicMock

import pytest


# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# 超时和并发保护
# ============================================================================

class TimeoutError(Exception):
    """超时异常"""
    pass


class ConcurrencyGuard:
    """并发和死锁防护"""
    
    def __init__(self):
        self.active_threads = []
        self.locks = []
        self.max_threads = 100
        self.deadlock_timeout = 30  # 30秒检测死锁
        
    def register_thread(self, thread: threading.Thread):
        """注册线程"""
        self.active_threads.append(thread)
        
    def register_lock(self, lock: threading.Lock):
        """注册锁"""
        self.locks.append(lock)
        
    def check_deadlock(self) -> bool:
        """检查是否可能死锁"""
        # 简单的死锁检测：检查是否有过多活动线程
        active_count = sum(1 for t in self.active_threads if t.is_alive())
        return active_count > self.max_threads
    
    def cleanup(self):
        """清理资源"""
        # 等待所有线程结束，但有超时
        start_time = time.time()
        for thread in self.active_threads:
            remaining = self.deadlock_timeout - (time.time() - start_time)
            if remaining > 0 and thread.is_alive():
                thread.join(timeout=remaining)
        self.active_threads.clear()
        self.locks.clear()


@pytest.fixture(scope="session")
def concurrency_guard() -> Generator[ConcurrencyGuard, None, None]:
    """会话级别的并发防护"""
    guard = ConcurrencyGuard()
    yield guard
    guard.cleanup()


@pytest.fixture(autouse=True)
def timeout_protection():
    """每个测试的超时保护"""
    # pytest-timeout 已经提供了超时机制，这里添加额外的保护
    start_time = time.time()
    yield
    elapsed = time.time() - start_time
    if elapsed > 60:  # 单个测试超过60秒发出警告
        pytest.warns(UserWarning, match="Test took longer than 60 seconds")


# ============================================================================
# 外部调用超时保护
# ============================================================================

class MockExternalCall:
    """Mock外部调用，带超时保护"""
    
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        
    def __call__(self, func, *args, **kwargs):
        """执行函数调用，带超时"""
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=self.timeout)
        
        if thread.is_alive():
            raise TimeoutError(f"External call exceeded {self.timeout}s timeout")
        
        if exception[0]:
            raise exception[0]
            
        return result[0]


@pytest.fixture
def mock_external_call():
    """提供带超时的外部调用mock"""
    return MockExternalCall(timeout=5.0)


# ============================================================================
# 环境和平台检测
# ============================================================================

@pytest.fixture(scope="session")
def is_ci() -> bool:
    """检测是否在CI环境中运行"""
    return os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"


@pytest.fixture(scope="session")
def is_macos() -> bool:
    """检测是否在macOS上运行"""
    return sys.platform == "darwin"


def pytest_configure(config):
    """pytest配置钩子"""
    # 在CI环境中自动跳过某些测试
    if os.getenv("CI") == "true":
        config.addinivalue_line(
            "markers", "skip_ci: 自动在CI环境跳过"
        )


def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    is_ci = os.getenv("CI") == "true"
    
    for item in items:
        # 在CI环境跳过标记为skip_ci的测试
        if is_ci and "skip_ci" in item.keywords:
            item.add_marker(pytest.mark.skip(reason="跳过CI环境"))
            
        # 慢测试标记
        if "slow" in item.keywords:
            item.add_marker(pytest.mark.timeout(600))  # 慢测试10分钟超时
        
        # UI测试需要显示环境
        if "ui" in item.keywords and not os.getenv("DISPLAY"):
            if sys.platform != "darwin":  # macOS不需要DISPLAY
                item.add_marker(pytest.mark.skip(reason="需要显示环境"))


# ============================================================================
# Mock对象和测试数据
# ============================================================================

@pytest.fixture
def temp_test_dir(tmp_path) -> Path:
    """临时测试目录"""
    test_dir = tmp_path / "test_data"
    test_dir.mkdir(exist_ok=True)
    return test_dir


@pytest.fixture
def sample_image_path(temp_test_dir) -> Path:
    """创建示例图片文件"""
    from PIL import Image
    
    # 创建一个简单的测试图片
    img = Image.new('RGB', (100, 100), color='red')
    img_path = temp_test_dir / "test_image.jpg"
    img.save(img_path)
    return img_path


@pytest.fixture
def mock_config():
    """Mock配置对象"""
    config = Mock()
    config.CACHE_SIZE = 100
    config.MAX_IMAGE_SIZE = 1024 * 1024
    config.ENABLE_PRELOAD = True
    return config


@pytest.fixture
def mock_logger():
    """Mock日志对象"""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    return logger


# ============================================================================
# 资源清理
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_resources():
    """自动清理测试资源"""
    # 测试前的设置
    yield
    # 测试后的清理
    import gc
    gc.collect()  # 强制垃圾回收


@pytest.fixture(scope="function")
def isolated_test():
    """隔离测试环境"""
    # 保存原始状态
    original_sys_path = sys.path.copy()
    original_env = os.environ.copy()
    
    yield
    
    # 恢复状态
    sys.path = original_sys_path
    os.environ.clear()
    os.environ.update(original_env)


# ============================================================================
# 性能测试辅助
# ============================================================================

@pytest.fixture
def performance_tracker():
    """性能跟踪器"""
    class PerformanceTracker:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            
        def start(self):
            self.start_time = time.time()
            
        def stop(self):
            self.end_time = time.time()
            
        @property
        def elapsed(self) -> float:
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return 0.0
            
        def assert_faster_than(self, seconds: float):
            assert self.elapsed < seconds, f"操作耗时{self.elapsed}秒，超过{seconds}秒限制"
    
    return PerformanceTracker()


# ============================================================================
# Mock macOS特定功能
# ============================================================================

@pytest.fixture
def mock_cocoa():
    """Mock Cocoa框架"""
    if sys.platform != "darwin":
        mock_cocoa_module = MagicMock()
        sys.modules['Cocoa'] = mock_cocoa_module
        sys.modules['AppKit'] = mock_cocoa_module
        sys.modules['Foundation'] = mock_cocoa_module
        yield mock_cocoa_module
        # 清理
        for module in ['Cocoa', 'AppKit', 'Foundation']:
            if module in sys.modules:
                del sys.modules[module]
    else:
        yield None


# ============================================================================
# 数据库测试支持
# ============================================================================

@pytest.fixture
def mock_db_connection():
    """Mock数据库连接"""
    connection = Mock()
    connection.cursor = Mock(return_value=Mock())
    connection.commit = Mock()
    connection.rollback = Mock()
    connection.close = Mock()
    return connection


# ============================================================================
# 网络测试支持
# ============================================================================

@pytest.fixture
def mock_network_call():
    """Mock网络调用"""
    def _mock_call(url: str, timeout: float = 5.0):
        # 模拟网络延迟
        time.sleep(0.1)
        return {"status": "success", "url": url}
    return _mock_call


# ============================================================================
# 测试报告增强
# ============================================================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """增强测试报告"""
    outcome = yield
    report = outcome.get_result()
    
    # 添加自定义测试信息
    if report.when == "call":
        # 记录测试执行时间
        report.test_duration = call.stop - call.start
        
        # 记录是否超时
        if hasattr(item, 'timeout') and report.test_duration > item.timeout:
            report.timeout_exceeded = True


# ============================================================================
# CI专用配置
# ============================================================================

def pytest_addoption(parser):
    """添加命令行选项"""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="运行慢速测试"
    )
    parser.addoption(
        "--run-flaky",
        action="store_true",
        default=False,
        help="运行不稳定的测试"
    )


def pytest_runtest_setup(item):
    """测试设置钩子"""
    # 跳过慢测试（除非明确指定）
    if "slow" in item.keywords and not item.config.getoption("--run-slow"):
        pytest.skip("需要 --run-slow 选项来运行慢测试")
        
    # 跳过不稳定的测试（除非明确指定）
    if "flaky" in item.keywords and not item.config.getoption("--run-flaky"):
        pytest.skip("需要 --run-flaky 选项来运行不稳定的测试")

