#!/usr/bin/env python3
"""
测试图片显示功能的脚本
"""

import sys
import os
sys.path.insert(0, '.')

def test_image_display():
    """测试图片显示功能"""
    print('🖼️  图片显示功能测试')
    print('=' * 60)
    
    try:
        # 检查测试图片是否存在
        test_image_path = 'temp_test_images/test.jpg'
        if not os.path.exists(test_image_path):
            print(f'❌ 测试图片不存在: {test_image_path}')
            return False
        
        print(f'✅ 测试图片存在: {test_image_path}')
        
        # 导入必要的模块
        from AppKit import NSApplication, NSRect, NSRunningApplication, NSApplicationActivationPolicyRegular
        from plookingII.ui.window import MainWindow
        
        print('✅ 必要模块导入成功')
        
        # 创建应用程序实例（但不运行主循环）
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        
        print('✅ NSApplication创建成功')
        
        # 创建主窗口
        main_window = MainWindow.alloc().init()
        if not main_window:
            print('❌ MainWindow创建失败')
            return False
            
        print('✅ MainWindow创建成功')
        
        # 检查关键组件是否正确创建
        components_check = [
            ('image_view_controller', 'image_view_controller'),
            ('image_manager', 'image_manager'),
            ('image_view', 'image_view'),
            ('status_bar_controller', 'status_bar_controller')
        ]
        
        for name, attr in components_check:
            if hasattr(main_window, attr) and getattr(main_window, attr):
                print(f'  ✅ {name}')
            else:
                print(f'  ❌ {name} - 缺失或为None')
        
        # 设置图片列表
        main_window.images = [test_image_path]
        main_window.current_index = 0
        main_window.current_folder = os.path.dirname(test_image_path)
        
        print(f'✅ 图片列表设置完成: {len(main_window.images)} 张图片')
        
        # 测试图片显示
        print('\n🔄 测试图片显示...')
        try:
            # 调用图片管理器显示图片
            main_window.image_manager.show_current_image()
            print('✅ show_current_image() 调用成功')
            
            # 检查图片是否被设置到视图
            if main_window.image_view:
                # 首先检查CGImage（项目使用CGImage直通以提高性能）
                cgimage_set = False
                if hasattr(main_window.image_view, '_cgimage'):
                    cgimage = getattr(main_window.image_view, '_cgimage', None)
                    if cgimage:
                        print('✅ CGImage已设置到视图（高性能直通模式）')
                        print(f'📊 CGImage对象类型: {type(cgimage)}')
                        
                        # 获取CGImage尺寸
                        try:
                            from Quartz import CGImageGetWidth, CGImageGetHeight
                            width = CGImageGetWidth(cgimage)
                            height = CGImageGetHeight(cgimage)
                            print(f'📐 图片尺寸: {width} x {height}')
                        except:
                            print('📐 图片尺寸: 无法获取')
                        
                        cgimage_set = True
                
                # 然后检查NSImage（备用路径）
                current_image = main_window.image_view.image()
                if current_image:
                    print('✅ NSImage也已设置到视图')
                    print(f'📊 NSImage对象类型: {type(current_image)}')
                    
                    # 检查图片尺寸
                    if hasattr(current_image, 'size'):
                        size = current_image.size()
                        print(f'📐 NSImage尺寸: {size.width} x {size.height}')
                
                # 判断是否成功显示
                if cgimage_set or current_image:
                    return True
                else:
                    print('❌ 视图中既没有CGImage也没有NSImage')
            else:
                print('❌ image_view为None')
                
        except Exception as e:
            print(f'❌ 图片显示测试失败: {e}')
            import traceback
            traceback.print_exc()
            return False
            
        return False
        
    except Exception as e:
        print(f'❌ 测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False

def test_image_loading_components():
    """测试图片加载相关组件"""
    print('\n🔧 图片加载组件测试')
    print('=' * 60)
    
    try:
        # 测试图片处理器
        from plookingII.core.image_processing import HybridImageProcessor
        processor = HybridImageProcessor()
        
        test_image_path = 'temp_test_images/test.jpg'
        if os.path.exists(test_image_path):
            image = processor.load_image_optimized(test_image_path)
            if image:
                print('✅ HybridImageProcessor加载成功')
                print(f'📊 加载的图片类型: {type(image)}')
            else:
                print('❌ HybridImageProcessor加载失败')
                return False
        else:
            print('❌ 测试图片不存在')
            return False
        
        # 测试图片视图
        from plookingII.ui.views import AdaptiveImageView
        from AppKit import NSMakeRect
        
        frame = NSMakeRect(0, 0, 400, 300)
        image_view = AdaptiveImageView.alloc().initWithFrame_(frame)
        
        if image_view:
            print('✅ AdaptiveImageView创建成功')
            
            # 测试图片设置
            if hasattr(image_view, 'setCGImage_'):
                image_view.setCGImage_(image)
                print('✅ CGImage设置成功')
            else:
                print('❌ setCGImage_方法不存在')
                return False
        else:
            print('❌ AdaptiveImageView创建失败')
            return False
            
        return True
        
    except Exception as e:
        print(f'❌ 组件测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    # 测试图片加载组件
    component_test_result = test_image_loading_components()
    
    # 测试完整的图片显示流程
    display_test_result = test_image_display()
    
    print('\n' + '=' * 60)
    print('📋 测试结果总结:')
    print(f'  组件测试: {"✅ 通过" if component_test_result else "❌ 失败"}')
    print(f'  显示测试: {"✅ 通过" if display_test_result else "❌ 失败"}')
    
    if component_test_result and display_test_result:
        print('\n🎉 所有测试通过！图片显示功能正常')
        sys.exit(0)
    else:
        print('\n❌ 测试失败，需要修复图片显示功能')
        sys.exit(1)
