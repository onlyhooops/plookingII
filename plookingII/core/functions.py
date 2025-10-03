import gc as _gc

from AppKit import (
    NSMenu,
)

from ..config.constants import SUPPORTED_IMAGE_EXTS
from ..imports import NSURL, QUARTZ_AVAILABLE, os
from ..ui.menu_builder import MenuBuilder


def simple_thumbnail_cache(path_and_size):
    """创建并缓存图像缩略图

    将指定路径的图像文件转换为指定尺寸的缩略图，并返回PNG格式的字节数据。
    支持JPG、JPEG和PNG格式的图像文件。

    Args:
        path_and_size (tuple): 包含两个元素的元组
            - path (str): 图像文件路径
            - size (tuple): 目标缩略图尺寸 (width, height)

    Returns:
        bytes or None: PNG格式的缩略图字节数据，失败时返回None

    Note:
        - 仅支持JPG、JPEG、PNG格式的图像文件
        - 使用PIL库进行图像处理，如果PIL不可用则返回None
        - 缩略图保持原始图像的宽高比
        - 返回的PNG数据可以直接用于显示或保存

    Example:
        >>> thumbnail_data = simple_thumbnail_cache(("image.jpg", (100, 100)))
        >>> if thumbnail_data:
        ...     with open("thumbnail.png", "wb") as f:
        ...         f.write(thumbnail_data)
    """
    path, size = path_and_size

    # 检查文件格式是否支持
    if not path.lower().endswith(tuple(SUPPORTED_IMAGE_EXTS)):
        return None

    try:
        from io import BytesIO

        from PIL import Image

        # 打开图像文件并创建缩略图
        with Image.open(path) as im:
            # 创建指定尺寸的缩略图，保持宽高比
            im.thumbnail(size)

            # 将缩略图保存为PNG格式的字节数据
            buf = BytesIO()
            im.save(buf, format="PNG")
            data = buf.getvalue()
            buf.close()
            return data
    except Exception:
        # 图像处理失败时返回None
        return None


def force_gc():
    """强制执行垃圾回收

    连续调用两次垃圾回收器，确保内存中的无用对象被及时清理。
    主要用于内存敏感的场景，如图像处理后的内存清理。

    Note:
        - 调用两次是为了确保循环引用的对象被完全清理
        - 这是一个相对昂贵的操作，不应频繁调用
        - 通常在内存压力较大或处理大量图像后调用

    Example:
        >>> # 处理大量图像后强制清理内存
        >>> process_large_images()
        >>> force_gc()
    """
    _gc.collect()  # 第一次垃圾回收
    _gc.collect()  # 第二次垃圾回收，确保循环引用被清理


def build_menu(app, win):
    """构建应用程序的主菜单栏 - 使用MenuBuilder重构版本

    ✨ 重构说明: 原150行复杂函数已拆分为专门的MenuBuilder类
    这个函数现在只负责协调调用，具体逻辑在menu_builder模块中。

    Args:
        app: NSApplication实例，应用程序对象
        win: 主窗口实例，用于设置菜单项的目标对象

    Note:
        - 使用MenuBuilder类构建完整的macOS原生菜单系统
        - 保持与原函数完全相同的功能和接口
        - 自动设置所有必要的菜单项引用和快捷键
    """
    try:
        # 使用MenuBuilder构建菜单
        menu_builder = MenuBuilder(app, win)
        main_menu = menu_builder.build_menu()

        # 设置为应用程序的主菜单
        app.setMainMenu_(main_menu)

    except Exception as e:
        # 如果重构版本失败，记录错误但不中断程序
        import logging
        logger = logging.getLogger("PlookingII")
        logger.error(f"菜单构建失败: {e}")

        # 创建一个最基本的菜单作为回退
        fallback_menu = NSMenu.alloc().init()
        app.setMainMenu_(fallback_menu)


def _env_int(name, default):
    """从环境变量中获取正整数值。

    安全地从环境变量中读取整数配置，提供默认值和错误处理。

    Args:
        name (str): 环境变量名称
        default (int): 默认值，当环境变量不存在或无效时使用

    Returns:
        int: 环境变量的正整数值，如果无效则返回默认值

    Note:
        - 只接受正整数值（>0），零和负数被视为无效
        - 自动处理字符串前后空格
        - 异常安全：任何解析错误都返回默认值
        - 用于读取性能相关的配置参数
    """
    try:
        v = int(os.environ.get(name, "").strip())
        return v if v > 0 else default
    except Exception:
        return default


def get_image_dimensions_safe(path: str):
    """安全获取图像尺寸（宽, 高），尽量避免解码与大图告警。

    优先走 macOS Quartz ImageIO 的元数据读取；失败时回退到 Pillow，
    并在 Pillow 路径下静默忽略 DecompressionBombWarning。

    Returns:
        tuple[int, int] or None
    """
    # 优先：Quartz（无需完整解码，性能/稳态更佳）
    try:
        if QUARTZ_AVAILABLE and NSURL is not None:
            try:
                from Quartz.ImageIO import (
                    CGImageSourceCopyPropertiesAtIndex,
                    CGImageSourceCreateWithURL,
                    kCGImagePropertyPixelHeight,
                    kCGImagePropertyPixelWidth,
                )
            except Exception:
                from Quartz import (  # type: ignore
                    CGImageSourceCopyPropertiesAtIndex,  # type: ignore
                    CGImageSourceCreateWithURL,  # type: ignore
                    kCGImagePropertyPixelHeight,
                    kCGImagePropertyPixelWidth,
                )

            url = NSURL.fileURLWithPath_(path)
            source = CGImageSourceCreateWithURL(url, None)
            if source is not None:
                props = CGImageSourceCopyPropertiesAtIndex(source, 0, None)
                if props is not None:
                    try:
                        w = int(props.get(kCGImagePropertyPixelWidth, 0))
                        h = int(props.get(kCGImagePropertyPixelHeight, 0))
                        if w > 0 and h > 0:
                            return (w, h)
                    except Exception:
                        pass
    except Exception:
        pass

    # 回退：Pillow（忽略超大图告警，仅读取尺寸）
    try:
        import warnings

        from PIL import Image
        try:
            from PIL.Image import DecompressionBombWarning  # type: ignore
        except Exception:
            DecompressionBombWarning = Warning  # 宽松兜底

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DecompressionBombWarning)
            with Image.open(path) as im:
                size = getattr(im, "size", None)
                if size and isinstance(size, tuple) and len(size) == 2:
                    w, h = size
                    if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
                        return (w, h)
    except Exception:
        return None

    return None
