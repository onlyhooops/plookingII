#!/usr/bin/env python3
"""
PlookingII 发布打包脚本

用于构建和打包 macOS 应用程序，生成可分发的 .app bundle 和 .zip 压缩包。

功能：
1. 使用 py2app 构建 macOS 应用
2. 创建可分发的 ZIP 压缩包
3. 生成校验和文件
4. 准备 GitHub Release 发布物

使用方法：
    python3 tools/package_release.py --build           # 仅构建
    python3 tools/package_release.py --package         # 仅打包
    python3 tools/package_release.py --build --package # 构建并打包
    python3 tools/package_release.py --clean           # 清理构建产物

Author: PlookingII Team
Date: 2025-11-07
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path


def get_version():
    """从 __version__.py 获取版本号"""
    version_file = Path(__file__).parent.parent / "plookingII" / "__version__.py"
    namespace = {}
    with open(version_file) as f:
        exec(f.read(), namespace)
    return namespace["__version__"]


def clean_build():
    """清理构建目录"""
    print("🧹 清理构建目录...")

    dirs_to_clean = ["build", "dist", "release"]
    for dirname in dirs_to_clean:
        dirpath = Path(dirname)
        if dirpath.exists():
            print(f"   删除: {dirpath}")
            shutil.rmtree(dirpath)

    # 清理 .egg-info
    for egg_info in Path(".").glob("*.egg-info"):
        print(f"   删除: {egg_info}")
        shutil.rmtree(egg_info)

    print("✅ 清理完成")


def build_app():
    """使用 py2app 构建应用"""
    print("📦 开始构建 macOS 应用...")

    # 检查 setup.py 是否存在
    if not Path("setup.py").exists():
        create_setup_py()

    # 运行 py2app 构建
    try:
        cmd = [sys.executable, "setup.py", "py2app"]
        print(f"   执行: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        print("✅ 应用构建完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 构建失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False


def create_setup_py():
    """创建 setup.py 配置文件"""
    print("📝 创建 setup.py...")

    setup_content = '''#!/usr/bin/env python3
"""
PlookingII py2app 打包配置
"""

from setuptools import setup
from plookingII.__version__ import __version__

APP = ['plookingII/__main__.py']
DATA_FILES = [
    ('', ['LICENSE', 'README.md']),
]

OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'plookingII/logo/PlookingII.icns',
    'plist': {
        'CFBundleName': 'PlookingII',
        'CFBundleDisplayName': 'PlookingII',
        'CFBundleGetInfoString': f"PlookingII {__version__}",
        'CFBundleIdentifier': 'com.plookingii.app',
        'CFBundleVersion': __version__,
        'CFBundleShortVersionString': __version__,
        'NSHumanReadableCopyright': '© 2025 PlookingII Team',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15',
        'LSApplicationCategoryType': 'public.app-category.graphics-design',
        'NSDocumentsFolderUsageDescription': 'PlookingII needs access to your documents to browse images.',
        'NSDesktopFolderUsageDescription': 'PlookingII needs access to your desktop to browse images.',
        'NSDownloadsFolderUsageDescription': 'PlookingII needs access to your downloads to browse images.',
    },
    'packages': ['plookingII'],
    'includes': [
        'objc',
        'Foundation',
        'AppKit',
        'Quartz',
        'Cocoa',
        'PIL',
        'sqlite3',
    ],
    'excludes': [
        'test',
        'tests',
        'pytest',
        'setuptools',
        'distutils',
    ],
    'optimize': 2,
    'compressed': True,
    'semi_standalone': False,
    'site_packages': True,
}

setup(
    name='PlookingII',
    version=__version__,
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
'''

    with open("setup.py", "w") as f:
        f.write(setup_content)

    print("✅ setup.py 创建完成")


def package_app():
    """打包应用为可分发格式"""
    print("📦 开始打包应用...")

    version = get_version()
    dist_dir = Path("dist")
    app_path = dist_dir / "PlookingII.app"

    if not app_path.exists():
        print(f"❌ 应用不存在: {app_path}")
        print("   请先运行 --build 构建应用")
        return False

    # 创建 release 目录
    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)

    # 创建 ZIP 压缩包
    zip_name = f"PlookingII-v{version}-macOS-x86_64.zip"
    zip_path = release_dir / zip_name

    print(f"   创建压缩包: {zip_name}")
    try:
        # 使用 ditto 创建 macOS 兼容的 ZIP
        cmd = ["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app_path), str(zip_path)]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ 压缩包创建完成: {zip_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ 压缩失败: {e}")
        return False

    # 生成 SHA256 校验和
    print("   生成校验和...")
    sha256 = calculate_sha256(zip_path)
    checksum_file = zip_path.with_suffix(".zip.sha256")

    with open(checksum_file, "w") as f:
        f.write(f"{sha256}  {zip_name}\n")

    print(f"✅ 校验和: {sha256}")
    print(f"✅ 校验和文件: {checksum_file}")

    # 显示文件大小
    file_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"📊 文件大小: {file_size_mb:.2f} MB")

    # 创建发布说明
    create_release_notes(version, release_dir)

    print("\n" + "=" * 70)
    print("✅ 打包完成！")
    print("=" * 70)
    print(f"\n发布产物位置: {release_dir.absolute()}")
    print(f"  • 应用压缩包: {zip_name}")
    print(f"  • 校验和文件: {checksum_file.name}")
    print(f"  • 发布说明: RELEASE_NOTES.md")
    print("\n准备发布到 GitHub Release:")
    print(f"  1. 创建新的 Release: v{version}")
    print(f"  2. 上传文件: {zip_name} 和 {checksum_file.name}")
    print(f"  3. 使用 RELEASE_NOTES.md 作为发布说明")
    print("=" * 70 + "\n")

    return True


def calculate_sha256(file_path):
    """计算文件的 SHA256 校验和"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def create_release_notes(version, release_dir):
    """创建发布说明"""
    notes = f"""# PlookingII v{version} Release Notes

## 📦 发布信息

**版本号**: v{version}
**发布日期**: {Path(__file__).stat().st_mtime}
**平台**: macOS x86_64 (Intel)

## 🎯 核心特性

- ✨ **macOS 原生体验** - 完全基于 PyObjC、AppKit、Quartz 框架
- 🚀 **高性能渲染** - CGImage 直通渲染，零拷贝优化
- 🔄 **智能预加载** - 自适应缓存策略，流畅浏览体验
- 🎨 **EXIF 方向修正** - 自动处理图像方向
- 🗂️ **拖拽支持** - 从 Finder 拖拽文件夹快速浏览
- 🌐 **SMB 优化** - 远程文件高效访问

## 💻 系统要求

- **操作系统**: macOS 10.15 (Catalina) 或更高版本
- **架构**: Intel x86_64（不支持 Apple Silicon）
- **内存**: 建议 4GB 以上

## 📥 安装说明

1. 下载 `PlookingII-v{version}-macOS-x86_64.zip`
2. 解压得到 `PlookingII.app`
3. 拖拽到"应用程序"文件夹
4. 首次运行可能需要在"系统偏好设置 > 安全性与隐私"中允许

## 🔐 安全校验

下载后请验证文件完整性：

```bash
shasum -a 256 -c PlookingII-v{version}-macOS-x86_64.zip.sha256
```

## 📝 使用方法

1. 启动应用
2. 拖拽包含图片的文件夹到窗口
3. 使用键盘快捷键浏览：
   - ← → : 切换图片
   - Space : 拖拽移动
   - Cmd+R : 在 Finder 中显示
   - Cmd+Option+R/L : 旋转图片

## 🐛 已知问题

- 仅支持 Intel Mac，Apple Silicon 需要使用 Rosetta 2
- 不支持跨平台（Linux、Windows）

## 🔗 相关链接

- 项目主页: https://github.com/onlyhooops/plookingII
- 问题反馈: https://github.com/onlyhooops/plookingII/issues
- 更新日志: https://github.com/onlyhooops/plookingII/blob/main/CHANGELOG.md

---

**PlookingII Team** © 2025
"""

    notes_file = release_dir / "RELEASE_NOTES.md"
    with open(notes_file, "w") as f:
        f.write(notes)

    print(f"📝 发布说明已创建: {notes_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="PlookingII 发布打包工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 tools/package_release.py --build           # 仅构建
  python3 tools/package_release.py --package         # 仅打包
  python3 tools/package_release.py --build --package # 构建并打包（推荐）
  python3 tools/package_release.py --clean           # 清理
        """,
    )

    parser.add_argument("--build", action="store_true", help="构建应用")
    parser.add_argument("--package", action="store_true", help="打包应用")
    parser.add_argument("--clean", action="store_true", help="清理构建产物")

    args = parser.parse_args()

    # 检查是否在项目根目录
    if not Path("plookingII").exists():
        print("❌ 错误: 请在项目根目录运行此脚本")
        sys.exit(1)

    # 获取版本号
    version = get_version()
    print(f"\n{'=' * 70}")
    print(f"  PlookingII v{version} - 发布打包工具")
    print(f"{'=' * 70}\n")

    try:
        if args.clean:
            clean_build()
            return

        if not (args.build or args.package):
            # 默认行为：构建并打包
            args.build = True
            args.package = True

        if args.build:
            if not build_app():
                sys.exit(1)

        if args.package:
            if not package_app():
                sys.exit(1)

        print("\n🎉 所有操作完成！\n")

    except KeyboardInterrupt:
        print("\n\n⚠️ 操作已取消")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
