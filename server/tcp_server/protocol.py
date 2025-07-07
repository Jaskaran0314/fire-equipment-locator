"""
M63终端通讯协议解析器
处理消息的编码、解码、转义等
"""
import struct
import binascii
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

class M63Protocol:
    # 消息ID定义
    MSG_ID = {
        'TERMINAL_COMMON_REPLY': 0x0001,      # 终端通用应答
        'TERMINAL_HEARTBEAT': 0x0002,         # 终端心跳
        'TERMINAL_LOGOUT': 0x0003,            # 终端注销
        'TERMINAL_REGISTER': 0x0100,          # 终端注册
        'TERMINAL_AUTH': 0x0102,              # 终端鉴权
        'QUERY_PARAMS_REPLY': 0x0104,         # 查询终端参数应答
        'POSITION_REPORT': 0x0200,            # 位置信息汇报
        'POSITION_QUERY_REPLY': 0x0201,       # 位置信息查询应答
        'BATCH_POSITION': 0x0704,             # 定位数据批量上传
        'TEXT_MESSAGE': 0x6006,               # 上报文本消息
        
        'PLATFORM_COMMON_REPLY': 0x8001,      # 平台通用应答
        'TERMINAL_REGISTER_REPLY': 0x8100,    # 终端注册应答
        'SET_TERMINAL_PARAMS': 0x8103,        # 设置终端参数
        'QUERY_TERMINAL_PARAMS': 0x8104,      # 查询终端参数
        'TERMINAL_CONTROL': 0x8105,           # 终端控制
        'POSITION_QUERY': 0x8201,             # 位置信息查询
        'TEXT_MESSAGE_DOWN': 0x8300,          # 文本信息下发
    }
    
    # 标识位
    FLAG = 0x7E
    
    def __init__(self):
        self.sequence_number = 0
    
    def escape(self, data: bytes) -> bytes:
        """
        转义处理
        0x7e -> 0x7d 0x02
        0x7d -> 0x7d 0x01
        """
        result = bytearray()
        for byte in data:
            if byte == 0x7e:
                result.extend([0x7d, 0x02])
            elif byte == 0x7d:
                result.extend([0x7d, 0x01])
            else:
                result.append(byte)
        return bytes(result)
    
    def unescape(self, data: bytes) -> bytes:
        """
        反转义处理
        0x7d 0x02 -> 0x7e
        0x7d 0x01 -> 0x7d
        """
        result = bytearray()
        i = 0
        while i < len(data):
            if data[i] == 0x7d and i + 1 < len(data):
                if data[i + 1] == 0x02:
                    result.append(0x7e)
                    i += 2
                elif data[i + 1] == 0x01:
                    result.append(0x7d)
                    i += 2
                else:
                    result.append(data[i])
                    i += 1
            else:
                result.append(data[i])
                i += 1
        return bytes(result)
    
    def calculate_checksum(self, data: bytes) -> int:
        """计算校验码（异或）"""
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum
    
    def phone_to_bcd(self, phone: str) -> bytes:
        """手机号转BCD码（6字节）"""
        # 补充到12位
        phone = phone.zfill(12)
        return binascii.unhexlify(phone)
    
    def bcd_to_phone(self, bcd: bytes) -> str:
        """BCD码转手机号"""
        return binascii.hexlify(bcd).decode('ascii')
    
    def encode_message(self, msg_id: int, phone: str, body: bytes = b'') -> bytes:
        """
        编码消息
        """
        # 消息头
        header = struct.pack('>H', msg_id)  # 消息ID
        
        # 消息体属性
        body_len = len(body)
        body_attr = body_len & 0x03FF  # 低10位为消息体长度
        header += struct.pack('>H', body_attr)
        
        # 终端手机号（BCD码6字节）
        header += self.phone_to_bcd(phone)
        
        # 消息流水号
        header += struct.pack('>H', self.sequence_number)
        self.sequence_number = (self.sequence_number + 1) & 0xFFFF
        
        # 组合消息（不含标识位和校验码）
        message = header + body
        
        # 计算校验码
        checksum = self.calculate_checksum(message)
        
        # 添加校验码
        message += struct.pack('B', checksum)
        
        # 转义处理
        escaped_message = self.escape(message)
        
        # 添加标识位
        return struct.pack('B', self.FLAG) + escaped_message + struct.pack('B', self.FLAG)
    
    def decode_message(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        解码消息
        返回: {'msg_id': int, 'phone': str, 'sequence': int, 'body': bytes}
        """
        if len(data) < 2 or data[0] != self.FLAG or data[-1] != self.FLAG:
            return None
        
        # 去除标识位
        data = data[1:-1]
        
        # 反转义
        data = self.unescape(data)
        
        if len(data) < 13:  # 最小长度：消息头12字节+校验码1字节
            return None
        
        # 验证校验码
        checksum = self.calculate_checksum(data[:-1])
        if checksum != data[-1]:
            return None
        
        # 解析消息头
        msg_id = struct.unpack('>H', data[0:2])[0]
        body_attr = struct.unpack('>H', data[2:4])[0]
        phone = self.bcd_to_phone(data[4:10])
        sequence = struct.unpack('>H', data[10:12])[0]
        
        # 消息体长度
        body_len = body_attr & 0x03FF
        
        # 提取消息体
        body = data[12:12+body_len] if body_len > 0 else b''
        
        return {
            'msg_id': msg_id,
            'phone': phone,
            'sequence': sequence,
            'body': body,
            'body_attr': body_attr
        }
    
    def parse_position_data(self, body: bytes) -> Dict[str, Any]:
        """解析位置信息"""
        if len(body) < 28:
            return {}
        
        # 基本位置信息
        alarm_flag = struct.unpack('>I', body[0:4])[0]
        status = struct.unpack('>I', body[4:8])[0]
        latitude = struct.unpack('>I', body[8:12])[0] / 1000000.0
        longitude = struct.unpack('>I', body[12:16])[0] / 1000000.0
        altitude = struct.unpack('>H', body[16:18])[0]
        speed = struct.unpack('>H', body[18:20])[0] / 10.0
        direction = struct.unpack('>H', body[20:22])[0]
        
        # 时间（BCD码）
        time_bcd = body[22:28]
        time_str = '20' + ''.join([f'{b>>4}{b&0x0F}' for b in time_bcd])
        
        # 解析状态位
        acc_on = bool(status & 0x01)
        positioned = bool(status & 0x02)
        south_latitude = bool(status & 0x04)
        west_longitude = bool(status & 0x08)
        
        # 调整经纬度
        if south_latitude:
            latitude = -latitude
        if west_longitude:
            longitude = -longitude
        
        position_data = {
            'alarm_flag': alarm_flag,
            'status': status,
            'latitude': latitude,
            'longitude': longitude,
            'altitude': altitude,
            'speed': speed,
            'direction': direction,
            'time': time_str,
            'acc_on': acc_on,
            'positioned': positioned
        }
        
        # 解析附加信息
        index = 28
        while index < len(body) - 2:
            info_id = body[index]
            info_len = body[index + 1]
            
            if index + 2 + info_len > len(body):
                break
                
            info_data = body[index + 2:index + 2 + info_len]
            
            # 处理常见的附加信息
            if info_id == 0x01:  # 里程
                position_data['mileage'] = struct.unpack('>I', info_data)[0] / 10.0
            elif info_id == 0x30:  # 信号强度
                position_data['signal_strength'] = info_data[0]
            elif info_id == 0x31:  # 卫星数
                position_data['satellite_count'] = info_data[0]
                
            index += 2 + info_len
            
        return position_data
    
    def build_platform_common_reply(self, phone: str, reply_sequence: int, 
                                  reply_msg_id: int, result: int = 0) -> bytes:
        """构建平台通用应答"""
        body = struct.pack('>HHB', reply_sequence, reply_msg_id, result)
        return self.encode_message(self.MSG_ID['PLATFORM_COMMON_REPLY'], phone, body)
    
    def build_register_reply(self, phone: str, reply_sequence: int, 
                           result: int = 0, auth_code: str = '') -> bytes:
        """构建注册应答"""
        body = struct.pack('>HB', reply_sequence, result)
        if result == 0 and auth_code:
            body += auth_code.encode('gbk')
        return self.encode_message(self.MSG_ID['TERMINAL_REGISTER_REPLY'], phone, body)