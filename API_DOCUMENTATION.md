# PlookingII API 文档

**版本**: 1.0.0  
**生成时间**: 2025年10月2日  

---

## 📚 概述

PlookingII 是一个高性能的图片浏览器应用，采用模块化架构设计。本文档描述了主要的公共API接口。

---

## 🛠️ 工具模块 (Utils)

### PathUtils 类

路径处理和规范化工具类。

#### 方法

##### `normalize_path_basic(path: str) -> str`
基础路径规范化。

**参数**:
- `path`: 要规范化的路径字符串

**返回**: 规范化后的路径字符串

**示例**:
```python
from plookingII.utils.path_utils import PathUtils

normalized = PathUtils.normalize_path_basic("/Users/test/../test/Documents")
# 返回: "/Users/test/Documents"
```

##### `canonicalize_path(path: str, resolve_symlinks: bool = True) -> str`
路径标准化，可选择是否解析符号链接。

**参数**:
- `path`: 要标准化的路径
- `resolve_symlinks`: 是否解析符号链接

**返回**: 标准化后的绝对路径

##### `normalize_folder_path(folder_path: str, resolve_symlinks: bool = False) -> str`
文件夹路径规范化。

**参数**:
- `folder_path`: 文件夹路径
- `resolve_symlinks`: 是否解析符号链接

**返回**: 规范化后的文件夹路径

##### `is_valid_path(path: str) -> bool`
检查路径是否有效。

**参数**:
- `path`: 要检查的路径

**返回**: 路径是否有效

##### `is_valid_folder(folder_path: str) -> bool`
检查文件夹路径是否有效。

**参数**:
- `folder_path`: 要检查的文件夹路径

**返回**: 文件夹路径是否有效

---

### FileUtils 类

文件和文件夹操作工具类。

#### 方法

##### `is_image_file(filename: str) -> bool`
检查文件是否为支持的图片格式。

**参数**:
- `filename`: 文件名或路径

**返回**: 是否为图片文件

**支持格式**: jpg, jpeg, png, bmp, tiff, webp

**示例**:
```python
from plookingII.utils.file_utils import FileUtils

is_image = FileUtils.is_image_file("photo.jpg")  # True
is_image = FileUtils.is_image_file("document.txt")  # False
```

##### `list_files_safe(folder_path: str) -> List[str]`
安全地列出文件夹中的文件。

**参数**:
- `folder_path`: 文件夹路径

**返回**: 文件路径列表

##### `folder_contains_images(folder_path: str, recursive_depth: int = 1) -> bool`
检查文件夹是否包含图片文件。

**参数**:
- `folder_path`: 文件夹路径
- `recursive_depth`: 递归深度

**返回**: 是否包含图片文件

##### `get_image_files(folder_path: str, recursive: bool = False) -> List[str]`
获取文件夹中的所有图片文件。

**参数**:
- `folder_path`: 文件夹路径
- `recursive`: 是否递归搜索

**返回**: 图片文件路径列表

##### `count_image_files(folder_path: str, recursive: bool = False) -> int`
统计文件夹中的图片文件数量。

**参数**:
- `folder_path`: 文件夹路径
- `recursive`: 是否递归统计

**返回**: 图片文件数量

##### `get_folder_info(folder_path: str) -> Tuple[int, int, bool]`
获取文件夹信息。

**参数**:
- `folder_path`: 文件夹路径

**返回**: (总文件数, 图片文件数, 是否包含子文件夹)

##### `is_empty_folder(folder_path: str) -> bool`
检查文件夹是否为空。

**参数**:
- `folder_path`: 文件夹路径

**返回**: 是否为空文件夹

---

### ValidationUtils 类

验证和检查工具类。

#### 方法

##### `validate_folder_path(folder_path: str, check_permissions: bool = True) -> bool`
验证文件夹路径的有效性。

**参数**:
- `folder_path`: 文件夹路径
- `check_permissions`: 是否检查权限

**返回**: 路径是否有效

##### `validate_recent_folder_path(folder_path: str) -> bool`
验证最近文件夹路径。

**参数**:
- `folder_path`: 文件夹路径

**返回**: 路径是否有效

##### `validate_parameter(param, param_name: str, expected_type=None, allow_none: bool = False) -> bool`
验证参数的有效性。

**参数**:
- `param`: 要验证的参数
- `param_name`: 参数名称
- `expected_type`: 期望的类型
- `allow_none`: 是否允许None值

**返回**: 参数是否有效

##### `validate_path_list(paths: List[str], check_existence: bool = True) -> List[str]`
验证路径列表。

**参数**:
- `paths`: 路径列表
- `check_existence`: 是否检查路径存在性

**返回**: 有效的路径列表

##### `is_safe_path(path: str, base_path: Optional[str] = None) -> bool`
检查路径是否安全。

**参数**:
- `path`: 要检查的路径
- `base_path`: 基础路径

**返回**: 路径是否安全

##### `validate_config_value(value, config_name: str, valid_values: Optional[List] = None) -> bool`
验证配置值。

**参数**:
- `value`: 配置值
- `config_name`: 配置名称
- `valid_values`: 有效值列表

**返回**: 配置值是否有效

---

### 错误处理工具

#### 函数

##### `safe_execute(func: Callable, *args, default=None, log_error: bool = True, context: str = "", **kwargs)`
安全执行函数，捕获异常并返回默认值。

**参数**:
- `func`: 要执行的函数
- `*args`: 函数参数
- `default`: 异常时返回的默认值
- `log_error`: 是否记录错误日志
- `context`: 错误上下文描述
- `**kwargs`: 函数关键字参数

**返回**: 函数返回值或默认值

**示例**:
```python
from plookingII.utils.error_utils import safe_execute

def risky_operation():
    return 1 / 0  # 会抛出异常

result = safe_execute(risky_operation, default="error")
# 返回: "error"
```

##### `handle_exceptions(default_return=None, log_level: str = "debug", context: str = "")`
异常处理装饰器。

**参数**:
- `default_return`: 异常时返回的默认值
- `log_level`: 日志级别
- `context`: 错误上下文

**示例**:
```python
from plookingII.utils.error_utils import handle_exceptions

@handle_exceptions(default_return=False)
def might_fail():
    # 可能失败的操作
    pass
```

#### ErrorCollector 类

错误收集器，用于收集和管理多个错误。

##### `add_error(error: Exception, context: str = "")`
添加错误到收集器。

**参数**:
- `error`: 异常对象
- `context`: 错误上下文

##### `has_errors() -> bool`
检查是否有错误。

**返回**: 是否有错误

##### `get_error_summary() -> dict`
获取错误摘要。

**返回**: 错误摘要字典

##### `clear()`
清空所有错误。

---

## 🎮 控制器模块 (Controllers)

### MenuController

菜单控制器，负责应用程序菜单的创建和管理。

#### 方法

##### `__init__(main_window)`
初始化菜单控制器。

**参数**:
- `main_window`: 主窗口实例

##### `setup_menu()`
设置应用程序菜单。

---

### NavigationController

导航控制器，负责图片浏览的导航逻辑。

#### 方法

##### `__init__(main_window)`
初始化导航控制器。

##### `next_image()`
切换到下一张图片。

##### `previous_image()`
切换到上一张图片。

##### `go_to_image(index: int)`
跳转到指定索引的图片。

**参数**:
- `index`: 图片索引

---

### DragDropController

拖拽控制器，处理文件和文件夹的拖拽操作。

#### 方法

##### `__init__(main_window)`
初始化拖拽控制器。

##### `setup_drag_drop()`
设置拖拽功能。

##### `dragEnterEvent(event)`
处理拖拽进入事件。

##### `dropEvent(event)`
处理拖拽放下事件。

---

### ImageViewController

图片视图控制器，负责图片的显示和渲染。

#### 方法

##### `__init__(main_window)`
初始化图片视图控制器。

##### `update_image_display()`
更新图片显示。

##### `fit_image_to_window(image_path: str)`
将图片适应窗口大小。

**参数**:
- `image_path`: 图片路径

---

### StatusBarController

状态栏控制器，管理状态栏信息显示。

#### 方法

##### `__init__(main_window)`
初始化状态栏控制器。

##### `update_status()`
更新状态栏信息。

##### `show_progress(message: str, progress: int)`
显示进度信息。

**参数**:
- `message`: 进度消息
- `progress`: 进度百分比 (0-100)

---

## 📊 监控模块 (Monitor)

### UnifiedMonitorV2

统一监控器，提供系统性能和应用状态监控。

#### 方法

##### `__init__()`
初始化监控器。

##### `start_monitoring()`
开始监控。

##### `stop_monitoring()`
停止监控。

##### `get_performance_stats() -> dict`
获取性能统计信息。

**返回**: 性能统计字典，包含CPU、内存、缓存使用情况

##### `get_operation_stats() -> dict`
获取操作统计信息。

**返回**: 操作统计字典

---

## 🔧 配置模块 (Config)

### 常量

#### `SUPPORTED_IMAGE_EXTS`
支持的图片文件扩展名列表。

**类型**: `List[str]`  
**值**: `['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']`

#### `APP_NAME`
应用程序名称。

**类型**: `str`  
**值**: `"PlookingII"`

---

## 📝 使用示例

### 基本文件操作

```python
from plookingII.utils.file_utils import FileUtils
from plookingII.utils.path_utils import PathUtils

# 检查文件夹是否包含图片
folder_path = "/Users/username/Pictures"
if FileUtils.folder_contains_images(folder_path):
    print("文件夹包含图片文件")
    
    # 获取所有图片文件
    image_files = FileUtils.get_image_files(folder_path)
    print(f"找到 {len(image_files)} 个图片文件")
    
    # 规范化路径
    for image_file in image_files:
        normalized_path = PathUtils.normalize_path_basic(image_file)
        print(f"图片: {normalized_path}")
```

### 安全操作

```python
from plookingII.utils.error_utils import safe_execute
from plookingII.utils.file_utils import FileUtils

def load_image_safely(image_path):
    """安全加载图片"""
    return safe_execute(
        FileUtils.get_image_files,
        image_path,
        default=[],
        context=f"加载图片: {image_path}"
    )

# 使用
images = load_image_safely("/path/to/folder")
```

### 路径验证

```python
from plookingII.utils.validation_utils import ValidationUtils

folder_path = "/Users/username/Pictures"

# 验证文件夹路径
if ValidationUtils.validate_folder_path(folder_path):
    print("文件夹路径有效")
    
    # 检查路径安全性
    if ValidationUtils.is_safe_path(folder_path):
        print("路径安全")
    else:
        print("路径可能不安全")
```

---

## 🔄 版本历史

### v1.0.0 (2025-10-02)
- 初始API文档
- 完整的工具模块API
- 控制器模块基础API
- 监控模块API

---

## 📞 支持

如需技术支持或有任何问题，请查看项目文档或提交Issue。

**项目地址**: PlookingII  
**文档更新**: 2025年10月2日
