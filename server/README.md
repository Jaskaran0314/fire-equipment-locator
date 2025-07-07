# 动火设备管理系统 - 后端服务

## 功能说明

本后端服务包含两个主要部分：
1. **TCP服务器**：监听7788端口，处理M63定位终端的连接和数据上报
2. **Flask API服务器**：监听5000端口，提供RESTful API接口

## 安装依赖

```bash
cd server
pip install -r requirements.txt
```

## 启动服务

```bash
python start.py
```

## API接口说明

### 认证相关
- POST /api/auth/login - 用户登录
- POST /api/auth/logout - 用户登出
- GET /api/auth/current - 获取当前用户信息

### 用户管理（需要管理员权限）
- GET /api/users - 获取用户列表
- POST /api/users - 创建用户
- PUT /api/users/:id - 更新用户信息
- DELETE /api/users/:id - 删除用户

### 设备管理
- GET /api/devices - 获取设备列表
- POST /api/devices - 创建设备
- GET /api/devices/:id - 获取设备详情
- PUT /api/devices/:id - 更新设备信息
- DELETE /api/devices/:id - 删除设备（管理员）
- POST /api/devices/:id/confirm-location - 确认设备位置
- GET /api/devices/:id/tracks - 获取设备轨迹

### 终端管理
- GET /api/terminals - 获取在线终端列表
- GET /api/terminals/all - 获取所有终端状态

### 报警管理
- GET /api/alarms - 获取报警列表

## 默认账号

- 管理员账号：admin / admin123

## 数据库

系统使用SQLite数据库，数据库文件为`fire_device.db`，首次运行会自动创建。

## 报警规则

1. **移动报警**：当设备移动超过确认位置20米时触发
2. **掉线报警**：当终端断开连接时触发
3. **解除报警**：当设备返回确认位置20米范围内时自动解除移动报警