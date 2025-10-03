"""
图像性能基准测试模块

提供全面的性能测试和基准比较功能，用于验证v1.0.0性能优化的效果。
支持多种测试场景和性能指标分析。

主要功能：
    - 图像加载性能测试
    - 内存使用情况测试
    - 缓存性能测试
    - 策略对比测试

Author: PlookingII Team
Version: 1.0.0
"""

import os
import time
import logging
import tempfile
from typing import List, Dict, Any
from pathlib import Path

# 导入项目模块
from ..core.image_processing import HybridImageProcessor
from ..core.cache import AdvancedImageCache
from ..core.memory_estimator import ImageMemoryEstimator
from ..core.memory_pool import ImageMemoryPool
from ..monitor.performance import ImagePerformanceMonitor

logger = logging.getLogger(__name__)

class ImagePerformanceBenchmark:
    """图像性能基准测试"""

    def __init__(self, test_images_dir: str = None):
        """初始化性能测试

        Args:
            test_images_dir: 测试图像目录，如果为None则使用默认测试图像
        """
        self.test_images_dir = test_images_dir or self._create_test_images()
        self.test_images = self._discover_test_images()

        # 初始化测试组件
        self.image_processor = HybridImageProcessor()
        self.image_cache = AdvancedImageCache()
        self.memory_estimator = ImageMemoryEstimator()
        self.memory_pool = ImageMemoryPool(max_memory_mb=500)
        self.performance_monitor = ImagePerformanceMonitor()

        # 测试结果
        self.results = {}

    def _create_test_images(self) -> str:
        """创建测试图像（如果不存在）"""
        try:
            from PIL import Image
            import numpy as np

            test_dir = tempfile.mkdtemp(prefix="plookingii_test_")

            # 创建不同大小的测试图像
            test_sizes = [
                (800, 600, "small"),      # 小图像
                (1920, 1080, "medium"),   # 中等图像
                (3840, 2160, "large"),    # 大图像
                (7680, 4320, "huge"),     # 超大图像
            ]

            for width, height, size_name in test_sizes:
                # 创建随机图像数据
                image_data = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
                image = Image.fromarray(image_data)

                # 保存为不同格式
                for ext in ['jpg', 'png']:
                    file_path = os.path.join(test_dir, f"test_{size_name}_{width}x{height}.{ext}")
                    if ext == 'jpg':
                        image.save(file_path, 'JPEG', quality=95)
                    else:
                        image.save(file_path, 'PNG')

            logger.info(f"Created test images in: {test_dir}")
            return test_dir

        except ImportError:
            logger.warning("PIL not available, using existing test images")
            return "/tmp"  # 回退到临时目录

    def _discover_test_images(self) -> List[str]:
        """发现测试图像"""
        if not os.path.exists(self.test_images_dir):
            return []

        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        test_images = []

        for file_path in Path(self.test_images_dir).rglob('*'):
            if file_path.suffix.lower() in image_extensions:
                test_images.append(str(file_path))

        # 按文件大小排序
        test_images.sort(key=lambda x: os.path.getsize(x) if os.path.exists(x) else 0)

        logger.info(f"Found {len(test_images)} test images")
        return test_images

    def run_loading_benchmark(self, max_images: int = 10) -> Dict[str, Any]:
        """运行加载性能测试

        Args:
            max_images: 最大测试图像数量

        Returns:
            dict: 测试结果
        """
        logger.info("Starting loading performance benchmark...")

        test_images = self.test_images[:max_images]
        if not test_images:
            logger.error("No test images found")
            return {}

        results = {
            'original_method': [],
            'optimized_method': [],
            'memory_mapped': [],
            'quartz_optimized': [],
            'fast_loading': [],
            'preview_loading': []
        }

        # 测试不同策略
        strategies = [
            ('auto', 'auto'),
            ('optimized', 'optimized'),
            ('preview', 'preview')
        ]
        # 如果开启了pyvips并且可用，加入对比
        try:
            from ..core.unified_config import unified_config
            import pyvips  # type: ignore  # noqa: F401
            if unified_config.get('image_processing.vips_enabled', False):
                strategies.append(('vips', 'optimized'))  # 仍走optimized，但会在内部触发vips
        except Exception:
            pass

        for strategy_name, strategy_type in strategies:
            logger.info(f"Testing {strategy_name}...")

            for image_path in test_images:
                try:
                    # 记录文件大小
                    file_size_mb = os.path.getsize(image_path) / (1024 * 1024)

                    # 测试加载时间
                    start_time = time.time()
                    image = self.image_processor.load_image_optimized(
                        image_path, strategy=strategy_type
                    )
                    load_time = time.time() - start_time

                    # 记录结果
                    results[strategy_name].append({
                        'file': image_path,
                        'load_time': load_time,
                        'file_size_mb': file_size_mb,
                        'success': image is not None
                    })

                    # 记录到性能监控器
                    self.performance_monitor.record_load_time(
                        image_path, load_time, strategy_type, file_size_mb, image is not None
                    )

                except Exception as exc:
                    logger.error(f"Error testing {strategy_name} with {image_path}: {exc}")
                    results[strategy_name].append({
                        'file': image_path,
                        'load_time': 0,
                        'file_size_mb': 0,
                        'success': False,
                        'error': str(exc)
                    })

        self.results['loading_benchmark'] = results
        return results

    def run_switch_sequence_benchmark(self, max_images: int = 20) -> Dict[str, Any]:
        """运行快速切图序列基准（正向/反向/抖动）

        说明：不依赖UI管理器，仅以处理器+缓存近似模拟切换延迟。
        记录每次“上一张→下一张”加载的端到端耗时（含缓存命中）。
        """
        logger.info("Starting switch sequence benchmark...")

        seq = self.test_images[:max_images]
        if len(seq) < 3:
            return {}

        def _measure_sequence(order: List[int], name: str) -> Dict[str, Any]:
            times = []
            hits = 0
            misses = 0
            for idx in order:
                path = seq[idx]
                start = time.time()
                # 先尝试缓存
                cached = self.image_cache.get(path)
                if cached is None:
                    misses += 1
                    img = self.image_processor.load_image_optimized(path, strategy="auto")
                    if img:
                        try:
                            self.image_cache.put_new(path, img, layer="main")
                        except Exception:
                            pass
                else:
                    hits += 1
                times.append(time.time() - start)
            # 统计
            if times:
                sorted_t = sorted(times)
                p50 = sorted_t[int(0.5 * (len(sorted_t)-1))]
                p95 = sorted_t[int(0.95 * (len(sorted_t)-1))]
            else:
                p50 = p95 = 0.0
            return {
                'pattern': name,
                'count': len(times),
                'avg': sum(times)/len(times) if times else 0.0,
                'p50': p50,
                'p95': p95,
                'hits': hits,
                'misses': misses,
            }

        n = len(seq)
        forward_order = list(range(n))
        backward_order = list(reversed(range(n)))
        jitter_order = []
        for i in range(min(n-2, max_images-2)):
            jitter_order.extend([i, i+2, i+1])
        jitter_order = [x for x in jitter_order if x < n]

        results = {
            'forward': _measure_sequence(forward_order, 'forward'),
            'backward': _measure_sequence(backward_order, 'backward'),
            'jitter': _measure_sequence(jitter_order, 'jitter'),
        }

        self.results['switch_sequence_benchmark'] = results
        return results

    def run_memory_benchmark(self) -> Dict[str, Any]:
        """运行内存使用测试

        Returns:
            dict: 内存测试结果
        """
        logger.info("Starting memory usage benchmark...")

        results = {
            'memory_estimation_accuracy': [],
            'cache_memory_efficiency': [],
            'memory_pool_efficiency': []
        }

        # 测试内存估算准确性
        for image_path in self.test_images[:5]:  # 测试前5张图片
            try:
                # 加载图像
                image = self.image_processor.load_image_optimized(image_path)
                if image:
                    # 估算内存使用
                    estimated_mb = self.memory_estimator.estimate_image_memory(image)

                    # 实际文件大小
                    file_size_mb = os.path.getsize(image_path) / (1024 * 1024)

                    # 计算准确性
                    accuracy = (
                        min(estimated_mb, file_size_mb) / max(estimated_mb, file_size_mb) if max(estimated_mb, file_size_mb) > 0 else 0
                    )

                    results['memory_estimation_accuracy'].append({
                        'file': image_path,
                        'estimated_mb': estimated_mb,
                        'file_size_mb': file_size_mb,
                        'accuracy': accuracy
                    })

            except Exception as e:
                logger.error(f"Error in memory estimation test: {e}")

        # 测试缓存内存效率
        cache_stats = self.image_cache.get_stats()
        results['cache_memory_efficiency'] = {
            'total_memory_mb': sum(layer['memory_mb'] for layer in cache_stats['layers'].values()),
            'hit_rate': cache_stats['hit_rate'],
            'total_requests': cache_stats['total_requests']
        }

        # 测试内存池效率
        pool_stats = self.memory_pool.get_memory_usage()
        results['memory_pool_efficiency'] = pool_stats

        self.results['memory_benchmark'] = results
        return results

    def run_cache_benchmark(self) -> Dict[str, Any]:
        """运行缓存性能测试

        Returns:
            dict: 缓存测试结果
        """
        logger.info("Starting cache performance benchmark...")

        results = {
            'cache_hit_rates': {},
            'cache_access_times': [],
            'cache_memory_usage': []
        }

        # 测试缓存命中率
        test_images = self.test_images[:10]

        # 第一次加载（应该都是缓存未命中）
        for image_path in test_images:
            start_time = time.time()
            image = self.image_cache.get(image_path)
            access_time = time.time() - start_time

            results['cache_access_times'].append({
                'file': image_path,
                'access_time': access_time,
                'hit': image is not None
            })

        # 第二次加载（应该都是缓存命中）
        for image_path in test_images:
            start_time = time.time()
            image = self.image_cache.get(image_path)
            access_time = time.time() - start_time

            results['cache_access_times'].append({
                'file': image_path,
                'access_time': access_time,
                'hit': image is not None
            })

        # 计算缓存统计
        cache_stats = self.image_cache.get_stats()
        results['cache_hit_rates'] = {
            'overall': cache_stats['hit_rate'],
            'by_layer': {layer: stats['hit_rate'] for layer, stats in cache_stats['layers'].items()}
        }

        # 记录内存使用
        results['cache_memory_usage'] = {
            'total_mb': sum(layer['memory_mb'] for layer in cache_stats['layers'].values()),
            'by_layer': {layer: stats['memory_mb'] for layer, stats in cache_stats['layers'].items()}
        }

        self.results['cache_benchmark'] = results
        return results

    def run_strategy_comparison(self) -> Dict[str, Any]:
        """运行策略对比测试

        Returns:
            dict: 策略对比结果
        """
        logger.info("Starting strategy comparison benchmark...")

        results = {
            'strategy_performance': {},
            'strategy_memory_usage': {},
            'strategy_success_rates': {}
        }

        strategies = ['optimized', 'preview', 'auto']
        test_images = self.test_images[:5]  # 测试前5张图片

        for strategy_name in strategies:
            strategy_results = {
                'load_times': [],
                'memory_usage': [],
                'success_count': 0,
                'total_count': 0
            }

            for image_path in test_images:
                try:
                    os.path.getsize(image_path) / (1024 * 1024)

                    # 测试加载
                    start_time = time.time()
                    image = (
                        self.image_processor.load_image_optimized(image_path, strategy=strategy_name)
                    )
                    load_time = time.time() - start_time

                    # 测试内存使用
                    memory_usage = 0
                    if image:
                        memory_usage = self.memory_estimator.estimate_image_memory(image)

                    strategy_results['load_times'].append(load_time)
                    strategy_results['memory_usage'].append(memory_usage)
                    strategy_results['total_count'] += 1

                    if image:
                        strategy_results['success_count'] += 1

                except Exception as e:
                    logger.error(f"Error testing strategy {strategy_name}: {e}")
                    strategy_results['total_count'] += 1

            # 计算统计信息
            if strategy_results['load_times']:
                results['strategy_performance'][strategy_name] = {
                    'avg_load_time': sum(strategy_results['load_times']) / len(strategy_results['load_times']),
                    'min_load_time': min(strategy_results['load_times']),
                    'max_load_time': max(strategy_results['load_times'])
                }

            if strategy_results['memory_usage']:
                results['strategy_memory_usage'][strategy_name] = {
                    'avg_memory': sum(strategy_results['memory_usage']) / len(strategy_results['memory_usage']),
                    'max_memory': max(strategy_results['memory_usage'])
                }

            results['strategy_success_rates'][strategy_name] = (
                strategy_results['success_count'] / strategy_results['total_count'] * 100
                if strategy_results['total_count'] > 0 else 0
            )

        self.results['strategy_comparison'] = results
        return results

    def run_cgimage_passthrough_benchmark(self, sample_image_path: str, iterations: int = 50) -> Dict[str, Any]:
        """Quick micro-benchmark: CGImage pass-through vs NSImage wrapping.

        Args:
            sample_image_path: path to a valid image file
            iterations: number of set operations per mode

        Returns:
            dict with avg_ms for cgimage_direct and nsimage_wrap
        """
        try:
            from AppKit import NSMakeRect, NSImage
            from Quartz import CGImageSourceCreateWithURL, CGImageSourceCreateImageAtIndex
            from Foundation import NSURL
            from ..ui.views import AdaptiveImageView
        except Exception:
            return {"error": "CGImage/NSAppKit not available"}

        try:
            url = NSURL.fileURLWithPath_(sample_image_path)
            source = CGImageSourceCreateWithURL(url, None)
            if not source:
                return {"error": "failed to create image source"}
            cg = CGImageSourceCreateImageAtIndex(source, 0, None)
            if not cg:
                return {"error": "failed to create cgimage"}

            view = AdaptiveImageView.alloc().initWithFrame_(NSMakeRect(0, 0, 1600, 900))

            import time
            iters = max(1, int(iterations))

            t0 = time.time()
            for _ in range(iters):
                view.setCGImage_(cg)
            cg_ms = (time.time() - t0) * 1000.0 / iters

            nsimg = NSImage.alloc().initWithCGImage_(cg)
            t1 = time.time()
            for _ in range(iters):
                view.setImage_(nsimg)
            ns_ms = (time.time() - t1) * 1000.0 / iters

            result = {
                "cgimage_direct_avg_ms": round(cg_ms, 3),
                "nsimage_wrap_avg_ms": round(ns_ms, 3),
                "iterations": iters,
                "path": sample_image_path,
            }
            self.results.setdefault('microbenchmarks', {})['cgimage_vs_nsimage'] = result
            return result
        except Exception as e:
            return {"error": str(e)}

    def generate_report(self) -> Dict[str, Any]:
        """生成完整的性能报告

        Returns:
            dict: 完整的性能报告
        """
        logger.info("Generating performance report...")

        # 运行所有测试
        loading_results = self.run_loading_benchmark()
        switch_results = self.run_switch_sequence_benchmark()
        memory_results = self.run_memory_benchmark()
        cache_results = self.run_cache_benchmark()
        strategy_results = self.run_strategy_comparison()

        # 获取性能监控报告
        performance_report = self.performance_monitor.get_performance_report()

        # 生成优化建议
        optimization_suggestions = self.performance_monitor.get_optimization_suggestions()

        # 计算总体性能提升
        performance_improvement = self._calculate_performance_improvement()

        report = {
            'test_info': {
                'version': 'v1.0.0',
                'test_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'test_images_count': len(self.test_images),
                'test_images_dir': self.test_images_dir
            },
            'loading_benchmark': loading_results,
            'memory_benchmark': memory_results,
            'switch_sequence_benchmark': switch_results,
            'cache_benchmark': cache_results,
            'strategy_comparison': strategy_results,
            'performance_monitor': performance_report,
            'optimization_suggestions': optimization_suggestions,
            'performance_improvement': performance_improvement
        }

        self.results['full_report'] = report
        return report

    def _calculate_performance_improvement(self) -> Dict[str, Any]:
        """计算性能提升

        Returns:
            dict: 性能提升统计
        """
        if 'loading_benchmark' not in self.results:
            return {}

        loading_results = self.results['loading_benchmark']

        # 比较原始方法和优化方法
        original_times = (
            [r['load_time'] for r in loading_results.get('original_method', []) if r['success']]
        )
        optimized_times = (
            [r['load_time'] for r in loading_results.get('optimized_method', []) if r['success']]
        )

        if not original_times or not optimized_times:
            return {}

        avg_original = sum(original_times) / len(original_times)
        avg_optimized = sum(optimized_times) / len(optimized_times)

        improvement_percentage = (
            ((avg_original - avg_optimized) / avg_original * 100) if avg_original > 0 else 0
        )

        return {
            'avg_load_time_improvement': improvement_percentage,
            'original_avg_time': avg_original,
            'optimized_avg_time': avg_optimized,
            'speedup_factor': avg_original / avg_optimized if avg_optimized > 0 else 1.0
        }

    def save_report(self, output_file: str = None):
        """保存测试报告到文件

        Args:
            output_file: 输出文件路径，如果为None则使用默认路径
        """
        if not output_file:
            output_file = f"plookingii_performance_report_{int(time.time())}.json"

        import json

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results.get('full_report', {}), f, indent=2, ensure_ascii=False)

        logger.info(f"Performance report saved to: {output_file}")

    def cleanup(self):
        """清理测试资源"""
        try:
            # 清理测试图像目录
            if self.test_images_dir and os.path.exists(self.test_images_dir):
                import shutil
                shutil.rmtree(self.test_images_dir)
                logger.info("Test images cleaned up")
        except Exception as e:
            logger.warning(f"Failed to cleanup test resources: {e}")

def run_performance_benchmark():
    """运行性能基准测试的主函数"""
    benchmark = ImagePerformanceBenchmark()

    try:
        # 生成报告
        report = benchmark.generate_report()

        # 运行CGImage直通微基准（选取最小测试图像）
        try:
            sample = benchmark.test_images[0] if benchmark.test_images else None
            if sample:
                cgbench = benchmark.run_cgimage_passthrough_benchmark(sample)
                report.setdefault('microbenchmarks', {})['cgimage_vs_nsimage'] = cgbench
        except Exception:
            pass

        # 保存报告
        benchmark.save_report()

        # 打印关键指标
        print("\n=== PlookingII v1.0.0 Performance Benchmark ===")
        print(f"Test completed at: {report['test_info']['test_time']}")
        print(f"Test images: {report['test_info']['test_images_count']}")

        if 'performance_improvement' in report and report['performance_improvement']:
            improvement = report['performance_improvement']
            print(f"\nPerformance Improvement:")
            print(f"  Average load time improvement: {improvement['avg_load_time_improvement']:.1f}%")
            print(f"  Speedup factor: {improvement['speedup_factor']:.2f}x")

        if 'performance_monitor' in report:
            perf = report['performance_monitor']
            print(f"\nPerformance Score: {perf['performance_score']:.1f}/100")
            print(f"Cache Hit Rate: {perf['cache_stats']['hit_rate']:.1f}%")

        if 'optimization_suggestions' in report and report['optimization_suggestions']:
            print(f"\nOptimization Suggestions:")
            for suggestion in report['optimization_suggestions']:
                print(f"  - {suggestion}")

        if 'microbenchmarks' in report and 'cgimage_vs_nsimage' in report['microbenchmarks']:
            m = report['microbenchmarks']['cgimage_vs_nsimage']
            if 'error' not in m:
                print("\nCGImage pass-through microbenchmark:")
                print(f"  CGImage direct avg: {m['cgimage_direct_avg_ms']} ms")
                print(f"  NSImage wrap avg:   {m['nsimage_wrap_avg_ms']} ms")

        return report

    finally:
        benchmark.cleanup()

if __name__ == "__main__":
    run_performance_benchmark()
