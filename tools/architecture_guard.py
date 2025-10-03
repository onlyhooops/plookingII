#!/usr/bin/env python3
"""
架构守护工具
防止架构回退和确保代码质量
"""

import re
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

class ArchitectureGuard:
    """架构守护器"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.issues = []
        self.warnings = []

        # 已移除的弃用模块列表
        self.deprecated_modules = [
            "plookingII/core/unified_config.py",
            "plookingII/core/simple_config.py",
            "plookingII/monitor/memory.py",
            "plookingII/monitor/performance.py",
            "plookingII/monitor/simplified_memory.py",
            "plookingII/core/cache_adapter.py"
        ]

        # 弃用的导入模式
        self.deprecated_imports = [
            r"from plookingII\.core\.unified_config import",
            r"from plookingII\.core\.simple_config import",
            r"from plookingII\.monitor\.memory import",
            r"from plookingII\.monitor\.performance import",
            r"from plookingII\.monitor\.simplified_memory import",
            r"from plookingII\.core\.cache_adapter import"
        ]

        # 推荐的接口模式
        self.recommended_patterns = [
            (r"from plookingII\.config\.manager import get_config", "配置获取"),
            (r"from plookingII\.config\.manager import set_config", "配置设置"),
            (r"from plookingII\.monitor import get_unified_monitor", "统一监控"),
        ]

        # 版本检查文件
        self.version_files = [
            "plookingII/config/constants.py",
            "README.md",
            "VERSION_HISTORY.md"
        ]

        self.expected_version = "1.4.0"

    def log_issue(self, issue: str):
        """记录问题"""
        self.issues.append(issue)
        print(f"❌ {issue}")

    def log_warning(self, warning: str):
        """记录警告"""
        self.warnings.append(warning)
        print(f"⚠️ {warning}")

    def log_success(self, message: str):
        """记录成功"""
        print(f"✅ {message}")

    def check_deprecated_modules(self) -> bool:
        """检查弃用模块是否被重新引入"""
        print("🔍 检查弃用模块...")

        found_deprecated = False
        for module in self.deprecated_modules:
            module_path = self.project_root / module
            if module_path.exists():
                self.log_issue(f"发现已移除的弃用模块: {module}")
                found_deprecated = True

        if not found_deprecated:
            self.log_success("弃用模块检查通过")

        return not found_deprecated

    def check_deprecated_imports(self) -> bool:
        """检查弃用导入是否被使用"""
        print("🔍 检查弃用导入...")

        found_imports = False

        # 遍历Python文件
        for py_file in self.project_root.rglob("*.py"):
            # 跳过一些目录和文件
            if any(skip in str(py_file) for skip in [
                "__pycache__", ".git", "migration_examples", "test_",
                "unify_config_systems.py", "version_updater.py"  # 这些工具文件包含字符串映射
            ]):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    # 跳过注释行
                    stripped = line.strip()
                    if stripped.startswith('#') or not stripped:
                        continue

                    # 检查弃用导入
                    for pattern in self.deprecated_imports:
                        if re.search(pattern, line):
                            self.log_issue(f"弃用导入 {py_file}:{line_num}: {line.strip()}")
                            found_imports = True

            except Exception as e:
                self.log_warning(f"无法检查文件 {py_file}: {e}")

        if not found_imports:
            self.log_success("弃用导入检查通过")

        return not found_imports

    def check_version_consistency(self) -> bool:
        """检查版本一致性"""
        print("🔍 检查版本一致性...")

        version_issues = False

        for file_path in self.version_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    if self.expected_version not in content:
                        self.log_issue(f"版本不一致: {file_path} 中未找到版本 {self.expected_version}")
                        version_issues = True

                except Exception as e:
                    self.log_warning(f"无法检查版本文件 {file_path}: {e}")
            else:
                self.log_warning(f"版本文件不存在: {file_path}")

        if not version_issues:
            self.log_success("版本一致性检查通过")

        return not version_issues

    def check_unified_interfaces(self) -> bool:
        """检查统一接口使用"""
        print("🔍 检查统一接口使用...")

        interface_stats = {
            "config_get": 0,
            "config_set": 0,
            "unified_monitor": 0
        }

        # 遍历核心代码文件
        for py_file in (self.project_root / "plookingII").rglob("*.py"):
            # 跳过测试和缓存文件
            if any(skip in str(py_file) for skip in [
                "__pycache__", "test_", "migration_examples"
            ]):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 统计推荐接口使用
                if "get_config(" in content:
                    interface_stats["config_get"] += content.count("get_config(")
                if "set_config(" in content:
                    interface_stats["config_set"] += content.count("set_config(")
                if "get_unified_monitor(" in content:
                    interface_stats["unified_monitor"] += content.count("get_unified_monitor(")

            except Exception as e:
                self.log_warning(f"无法检查接口使用 {py_file}: {e}")

        # 报告统计结果
        print(f"📊 统一接口使用统计:")
        print(f"   - get_config(): {interface_stats['config_get']} 次")
        print(f"   - set_config(): {interface_stats['config_set']} 次")
        print(f"   - get_unified_monitor(): {interface_stats['unified_monitor']} 次")

        if sum(interface_stats.values()) > 0:
            self.log_success("发现统一接口使用")
        else:
            self.log_warning("未发现统一接口使用")

        return True

    def run_architecture_tests(self) -> bool:
        """运行架构测试"""
        print("🧪 运行架构测试...")

        test_files = [
            "tests/test_architecture.py",
            "tests/test_unified_config.py",
            "tests/test_core_modules.py"
        ]

        tests_passed = True
        tests_run = 0

        for test_file in test_files:
            test_path = self.project_root / test_file
            if test_path.exists():
                try:
                    result = subprocess.run([
                        sys.executable, "-m", "pytest", str(test_path), "-v"
                    ], capture_output=True, text=True, cwd=self.project_root)

                    if result.returncode == 0:
                        self.log_success(f"架构测试通过: {test_file}")
                        tests_run += 1
                    else:
                        self.log_issue(f"架构测试失败: {test_file}")
                        tests_passed = False

                except Exception as e:
                    self.log_warning(f"无法运行测试 {test_file}: {e}")
            else:
                self.log_warning(f"测试文件不存在: {test_file}")

        if tests_run == 0:
            self.log_warning("未找到架构测试文件")
        elif tests_passed:
            self.log_success(f"所有架构测试通过 ({tests_run} 个)")

        return tests_passed

    def check_code_quality(self) -> bool:
        """检查代码质量"""
        print("🔍 检查代码质量...")

        quality_checks = {
            "flake8": ["flake8", "plookingII/", "--max-line-length=100", "--ignore=E203,W503"],
            "black": ["black", "--check", "--diff", "plookingII/"],
            "isort": ["isort", "--check-only", "--diff", "plookingII/"]
        }

        quality_passed = True

        for check_name, command in quality_checks.items():
            try:
                result = subprocess.run(command, capture_output=True, text=True, cwd=self.project_root)

                if result.returncode == 0:
                    self.log_success(f"{check_name} 检查通过")
                else:
                    self.log_warning(f"{check_name} 检查有问题")
                    if result.stdout:
                        print(f"输出: {result.stdout[:500]}...")
                    quality_passed = False

            except FileNotFoundError:
                self.log_warning(f"{check_name} 工具未安装，跳过检查")
            except Exception as e:
                self.log_warning(f"{check_name} 检查失败: {e}")

        return quality_passed

    def generate_report(self) -> Dict[str, Any]:
        """生成检查报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "version": self.expected_version,
            "total_issues": len(self.issues),
            "total_warnings": len(self.warnings),
            "issues": self.issues,
            "warnings": self.warnings,
            "status": "PASS" if len(self.issues) == 0 else "FAIL"
        }

        return report

    def run_all_checks(self) -> bool:
        """运行所有检查"""
        print("🚀 开始架构守护检查")
        print("=" * 50)

        checks = [
            ("弃用模块检查", self.check_deprecated_modules),
            ("弃用导入检查", self.check_deprecated_imports),
            ("版本一致性检查", self.check_version_consistency),
            ("统一接口检查", self.check_unified_interfaces),
            ("架构测试", self.run_architecture_tests),
            ("代码质量检查", self.check_code_quality)
        ]

        all_passed = True

        for check_name, check_func in checks:
            print(f"\n📋 {check_name}")
            print("-" * 30)

            try:
                passed = check_func()
                if not passed:
                    all_passed = False
            except Exception as e:
                self.log_issue(f"{check_name} 执行失败: {e}")
                all_passed = False

        # 生成报告
        report = self.generate_report()

        print("\n" + "=" * 50)
        print("📊 架构守护检查总结")
        print("=" * 50)

        if all_passed:
            print("🟢 状态: 通过")
            print("🎉 所有架构检查通过，项目架构健康！")
        else:
            print("🔴 状态: 失败")
            print(f"❌ 发现 {len(self.issues)} 个问题")

        if self.warnings:
            print(f"⚠️ 发现 {len(self.warnings)} 个警告")

        # 保存报告
        report_path = self.project_root / "architecture_guard_report.json"
        import json
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"📋 详细报告已保存: {report_path}")

        return all_passed


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="PlookingII 架构守护工具")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--check", choices=[
        "deprecated", "imports", "version", "interfaces", "tests", "quality", "all"
    ], default="all", help="运行特定检查")

    args = parser.parse_args()

    guard = ArchitectureGuard(args.project_root)

    if args.check == "all":
        success = guard.run_all_checks()
    elif args.check == "deprecated":
        success = guard.check_deprecated_modules()
    elif args.check == "imports":
        success = guard.check_deprecated_imports()
    elif args.check == "version":
        success = guard.check_version_consistency()
    elif args.check == "interfaces":
        success = guard.check_unified_interfaces()
    elif args.check == "tests":
        success = guard.run_architecture_tests()
    elif args.check == "quality":
        success = guard.check_code_quality()
    else:
        success = guard.run_all_checks()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
