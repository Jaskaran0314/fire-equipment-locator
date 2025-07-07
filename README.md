# 消防设备定位管理系统

## 项目概述

本项目是一个基于M63协议的消防设备定位管理系统，包含：
- TCP服务器：接收和处理GPS定位终端数据
- Flask API服务器：提供RESTful接口和业务逻辑
- 微信小程序：前端用户界面

## 核心功能

### 1. 用户管理
- 管理员可以增删改查用户（姓名、电话、用户名密码）
- 普通用户只能查看和修改自己的信息
- 支持管理员和普通用户两种角色

### 2. 设备管理
- 所有用户都可以新增设备
- 只有管理员可以删除设备
- 设备信息包括：设备名称、ID、类型、所属机构、联系人等
- 设备需要绑定GPS定位终端

### 3. 定位监控
- 实时接收终端位置数据
- 在地图上显示设备当前位置
- 支持确认设备位置（location字段）
- 设备离开确认位置20米触发报警
- 设备返回20米范围内自动解除报警

### 4. 报警管理
- 移动报警：设备移动超过20米范围
- 掉线报警：终端离线超过3分钟
- 报警自动触发和解除
- 报警仅用于展示，无需处理逻辑

### 5. 轨迹查询
- 查看设备历史移动轨迹
- 支持按时间范围筛选
- 轨迹回放功能

## 技术架构

### 后端（server/）

#### TCP服务器
- **端口**：7788
- **协议**：M63 GPS终端通信协议
- **功能**：
  - 终端注册和认证
  - 心跳保持
  - 位置数据接收
  - 状态管理

#### Flask API服务器
- **端口**：5000
- **认证**：基于Session的用户认证
- **数据库**：SQLite
- **主要接口**：
  - `/auth/*` - 认证相关
  - `/users/*` - 用户管理
  - `/devices/*` - 设备管理
  - `/terminals/*` - 终端管理
  - `/alarms/*` - 报警查询

### 前端（miniprogram/）

#### 页面结构
1. **登录页** (`login/`) - 用户认证
2. **设备列表** (`device-list/`) - 设备概览和管理
3. **地图页** (`map/`) - 实时位置显示和确认
4. **设备编辑** (`device-edit/`) - 新增/编辑设备
5. **设备详情** (`device-detail/`) - 设备完整信息
6. **报警管理** (`alarm/`) - 报警列表和筛选
7. **用户中心** (`user-manage/`) - 个人信息和用户管理
8. **历史轨迹** (`track/`) - 轨迹查询和回放

## 启动说明

### 1. 安装依赖
```bash
cd server
pip install -r requirements.txt
```

### 2. 启动服务器
```bash
cd server
python start.py
```
这将同时启动：
- TCP服务器（端口7788）
- Flask API服务器（端口5000）

### 3. 默认账号
- 管理员账号：admin / admin123

### 4. 小程序配置
1. 使用微信开发者工具打开 `miniprogram` 目录
2. 修改 `utils/config.js` 中的 `API_BASE_URL` 为实际服务器地址
3. 编译运行

## 数据库结构

### users - 用户表
- id: 主键
- username: 用户名（唯一）
- password: 密码（加密存储）
- real_name: 真实姓名
- phone: 联系电话
- is_admin: 是否管理员

### devices - 设备表
- device_id: 设备ID（主键）
- device_name: 设备名称
- device_type: 设备类型
- organization: 所属机构
- contact_person: 联系人
- contact_phone: 联系电话
- terminal_id: 绑定的终端ID
- location: 确认位置（JSON格式：{lat, lng}）
- created_by: 创建用户ID

### terminals - 终端表
- terminal_id: 终端ID（主键）
- auth_code: 认证码
- is_online: 在线状态
- last_heartbeat: 最后心跳时间
- last_position: 最新位置（JSON格式）

### alarms - 报警表
- id: 主键
- device_id: 设备ID
- alarm_type: 报警类型（move/offline）
- alarm_time: 报警时间
- alarm_location: 报警位置（JSON格式）
- is_active: 是否激活
- resolved_at: 解除时间

### tracks - 轨迹表
- id: 主键
- device_id: 设备ID
- terminal_id: 终端ID
- report_time: 上报时间
- location: 位置信息（JSON格式）
- speed: 速度
- direction: 方向

## 注意事项

1. **位置确认**：新增设备后需要在地图页面确认设备位置，否则不会触发移动报警
2. **报警逻辑**：报警仅用于展示，不需要人工处理
3. **终端绑定**：一个终端只能绑定一个设备
4. **权限控制**：普通用户不能删除设备和管理其他用户
5. **图片资源**：小程序中使用的图标需要自行添加到 `miniprogram/images/` 目录

## 开发计划

### 已完成功能
- ✅ TCP服务器实现
- ✅ Flask API接口
- ✅ 用户认证和权限
- ✅ 设备CRUD操作
- ✅ 实时位置监控
- ✅ 自动报警机制
- ✅ 轨迹记录和查询
- ✅ 小程序全部页面

### 待优化项
- [ ] 添加图标资源
- [ ] 优化地图显示效果
- [ ] 增加数据导出功能
- [ ] 性能优化
- [ ] 错误处理增强 