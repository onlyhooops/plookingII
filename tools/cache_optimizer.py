#!/usr/bin/env python3
"""
缓存优化工具

分析缓存性能，优化缓存策略，提升缓存命中率和整体性能。
"""

import os
import sys
import random
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class CacheSimulator:
    """缓存模拟器"""

    def __init__(self, max_size: int = 100, strategy: str = 'lru'):
        self.max_size = max_size
        self.strategy = strategy
        self.cache = {}
        self.access_order = deque()
        self.access_count = defaultdict(int)
        self.hits = 0
        self.misses = 0
        self.total_requests = 0

    def get(self, key: str) -> Optional[Any]:
        """获取缓存项"""
        self.total_requests += 1

        if key in self.cache:
            self.hits += 1
            self.access_count[key] += 1

            # 更新访问顺序
            if self.strategy == 'lru':
                if key in self.access_order:
                    self.access_order.remove(key)
                self.access_order.append(key)

            return self.cache[key]
        else:
            self.misses += 1
            return None

    def put(self, key: str, value: Any) -> bool:
        """添加缓存项"""
        if key in self.cache:
            # 更新现有项
            self.cache[key] = value
            if self.strategy == 'lru':
                if key in self.access_order:
                    self.access_order.remove(key)
                self.access_order.append(key)
            return True

        # 检查是否需要驱逐
        if len(self.cache) >= self.max_size:
            self._evict()

        # 添加新项
        self.cache[key] = value
        if self.strategy == 'lru':
            self.access_order.append(key)

        return True

    def _evict(self):
        """驱逐缓存项"""
        if not self.cache:
            return

        if self.strategy == 'lru':
            # LRU: 驱逐最久未使用的项
            if self.access_order:
                oldest_key = self.access_order.popleft()
                if oldest_key in self.cache:
                    del self.cache[oldest_key]
        elif self.strategy == 'lfu':
            # LFU: 驱逐使用频率最低的项
            least_frequent_key = min(self.cache.keys(),
                                   key=lambda k: self.access_count[k])
            del self.cache[least_frequent_key]
        elif self.strategy == 'random':
            # 随机驱逐
            key_to_remove = random.choice(list(self.cache.keys()))
            del self.cache[key_to_remove]

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        hit_rate = (self.hits / self.total_requests * 100) if self.total_requests > 0 else 0

        return {
            'total_requests': self.total_requests,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'cache_size': len(self.cache),
            'max_size': self.max_size,
            'strategy': self.strategy
        }


class CacheOptimizer:
    """缓存优化器"""

    def __init__(self):
        self.optimization_results = []

    def test_cache_strategies(self, access_pattern: List[str],
                            cache_sizes: List[int] = [50, 100, 200]) -> Dict[str, Any]:
        """测试不同缓存策略的性能"""
        strategies = ['lru', 'lfu', 'random']
        results = {}

        print("Testing cache strategies...")

        for strategy in strategies:
            results[strategy] = {}

            for cache_size in cache_sizes:
                print(f"  Testing {strategy} with size {cache_size}...")

                # 创建缓存模拟器
                cache = CacheSimulator(max_size=cache_size, strategy=strategy)

                # 模拟访问模式
                for key in access_pattern:
                    # 尝试获取
                    value = cache.get(key)
                    if value is None:
                        # 缓存未命中，添加项
                        cache.put(key, f"value_{key}")

                # 记录结果
                stats = cache.get_stats()
                results[strategy][cache_size] = stats

        return results

    def analyze_access_patterns(self, access_pattern: List[str]) -> Dict[str, Any]:
        """分析访问模式"""
        # 计算访问频率
        access_count = defaultdict(int)
        for key in access_pattern:
            access_count[key] += 1

        # 计算访问模式特征
        total_accesses = len(access_pattern)
        unique_keys = len(access_count)

        # 计算重复率
        repeated_accesses = sum(count - 1 for count in access_count.values() if count > 1)
        repeat_rate = repeated_accesses / total_accesses if total_accesses > 0 else 0

        # 计算访问集中度（前20%的键占总访问的比例）
        sorted_counts = sorted(access_count.values(), reverse=True)
        top_20_percent = int(unique_keys * 0.2)
        top_20_accesses = sum(sorted_counts[:top_20_percent])
        concentration = top_20_accesses / total_accesses if total_accesses > 0 else 0

        # 计算时间局部性（连续访问相同键的比例）
        temporal_locality = 0
        for i in range(1, len(access_pattern)):
            if access_pattern[i] == access_pattern[i-1]:
                temporal_locality += 1
        temporal_locality = temporal_locality / (len(access_pattern) - 1) if len(access_pattern) > 1 else 0

        return {
            'total_accesses': total_accesses,
            'unique_keys': unique_keys,
            'repeat_rate': repeat_rate,
            'concentration': concentration,
            'temporal_locality': temporal_locality,
            'top_access_counts': sorted_counts[:10]  # 前10个最常访问的键的访问次数
        }

    def generate_optimization_suggestions(self, results: Dict[str, Any],
                                        access_analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """生成优化建议"""
        suggestions = []

        # 找到最佳策略
        best_strategy = None
        best_hit_rate = 0

        for strategy, strategy_results in results.items():
            for cache_size, stats in strategy_results.items():
                if stats['hit_rate'] > best_hit_rate:
                    best_hit_rate = stats['hit_rate']
                    best_strategy = strategy

        if best_strategy:
            suggestions.append({
                'type': 'cache_strategy',
                'priority': 'high',
                'description': f"Best cache strategy is {best_strategy.upper()} with {best_hit_rate:.1f}% hit rate",
                'action': f"Implement {best_strategy.upper()} cache replacement strategy"
            })

        # 基于访问模式分析的建议
        if access_analysis['repeat_rate'] > 0.7:
            suggestions.append({
                'type': 'high_repeat_rate',
                'priority': 'medium',
                'description': f"High repeat rate ({access_analysis['repeat_rate']:.1%}) indicates good cache potential",
                'action': 'Increase cache size to capture more repeated accesses'
            })

        if access_analysis['concentration'] > 0.8:
            suggestions.append({
                'type': 'high_concentration',
                'priority': 'medium',
                'description': f"High access concentration ({access_analysis['concentration']:.1%}) in top 20% of keys",
                'action': 'Consider implementing hot/cold cache separation'
            })

        if access_analysis['temporal_locality'] > 0.3:
            suggestions.append({
                'type': 'temporal_locality',
                'priority': 'low',
                'description': f"Good temporal locality ({access_analysis['temporal_locality']:.1%})",
                'action': 'Consider implementing prefetching for recently accessed items'
            })

        return suggestions

    def optimize_cache_size(self, access_pattern: List[str],
                          strategy: str = 'lru') -> Dict[str, Any]:
        """优化缓存大小"""
        print(f"Optimizing cache size for {strategy} strategy...")

        # 测试不同缓存大小
        cache_sizes = [10, 25, 50, 100, 200, 500]
        results = {}

        for size in cache_sizes:
            cache = CacheSimulator(max_size=size, strategy=strategy)

            for key in access_pattern:
                value = cache.get(key)
                if value is None:
                    cache.put(key, f"value_{key}")

            stats = cache.get_stats()
            results[size] = stats

        # 找到最佳缓存大小（性价比最高的点）
        best_size = None
        best_efficiency = 0

        for size, stats in results.items():
            # 效率 = 命中率 / (缓存大小 / 100)
            efficiency = stats['hit_rate'] / (size / 100)
            if efficiency > best_efficiency:
                best_efficiency = efficiency
                best_size = size

        return {
            'best_size': best_size,
            'best_efficiency': best_efficiency,
            'results': results
        }


def generate_access_patterns() -> Dict[str, List[str]]:
    """生成不同的访问模式用于测试"""
    patterns = {}

    # 1. 随机访问模式
    keys = [f"key_{i}" for i in range(100)]
    random_pattern = [random.choice(keys) for _ in range(1000)]
    patterns['random'] = random_pattern

    # 2. 热点访问模式（80/20规则）
    hot_keys = keys[:20]  # 前20个键
    cold_keys = keys[20:]  # 后80个键

    hot_pattern = []
    for _ in range(1000):
        if random.random() < 0.8:  # 80%访问热点
            hot_pattern.append(random.choice(hot_keys))
        else:  # 20%访问冷点
            hot_pattern.append(random.choice(cold_keys))
    patterns['hotspot'] = hot_pattern

    # 3. 顺序访问模式
    sequential_pattern = []
    for _ in range(10):  # 重复10次
        sequential_pattern.extend(keys)
    patterns['sequential'] = sequential_pattern

    # 4. 时间局部性模式（最近访问的项更可能被再次访问）
    temporal_pattern = []
    recent_keys = deque(maxlen=10)

    for _ in range(1000):
        if recent_keys and random.random() < 0.6:  # 60%访问最近访问的项
            temporal_pattern.append(random.choice(list(recent_keys)))
        else:  # 40%访问新项
            new_key = random.choice(keys)
            temporal_pattern.append(new_key)
            recent_keys.append(new_key)
    patterns['temporal'] = temporal_pattern

    return patterns


def main():
    """主函数"""
    print("PlookingII Cache Optimizer")
    print("=" * 40)

    optimizer = CacheOptimizer()

    # 生成访问模式
    print("Generating access patterns...")
    patterns = generate_access_patterns()

    # 分析每种访问模式
    for pattern_name, access_pattern in patterns.items():
        print(f"\nAnalyzing {pattern_name} access pattern...")

        # 分析访问模式特征
        access_analysis = optimizer.analyze_access_patterns(access_pattern)
        print(f"  Total accesses: {access_analysis['total_accesses']}")
        print(f"  Unique keys: {access_analysis['unique_keys']}")
        print(f"  Repeat rate: {access_analysis['repeat_rate']:.1%}")
        print(f"  Concentration: {access_analysis['concentration']:.1%}")
        print(f"  Temporal locality: {access_analysis['temporal_locality']:.1%}")

        # 测试缓存策略
        results = optimizer.test_cache_strategies(access_pattern)

        # 显示最佳策略
        best_hit_rate = 0
        best_strategy = None
        best_size = None

        for strategy, strategy_results in results.items():
            for size, stats in strategy_results.items():
                if stats['hit_rate'] > best_hit_rate:
                    best_hit_rate = stats['hit_rate']
                    best_strategy = strategy
                    best_size = size

        print(f"  Best strategy: {best_strategy} (size {best_size}) with {best_hit_rate:.1f}% hit rate")

        # 生成优化建议
        suggestions = optimizer.generate_optimization_suggestions(results, access_analysis)

        if suggestions:
            print(f"  Optimization suggestions:")
            for suggestion in suggestions:
                print(f"    [{suggestion['priority'].upper()}] {suggestion['description']}")

    # 优化缓存大小
    print(f"\nOptimizing cache size for LRU strategy...")
    size_optimization = optimizer.optimize_cache_size(patterns['hotspot'], 'lru')

    print(f"Best cache size: {size_optimization['best_size']}")
    print(f"Best efficiency: {size_optimization['best_efficiency']:.2f}")

    print("\n✅ Cache optimization analysis completed!")


if __name__ == "__main__":
    main()
