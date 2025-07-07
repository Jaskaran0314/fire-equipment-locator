"""
Flask API服务器
提供RESTful API接口
"""
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from functools import wraps
import hashlib
import os
import sys
from datetime import datetime
import threading
import math

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Database
from tcp_server.server import TCPServer
from utils.distance import calculate_distance

app = Flask(__name__)
app.secret_key = 'fire-device-secret-key-2024'
CORS(app, supports_credentials=True)

# 全局对象
db = Database(os.path.join(os.path.dirname(__file__), '../../fire_device.db'))
tcp_server = TCPServer()

# 报警检查间隔（秒）
ALARM_CHECK_INTERVAL = 30

def hash_password(password: str) -> str:
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'code': 401, 'message': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'code': 401, 'message': '请先登录'}), 401
        if not session.get('is_admin'):
            return jsonify({'code': 403, 'message': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function

# 用户相关API
@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'code': 400, 'message': '用户名和密码不能为空'})
    
    user = db.get_user_by_username(username)
    if not user or user['password'] != hash_password(password):
        return jsonify({'code': 401, 'message': '用户名或密码错误'})
    
    # 设置session
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['is_admin'] = bool(user['is_admin'])
    
    return jsonify({
        'code': 200,
        'message': '登录成功',
        'data': {
            'id': user['id'],
            'username': user['username'],
            'real_name': user['real_name'],
            'is_admin': bool(user['is_admin'])
        }
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """用户登出"""
    session.clear()
    return jsonify({'code': 200, 'message': '登出成功'})

@app.route('/api/auth/current', methods=['GET'])
@login_required
def get_current_user():
    """获取当前用户信息"""
    user = db.get_user_by_id(session['user_id'])
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在'})
    
    return jsonify({
        'code': 200,
        'data': {
            'id': user['id'],
            'username': user['username'],
            'real_name': user['real_name'],
            'phone': user['phone'],
            'is_admin': bool(user['is_admin'])
        }
    })

@app.route('/api/users', methods=['GET'])
@admin_required
def list_users():
    """获取用户列表（管理员）"""
    users = db.list_users()
    # 移除密码字段
    for user in users:
        user.pop('password', None)
    
    return jsonify({
        'code': 200,
        'data': users
    })

@app.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    """创建用户（管理员）"""
    data = request.get_json()
    
    required_fields = ['username', 'password', 'real_name', 'phone']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'code': 400, 'message': f'{field}不能为空'})
    
    user_id = db.create_user(
        username=data['username'],
        password=hash_password(data['password']),
        real_name=data['real_name'],
        phone=data['phone'],
        is_admin=data.get('is_admin', False)
    )
    
    if not user_id:
        return jsonify({'code': 400, 'message': '用户名已存在'})
    
    return jsonify({
        'code': 200,
        'message': '创建成功',
        'data': {'id': user_id}
    })

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """更新用户信息（管理员）"""
    data = request.get_json()
    
    # 处理密码更新
    if 'password' in data and data['password']:
        data['password'] = hash_password(data['password'])
    else:
        data.pop('password', None)
    
    if db.update_user(user_id, **data):
        return jsonify({'code': 200, 'message': '更新成功'})
    else:
        return jsonify({'code': 404, 'message': '用户不存在'})

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """删除用户（管理员）"""
    if db.delete_user(user_id):
        return jsonify({'code': 200, 'message': '删除成功'})
    else:
        return jsonify({'code': 404, 'message': '用户不存在或为管理员'})

# 设备相关API
@app.route('/api/devices', methods=['GET'])
@login_required
def list_devices():
    """获取设备列表"""
    devices = db.list_devices()
    
    # 添加终端状态信息
    for device in devices:
        if device.get('terminal_id'):
            terminal = db.get_terminal_status(device['terminal_id'])
            device['terminal_status'] = terminal.get('status', 'offline') if terminal else 'offline'
            device['last_position'] = terminal.get('last_location') if terminal else None
        else:
            device['terminal_status'] = 'unbound'
            device['last_position'] = None
            
        # 获取激活的报警
        alarms = db.get_active_alarms(device['device_id'])
        device['active_alarms'] = alarms
    
    return jsonify({
        'code': 200,
        'data': devices
    })

@app.route('/api/devices', methods=['POST'])
@login_required
def create_device():
    """创建设备"""
    data = request.get_json()
    
    required_fields = ['device_name', 'device_id', 'organization', 
                      'contact_person', 'contact_phone', 'device_type']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'code': 400, 'message': f'{field}不能为空'})
    
    # 检查是否绑定终端
    terminal_id = data.get('terminal_id')
    if terminal_id:
        # 检查终端是否已被其他设备绑定
        existing = db.get_device_by_terminal(terminal_id)
        if existing:
            return jsonify({'code': 400, 'message': '该终端已被其他设备绑定'})
    
    device_id = db.create_device(
        device_name=data['device_name'],
        device_id=data['device_id'],
        organization=data['organization'],
        contact_person=data['contact_person'],
        contact_phone=data['contact_phone'],
        device_type=data['device_type'],
        location=data.get('location'),
        terminal_id=terminal_id,
        created_by=session['user_id']
    )
    
    if not device_id:
        return jsonify({'code': 400, 'message': '设备ID已存在'})
    
    return jsonify({
        'code': 200,
        'message': '创建成功',
        'data': {'id': device_id}
    })

@app.route('/api/devices/<device_id>', methods=['GET'])
@login_required
def get_device(device_id):
    """获取设备详情"""
    device = db.get_device_by_id(device_id)
    if not device:
        return jsonify({'code': 404, 'message': '设备不存在'})
    
    # 添加终端状态信息
    if device.get('terminal_id'):
        terminal = db.get_terminal_status(device['terminal_id'])
        device['terminal_status'] = terminal.get('status', 'offline') if terminal else 'offline'
        device['last_position'] = terminal.get('last_location') if terminal else None
    else:
        device['terminal_status'] = 'unbound'
        device['last_position'] = None
    
    # 获取激活的报警
    device['active_alarms'] = db.get_active_alarms(device['device_id'])
    
    return jsonify({
        'code': 200,
        'data': device
    })

@app.route('/api/devices/<device_id>', methods=['PUT'])
@login_required
def update_device(device_id):
    """更新设备信息"""
    data = request.get_json()
    
    # 检查终端绑定
    if 'terminal_id' in data:
        terminal_id = data['terminal_id']
        if terminal_id:
            existing = db.get_device_by_terminal(terminal_id)
            if existing and existing['device_id'] != device_id:
                return jsonify({'code': 400, 'message': '该终端已被其他设备绑定'})
    
    if db.update_device(device_id, **data):
        return jsonify({'code': 200, 'message': '更新成功'})
    else:
        return jsonify({'code': 404, 'message': '设备不存在'})

@app.route('/api/devices/<device_id>', methods=['DELETE'])
@admin_required
def delete_device(device_id):
    """删除设备（管理员）"""
    if db.delete_device(device_id):
        return jsonify({'code': 200, 'message': '删除成功'})
    else:
        return jsonify({'code': 404, 'message': '设备不存在'})

@app.route('/api/devices/<device_id>/confirm-location', methods=['POST'])
@login_required
def confirm_device_location(device_id):
    """确认设备位置"""
    data = request.get_json()
    location = data.get('location')
    
    if not location or 'lat' not in location or 'lng' not in location:
        return jsonify({'code': 400, 'message': '位置信息不完整'})
    
    # 更新设备位置
    if db.update_device(device_id, location=location):
        return jsonify({'code': 200, 'message': '位置确认成功'})
    else:
        return jsonify({'code': 404, 'message': '设备不存在'})

# 终端相关API
@app.route('/api/terminals', methods=['GET'])
@login_required
def list_terminals():
    """获取在线终端列表"""
    terminals = db.list_online_terminals()
    return jsonify({
        'code': 200,
        'data': terminals
    })

@app.route('/api/terminals/all', methods=['GET'])
@login_required
def get_all_terminals():
    """获取所有终端状态（从TCP服务器）"""
    terminals = tcp_server.get_all_terminals()
    return jsonify({
        'code': 200,
        'data': terminals
    })

# 报警相关API
@app.route('/api/alarms', methods=['GET'])
@login_required
def list_alarms():
    """获取报警列表"""
    device_id = request.args.get('device_id')
    active_only = request.args.get('active_only', 'false').lower() == 'true'
    
    if active_only:
        alarms = db.get_active_alarms(device_id)
    else:
        alarms = db.list_alarms(device_id)
    
    return jsonify({
        'code': 200,
        'data': alarms
    })

# 轨迹相关API
@app.route('/api/devices/<device_id>/tracks', methods=['GET'])
@login_required
def get_device_tracks(device_id):
    """获取设备轨迹"""
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    
    tracks = db.get_device_tracks(device_id, start_time, end_time)
    
    return jsonify({
        'code': 200,
        'data': tracks
    })

# TCP服务器回调处理
def on_terminal_status_change(terminal_id: str, status: str, data: dict):
    """终端状态变化回调"""
    print(f"终端状态变化: {terminal_id} -> {status}")
    
    if status == 'registered':
        db.update_terminal_status(terminal_id, 'online', data.get('phone'))
    elif status == 'authenticated':
        db.update_terminal_status(terminal_id, 'online')
    elif status == 'offline':
        db.update_terminal_status(terminal_id, 'offline')
        
        # 检查是否有绑定的设备，生成掉线报警
        device = db.get_device_by_terminal(terminal_id)
        if device:
            db.create_alarm(device['device_id'], 'offline')

def on_position_update(terminal_id: str, position: dict):
    """位置更新回调"""
    print(f"位置更新: {terminal_id} -> {position['latitude']}, {position['longitude']}")
    
    # 更新终端位置
    location = {
        'lat': position['latitude'],
        'lng': position['longitude']
    }
    db.update_terminal_status(terminal_id, 'online', location=location)
    
    # 检查是否有绑定的设备
    device = db.get_device_by_terminal(terminal_id)
    if device:
        # 添加轨迹点
        db.add_device_track(
            device['device_id'],
            terminal_id,
            location,
            position.get('speed', 0),
            position.get('direction', 0),
            position.get('report_time')
        )
        
        # 检查是否需要报警
        check_device_alarm(device, location)

def check_device_alarm(device: dict, current_location: dict):
    """检查设备是否需要报警"""
    if not device.get('location'):
        return
    
    # 计算与设定位置的距离
    device_location = device['location']
    distance = calculate_distance(
        device_location['lat'], device_location['lng'],
        current_location['lat'], current_location['lng']
    )
    
    print(f"设备 {device['device_id']} 距离: {distance}米")
    
    # 检查是否超过20米
    if distance > 20:
        # 检查是否已有激活的移动报警
        active_alarms = db.get_active_alarms(device['device_id'])
        has_move_alarm = any(alarm['alarm_type'] == 'move' for alarm in active_alarms)
        
        if not has_move_alarm:
            # 创建移动报警
            db.create_alarm(device['device_id'], 'move', current_location)
            print(f"设备 {device['device_id']} 触发移动报警")
    else:
        # 在20米范围内，解除报警
        if db.resolve_alarm(device['device_id'], 'move'):
            print(f"设备 {device['device_id']} 解除移动报警")

# 启动函数
def start_servers():
    """启动所有服务器"""
    # 设置TCP服务器回调
    tcp_server.set_status_callback(on_terminal_status_change)
    tcp_server.set_position_callback(on_position_update)
    
    # 启动TCP服务器
    tcp_server.start()
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

if __name__ == '__main__':
    start_servers()