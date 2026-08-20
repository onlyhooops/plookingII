"""
加载辅助函数

提供各种图片加载方法的底层实现。

Author: PlookingII Team
Date: 2025-10-06
"""

import fcntl
import logging
import mmap
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)

# 加载器实例缓存（get_loader 全局复用，避免热路径重复构造策略对象）
_loader_cache: dict[str, Any] = {}
_loader_cache_lock = threading.Lock()

# macOS F_NOCACHE 常量：标记文件读操作不污染系统页缓存
# 适用于大尺寸图片的顺序读取（once-and-done 访问模式）
F_NOCACHE = 48

# 文件大小缓存（避免重复 os.path.getsize）
_file_size_cache: dict[str, tuple[float, float]] = {}  # path -> (size_mb, timestamp)
_FILE_SIZE_CACHE_TTL = 5.0  # 5秒TTL
_file_size_cache_hits = 0  # 累积命中/未命中计数，用于定期清理
_FILE_SIZE_CACHE_CLEANUP_INTERVAL = 200  # 每 200 次缓存访问执行一次过期淘汰


def get_file_size_mb(file_path: str, use_cache: bool = True) -> float:
    """获取文件大小(MB)

    Args:
        file_path: 文件路径
        use_cache: 是否使用缓存

    Returns:
        文件大小（MB）
    """
    try:
        # 字典只做原地增删不需要 global；计数器赋值需要，加 noqa 说明合理用途
        global _file_size_cache_hits  # noqa: PLW0603  # 模块级计数缓存
        import time

        now = time.time()

        # 定期清理过期缓存条目（每 200 次访问执行一次）
        _file_size_cache_hits += 1
        if _file_size_cache_hits >= _FILE_SIZE_CACHE_CLEANUP_INTERVAL:
            _file_size_cache_hits = 0
            expired = [p for p, (_, ts) in _file_size_cache.items() if (now - ts) >= _FILE_SIZE_CACHE_TTL]
            for p in expired:
                _file_size_cache.pop(p, None)

        # 检查缓存
        if use_cache and file_path in _file_size_cache:
            size_mb, timestamp = _file_size_cache[file_path]
            if (now - timestamp) < _FILE_SIZE_CACHE_TTL:
                return size_mb

        # 获取文件大小
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)

        # 更新缓存
        if use_cache:
            _file_size_cache[file_path] = (size_mb, now)

        return size_mb
    except Exception as e:
        logger.warning("获取文件大小失败 %s: %s", file_path, e)
        return 0.0


def clear_file_size_cache() -> None:
    """清除文件大小缓存"""
    _file_size_cache.clear()


def check_quartz_availability() -> bool:
    """检查Quartz是否可用"""
    try:
        from Quartz import CGImageSourceCreateWithURL  # noqa: F401

        return True
    except ImportError:
        return False


def load_with_nsimage(file_path: str) -> Any | None:
    """使用NSImage加载（快速，适合小文件）

    Args:
        file_path: 文件路径

    Returns:
        NSImage对象，失败返回None
    """
    try:
        from AppKit import NSImage

        return NSImage.alloc().initWithContentsOfFile_(file_path)
    except Exception as e:
        logger.exception("NSImage加载失败 %s: %s", file_path, e)
        return None


def is_png_file(file_path: str) -> bool:
    """判断文件是否为PNG格式

    Args:
        file_path: 文件路径

    Returns:
        True if PNG file
    """
    return os.path.splitext(file_path)[1].lower() == ".png"


def is_jpeg_file(file_path: str) -> bool:
    """判断文件是否为JPEG格式

    Args:
        file_path: 文件路径

    Returns:
        True if JPEG file
    """
    ext = os.path.splitext(file_path)[1].lower()
    return ext in (".jpg", ".jpeg")


def load_with_quartz(file_path: str, target_size: tuple[int, int] | None = None, thumbnail: bool = False) -> Any | None:
    """使用Quartz加载（预览风格懒解码）

    两种模式：
    - thumbnail=True:  立即解码缩略图 (CGImageSourceCreateThumbnailAtIndex)
    - thumbnail=False: 创建懒解码CGImage代理 (CGImageSourceCreateImageAtIndex + ShouldCacheImmediately=False)
      代理CGImage不解码像素，仅在GPU需要时才解码屏幕可见区域。
      注意：项目已放弃运行期 EXIF 方向修正（图片集在筛选前由外部工作流统一纠正朝向），
      解码与渲染均不做方向变换，保持零拷贝直绘。

    Args:
        file_path: 文件路径
        target_size: 目标尺寸 (width, height)，用于缩略图模式
        thumbnail: 是否创建缩略图（立即解码）

    Returns:
        CGImage对象（代理或缩略图），失败返回None
    """
    try:
        from Foundation import NSURL
        from Quartz import (
            CGImageSourceCreateImageAtIndex,
            CGImageSourceCreateThumbnailAtIndex,
            CGImageSourceCreateWithURL,
            kCGImageSourceCreateThumbnailFromImageAlways,
            kCGImageSourceCreateThumbnailFromImageIfAbsent,
            kCGImageSourceShouldAllowFloat,
            kCGImageSourceShouldCache,
            kCGImageSourceShouldCacheImmediately,
            kCGImageSourceSubsampleFactor,
            kCGImageSourceThumbnailMaxPixelSize,
        )

        url = NSURL.fileURLWithPath_(file_path)
        source = CGImageSourceCreateWithURL(url, None)

        if not source:
            logger.warning("无法创建CGImageSource: %s", file_path)
            return None

        if thumbnail and target_size:
            # 缩略图模式：根据格式选择最优参数
            png = is_png_file(file_path)
            max_size = max(target_size)

            if png:
                # PNG 缩略图优化：
                # - PNG 没有内嵌缩略图（无 MPF 段），使用 FromImageAlways 避免无效查找
                # - PNG 为 DEFLATE 解压，比 JPEG 的 DCT 解压更重，加大 SubsampleFactor 降采样
                # - 关闭 ShouldCacheImmediately 减少即时内存分配
                options = {
                    kCGImageSourceThumbnailMaxPixelSize: max_size,
                    kCGImageSourceSubsampleFactor: 4,
                    kCGImageSourceShouldCache: True,
                    kCGImageSourceShouldCacheImmediately: False,
                    kCGImageSourceCreateThumbnailFromImageAlways: True,
                    kCGImageSourceShouldAllowFloat: False,
                }
            else:
                # JPEG/其他格式缩略图：
                # - FromImageIfAbsent: 优先使用文件内嵌缩略图（JPEG/HEIC），减少全图解码
                # - SubsampleFactor:      解码阶段跳过像素行/列，像素量降至 1/factor²
                # - MaxPixelSize:         配合SubsampleFactor，ImageIO内部自动选择最优组合
                # - ShouldCacheImmediately: v2.8.1 改为 False —— 实机验证 True 时每次
                #   缩略图解码向永不 drain 的 autorelease pool 泄漏整张缩略图缓冲
                #   （800×600 ≈ 1.63MB/张）；False 为懒解码，缓冲随 CGImage 包装器
                #   释放（实测 +0.01MB/张），解码时机延后到首次绘制，像素结果不变
                options = {
                    kCGImageSourceThumbnailMaxPixelSize: max_size,
                    kCGImageSourceSubsampleFactor: 2,
                    kCGImageSourceShouldCache: True,
                    kCGImageSourceShouldCacheImmediately: False,
                    kCGImageSourceCreateThumbnailFromImageIfAbsent: True,
                    kCGImageSourceShouldAllowFloat: True,
                }
            return CGImageSourceCreateThumbnailAtIndex(source, 0, options)

        # 全尺寸模式：创建懒解码CGImage代理（Preview.app风格）
        # - kCGImageSourceShouldCacheImmediately=False 不解码像素，CGImage仅存储元数据
        # - 实际解码延迟到 Core Animation / GPU 需要时才进行
        # - 超大图片（10000px+）可在数毫秒内"加载"完成
        # - 不做 EXIF 方向变换（外部工作流已在筛选前纠正朝向）
        options = {
            kCGImageSourceShouldCache: False,
            kCGImageSourceShouldCacheImmediately: False,
            kCGImageSourceShouldAllowFloat: True,
        }
        return CGImageSourceCreateImageAtIndex(source, 0, options)

    except Exception:
        logger.exception("Quartz加载失败 %s", file_path)
        return None


def load_with_memory_map(file_path: str, target_size: tuple[int, int] | None = None) -> Any | None:
    """使用内存映射加载（大文件优化，F_NOCACHE 不污染页缓存）

    Args:
        file_path: 文件路径
        target_size: 目标尺寸（当前未使用）

    Returns:
        NSImage对象，失败返回None
    """
    try:
        from AppKit import NSData, NSImage

        # 使用 F_NOCACHE 打开，避免大图数据污染内核页缓存
        f = open_no_cache(file_path)
        if f is None:
            return None
        with f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            # 从内存映射创建NSData
            data = NSData.dataWithBytes_length_(mm, len(mm))
            return NSImage.alloc().initWithData_(data)
    except Exception:
        logger.exception("内存映射加载失败 %s", file_path)
        return None


def cgimage_to_nsimage(cgimage: Any) -> Any | None:
    """将CGImage转换为NSImage

    Args:
        cgimage: CGImage对象

    Returns:
        NSImage对象，失败返回None
    """
    try:
        from AppKit import NSBitmapImageRep, NSImage

        if cgimage is None:
            return None

        # 获取CGImage尺寸
        from Quartz import CGImageGetHeight, CGImageGetWidth

        width = CGImageGetWidth(cgimage)
        height = CGImageGetHeight(cgimage)

        # 创建NSImage
        bitmap = NSBitmapImageRep.alloc().initWithCGImage_(cgimage)
        image = NSImage.alloc().initWithSize_((width, height))
        image.addRepresentation_(bitmap)

        return image
    except Exception as e:
        logger.exception("CGImage转NSImage失败: %s", e)
        return None


def extract_embedded_preview(file_path: str) -> Any | None:
    """从 JPEG/HEIC 文件中提取内嵌预览图（不解码全分辨率图像）

    JPEG 文件的 MPF（Multi-Picture Format）段中通常存储了
    "Large Thumbnail (full HD equivalent)" 预览图（~90KB-900KB），
    可以直接提取并在毫秒级显示，无需解码 45MP 全分辨率图像。

    Args:
        file_path: 文件路径

    Returns:
        CGImageRef（预览图），无内嵌预览图时返回 None
    """
    try:
        from Foundation import NSURL, NSData
        from Quartz import (
            CGImageSourceCopyPropertiesAtIndex,
            CGImageSourceCreateImageAtIndex,
            CGImageSourceCreateWithData,
            CGImageSourceCreateWithURL,
            kCGImagePropertyMPFDictionary,
            kCGImageSourceShouldCacheImmediately,
        )

        url = NSURL.fileURLWithPath_(file_path)
        source = CGImageSourceCreateWithURL(url, None)
        if not source:
            return None

        # 检查是否存在 MPF 段（Multi-Picture Format，JPEG 多图像扩展）
        props = CGImageSourceCopyPropertiesAtIndex(source, 0, None)
        if not props:
            return None

        mpf_dict = props.get(kCGImagePropertyMPFDictionary)
        if not mpf_dict:
            return None

        # 获取 MPF 中图像的数量
        num_images = mpf_dict.get("NumberOfImages", 0)
        if num_images < 2:
            return None

        # MPF 图像布局（Index 从 0 开始）：
        #   Index 0 = 主图像（全分辨率）
        #   Index 1 = Large Thumbnail (full HD equivalent) ← 目标
        #   Index 2+ = 其他辅助图
        # 提取 Index 1 的起始偏移和大小
        # CGImageSource 的 property 字典中 MPF 条目为标量（非数组），
        # 需要直接读取文件字节范围来提取子图像数据
        mp_entry_count = int(mpf_dict.get("NumberOfImages", 0))
        if mp_entry_count < 2:
            return None

        # 读取 MPF 条目：Image 0 (主图), Image 1 (Full HD 预览)
        # kCGImagePropertyMPFImageLength / kCGImagePropertyMPFImageOffset
        # 这些 key 是 CGImageProperties 中的数字索引，用字符串形式访问
        mp_image_length = mpf_dict.get("MP Image Length", None)
        mp_image_start = mpf_dict.get("MP Image Start", None)

        # 如果顶层没有，尝试 number-based keys (deprecated but still present in some files)
        if mp_image_length is None or mp_image_start is None:
            # 尝试读取 Index 1 的条目
            # MPF 条目格式：16 bytes per entry
            #   Entry 0 offset: mpf_offset + 16
            #   Entry 1 offset: mpf_offset + 32
            # 但这需要解析原始 MPF 段结构，简化处理：
            # 许多 JPEG 的 MPF 段第一组条目在字典中暴露为 Index 0/1
            for idx in range(mp_entry_count):
                len_key = f"MPImageLength_{idx}"
                start_key = f"MPImageStart_{idx}"
                if len_key in mpf_dict and start_key in mpf_dict:
                    mp_image_length = mpf_dict[len_key]
                    mp_image_start = mpf_dict[start_key]

        # 如果仍然没有，尝试不带索引后缀的字段
        mp_image_length = mp_image_length or mpf_dict.get("MPImageLength", None)
        mp_image_start = mp_image_start or mpf_dict.get("MPImageStart", None)

        if mp_image_length is None or mp_image_start is None:
            return None

        mp_image_length = int(mp_image_length)
        mp_image_start = int(mp_image_start)

        if mp_image_length <= 0 or mp_image_start <= 0:
            return None

        # 从文件中读取预览图像数据
        with open_no_cache(file_path) as f:
            if f is None:
                return None
            f.seek(mp_image_start)
            preview_data = f.read(mp_image_length)

        if not preview_data:
            return None

        # 从二进制数据创建 CGImageSource 并解码预览图
        ns_data = NSData.dataWithBytes_length_(preview_data, len(preview_data))
        preview_source = CGImageSourceCreateWithData(ns_data, None)
        if not preview_source:
            return None

        options = {
            kCGImageSourceShouldCacheImmediately: False,
        }
        return CGImageSourceCreateImageAtIndex(preview_source, 0, options)

    except Exception as e:
        logger.debug("提取内嵌预览图失败 %s: %s", file_path, e)
        return None


def open_no_cache(file_path: str):
    """使用 F_NOCACHE 标记打开大文件（不污染系统页缓存）

    适合 10MB+ 图片的顺序一次读取模式。
    F_NOCACHE 告诉内核：该文件的页面在使用后应立即从缓存中驱逐，
    避免大图数据挤出缩略图、目录元数据等热数据。

    非 macOS 平台或 fcntl 失败时回退到普通 open()。

    Args:
        file_path: 文件路径

    Returns:
        file object 或 None
    """
    try:
        fd = os.open(file_path, os.O_RDONLY)
        try:
            fcntl.fcntl(fd, F_NOCACHE, 1)
        except (OSError, ValueError):
            # F_NOCACHE 在某些文件系统（如网络挂载）可能不支持，
            # 静默回退，不影响正常读取
            pass
        return os.fdopen(fd, "rb")
    except OSError:
        logger.exception("F_NOCACHE 打开文件失败 %s", file_path)
        return None


def png_has_alpha(file_path: str) -> bool | None:
    """检测PNG文件是否包含Alpha通道（不解码像素，仅读元数据）

    Args:
        file_path: PNG文件路径

    Returns:
        True/False，失败返回None
    """
    try:
        from Foundation import NSURL
        from Quartz import (
            CGImageSourceCopyPropertiesAtIndex,
            CGImageSourceCreateWithURL,
        )

        url = NSURL.fileURLWithPath_(file_path)
        source = CGImageSourceCreateWithURL(url, None)
        if not source:
            return None

        props = CGImageSourceCopyPropertiesAtIndex(source, 0, None)
        if not props:
            return None

        # kCGImagePropertyPNGHasAlphaChannel 在 CGImageProperties 中
        # 尝试多种方式获取 alpha 信息
        has_alpha = props.get("HasAlpha", None)
        if has_alpha is not None:
            return bool(has_alpha)

        # 回退：通过色彩模型判断（RGBA 像素格式 = 有 alpha）
        color_model = props.get("ColorModel", "")
        depth = props.get("Depth", 0)
        return color_model == "RGB" and int(depth) == 32
    except Exception:
        logger.debug("检测PNG Alpha通道失败 %s", file_path)
        return None


def get_image_dimensions(file_path: str) -> tuple[int, int] | None:
    """获取图片尺寸（不加载完整图片）

    Args:
        file_path: 文件路径

    Returns:
        (width, height) 或 None
    """
    try:
        from Foundation import NSURL
        from Quartz import (
            CGImageSourceCopyPropertiesAtIndex,
            CGImageSourceCreateWithURL,
            kCGImagePropertyPixelHeight,
            kCGImagePropertyPixelWidth,
        )

        url = NSURL.fileURLWithPath_(file_path)
        source = CGImageSourceCreateWithURL(url, None)

        if not source:
            return None

        props = CGImageSourceCopyPropertiesAtIndex(source, 0, None)
        if not props:
            return None

        width = props.get(kCGImagePropertyPixelWidth, 0)
        height = props.get(kCGImagePropertyPixelHeight, 0)

        return (int(width), int(height))
    except Exception:
        logger.exception("获取图片尺寸失败 %s", file_path)
        return None


def get_loader(strategy: str = "auto"):
    """获取加载器实例（工厂函数，全局缓存实例避免热路径重复构造）

    加载策略除统计外无状态，同一策略只需一个实例；
    缓存后每次加载不再重复构造策略对象与 Quartz 可用性检查。

    Args:
        strategy: 策略名称 ('auto', 'optimized', 'preview')

    Returns:
        对应的加载器实例
    """
    from .strategies import AutoStrategy, OptimizedStrategy, PreviewStrategy

    if strategy not in ("auto", "optimized", "preview"):
        logger.warning("未知策略 %s，使用 auto", strategy)
        strategy = "auto"

    with _loader_cache_lock:
        loader = _loader_cache.get(strategy)
        if loader is None:
            if strategy == "auto":
                loader = AutoStrategy()
            elif strategy == "optimized":
                loader = OptimizedStrategy()
            else:
                loader = PreviewStrategy()
            _loader_cache[strategy] = loader
        return loader


def clear_loader_cache() -> None:
    """清空加载器实例缓存（主要用于测试隔离）"""
    with _loader_cache_lock:
        _loader_cache.clear()


def create_loader(config=None, **kwargs):
    """创建自定义加载器

    Args:
        config: LoadingConfig对象
        **kwargs: 传递给策略的额外参数

    Returns:
        OptimizedStrategy实例
    """
    from .config import LoadingConfig
    from .strategies import OptimizedStrategy

    if config is None:
        config = LoadingConfig.from_global_config()

    return OptimizedStrategy(config=config, **kwargs)
