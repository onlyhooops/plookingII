"""
预加载管理器 - 从双向缓存中分离出来的专门预加载逻辑

该模块负责处理图像预加载的复杂逻辑，包括：
- 智能优先级算法
- 内存感知的预加载窗口计算
- 导航方向感知的优先级调整
- 任务代次验证和取消机制
"""

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ..config.constants import APP_NAME
from ..config.manager import get_config
from ..imports import logging

logger = logging.getLogger(APP_NAME)


class PreloadTask:
    """预加载任务封装"""

    def __init__(self, priority: int, index: int, distance: int, image_key: str):
        self.priority = priority
        self.index = index
        self.distance = distance
        self.image_key = image_key
        self.created_at = time.time()

    def __lt__(self, other):
        """支持优先级队列排序"""
        return self.priority > other.priority  # 高优先级排前面


class PreloadWindowCalculator:
    """预加载窗口计算器"""

    @staticmethod
    def compute_window(
        cur_index: int, sequence_length: int, available_memory_mb: float, nav_speed_ips: float, nav_direction: str
    ) -> tuple[list[int], list[int]]:
        """计算预加载窗口

        Args:
            cur_index: 当前图像索引
            sequence_length: 序列总长度
            available_memory_mb: 可用内存(MB)
            nav_speed_ips: 导航速度(图像/秒)
            nav_direction: 导航方向

        Returns:
            (forward_indices, backward_indices): 前向和后向索引列表
        """
        # 基于内存的基础窗口大小
        base_window = min(max(int(available_memory_mb / 20), 3), 12)

        # 基于导航速度的动态调整
        speed_factor = min(nav_speed_ips / 2.0, 2.0)
        dynamic_window = int(base_window * (1 + speed_factor * 0.3))

        # 方向感知的窗口分配
        if nav_direction == "forward":
            forward_size = int(dynamic_window * 0.7)
            backward_size = int(dynamic_window * 0.3)
        elif nav_direction == "backward":
            forward_size = int(dynamic_window * 0.3)
            backward_size = int(dynamic_window * 0.7)
        else:
            forward_size = backward_size = int(dynamic_window * 0.5)

        # 计算索引范围
        forward_indices = []
        backward_indices = []

        # 前向索引
        for i in range(1, forward_size + 1):
            idx = cur_index + i
            if 0 <= idx < sequence_length:
                forward_indices.append(idx)

        # 后向索引
        for i in range(1, backward_size + 1):
            idx = cur_index - i
            if 0 <= idx < sequence_length:
                backward_indices.append(idx)

        return forward_indices, backward_indices


class PreloadPriorityCalculator:
    """预加载优先级计算器"""

    @staticmethod
    def calculate_priorities(
        forward_indices: list[int], backward_indices: list[int], nav_direction: str, sequence: list[str]
    ) -> list[PreloadTask]:
        """计算预加载任务的优先级

        Args:
            forward_indices: 前向索引列表
            backward_indices: 后向索引列表
            nav_direction: 导航方向
            sequence: 图像序列

        Returns:
            按优先级排序的PreloadTask列表
        """
        tasks = []

        # 前向图像：基础优先级100，距离越近优先级越高
        for d, i in enumerate(forward_indices, start=1):
            if i < len(sequence):
                priority = 100 - d
                # 前向导航时提升前向优先级
                if nav_direction == "forward":
                    priority += 10
                tasks.append(PreloadTask(priority, i, d, sequence[i]))

        # 后向图像：基础优先级50，距离越近优先级越高
        for d, i in enumerate(backward_indices, start=1):
            if i < len(sequence):
                priority = 50 - d
                # 后向导航时提升后向优先级
                if nav_direction == "backward":
                    priority += 10
                tasks.append(PreloadTask(priority, i, d, sequence[i]))

        # 按优先级排序
        tasks.sort()
        return tasks


class PreloadExecutor:
    """预加载执行器"""

    def __init__(self, cache_instance, memory_monitor):
        self.cache = cache_instance
        self.memory_monitor = memory_monitor
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="preload")

    def execute_tasks(self, tasks: list[PreloadTask], generation: int, cancel_check_callback) -> dict[str, Any]:
        """执行预加载任务

        Args:
            tasks: 预加载任务列表
            generation: 任务代次
            cancel_check_callback: 取消检查回调

        Returns:
            执行统计信息
        """
        stats = {
            "total_tasks": len(tasks),
            "completed": 0,
            "skipped": 0,
            "cancelled": 0,
            "errors": 0,
            "start_time": time.time(),
        }

        for task in tasks:
            # 检查是否需要取消
            if cancel_check_callback(generation):
                stats["cancelled"] += len(tasks) - stats["completed"] - stats["skipped"] - stats["errors"]
                break

            try:
                # 检查是否已在缓存中
                if task.image_key in self.cache._cache:
                    stats["skipped"] += 1
                    continue

                # 检查内存是否充足
                if self._should_skip_due_to_memory():
                    stats["skipped"] += 1
                    continue

                # 执行预加载
                success = self._load_single_image(task)
                if success:
                    stats["completed"] += 1
                else:
                    stats["errors"] += 1

                # 短暂延迟，避免过度占用资源
                time.sleep(0.01)

            except Exception as e:
                logger.warning("预加载任务执行失败: %s", e)
                stats["errors"] += 1

        stats["duration"] = time.time() - stats["start_time"]
        return stats

    def _should_skip_due_to_memory(self) -> bool:
        """检查是否因内存不足而跳过"""
        if not self.memory_monitor:
            return False

        try:
            mem_info = self.memory_monitor.get_memory_info()
            available = mem_info.get("available_mb", 1000)
            return available < 100  # 可用内存低于100MB时跳过
        except Exception:
            return False

    def _load_single_image(self, task: PreloadTask) -> bool:
        """加载单个图像"""
        try:
            # 使用图像处理器加载图像
            if hasattr(self.cache, "image_processor"):
                result = self.cache.image_processor.load_image_optimized(task.image_key)
            elif hasattr(self.cache, "image_cache"):
                result = self.cache.image_cache.get(task.image_key)
            else:
                # 回退到简单加载
                result = None

            if result:
                # 将结果存储到缓存中
                if hasattr(self.cache, "image_cache"):
                    self.cache.image_cache.put_new(task.image_key, result, layer="preload")
                return True
            return False
        except Exception:
            logger.debug("加载图像失败 %s: {e}", task.image_key)
            return False

    def shutdown(self):
        """关闭执行器"""
        self._executor.shutdown(wait=False)


class PreloadManager:
    """预加载管理器 - 负责整个预加载流程的协调"""

    def __init__(self, cache_instance, memory_monitor):
        self.cache = cache_instance
        self.memory_monitor = memory_monitor
        self.window_calculator = PreloadWindowCalculator()
        self.priority_calculator = PreloadPriorityCalculator()
        self.executor = PreloadExecutor(cache_instance, memory_monitor)

    def preload_images(
        self,
        current_key: str,
        generation: int,
        sequence: list[str],
        index_map: dict[str, int],
        nav_speed_ips: float,
        nav_direction: str,
        cancel_check_callback,
    ) -> dict[str, Any]:
        """执行图像预加载的主流程

        这是从原始_preload_images_sync函数重构而来的简化版本。

        Args:
            current_key: 当前图像键
            generation: 任务代次
            sequence: 图像序列
            index_map: 索引映射
            nav_speed_ips: 导航速度
            nav_direction: 导航方向
            cancel_check_callback: 取消检查回调

        Returns:
            预加载统计信息
        """
        # 检查是否禁用预加载
        if get_config("feature.disable_bidi_preload", True):
            return {"status": "disabled"}

        # 获取当前索引
        current_index = index_map.get(current_key, -1)
        if current_index < 0 or not sequence:
            return {"status": "invalid_index"}

        # 获取内存信息
        mem_info = self.memory_monitor.get_memory_info() if self.memory_monitor else {"available_mb": 1000}
        available_memory = mem_info.get("available_mb", 1000) or 1000

        # 计算预加载窗口
        forward_indices, backward_indices = self.window_calculator.compute_window(
            current_index, len(sequence), available_memory, nav_speed_ips, nav_direction
        )

        # 计算任务优先级
        tasks = self.priority_calculator.calculate_priorities(
            forward_indices, backward_indices, nav_direction, sequence
        )

        # 执行预加载任务
        stats = self.executor.execute_tasks(tasks, generation, cancel_check_callback)

        # 添加窗口信息到统计
        stats.update(
            {
                "current_index": current_index,
                "forward_window": len(forward_indices),
                "backward_window": len(backward_indices),
                "available_memory_mb": available_memory,
                "nav_direction": nav_direction,
            }
        )

        return stats

    def shutdown(self):
        """关闭预加载管理器"""
        self.executor.shutdown()
