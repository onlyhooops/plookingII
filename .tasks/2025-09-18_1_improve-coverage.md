# 背景
文件名：2025-09-18_1_improve-coverage.md
创建于：2025-09-18_18:55:11
创建者: $USER
主分支：main
任务分支：task/improve-coverage_2025-09-18_1
Yolo模式：Off

# 任务描述
将该项目核心业务逻辑代码覆盖率达到 80% 以上。

# 项目概览
PlookingII 图像查看与处理应用，核心在 plookingII/core 与 ui/managers。

⚠️ 警告：永远不要修改此部分 ⚠️
[遵循 RIPER-5 协议：模式、步骤、约束、质量标准]
⚠️ 警告：永远不要修改此部分 ⚠️

# 分析
[待填]

# 提议的解决方案
[待填]

# 当前执行步骤："1. 基线调研与覆盖率基准"

# 任务进度
[待填]

# 最终审查
[待填]

[2025-09-18_21:34:23]
- 已修改：pytest.ini；tests/test_cache_layers_core_new.py；tests/test_cache_core_new.py；tests/test_bidirectional_cache.py；tests/test_optimized_loading_strategies.py；tests/conftest.py
- 更改：配置覆盖率排除与分支覆盖；新增缓存层、缓存管理、双向缓存与优化加载策略的测试；修复测试导入路径
- 原因：提升核心模块可测试性与覆盖率，隔离平台依赖路径
- 覆盖率：当前总覆盖率约 35[2025-09-18_Progress]
- 已修改：pytest.ini；tests/test_cache_layers_core_new.py；tests/test_cache_core_new.py；tests/test_bidirectional_cache.py；tests/test_optimized_loading_strategies.py；tests/conftest.py
- 更改：配置覆盖率排除与分支覆盖；新增缓存层、缓存管理、双向缓存与优化加载策略的测试；修复测试导入路径
- 原因：提升核心模块可测试性与覆盖率，隔离平台依赖路径
- 覆盖率：当前总覆盖率约 35%（核心 cache/**、optimized_loading_strategies 提升明显）
- 阻碍因素：UI 与 macOS 专有 API 路径仍难以在无 GUI 环境下覆盖；functions.py 可测试性不足
- 状态：成功
