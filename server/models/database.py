"""
数据库模型定义
使用SQLite存储数据
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import threading
import os

class Database:
    def __init__(self, db_path='fire_device.db'):
        self.db_path = db_path
        self.local = threading.local()
        self._init_database()
        
    def _get_connection(self):
        """获取线程本地的数据库连接"""
        if not hasattr(self.local, 'connection'):
            self.local.connection = sqlite3.connect(self.db_path)
            self.local.connection.row_factory = sqlite3.Row
        return self.local.connection
        
    def _init_database(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                real_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 动火设备表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT NOT NULL,
                device_id TEXT UNIQUE NOT NULL,
                organization TEXT NOT NULL,
                contact_person TEXT NOT NULL,
                contact_phone TEXT NOT NULL,
                device_type TEXT NOT NULL,
                location TEXT,  -- JSON格式存储 {"lat": 0.0, "lng": 0.0}
                terminal_id TEXT,  -- 绑定的定位终端ID
                created_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        ''')
        
        # 报警信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                alarm_type TEXT NOT NULL,  -- 'move'移动报警, 'offline'掉线报警
                alarm_time TEXT NOT NULL,
                alarm_location TEXT,  -- JSON格式存储 {"lat": 0.0, "lng": 0.0}
                is_active INTEGER DEFAULT 1,  -- 是否激活状态
                resolved_at TEXT,  -- 解除时间
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 终端状态表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS terminals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                terminal_id TEXT UNIQUE NOT NULL,
                phone TEXT,
                status TEXT DEFAULT 'offline',  -- online, offline
                last_location TEXT,  -- JSON格式存储位置信息
                last_update_time TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 设备轨迹表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                terminal_id TEXT NOT NULL,
                location TEXT NOT NULL,  -- JSON格式
                speed REAL,
                direction INTEGER,
                report_time TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建默认管理员账号
        cursor.execute('''
            INSERT OR IGNORE INTO users (username, password, real_name, phone, is_admin)
            VALUES ('admin', 'admin123', '系统管理员', '13800000000', 1)
        ''')
        
        conn.commit()
        
    def close(self):
        """关闭数据库连接"""
        if hasattr(self.local, 'connection'):
            self.local.connection.close()
            
    # 用户相关操作
    def create_user(self, username: str, password: str, real_name: str, 
                   phone: str, is_admin: bool = False) -> Optional[int]:
        """创建用户"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (username, password, real_name, phone, is_admin)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, password, real_name, phone, 1 if is_admin else 0))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
            
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """通过用户名获取用户"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        return dict(row) if row else None
        
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """通过ID获取用户"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
        
    def update_user(self, user_id: int, **kwargs) -> bool:
        """更新用户信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        allowed_fields = ['password', 'real_name', 'phone', 'is_admin']
        updates = []
        values = []
        
        for field in allowed_fields:
            if field in kwargs:
                updates.append(f'{field} = ?')
                values.append(kwargs[field])
                
        if not updates:
            return False
            
        values.append(user_id)
        cursor.execute(f'''
            UPDATE users SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', values)
        conn.commit()
        return cursor.rowcount > 0
        
    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = ? AND is_admin = 0', (user_id,))
        conn.commit()
        return cursor.rowcount > 0
        
    def list_users(self) -> List[Dict]:
        """获取所有用户"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users ORDER BY id')
        return [dict(row) for row in cursor.fetchall()]
        
    # 设备相关操作
    def create_device(self, device_name: str, device_id: str, organization: str,
                     contact_person: str, contact_phone: str, device_type: str,
                     location: Optional[Dict] = None, terminal_id: Optional[str] = None, 
                     created_by: Optional[int] = None) -> Optional[int]:
        """创建设备"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        location_json = json.dumps(location) if location else None
        
        try:
            cursor.execute('''
                INSERT INTO devices (device_name, device_id, organization, 
                                   contact_person, contact_phone, device_type,
                                   location, terminal_id, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (device_name, device_id, organization, contact_person, 
                  contact_phone, device_type, location_json, terminal_id, created_by))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
            
    def get_device_by_id(self, device_id: str) -> Optional[Dict]:
        """通过设备ID获取设备"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
        row = cursor.fetchone()
        if row:
            device = dict(row)
            if device['location']:
                device['location'] = json.loads(device['location'])
            return device
        return None
        
    def get_device_by_terminal(self, terminal_id: str) -> Optional[Dict]:
        """通过终端ID获取设备"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM devices WHERE terminal_id = ?', (terminal_id,))
        row = cursor.fetchone()
        if row:
            device = dict(row)
            if device['location']:
                device['location'] = json.loads(device['location'])
            return device
        return None
        
    def update_device(self, device_id: str, **kwargs) -> bool:
        """更新设备信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        allowed_fields = ['device_name', 'organization', 'contact_person', 
                         'contact_phone', 'device_type', 'location', 'terminal_id']
        updates = []
        values = []
        
        for field in allowed_fields:
            if field in kwargs:
                if field == 'location':
                    updates.append(f'{field} = ?')
                    values.append(json.dumps(kwargs[field]))
                else:
                    updates.append(f'{field} = ?')
                    values.append(kwargs[field])
                    
        if not updates:
            return False
            
        values.append(device_id)
        cursor.execute(f'''
            UPDATE devices SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
            WHERE device_id = ?
        ''', values)
        conn.commit()
        return cursor.rowcount > 0
        
    def delete_device(self, device_id: str) -> bool:
        """删除设备"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM devices WHERE device_id = ?', (device_id,))
        conn.commit()
        return cursor.rowcount > 0
        
    def list_devices(self) -> List[Dict]:
        """获取所有设备"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM devices ORDER BY created_at DESC')
        devices = []
        for row in cursor.fetchall():
            device = dict(row)
            if device['location']:
                device['location'] = json.loads(device['location'])
            devices.append(device)
        return devices
        
    # 报警相关操作
    def create_alarm(self, device_id: str, alarm_type: str, 
                    alarm_location: Optional[Dict] = None) -> int:
        """创建报警"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        alarm_time = datetime.now().isoformat()
        location_json = json.dumps(alarm_location) if alarm_location else None
        
        cursor.execute('''
            INSERT INTO alarms (device_id, alarm_type, alarm_time, alarm_location)
            VALUES (?, ?, ?, ?)
        ''', (device_id, alarm_type, alarm_time, location_json))
        conn.commit()
        return cursor.lastrowid
        
    def resolve_alarm(self, device_id: str, alarm_type: str) -> bool:
        """解除报警"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE alarms SET is_active = 0, resolved_at = CURRENT_TIMESTAMP
            WHERE device_id = ? AND alarm_type = ? AND is_active = 1
        ''', (device_id, alarm_type))
        conn.commit()
        return cursor.rowcount > 0
        
    def get_active_alarms(self, device_id: str = None) -> List[Dict]:
        """获取激活的报警"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if device_id:
            cursor.execute('''
                SELECT a.*, d.device_name, d.organization 
                FROM alarms a
                JOIN devices d ON a.device_id = d.device_id
                WHERE a.is_active = 1 AND a.device_id = ?
                ORDER BY a.alarm_time DESC
            ''', (device_id,))
        else:
            cursor.execute('''
                SELECT a.*, d.device_name, d.organization 
                FROM alarms a
                JOIN devices d ON a.device_id = d.device_id
                WHERE a.is_active = 1
                ORDER BY a.alarm_time DESC
            ''')
            
        alarms = []
        for row in cursor.fetchall():
            alarm = dict(row)
            if alarm['alarm_location']:
                alarm['alarm_location'] = json.loads(alarm['alarm_location'])
            alarms.append(alarm)
        return alarms
        
    def list_alarms(self, device_id: str = None, limit: int = 100) -> List[Dict]:
        """获取报警列表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if device_id:
            cursor.execute('''
                SELECT a.*, d.device_name, d.organization 
                FROM alarms a
                JOIN devices d ON a.device_id = d.device_id
                WHERE a.device_id = ?
                ORDER BY a.alarm_time DESC
                LIMIT ?
            ''', (device_id, limit))
        else:
            cursor.execute('''
                SELECT a.*, d.device_name, d.organization 
                FROM alarms a
                JOIN devices d ON a.device_id = d.device_id
                ORDER BY a.alarm_time DESC
                LIMIT ?
            ''', (limit,))
            
        alarms = []
        for row in cursor.fetchall():
            alarm = dict(row)
            if alarm['alarm_location']:
                alarm['alarm_location'] = json.loads(alarm['alarm_location'])
            alarms.append(alarm)
        return alarms
        
    # 终端相关操作
    def update_terminal_status(self, terminal_id: str, status: str, 
                              phone: Optional[str] = None, location: Optional[Dict] = None) -> bool:
        """更新终端状态"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 先检查是否存在
        cursor.execute('SELECT id FROM terminals WHERE terminal_id = ?', (terminal_id,))
        exists = cursor.fetchone()
        
        if exists:
            # 更新
            if location:
                cursor.execute('''
                    UPDATE terminals 
                    SET status = ?, phone = ?, last_location = ?, 
                        last_update_time = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE terminal_id = ?
                ''', (status, phone, json.dumps(location), terminal_id))
            else:
                cursor.execute('''
                    UPDATE terminals 
                    SET status = ?, phone = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE terminal_id = ?
                ''', (status, phone, terminal_id))
        else:
            # 插入
            cursor.execute('''
                INSERT INTO terminals (terminal_id, phone, status, last_location, last_update_time)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (terminal_id, phone, status, json.dumps(location) if location else None))
            
        conn.commit()
        return True
        
    def get_terminal_status(self, terminal_id: str) -> Optional[Dict]:
        """获取终端状态"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM terminals WHERE terminal_id = ?', (terminal_id,))
        row = cursor.fetchone()
        if row:
            terminal = dict(row)
            if terminal['last_location']:
                terminal['last_location'] = json.loads(terminal['last_location'])
            return terminal
        return None
        
    def list_online_terminals(self) -> List[Dict]:
        """获取在线终端列表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.*, d.device_id as bound_device_id, d.device_name
            FROM terminals t
            LEFT JOIN devices d ON t.terminal_id = d.terminal_id
            WHERE t.status = 'online'
            ORDER BY t.last_update_time DESC
        ''')
        
        terminals = []
        for row in cursor.fetchall():
            terminal = dict(row)
            if terminal['last_location']:
                terminal['last_location'] = json.loads(terminal['last_location'])
            terminals.append(terminal)
        return terminals
        
    # 轨迹相关操作
    def add_device_track(self, device_id: str, terminal_id: str, 
                        location: Dict, speed: float = 0, direction: int = 0,
                        report_time: str = None) -> int:
        """添加设备轨迹点"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if not report_time:
            report_time = datetime.now().isoformat()
            
        cursor.execute('''
            INSERT INTO device_tracks (device_id, terminal_id, location, speed, direction, report_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (device_id, terminal_id, json.dumps(location), speed, direction, report_time))
        conn.commit()
        return cursor.lastrowid
        
    def get_device_tracks(self, device_id: str, start_time: str = None, 
                         end_time: str = None, limit: int = 1000) -> List[Dict]:
        """获取设备轨迹"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM device_tracks WHERE device_id = ?'
        params = [device_id]
        
        if start_time:
            query += ' AND report_time >= ?'
            params.append(start_time)
            
        if end_time:
            query += ' AND report_time <= ?'
            params.append(end_time)
            
        query += ' ORDER BY report_time DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        
        tracks = []
        for row in cursor.fetchall():
            track = dict(row)
            track['location'] = json.loads(track['location'])
            tracks.append(track)
        return tracks