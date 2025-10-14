"""
图像旋转处理模块

提供高质量的图像旋转功能，支持90度顺时针和逆时针旋转。
采用混合处理策略，结合PIL和Quartz的优势，确保性能和质量的平衡。

主要功能：
    - 90度顺时针和逆时针旋转
    - EXIF信息正确处理
    - 智能处理策略选择
    - 高质量图像保持
    - 内存优化处理

Author: PlookingII Team
"""

import os
import shutil
import subprocess
import tempfile
import time

from PIL import Image

from ..config.constants import APP_NAME
from ..imports import logging as _logging

logger = _logging.getLogger(APP_NAME)


class ImageRotationProcessor:
    """图像旋转处理器

    提供高质量的图像旋转功能，支持多种处理策略和EXIF信息处理。
    """

    def __init__(self):
        """初始化图像旋转处理器"""
        self.rotation_stats = {
            "clockwise_rotations": 0,
            "counterclockwise_rotations": 0,
            "pil_processed": 0,
            "quartz_processed": 0,
            "total_processing_time": 0.0,
            "failed_rotations": 0,
            "lossless_attempts": 0,
            "lossless_successes": 0,
            "pil_fallbacks": 0,
        }

        # 处理策略配置
        self.pil_threshold_mb = 10.0  # 小于10MB使用PIL
        self.quartz_threshold_mb = 10.0  # 大于等于10MB使用Quartz

    def rotate_image(self, image_path, direction="clockwise", callback=None):
        """旋转图像

        Args:
            image_path: 图像文件路径
            direction: 旋转方向 ("clockwise" 或 "counterclockwise")
            callback: 完成回调函数

        Returns:
            bool: 旋转是否成功
        """
        start_time = time.time()

        try:
            # 验证旋转方向
            if direction not in ["clockwise", "counterclockwise"]:
                logger.warning("无效的旋转方向: %s", direction)
                return False

            # 验证文件
            if not self._validate_image_file(image_path):
                return False

            # 获取文件大小
            file_size_mb = self._get_file_size_mb(image_path)

            # 选择处理策略
            strategy = self._select_rotation_strategy(file_size_mb)

            # 执行旋转
            success = self._execute_rotation(image_path, direction, strategy)

            # 更新统计
            self._update_rotation_stats(direction, strategy, time.time() - start_time, success)

            # 调用回调
            if callback and success:
                callback(image_path, direction)

            return success

        except Exception as e:
            logger.error("图像旋转失败 %s: %s", image_path, e)
            self.rotation_stats["failed_rotations"] += 1
            return False

    def _validate_image_file(self, image_path):
        """验证图像文件

        Args:
            image_path: 图像文件路径

        Returns:
            bool: 文件是否有效
        """
        if not os.path.exists(image_path):
            logger.warning("图像文件不存在: %s", image_path)
            return False

        if not os.path.isfile(image_path):
            logger.warning("路径不是文件: %s", image_path)
            return False

        # 检查文件扩展名（测试要求支持 TIFF）
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".tif", ".tiff"]:
            logger.warning("不支持的图像格式: %s", ext)
            return False

        return True

    def _get_file_size_mb(self, image_path):
        """获取文件大小（MB）

        Args:
            image_path: 图像文件路径

        Returns:
            float: 文件大小（MB）
        """
        try:
            size_bytes = os.path.getsize(image_path)
            return size_bytes / (1024 * 1024)
        except Exception as e:
            logger.warning("获取文件大小失败 %s: %s", image_path, e)
            return 0.0

    def _select_rotation_strategy(self, file_size_mb):
        """选择旋转处理策略

        Args:
            file_size_mb: 文件大小（MB）

        Returns:
            str: 处理策略 ("pil" 或 "quartz")
        """
        if file_size_mb < self.pil_threshold_mb:
            return "pil"
        return "quartz"

    def _execute_rotation(self, image_path, direction, strategy):
        """执行旋转操作

        Args:
            image_path: 图像文件路径
            direction: 旋转方向
            strategy: 处理策略

        Returns:
            bool: 操作是否成功
        """
        # JPEG：优先采用无损旋转
        try:
            ext = os.path.splitext(image_path)[1].lower()
        except Exception:
            ext = ""

        if ext in [".jpg", ".jpeg"]:
            # 记录尝试无损旋转
            try:
                self.rotation_stats["lossless_attempts"] += 1
            except Exception:
                pass
            lossless_ok = self._rotate_jpeg_lossless(image_path, direction)
            if lossless_ok:
                try:
                    self.rotation_stats["lossless_successes"] += 1
                except Exception:
                    pass
                # 无论无损旋转结果如何，统一将 EXIF Orientation 重置为 1
                try:
                    self._reset_exif_orientation_to_1(image_path)
                except Exception:
                    logger.debug("reset EXIF orientation failed after lossless rotation", exc_info=True)
                return True
            # 无损失败：回退到 PIL 优化路径
            try:
                self.rotation_stats["pil_fallbacks"] += 1
            except Exception:
                pass
            return self._rotate_with_pil_optimized(image_path, direction)

        # 非JPEG：按既有策略处理（PNG/TIFF 等）
        if strategy == "pil":
            return self._rotate_with_pil(image_path, direction)
        return self._rotate_with_quartz(image_path, direction)

    def _rotate_jpeg_lossless(self, image_path, direction):
        """使用 jpegtran 对 JPEG 进行无损旋转并原地替换。

        Args:
            image_path (str): JPEG 文件路径
            direction (str): "clockwise" 或 "counterclockwise"

        Returns:
            bool: 成功返回 True，失败返回 False
        """
        try:
            # 选择角度
            # clockwise(右转90) -> 90; counterclockwise(左转90) -> 270
            angle = 90 if direction == "clockwise" else 270

            # 查找 jpegtran 可执行文件
            jpegtran_path = None
            try:
                # 允许通过配置覆盖
                if "LOSSLESS_JPEG_CONFIG" in globals():
                    cfg = globals().get("LOSSLESS_JPEG_CONFIG")  # type: ignore
                    jpegtran_path = (cfg or {}).get("jpegtran_path")
            except Exception:
                jpegtran_path = None

            if not jpegtran_path:
                jpegtran_path = shutil.which("jpegtran")

            if not jpegtran_path:
                logger.error("未找到 jpegtran，可通过安装 'jpeg' 包或配置 LOSSLESS_JPEG_CONFIG.jpegtran_path")
                return False

            # 在同目录创建临时文件，避免跨设备移动问题
            dir_name = os.path.dirname(image_path) or "."
            with tempfile.NamedTemporaryFile(prefix=".rot_", suffix=".jpg", dir=dir_name, delete=False) as tmpf:
                tmp_path = tmpf.name

            # 基本参数：-copy all 保留元数据；-optimize 优化 Huffman 表；-rotate angle 无损旋转
            # -perfect 在某些非8x8对齐情况下会失败，因此先尝试 -perfect，失败则回退
            base_cmd = [
                jpegtran_path,
                "-copy",
                "all",
                "-optimize",
                "-rotate",
                str(angle),
                "-outfile",
                tmp_path,
                image_path,
            ]
            try:
                cmd = base_cmd[:]
                # 尝试 perfect
                cmd.insert(2, "-perfect")
                result = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.decode(errors="ignore") or "jpegtran perfect 失败")
            except Exception:
                # 回退去掉 -perfect
                result = subprocess.run(base_cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode != 0:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
                    logger.error(
                        "jpegtran 无损旋转失败: %s",
                        (result.stderr.decode(errors="ignore") or "unknown error"),
                    )
                    return False

            # 原子替换：先备份，再替换，尽量保证安全
            backup_path = None
            try:
                backup_path = image_path + ".bak"
                if os.path.exists(backup_path):
                    try:
                        os.remove(backup_path)
                    except Exception:
                        pass
                os.replace(image_path, backup_path)
                os.replace(tmp_path, image_path)
                # 替换成功后删除备份
                try:
                    os.remove(backup_path)
                except Exception:
                    pass
            except Exception as e:
                # 失败则回滚
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass
                try:
                    if backup_path and os.path.exists(backup_path):
                        os.replace(backup_path, image_path)
                except Exception:
                    pass
                logger.error("无损旋转替换文件失败 %s: %s", image_path, e)
                return False

            return True

        except Exception as e:
            logger.error("JPEG 无损旋转发生异常 %s: %s", image_path, e)
            return False

    def _rotate_with_pil(self, image_path, direction):
        """使用PIL进行图像旋转

        Args:
            image_path: 图像文件路径
            direction: 旋转方向

        Returns:
            bool: 操作是否成功
        """
        try:
            # 计算旋转角度
            angle = 90 if direction == "clockwise" else -90

            # 读取原始图像和EXIF信息
            with Image.open(image_path) as img:
                # 保存原始EXIF信息
                exif_data = img.info.get("exif")

                # 执行旋转
                rotated_img = img.rotate(angle, expand=True, fillcolor="white")

                # 处理EXIF方向信息（将 Orientation 重置为 1），并写回到 rotated_img.info['exif']
                rotated_img = self._update_exif_orientation(rotated_img, direction, exif_data)

                # 保存旋转后的图像（优先使用更新后的 exif）
                self._save_rotated_image(rotated_img, image_path, rotated_img.info.get("exif") or exif_data)

            return True

        except Exception as e:
            logger.error("PIL旋转失败 %s: %s", image_path, e)
            return False

    def _rotate_with_quartz(self, image_path, direction):
        """使用Quartz进行图像旋转

        Args:
            image_path: 图像文件路径
            direction: 旋转方向

        Returns:
            bool: 操作是否成功
        """
        try:
            # 使用PIL作为Quartz的备用方案
            # 对于大文件，仍然使用PIL但采用更优化的处理方式
            return self._rotate_with_pil_optimized(image_path, direction)

        except Exception as e:
            logger.error("Quartz旋转失败 %s: %s", image_path, e)
            return False

    def _rotate_with_pil_optimized(self, image_path, direction):
        """使用优化的PIL进行大文件旋转

        Args:
            image_path: 图像文件路径
            direction: 旋转方向

        Returns:
            bool: 操作是否成功
        """
        try:
            angle = 90 if direction == "clockwise" else -90

            with Image.open(image_path) as img:
                # 对于大文件，使用更高效的重采样算法
                exif_data = img.info.get("exif")

                # 使用LANCZOS重采样算法保证质量
                rotated_img = img.rotate(angle, expand=True, fillcolor="white", resample=Image.Resampling.LANCZOS)

                # 处理EXIF方向信息（将 Orientation 重置为 1），并写回到 rotated_img.info['exif']
                rotated_img = self._update_exif_orientation(rotated_img, direction, exif_data)

                # 优化保存参数（优先使用更新后的 exif）
                self._save_rotated_image_optimized(rotated_img, image_path, rotated_img.info.get("exif") or exif_data)

            return True

        except Exception as e:
            logger.error("优化PIL旋转失败 %s: %s", image_path, e)
            return False

    def _update_exif_orientation(self, img, direction, original_exif):
        """更新EXIF方向信息

        Args:
            img: PIL图像对象
            direction: 旋转方向
            original_exif: 原始EXIF数据

        Returns:
            PIL.Image: 更新后的图像对象
        """
        try:
            # 若无 EXIF 数据，直接返回
            if not original_exif:
                return img

            # 解析EXIF数据（Pillow 未提供 ORIENTATION 常量，需从 TAGS 查找，回退274）
            try:
                from PIL import ExifTags

                ORIENTATION = next((k for k, v in ExifTags.TAGS.items() if v == "Orientation"), 274)
            except Exception:
                ORIENTATION = 274

            # 获取当前方向值
            current_orientation = 1  # 默认值
            try:
                exif_dict = img._getexif()
                if exif_dict and ORIENTATION in exif_dict:
                    current_orientation = exif_dict[ORIENTATION]
            except Exception:
                pass

            # 计算新的方向值
            new_orientation = self._calculate_new_orientation(current_orientation, direction)

            # 更新EXIF数据
            if new_orientation != current_orientation:
                # 这里需要更复杂的EXIF处理逻辑，暂保留原始 EXIF
                pass

            # 将 Orientation 重置为 1，避免查看器再次应用方向造成“看起来未生效”
            try:
                exif = img.getexif()
                exif[ORIENTATION] = 1
                img.info["exif"] = exif.tobytes()
            except Exception:
                # 如果 Pillow 版本不支持写 EXIF，则保留原始 EXIF
                img.info["exif"] = original_exif

            return img

        except Exception as e:
            logger.warning("EXIF方向更新失败: %s", e)
            return img

    def _reset_exif_orientation_to_1(self, image_path: str) -> None:
        """将图像文件的 EXIF Orientation 重置为 1（就地写回）。

        说明：优先保证查看器不会再次应用旋转。若写回失败则静默忽略。
        """
        try:
            with Image.open(image_path) as img:
                from PIL import ExifTags

                try:
                    ORIENTATION = next((k for k, v in ExifTags.TAGS.items() if v == "Orientation"), 274)
                except Exception:
                    ORIENTATION = 274

                exif = img.getexif() or {}
                exif[ORIENTATION] = 1

                # 采用原文件格式保存到临时文件后原子替换
                ext = os.path.splitext(image_path)[1].lower()
                fmt = "JPEG" if ext in [".jpg", ".jpeg"] else ("PNG" if ext == ".png" else img.format or "JPEG")

                dir_name = os.path.dirname(image_path) or "."
                with tempfile.NamedTemporaryFile(
                    prefix=".exif_", suffix=ext or ".jpg", dir=dir_name, delete=False
                ) as tmpf:
                    tmp_path = tmpf.name

                save_kwargs = {"format": fmt}
                if fmt == "JPEG":
                    save_kwargs.update({"quality": 95, "optimize": True})
                save_kwargs["exif"] = exif.tobytes()

                img.save(tmp_path, **save_kwargs)
                try:
                    os.replace(tmp_path, image_path)
                except Exception:
                    # 回滚
                    try:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                    except Exception:
                        pass
        except Exception:
            # 静默失败，不影响主流程
            pass

    def _calculate_new_orientation(self, current_orientation, direction):
        """计算新的EXIF方向值

        Args:
            current_orientation: 当前方向值
            direction: 旋转方向

        Returns:
            int: 新的方向值
        """
        # 注：方向值映射表省略，直接进行数值变换

        # 简化的方向计算（实际应用中需要更复杂的逻辑）
        if direction == "clockwise":
            if current_orientation == 1:
                return 6  # 顺时针90度
            if current_orientation == 6:
                return 3  # 旋转180度
            if current_orientation == 3:
                return 8  # 逆时针90度
            if current_orientation == 8:
                return 1  # 正常
        elif current_orientation == 1:
            return 8  # 逆时针90度
        elif current_orientation == 8:
            return 3  # 旋转180度
        elif current_orientation == 3:
            return 6  # 顺时针90度
        elif current_orientation == 6:
            return 1  # 正常

        return current_orientation

    def _save_rotated_image(self, img, image_path, exif_data):
        """保存旋转后的图像

        Args:
            img: PIL图像对象
            image_path: 原始图像路径
            exif_data: EXIF数据
        """
        try:
            # 确定保存格式
            ext = os.path.splitext(image_path)[1].lower()
            if ext in [".jpg", ".jpeg"]:
                format_type = "JPEG"
                quality = 95
            elif ext in [".png"]:
                format_type = "PNG"
                quality = None
            else:
                format_type = "JPEG"
                quality = 95

            # 保存图像
            save_kwargs = {
                "format": format_type,
                "optimize": True,
            }

            if quality:
                save_kwargs["quality"] = quality

            if exif_data:
                save_kwargs["exif"] = exif_data

            img.save(image_path, **save_kwargs)

        except Exception as e:
            logger.error("保存旋转图像失败 %s: %s", image_path, e)
            raise

    def _save_rotated_image_optimized(self, img, image_path, exif_data):
        """优化保存旋转后的图像（用于大文件）

        Args:
            img: PIL图像对象
            image_path: 原始图像路径
            exif_data: EXIF数据
        """
        try:
            # 对于大文件，使用更保守的保存参数
            ext = os.path.splitext(image_path)[1].lower()
            if ext in [".jpg", ".jpeg"]:
                format_type = "JPEG"
                quality = 90  # 稍微降低质量以节省空间
            elif ext in [".png"]:
                format_type = "PNG"
                quality = None
            else:
                format_type = "JPEG"
                quality = 90

            save_kwargs = {
                "format": format_type,
                "optimize": True,
            }

            if quality:
                save_kwargs["quality"] = quality

            if exif_data:
                save_kwargs["exif"] = exif_data

            img.save(image_path, **save_kwargs)

        except Exception as e:
            logger.error("优化保存旋转图像失败 %s: %s", image_path, e)
            raise

    def _update_rotation_stats(self, direction, strategy, processing_time, success):
        """更新旋转统计信息

        Args:
            direction: 旋转方向
            strategy: 处理策略
            processing_time: 处理时间
            success: 是否成功
        """
        try:
            if success:
                if direction == "clockwise":
                    self.rotation_stats["clockwise_rotations"] += 1
                else:
                    self.rotation_stats["counterclockwise_rotations"] += 1

                if strategy == "pil":
                    self.rotation_stats["pil_processed"] += 1
                else:
                    self.rotation_stats["quartz_processed"] += 1

                self.rotation_stats["total_processing_time"] += processing_time
            else:
                self.rotation_stats["failed_rotations"] += 1

        except Exception as e:
            logger.warning("更新旋转统计失败: %s", e)

    def get_rotation_stats(self):
        """获取旋转统计信息

        Returns:
            dict: 旋转统计信息
        """
        return self.rotation_stats.copy()

    def reset_rotation_stats(self):
        """重置旋转统计信息"""
        self.rotation_stats = {
            "clockwise_rotations": 0,
            "counterclockwise_rotations": 0,
            "pil_processed": 0,
            "quartz_processed": 0,
            "total_processing_time": 0.0,
            "failed_rotations": 0,
        }
