#
#
## Error Handling and Observability Policy (v1.2.2)

This project standardizes error handling and observability across hot paths (image loading, rotation, UI, file watching):

- Use plookingII.core.error_handling:
  - Prefer `@error_handler(...)` for call sites where raising is acceptable but recovery is desirable.
  - Prefer `with error_context(name, category=...)` in entrypoints and long-running tasks to ensure classification and logging.
- No bare `except:`. Catch `Exception` at most, and log with `exc_info=True`.
- Fallbacks must be observable:
  - Log a structured debug message when primary path fails and fallback is attempted.
  - Maintain counters for fallbacks in hot paths:
    - OptimizedLoadingStrategy.stats: `fallback_attempts`, `fallback_successes`.
    - ImageRotationProcessor.rotation_stats: `lossless_attempts`, `lossless_successes`, `pil_fallbacks`.
- Logging setup:
  - `__main__` configures logging level via `PLOOKINGII_LOG_LEVEL` and installs rotating error log (error.log) and global exception hook.
  - Use module loggers; avoid prints.

Operational notes:
- Use tools/fallback_metrics_cli.py to get a quick summary combining runtime counters and logs.
- When adding new fallback branches, always: (1) add structured debug log, (2) extend counters, (3) add unit coverage for success/failure.

# PlookingII 技术指南

本文档提供 PlookingII 项目的详细技术实现说明，包括架构设计、核心算法、API 接口和开发指南。

## 目录

- [技术架构](#技术架构)
- [核心模块](#核心模块)
- [图像处理](#图像处理)
- [缓存系统](#缓存系统)
- [性能优化](#性能优化)
- [API 参考](#api-参考)
- [开发指南](#开发指南)
- [测试指南](#测试指南)

---

## 技术架构

### 整体架构设计

PlookingII 采用分层的 MVC 架构，结合模块化设计原则：

```python
# 架构层次
plookingII/
├── app/                    # 应用程序层
│   ├── main.py            # 应用入口
│   └── delegate.py        # 应用代理
├── ui/                     # 用户界面层
│   ├── window.py          # 主窗口
│   ├── views.py           # 视图组件
│   ├── controllers/       # 控制器
│   └── managers/          # UI管理器
├── core/                   # 核心业务层
│   ├── cache.py           # 缓存系统
│   ├── image_processing.py # 图像处理
│   ├── bidirectional_cache.py # 双向缓存
│   └── performance.py     # 性能监控
├── services/              # 服务层
│   └── recent.py         # 最近文件服务
├── db/                    # 数据层
│   └── connection.py     # 数据库连接
└── config/               # 配置层
    └── constants.py      # 常量配置
```

### 设计模式应用

#### 1. MVC 模式
```python
# Model - 数据模型
class ImageModel:
    def __init__(self, path: str):
        self.path = path
        self.metadata = {}
    
# View - 视图组件  
class AdaptiveImageView(NSView):
    def drawRect_(self, rect):
        # CGImage直通渲染
        pass
    
# Controller - 控制器
class ImageViewController:
    def __init__(self, model, view):
        self.model = model
        self.view = view
```

#### 2. 策略模式
```python
class LoadingStrategy:
    def load_image(self, path: str) -> CGImage:
        raise NotImplementedError

class OptimizedLoadingStrategy(LoadingStrategy):
    def load_image(self, path: str) -> CGImage:
        # Quartz-only加载实现
        return self._load_with_quartz(path)

class PreviewLoadingStrategy(LoadingStrategy):
    def load_image(self, path: str) -> CGImage:
        # 预览优化加载
        return self._load_preview(path)
```

#### 3. 观察者模式
```python
class PerformanceMonitor:
    def __init__(self):
        self.observers = []
    
    def add_observer(self, observer):
        self.observers.append(observer)
    
    def notify_performance_change(self, score: float):
        for observer in self.observers:
            observer.on_performance_change(score)
```

#### 4. 单例模式
```python
class ImagePerformanceMonitor:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

---

## 核心模块

### 1. 图像管理器 (ImageManager)

#### 职责与功能
- 统一图像加载和显示管理
- 策略选择和性能调优
- 缓存协调和生命周期管理

#### 核心实现
```python
class ImageManager:
    def __init__(self):
        self.cache = AdvancedImageCache()
        self.processor = HybridImageProcessor()
        self.performance_monitor = ImagePerformanceMonitor()
        self.loading_strategy = OptimizedLoadingStrategy()
    
    def load_image_async(self, path: str, callback):
        """异步加载图像"""
        def load_task():
            try:
                # 检查缓存
                cached_image = self.cache.get(path)
                if cached_image:
                    callback(cached_image, None)
                    return
                
                # 加载图像
                image = self.loading_strategy.load_image(path)
                
                # 缓存图像
                self.cache.put(path, image)
                
                # 主线程回调
                NSOperationQueue.mainQueue().addOperationWithBlock_(
                    lambda: callback(image, None)
                )
            except Exception as e:
                NSOperationQueue.mainQueue().addOperationWithBlock_(
                    lambda: callback(None, e)
                )
        
        # 后台线程执行
        threading.Thread(target=load_task, daemon=True).start()
    
    def apply_performance_tuning(self, performance_score: float):
        """应用性能调优"""
        if performance_score < 60:
            # 降低并发度
            self.loading_strategy.set_concurrency(2)
            # 减少预加载窗口
            self.cache.set_preload_window(1)
        elif performance_score > 80:
            # 提高并发度
            self.loading_strategy.set_concurrency(4)
            # 增加预加载窗口
            self.cache.set_preload_window(3)
```

### 2. 混合图像处理器 (HybridImageProcessor)

#### Quartz-only 处理管道
```python
class HybridImageProcessor:
    def __init__(self):
        self.rotation_processor = ImageRotationProcessor()
        self.statistics = ProcessingStatistics()
    
    def load_image_quartz_only(self, file_path: str, target_size: tuple = None) -> CGImage:
        """Quartz-only图像加载"""
        try:
            # 创建图像源
            url = NSURL.fileURLWithPath_(file_path)
            source = CGImageSourceCreateWithURL(url, None)
            
            if not source:
                raise ValueError(f"无法创建图像源: {file_path}")
            
            # 配置加载选项
            options = {
                # 自动处理EXIF方向
                kCGImageSourceCreateThumbnailWithTransform: True,
                # 创建缩略图
                kCGImageSourceCreateThumbnailFromImageAlways: True,
            }
            
            if target_size:
                # 设置目标尺寸
                max_size = max(target_size)
                options[kCGImageSourceThumbnailMaxPixelSize] = max_size
            
            # 创建CGImage
            image = CGImageSourceCreateThumbnailAtIndex(source, 0, options)
            
            if not image:
                # 尝试直接创建图像
                image = CGImageSourceCreateImageAtIndex(source, 0, {
                    kCGImageSourceCreateThumbnailWithTransform: True
                })
            
            self.statistics.record_success(file_path)
            return image
            
        except Exception as e:
            self.statistics.record_error(file_path, str(e))
            raise
    
    def rotate_image(self, image_path: str, degrees: int) -> bool:
        """图像旋转"""
        return self.rotation_processor.rotate_image(image_path, degrees)
```

### 3. 高级图像缓存 (AdvancedImageCache)

#### 多层缓存架构
```python
class SimpleCacheLayer:
    """简化的缓存层实现"""
    
    def __init__(self, max_size: int = 50):
        self.cache = {}
        self.access_order = []
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str):
        """获取缓存项"""
        if key in self.cache:
            self.hits += 1
            # 更新访问顺序 (LRU)
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        else:
            self.misses += 1
            return None
    
    def put(self, key: str, value, size_mb: float = 0):
        """添加缓存项"""
        # 如果已存在，更新
        if key in self.cache:
            self.cache[key] = value
            self.access_order.remove(key)
            self.access_order.append(key)
            return
        
        # 检查容量限制
        if len(self.cache) >= self.max_size:
            # LRU淘汰
            oldest_key = self.access_order.pop(0)
            del self.cache[oldest_key]
        
        # 添加新项
        self.cache[key] = value
        self.access_order.append(key)
    
    def get_stats(self) -> dict:
        """获取缓存统计"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate
        }

class AdvancedImageCache:
    """高级图像缓存系统"""
    
    def __init__(self, max_size: int = 100):
        # 默认两层缓存（由 AdvancedImageCache 统一管理）；预加载/渐进式为可选
        self.cache_layers = {
            'preview': SimpleCacheLayer(max_size=30),
            'main': SimpleCacheLayer(max_size=max_size)
        }
        
        # 快速引用
        self.main_cache = self.cache_layers['main']
        self.preview_cache = self.cache_layers['preview']
        # 可选：预加载缓存（默认关闭）
        self.preload_cache = self.cache_layers.get('preload')
        # 已移除：渐进式缓存（统一由优化策略按需生成缩略）
```

### 4. 自适应图像视图 (AdaptiveImageView)

#### CGImage 直通渲染
```python
class AdaptiveImageView(NSView):
    """自适应图像视图 - CGImage直通渲染"""
    
    def __init__(self):
        super().__init__()
        self.current_image = None
        self.image_rect = NSRect()
        self.scale_factor = 1.0
    
    def setImage_(self, cg_image):
        """设置CGImage"""
        self.current_image = cg_image
        if cg_image:
            # 计算图像显示矩形
            self._calculate_image_rect()
        self.setNeedsDisplay_(True)
    
    def drawRect_(self, rect):
        """绘制方法 - CGImage直通渲染"""
        if not self.current_image:
            return
        
        # 获取绘制上下文
        context = NSGraphicsContext.currentContext().CGContext()
        
        # 直接绘制CGImage (零拷贝)
        CGContextDrawImage(context, self.image_rect, self.current_image)
    
    def _calculate_image_rect(self):
        """计算图像显示矩形"""
        if not self.current_image:
            return
        
        # 获取图像尺寸
        image_width = CGImageGetWidth(self.current_image)
        image_height = CGImageGetHeight(self.current_image)
        
        # 获取视图尺寸
        view_size = self.bounds().size
        
        # 计算缩放比例 (保持宽高比)
        scale_x = view_size.width / image_width
        scale_y = view_size.height / image_height
        scale = min(scale_x, scale_y)
        
        # 计算显示尺寸
        display_width = image_width * scale
        display_height = image_height * scale
        
        # 居中显示
        x = (view_size.width - display_width) / 2
        y = (view_size.height - display_height) / 2
        
        self.image_rect = NSRect(
            NSPoint(x, y),
            NSSize(display_width, display_height)
        )
        self.scale_factor = scale
```

---

## 图像处理

### Quartz-only 处理流程

#### 1. 图像加载策略
```python
class OptimizedLoadingStrategy:
    """优化加载策略"""
    
    def __init__(self):
        self.concurrency_level = 4
        self.memory_threshold = 100 * 1024 * 1024  # 100MB
    
    def load_image(self, file_path: str, target_size: tuple = None) -> CGImage:
        """智能图像加载"""
        try:
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            
            # 选择加载策略
            if file_size > self.memory_threshold:
                return self._load_large_file(file_path, target_size)
            else:
                return self._load_standard(file_path, target_size)
                
        except Exception as e:
            # 降级处理
            return self._fallback_load(file_path, target_size)
    
    def _load_standard(self, file_path: str, target_size: tuple) -> CGImage:
        """标准加载"""
        url = NSURL.fileURLWithPath_(file_path)
        source = CGImageSourceCreateWithURL(url, None)
        
        options = {
            kCGImageSourceCreateThumbnailWithTransform: True,
            kCGImageSourceCreateThumbnailFromImageAlways: True,
        }
        
        if target_size:
            options[kCGImageSourceThumbnailMaxPixelSize] = max(target_size)
        
        return CGImageSourceCreateThumbnailAtIndex(source, 0, options)
    
    def _load_large_file(self, file_path: str, target_size: tuple) -> CGImage:
        """大文件加载 - 使用内存映射"""
        # 使用内存映射减少内存占用
        with open(file_path, 'rb') as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                data = NSData.dataWithBytes_length_(mm, len(mm))
                source = CGImageSourceCreateWithData(data, None)
                
                options = {
                    kCGImageSourceCreateThumbnailWithTransform: True,
                    kCGImageSourceCreateThumbnailFromImageAlways: True,
                }
                
                if target_size:
                    options[kCGImageSourceThumbnailMaxPixelSize] = max(target_size)
                
                return CGImageSourceCreateThumbnailAtIndex(source, 0, options)
    
    def _fallback_load(self, file_path: str, target_size: tuple) -> CGImage:
        """降级加载"""
        try:
            # 简单加载，不使用缩略图
            url = NSURL.fileURLWithPath_(file_path)
            source = CGImageSourceCreateWithURL(url, None)
            return CGImageSourceCreateImageAtIndex(source, 0, {
                kCGImageSourceCreateThumbnailWithTransform: True
            })
        except Exception:
            return None
```

#### 2. EXIF 方向处理
```python
def get_image_orientation(file_path: str) -> int:
    """获取图像EXIF方向信息"""
    url = NSURL.fileURLWithPath_(file_path)
    source = CGImageSourceCreateWithURL(url, None)
    
    if not source:
        return 1  # 默认方向
    
    # 获取图像属性
    properties = CGImageSourceCopyPropertiesAtIndex(source, 0, None)
    if not properties:
        return 1
    
    # 获取EXIF信息
    exif_dict = properties.get(kCGImagePropertyExifDictionary, {})
    orientation = exif_dict.get(kCGImagePropertyOrientation, 1)
    
    return orientation

def apply_orientation_transform(image: CGImage, orientation: int) -> CGImage:
    """应用方向变换"""
    if orientation == 1:
        return image  # 无需变换
    
    width = CGImageGetWidth(image)
    height = CGImageGetHeight(image)
    
    # 创建位图上下文
    if orientation in [5, 6, 7, 8]:
        # 需要交换宽高
        context = CGBitmapContextCreate(
            None, height, width, 8, 0,
            CGImageGetColorSpace(image),
            kCGImageAlphaPremultipliedLast
        )
    else:
        context = CGBitmapContextCreate(
            None, width, height, 8, 0,
            CGImageGetColorSpace(image),
            kCGImageAlphaPremultipliedLast
        )
    
    # 应用变换矩阵
    transform = _get_orientation_transform(orientation, width, height)
    CGContextConcatCTM(context, transform)
    
    # 绘制图像
    CGContextDrawImage(context, CGRect(0, 0, width, height), image)
    
    # 创建新图像
    return CGBitmapContextCreateImage(context)
```

### 图像旋转功能

#### 旋转处理器
```python
class ImageRotationProcessor:
    """图像旋转处理器"""
    
    def __init__(self):
        self.statistics = RotationStatistics()
    
    def rotate_image(self, image_path: str, degrees: int) -> bool:
        """旋转图像"""
        try:
            # 验证参数
            if degrees % 90 != 0:
                raise ValueError("只支持90度的倍数旋转")
            
            # 加载原图像
            original_image = self._load_image(image_path)
            if not original_image:
                return False
            
            # 执行旋转
            rotated_image = self._rotate_cgimage(original_image, degrees)
            if not rotated_image:
                return False
            
            # 保存旋转后的图像
            success = self._save_image(rotated_image, image_path)
            
            if success:
                self.statistics.record_success(image_path, degrees)
            else:
                self.statistics.record_error(image_path, "保存失败")
            
            return success
            
        except Exception as e:
            self.statistics.record_error(image_path, str(e))
            return False
    
    def _rotate_cgimage(self, image: CGImage, degrees: int) -> CGImage:
        """旋转CGImage"""
        width = CGImageGetWidth(image)
        height = CGImageGetHeight(image)
        
        # 计算旋转后的尺寸
        if degrees % 180 == 0:
            new_width, new_height = width, height
        else:
            new_width, new_height = height, width
        
        # 创建位图上下文
        context = CGBitmapContextCreate(
            None, new_width, new_height, 8, 0,
            CGImageGetColorSpace(image),
            kCGImageAlphaPremultipliedLast
        )
        
        # 移动到中心点
        CGContextTranslateCTM(context, new_width/2, new_height/2)
        
        # 应用旋转
        angle_radians = math.radians(degrees)
        CGContextRotateCTM(context, angle_radians)
        
        # 绘制图像
        CGContextDrawImage(context, 
            CGRect(-width/2, -height/2, width, height), image)
        
        # 创建旋转后的图像
        return CGBitmapContextCreateImage(context)
```

---

## 缓存系统

### 缓存层次结构

#### 1. 默认两层缓存架构（main/preview）
```python
class CacheArchitecture:
    """缓存架构说明
    
    1. 预览缓存 (preview): 小尺寸预览图，快速显示
    2. 主缓存 (main): 当前显示的完整图像
    3. 预加载缓存 (preload): 即将显示的图像预加载（可选，默认关闭）
    """
    pass
```

#### 2. 双向缓存系统
```python
class BidirectionalCache:
    """双向缓存系统"""
    
    def __init__(self, window_size: int = 3):
        self.forward_cache = {}   # 前向缓存
        self.backward_cache = {}  # 后向缓存
        self.window_size = window_size
        self.current_index = 0
        self.image_list = []
    
    def preload_around_index(self, index: int, image_list: list):
        """围绕指定索引预加载图像"""
        self.current_index = index
        self.image_list = image_list
        
        # 预加载前向图像
        for i in range(1, self.window_size + 1):
            forward_index = index + i
            if forward_index < len(image_list):
                self._preload_image(image_list[forward_index], 'forward')
        
        # 预加载后向图像
        for i in range(1, self.window_size + 1):
            backward_index = index - i
            if backward_index >= 0:
                self._preload_image(image_list[backward_index], 'backward')
    
    def _preload_image(self, image_path: str, direction: str):
        """预加载图像"""
        def load_task():
            try:
                # 使用快速加载策略
                strategy = PreviewLoadingStrategy()
                image = strategy.load_image(image_path)
                
                # 存储到对应缓存
                if direction == 'forward':
                    self.forward_cache[image_path] = image
                else:
                    self.backward_cache[image_path] = image
                    
            except Exception as e:
                logger.warning(f"预加载失败 {image_path}: {e}")
        
        # 后台线程执行
        threading.Thread(target=load_task, daemon=True).start()
    
    def get_cached_image(self, image_path: str):
        """获取缓存的图像"""
        # 先检查前向缓存
        if image_path in self.forward_cache:
            return self.forward_cache[image_path]
        
        # 再检查后向缓存
        if image_path in self.backward_cache:
            return self.backward_cache[image_path]
        
        return None
```

### 缓存策略

#### 1. LRU 淘汰策略
```python
class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.cache = OrderedDict()
    
    def get(self, key):
        if key in self.cache:
            # 移动到末尾 (最近使用)
            value = self.cache.pop(key)
            self.cache[key] = value
            return value
        return None
    
    def put(self, key, value):
        if key in self.cache:
            # 更新值并移动到末尾
            self.cache.pop(key)
        elif len(self.cache) >= self.max_size:
            # 删除最久未使用的项 (开头)
            self.cache.popitem(last=False)
        
        self.cache[key] = value
```

#### 2. 内存压力响应
```python
class MemoryPressureHandler:
    """内存压力处理器"""
    
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.memory_monitor = MemoryMonitor()
    
    def handle_memory_pressure(self, pressure_level: str):
        """处理内存压力"""
        if pressure_level == 'low':
            # 轻微清理
            self.cache_manager.clear_preview_cache()
        elif pressure_level == 'medium':
            # 中等清理
            self.cache_manager.clear_preview_cache()
            self.cache_manager.clear_preload_cache()
        elif pressure_level == 'high':
            # 大幅清理
            self.cache_manager.clear_all_except_main()
            # 强制垃圾回收
            import gc
            gc.collect()
```

---

## 性能优化

### 自适应性能调优

#### 1. 性能监控器
```python
class ImagePerformanceMonitor:
    """图像性能监控器"""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.thresholds = {
            'cpu_usage': 80.0,      # CPU使用率阈值
            'memory_usage': 70.0,   # 内存使用率阈值
            'load_time': 200.0,     # 图像加载时间阈值(ms)
            'cache_hit_rate': 60.0, # 缓存命中率阈值
        }
    
    def calculate_performance_score(self) -> float:
        """计算性能分数 (0-100)"""
        scores = []
        
        # CPU性能分数
        cpu_score = max(0, 100 - self.metrics.cpu_usage)
        scores.append(cpu_score)
        
        # 内存性能分数
        memory_score = max(0, 100 - self.metrics.memory_usage)
        scores.append(memory_score)
        
        # 加载时间分数
        load_time_score = max(0, 100 - (self.metrics.avg_load_time / 5))
        scores.append(load_time_score)
        
        # 缓存命中率分数
        cache_score = self.metrics.cache_hit_rate
        scores.append(cache_score)
        
        # 加权平均
        weights = [0.3, 0.3, 0.2, 0.2]
        weighted_score = sum(s * w for s, w in zip(scores, weights))
        
        return max(0, min(100, weighted_score))
    
    def get_optimization_suggestions(self) -> list:
        """获取优化建议"""
        suggestions = []
        
        if self.metrics.cpu_usage > self.thresholds['cpu_usage']:
            suggestions.append('reduce_concurrency')
        
        if self.metrics.memory_usage > self.thresholds['memory_usage']:
            suggestions.append('clear_cache')
        
        if self.metrics.avg_load_time > self.thresholds['load_time']:
            suggestions.append('enable_preview_mode')
        
        if self.metrics.cache_hit_rate < self.thresholds['cache_hit_rate']:
            suggestions.append('increase_cache_size')
        
        return suggestions
```

#### 2. 动态参数调整
```python
class AdaptiveParameterTuner:
    """自适应参数调优器"""
    
    def __init__(self, image_manager):
        self.image_manager = image_manager
        self.performance_monitor = ImagePerformanceMonitor()
        self.default_params = {
            'concurrency_level': 4,
            'preload_window': 3,
            'cache_size': 100,
            'thumbnail_size': 512,
        }
        self.current_params = self.default_params.copy()
    
    def apply_tuning(self, performance_score: float):
        """应用性能调优"""
        if performance_score < 40:
            # 严重性能问题
            self._apply_conservative_settings()
        elif performance_score < 60:
            # 中等性能问题
            self._apply_balanced_settings()
        elif performance_score > 80:
            # 性能良好，可以提升质量
            self._apply_aggressive_settings()
        
        # 应用参数更改
        self._update_manager_settings()
    
    def _apply_conservative_settings(self):
        """保守设置 - 优先稳定性"""
        self.current_params.update({
            'concurrency_level': 1,
            'preload_window': 1,
            'cache_size': 50,
            'thumbnail_size': 256,
        })
    
    def _apply_balanced_settings(self):
        """平衡设置"""
        self.current_params.update({
            'concurrency_level': 2,
            'preload_window': 2,
            'cache_size': 75,
            'thumbnail_size': 384,
        })
    
    def _apply_aggressive_settings(self):
        """激进设置 - 优先性能"""
        self.current_params.update({
            'concurrency_level': 6,
            'preload_window': 5,
            'cache_size': 150,
            'thumbnail_size': 1024,
        })
    
    def _update_manager_settings(self):
        """更新管理器设置"""
        self.image_manager.set_concurrency_level(
            self.current_params['concurrency_level']
        )
        self.image_manager.set_preload_window(
            self.current_params['preload_window']
        )
        self.image_manager.set_cache_size(
            self.current_params['cache_size']
        )
```

### 内存管理

#### 1. 内存监控
```python
class MemoryMonitor:
    """内存监控器"""
    
    def __init__(self):
        self.memory_threshold_mb = 500  # 500MB阈值
        self.warning_threshold_mb = 400  # 400MB警告阈值
    
    def get_memory_usage(self) -> dict:
        """获取内存使用情况"""
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss': memory_info.rss / (1024 * 1024),  # MB
            'vms': memory_info.vms / (1024 * 1024),  # MB
            'percent': process.memory_percent(),
        }
    
    def check_memory_pressure(self) -> str:
        """检查内存压力级别"""
        usage = self.get_memory_usage()
        rss_mb = usage['rss']
        
        if rss_mb > self.memory_threshold_mb:
            return 'high'
        elif rss_mb > self.warning_threshold_mb:
            return 'medium'
        else:
            return 'low'
    
    def force_garbage_collection(self):
        """强制垃圾回收"""
        import gc
        collected = gc.collect()
        logger.info(f"垃圾回收完成，清理了 {collected} 个对象")
        return collected
```

#### 2. 自动内存清理
```python
class AutoMemoryManager:
    """自动内存管理器"""
    
    def __init__(self, cache_manager, memory_monitor):
        self.cache_manager = cache_manager
        self.memory_monitor = memory_monitor
        self.cleanup_timer = None
        self.start_monitoring()
    
    def start_monitoring(self):
        """开始内存监控"""
        def monitor_loop():
            while True:
                try:
                    pressure = self.memory_monitor.check_memory_pressure()
                    if pressure != 'low':
                        self._handle_memory_pressure(pressure)
                    time.sleep(10)  # 每10秒检查一次
                except Exception as e:
                    logger.error(f"内存监控错误: {e}")
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
    
    def _handle_memory_pressure(self, pressure_level: str):
        """处理内存压力"""
        logger.info(f"检测到内存压力: {pressure_level}")
        
        if pressure_level == 'medium':
            # 清理预览和预加载缓存
            self.cache_manager.clear_preview_cache()
            self.cache_manager.clear_preload_cache()
        elif pressure_level == 'high':
            # 清理所有非主缓存
            self.cache_manager.clear_all_except_main()
            # 强制垃圾回收
            self.memory_monitor.force_garbage_collection()
```

---

## API 参考

### 核心 API

#### ImageManager API
```python
class ImageManager:
    """图像管理器主要API"""
    
    def load_image_async(self, path: str, callback: callable) -> None:
        """异步加载图像
        
        Args:
            path: 图像文件路径
            callback: 回调函数 callback(image, error)
        """
    
    def preload_images(self, paths: list) -> None:
        """预加载图像列表
        
        Args:
            paths: 图像路径列表
        """
    
    def clear_cache(self, layer: str = None) -> None:
        """清理缓存
        
        Args:
            layer: 缓存层名称，None表示清理所有
        """
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息
        
        Returns:
            包含缓存统计的字典
        """
```

#### HybridImageProcessor API
```python
class HybridImageProcessor:
    """图像处理器主要API"""
    
    def load_image_quartz_only(self, file_path: str, 
                              target_size: tuple = None) -> CGImage:
        """Quartz-only图像加载
        
        Args:
            file_path: 图像文件路径
            target_size: 目标尺寸 (width, height)
            
        Returns:
            CGImage对象或None
        """
    
    def rotate_image(self, image_path: str, degrees: int) -> bool:
        """旋转图像
        
        Args:
            image_path: 图像文件路径
            degrees: 旋转角度 (90的倍数)
            
        Returns:
            是否成功
        """
    
    def get_processing_stats(self) -> dict:
        """获取处理统计信息
        
        Returns:
            包含处理统计的字典
        """
```

#### AdaptiveImageView API
```python
class AdaptiveImageView(NSView):
    """自适应图像视图主要API"""
    
    def setImage_(self, cg_image: CGImage) -> None:
        """设置显示的图像
        
        Args:
            cg_image: CGImage对象
        """
    
    def setScaleFactor_(self, scale: float) -> None:
        """设置缩放因子
        
        Args:
            scale: 缩放因子
        """
    
    def fitToWindow(self) -> None:
        """适应窗口大小"""
    
    def actualSize(self) -> None:
        """实际大小显示"""
```

### 配置 API

#### 配置常量
```python
# 应用配置
APP_NAME = "PlookingII"
VERSION = "1.0.0"
AUTHOR = "PlookingII Team"

# 缓存配置
MAX_CACHE_SIZE = 100
MEMORY_THRESHOLD_MB = 500

# 图像处理配置
SUPPORTED_IMAGE_EXTS = ['.jpg', '.jpeg', '.png']
IMAGE_PROCESSING_CONFIG = {
    'max_thumbnail_size': 1024,
    'jpeg_quality': 0.95,
    'enable_exif_rotation': True,
}

# 性能配置
PERFORMANCE_CONFIG = {
    'default_concurrency': 4,
    'max_concurrency': 8,
    'preload_window': 3,
    'performance_check_interval': 5.0,
}
```

#### 运行时配置
```python
def get_runtime_config() -> dict:
    """获取运行时配置"""
    return {
        'cache_size': MAX_CACHE_SIZE,
        'memory_threshold': MEMORY_THRESHOLD_MB,
        'concurrency_level': 4,
        'preload_window': 3,
        'enable_performance_tuning': True,
    }

def update_runtime_config(config: dict) -> None:
    """更新运行时配置"""
    # 验证配置参数
    # 应用配置更改
    pass
```

---

## 开发指南

### 环境搭建

#### 1. 系统要求
- macOS 10.15+ (Catalina 或更高版本)
- Python 3.8+
- Xcode Command Line Tools

#### 2. 依赖安装
```bash
# 克隆项目
git clone https://github.com/onlyhooops/plookingII.git
cd plookingII

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装运行时依赖（最小集合）
pip install -r requirements.txt

# 安装开发依赖（质量与审计工具）
pip install -r requirements-dev.txt
```

#### 3. 开发工具配置
```bash
# 配置代码风格检查
flake8 --install-hook git
git config flake8.strict true

# 配置预提交钩子
pre-commit install
```

### 代码规范

#### 1. Python 代码风格
遵循 PEP 8 规范：
```python
# 好的示例
class ImageProcessor:
    """图像处理器
    
    负责图像的加载、处理和缓存管理。
    """
    
    def __init__(self, cache_size: int = 100):
        self.cache_size = cache_size
        self._cache = {}
    
    def load_image(self, path: str) -> Optional[CGImage]:
        """加载图像
        
        Args:
            path: 图像文件路径
            
        Returns:
            CGImage对象，失败时返回None
        """
        if not os.path.exists(path):
            logger.warning(f"图像文件不存在: {path}")
            return None
        
        try:
            return self._load_with_quartz(path)
        except Exception as e:
            logger.error(f"加载图像失败 {path}: {e}")
            return None
```

#### 2. 注释和文档
```python
def complex_method(self, param1: str, param2: int = 0) -> dict:
    """复杂方法的文档示例
    
    这个方法演示了如何编写完整的文档字符串，包括参数说明、
    返回值说明和使用示例。
    
    Args:
        param1: 第一个参数的说明
        param2: 第二个参数的说明，默认值为0
        
    Returns:
        包含处理结果的字典，格式如下：
        {
            'status': 'success' | 'error',
            'data': 处理后的数据,
            'message': 状态消息
        }
        
    Raises:
        ValueError: 当参数无效时抛出
        IOError: 当文件操作失败时抛出
        
    Example:
        >>> processor = ImageProcessor()
        >>> result = processor.complex_method("test.jpg", 100)
        >>> print(result['status'])
        success
    """
    pass
```

#### 3. 错误处理
```python
def robust_method(self, path: str) -> Optional[Any]:
    """健壮的方法示例"""
    try:
        # 参数验证
        if not path or not isinstance(path, str):
            raise ValueError("路径参数无效")
        
        # 主要逻辑
        result = self._process_file(path)
        
        # 结果验证
        if not self._validate_result(result):
            raise RuntimeError("处理结果验证失败")
        
        return result
        
    except ValueError as e:
        logger.error(f"参数错误: {e}")
        return None
    except IOError as e:
        logger.error(f"文件操作错误: {e}")
        return None
    except Exception as e:
        logger.exception(f"未预期的错误: {e}")
        return None
    finally:
        # 清理资源
        self._cleanup()
```

### 测试指南

#### 1. 单元测试
```python
import unittest
from unittest.mock import Mock, patch
from plookingII.core.image_processing import HybridImageProcessor

class TestHybridImageProcessor(unittest.TestCase):
    """混合图像处理器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.processor = HybridImageProcessor()
    
    def tearDown(self):
        """测试后清理"""
        self.processor = None
    
    def test_load_image_success(self):
        """测试图像加载成功"""
        # 准备测试数据
        test_path = "tests/fixtures/test_image.jpg"
        
        # 执行测试
        result = self.processor.load_image_quartz_only(test_path)
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertIsInstance(result, CGImage)
    
    @patch('os.path.exists')
    def test_load_image_file_not_found(self, mock_exists):
        """测试文件不存在的情况"""
        # 模拟文件不存在
        mock_exists.return_value = False
        
        # 执行测试
        result = self.processor.load_image_quartz_only("nonexistent.jpg")
        
        # 验证结果
        self.assertIsNone(result)
    
    def test_rotate_image_90_degrees(self):
        """测试90度旋转"""
        test_path = "tests/fixtures/test_image.jpg"
        
        # 执行旋转
        success = self.processor.rotate_image(test_path, 90)
        
        # 验证结果
        self.assertTrue(success)
```

#### 2. 集成测试
```python
class TestImageManagerIntegration(unittest.TestCase):
    """图像管理器集成测试"""
    
    def setUp(self):
        """集成测试准备"""
        self.image_manager = ImageManager()
        self.test_images = [
            "tests/fixtures/small_image.jpg",
            "tests/fixtures/large_image.jpg",
            "tests/fixtures/rotated_image.jpg",
        ]
    
    def test_complete_workflow(self):
        """测试完整工作流程"""
        # 1. 加载图像
        for path in self.test_images:
            with self.subTest(path=path):
                result = self.image_manager.load_image_sync(path)
                self.assertIsNotNone(result)
        
        # 2. 检查缓存
        cache_stats = self.image_manager.get_cache_stats()
        self.assertGreater(cache_stats['main']['size'], 0)
        
        # 3. 清理缓存
        self.image_manager.clear_cache()
        cache_stats = self.image_manager.get_cache_stats()
        self.assertEqual(cache_stats['main']['size'], 0)
```

#### 3. 性能测试
```python
import time
import unittest
from plookingII.core.performance import ImagePerformanceMonitor

class TestPerformance(unittest.TestCase):
    """性能测试"""
    
    def test_image_loading_performance(self):
        """测试图像加载性能"""
        processor = HybridImageProcessor()
        test_image = "tests/fixtures/large_image.jpg"
        
        # 测量加载时间
        start_time = time.time()
        for _ in range(10):
            image = processor.load_image_quartz_only(test_image)
            self.assertIsNotNone(image)
        end_time = time.time()
        
        # 验证性能要求
        avg_time = (end_time - start_time) / 10
        self.assertLess(avg_time, 0.2)  # 平均加载时间 < 200ms
    
    def test_cache_performance(self):
        """测试缓存性能"""
        cache = AdvancedImageCache(max_size=50)
        
        # 填充缓存
        for i in range(100):
            cache.put(f"image_{i}", f"data_{i}")
        
        # 测试命中率
        hits = 0
        for i in range(50, 100):  # 测试最近的50个
            if cache.get(f"image_{i}") is not None:
                hits += 1
        
        hit_rate = hits / 50
        self.assertGreater(hit_rate, 0.8)  # 命中率 > 80%
```

### 调试技巧

#### 1. 日志配置
```python
import logging
from plookingII.config.constants import APP_NAME

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{APP_NAME}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(APP_NAME)

# 使用日志
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.exception("异常信息")  # 自动包含堆栈跟踪
```

#### 2. 性能分析
```python
import cProfile
import pstats
from plookingII.core.image_processing import HybridImageProcessor

def profile_image_loading():
    """性能分析示例"""
    processor = HybridImageProcessor()
    
    # 创建性能分析器
    profiler = cProfile.Profile()
    
    # 开始分析
    profiler.enable()
    
    # 执行要分析的代码
    for i in range(100):
        processor.load_image_quartz_only("test_image.jpg")
    
    # 停止分析
    profiler.disable()
    
    # 生成报告
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # 显示前20个最耗时的函数

if __name__ == '__main__':
    profile_image_loading()
```

#### 3. 内存分析
```python
import tracemalloc
import gc

def analyze_memory_usage():
    """内存使用分析"""
    # 开始内存跟踪
    tracemalloc.start()
    
    # 执行要分析的代码
    image_manager = ImageManager()
    for i in range(100):
        image_manager.load_image_sync(f"test_image_{i}.jpg")
    
    # 获取内存快照
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    print("内存使用前10位:")
    for stat in top_stats[:10]:
        print(stat)
    
    # 强制垃圾回收
    collected = gc.collect()
    print(f"垃圾回收清理了 {collected} 个对象")

if __name__ == '__main__':
    analyze_memory_usage()
```

---

## 结语

本技术指南提供了 PlookingII 项目的完整技术实现细节。项目采用现代化的架构设计和最佳实践，确保了代码的可维护性、可扩展性和高性能。

通过 Quartz-only 图像处理架构、自适应性能调优系统和智能缓存机制，PlookingII 为 macOS 用户提供了流畅、高效的图像浏览体验。

---

**版本**: v1.4.0  
**最后更新**: 2025-09-30  
**维护团队**: PlookingII Team

如有技术问题或建议，请通过项目 Issues 页面联系我们。
