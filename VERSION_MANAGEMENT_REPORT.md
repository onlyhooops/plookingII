# 版本号统一管理报告

## 📋 规范版本号

- **当前版本**: 1.6.0
- **定义位置**: `plookingII/config/constants.py`

## ✅ 版本号管理策略

### 单一真实来源（Single Source of Truth）

- ✅ 版本号只在 `plookingII/config/constants.py` 中定义
- ✅ 所有其他模块通过导入获取版本号
- ✅ 文档字符串中不再硬编码具体版本号

### 自动化版本管理

- ✅ 使用 `semantic-release` 自动更新版本号
- ✅ 配置文件: `pyproject.toml` [tool.semantic_release]
- ✅ 自动更新位置:
  - `pyproject.toml:project.version`
  - `plookingII/config/constants.py:VERSION`

### 版本号引用规范

```python
# ✅ 正确方式
from plookingII.config.constants import VERSION

# ❌ 错误方式
__version__ = "1.6.0"  # 硬编码
VERSION = "1.6.0"  # 重复定义
```

## 📊 清理统计

- 处理文件数: 83
- 清理的硬编码版本号: 83
- 移除的 __version__ 变量: 待统计

## 🔧 修改的文件

- `plookingII/__init__.py`
- `plookingII/__main__.py`
- `plookingII/app/main.py`
- `plookingII/config/__init__.py`
- `plookingII/config/cache_optimization_config.py`
- `plookingII/config/fun_messages_config.py`
- `plookingII/config/manager.py`
- `plookingII/config/ui_strings.py`
- `plookingII/core/__init__.py`
- `plookingII/core/base_classes.py`
- `plookingII/core/bidirectional_cache.py`
- `plookingII/core/cache/__init__.py`
- `plookingII/core/cache/adapters.py`
- `plookingII/core/cache/cache_adapter.py`
- `plookingII/core/cache/cache_monitor.py`
- `plookingII/core/cache/cache_policy.py`
- `plookingII/core/cache/config.py`
- `plookingII/core/cache/unified_cache.py`
- `plookingII/core/cache.py`
- `plookingII/core/cache_interface.py`
- `plookingII/core/cleanup_utils.py`
- `plookingII/core/enhanced_logging.py`
- `plookingII/core/error_handling.py`
- `plookingII/core/file_watcher.py`
- `plookingII/core/functions.py`
- `plookingII/core/globals.py`
- `plookingII/core/history.py`
- `plookingII/core/image_processing.py`
- `plookingII/core/image_rotation.py`
- `plookingII/core/lazy_initialization.py`
- `plookingII/core/lightweight_monitor.py`
- `plookingII/core/memory_estimator.py`
- `plookingII/core/memory_pool.py`
- `plookingII/core/network_cache.py`
- `plookingII/core/optimized_algorithms.py`
- `plookingII/core/optimized_loading_strategies.py`
- `plookingII/core/performance_optimizer.py`
- `plookingII/core/preload_manager.py`
- `plookingII/core/remote_file_detector.py`
- `plookingII/core/remote_file_manager.py`
- `plookingII/core/session_manager.py`
- `plookingII/core/smart_memory_manager.py`
- `plookingII/core/smb_optimizer.py`
- `plookingII/core/threading.py`
- `plookingII/core/unified_cache_manager.py`
- `plookingII/core/unified_interfaces.py`
- `plookingII/db/connection.py`
- `plookingII/imports.py`
- `plookingII/monitor/__init__.py`
- `plookingII/monitor/telemetry.py`
- `plookingII/monitor/unified/__init__.py`
- `plookingII/monitor/unified/monitor_adapter.py`
- `plookingII/monitor/unified/unified_monitor_v2.py`
- `plookingII/monitor/unified_monitor.py`
- `plookingII/services/background_task_manager.py`
- `plookingII/services/history_manager.py`
- `plookingII/services/image_loader_service.py`
- `plookingII/services/recent.py`
- `plookingII/ui/context_menu_manager.py`
- `plookingII/ui/controllers/__init__.py`
- `plookingII/ui/controllers/drag_drop_controller.py`
- `plookingII/ui/controllers/image_view_controller.py`
- `plookingII/ui/controllers/menu_controller.py`
- `plookingII/ui/controllers/navigation_controller.py`
- `plookingII/ui/controllers/rotation_controller.py`
- `plookingII/ui/controllers/status_bar_controller.py`
- `plookingII/ui/controllers/system_controller.py`
- `plookingII/ui/controllers/unified_status_controller.py`
- `plookingII/ui/managers/__init__.py`
- `plookingII/ui/managers/folder_manager.py`
- `plookingII/ui/managers/image_manager.py`
- `plookingII/ui/managers/image_update_manager.py`
- `plookingII/ui/managers/operation_manager.py`
- `plookingII/ui/menu_builder.py`
- `plookingII/ui/utils/user_feedback.py`
- `plookingII/ui/views.py`
- `plookingII/ui/window.py`
- `plookingII/utils/__init__.py`
- `plookingII/utils/error_utils.py`
- `plookingII/utils/file_utils.py`
- `plookingII/utils/path_utils.py`
- `plookingII/utils/robust_error_handler.py`
- `plookingII/utils/validation_utils.py`

## 📖 开发者指南

### 如何在代码中使用版本号

```python
from plookingII.config.constants import VERSION

# 在日志中使用
logger.info(f"PlookingII version {VERSION} started")

# 在 UI 中显示
about_text = f"Version {VERSION}"
```

### 如何更新版本号

1. 使用语义化提交信息（Semantic Commit）

   ```bash
   git commit -m "feat: 新功能"  # 触发 minor 版本更新
   git commit -m "fix: 修复bug"  # 触发 patch 版本更新
   ```

1. semantic-release 将自动：

   - 根据提交信息计算新版本号
   - 更新 `pyproject.toml` 和 `constants.py`
   - 生成 CHANGELOG.md
   - 创建 Git tag

### 版本号规范

遵循 [Semantic Versioning 2.0.0](https://semver.org/)：

- **MAJOR**: 不兼容的 API 修改
- **MINOR**: 向后兼容的功能新增
- **PATCH**: 向后兼容的问题修复

## ✅ 验证清单

- [x] 移除所有硬编码版本号
- [x] 统一从 constants.py 导入
- [x] 配置 semantic-release
- [x] 验证版本号一致性
- [x] 更新文档

______________________________________________________________________

生成时间: {self.\_get_timestamp()}
工具版本: unify_version.py v1.0.0
