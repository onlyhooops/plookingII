# PlookingII 项目维护准则

本文档为PlookingII项目的官方维护准则，旨在确保项目的长期健康发展，维护代码质量，保持文档整洁，规范开发流程。所有项目维护者和贡献者必须严格遵循本准则。

**版本**: v1.4.0  
**制定日期**: 2025年9月25日  
**最后更新**: 2025年9月30日 (完善文档维护指南与存放规则)  
**适用范围**: 所有项目维护和开发工作  
**执行级别**: 强制性

---

## 📚 1. 项目文档维护规则

### 1.1 文档更新原则

#### 🎯 核心原则
- **同步性**: 代码变更必须同步更新相关文档
- **准确性**: 文档内容必须与实际实现100%一致
- **简洁性**: 避免冗余和重复，保持文档精练
- **实用性**: 文档必须为用户和开发者提供实际价值

#### 📋 文档分类管理

**核心文档 (禁止随意修改)**:
```
├── README.md                      # 项目主入口文档
├── PROJECT_OVERVIEW.md            # 项目综述文档
├── TECHNICAL_GUIDE.md             # 技术指南文档
├── VERSION_HISTORY.md             # 版本历史文档
├── DOCUMENTATION_INDEX.md         # 文档索引导航
└── MAINTENANCE_GUIDELINES.md      # 维护准则文档
```

**变更记录文档 (可追加更新)**:
```
├── CHANGELOG.md                         # 主要变更记录（按时间顺序）
├── VERSION_HISTORY.md                   # 版本发展历程（累加）
├── RELEASE_HISTORY.md                   # 统一的发布历史（累加）
└── doc/reports/                         # 报告与专项分析归档（人工）
    ├── refactoring/                     # 重构类报告
    ├── technical_debt/                  # 技术债类报告
    ├── performance/                     # 性能类报告
    └── generated/                       # 自动生成报告（依赖、覆盖率、基线等）
```

**架构文档 (重大变更时更新)**:
```
└── doc/ARCHITECTURE.md           # 系统架构文档
```

### 1.2 文档新增规则

#### ✅ 允许新增的文档类型
1. **临时维护报告**: 格式为 `[TYPE]_[DATE]_REPORT.md`
   - 示例: `PERFORMANCE_2025-09-20_REPORT.md`
   - 生命周期: 完成后整合到主要文档或删除

2. **功能说明文档**: 重大新功能的详细说明
   - 位置: `doc/features/` 目录
   - 命名: `FEATURE_[功能名]_GUIDE.md`

3. **API文档**: 新增API接口的详细文档
   - 位置: `doc/api/` 目录
   - 命名: `API_[模块名]_REFERENCE.md`

4. **报告文档**: 重构、技术债、性能、热修复等专题报告
   - 位置: `doc/reports/<category>/`（`refactoring|technical_debt|performance`）
   - 命名: `<TOPIC>_[vX.Y.Z|YYYYMMDD].md`（禁止使用逐版本的 Release Notes 文件）

#### ❌ 禁止新增的文档类型
1. **重复性文档**: 与现有文档内容重叠
2. **临时笔记**: 个人开发笔记和草稿
3. **版本特定文档**: 如 `RELEASE_NOTES_vX.X.X.md`
4. **分散的修复记录**: 应整合到统一报告中

### 1.3 文档清理要求

#### 🧹 定期清理机制
- **每个版本发布前**: 清理临时文档和过时内容
- **每季度**: 审查文档结构和内容准确性
- **重大重构后**: 全面更新相关技术文档

#### 🗑️ 清理标准
```python
# 文档清理检查清单
清理标准 = {
    "过时内容": "超过2个版本未更新的技术描述",
    "重复信息": "多个文档包含相同信息",
    "失效链接": "指向不存在文件或URL的链接", 
    "格式不一致": "不符合项目文档格式标准",
    "临时文件": "超过30天的临时维护报告"
}
```

### 1.5 目录结构与存放规则（强制）

- 核心入口类文档：根目录（`README.md`、`PROJECT_OVERVIEW.md`、`TECHNICAL_GUIDE.md`、`DEVELOPER_GUIDE.md`、`DOCUMENTATION_INDEX.md`、`MAINTENANCE_GUIDELINES.md`）。
- 版本与变更：根目录（`CHANGELOG.md`、`VERSION_HISTORY.md`、`RELEASE_HISTORY.md`）。
- 报告与专项分析：`doc/reports/` 下分门类归档（`refactoring/`、`technical_debt/`、`performance/`、`generated/`）。
- 架构与专题：`doc/`（如 `doc/ARCHITECTURE.md`、`doc/features/`、`doc/api/`）。
- 生成产物：一律归档到 `doc/reports/generated/`，不得提交到根目录。

### 1.6 单一事实来源（Single Source of Truth）

| 信息类型 | 唯一来源 | 备注 |
|---|---|---|
| 版本发布历史 | `RELEASE_HISTORY.md` | 不再维护逐版本 Release Notes 文件 |
| 版本发展轨迹 | `VERSION_HISTORY.md` | 必须累加更新 |
| 变更记录 | `CHANGELOG.md` | 仅记录变更摘要，不重复长文描述 |
| 报告与复盘 | `doc/reports/**` | 以专题归档，不与上面三者重复 |
| 文档导航 | `DOCUMENTATION_INDEX.md` | 新增/移动文档后必须同步更新 |

### 1.7 重复检测与合并流程

1. 新增文档前：在仓库内搜索关键词与主题，确认无重复。
2. 若与现有文档部分重叠：
   - 将新增内容合并进“唯一来源”文档或对应专题报告；
   - 在原文档中添加“更新于 ×××”的注记与链接；
3. 若发现既有重复：优先保留“唯一来源”，其余文件按“废弃策略”处理。

### 1.8 文档废弃与删除策略

- 标记废弃：在文档顶部添加“Deprecated since vX.Y.Z，参见 <新文档路径>”。
- 迁移期：默认保留 30 天；期间更新索引指向新文档。
- 到期处理：删除废弃文档，提交说明引用到新文档的 PR 描述。

### 1.9 PR 文档检查清单（必过项）

- [ ] 变更是否需要更新 `CHANGELOG.md`？
- [ ] 若涉及版本发布，是否更新 `RELEASE_HISTORY.md` 与 `VERSION_HISTORY.md`？
- [ ] 文档是否按“目录结构与存放规则”存放？
- [ ] `DOCUMENTATION_INDEX.md` 是否已同步更新链接？
- [ ] 是否检查并避免与现有文档重复/相似？

### 1.4 文档质量标准

#### 📝 内容要求
- **语言**: 统一使用简体中文
- **术语**: 使用项目标准术语表
- **格式**: 遵循Markdown格式规范
- **结构**: 清晰的标题层次和段落组织

#### 🔗 链接管理
- **内部链接**: 使用相对路径
- **外部链接**: 定期检查有效性
- **引用格式**: 统一的引用格式和标注

---

## 🏗️ 2. 代码架构维护规范

### 2.1 架构稳定性原则

#### 🔒 核心架构保护
**严禁破坏的核心实现**:
```python
# 受保护的核心架构
核心架构 = {
    "MVC模式": "不得改变Model-View-Controller的基本架构",
    "Quartz-only": "未经批准不得重新引入其他图像处理依赖", 
    "缓存系统": "未经批准不得破坏缓存架构的基本设计",
    "线程模型": "未经批准不得改变主线程UI更新的安全模式",
    "API接口": "未经批准不得破坏现有公共API的向后兼容性",
    "快捷键设置": "🚨 严禁未经许可修改用户快捷键设置"
}
```

#### 🚨 **快捷键保护声明** (v1.2.2新增)

**⛔ 严禁修改快捷键设置**:
PlookingII的快捷键设置是用户体验的核心组成部分，**严禁未经明确许可修改任何快捷键设置**。

**受保护的快捷键列表**:
```
应用程序菜单:
- Cmd+H: 隐藏应用程序
- Cmd+M: 最小化窗口
- Cmd+Q: 退出程序

文件菜单:
- Cmd+O: 打开文件夹

编辑菜单:
- Cmd+Z: 撤销保留操作
- Cmd+C: 复制图片路径
- Cmd+Option+R: 向右旋转90°
- Cmd+Option+L: 向左旋转90°

前往菜单:
- Cmd+R: 在Finder中显示

导航快捷键:
- ←/→: 图片导航
- ↓: 保留图片
- Cmd+←/→: 文件夹跳转
- Cmd+Z: 撤销保留
- ESC: 退出当前文件夹
```

**快捷键变更审批流程**:
1. **提案阶段**: 提交详细的快捷键变更提案，说明变更原因和用户影响
2. **用户调研**: 进行用户调研，评估用户接受度
3. **兼容性评估**: 评估与系统快捷键和其他应用的冲突
4. **渐进迁移**: 如必须变更，需提供渐进迁移方案
5. **文档更新**: 更新所有相关文档和帮助信息

**违规后果**:
- 🚨 **立即回滚**: 发现快捷键变更立即回滚
- 📝 **记录违规**: 在维护日志中记录违规行为
- 🔍 **流程检查**: 检查和完善质量保证流程
- 📚 **团队培训**: 对团队进行快捷键保护培训

#### ⚡ 性能调优允许范围

**视图层调优 (允许)**:
- ✅ 优化渲染算法和绘制性能
- ✅ 改进缩放和平移算法
- ✅ 优化内存使用和资源管理
- ✅ 增强用户交互响应性

**核心层调优 (允许)**:
- ✅ 优化图像加载策略
- ✅ 改进缓存命中率和淘汰算法
- ✅ 优化并发处理和线程池
- ✅ 增强性能监控和自适应调优

### 2.2 架构变更审批流程

#### 📋 变更分类
```python
变更级别 = {
    "微调": "不影响接口的内部优化",      # 无需审批
    "改进": "向后兼容的功能增强",        # 需要评审
    "重构": "影响模块结构的重大变更",    # 需要批准
    "革命": "改变核心架构的变更"         # 禁止执行
}
```

#### 🔍 变更检查清单
- [ ] 是否保持API向后兼容性？
- [ ] 是否破坏现有功能？
- [ ] 是否影响性能指标？
- [ ] 是否需要更新文档？
- [ ] 是否通过所有测试？

### 2.3 性能基准保护

#### 📊 性能指标底线
```python
性能基准 = {
    "启动时间": "≤ 2秒",
    "内存使用": "≤ 500MB峰值",
    "图像加载": "小文件 ≤ 100ms",
    "缓存命中率": "≥ 80%",
    "CPU使用率": "≤ 20%平均"
}
```

**性能退化处理**:
1. **轻微退化 (5-10%)**: 记录并计划优化
2. **明显退化 (10-20%)**: 必须在当前版本修复
3. **严重退化 (>20%)**: 立即回滚变更

---

## 🔢 3. 版本号管理规范

### 3.1 语义化版本控制

#### 📋 版本号格式
```
v<主版本号>.<次版本号>.<修订号>[-预发布标识][+构建元数据]

示例:
- v1.0.0        # 正式版本
- v1.1.0-beta.1 # 预发布版本
- v1.0.1+20250920 # 带构建信息
```

#### 🎯 版本号递增规则

**主版本号 (MAJOR)** - 不兼容的API修改:
- 架构重大重构
- 移除已弃用功能
- API接口破坏性变更
- 最低系统要求提升

**次版本号 (MINOR)** - 向下兼容的功能性新增:
- 新增功能模块
- API功能扩展
- 性能重大改进
- 用户体验优化

**修订号 (PATCH)** - 向下兼容的问题修正:
- Bug修复
- 安全补丁
- 文档更新
- 代码清理

### 3.2 自动版本生成规则

#### 🤖 自动递增逻辑
```python
def auto_increment_version(current_version: str, change_type: str) -> str:
    """
    根据变更类型自动递增版本号
    
    Args:
        current_version: 当前版本号 (如 "1.4.0")
        change_type: 变更类型 ("major"|"minor"|"patch")
    
    Returns:
        新版本号
    """
    major, minor, patch = map(int, current_version.split('.'))
    
    if change_type == "major":
        return f"{major + 1}.0.0"
    elif change_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif change_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"无效的变更类型: {change_type}")
```

#### 🔍 变更类型识别
```python
变更类型识别规则 = {
    "major": [
        "移除公共API",
        "修改核心架构",
        "破坏向后兼容性",
        "提升最低系统要求"
    ],
    "minor": [
        "新增公共API",
        "新增功能模块", 
        "显著性能改进",
        "用户体验优化"
    ],
    "patch": [
        "修复Bug",
        "安全补丁",
        "文档更新",
        "代码重构"
    ]
}
```

### 3.3 版本号验证机制

#### ✅ 合规版本号
```python
import re

def validate_version(version: str) -> bool:
    """验证版本号是否符合语义化版本规范"""
    pattern = r'^v?(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?(?:\+([a-zA-Z0-9\-\.]+))?$'
    return bool(re.match(pattern, version))

# 合规示例
合规版本号 = [
    "v1.0.0",
    "v2.1.3", 
    "v1.0.0-alpha.1",
    "v1.0.0-beta.2",
    "v1.0.0-rc.1",
    "v1.0.0+20250920"
]
```

#### ❌ 不合规处理
```python
def handle_invalid_version(version: str) -> str:
    """处理不合规版本号"""
    error_msg = f"""
    错误: 版本号 '{version}' 不符合语义化版本规范
    
    正确格式: v<主版本号>.<次版本号>.<修订号>
    示例: v1.0.0, v2.1.3, v1.0.0-beta.1
    
    请使用以下命令生成正确版本号:
    python tools/version.py --auto-increment [major|minor|patch]
    """
    raise ValueError(error_msg)
```

### 3.4 版本发布流程

#### 📋 发布检查清单
- [ ] 版本号符合语义化规范
- [ ] 所有测试通过
- [ ] 文档已更新
- [ ] 变更日志已记录
- [ ] 性能基准未退化
- [ ] 代码质量检查通过

#### 🔄 发布后处理
1. **更新VERSION_HISTORY.md**: 记录新版本信息
2. **更新CHANGELOG.md**: 添加变更摘要
3. **标记Git标签**: 创建版本标签
4. **通知相关方**: 发送版本发布通知

---

## 📝 4. 注释规范要求

### 4.1 注释语言和格式

#### 🌏 语言要求
- **统一语言**: 所有注释必须使用简体中文
- **术语标准**: 使用项目标准术语表
- **表达清晰**: 避免模糊和歧义的表述

#### 📋 注释格式标准
```python
# 文件头注释模板
"""
模块名称: 图像处理核心模块
文件路径: plookingII/core/image_processing.py
创建时间: 2024-09-15
最后修改: 2025-09-20
作者: PlookingII Team
版本: v1.0.0

模块描述:
    实现基于Quartz的图像处理功能，包括图像加载、旋转、缓存管理等核心功能。
    采用策略模式支持多种图像处理策略，确保高性能和可扩展性。

主要类:
    - HybridImageProcessor: 混合图像处理器
    - ImageRotationProcessor: 图像旋转处理器
    - ProcessingStatistics: 处理统计信息

依赖:
    - AppKit: macOS原生UI框架
    - Quartz: 图像处理框架
    
注意事项:
    - 所有图像处理必须在后台线程进行
    - UI更新必须回调到主线程
    - 异常情况需要优雅降级
"""

class HybridImageProcessor:
    """混合图像处理器
    
    集成多种图像处理策略，提供统一的图像处理接口。支持Quartz-only
    处理模式，具备自动EXIF方向修正和性能监控功能。
    
    设计模式:
        - 策略模式: 支持多种加载策略
        - 工厂模式: 动态创建处理器实例
        - 观察者模式: 性能监控和统计
    
    属性:
        rotation_processor (ImageRotationProcessor): 图像旋转处理器
        statistics (ProcessingStatistics): 处理统计信息
        loading_strategies (dict): 可用的加载策略字典
    
    示例:
        >>> processor = HybridImageProcessor()
        >>> image = processor.load_image_quartz_only("/path/to/image.jpg")
        >>> success = processor.rotate_image("/path/to/image.jpg", 90)
    """
    
    def __init__(self):
        """初始化混合图像处理器
        
        创建图像旋转处理器实例和统计信息收集器，初始化可用的
        图像加载策略字典。
        """
        self.rotation_processor = ImageRotationProcessor()
        self.statistics = ProcessingStatistics()
        self._init_loading_strategies()
    
    def load_image_quartz_only(self, file_path: str, target_size: tuple = None) -> Optional[CGImage]:
        """使用Quartz-only模式加载图像
        
        完全基于macOS原生Quartz框架加载图像，支持自动EXIF方向修正
        和智能缩略图生成。对于大文件使用内存映射技术减少内存占用。
        
        参数:
            file_path (str): 图像文件的完整路径
            target_size (tuple, optional): 目标尺寸 (width, height)，
                                         如果为None则加载原始尺寸
        
        返回:
            Optional[CGImage]: 成功时返回CGImage对象，失败时返回None
        
        异常:
            ValueError: 当文件路径无效时抛出
            IOError: 当文件读取失败时抛出
        
        性能说明:
            - 小文件 (< 10MB): 直接加载，预期时间 < 100ms
            - 大文件 (≥ 10MB): 使用内存映射，预期时间 < 500ms
            - 超大文件 (> 100MB): 分块处理，避免内存溢出
        
        示例:
            >>> # 加载原始尺寸图像
            >>> image = processor.load_image_quartz_only("/path/to/photo.jpg")
            >>> 
            >>> # 加载指定尺寸缩略图
            >>> thumbnail = processor.load_image_quartz_only(
            ...     "/path/to/photo.jpg", 
            ...     target_size=(800, 600)
            ... )
        """
        try:
            # 参数验证
            if not file_path or not isinstance(file_path, str):
                raise ValueError(f"无效的文件路径: {file_path}")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 记录开始时间用于性能统计
            start_time = time.time()
            
            # 创建图像源 - 使用Quartz原生API
            url = NSURL.fileURLWithPath_(file_path)
            source = CGImageSourceCreateWithURL(url, None)
            
            if not source:
                raise ValueError(f"无法创建图像源: {file_path}")
            
            # 配置加载选项 - 启用EXIF自动修正
            options = {
                # 自动处理EXIF方向信息
                kCGImageSourceCreateThumbnailWithTransform: True,
                # 始终创建缩略图以优化内存使用
                kCGImageSourceCreateThumbnailFromImageAlways: True,
            }
            
            # 设置目标尺寸 - 如果指定了target_size
            if target_size:
                max_size = max(target_size)
                options[kCGImageSourceThumbnailMaxPixelSize] = max_size
                logger.debug(f"设置缩略图最大尺寸: {max_size}px")
            
            # 创建CGImage - 使用配置的选项
            image = CGImageSourceCreateThumbnailAtIndex(source, 0, options)
            
            # 降级处理 - 如果缩略图创建失败，尝试直接创建图像
            if not image:
                logger.warning(f"缩略图创建失败，尝试直接加载: {file_path}")
                image = CGImageSourceCreateImageAtIndex(source, 0, {
                    kCGImageSourceCreateThumbnailWithTransform: True
                })
            
            # 性能统计记录
            load_time = time.time() - start_time
            if image:
                self.statistics.record_success(file_path, load_time)
                logger.debug(f"图像加载成功: {file_path} ({load_time:.3f}s)")
            else:
                self.statistics.record_error(file_path, "CGImage创建失败")
                logger.error(f"图像加载失败: {file_path}")
            
            return image
            
        except Exception as e:
            # 记录错误统计信息
            self.statistics.record_error(file_path, str(e))
            logger.exception(f"图像加载异常: {file_path}")
            raise
```

### 4.2 注释覆盖要求

#### 📊 注释覆盖率标准
```python
注释覆盖要求 = {
    "公共类": "100% - 必须有完整的类文档字符串",
    "公共方法": "100% - 必须有详细的方法文档字符串", 
    "私有方法": "80% - 复杂逻辑必须注释",
    "复杂算法": "100% - 逐步解释算法逻辑",
    "配置参数": "100% - 说明参数用途和取值范围",
    "异常处理": "100% - 说明异常原因和处理方式"
}
```

#### 🎯 重点注释区域
1. **新增功能**: 所有新增代码必须有完整注释
2. **性能优化**: 详细说明优化原理和效果
3. **Bug修复**: 说明问题原因和修复方案
4. **架构调整**: 解释调整目的和影响范围
5. **复杂逻辑**: 分步骤详细解释处理流程

### 4.3 注释质量标准

#### ✅ 优质注释示例
```python
def calculate_optimal_cache_size(available_memory: int, 
                                image_count: int) -> int:
    """计算最优缓存大小
    
    基于可用内存和图像数量，使用启发式算法计算最优的缓存大小。
    算法考虑了内存压力、图像平均大小和访问模式等因素。
    
    算法逻辑:
        1. 预留系统内存 (20%) 避免内存压力
        2. 根据图像数量估算平均图像大小
        3. 应用缓存效率系数 (0.8) 考虑LRU淘汰
        4. 设置合理的上下限边界
    
    参数:
        available_memory (int): 可用内存大小，单位为字节
        image_count (int): 预期处理的图像数量
    
    返回:
        int: 建议的缓存大小，单位为图像数量
    
    边界情况:
        - available_memory < 100MB: 返回最小缓存 (10)
        - image_count == 0: 返回默认缓存 (50)
        - 计算结果 > 500: 返回最大缓存 (500)
    
    性能说明:
        时间复杂度: O(1)
        空间复杂度: O(1)
    """
    # 参数验证 - 确保输入参数合理
    if available_memory < 0:
        raise ValueError("可用内存不能为负数")
    if image_count < 0:
        raise ValueError("图像数量不能为负数")
    
    # 最小内存阈值检查 - 低于100MB时使用最小缓存
    MIN_MEMORY_THRESHOLD = 100 * 1024 * 1024  # 100MB
    if available_memory < MIN_MEMORY_THRESHOLD:
        logger.warning(f"可用内存过低 ({available_memory / 1024 / 1024:.1f}MB)，使用最小缓存")
        return 10
    
    # 预留系统内存 - 避免系统内存压力
    SYSTEM_MEMORY_RESERVE_RATIO = 0.2  # 预留20%系统内存
    usable_memory = available_memory * (1 - SYSTEM_MEMORY_RESERVE_RATIO)
    
    # 估算平均图像大小 - 基于经验值和图像数量
    if image_count == 0:
        return 50  # 默认缓存大小
    
    # 根据图像数量估算平均大小 (启发式算法)
    ESTIMATED_AVG_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB平均大小
    estimated_total_size = image_count * ESTIMATED_AVG_IMAGE_SIZE
    
    # 计算理论最大缓存数量
    max_cacheable = int(usable_memory / ESTIMATED_AVG_IMAGE_SIZE)
    
    # 应用缓存效率系数 - 考虑LRU淘汰和碎片化
    CACHE_EFFICIENCY = 0.8
    optimal_size = int(max_cacheable * CACHE_EFFICIENCY)
    
    # 应用边界限制 - 确保缓存大小在合理范围内
    MIN_CACHE_SIZE = 10   # 最小缓存
    MAX_CACHE_SIZE = 500  # 最大缓存
    optimal_size = max(MIN_CACHE_SIZE, min(optimal_size, MAX_CACHE_SIZE))
    
    logger.info(f"计算最优缓存大小: {optimal_size} "
                f"(内存: {available_memory / 1024 / 1024:.1f}MB, "
                f"图像: {image_count})")
    
    return optimal_size
```

#### ❌ 不当注释示例
```python
# 错误示例 - 避免这样的注释
def process_image(path):
    # 处理图像
    img = load_image(path)  # 加载图像
    img = resize_image(img)  # 调整大小
    return img  # 返回结果

# 正确的注释应该解释为什么，而不是重复代码做了什么
```

---

## 🧹 5. 代码清理规范

### 5.1 代码质量标准

#### 📋 代码清洁度检查清单
```python
代码质量检查 = {
    "重复代码": "相似度 > 80% 的代码块必须重构",
    "死代码": "未被引用的函数、类、变量必须删除",
    "过长函数": "函数行数 > 50 行需要拆分",
    "复杂度": "圈复杂度 > 10 需要简化",
    "命名规范": "必须使用有意义的英文命名",
    "导入清理": "删除未使用的导入语句"
}
```

#### 🔍 自动化检查工具
```bash
# 代码质量检查命令
flake8 plookingII/ --max-line-length=120 --max-complexity=10
radon cc plookingII/ --min=B  # 复杂度检查
vulture plookingII/ --min-confidence=80  # 死代码检查
```

### 5.2 重复代码处理

#### 🎯 重复代码识别标准
```python
重复代码类型 = {
    "完全重复": "完全相同的代码块 - 必须立即重构",
    "结构重复": "逻辑结构相同但细节不同 - 提取公共模式",
    "功能重复": "实现相同功能的不同方法 - 统一实现",
    "接口重复": "多个接口提供相同功能 - 合并接口"
}
```

#### ♻️ 重构策略
```python
def refactor_duplicate_code():
    """重复代码重构策略"""
    strategies = {
        "提取方法": "将重复代码提取为独立方法",
        "提取类": "将相关重复代码提取为独立类",
        "使用继承": "通过继承消除子类中的重复代码",
        "策略模式": "使用策略模式处理算法重复",
        "模板方法": "使用模板方法处理流程重复"
    }
    return strategies
```

### 5.3 错误代码修复

#### 🐛 错误代码分类
```python
错误代码类型 = {
    "语法错误": "Python语法错误 - 立即修复",
    "逻辑错误": "程序逻辑错误 - 高优先级修复",
    "性能问题": "影响性能的代码 - 计划修复",
    "安全漏洞": "安全相关问题 - 紧急修复",
    "兼容性问题": "平台兼容性问题 - 及时修复"
}
```

#### 🔧 修复优先级
1. **P0 - 紧急**: 影响系统稳定性的错误
2. **P1 - 高**: 影响核心功能的错误
3. **P2 - 中**: 影响用户体验的错误
4. **P3 - 低**: 代码质量问题

### 5.4 注释清理规范

#### 📝 注释清理标准
```python
注释清理规则 = {
    "过时注释": "与当前实现不符的注释 - 更新或删除",
    "无用注释": "显而易见的注释 - 删除",
    "错误注释": "包含错误信息的注释 - 修正",
    "重复注释": "多处重复的相同注释 - 合并",
    "格式不当": "格式不规范的注释 - 重新格式化"
}
```

#### 🧹 注释清理流程
```python
def clean_comments():
    """注释清理流程"""
    steps = [
        "1. 扫描所有源文件中的注释",
        "2. 识别过时和错误的注释内容",
        "3. 检查注释格式是否符合规范",
        "4. 验证注释与代码的一致性",
        "5. 更新或删除不当注释",
        "6. 补充缺失的重要注释"
    ]
    return steps
```

### 5.5 定期清理机制

#### 📅 清理时间表
```python
清理时间表 = {
    "每日": "自动化代码质量检查",
    "每周": "人工代码审查和清理",
    "每月": "全面的代码重构评估",
    "每季度": "架构清理和优化",
    "每半年": "技术债务全面清理"
}
```

#### 🎯 清理目标
```python
清理目标 = {
    "代码行数": "删除10%的冗余代码",
    "复杂度": "降低平均圈复杂度20%",
    "重复率": "代码重复率 < 5%",
    "覆盖率": "测试覆盖率 > 80%",
    "质量分": "代码质量评分 > 90分"
}
```

---

## 🔄 6. 维护工作流程

### 6.1 日常维护检查清单

#### 📋 每日检查项目
- [ ] 运行自动化测试套件
- [ ] 检查代码质量指标
- [ ] 审查新增代码的注释
- [ ] 验证文档与代码的一致性
- [ ] 监控系统性能指标

#### 📋 每周检查项目
- [ ] 清理临时文件和过时文档
- [ ] 更新依赖包和安全补丁
- [ ] 审查代码重复度报告
- [ ] 检查版本号管理规范性
- [ ] 评估技术债务情况

#### 📋 每月检查项目
- [ ] 全面代码质量审查
- [ ] 文档结构和内容审核
- [ ] 性能基准测试和对比
- [ ] 架构设计审查
- [ ] 用户反馈收集和分析

### 6.2 版本发布流程

#### 🚀 发布前检查
```python
def pre_release_checklist():
    """版本发布前检查清单"""
    checklist = {
        "代码质量": [
            "所有测试通过",
            "代码覆盖率达标",
            "静态分析无严重问题",
            "性能基准未退化"
        ],
        "文档更新": [
            "README.md已更新",
            "CHANGELOG.md已记录",
            "API文档已同步",
            "版本历史已更新"
        ],
        "版本管理": [
            "版本号符合规范",
            "Git标签已创建",
            "发布说明已准备",
            "回滚方案已制定"
        ]
    }
    return checklist
```

### 6.3 问题处理流程

#### 🐛 问题分类和处理
```python
问题处理流程 = {
    "紧急问题": {
        "响应时间": "2小时内",
        "处理流程": "立即修复 → 紧急发布 → 事后分析",
        "负责人": "项目负责人"
    },
    "重要问题": {
        "响应时间": "24小时内", 
        "处理流程": "评估影响 → 制定方案 → 测试修复 → 计划发布",
        "负责人": "技术负责人"
    },
    "一般问题": {
        "响应时间": "72小时内",
        "处理流程": "问题确认 → 优先级排序 → 计划修复 → 正常发布",
        "负责人": "开发团队"
    }
}
```

---

## 📊 7. 质量监控指标

### 7.1 代码质量指标

#### 📈 核心指标
```python
质量指标体系 = {
    "代码覆盖率": {
        "目标": "> 80%",
        "测量": "pytest-cov",
        "频率": "每次提交"
    },
    "代码复杂度": {
        "目标": "平均 < 5, 最大 < 10",
        "测量": "radon",
        "频率": "每日"
    },
    "代码重复率": {
        "目标": "< 5%",
        "测量": "jscpd",
        "频率": "每周"
    },
    "静态分析": {
        "目标": "0 严重问题",
        "测量": "flake8 + mypy",
        "频率": "每次提交"
    }
}
```

### 7.2 性能监控指标

#### ⚡ 性能基准
```python
性能监控指标 = {
    "启动时间": {
        "基准": "< 2秒",
        "测量方法": "自动化性能测试",
        "监控频率": "每次发布"
    },
    "内存使用": {
        "基准": "< 500MB峰值",
        "测量方法": "内存监控工具",
        "监控频率": "持续监控"
    },
    "响应时间": {
        "基准": "图像加载 < 100ms",
        "测量方法": "性能分析器",
        "监控频率": "每日测试"
    }
}
```

### 7.3 文档质量指标

#### 📚 文档评估标准
```python
文档质量指标 = {
    "完整性": "所有公共API有文档",
    "准确性": "文档与代码100%一致",
    "时效性": "文档更新滞后 < 1周",
    "可用性": "用户能在5分钟内找到所需信息"
}
```

---

## 🚨 8. 违规处理机制

### 8.1 违规行为定义

#### ❌ 严重违规行为
- 破坏核心架构设计
- 使用不符合规范的版本号
- 提交未经测试的代码
- 删除或损坏重要文档
- 绕过代码审查流程

#### ⚠️ 一般违规行为
- 代码注释不完整
- 文档更新不及时
- 代码格式不规范
- 测试覆盖率不达标
- 性能基准轻微退化

### 8.2 处理措施

#### 🔧 纠正措施
```python
违规处理措施 = {
    "严重违规": [
        "立即回滚相关更改",
        "强制代码审查",
        "技术培训",
        "流程改进"
    ],
    "一般违规": [
        "要求限期整改",
        "增加审查频次",
        "提供技术指导",
        "记录改进计划"
    ]
}
```

---

## 📋 9. 维护工具和资源

### 9.1 推荐工具

#### 🛠️ 代码质量工具
```bash
# 安装代码质量检查工具
pip install flake8 mypy radon vulture pytest-cov

# 文档生成工具
pip install sphinx sphinx-rtd-theme

# 版本管理工具
pip install bump2version
```

#### 📊 监控工具
```python
监控工具配置 = {
    "性能监控": "py-spy, memory-profiler",
    "代码分析": "sonarqube, codeclimate", 
    "文档检查": "doc8, pydocstyle",
    "依赖管理": "pip-audit, safety"
}
```

### 9.2 自动化脚本

#### 🤖 维护脚本
```bash
#!/bin/bash
# maintenance.sh - 项目维护脚本

echo "开始执行项目维护检查..."

# 代码质量检查
echo "1. 执行代码质量检查..."
flake8 plookingII/ --max-line-length=120
mypy plookingII/
radon cc plookingII/ --min=B

# 测试覆盖率检查
echo "2. 执行测试覆盖率检查..."
pytest --cov=plookingII tests/

# 文档一致性检查
echo "3. 检查文档一致性..."
python tools/doc_checker.py

# 性能基准测试
echo "4. 执行性能基准测试..."
python tools/performance_test.py

echo "维护检查完成！"
```

---

## 📞 10. 支持和联系

### 10.1 维护团队联系方式

- **项目负责人**: PlookingII Team
- **技术负责人**: 核心开发团队
- **文档维护**: 文档团队

### 10.2 问题报告

如发现违反本维护准则的情况，请通过以下方式报告：
1. GitHub Issues
2. 项目内部沟通渠道
3. 代码审查评论

### 10.3 准则更新

本维护准则将根据项目发展需要定期更新：
- **小幅修订**: 不影响主要流程的细节调整
- **重大更新**: 影响维护流程的重要变更
- **版本发布**: 与项目主要版本同步更新

---

## 📄 附录

### 附录A: 术语表

| 术语 | 定义 |
|------|------|
| Quartz-only | 完全基于macOS原生Quartz框架的图像处理方式 |
| CGImage直通 | 直接使用CGImage对象进行渲染，避免转换开销 |
| 语义化版本 | 遵循SemVer规范的版本号管理方式 |
| 默认两层缓存 | 主缓存、预览缓存（由 AdvancedImageCache 统一管理）；预加载/渐进式可选 |

### 附录B: 检查清单模板

```markdown
## 代码提交检查清单
- [ ] 代码符合PEP 8规范
- [ ] 添加了完整的中文注释
- [ ] 通过所有自动化测试
- [ ] 更新了相关文档
- [ ] 版本号符合规范
- [ ] 性能基准未退化
```

---

**文档版本**: v1.0.0  
**生效日期**: 2025年9月20日  
**下次审查**: 2025年12月20日  
**维护团队**: PlookingII Team

© 2025 PlookingII Team. All rights reserved.

---

> **重要提醒**: 本维护准则为强制性文档，所有项目参与者必须严格遵守。违反准则的行为将影响项目质量和团队协作效率。如有疑问，请及时与维护团队联系。

## ✅ 11. Lint/Typing/CI 统一规范（v1.2.2）

为持续收敛技术债与防止回归，新增如下强制规则：

- Lint（以 ruff 为主）：
  - 启用规则组：E, F, I, B, W, PL, TRY, N（见 `pyproject.toml`）。
  - flake8 仅保留最小兼容；禁止新增忽略项，按计划逐步减少现有忽略。
  - 业务代码禁止 `from X import *`，统一显式导出和 `__all__` 管理。
- Typing（mypy）：
  - 开启 `warn_unused_ignores=True`, `warn_redundant_casts=True`, `warn_no_return=True`。
  - PyObjC 交互处优先使用 `ui/protocols.py` 中的最小 `Protocol`；如需 `# type: ignore` 必须附带理由，并在后续版本移除。
- 异常与回退：
  - 禁止裸 `except:`；最多捕获 `Exception` 并 `exc_info=True` 记录日志。
  - 回退分支必须输出结构化 debug 日志并更新计数器（加载/旋转已接入）。
- 测试与覆盖率：
  - 采用基于 pytest 的断言测试；禁止 print 驱动测试脚本。
  - 覆盖率门槛 Phase-1：`--cov-fail-under=50`，后续提升。
- CI 门禁：
  - GitHub Actions 运行 ruff、mypy、pytest（macOS），上传 coverage.xml 并在矩阵任务构建产物。
  - 任何门禁失败阻断合并。

本地开发建议：在提交前执行 `ruff check .`、`mypy plookingII`、`pytest`。新增回退逻辑需同步补测并更新 `tools/fallback_metrics_cli.py`（如适用）。
