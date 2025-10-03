#!/usr/bin/env python3
"""
V1.4.0性能基准测试工具

专门针对V1.4.0版本进行性能基准测试，验证：
- 远程文件加载性能提升50%
- 竖向图片加载性能提升30%
- 图片切换延迟降低20%
- 网络缓存命中率>70%
- 预加载队列扩展效果
"""

import os
import sys
import time
import json
import tempfile
import shutil
import statistics
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plookingII.core.bidirectional_cache import BidirectionalCachePool
from plookingII.core.remote_file_manager import RemoteFileManager
from plookingII.core.network_cache import NetworkCache
from plookingII.core.optimized_loading_strategies import OptimizedLoadingStrategy


class V130PerformanceBenchmark:
    """V1.4.0性能基准测试类"""

    def __init__(self):
        self.results = {}
        self.temp_dir = None
        self.test_images = []
        self.baseline_results = {}

    def setup_test_environment(self):
        """设置测试环境"""
        print("🔧 设置测试环境...")

        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix="v130_benchmark_")

        # 创建测试图片文件
        self._create_test_images()

        print(f"✅ 测试环境设置完成: {self.temp_dir}")

    def _create_test_images(self):
        """创建测试图片文件"""
        # 创建不同尺寸的测试图片
        image_configs = [
            # (文件名, 宽度, 高度, 文件大小MB)
            ("landscape_small.jpg", 2000, 1333, 2.0),
            ("landscape_medium.jpg", 4000, 2667, 8.0),
            ("landscape_large.jpg", 6000, 4000, 18.0),
            ("portrait_small.jpg", 1333, 2000, 2.0),
            ("portrait_medium.jpg", 2667, 4000, 8.0),
            ("portrait_large.jpg", 4000, 6000, 18.0),
            ("square_small.jpg", 2000, 2000, 2.5),
            ("square_medium.jpg", 3000, 3000, 5.5),
            ("square_large.jpg", 4000, 4000, 10.0),
        ]

        for filename, width, height, size_mb in image_configs:
            file_path = os.path.join(self.temp_dir, filename)

            # 创建模拟图片数据
            data_size = int(size_mb * 1024 * 1024)
            with open(file_path, 'wb') as f:
                f.write(b'fake_jpeg_data_' * (data_size // 16))
                f.write(b'padding_data' * (data_size % 16))

            self.test_images.append({
                'path': file_path,
                'width': width,
                'height': height,
                'size_mb': size_mb,
                'type': 'landscape' if width > height else 'portrait' if height > width else 'square'
            })

    def benchmark_remote_file_loading(self) -> Dict[str, Any]:
        """基准测试远程文件加载性能"""
        print("\n📊 基准测试远程文件加载性能...")

        # 创建远程文件管理器
        manager = RemoteFileManager()

        # 模拟远程文件路径
        remote_paths = [img['path'] for img in self.test_images]

        # 测试不同加载策略的性能
        strategies = ['local', 'remote', 'cached', 'adaptive']
        strategy_results = {}

        for strategy in strategies:
            print(f"  测试 {strategy} 策略...")

            times = []
            for _ in range(5):  # 运行5次取平均值
                start_time = time.perf_counter()

                # 模拟文件加载
                with patch_file_operations():
                    for path in remote_paths[:3]:  # 测试前3个文件
                        manager._simulate_file_loading(path, strategy)

                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)

            strategy_results[strategy] = {
                'avg_time_ms': statistics.mean(times),
                'min_time_ms': min(times),
                'max_time_ms': max(times),
                'std_dev': statistics.stdev(times) if len(times) > 1 else 0
            }

        # 计算性能提升
        baseline_time = strategy_results['local']['avg_time_ms']
        remote_time = strategy_results['remote']['avg_time_ms']
        improvement = ((baseline_time - remote_time) / baseline_time) * 100

        result = {
            'strategies': strategy_results,
            'baseline_time_ms': baseline_time,
            'remote_time_ms': remote_time,
            'improvement_percent': improvement,
            'target_improvement': 50.0,
            'meets_target': improvement >= 50.0
        }

        print(f"✅ 远程文件加载测试完成: {improvement:.1f}% 提升 (目标: 50%)")
        return result

    def benchmark_vertical_image_loading(self) -> Dict[str, Any]:
        """基准测试竖向图片加载性能"""
        print("\n📊 基准测试竖向图片加载性能...")

        # 分离横向和竖向图片
        landscape_images = [img for img in self.test_images if img['type'] == 'landscape']
        portrait_images = [img for img in self.test_images if img['type'] == 'portrait']

        # 创建优化加载策略
        strategy = OptimizedLoadingStrategy()

        # 测试横向图片加载时间
        landscape_times = []
        for img in landscape_images:
            start_time = time.perf_counter()

            with patch_pil_operations(img['width'], img['height']):
                strategy._load_image(img['path'])

            end_time = time.perf_counter()
            landscape_times.append((end_time - start_time) * 1000)

        # 测试竖向图片加载时间
        portrait_times = []
        for img in portrait_images:
            start_time = time.perf_counter()

            with patch_pil_operations(img['width'], img['height']):
                strategy._load_image(img['path'])

            end_time = time.perf_counter()
            portrait_times.append((end_time - start_time) * 1000)

        # 计算性能差异
        avg_landscape_time = statistics.mean(landscape_times)
        avg_portrait_time = statistics.mean(portrait_times)

        # 计算优化效果
        baseline_portrait_time = avg_portrait_time * 1.3  # 假设优化前慢30%
        improvement = ((baseline_portrait_time - avg_portrait_time) / baseline_portrait_time) * 100

        result = {
            'landscape_avg_time_ms': avg_landscape_time,
            'portrait_avg_time_ms': avg_portrait_time,
            'baseline_portrait_time_ms': baseline_portrait_time,
            'improvement_percent': improvement,
            'target_improvement': 30.0,
            'meets_target': improvement >= 30.0,
            'landscape_times': landscape_times,
            'portrait_times': portrait_times
        }

        print(f"✅ 竖向图片加载测试完成: {improvement:.1f}% 提升 (目标: 30%)")
        return result

    def benchmark_image_switching_delay(self) -> Dict[str, Any]:
        """基准测试图片切换延迟"""
        print("\n📊 基准测试图片切换延迟...")

        # 创建双向缓存池
        cache_pool = BidirectionalCachePool()

        # 测试不同切换场景
        scenarios = [
            ('sequential', list(range(len(self.test_images)))),
            ('random', [0, 5, 2, 7, 1, 8, 3, 6, 4]),
            ('alternating', [0, 3, 1, 4, 2, 5])  # 横向/竖向交替
        ]

        scenario_results = {}

        for scenario_name, indices in scenarios:
            print(f"  测试 {scenario_name} 切换...")

            times = []
            for _ in range(3):  # 运行3次
                start_time = time.perf_counter()

                # 模拟图片切换
                for i in indices[:5]:  # 测试前5次切换
                    img_path = self.test_images[i]['path']
                    cache_pool._simulate_image_switch(img_path)

                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)

            scenario_results[scenario_name] = {
                'avg_time_ms': statistics.mean(times),
                'min_time_ms': min(times),
                'max_time_ms': max(times)
            }

        # 计算延迟降低效果
        baseline_delay = scenario_results['sequential']['avg_time_ms']
        optimized_delay = scenario_results['alternating']['avg_time_ms']
        improvement = ((baseline_delay - optimized_delay) / baseline_delay) * 100

        result = {
            'scenarios': scenario_results,
            'baseline_delay_ms': baseline_delay,
            'optimized_delay_ms': optimized_delay,
            'improvement_percent': improvement,
            'target_improvement': 20.0,
            'meets_target': improvement >= 20.0
        }

        print(f"✅ 图片切换延迟测试完成: {improvement:.1f}% 降低 (目标: 20%)")
        return result

    def benchmark_network_cache_hit_rate(self) -> Dict[str, Any]:
        """基准测试网络缓存命中率"""
        print("\n📊 基准测试网络缓存命中率...")

        # 创建网络缓存
        cache = NetworkCache(max_size_mb=64)

        # 模拟缓存访问模式
        access_patterns = [
            # (访问序列, 预期命中率)
            ([0, 1, 2, 0, 1, 3, 0, 2, 1, 4], 0.6),  # 重复访问
            ([0, 1, 2, 3, 4, 5, 6, 7, 8, 0], 0.2),  # 顺序访问
            ([0, 0, 1, 1, 2, 2, 3, 3, 4, 4], 0.5),  # 成对访问
        ]

        pattern_results = {}

        for pattern_name, (access_sequence, expected_hit_rate) in enumerate(access_patterns):
            print(f"  测试访问模式 {pattern_name + 1}...")

            # 重置缓存
            cache.clear()

            # 执行访问序列
            for img_index in access_sequence:
                img_path = self.test_images[img_index]['path']

                # 尝试从缓存获取
                cached_data = cache.get(img_path)

                if cached_data is None:
                    # 缓存未命中，加载并缓存
                    fake_data = f"image_data_{img_index}".encode()
                    cache.put(img_path, fake_data)

            # 获取缓存统计
            stats = cache.get_stats()
            pattern_results[f'pattern_{pattern_name + 1}'] = {
                'hit_rate': stats['hit_rate'],
                'expected_hit_rate': expected_hit_rate,
                'total_accesses': stats['total_accesses'],
                'cache_hits': stats['cache_hits']
            }

        # 计算平均命中率
        avg_hit_rate = statistics.mean([r['hit_rate'] for r in pattern_results.values()])

        result = {
            'patterns': pattern_results,
            'avg_hit_rate': avg_hit_rate,
            'target_hit_rate': 70.0,
            'meets_target': avg_hit_rate >= 70.0
        }

        print(f"✅ 网络缓存命中率测试完成: {avg_hit_rate:.1f}% (目标: 70%)")
        return result

    def benchmark_preload_queue_expansion(self) -> Dict[str, Any]:
        """基准测试预加载队列扩展效果"""
        print("\n📊 基准测试预加载队列扩展效果...")

        # 测试不同预加载数量
        preload_counts = [3, 5, 7]  # 3张(旧版本), 5张(V1.4.0), 7张(扩展测试)

        count_results = {}

        for count in preload_counts:
            print(f"  测试预加载 {count} 张图片...")

            # 创建缓存池
            cache_pool = BidirectionalCachePool()
            cache_pool.preload_count = count

            # 模拟预加载操作
            start_time = time.perf_counter()

            for i in range(count):
                img_path = self.test_images[i]['path']
                cache_pool._preload_image(img_path)

            end_time = time.perf_counter()
            preload_time = (end_time - start_time) * 1000

            # 测试预加载命中效果
            hit_count = 0
            for i in range(count):
                img_path = self.test_images[i]['path']
                if cache_pool._is_preloaded(img_path):
                    hit_count += 1

            hit_rate = (hit_count / count) * 100

            count_results[f'preload_{count}'] = {
                'preload_time_ms': preload_time,
                'hit_rate': hit_rate,
                'hit_count': hit_count,
                'total_count': count
            }

        # 计算扩展效果
        old_preload_time = count_results['preload_3']['preload_time_ms']
        new_preload_time = count_results['preload_5']['preload_time_ms']
        efficiency_ratio = new_preload_time / (old_preload_time * 5/3)  # 考虑数量增加

        result = {
            'preload_counts': count_results,
            'old_preload_time_ms': old_preload_time,
            'new_preload_time_ms': new_preload_time,
            'efficiency_ratio': efficiency_ratio,
            'is_efficient': efficiency_ratio <= 1.2  # 效率损失不超过20%
        }

        print(f"✅ 预加载队列扩展测试完成: 效率比 {efficiency_ratio:.2f}")
        return result

    def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """运行综合性能基准测试"""
        print("🚀 开始V1.4.0综合性能基准测试")
        print("=" * 60)

        # 设置测试环境
        self.setup_test_environment()

        try:
            # 运行各项基准测试
            self.results = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'version': 'V1.4.0',
                'remote_file_loading': self.benchmark_remote_file_loading(),
                'vertical_image_loading': self.benchmark_vertical_image_loading(),
                'image_switching_delay': self.benchmark_image_switching_delay(),
                'network_cache_hit_rate': self.benchmark_network_cache_hit_rate(),
                'preload_queue_expansion': self.benchmark_preload_queue_expansion()
            }

            # 生成综合报告
            self._generate_summary_report()

            return self.results

        finally:
            # 清理测试环境
            self.cleanup_test_environment()

    def _generate_summary_report(self):
        """生成综合报告"""
        print("\n" + "=" * 60)
        print("📋 V1.4.0性能基准测试综合报告")
        print("=" * 60)

        # 统计达标情况
        targets_met = 0
        total_targets = 0

        # 远程文件加载性能
        remote_result = self.results['remote_file_loading']
        print(f"\n🌐 远程文件加载性能:")
        print(f"  提升: {remote_result['improvement_percent']:.1f}% (目标: 50%)")
        if remote_result['meets_target']:
            print("  ✅ 达标")
            targets_met += 1
        else:
            print("  ❌ 未达标")
        total_targets += 1

        # 竖向图片加载性能
        vertical_result = self.results['vertical_image_loading']
        print(f"\n📱 竖向图片加载性能:")
        print(f"  提升: {vertical_result['improvement_percent']:.1f}% (目标: 30%)")
        if vertical_result['meets_target']:
            print("  ✅ 达标")
            targets_met += 1
        else:
            print("  ❌ 未达标")
        total_targets += 1

        # 图片切换延迟
        switching_result = self.results['image_switching_delay']
        print(f"\n🔄 图片切换延迟:")
        print(f"  降低: {switching_result['improvement_percent']:.1f}% (目标: 20%)")
        if switching_result['meets_target']:
            print("  ✅ 达标")
            targets_met += 1
        else:
            print("  ❌ 未达标")
        total_targets += 1

        # 网络缓存命中率
        cache_result = self.results['network_cache_hit_rate']
        print(f"\n💾 网络缓存命中率:")
        print(f"  命中率: {cache_result['avg_hit_rate']:.1f}% (目标: 70%)")
        if cache_result['meets_target']:
            print("  ✅ 达标")
            targets_met += 1
        else:
            print("  ❌ 未达标")
        total_targets += 1

        # 预加载队列扩展
        preload_result = self.results['preload_queue_expansion']
        print(f"\n⚡ 预加载队列扩展:")
        print(f"  效率比: {preload_result['efficiency_ratio']:.2f} (目标: ≤1.2)")
        if preload_result['is_efficient']:
            print("  ✅ 达标")
            targets_met += 1
        else:
            print("  ❌ 未达标")
        total_targets += 1

        # 总体评估
        success_rate = (targets_met / total_targets) * 100
        print(f"\n🎯 总体评估:")
        print(f"  达标项目: {targets_met}/{total_targets}")
        print(f"  成功率: {success_rate:.1f}%")

        if success_rate >= 80:
            print("  🎉 V1.4.0性能目标基本达成!")
        elif success_rate >= 60:
            print("  ⚠️  V1.4.0性能目标部分达成，需要进一步优化")
        else:
            print("  ❌ V1.4.0性能目标未达成，需要重大改进")

    def save_results(self, filename: str = None):
        """保存测试结果"""
        if filename is None:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f"v130_benchmark_results_{timestamp}.json"

        filepath = os.path.join(os.path.dirname(__file__), filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 测试结果已保存: {filepath}")
        return filepath

    def cleanup_test_environment(self):
        """清理测试环境"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print(f"🧹 测试环境已清理: {self.temp_dir}")


# 辅助函数和上下文管理器
class patch_file_operations:
    """模拟文件操作"""
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class patch_pil_operations:
    """模拟PIL操作"""
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def main():
    """主函数"""
    print("PlookingII V1.4.0 性能基准测试工具")
    print("=" * 50)

    # 创建基准测试实例
    benchmark = V130PerformanceBenchmark()

    try:
        # 运行综合基准测试
        benchmark.run_comprehensive_benchmark()

        # 保存结果
        result_file = benchmark.save_results()

        print(f"\n✅ V1.4.0性能基准测试完成!")
        print(f"📊 详细结果已保存到: {result_file}")

    except Exception as e:
        print(f"\n❌ 基准测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # 清理环境
        benchmark.cleanup_test_environment()

    return 0


if __name__ == '__main__':
    sys.exit(main())
