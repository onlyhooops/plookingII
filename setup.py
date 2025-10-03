#!/usr/bin/env python3
"""
PlookingII 安装配置文件

专业级macOS图片浏览器，支持SMB远程存储和高性能图像处理。
"""

from setuptools import setup, find_packages
import os
import sys

# 读取版本信息
def get_version():
    """从constants.py获取版本信息"""
    version_file = os.path.join('plookingII', 'config', 'constants.py')
    if os.path.exists(version_file):
        with open(version_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('VERSION = '):
                    return line.split('"')[1]
    return "1.4.0"  # 默认版本

# 读取README
def get_long_description():
    """读取README作为长描述"""
    if os.path.exists('README.md'):
        with open('README.md', 'r', encoding='utf-8') as f:
            return f.read()
    return ""

# 读取依赖
def get_requirements():
    """读取requirements.txt"""
    if os.path.exists('requirements.txt'):
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

# 平台检查
if sys.platform != 'darwin':
    print("警告: PlookingII 专为 macOS 设计，在其他平台上可能无法正常工作。")

setup(
    # 基础信息
    name="plookingII",
    version=get_version(),
    description="专业级macOS图片浏览器，支持SMB远程存储和高性能图像处理",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",

    # 作者信息
    author="PlookingII Team",
    author_email="plookingii@example.com",
    maintainer="PlookingII Team",
    maintainer_email="plookingii@example.com",

    # 项目链接
    url="https://github.com/onlyhooops/plookingII",
    project_urls={
        "Bug Reports": "https://github.com/onlyhooops/plookingII/issues",
        "Source": "https://github.com/onlyhooops/plookingII",
        "Documentation": "https://github.com/onlyhooops/plookingII/blob/main/README.md",
    },

    # 包配置
    packages=find_packages(exclude=['tests*', 'tools*', 'doc*', 'archive*']),
    package_data={
        'plookingII': [
            'resources/*',
            'config/*.json',
            'ui/resources/*',
        ],
    },
    include_package_data=True,

    # 依赖
    install_requires=get_requirements(),
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'flake8>=6.0.0',
            'black>=23.0.0',
            'isort>=5.12.0',
            'mypy>=1.0.0',
        ],
        'security': [
            'bandit>=1.7.0',
            'safety>=2.0.0',
        ],
        'performance': [
            'memory-profiler>=0.60.0',
            'psutil>=5.9.0',
        ],
    },

    # Python版本要求
    python_requires=">=3.9",

    # 平台要求
    platforms=["darwin"],  # macOS only

    # 分类
    classifiers=[
        # 开发状态
        "Development Status :: 4 - Beta",

        # 目标受众
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Developers",

        # 主题
        "Topic :: Multimedia :: Graphics :: Viewers",
        "Topic :: Desktop Environment :: File Managers",
        "Topic :: System :: Filesystems",

        # 许可证
        "License :: OSI Approved :: MIT License",

        # 编程语言
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",

        # 操作系统
        "Operating System :: MacOS :: MacOS X",

        # 环境
        "Environment :: MacOS X :: Cocoa",
        "Environment :: Console",

        # 自然语言
        "Natural Language :: Chinese (Simplified)",
        "Natural Language :: English",
    ],

    # 关键词
    keywords="image viewer macos smb remote storage quartz cocoa",

    # 入口点
    entry_points={
        'console_scripts': [
            'plookingii=plookingII.__main__:main',
            'plooking2=plookingII.__main__:main',  # 简短别名
        ],
        'gui_scripts': [
            'PlookingII=plookingII.__main__:main',
        ],
    },

    # 数据文件
    data_files=[
        ('share/applications', ['resources/PlookingII.desktop']) if os.path.exists('resources/PlookingII.desktop') else [],
        ('share/icons/hicolor/256x256/apps', ['resources/PlookingII.png']) if os.path.exists('resources/PlookingII.png') else [],
    ],

    # ZIP安全
    zip_safe=False,

    # 测试
    test_suite='tests',
    tests_require=[
        'pytest>=7.0.0',
        'pytest-cov>=4.0.0',
    ],

    # 命令
    cmdclass={},

    # 选项
    options={
        'build_exe': {
            'packages': ['plookingII'],
            'excludes': ['tkinter', 'unittest'],
            'include_files': [
                ('plookingII/resources/', 'resources/'),
            ] if os.path.exists('plookingII/resources/') else [],
        },
        'bdist_mac': {
            'bundle_name': 'PlookingII',
            'iconfile': 'resources/PlookingII.icns' if os.path.exists('resources/PlookingII.icns') else None,
        },
    },
)

# 安装后提示
print(f"""
🎉 PlookingII {get_version()} 安装完成！

📖 快速开始:
   plookingii --help              # 查看帮助
   plookingii /path/to/images     # 打开图片目录

🔧 开发模式:
   pip install -e .[dev]         # 安装开发依赖
   pytest                        # 运行测试

📚 更多信息:
   README.md                     # 详细文档
   https://github.com/onlyhooops/plookingII

⚠️  注意: PlookingII 专为 macOS 设计，需要 Python 3.9+ 和 PyObjC。
""")
