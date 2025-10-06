

"""线程池管理模块

提供优化的线程池执行器，用于 PlookingII 应用程序的并发任务处理。
主要用于图像加载、缓存管理、预处理等 I/O 密集型和 CPU 密集型任务。

核心功能：
    - 自适应线程池大小配置
    - 基于 CPU 核心数的智能线程数量计算
    - 线程池资源管理和优化
    - 异步任务执行支持

使用场景：
    - 图像文件的并行加载和处理
    - 缓存系统的后台清理和维护
    - 预加载任务的异步执行
    - 大批量文件操作的并发处理

Author: PlookingII Team
"""

import os
from concurrent.futures import ThreadPoolExecutor

class _PatchedThreadPoolExecutor(ThreadPoolExecutor):
    """优化的线程池执行器

    继承自 concurrent.futures.ThreadPoolExecutor，提供智能的线程数量配置。
    根据系统 CPU 核心数自动计算最优线程池大小，平衡性能与资源占用。

    特性：
        - 自适应线程数量：基于 CPU 核心数动态计算
        - 资源限制：最大线程数限制为 64，避免过度消耗系统资源
        - 性能优化：针对 I/O 密集型任务优化的线程配置
        - 兼容性：完全兼容标准 ThreadPoolExecutor 接口

    计算公式：
        max_workers = min(64, cpu_count * 4)

    示例：
        - 4核CPU：max_workers = 16
        - 8核CPU：max_workers = 32
        - 16核CPU：max_workers = 64（受限制）
    """

    def __init__(self, max_workers=None, *args, **kwargs):
        """初始化优化的线程池执行器

        Args:
            max_workers (int, optional): 最大工作线程数。
                                       如果为 None，则根据 CPU 核心数自动计算。
                                       默认为 None。
            *args: 传递给父类的位置参数
            **kwargs: 传递给父类的关键字参数

        Note:
            - 自动计算的线程数适合 I/O 密集型任务（如文件读取、网络请求）
            - 对于 CPU 密集型任务，可能需要手动指定较小的 max_workers
            - 线程数上限为 64，防止创建过多线程导致系统性能下降
        """
        if max_workers is None:
            # 获取 CPU 核心数，如果获取失败则默认为 1
            cpu = os.cpu_count() or 1

            # 计算最优线程数：CPU核心数 * 4，但不超过 64
            # 这个比例适合 I/O 密集型任务，如图像文件读取
            max_workers = min(64, cpu * 4)

        # 调用父类构造函数，传递计算得到的线程数
        super().__init__(max_workers=max_workers, *args, **kwargs)
