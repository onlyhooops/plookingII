#!/usr/bin/env python3
"""
架构完整性测试

验证项目架构的完整性和一致性，防止架构回退。
"""

import os
import re
import ast
import pytest
from pathlib import Path
from typing import Set, Dict


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
PLOOKING_DIR = PROJECT_ROOT / "plookingII"


class TestArchitectureIntegrity:
    """架构完整性测试"""

    def test_deprecated_modules_not_exist(self):
        """测试已弃用的模块文件不存在"""
        deprecated_modules = [
            "plookingII/core/unified_config.py",
            "plookingII/core/simple_config.py",
            "plookingII/monitor/memory.py",
            "plookingII/monitor/performance.py",
            "plookingII/monitor/simplified_memory.py",
            "plookingII/core/cache_adapter.py",
        ]

        found_deprecated = []
        for module_path in deprecated_modules:
            full_path = PROJECT_ROOT / module_path
            if full_path.exists():
                found_deprecated.append(module_path)

        assert not found_deprecated, (
            f"发现已弃用的模块被重新引入: {found_deprecated}\n"
            "这些模块已在架构重构中移除，不应被重新引入。"
        )

    def test_deprecated_imports_not_used(self):
        """测试代码中不使用已弃用的导入"""
        deprecated_imports = [
            "from plookingII.core.unified_config import",
            "from plookingII.core.simple_config import",
            "from plookingII.monitor.memory import",
            "from plookingII.monitor.performance import",
            "from plookingII.monitor.simplified_memory import",
            "from plookingII.core.cache_adapter import",
        ]

        violations = []
        for py_file in PLOOKING_DIR.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                for deprecated_import in deprecated_imports:
                    # 排除注释行
                    for line_num, line in enumerate(content.split("\n"), 1):
                        if deprecated_import in line and not line.strip().startswith("#"):
                            violations.append(
                                f"{py_file.relative_to(PROJECT_ROOT)}:{line_num} - {line.strip()}"
                            )
            except Exception as e:
                print(f"警告: 无法读取文件 {py_file}: {e}")

        assert not violations, (
            f"发现使用了已弃用的导入:\n" + "\n".join(violations) + "\n"
            "请使用新的统一接口代替这些已弃用的导入。"
        )

    def test_core_modules_exist(self):
        """测试核心模块文件存在"""
        required_core_modules = [
            "plookingII/__init__.py",
            "plookingII/app/main.py",
            "plookingII/core/image_processing.py",
            "plookingII/core/bidirectional_cache.py",
            "plookingII/config/constants.py",
            "plookingII/config/manager.py",
            "plookingII/config/ui_strings.py",
            "plookingII/ui/managers/operation_manager.py",
        ]

        missing_modules = []
        for module_path in required_core_modules:
            full_path = PROJECT_ROOT / module_path
            if not full_path.exists():
                missing_modules.append(module_path)

        assert not missing_modules, (
            f"核心模块缺失: {missing_modules}\n" "这些模块是项目的核心组件，必须存在。"
        )

    def test_no_circular_imports(self):
        """测试不存在循环导入（基础检查）"""
        # 简化的循环导入检测：检查每个文件的导入依赖
        import_graph: Dict[str, Set[str]] = {}

        for py_file in PLOOKING_DIR.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            module_path = str(py_file.relative_to(PLOOKING_DIR)).replace(os.sep, ".").rstrip(".py")

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)

                imports = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name.startswith("plookingII"):
                                imports.add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.module.startswith("plookingII"):
                            imports.add(node.module)

                import_graph[module_path] = imports

            except Exception as e:
                print(f"警告: 无法解析文件 {py_file}: {e}")

        # 检测直接的相互导入（简化版）
        circular_imports = []
        for module, imports in import_graph.items():
            for imported in imports:
                if imported in import_graph and module in import_graph[imported]:
                    circular_imports.append(f"{module} <-> {imported}")

        assert not circular_imports, f"发现循环导入: {circular_imports}"

    def test_config_structure_integrity(self):
        """测试配置模块结构完整性"""
        config_dir = PLOOKING_DIR / "config"
        assert config_dir.exists(), "config 目录必须存在"

        required_files = ["__init__.py", "constants.py", "manager.py", "ui_strings.py"]

        missing_files = []
        for file_name in required_files:
            if not (config_dir / file_name).exists():
                missing_files.append(file_name)

        assert not missing_files, f"配置模块缺失文件: {missing_files}"

    def test_ui_structure_integrity(self):
        """测试UI模块结构完整性"""
        ui_dir = PLOOKING_DIR / "ui"
        assert ui_dir.exists(), "ui 目录必须存在"

        # 检查必需的子目录
        required_subdirs = ["controllers", "managers"]
        missing_subdirs = []
        for subdir_name in required_subdirs:
            if not (ui_dir / subdir_name).is_dir():
                missing_subdirs.append(subdir_name)

        assert not missing_subdirs, f"UI模块缺失子目录: {missing_subdirs}"

        # 检查关键文件
        required_files = ["window.py", "views.py", "menu_builder.py"]
        missing_files = []
        for file_name in required_files:
            if not (ui_dir / file_name).is_file():
                missing_files.append(file_name)

        assert not missing_files, f"UI模块缺失文件: {missing_files}"


class TestCodeQualityStandards:
    """代码质量标准测试"""

    def test_no_print_statements_in_core(self):
        """测试核心代码中不使用print语句（应使用日志）"""
        core_dirs = [
            PLOOKING_DIR / "core",
            PLOOKING_DIR / "utils",
        ]

        violations = []
        for core_dir in core_dirs:
            if not core_dir.exists():
                continue

            for py_file in core_dir.rglob("*.py"):
                if "__pycache__" in str(py_file):
                    continue

                try:
                    content = py_file.read_text(encoding="utf-8")
                    for line_num, line in enumerate(content.split("\n"), 1):
                        # 排除注释和文档字符串
                        if line.strip().startswith("#") or '"""' in line or "'''" in line:
                            continue

                        # 检测print语句
                        if re.search(r'\bprint\s*\(', line):
                            violations.append(
                                f"{py_file.relative_to(PROJECT_ROOT)}:{line_num} - {line.strip()}"
                            )
                except Exception as e:
                    print(f"警告: 无法读取文件 {py_file}: {e}")

        # 允许一些print语句，但应该有限制
        assert len(violations) <= 5, (
            f"核心代码中发现过多的print语句 ({len(violations)} 处):\n"
            + "\n".join(violations[:10])
            + "\n请使用logging模块代替print进行日志输出。"
        )

    def test_docstrings_exist_for_public_classes(self):
        """测试公共类都有文档字符串"""
        violations = []

        for py_file in PLOOKING_DIR.rglob("*.py"):
            if "__pycache__" in str(py_file) or py_file.name.startswith("test_"):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # 跳过私有类
                        if node.name.startswith("_"):
                            continue

                        # 检查是否有文档字符串
                        docstring = ast.get_docstring(node)
                        if not docstring:
                            violations.append(
                                f"{py_file.relative_to(PROJECT_ROOT)} - 类 {node.name} 缺少文档字符串"
                            )

            except Exception as e:
                print(f"警告: 无法解析文件 {py_file}: {e}")

        # 允许一些类没有文档字符串，但应该有限制
        assert len(violations) <= 20, (
            f"发现 {len(violations)} 个公共类缺少文档字符串:\n"
            + "\n".join(violations[:10])
            + "\n请为公共类添加文档字符串。"
        )

    def test_no_hardcoded_paths(self):
        """测试代码中不包含硬编码的绝对路径"""
        violations = []

        # 常见的硬编码路径模式
        hardcoded_patterns = [
            r'/Users/\w+',
            r'C:\\Users\\',
            r'/home/\w+',
            r'/Volumes/\w+',
        ]

        for py_file in PLOOKING_DIR.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                for line_num, line in enumerate(content.split("\n"), 1):
                    # 排除注释
                    if line.strip().startswith("#"):
                        continue

                    for pattern in hardcoded_patterns:
                        if re.search(pattern, line):
                            violations.append(
                                f"{py_file.relative_to(PROJECT_ROOT)}:{line_num} - {line.strip()}"
                            )

            except Exception as e:
                print(f"警告: 无法读取文件 {py_file}: {e}")

        assert not violations, (
            f"发现硬编码的路径:\n" + "\n".join(violations[:10]) + "\n请使用相对路径或配置文件。"
        )

    def test_exception_handling_exists(self):
        """测试关键函数包含异常处理"""
        violations = []

        critical_modules = [
            PLOOKING_DIR / "core" / "image_loader.py",
            PLOOKING_DIR / "core" / "bidirectional_cache.py",
            PLOOKING_DIR / "utils" / "file_utils.py",
        ]

        for module_file in critical_modules:
            if not module_file.exists():
                continue

            try:
                content = module_file.read_text(encoding="utf-8")
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # 检查函数是否包含try-except
                        has_exception_handling = any(
                            isinstance(child, ast.Try) for child in ast.walk(node)
                        )

                        # 关键函数应该有异常处理
                        if node.name in ['load_image', 'save_cache', 'read_file', 'load'] and not has_exception_handling:
                            violations.append(
                                f"{module_file.relative_to(PROJECT_ROOT)} - 函数 {node.name} 缺少异常处理"
                            )

            except Exception as e:
                print(f"警告: 无法解析文件 {module_file}: {e}")

        # 这是一个软检查，不强制所有函数都有异常处理
        if violations:
            print(f"建议: 以下关键函数应添加异常处理:\n" + "\n".join(violations))


class TestVersionConsistency:
    """版本一致性测试"""

    def test_version_exists_in_constants(self):
        """测试版本号在constants.py中存在"""
        constants_file = PLOOKING_DIR / "config" / "constants.py"
        assert constants_file.exists(), "constants.py 必须存在"

        content = constants_file.read_text(encoding="utf-8")
        assert "VERSION" in content or "version" in content, "constants.py 中必须定义版本号"

    def test_version_format_valid(self):
        """测试版本号格式有效（语义化版本）"""
        constants_file = PLOOKING_DIR / "config" / "constants.py"
        if not constants_file.exists():
            pytest.skip("constants.py 不存在")

        content = constants_file.read_text(encoding="utf-8")

        # 查找版本号定义
        version_pattern = r'VERSION\s*=\s*["\'](\d+\.\d+\.\d+.*?)["\']'
        match = re.search(version_pattern, content)

        if match:
            version = match.group(1)
            # 验证语义化版本格式
            semver_pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$'
            assert re.match(semver_pattern, version), (
                f"版本号格式无效: {version}\n" "应遵循语义化版本规范: MAJOR.MINOR.PATCH"
            )


class TestDependencyManagement:
    """依赖管理测试"""

    def test_requirements_files_exist(self):
        """测试依赖文件存在"""
        required_files = ["requirements.txt", "requirements-dev.txt"]

        missing_files = []
        for file_name in required_files:
            if not (PROJECT_ROOT / file_name).exists():
                missing_files.append(file_name)

        assert not missing_files, f"依赖文件缺失: {missing_files}"

    def test_no_duplicate_dependencies(self):
        """测试依赖文件中没有重复的包"""
        requirements_file = PROJECT_ROOT / "requirements.txt"
        if not requirements_file.exists():
            pytest.skip("requirements.txt 不存在")

        content = requirements_file.read_text(encoding="utf-8")
        packages = set()
        duplicates = []

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # 提取包名（忽略版本号）
            package_name = re.split(r'[>=<~!]', line)[0].strip()

            if package_name in packages:
                duplicates.append(package_name)
            packages.add(package_name)

        assert not duplicates, f"发现重复的依赖包: {duplicates}"

    def test_pinned_versions_in_requirements(self):
        """测试生产依赖使用固定版本"""
        requirements_file = PROJECT_ROOT / "requirements.txt"
        if not requirements_file.exists():
            pytest.skip("requirements.txt 不存在")

        content = requirements_file.read_text(encoding="utf-8")
        unpinned_packages = []

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # 检查是否有版本约束
            if not re.search(r'[>=<~!]=', line):
                unpinned_packages.append(line)

        # 允许少量未固定版本的包，但应该有限制
        assert len(unpinned_packages) <= 2, (
            f"发现未固定版本的生产依赖:\n"
            + "\n".join(unpinned_packages)
            + "\n建议为生产依赖指定明确的版本号。"
        )


class TestSecurityBaseline:
    """安全基线测试"""

    def test_no_hardcoded_credentials(self):
        """测试代码中不包含硬编码的凭据"""
        violations = []

        # 常见的凭据关键字
        credential_patterns = [
            r'password\s*=\s*["\'][^"\']{3,}["\']',
            r'api_key\s*=\s*["\'][^"\']{10,}["\']',
            r'secret\s*=\s*["\'][^"\']{10,}["\']',
            r'token\s*=\s*["\'][^"\']{10,}["\']',
        ]

        for py_file in PLOOKING_DIR.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                for line_num, line in enumerate(content.split("\n"), 1):
                    # 排除注释和示例代码
                    if line.strip().startswith("#") or "example" in line.lower():
                        continue

                    for pattern in credential_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            violations.append(
                                f"{py_file.relative_to(PROJECT_ROOT)}:{line_num}"
                            )

            except Exception as e:
                print(f"警告: 无法读取文件 {py_file}: {e}")

        assert not violations, (
            f"发现可能的硬编码凭据:\n" + "\n".join(violations) + "\n请使用环境变量或配置文件。"
        )

    def test_no_eval_exec_usage(self):
        """测试代码中不使用危险的eval/exec函数"""
        violations = []

        for py_file in PLOOKING_DIR.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                for line_num, line in enumerate(content.split("\n"), 1):
                    if line.strip().startswith("#"):
                        continue

                    if re.search(r'\beval\s*\(', line) or re.search(r'\bexec\s*\(', line):
                        violations.append(
                            f"{py_file.relative_to(PROJECT_ROOT)}:{line_num} - {line.strip()}"
                        )

            except Exception as e:
                print(f"警告: 无法读取文件 {py_file}: {e}")

        assert not violations, (
            f"发现使用eval/exec的危险代码:\n" + "\n".join(violations) + "\n请避免使用eval和exec。"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
