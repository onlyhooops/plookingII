# 贡献指南

欢迎为 PlookingII 项目做出贡献！我们感谢所有形式的贡献，包括但不限于代码、文档、测试、问题报告和功能建议。

## 🚀 快速开始

### 开发环境设置

1. **克隆项目**
   ```bash
   git clone https://github.com/onlyhooops/plookingII.git
   cd plookingII
   ```

2. **创建虚拟环境**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   pip install -e .[dev]  # 安装开发依赖
   ```

4. **运行测试**
   ```bash
   pytest
   ```

### 系统要求

- **操作系统**: macOS 10.15+ (Catalina或更高版本)
- **Python**: 3.9+ 
- **依赖**: PyObjC, Pillow, psutil等（详见requirements.txt）

## 📝 贡献类型

### 🐛 问题报告

发现了bug？请通过以下步骤报告：

1. 检查[已有问题](https://github.com/onlyhooops/plookingII/issues)，避免重复报告
2. 使用问题模板创建新的issue
3. 提供详细信息：
   - macOS版本
   - Python版本
   - 重现步骤
   - 期望行为vs实际行为
   - 错误日志或截图

### 💡 功能建议

有新的想法？我们很乐意听到：

1. 在[Discussions](https://github.com/onlyhooops/plookingII/discussions)中讨论
2. 描述功能的用途和价值
3. 考虑实现的复杂性和维护成本
4. 提供具体的用例场景

### 🔧 代码贡献

#### 开发流程

1. **Fork项目** 到你的GitHub账户
2. **创建特性分支**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **编写代码** 遵循项目编码规范
4. **添加测试** 确保新功能有相应的测试
5. **运行测试套件**
   ```bash
   pytest
   python3 tools/architecture_guard.py
   ```
6. **提交更改**
   ```bash
   git commit -m "feat: add amazing feature"
   ```
7. **推送分支**
   ```bash
   git push origin feature/amazing-feature
   ```
8. **创建Pull Request**

#### 代码规范

- **Python风格**: 遵循PEP 8，使用black格式化
- **导入排序**: 使用isort整理导入
- **类型注解**: 为函数参数和返回值添加类型注解
- **文档字符串**: 使用Google风格的docstring
- **命名规范**: 
  - 类名: PascalCase
  - 函数名: snake_case
  - 常量: UPPER_CASE
  - 私有成员: _leading_underscore

#### 代码质量检查

提交前请运行：

```bash
# 代码格式化
black plookingII/
isort plookingII/

# 代码检查
flake8 plookingII/
mypy plookingII/

# 架构检查
python3 tools/architecture_guard.py

# 测试
pytest --cov=plookingII
```

### 📚 文档贡献

文档改进包括：
- README更新
- API文档完善
- 教程和示例
- 注释改进
- 翻译工作

### 🧪 测试贡献

- 添加单元测试
- 完善集成测试
- 性能测试
- UI测试
- 兼容性测试

## 🎯 开发重点

### 当前优先级

1. **架构优化** - 继续完善统一接口设计
2. **性能提升** - 优化图像加载和缓存机制
3. **SMB支持** - 增强远程存储功能
4. **用户体验** - 改进界面和交互
5. **测试覆盖** - 提高测试覆盖率

### 技术栈

- **UI框架**: PyObjC + Cocoa
- **图像处理**: Pillow + Quartz
- **网络**: SMB协议支持
- **缓存**: 多层缓存架构
- **测试**: pytest + coverage
- **CI/CD**: GitHub Actions

## 📋 Pull Request 指南

### PR标题格式

使用[约定式提交](https://www.conventionalcommits.org/zh-hans/)格式：

- `feat:` 新功能
- `fix:` 修复bug
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 重构代码
- `test:` 测试相关
- `chore:` 构建或辅助工具变动

### PR描述模板

```markdown
## 变更类型
- [ ] Bug修复
- [ ] 新功能
- [ ] 重构
- [ ] 文档更新
- [ ] 其他

## 变更描述
简要描述这个PR的目的和内容

## 测试
- [ ] 添加了新的测试
- [ ] 所有测试通过
- [ ] 手动测试完成

## 检查清单
- [ ] 代码遵循项目规范
- [ ] 添加了必要的文档
- [ ] 没有引入破坏性变更
- [ ] PR标题符合约定式提交规范
```

### 审查流程

1. **自动检查** - CI流水线验证
2. **代码审查** - 维护者review
3. **测试验证** - 功能和性能测试
4. **合并** - squash merge到main分支

## 🏷️ 版本发布

项目采用[语义化版本](https://semver.org/lang/zh-CN/)：

- **主版本号**: 不兼容的API修改
- **次版本号**: 向下兼容的功能性新增
- **修订号**: 向下兼容的问题修正

## 🤝 社区准则

### 行为规范

- **尊重他人**: 友善、包容、专业
- **建设性沟通**: 提供有价值的反馈
- **协作精神**: 帮助他人成长
- **质量第一**: 追求代码和文档质量

### 沟通渠道

- **GitHub Issues**: 问题报告和功能请求
- **GitHub Discussions**: 技术讨论和想法分享
- **Pull Requests**: 代码审查和讨论

## 📞 获得帮助

需要帮助？可以通过以下方式：

1. 查看[FAQ](README.md#常见问题)
2. 搜索[已有问题](https://github.com/onlyhooops/plookingII/issues)
3. 在[Discussions](https://github.com/onlyhooops/plookingII/discussions)中提问
4. 创建新的issue

## 🙏 致谢

感谢所有为PlookingII做出贡献的开发者！每一个贡献都让这个项目变得更好。

---

**记住**: 贡献不仅仅是代码，文档、测试、问题报告、功能建议都是宝贵的贡献！

欢迎加入PlookingII社区！🚀
