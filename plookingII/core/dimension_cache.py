"""
目录级图片尺寸元数据持久化缓存（P3-4）

以目录 mtime 为失效键，将"目录内文件名 → 像素尺寸"映射持久化到应用支持
目录（`~/Library/Application Support/PlookingII/dimension_cache/`），
二次打开同一目录时直接命中，避免跨启动重复读取图片元数据。

设计原则：
- 只读缓存 + 严格校验：缓存文件损坏/格式非法时忽略并重建，不影响主流程
- 以目录 mtime 为失效依据：目录内文件增删会更新 mtime，mtime 变化即失效
- 目录 mtime 粒度保护：同一次扫描期间 mtime 可能未变，用目录 hash 命名文件
- 磁盘写入节流：仅在实际扫描到尺寸后异步/延迟写盘，避免热路径 I/O
- 与内存缓存互补：内存 LRU 管会话内热路径，本缓存管跨启动冷启动

文件结构：
    <app_support>/dimension_cache/<dir_hash>.json
    JSON: {"mtime": 1234567890.0, "dims": {"a.jpg": [1920, 1080], ...}}

Author: PlookingII Team
"""

import hashlib
import json
import logging
import os
import threading
from pathlib import Path

from ..config.constants import APP_NAME

logger = logging.getLogger(APP_NAME)


class DirectoryDimensionCache:
    """目录级图片尺寸持久化缓存"""

    def __init__(self, cache_dir: str | None = None, max_dirs: int = 256):
        """
        Args:
            cache_dir: 缓存根目录；None 使用默认应用支持目录
            max_dirs: 缓存目录条目上限（LRU 清理）
        """
        if cache_dir is None:
            cache_dir = os.path.join(
                os.path.expanduser("~"), "Library", "Application Support", APP_NAME, "dimension_cache"
            )
        self._cache_dir = Path(cache_dir)
        self._max_dirs = max(1, max_dirs)
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    @staticmethod
    def _dir_hash(dir_path: str) -> str:
        """目录路径 → 缓存文件名 hash（MD5 仅用于文件名，非安全场景）"""
        normalized = os.path.normpath(dir_path)
        return hashlib.md5(normalized.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]

    def _cache_file(self, dir_path: str) -> Path:
        return self._cache_dir / f"{self._dir_hash(dir_path)}.json"

    def _ensure_dir(self) -> bool:
        """确保缓存目录存在且可写"""
        try:
            os.makedirs(self._cache_dir, exist_ok=True)
            return True
        except OSError:
            return False

    # ------------------------------------------------------------------
    # 读写接口
    # ------------------------------------------------------------------
    def load(self, dir_path: str, dir_mtime: float) -> dict[str, tuple[int, int]] | None:
        """加载目录尺寸缓存；mtime 不匹配或缓存无效时返回 None

        Args:
            dir_path: 目录路径
            dir_mtime: 目录当前 mtime（失效依据）

        Returns:
            文件名 → (宽, 高) 映射；无效/过期返回 None
        """
        try:
            cache_file = self._cache_file(dir_path)
            if not cache_file.exists():
                return None
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return None
            if abs(float(data.get("mtime", -1.0)) - dir_mtime) > 1e-9:
                return None
            raw = data.get("dims")
            if not isinstance(raw, dict):
                return None
            result: dict[str, tuple[int, int]] = {}
            for name, dims in raw.items():
                if (
                    isinstance(name, str)
                    and isinstance(dims, list)
                    and len(dims) == 2
                    and all(isinstance(v, (int, float)) for v in dims)
                    and dims[0] > 0
                    and dims[1] > 0
                ):
                    result[name] = (int(dims[0]), int(dims[1]))
            return result
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            # 缓存损坏/不可读：忽略，由调用方重建
            logger.debug("维度缓存读取失败，忽略: %s", dir_path)
            return None

    def save(self, dir_path: str, dir_mtime: float, dims: dict[str, tuple[int, int]]) -> bool:
        """保存目录尺寸缓存

        Args:
            dir_path: 目录路径
            dir_mtime: 目录 mtime
            dims: 文件名 → (宽, 高) 映射

        Returns:
            是否成功写盘
        """
        try:
            if not self._ensure_dir():
                return False
            if not dims:
                return False
            cache_file = self._cache_file(dir_path)
            payload = {
                "mtime": dir_mtime,
                "dims": {name: list(dims_values) for name, dims_values in dims.items()},
            }
            tmp_file = cache_file.with_suffix(".tmp")
            tmp_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp_file, cache_file)
            self._prune_lru()
            return True
        except OSError:
            logger.debug("维度缓存写入失败，忽略: %s", dir_path)
            return False

    def clear(self) -> None:
        """清空全部持久化缓存"""
        try:
            if self._cache_dir.exists():
                for f in self._cache_dir.glob("*.json"):
                    f.unlink(missing_ok=True)
        except OSError:
            pass

    def _prune_lru(self) -> None:
        """按修改时间清理最旧的缓存文件（仅保留最近 max_dirs 份）"""
        try:
            if not self._cache_dir.exists():
                return
            files = sorted(
                (f for f in self._cache_dir.glob("*.json")),
                key=lambda f: f.stat().st_mtime,
            )
            excess = len(files) - self._max_dirs
            for f in files[:excess]:
                f.unlink(missing_ok=True)
        except OSError:
            pass

    def get_stats(self) -> dict:
        """导出缓存统计"""
        count = 0
        try:
            if self._cache_dir.exists():
                count = len(list(self._cache_dir.glob("*.json")))
        except OSError:
            pass
        return {"dir_count": count, "cache_dir": str(self._cache_dir)}


# 全局单例（与内存尺寸缓存并行：前者会话内热路径，本缓存跨启动冷启动）
_global_dim_cache: DirectoryDimensionCache | None = None
_dim_cache_lock = threading.Lock()


def get_dimension_cache() -> DirectoryDimensionCache:
    """获取全局目录尺寸持久化缓存单例"""
    global _global_dim_cache  # noqa: PLW0603  # 单例模式的合理使用
    with _dim_cache_lock:
        if _global_dim_cache is None:
            _global_dim_cache = DirectoryDimensionCache()
        return _global_dim_cache


def reset_dimension_cache() -> None:
    """重置全局单例（主要用于测试）"""
    global _global_dim_cache  # noqa: PLW0603  # 单例模式的合理使用
    with _dim_cache_lock:
        _global_dim_cache = None


__all__ = [
    "DirectoryDimensionCache",
    "get_dimension_cache",
    "reset_dimension_cache",
]
