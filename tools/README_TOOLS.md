# PlookingII Tools Guide

## 代码风格工具

### code_style_fixer.py (推荐使用)
**功能**: 批量修复 flake8 发现的代码风格问题
**用法**: 
```bash
python tools/code_style_fixer.py
```

**修复项目**:
- W293: 空行包含空白字符
- W291: 行尾空白字符
- W391: 文件末尾空行
- F401: 未使用的导入
- E231: 逗号后缺少空格
- E303: 过多空行

### safe_style_fixer.py
**功能**: 只修复确定安全的代码风格问题（验证语法）
**用法**: 
```bash
python tools/safe_style_fixer.py
```

**特点**:
- 修复前后都验证 Python 语法
- 避免破坏代码结构
- 适合大批量自动化修复

---

## 工具清理记录

### 已删除的重复/过期工具

#### fix_code_style.py (已删除于 2025-10-02)
- **原因**: 与 `code_style_fixer.py` 功能重复
- **决策**: 保留 `code_style_fixer.py`（更完整、270行）
- **删除收益**: -254 行工具代码

#### add_deprecation_warnings.py (已删除于 2025-10-02)
- **原因**: 目标模块已在 v1.4.0 移除，工具已过期
- **功能**: 为废弃模块添加警告（已无对象）
- **删除收益**: -74 行工具代码

#### check_deprecated_imports.py (已删除于 2025-10-02)
- **原因**: 检查的导入已在 v1.4.0 清理，工具已过期
- **功能**: 检查已废弃的导入（已无检查对象）
- **删除收益**: -87 行工具代码

---

## 工具分类

### 活跃工具 (Active)
- `code_cleanup_auditor.py` - 代码清理审计
- `code_style_fixer.py` - 代码风格修复
- `safe_style_fixer.py` - 安全的风格修复
- `architecture_guard.py` - 架构守护
- `version_updater.py` - 版本更新

### 维护工具 (Maintenance)
- `cleanup_all_selection_folders.py` - 清理精选文件夹

### 分析工具 (Analysis)
- `analyze_image_performance.py` - 图像性能分析
- `benchmark_images.py` - 图像基准测试
- `v1_3_0_benchmark.py` - v1.3.0 基准

### 发布工具 (Release)
- `release_validator.py` - 发布验证
- `package_release.py` - 打包发布
- `github_readiness_checker.py` - GitHub 就绪检查

### 迁移工具 (Migration)
- `unify_config_systems.py` - 统一配置系统
- `integrate_cache_systems.py` - 集成缓存系统

---

**最后更新**: 2025-10-02
**维护者**: PlookingII Team

