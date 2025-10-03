# PlookingII 日志配置说明

## 🎯 日志优化概述

为了减少日志噪音并提升用户体验，PlookingII 现在采用更加简洁的日志输出策略。

## 🔧 日志级别配置

### 默认设置
- **控制台输出**: `WARNING` 级别及以上（减少噪音）
- **文件记录**: `DEBUG` 级别及以上（完整记录）
- **启动报告**: 简化为单行总时间

### 环境变量控制

#### PLOOKINGII_VERBOSE
启用详细日志输出：
```bash
export PLOOKINGII_VERBOSE=1
python3 -m plookingII
```
设置后控制台将显示 `INFO` 级别日志。

#### PLOOKINGII_LOG_LEVEL  
直接设置日志级别：
```bash
export PLOOKINGII_LOG_LEVEL=DEBUG
python3 -m plookingII
```

可选值：`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## 📊 日志输出对比

### 优化前（噪音日志）
```
2025-09-29 23:08:41 [INFO] PlookingII: Startup Performance Report:
2025-09-29 23:08:41 [INFO] PlookingII:   total_startup_time: 0.456s
2025-09-29 23:08:41 [INFO] PlookingII:   main_window_init: 0.089s
2025-09-29 23:08:41 [INFO] PlookingII:   folder_manager: 0.005s
2025-09-29 23:08:41 [INFO] PlookingII:   status_bar_controller: 0.000s
2025-09-29 23:08:45 [INFO] PlookingII: 开始新的工作会话
2025-09-29 23:08:45 [INFO] PlookingII: 工作会话已启动
2025-09-29 23:08:46 [INFO] PlookingII: 统一监控器已初始化
2025-09-29 23:08:46 [INFO] PlookingII: RemoteFileDetector initialized
2025-09-29 23:08:46 [INFO] PlookingII: SMBOptimizer initialized
2025-09-29 23:08:46 [INFO] PlookingII: NetworkCache initialized: 256MB, strategy=lru
2025-09-29 23:08:46 [INFO] PlookingII: RemoteFileManager initialized
2025-09-29 23:08:46 [INFO] PlookingII: Initializing dual-thread processing
2025-09-29 23:08:46 [INFO] PlookingII: 使用轮询文件监听策略
2025-09-29 23:08:46 [INFO] PlookingII: 图片更新管理器已初始化
2025-09-29 23:08:46 [INFO] PlookingII: 文件监听轮询已启动
2025-09-29 23:09:00 [INFO] PlookingII: 图片更新管理器已清理
```

### 优化后（简洁输出）
```
2025-09-29 23:08:41 [INFO] PlookingII: Application started in 0.456s
```

## 🛠️ 开发者调试模式

开发者可以通过以下方式启用详细日志：

### 方式一：环境变量
```bash
export PLOOKINGII_VERBOSE=1
export PLOOKINGII_LOG_LEVEL=DEBUG
python3 -m plookingII
```

### 方式二：临时启用
```bash
PLOOKINGII_VERBOSE=1 python3 -m plookingII
```

## 📁 日志文件位置

详细日志始终记录到文件中：

### macOS
```
~/Library/Logs/PlookingII/
├── plookingII.log      # 完整应用日志
├── errors.log          # 错误日志
└── performance.log     # 性能日志
```

### Windows
```
%APPDATA%/PlookingII/Logs/
```

### Linux
```
~/.local/share/PlookingII/logs/
```

## 🎛️ 应用内日志查看

使用增强日志功能：
```python
from plookingII.core.enhanced_logging import get_enhanced_logger

logger = get_enhanced_logger()
logger.info(LogCategory.SYSTEM, "应用启动")
logger.debug(LogCategory.PERFORMANCE, "性能数据", {"metric": "load_time", "value": 0.1})
```

## ⚡ 性能影响

### 优化效果
- **启动噪音减少**: 95%
- **控制台输出**: 仅关键信息
- **文件记录**: 完整保留
- **开发体验**: 可按需启用详细输出

### 磁盘使用
- 日志文件自动轮转
- 最大文件大小限制
- 自动清理过期日志

---

**配置建议：**
- 一般用户：使用默认配置（安静模式）
- 开发调试：启用 `PLOOKINGII_VERBOSE=1`
- 问题排查：设置 `PLOOKINGII_LOG_LEVEL=DEBUG`

此优化大幅提升了用户体验，同时保持了完整的调试能力。 ✨
