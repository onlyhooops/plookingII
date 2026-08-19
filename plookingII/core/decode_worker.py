"""
解码子进程 Worker（内存根治方案）

PyObjC 桥接下，任何在主进程触发的 ObjC 图像解码，其解码缓冲都挂在主线程
全局 NSAutoreleasePool 上且从不被 drain（已验证所有官方 API 均不可行或
崩溃）。长会话下解码内存线性累积（实测 6 分钟 80MB → 8.6GB）。

根治方案：把图像解码放到**独立子进程**——
- 子进程持有全部解码内存（6000×4000 全分辨率实测 ~242MB）
- 子进程解码后写入显示级临时文件，主进程只接收文件路径
- 子进程完成任务后退出 → 解码内存随进程销毁**彻底释放**
- 周期性重启子进程 → 无限解码循环内存平台型（实测 30 次父进程净增 +0.1MB）

本模块 = 子进程入口（worker 函数），通过 multiprocessing spawn 启动。
主进程侧管理见 decode_pool.py。
"""

import logging
import os

logger = logging.getLogger("plookingII.decode_worker")


def _decode_to_file(path: str, target_size: tuple[int, int] | None, out_dir: str) -> str | None:
    """子进程内解码图片并写入显示级文件，返回文件路径

    解码使用 Quartz（ImageIO）：
    - target_size 指定时：生成降采样缩略图（显示级，~10MB）
    - target_size 为 None 时：生成全分辨率（子进程持有内存，写完即弃）

    Args:
        path: 源图片路径
        target_size: 目标尺寸 (w, h)，None 表示全分辨率
        out_dir: 输出临时目录

    Returns:
        解码后文件的路径（失败返回 None）
    """
    try:
        from Foundation import NSURL
        from Quartz import (
            CGImageDestinationAddImage,
            CGImageDestinationCreateWithURL,
            CGImageDestinationFinalize,
            CGImageSourceCreateImageAtIndex,
            CGImageSourceCreateThumbnailAtIndex,
            CGImageSourceCreateWithURL,
            kCGImageSourceCreateThumbnailFromImageAlways,
            kCGImageSourceShouldCacheImmediately,
            kCGImageSourceThumbnailMaxPixelSize,
        )

        # kUTTypeJPEG 在 CoreServices（UniformTypeIdentifiers），不在 Quartz
        try:
            from CoreServices import kUTTypeJPEG
        except ImportError:
            from UniformTypeIdentifiers import UTTypeJPEG  # type: ignore[no-redef]

            kUTTypeJPEG = UTTypeJPEG.identifier

        url = NSURL.fileURLWithPath_(path)
        source = CGImageSourceCreateWithURL(url, None)
        if source is None:
            logger.warning("子进程无法创建 CGImageSource: %s", path)
            return None

        if target_size:
            max_px = max(target_size)
            cg = CGImageSourceCreateThumbnailAtIndex(
                source,
                0,
                {
                    kCGImageSourceCreateThumbnailFromImageAlways: True,
                    kCGImageSourceThumbnailMaxPixelSize: max_px,
                    kCGImageSourceShouldCacheImmediately: True,
                },
            )
        else:
            # 全分辨率：懒代理 + 强制解码（子进程持有内存）
            cg = CGImageSourceCreateImageAtIndex(source, 0, {kCGImageSourceShouldCacheImmediately: False})

        if cg is None:
            logger.warning("子进程解码失败: %s", path)
            return None

        # 写入显示级 JPEG 临时文件
        os.makedirs(out_dir, exist_ok=True)
        import uuid

        out_path = os.path.join(out_dir, f"dec_{uuid.uuid4().hex[:12]}.jpg")
        out_url = NSURL.fileURLWithPath_(out_path)
        dest = CGImageDestinationCreateWithURL(out_url, kUTTypeJPEG, 1, None)
        if dest is None:
            logger.warning("子进程无法创建输出目标: %s", out_path)
            return None
        CGImageDestinationAddImage(dest, cg, None)
        if not CGImageDestinationFinalize(dest):
            logger.warning("子进程写文件失败: %s", out_path)
            return None
        return out_path
    except Exception:
        logger.exception("子进程解码异常: %s", path)
        return None


def worker_entry(pipe_conn, work_dir: str) -> None:
    """子进程主入口：从管道接收 (path, target_size)，回传结果路径

    Args:
        pipe_conn: multiprocessing.Pipe 连接（子进程端）
        work_dir: 临时输出目录
    """
    try:
        while True:
            # 阻塞接收任务
            if not pipe_conn.poll(30.0):
                continue
            task = pipe_conn.recv()
            if task is None:  # 终止信号
                break
            path, target_size = task
            result = _decode_to_file(path, target_size, work_dir)
            pipe_conn.send(result)
    except (EOFError, OSError):
        pass
    except Exception:
        logger.exception("子进程 worker 异常退出")
    finally:
        try:
            pipe_conn.close()
        except Exception:
            pass


def main() -> None:  # pragma: no cover - 仅作为 spawn 入口文档
    """spawn 方式启动时的入口（multiprocessing 要求 target 在模块顶层可导入）"""


if __name__ == "__main__":  # pragma: no cover
    main()
