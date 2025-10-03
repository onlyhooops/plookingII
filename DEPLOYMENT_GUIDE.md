# PlookingII 部署指南

**版本**: 1.0.0  
**更新时间**: 2025年10月2日  

---

## 📋 系统要求

### 最低要求
- **操作系统**: macOS 10.14+ / Windows 10+ / Linux (Ubuntu 18.04+)
- **Python**: 3.8+
- **内存**: 4GB RAM
- **存储**: 100MB 可用空间

### 推荐配置
- **操作系统**: macOS 12+ / Windows 11 / Linux (Ubuntu 20.04+)
- **Python**: 3.11+
- **内存**: 8GB+ RAM
- **存储**: 500MB+ 可用空间

---

## 🚀 快速部署

### 1. 环境准备

#### 安装Python依赖
```bash
# 克隆项目
git clone <repository-url>
cd plookingII

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

#### 开发环境依赖（可选）
```bash
# 安装开发依赖
pip install -r requirements-dev.txt
```

### 2. 配置检查

#### 验证安装
```bash
# 检查Python版本
python --version

# 检查依赖
pip list

# 运行基础测试
python -m pytest tests/ -v --tb=short
```

### 3. 启动应用

#### 命令行启动
```bash
# 方式1: 直接运行
python -m plookingII

# 方式2: 使用启动脚本
python plookingII/__main__.py

# 方式3: 指定文件夹启动
python -m plookingII --folder "/path/to/images"
```

#### GUI启动
```bash
# 启动图形界面
python -m plookingII.app.main
```

---

## 🔧 配置选项

### 环境变量

#### 基础配置
```bash
# 设置日志级别
export PLOOKING_LOG_LEVEL=INFO

# 设置缓存目录
export PLOOKING_CACHE_DIR="/path/to/cache"

# 设置最大内存使用量 (MB)
export PLOOKING_MAX_MEMORY=1024
```

#### 高级配置
```bash
# 启用性能监控
export PLOOKING_ENABLE_MONITORING=true

# 设置监控间隔 (秒)
export PLOOKING_MONITOR_INTERVAL=5

# 启用调试模式
export PLOOKING_DEBUG=true
```

### 配置文件

创建 `config/local_config.py` 文件：

```python
# 本地配置文件
LOCAL_CONFIG = {
    # 缓存设置
    'cache': {
        'max_size_mb': 512,
        'cleanup_threshold': 0.8,
        'enable_disk_cache': True
    },
    
    # UI设置
    'ui': {
        'theme': 'dark',
        'window_size': (1200, 800),
        'auto_fit_images': True
    },
    
    # 性能设置
    'performance': {
        'max_concurrent_loads': 4,
        'preload_count': 3,
        'enable_gpu_acceleration': False
    }
}
```

---

## 📦 打包部署

### 创建可执行文件

#### 使用PyInstaller
```bash
# 安装PyInstaller
pip install pyinstaller

# 创建单文件可执行程序
pyinstaller --onefile --windowed plookingII/__main__.py

# 创建目录形式的可执行程序
pyinstaller --onedir --windowed plookingII/__main__.py
```

#### 自定义打包脚本
```bash
# 使用项目提供的打包脚本
python build/build.py

# macOS专用打包
python build/package_mac_x86.py
```

### Docker部署

#### Dockerfile示例
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxcb-xinerama0 \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 设置环境变量
ENV PLOOKING_LOG_LEVEL=INFO
ENV PLOOKING_CACHE_DIR=/app/cache

# 创建缓存目录
RUN mkdir -p /app/cache

# 暴露端口（如果需要）
EXPOSE 8080

# 启动命令
CMD ["python", "-m", "plookingII"]
```

#### Docker Compose
```yaml
version: '3.8'

services:
  plookingii:
    build: .
    volumes:
      - ./images:/app/images:ro
      - ./cache:/app/cache
    environment:
      - PLOOKING_LOG_LEVEL=INFO
      - PLOOKING_MAX_MEMORY=1024
    ports:
      - "8080:8080"
```

---

## 🔍 故障排除

### 常见问题

#### 1. 依赖安装失败
```bash
# 问题：pip安装失败
# 解决：升级pip和setuptools
pip install --upgrade pip setuptools wheel

# 问题：PyQt6安装失败
# 解决：使用conda安装
conda install pyqt6
```

#### 2. 应用启动失败
```bash
# 问题：找不到模块
# 解决：检查Python路径
export PYTHONPATH="${PYTHONPATH}:/path/to/plookingII"

# 问题：权限错误
# 解决：检查文件权限
chmod +x plookingII/__main__.py
```

#### 3. 性能问题
```bash
# 问题：内存使用过高
# 解决：调整缓存设置
export PLOOKING_MAX_MEMORY=512

# 问题：启动缓慢
# 解决：禁用某些功能
export PLOOKING_ENABLE_MONITORING=false
```

### 日志调试

#### 启用详细日志
```bash
# 设置日志级别为DEBUG
export PLOOKING_LOG_LEVEL=DEBUG

# 指定日志文件
export PLOOKING_LOG_FILE="/path/to/plooking.log"

# 启动应用
python -m plookingII
```

#### 日志文件位置
- **macOS**: `~/Library/Logs/PlookingII/`
- **Windows**: `%APPDATA%\PlookingII\Logs\`
- **Linux**: `~/.local/share/PlookingII/logs/`

---

## 🔧 维护和更新

### 定期维护

#### 清理缓存
```bash
# 手动清理缓存
python -c "
from plookingII.core.cache import clear_all_caches
clear_all_caches()
"

# 或删除缓存目录
rm -rf ~/.cache/PlookingII/
```

#### 更新依赖
```bash
# 检查过期依赖
pip list --outdated

# 更新所有依赖
pip install --upgrade -r requirements.txt

# 更新特定依赖
pip install --upgrade PyQt6
```

### 版本更新

#### 从源码更新
```bash
# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt

# 运行迁移脚本（如果有）
python scripts/migrate.py
```

#### 备份配置
```bash
# 备份用户配置
cp -r ~/.config/PlookingII/ ~/.config/PlookingII.backup/

# 备份缓存（可选）
cp -r ~/.cache/PlookingII/ ~/.cache/PlookingII.backup/
```

---

## 📊 监控和性能

### 性能监控

#### 启用内置监控
```bash
# 启动时启用监控
export PLOOKING_ENABLE_MONITORING=true
python -m plookingII
```

#### 监控指标
- **内存使用**: 应用内存占用情况
- **CPU使用**: 处理器使用率
- **缓存效率**: 缓存命中率和使用量
- **操作统计**: 用户操作频率和响应时间

### 性能优化

#### 内存优化
```python
# 在配置文件中设置
LOCAL_CONFIG = {
    'cache': {
        'max_size_mb': 256,  # 减少缓存大小
        'cleanup_threshold': 0.7,  # 更早清理
    },
    'performance': {
        'max_concurrent_loads': 2,  # 减少并发加载
        'preload_count': 1,  # 减少预加载
    }
}
```

#### 磁盘优化
```bash
# 使用SSD存储缓存
export PLOOKING_CACHE_DIR="/path/to/ssd/cache"

# 定期清理临时文件
find ~/.cache/PlookingII/ -type f -mtime +7 -delete
```

---

## 🔐 安全考虑

### 文件权限
```bash
# 设置适当的文件权限
chmod 755 plookingII/
chmod 644 plookingII/*.py

# 保护配置文件
chmod 600 config/local_config.py
```

### 网络安全
- 如果启用网络功能，确保使用HTTPS
- 定期更新依赖以修复安全漏洞
- 避免在生产环境中启用调试模式

---

## 📞 支持和帮助

### 获取帮助
```bash
# 查看帮助信息
python -m plookingII --help

# 查看版本信息
python -m plookingII --version

# 运行诊断
python -m plookingII --diagnose
```

### 报告问题
1. 收集系统信息
2. 复现问题步骤
3. 收集相关日志
4. 提交Issue或联系支持团队

---

**部署指南版本**: 1.0.0  
**最后更新**: 2025年10月2日  
**适用版本**: PlookingII v1.0.0+
