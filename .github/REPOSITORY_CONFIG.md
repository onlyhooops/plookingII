# GitHub 仓库配置

这个文件包含 GitHub 仓库的推荐配置信息。

## About 描述

```
macOS 原生高性能图片浏览器 - 基于 PyObjC、AppKit、Quartz 的智能图片浏览体验
```

英文版本：
```
Native macOS image viewer with high performance - Intelligent image browsing experience based on PyObjC, AppKit, and Quartz
```

## Topics (标签)

建议添加以下 topics 到 GitHub 仓库：

```
macos
image-viewer
pyobjc
appkit
quartz
python
native-app
macos-app
image-processing
cocoa
performance
x86-64
intel-mac
image-browser
```

## 网站链接

```
https://github.com/onlyhooops/plookingII
```

## 社交图片

建议使用项目 logo：`plookingII/logo/PlookingII.svg`

## 如何应用这些配置

### 方法 1: 通过 GitHub Web 界面（推荐）

1. 访问仓库主页：https://github.com/onlyhooops/plookingII
2. 点击右上角的 "⚙️ Settings"
3. 在 "General" 部分：
   - **Description**: 粘贴上面的描述
   - **Website**: 留空或填写项目主页
   - **Topics**: 点击 "Topics" 输入框，逐个添加上面的标签
4. 保存更改

### 方法 2: 通过 GitHub CLI

如果您已安装 GitHub CLI (`gh`)：

```bash
# 设置描述
gh repo edit onlyhooops/plookingII \
  --description "macOS 原生高性能图片浏览器 - 基于 PyObjC、AppKit、Quartz 的智能图片浏览体验"

# 添加 topics
gh repo edit onlyhooops/plookingII \
  --add-topic macos \
  --add-topic image-viewer \
  --add-topic pyobjc \
  --add-topic appkit \
  --add-topic quartz \
  --add-topic python \
  --add-topic native-app \
  --add-topic macos-app \
  --add-topic image-processing \
  --add-topic cocoa \
  --add-topic performance \
  --add-topic x86-64 \
  --add-topic intel-mac \
  --add-topic image-browser
```

### 方法 3: 通过 GitHub API

```bash
# 设置环境变量
export GITHUB_TOKEN="your_github_token"

# 更新仓库描述和 topics
curl -X PATCH \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/onlyhooops/plookingII \
  -d '{
    "description": "macOS 原生高性能图片浏览器 - 基于 PyObjC、AppKit、Quartz 的智能图片浏览体验",
    "homepage": "",
    "topics": [
      "macos",
      "image-viewer",
      "pyobjc",
      "appkit",
      "quartz",
      "python",
      "native-app",
      "macos-app",
      "image-processing",
      "cocoa",
      "performance",
      "x86-64",
      "intel-mac",
      "image-browser"
    ]
  }'
```

## 额外配置建议

### Features

在 "Settings > General" 中建议启用：
- ✅ Issues
- ✅ Discussions (可选，用于社区讨论)
- ✅ Preserve this repository (归档保护)

### Pull Requests

建议设置：
- ✅ Allow squash merging
- ✅ Allow rebase merging
- ✅ Automatically delete head branches

### Branches

建议保护 `main` 分支：
- ✅ Require a pull request before merging
- ✅ Require status checks to pass before merging
- ✅ Require branches to be up to date before merging

### Security

建议启用：
- ✅ Dependabot alerts
- ✅ Dependabot security updates
- ✅ Code scanning alerts
