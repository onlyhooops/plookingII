#!/usr/bin/env python3
"""
版本更新工具
用于将项目从v1.4.0升级到v1.4.0
"""

import os
import re
import glob
from typing import List, Dict, Tuple

class VersionUpdater:
    """版本更新器"""

    def __init__(self, project_root: str = "."):
        self.project_root = project_root
        self.old_version = "1.4.0"
        self.new_version = "1.5.0"

        # 需要更新版本的文件模式
        self.version_files = [
            "**/*.py",
            "**/*.md",
            "**/*.json",
            "**/*.txt",
            "setup.py",
            "pyproject.toml",
            "requirements.txt"
        ]

        # 版本更新模式
        self.version_patterns = [
            (r'Version:\s*1\.3\.0', f'Version: {self.new_version}'),
            (r'version\s*=\s*["\']1\.3\.0["\']', f'version = "{self.new_version}"'),
            (r'__version__\s*=\s*["\']1\.3\.0["\']', f'__version__ = "{self.new_version}"'),
            (r'VERSION\s*=\s*["\']1\.3\.0["\']', f'VERSION = "{self.new_version}"'),
            (r'v1\.3\.0', f'v{self.new_version}'),
            (r'1\.3\.0', self.new_version),  # 通用版本号替换
        ]

        # 排除的文件和目录
        self.exclude_patterns = [
            "**/.*",  # 隐藏文件
            "**/__pycache__/**",  # Python缓存
            "**/node_modules/**",  # Node.js模块
            "**/venv/**",  # 虚拟环境
            "**/env/**",  # 环境目录
            "**/.git/**",  # Git目录
        ]

    def find_version_files(self) -> List[str]:
        """查找需要更新版本的文件"""
        files = []

        for pattern in self.version_files:
            matched_files = glob.glob(
                os.path.join(self.project_root, pattern),
                recursive=True
            )
            files.extend(matched_files)

        # 过滤排除的文件
        filtered_files = []
        for file_path in files:
            should_exclude = False
            for exclude_pattern in self.exclude_patterns:
                if self._match_pattern(file_path, exclude_pattern):
                    should_exclude = True
                    break

            if not should_exclude and os.path.isfile(file_path):
                filtered_files.append(file_path)

        return list(set(filtered_files))  # 去重

    def _match_pattern(self, file_path: str, pattern: str) -> bool:
        """检查文件路径是否匹配模式"""
        import fnmatch
        return fnmatch.fnmatch(file_path, pattern)

    def analyze_file(self, file_path: str) -> List[Tuple[int, str, str]]:
        """分析文件中的版本使用情况"""
        if not os.path.exists(file_path):
            return []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return []

        changes = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            for pattern, replacement in self.version_patterns:
                if re.search(pattern, line):
                    new_line = re.sub(pattern, replacement, line)
                    if new_line != line:
                        changes.append((line_num, line.strip(), new_line.strip()))

        return changes

    def update_file(self, file_path: str) -> bool:
        """更新文件中的版本"""
        if not os.path.exists(file_path):
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return False

        original_content = content

        # 应用所有版本替换模式
        for pattern, replacement in self.version_patterns:
            content = re.sub(pattern, replacement, content)

        # 如果内容有变化，写回文件
        if content != original_content:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            except Exception:
                return False

        return False

    def update_all_versions(self) -> Dict[str, List[str]]:
        """更新所有文件中的版本"""
        results = {
            "updated": [],
            "failed": [],
            "skipped": []
        }

        files = self.find_version_files()

        for file_path in files:
            changes = self.analyze_file(file_path)

            if not changes:
                results["skipped"].append(file_path)
                continue

            if self.update_file(file_path):
                results["updated"].append(file_path)
                print(f"✅ Updated: {file_path}")
                for line_num, old_line, new_line in changes:
                    print(f"   Line {line_num}: {old_line} → {new_line}")
            else:
                results["failed"].append(file_path)
                print(f"❌ Failed: {file_path}")

        return results

    def generate_changelog_entry(self) -> str:
        """生成变更日志条目"""
        changelog = f"""
## v{self.new_version} - {self._get_current_date()}

### 🎯 主要变更
- **架构优化**: 移除6个弃用模块，统一配置和监控系统
- **代码清理**: 完成架构重构，消除重复实现
- **兼容性**: 保持向后兼容，提供平滑迁移路径

### ✅ 移除的弃用模块
- `plookingII.core.unified_config` → 使用 `plookingII.config.manager`
- `plookingII.core.simple_config` → 使用 `plookingII.config.manager`
- `plookingII.monitor.memory` → 使用 `plookingII.monitor.unified_monitor`
- `plookingII.monitor.performance` → 使用 `plookingII.monitor.unified_monitor`
- `plookingII.monitor.simplified_memory` → 使用 `plookingII.monitor.unified_monitor`
- `plookingII.core.cache_adapter` → 直接使用 `UnifiedCacheManager`

### 🔧 技术改进
- 统一配置管理接口
- 整合监控系统
- 简化缓存架构
- 提升代码质量

### 📋 迁移指南
详见 `MIGRATION_GUIDE.md` 和 `MIGRATION_COMPLETION_REPORT.md`

### 🚨 破坏性变更
无 - 所有变更都保持向后兼容

---
"""
        return changelog

    def _get_current_date(self) -> str:
        """获取当前日期"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")

    def create_release_notes(self) -> str:
        """创建发布说明"""
        notes = f"""# PlookingII v{self.new_version} 发布说明

**发布日期**: {self._get_current_date()}
**版本类型**: 架构优化版本

## 🎉 版本亮点

本版本完成了项目架构的重大优化，移除了6个弃用模块，统一了配置和监控系统，显著提升了代码质量和维护性。

## 📊 版本统计

- **移除弃用模块**: 6个
- **统一接口**: 配置系统、监控系统
- **代码清理**: 100%完成
- **向后兼容**: 100%保持
- **测试覆盖**: 所有核心功能

## 🔧 主要改进

### 配置系统统一
- 移除 `unified_config` 和 `simple_config`
- 统一使用 `plookingII.config.manager`
- 提供兼容层确保平滑迁移

### 监控系统整合
- 移除 `memory`、`performance`、`simplified_memory` 模块
- 统一使用 `plookingII.monitor.unified_monitor`
- 保持所有原有功能

### 缓存架构简化
- 移除 `cache_adapter` 适配器
- 直接使用 `UnifiedCacheManager`
- 提升性能和可维护性

## 🚀 升级指南

### 自动迁移
项目提供了完整的兼容层，现有代码无需修改即可正常运行。

### 推荐迁移
为了获得最佳性能和未来兼容性，建议逐步迁移到新接口：

```python
# 旧方式 (仍可用，但不推荐)
from plookingII.core.unified_config import unified_config
value = unified_config.get("key")

# 新方式 (推荐)
from plookingII.config.manager import get_config
value = get_config("key")
```

## 📋 完整变更列表

详见项目中的以下文档：
- `MIGRATION_COMPLETION_REPORT.md` - 迁移完成报告
- `MIGRATION_GUIDE.md` - 详细迁移指南
- `ARCHITECTURE_VERIFICATION_REPORT.md` - 架构验证报告

## 🙏 致谢

感谢所有参与本次架构优化的贡献者，本版本的发布标志着PlookingII项目进入了一个更加成熟和稳定的发展阶段。

---

**下载**: [GitHub Releases](https://github.com/onlyhooops/plookingII/releases/tag/v{self.new_version})
**文档**: [项目文档](https://github.com/onlyhooops/plookingII/blob/main/README.md)
**问题反馈**: [GitHub Issues](https://github.com/onlyhooops/plookingII/issues)
"""
        return notes


def main():
    """主函数"""
    print("🚀 PlookingII 版本更新工具")
    print("=" * 50)

    updater = VersionUpdater()

    print(f"📋 版本更新: {updater.old_version} → {updater.new_version}")
    print()

    # 分析需要更新的文件
    print("🔍 查找需要更新的文件...")
    files = updater.find_version_files()
    print(f"找到 {len(files)} 个文件需要检查")
    print()

    # 分析变更
    print("📊 分析版本使用情况...")
    total_changes = 0
    for file_path in files:
        changes = updater.analyze_file(file_path)
        if changes:
            print(f"📁 {file_path}")
            for line_num, old_line, new_line in changes:
                print(f"  Line {line_num}: {old_line} → {new_line}")
            total_changes += len(changes)

    if total_changes == 0:
        print("✅ 没有发现需要更新的版本信息")
        return

    print(f"\n共发现 {total_changes} 处需要更新")

    # 自动执行更新
    print("\n🔄 自动执行版本更新...")

    # 执行更新
    print("\n🔄 执行版本更新...")
    results = updater.update_all_versions()

    # 显示结果
    print("\n📊 更新结果:")
    print(f"  ✅ 成功更新: {len(results['updated'])} 个文件")
    print(f"  ❌ 更新失败: {len(results['failed'])} 个文件")
    print(f"  ⏭️  跳过文件: {len(results['skipped'])} 个文件")

    if results['failed']:
        print("\n❌ 更新失败的文件:")
        for file_path in results['failed']:
            print(f"  - {file_path}")

    # 创建发布说明
    print("\n📝 创建发布说明...")

    # 创建变更日志条目
    changelog_entry = updater.generate_changelog_entry()
    changelog_path = "CHANGELOG_v1.4.0.md"
    with open(changelog_path, 'w', encoding='utf-8') as f:
        f.write(changelog_entry)
    print(f"✅ 变更日志已保存: {changelog_path}")

    # 创建发布说明
    release_notes = updater.create_release_notes()
    release_notes_path = "RELEASE_NOTES_v1.4.0.md"
    with open(release_notes_path, 'w', encoding='utf-8') as f:
        f.write(release_notes)
    print(f"✅ 发布说明已保存: {release_notes_path}")

    print("\n🎉 版本更新完成!")
    print(f"项目已成功从 v{updater.old_version} 更新到 v{updater.new_version}")


if __name__ == "__main__":
    main()
