#!/usr/bin/env python3
"""
pytest配置文件

提供测试环境的通用配置和fixture。
"""

import pytest
import tempfile
import shutil
import os
from unittest.mock import MagicMock

@pytest.fixture
def temp_dir():
    """临时目录fixture"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture
def mock_main_window():
    """模拟主窗口fixture"""
    mock_window = MagicMock()
    mock_window.images = []
    mock_window.current_index = 0
    mock_window.current_folder = ""
    mock_window.root_folder = ""
    return mock_window

@pytest.fixture
def sample_images(temp_dir):
    """示例图片文件fixture"""
    images = []
    for i in range(5):
        image_path = os.path.join(temp_dir, f"test_{i:03d}.jpg")
        with open(image_path, 'wb') as f:
            # 简单的JPEG文件头
            f.write(bytes([0xFF, 0xD8, 0xFF, 0xE0]))
            f.write(b"fake image data")
        images.append(image_path)
    return images

@pytest.fixture
def sample_folder_structure(temp_dir):
    """示例文件夹结构fixture"""
    # 创建根文件夹
    root_folder = os.path.join(temp_dir, "photos")
    os.makedirs(root_folder)

    # 创建子文件夹
    subfolders = []
    for i in range(3):
        subfolder = os.path.join(root_folder, f"folder_{i}")
        os.makedirs(subfolder)
        subfolders.append(subfolder)

        # 在每个子文件夹中创建图片
        for j in range(3):
            image_path = os.path.join(subfolder, f"image_{j}.jpg")
            with open(image_path, 'wb') as f:
                f.write(bytes([0xFF, 0xD8, 0xFF, 0xE0]))
                f.write(f"image data {i}-{j}".encode())

    return root_folder, subfolders