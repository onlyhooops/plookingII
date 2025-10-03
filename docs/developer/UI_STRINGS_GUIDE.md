# UI文案管理系统使用指南

## 📋 概述

PlookingII v1.2.3 引入了统一的UI文案管理系统，解决了硬编码文案问题，为国际化和文案维护提供了基础架构。

## 🎯 设计目标

- **集中管理**: 所有用户可见文案统一管理
- **非硬编码**: 避免在代码中直接写入文案字符串
- **国际化友好**: 为多语言支持奠定基础
- **类型安全**: 明确的分类和键名约定
- **向后兼容**: 提供默认值，不影响现有功能

## 📦 模块结构

```
plookingII/config/ui_strings.py
├── UIStrings (静态文案定义类)
│   ├── APP_INFO (应用信息)
│   ├── MENU (菜单文案)
│   ├── BUTTONS (按钮文案)
│   ├── SHORTCUTS_HELP (快捷键说明)
│   ├── ABOUT_DIALOG (关于对话框)
│   ├── STATUS_MESSAGES (状态消息)
│   ├── ERROR_MESSAGES (错误消息)
│   └── *_DIALOG (各种对话框)
├── UIStringManager (文案管理器)
└── 便捷函数 (get_ui_string, get_formatted_ui_string)
```

## 🚀 使用方法

### 基础使用

```python
from plookingII.config.ui_strings import get_ui_string

# 获取菜单文案
about_text = get_ui_string('menu', 'about', '关于')  # 返回: "关于"
quit_text = get_ui_string('menu', 'quit')  # 返回: "退出程序"

# 获取按钮文案
ok_button = get_ui_string('buttons', 'ok')  # 返回: "确定"
cancel_button = get_ui_string('buttons', 'cancel')  # 返回: "取消"
```

### 格式化文案

```python
from plookingII.config.ui_strings import get_formatted_ui_string

# 格式化状态消息
folder_msg = get_formatted_ui_string('status_messages', 'folder_opened', '我的图片')
# 返回: "已打开文件夹: 我的图片"

error_msg = get_formatted_ui_string('error_messages', 'keyboard_event_failed', 'test error')
# 返回: "键盘事件处理失败: test error"
```

### 复杂文本生成

```python
from plookingII.config.ui_strings import get_ui_string_manager

ui_manager = get_ui_string_manager()

# 生成完整的快捷键帮助文本
shortcuts_text = ui_manager.get_shortcuts_help_text()

# 生成关于对话框文本
about_text = ui_manager.get_about_dialog_text(
    version = "1.4.0",
    author="PlookingII Team", 
    copyright_text="© 2025 PlookingII Team"
)
```

## 📁 文案分类

### 🍎 应用信息 (app_info)
- `name`: 应用名称
- `version_label`: "版本："
- `developer_label`: "开发者："

### 📋 菜单 (menu)
- `about`: "关于"
- `hide`: "隐藏"
- `quit`: "退出程序"
- `undo_selection`: "撤销精选"
- `shortcuts`: "快捷键"
- `rotate_right`: "向右旋转90°"
- `rotate_left`: "向左旋转90°"

### 🔘 按钮 (buttons)
- `ok`: "确定"
- `cancel`: "取消"
- `restore`: "恢复"
- `restart`: "重新开始"
- `view_help`: "查看帮助"

### 📢 状态消息 (status_messages)
- `folder_opened`: "已打开文件夹: {}"
- `folder_skipped`: "已跳过文件夹: {}"
- `rotation_completed`: "{}旋转90°完成"
- `no_images`: "无图片 0/0"

### ❌ 错误消息 (error_messages)
- `keyboard_event_failed`: "键盘事件处理失败: {}"
- `folder_access_denied`: "无法访问文件夹"
- `unsupported_folder`: "拖拽的文件夹中未找到支持的图片文件"

## 🔧 实际应用示例

### 菜单构建器中的使用

```python
# 原来的硬编码方式
about_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
    "关于", "showAbout:", ""
)

# 新的文案管理方式
about_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
    get_ui_string('menu', 'about', '关于'), "showAbout:", ""
)
```

### 对话框中的使用

```python
# 原来的硬编码方式
alert.setMessageText_("任务完成")
alert.setInformativeText_("所有图片文件夹已浏览完毕！")
alert.addButtonWithTitle_("确定")

# 新的文案管理方式
alert.setMessageText_(get_ui_string('status_messages', 'task_completed'))
alert.setInformativeText_(get_ui_string('status_messages', 'all_folders_viewed'))
alert.addButtonWithTitle_(get_ui_string('buttons', 'ok'))
```

### 状态消息中的使用

```python
# 原来的硬编码方式
self.status_bar_controller.set_status_message(f"已打开文件夹: {folder_name}")

# 新的文案管理方式
message = get_formatted_ui_string('status_messages', 'folder_opened', folder_name)
self.status_bar_controller.set_status_message(message)
```

## 🌍 国际化支持

### 扩展新语言

1. 在 `UIStrings` 类中添加新语言的文案字典
2. 修改 `UIStringManager` 支持语言切换
3. 根据系统语言或用户设置选择对应文案

```python
# 未来扩展示例
class UIStrings:
    MENU_ZH = {'about': '关于', 'quit': '退出程序'}
    MENU_EN = {'about': 'About', 'quit': 'Quit'}
    
    @classmethod
    def get_menu(cls, language='zh'):
        return cls.MENU_ZH if language == 'zh' else cls.MENU_EN
```

## ✅ 迁移完成的模块

1. **ui/window.py**: 关于对话框、快捷键说明、复制路径功能
2. **ui/menu_builder.py**: 所有菜单项文案
3. **ui/managers/folder_manager.py**: 历史记录对话框按钮
4. **ui/managers/operation_manager.py**: 任务完成、错误提示等状态消息
5. **ui/utils/user_feedback.py**: 通用按钮文案

## 📈 测试覆盖

- **28个测试用例全部通过**
- **UI文案模块覆盖率96%**
- 涵盖基础获取、格式化、错误处理、集成测试等

## 🎉 使用优势

1. **维护性**: 文案修改只需在一处进行
2. **一致性**: 避免同一文案在不同地方的差异
3. **可扩展性**: 易于添加新文案和新语言
4. **测试性**: 文案变更可以通过测试验证
5. **代码清洁**: 业务逻辑与文案分离

---

**PlookingII Team** © 2025  
**版本**: v1.4.0
