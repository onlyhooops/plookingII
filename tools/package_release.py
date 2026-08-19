#!/usr/bin/env python3
"""
PlookingII macOS x86_64 发布打包脚本

功能：
1. 清理构建环境
2. 生成针对 macOS x86_64 优化的 setup.py
3. 使用 py2app 构建独立应用程序
4. 验证二进制文件架构
5. 打包为发布用的 ZIP 文件

Usage:
    python3 tools/package_release.py [options]
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.absolute()


def get_version():
    """获取版本号"""
    version_file = PROJECT_ROOT / "plookingII" / "__version__.py"
    namespace = {}
    try:
        with open(version_file) as f:
            exec(f.read(), namespace)
        return namespace["__version__"]
    except Exception as e:
        print(f"⚠️ 无法读取版本号: {e}")
        return "0.0.0"


def run_command(cmd, cwd=None, check=True, shell=False):
    """运行命令并打印输出"""
    print(f"Executing: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        subprocess.run(
            cmd,
            cwd=cwd,
            check=check,
            shell=shell,
            text=True,
            capture_output=False,  # 直接输出到终端以便调试
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        return False


def clean_build():
    """清理构建残留"""
    print("\n🧹 清理构建环境...")

    paths_to_clean = [
        PROJECT_ROOT / "build",
        PROJECT_ROOT / "dist",
        PROJECT_ROOT / "setup.py",
    ]

    # 清理目录
    for p in paths_to_clean:
        if p.exists():
            print(f"   Removing: {p}")
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink()

    # 清理 .egg-info
    for p in PROJECT_ROOT.glob("*.egg-info"):
        print(f"   Removing: {p}")
        shutil.rmtree(p, ignore_errors=True)

    # 清理 __pycache__
    print("   Cleaning __pycache__...")
    for p in PROJECT_ROOT.rglob("__pycache__"):
        try:
            shutil.rmtree(p, ignore_errors=True)
        except Exception:
            pass

    print("✅ 清理完成")


def create_setup_py(version):
    """生成 setup.py"""
    print("\n📝 生成 setup.py...")

    # 明确排除列表，减小包体积并避免冲突
    excludes = [
        "tkinter",
        "matplotlib",
        "scipy",
        "numpy",  # 明确排除 numpy
        "pandas",
        "PyQt5",  # 排除 Qt 相关
        "PyQt6",
        "pyside2",
        "PySide6",
        "sip",
        "wx",
        "cv2",  # 排除 OpenCV
        "opencv-python",
        "PIL.TkPlugin",
        "distutils",
        "setuptools",
        "pkg_resources",
        "pip",
        "wheel",
        "ipython",
        "pytest",
    ]

    # 包含列表
    includes = [
        "os",
        "sys",
        "logging",
        "pathlib",
        "shutil",
        "subprocess",
        "threading",
        "time",
        "hashlib",
        "sqlite3",
        "json",
        "plistlib",
        "imp",  # 修复 PIL 依赖问题
        # 第三方库
        "PIL",
        "psutil",
        # macOS 库
        "objc",
        "Foundation",
        "AppKit",
        "Quartz",
        # multiprocessing 相关：解码子进程池（decode_pool）依赖 spawn 子进程，
        # 必须显式包含，否则打包后子进程无法启动
        "multiprocessing",
        "multiprocessing.pool",
        "concurrent",
        "concurrent.futures",
        "queue",
    ]

    packages = [
        "plookingII",
    ]

    setup_content = f"""
from setuptools import setup
import sys

# py2app 兼容性修复：某些 Python SDK 中 zlib 是内置模块，缺少 __file__
import zlib
if not hasattr(zlib, '__file__'):
    # 指向 Python 解释器本身，因为 zlib 已编译进解释器
    zlib.__file__ = sys.executable

APP = ['plookingII/__main__.py']
DATA_FILES = []
OPTIONS = {{
    'argv_emulation': False,
    'iconfile': 'plookingII/logo/PlookingII.icns',
    'plist': {{
        'CFBundleName': 'PlookingII',
        'CFBundleDisplayName': 'PlookingII',
        'CFBundleGetInfoString': 'PlookingII {version}',
        'CFBundleIdentifier': 'com.plookingii.app',
        'CFBundleVersion': '{version}',
        'CFBundleShortVersionString': '{version}',
        'NSHumanReadableCopyright': '© 2025 PlookingII Team',
        'LSMinimumSystemVersion': '10.15',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,  # 支持深色模式
        'LSEnvironment': {{
            'LANG': 'en_US.UTF-8',
            'LC_ALL': 'en_US.UTF-8',
        }},
    }},
    'packages': {packages},
    'includes': {includes},
    'excludes': {excludes},
    'optimize': 2,
    'strip': True,  # 剥离符号以减小体积
    'site_packages': True, # 包含 site-packages
    'semi_standalone': False, # 全独立模式
    'resources': [],
}}

setup(
    name='PlookingII',
    app=APP,
    data_files=DATA_FILES,
    options={{'py2app': OPTIONS}},
    setup_requires=['py2app'],
)
"""

    setup_path = PROJECT_ROOT / "setup.py"
    with open(setup_path, "w") as f:
        f.write(setup_content)

    print(f"✅ setup.py 已生成于 {setup_path}")


def get_size(path):
    """计算文件或目录大小"""
    total = 0
    if path.is_file():
        return path.stat().st_size
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


def verify_arch(app_path):
    """验证二进制架构"""
    print("\n🔍 验证应用架构...")
    binary = app_path / "Contents" / "MacOS" / "PlookingII"

    if not binary.exists():
        print("❌ 找不到二进制文件")
        return False

    try:
        result = subprocess.run(["file", str(binary)], capture_output=True, text=True, check=False)
        output = result.stdout
        print(f"   Binary info: {output.strip()}")

        if "x86_64" in output:
            print("✅ 确认包含 x86_64 架构")
        else:
            print("⚠️ 警告: 未检测到 x86_64 架构")

        return True
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False


def _patch_py2app_zlib():
    """修复 py2app 在 zlib 为内置模块时的兼容性问题

    某些 Python SDK 将 zlib 编译为内置模块（无 __file__ 属性），
    py2app 的 build_app.py 尝试访问 zlib.__file__ 会抛出 AttributeError。
    此函数在构建前为 zlib 注入临时的 __file__ 属性。
    """
    import zlib as _z

    if hasattr(_z, "__file__"):
        return  # 无需修复

    # 为 zlib 注入临时 __file__，指向 _zlib C 扩展模块
    try:
        import _zlib

        _z.__file__ = getattr(_zlib, "__file__", "")
    except ImportError:
        _z.__file__ = ""
    print("   🔧 py2app zlib 兼容性补丁已应用")


def build():
    """执行构建"""
    print("\n📦 开始构建过程...")

    # py2app 兼容性修复：某些 Python SDK 中 zlib 是内置模块，缺少 __file__
    _patch_py2app_zlib()

    version = get_version()
    print(f"   Target Version: {version}")

    # 1. 清理
    clean_build()

    # 2. 生成配置
    create_setup_py(version)

    # 3. 运行 py2app
    print("\n🚀 运行 py2app (这可能需要几分钟)...")
    # 强制指定架构（尽管 py2app 通常跟随 python 解释器，但我们可以通过环境变量尝试影响）
    env = os.environ.copy()
    env["ARCHFLAGS"] = "-arch x86_64"

    cmd = [sys.executable, "setup.py", "py2app"]
    if not run_command(cmd, cwd=PROJECT_ROOT):
        print("❌ 构建失败")
        sys.exit(1)

    app_path = PROJECT_ROOT / "dist" / "PlookingII.app"
    if not app_path.exists():
        print("❌ 构建看似成功但未找到 .app 文件")
        sys.exit(1)

    # 3.1 强力清理未使用的巨型库 (PyQt6 等)
    # py2app 即使排除也可能包含它们，手动删除以减小体积
    print("\n🧹 进一步清理未使用的库...")
    # 库目录随打包所用解释器版本变化（如 python3.11 / python3.14），动态探测
    lib_dir = app_path / "Contents" / "Resources" / "lib"
    lib_path = lib_dir / f"python{sys.version_info.major}.{sys.version_info.minor}"
    if not lib_path.exists():
        candidates = sorted(lib_dir.glob("python3.*")) if lib_dir.exists() else []
        if candidates:
            lib_path = candidates[-1]
            print(
                f"   ⚠️ 未找到 {lib_dir.name}/python{sys.version_info.major}.{sys.version_info.minor}"
                f"，自动使用检测到的 {lib_path.name}"
            )
    unused_libs = ["PyQt6", "PyQt5", "PySide6", "pyside2", "wx", "cv2", "numpy", "matplotlib"]

    for lib_name in unused_libs:
        target = lib_path / lib_name
        if target.exists():
            print(f"   Removing unused lib: {lib_name} ({(get_size(target) / 1024 / 1024):.2f} MB)")
            shutil.rmtree(target, ignore_errors=True)

    print("✅ 构建成功")

    # 4. 验证
    verify_arch(app_path)

    # 5. 签名和权限处理
    print("\n🔐 处理应用签名和权限...")
    try:
        # 移除隔离属性 (修复 "应用已损坏" 提示)
        xattr_ok = run_command(["xattr", "-cr", str(app_path)])
        print("   已移除隔离属性" if xattr_ok else "   ⚠️ 移除隔离属性失败（可忽略）")

        # Ad-hoc 签名
        sign_ok = run_command(["codesign", "--force", "--deep", "-s", "-", str(app_path)])
        if sign_ok:
            print("   已应用 Ad-hoc 签名")
        else:
            print(
                "   ⚠️ Ad-hoc 签名失败（py2app 产物在部分 macOS 版本上无法签名，应用可正常运行，仅 Gatekeeper 会提示）"
            )
    except Exception as e:
        print(f"⚠️ 签名处理遇到警告 (可忽略): {e}")

    return version, app_path


def package(version, app_path):
    """打包为发布的 ZIP"""
    print("\n🎁 打包发布文件...")

    release_dir = PROJECT_ROOT / "release"
    release_dir.mkdir(exist_ok=True)

    zip_name = f"PlookingII-v{version}-macOS-x86_64.zip"
    zip_path = release_dir / zip_name

    # 删除旧的
    if zip_path.exists():
        zip_path.unlink()

    print(f"   Creating: {zip_name}")

    # 使用 ditto 保持权限和资源分叉
    cmd = ["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app_path), str(zip_path)]

    if run_command(cmd):
        print(f"✅ 打包完成: {zip_path}")

        # 计算 SHA256
        sha256 = hashlib.sha256()
        with open(zip_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)

        checksum_path = zip_path.with_suffix(".zip.sha256")
        with open(checksum_path, "w") as f:
            f.write(f"{sha256.hexdigest()}  {zip_name}\n")

        print(f"   SHA256: {checksum_path}")
    else:
        print("❌ 打包失败")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="PlookingII Build Tool")
    parser.add_argument("--clean-only", action="store_true", help="仅清理")
    parser.add_argument("--build", action="store_true", help="执行完整构建（默认行为，与 Makefile 保持一致）")
    args = parser.parse_args()

    if args.clean_only:
        clean_build()
        return

    try:
        version, app_path = build()
        package(version, app_path)
        print("\n✨ 所有任务完成！")
    except KeyboardInterrupt:
        print("\n⚠️ 用户取消")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 未预期的错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
