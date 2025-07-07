#!/usr/bin/env python3
"""
启动服务器脚本
同时启动TCP服务器和Flask API服务器
"""
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.app import start_servers

if __name__ == '__main__':
    print("启动动火设备管理系统服务器...")
    print("TCP服务器端口: 7788")
    print("API服务器端口: 5000")
    print("默认管理员账号: admin / admin123")
    print("=" * 50)
    
    try:
        start_servers()
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"服务器启动失败: {e}")