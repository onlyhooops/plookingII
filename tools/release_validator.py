#!/usr/bin/env python3
"""
PlookingII 版本发布验证工具

此脚本自动执行发布前的关键检查，确保代码质量和版本一致性。
"""

import os
import re
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

class ReleaseValidator:
    """版本发布验证器"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.passed_checks: List[str] = []

    def run_command(self, cmd: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
        """运行命令并返回结果"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                cwd=self.project_root
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)

    def check_version_consistency(self) -> bool:
        """检查版本号一致性"""
        print("🔍 检查版本号一致性...")

        # 读取主版本号
        constants_file = self.project_root / "plookingII" / "config" / "constants.py"
        main_version = None

        if constants_file.exists():
            with open(constants_file, 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    main_version = match.group(1)

        if not main_version:
            self.issues.append("❌ 无法从 constants.py 读取主版本号")
            return False

        # 检查文档中的版本引用
        version_files = [
            "README.md",
            "VERSION_HISTORY.md",
            "TECHNICAL_GUIDE.md",
            "MAINTENANCE_GUIDELINES.md",
            "doc/ARCHITECTURE.md",
            "doc/UI_STRINGS_GUIDE.md"
        ]

        inconsistent_files = []

        for file_path in version_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 查找版本号模式，排除当前版本
                    other_versions = re.findall(r'v?(\d+\.\d+\.\d+)', content)
                    if other_versions:
                        # 检查是否有与主版本不同的版本
                        for version in other_versions:
                            if version != main_version and not version.startswith('1.0.0') and version not in ['1.2.0', '1.2.1', '1.2.2', '1.2.3', '1.2.4', '1.2.5']:  # 排除历史版本
                                inconsistent_files.append(f"{file_path}: 发现版本 {version}")

        if inconsistent_files:
            self.warnings.extend([f"⚠️  版本不一致: {file}" for file in inconsistent_files])
        else:
            self.passed_checks.append(f"✅ 版本号一致性检查通过 (主版本: {main_version})")

        return len(inconsistent_files) == 0

    def check_imports(self) -> bool:
        """检查 Python 导入"""
        print("🔍 检查 Python 导入...")

        code, stdout, stderr = self.run_command([
            sys.executable, "-c", "import plookingII; print('Import successful')"
        ])

        if code == 0:
            self.passed_checks.append("✅ 主包导入检查通过")
            if "WARNING" in stderr or "ERROR" in stderr:
                self.warnings.append(f"⚠️  导入警告: {stderr.strip()}")
            return True
        else:
            self.issues.append(f"❌ 主包导入失败: {stderr}")
            return False

    def check_code_quality(self) -> bool:
        """检查代码质量"""
        print("🔍 检查代码质量...")

        # 检查 flake8
        code, stdout, stderr = self.run_command(["flake8", "plookingII/"])
        if code == 0:
            self.passed_checks.append("✅ flake8 代码风格检查通过")
        else:
            self.issues.append(f"❌ flake8 检查失败:\n{stdout}")

        # 检查基本语法
        code, stdout, stderr = self.run_command([
            sys.executable, "-m", "py_compile", "plookingII/__init__.py"
        ])
        if code == 0:
            self.passed_checks.append("✅ Python 语法检查通过")
        else:
            self.issues.append(f"❌ Python 语法错误: {stderr}")

        return len(self.issues) == 0

    def check_tests(self) -> bool:
        """检查测试状态"""
        print("🔍 检查测试状态...")

        # 简单的测试检查
        tests_dir = self.project_root / "tests"
        if not tests_dir.exists():
            self.issues.append("❌ 测试目录不存在")
            return False

        test_files = list(tests_dir.glob("**/*test*.py"))
        if len(test_files) < 10:
            self.warnings.append(f"⚠️  测试文件数量较少: {len(test_files)}")
        else:
            self.passed_checks.append(f"✅ 测试文件数量正常: {len(test_files)}")

        return True

    def check_documentation(self) -> bool:
        """检查文档完整性"""
        print("🔍 检查文档完整性...")

        required_docs = [
            "README.md",
            "CHANGELOG.md",
            "VERSION_HISTORY.md",
            "TECHNICAL_GUIDE.md",
            "DOCUMENTATION_INDEX.md",
            "TEST_COVERAGE_REPORT.md",
            "RELEASE_CHECKLIST.md"
        ]

        missing_docs = []
        for doc in required_docs:
            if not (self.project_root / doc).exists():
                missing_docs.append(doc)

        if missing_docs:
            self.issues.extend([f"❌ 缺少文档: {doc}" for doc in missing_docs])
        else:
            self.passed_checks.append("✅ 核心文档完整性检查通过")

        return len(missing_docs) == 0

    def check_project_structure(self) -> bool:
        """检查项目结构"""
        print("🔍 检查项目结构...")

        required_dirs = [
            "plookingII",
            "tests",
            "tools",
            "archive"
        ]

        missing_dirs = []
        for dir_name in required_dirs:
            if not (self.project_root / dir_name).exists():
                missing_dirs.append(dir_name)

        if missing_dirs:
            self.issues.extend([f"❌ 缺少目录: {dir_name}" for dir_name in missing_dirs])
        else:
            self.passed_checks.append("✅ 项目结构检查通过")

        return len(missing_dirs) == 0

    def generate_report(self) -> Dict[str, Any]:
        """生成验证报告"""
        total_checks = len(self.passed_checks) + len(self.issues) + len(self.warnings)
        passed_count = len(self.passed_checks)

        report = {
            "timestamp": "2025-09-30",
            "project": "PlookingII",
            "validation_summary": {
                "total_checks": total_checks,
                "passed": passed_count,
                "issues": len(self.issues),
                "warnings": len(self.warnings),
                "success_rate": f"{(passed_count/total_checks*100):.1f}%" if total_checks > 0 else "0%"
            },
            "passed_checks": self.passed_checks,
            "issues": self.issues,
            "warnings": self.warnings,
            "ready_for_release": len(self.issues) == 0
        }

        return report

    def run_validation(self) -> bool:
        """运行完整验证"""
        print("🚀 PlookingII 版本发布验证开始...")
        print(f"📁 项目目录: {self.project_root}")
        print("-" * 60)

        # 执行所有检查
        checks = [
            self.check_project_structure,
            self.check_version_consistency,
            self.check_imports,
            self.check_code_quality,
            self.check_tests,
            self.check_documentation
        ]

        for check in checks:
            try:
                check()
            except Exception as e:
                self.issues.append(f"❌ 检查失败: {check.__name__}: {str(e)}")

        # 生成报告
        report = self.generate_report()

        print("-" * 60)
        print("📊 验证结果汇总:")
        print(f"✅ 通过检查: {len(self.passed_checks)}")
        print(f"⚠️  警告: {len(self.warnings)}")
        print(f"❌ 问题: {len(self.issues)}")
        print(f"📈 成功率: {report['validation_summary']['success_rate']}")

        if self.passed_checks:
            print("\n✅ 通过的检查:")
            for check in self.passed_checks:
                print(f"  {check}")

        if self.warnings:
            print("\n⚠️  警告:")
            for warning in self.warnings:
                print(f"  {warning}")

        if self.issues:
            print("\n❌ 需要修复的问题:")
            for issue in self.issues:
                print(f"  {issue}")

        print("-" * 60)

        if report["ready_for_release"]:
            print("🎉 验证通过！项目已准备好发布。")
            return True
        else:
            print("🚨 验证失败！请修复上述问题后重新验证。")
            return False

def main():
    """主函数"""
    validator = ReleaseValidator()
    success = validator.run_validation()

    # 保存报告
    report = validator.generate_report()
    report_file = validator.project_root / "release_validation_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n📄 详细报告已保存到: {report_file}")

    # 返回适当的退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
