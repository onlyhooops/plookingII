# 拖拽文件夹功能说明

## 功能概述

为 PlookingII 项目新增了拖拽文件夹功能，用户现在可以直接将包含照片的文件夹拖拽到应用程序窗口中进行照片浏览，无需通过菜单选择文件夹。

## 新增功能特性

### 1. 拖拽接收功能
- **文件类型支持**: 支持拖拽文件夹到应用程序窗口
- **智能检测**: 自动检测拖拽的文件夹是否包含支持的图片文件（JPG、JPEG、PNG）
- **递归检查**: 支持检测文件夹及其子文件夹中的图片文件

### 2. 视觉反馈
- **高亮效果**: 当拖拽有效的图片文件夹到窗口上方时，显示蓝色高亮边框和半透明覆盖层
- **状态提示**: 在状态栏显示"松开鼠标打开文件夹: [文件夹名]"的提示信息
- **自动清除**: 拖拽离开窗口或操作完成后自动清除视觉效果

### 3. 无缝集成
- **兼容现有流程**: 拖拽打开的文件夹与通过菜单选择的文件夹处理流程完全一致
- **历史记录**: 拖拽打开的文件夹自动添加到最近打开记录
- **任务保存**: 自动保存当前任务进度并加载新文件夹

## 技术实现

### 修改的文件

#### 1. `plookingII/ui/window.py`
- **新增导入**: 添加了拖拽相关的 AppKit 类导入
- **拖拽设置**: `_setup_drag_and_drop()` 方法注册拖拽接收功能
- **拖拽处理**: 实现了完整的拖拽生命周期方法：
  - `draggingEntered_()`: 拖拽进入时的验证和视觉反馈
  - `draggingUpdated_()`: 拖拽移动时的状态更新
  - `draggingExited_()`: 拖拽离开时清除视觉效果
  - `performDragOperation_()`: 执行拖拽操作
- **文件夹验证**: `_folder_contains_images()` 方法检测文件夹是否包含图片

#### 2. `plookingII/ui/views.py`
- **高亮状态**: 在 `AdaptiveImageView` 类中添加拖拽高亮状态管理
- **视觉效果**: 实现了拖拽高亮的绘制逻辑
- **状态控制**: `setDragHighlight_()` 方法控制高亮效果的显示和隐藏

### 核心逻辑

1. **拖拽验证**:
   ```python
   # 检查是否为文件夹
   if os.path.isdir(filename):
       # 检查是否包含图片文件
       if self._folder_contains_images(filename):
           return NSDragOperationCopy
   ```

2. **视觉反馈**:
   ```python
   # 启用高亮效果
   self.image_view.setDragHighlight_(True)
   # 显示状态消息
   self.status_bar_controller.set_status_message(f"松开鼠标打开文件夹: {folder_name}")
   ```

3. **文件夹处理**:
   ```python
   # 保存到历史记录
   self.operation_manager._save_last_dir(valid_folder)
   self.folder_manager.add_recent_folder(valid_folder)
   # 加载文件夹图片
   self.folder_manager.load_images_from_root(valid_folder)
   ```

## 使用方法

1. **启动应用程序**: 正常启动 PlookingII 应用
2. **准备文件夹**: 确保要浏览的文件夹包含 JPG、JPEG 或 PNG 格式的图片文件
3. **拖拽操作**: 
   - 从 Finder 中选择包含图片的文件夹
   - 拖拽到 PlookingII 应用程序窗口上
   - 看到蓝色高亮效果和提示信息时松开鼠标
4. **开始浏览**: 应用程序自动加载文件夹中的图片，开始照片浏览

## 兼容性说明

- **操作系统**: 仅支持 macOS（使用 AppKit 框架）
- **文件格式**: 支持 JPG、JPEG、PNG 格式的图片文件
- **现有功能**: 完全兼容现有的菜单选择文件夹功能，不影响其他操作流程

## 错误处理

- **无效文件夹**: 拖拽不包含图片的文件夹时显示相应提示信息
- **权限问题**: 自动跳过无法访问的文件夹
- **异常情况**: 所有异常都有适当的捕获和日志记录，不会影响应用程序稳定性

## 测试验证

通过了完整的功能测试：
- ✅ 文件夹图片检测逻辑正确
- ✅ 支持的图片扩展名配置正常
- ✅ AppKit 拖拽相关导入成功
- ✅ 代码编译无错误
- ✅ 与现有流程完全兼容

---

**注意**: 此功能增强了用户体验，使文件夹选择更加直观便捷，同时保持了与现有功能的完全兼容性。
