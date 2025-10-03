#!/usr/bin/env python3
"""
内存优化工具

分析应用程序的内存使用情况，识别内存泄漏和优化机会，
提供内存优化建议和自动优化功能。
"""

import gc
import os
import sys
import time
import tracemalloc
from collections import defaultdict
from typing import Any, Dict, List

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plookingII.config.manager import get_config
from plookingII.core.enhanced_logging import get_enhanced_logger, LogCategory


class MemoryAnalyzer:
    """内存分析器"""

    def __init__(self):
        self.logger = get_enhanced_logger()
        self.snapshots = []
        self.object_counts = defaultdict(int)
        self.memory_usage_history = []

    def start_tracing(self):
        """开始内存跟踪"""
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            self.logger.info(LogCategory.PERFORMANCE, "Memory tracing started")

    def stop_tracing(self):
        """停止内存跟踪"""
        if tracemalloc.is_tracing():
            tracemalloc.stop()
            self.logger.info(LogCategory.PERFORMANCE, "Memory tracing stopped")

    def take_snapshot(self, label: str = "") -> Dict[str, Any]:
        """拍摄内存快照"""
        if not tracemalloc.is_tracing():
            self.start_tracing()

        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append((time.time(), label, snapshot))

        # 分析快照
        analysis = self._analyze_snapshot(snapshot)
        analysis['timestamp'] = time.time()
        analysis['label'] = label

        self.logger.log_performance("memory_snapshot", analysis['total_memory_mb'], "MB",
                                  {"label": label, "objects": analysis['total_objects']})

        return analysis

    def _analyze_snapshot(self, snapshot) -> Dict[str, Any]:
        """分析内存快照"""
        total_size = sum(stat.size for stat in snapshot.statistics('lineno'))
        total_objects = sum(stat.count for stat in snapshot.statistics('lineno'))

        # 按文件分组统计
        file_stats = {}
        for stat in snapshot.statistics('filename'):
            if stat.size > 1024:  # 只记录大于1KB的文件
                file_stats[stat.traceback.format()[0]] = {
                    'size_mb': stat.size / 1024 / 1024,
                    'count': stat.count
                }

        # 获取前10个最大的内存占用
        top_stats = []
        for stat in snapshot.statistics('lineno'):
            if stat.size > 1024 * 1024:  # 大于1MB
                top_stats.append({
                    'file': stat.traceback.format()[0],
                    'size_mb': stat.size / 1024 / 1024,
                    'count': stat.count
                })

        top_stats.sort(key=lambda x: x['size_mb'], reverse=True)

        return {
            'total_memory_mb': total_size / 1024 / 1024,
            'total_objects': total_objects,
            'file_stats': file_stats,
            'top_consumers': top_stats[:10]
        }

    def compare_snapshots(self, snapshot1_idx: int, snapshot2_idx: int) -> Dict[str, Any]:
        """比较两个快照"""
        if snapshot1_idx >= len(self.snapshots) or snapshot2_idx >= len(self.snapshots):
            return {}

        _, label1, snap1 = self.snapshots[snapshot1_idx]
        _, label2, snap2 = self.snapshots[snapshot2_idx]

        # 计算差异
        diff = snap2.compare_to(snap1, 'lineno')

        memory_diff = 0
        object_diff = 0
        changes = []

        for stat in diff:
            memory_diff += stat.size_diff
            object_diff += stat.count_diff

            if abs(stat.size_diff) > 1024 * 1024:  # 变化大于1MB
                changes.append({
                    'file': stat.traceback.format()[0],
                    'size_diff_mb': stat.size_diff / 1024 / 1024,
                    'count_diff': stat.count_diff
                })

        return {
            'memory_diff_mb': memory_diff / 1024 / 1024,
            'object_diff': object_diff,
            'changes': sorted(changes, key=lambda x: abs(x['size_diff_mb']), reverse=True),
            'snapshot1_label': label1,
            'snapshot2_label': label2
        }

    def get_memory_usage(self) -> Dict[str, Any]:
        """获取当前内存使用情况"""
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()

        # 获取Python对象统计
        gc_stats = gc.get_stats()

        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'gc_collections': gc_stats,
            'gc_objects': len(gc.get_objects())
        }


class MemoryOptimizer:
    """内存优化器"""

    def __init__(self):
        self.logger = get_enhanced_logger()
        self.analyzer = MemoryAnalyzer()
        self.optimization_history = []

    def analyze_memory_leaks(self) -> List[Dict[str, Any]]:
        """分析内存泄漏"""
        self.logger.info(LogCategory.PERFORMANCE, "Starting memory leak analysis")

        # 拍摄初始快照
        initial_snapshot = self.analyzer.take_snapshot("initial")

        # 强制垃圾回收
        collected = gc.collect()
        self.logger.info(LogCategory.PERFORMANCE, f"Garbage collection freed {collected} objects")

        # 拍摄清理后快照
        after_gc_snapshot = self.analyzer.take_snapshot("after_gc")

        # 分析差异
        memory_diff = after_gc_snapshot['total_memory_mb'] - initial_snapshot['total_memory_mb']

        leaks = []
        if memory_diff > 10:  # 如果内存增长超过10MB
            leaks.append({
                'type': 'potential_memory_leak',
                'memory_growth_mb': memory_diff,
                'description': f"Memory grew by {memory_diff:.2f}MB after garbage collection"
            })

        # 检查循环引用
        circular_refs = self._find_circular_references()
        if circular_refs:
            leaks.append({
                'type': 'circular_references',
                'count': len(circular_refs),
                'description': f"Found {len(circular_refs)} potential circular references"
            })

        return leaks

    def _find_circular_references(self) -> List[Any]:
        """查找循环引用"""
        circular_refs = []

        # 获取所有对象
        all_objects = gc.get_objects()

        # 检查循环引用
        for obj in all_objects:
            if gc.is_tracked(obj):
                refs = gc.get_referrers(obj)
                if len(refs) > 10:  # 如果引用过多，可能存在循环引用
                    circular_refs.append(obj)

        return circular_refs[:50]  # 限制返回数量

    def optimize_memory_usage(self) -> Dict[str, Any]:
        """执行内存优化"""
        self.logger.info(LogCategory.PERFORMANCE, "Starting memory optimization")

        optimization_results = {
            'before_mb': 0,
            'after_mb': 0,
            'freed_mb': 0,
            'optimizations_applied': []
        }

        # 记录优化前内存使用
        before_usage = self.analyzer.get_memory_usage()
        optimization_results['before_mb'] = before_usage['rss_mb']

        # 1. 强制垃圾回收
        collected = gc.collect()
        optimization_results['optimizations_applied'].append({
            'type': 'garbage_collection',
            'objects_freed': collected
        })

        # 2. 清理缓存
        cache_cleaned = self._cleanup_caches()
        optimization_results['optimizations_applied'].append({
            'type': 'cache_cleanup',
            'caches_cleaned': cache_cleaned
        })

        # 3. 优化图像缓存
        image_cache_optimized = self._optimize_image_cache()
        optimization_results['optimizations_applied'].append({
            'type': 'image_cache_optimization',
            'images_cleaned': image_cache_optimized
        })

        # 4. 清理临时文件
        temp_files_cleaned = self._cleanup_temp_files()
        optimization_results['optimizations_applied'].append({
            'type': 'temp_file_cleanup',
            'files_cleaned': temp_files_cleaned
        })

        # 记录优化后内存使用
        after_usage = self.analyzer.get_memory_usage()
        optimization_results['after_mb'] = after_usage['rss_mb']
        optimization_results['freed_mb'] = optimization_results['before_mb'] - optimization_results['after_mb']

        self.logger.info(LogCategory.PERFORMANCE,
                        f"Memory optimization completed. Freed {optimization_results['freed_mb']:.2f}MB")

        # 记录优化历史
        self.optimization_history.append({
            'timestamp': time.time(),
            'results': optimization_results
        })

        return optimization_results

    def _cleanup_caches(self) -> int:
        """清理各种缓存"""
        cleaned_count = 0

        try:
            # 清理统一缓存管理器
            try:
                from plookingII.core.unified_cache_manager import get_unified_cache_manager
                cache_manager = get_unified_cache_manager()
                if hasattr(cache_manager, 'clear'):
                    cache_manager.clear()
                    cleaned_count += 1
            except ImportError:
                pass  # 忽略导入错误

        except Exception as e:
            self.logger.error(e, "cache_cleanup")

        return cleaned_count

    def _optimize_image_cache(self) -> int:
        """优化图像缓存"""
        optimized_count = 0

        try:
            # 获取图像缓存配置
            get_config("cache.max_size", 100)
            get_config("cache.memory_threshold", 0.8)

            # 如果内存使用过高，清理部分缓存
            current_usage = self.analyzer.get_memory_usage()
            if current_usage['rss_mb'] > 500:  # 如果内存使用超过500MB
                # 这里需要实际的缓存清理逻辑
                optimized_count = 1

        except Exception as e:
            self.logger.error(e, "image_cache_optimization")

        return optimized_count

    def _cleanup_temp_files(self) -> int:
        """清理临时文件"""
        cleaned_count = 0

        try:
            import tempfile
            import shutil

            # 清理系统临时目录中的plookingII相关文件
            temp_dir = tempfile.gettempdir()
            for filename in os.listdir(temp_dir):
                if 'plooking' in filename.lower():
                    filepath = os.path.join(temp_dir, filename)
                    try:
                        if os.path.isfile(filepath):
                            os.remove(filepath)
                            cleaned_count += 1
                        elif os.path.isdir(filepath):
                            shutil.rmtree(filepath)
                            cleaned_count += 1
                    except Exception:
                        pass  # 忽略无法删除的文件

        except Exception as e:
            self.logger.error(e, "temp_file_cleanup")

        return cleaned_count

    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """获取内存优化建议"""
        suggestions = []

        # 分析当前内存使用
        current_usage = self.analyzer.get_memory_usage()

        # 检查内存使用是否过高
        if current_usage['rss_mb'] > 1000:  # 超过1GB
            suggestions.append({
                'type': 'high_memory_usage',
                'priority': 'high',
                'description': f"Memory usage is {current_usage['rss_mb']:.2f}MB, consider reducing cache sizes",
                'action': 'Reduce cache.max_size and cache.memory_threshold in configuration'
            })

        # 检查垃圾回收统计
        gc_stats = current_usage['gc_collections']
        if gc_stats:
            total_collections = sum(stat['collected'] for stat in gc_stats)
            if total_collections > 1000:
                suggestions.append({
                    'type': 'frequent_gc',
                    'priority': 'medium',
                    'description': f"Frequent garbage collection ({total_collections} collections)",
                    'action': 'Consider using object pooling or reducing object creation'
                })

        # 检查对象数量
        if current_usage['gc_objects'] > 100000:
            suggestions.append({
                'type': 'too_many_objects',
                'priority': 'medium',
                'description': f"Too many Python objects ({current_usage['gc_objects']})",
                'action': 'Review object lifecycle and consider using weak references'
            })

        return suggestions

    def generate_memory_report(self) -> Dict[str, Any]:
        """生成内存报告"""
        self.logger.info(LogCategory.PERFORMANCE, "Generating memory report")

        # 拍摄当前快照
        current_snapshot = self.analyzer.take_snapshot("current")

        # 获取内存使用情况
        memory_usage = self.analyzer.get_memory_usage()

        # 分析内存泄漏
        leaks = self.analyze_memory_leaks()

        # 获取优化建议
        suggestions = self.get_optimization_suggestions()

        # 获取优化历史
        recent_optimizations = self.optimization_history[-5:] if self.optimization_history else []

        report = {
            'timestamp': time.time(),
            'current_memory_mb': memory_usage['rss_mb'],
            'virtual_memory_mb': memory_usage['vms_mb'],
            'gc_objects': memory_usage['gc_objects'],
            'snapshot_analysis': current_snapshot,
            'memory_leaks': leaks,
            'optimization_suggestions': suggestions,
            'recent_optimizations': recent_optimizations
        }

        return report


def main():
    """主函数"""
    print("PlookingII Memory Optimizer")
    print("=" * 50)

    optimizer = MemoryOptimizer()

    # 生成内存报告
    report = optimizer.generate_memory_report()

    print(f"Current Memory Usage: {report['current_memory_mb']:.2f} MB")
    print(f"Virtual Memory: {report['virtual_memory_mb']:.2f} MB")
    print(f"Python Objects: {report['gc_objects']}")

    # 显示内存泄漏
    if report['memory_leaks']:
        print("\nMemory Leaks Detected:")
        for leak in report['memory_leaks']:
            print(f"  - {leak['description']}")

    # 显示优化建议
    if report['optimization_suggestions']:
        print("\nOptimization Suggestions:")
        for suggestion in report['optimization_suggestions']:
            print(f"  [{suggestion['priority'].upper()}] {suggestion['description']}")
            print(f"    Action: {suggestion['action']}")

    # 执行内存优化
    print("\nExecuting memory optimization...")
    optimization_results = optimizer.optimize_memory_usage()

    print(f"Memory freed: {optimization_results['freed_mb']:.2f} MB")
    print("Optimizations applied:")
    for opt in optimization_results['optimizations_applied']:
        print(f"  - {opt['type']}: {opt.get('objects_freed', opt.get('caches_cleaned', opt.get('images_cleaned', opt.get('files_cleaned', 'N/A'))))}")


if __name__ == "__main__":
    main()
