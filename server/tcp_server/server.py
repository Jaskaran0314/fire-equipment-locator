"""
TCP服务器 - 处理M63定位终端连接
监听7788端口
"""
import socket
import threading
import time
import logging
from datetime import datetime
from typing import Dict, Optional
from protocol import M63Protocol

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TCPServer')

class TerminalConnection:
    """终端连接管理"""
    def __init__(self, socket, address, terminal_id=None):
        self.socket = socket
        self.address = address
        self.terminal_id = terminal_id
        self.phone: Optional[str] = None
        self.auth_code: Optional[str] = None
        self.last_heartbeat = time.time()
        self.last_position: Optional[Dict] = None
        self.is_authenticated = False
        self.buffer = bytearray()
        
class TCPServer:
    def __init__(self, host='0.0.0.0', port=7788):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.connections: Dict[str, TerminalConnection] = {}  # terminal_id -> connection
        self.protocol = M63Protocol()
        self.position_callback = None  # 位置更新回调
        self.status_callback = None    # 状态更新回调
        
    def set_position_callback(self, callback):
        """设置位置更新回调函数"""
        self.position_callback = callback
        
    def set_status_callback(self, callback):
        """设置状态更新回调函数"""
        self.status_callback = callback
        
    def start(self):
        """启动服务器"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(100)
        self.running = True
        
        logger.info(f"TCP服务器启动，监听 {self.host}:{self.port}")
        
        # 启动心跳检查线程
        threading.Thread(target=self._check_heartbeat, daemon=True).start()
        
        # 接受连接
        threading.Thread(target=self._accept_connections, daemon=True).start()
        
    def stop(self):
        """停止服务器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        
        # 关闭所有连接
        for conn in self.connections.values():
            conn.socket.close()
        self.connections.clear()
        
        logger.info("TCP服务器已停止")
        
    def _accept_connections(self):
        """接受客户端连接"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                logger.info(f"新连接来自: {address}")
                
                # 创建连接对象
                conn = TerminalConnection(client_socket, address)
                
                # 启动处理线程
                threading.Thread(
                    target=self._handle_connection,
                    args=(conn,),
                    daemon=True
                ).start()
                
            except Exception as e:
                if self.running:
                    logger.error(f"接受连接错误: {e}")
                    
    def _handle_connection(self, conn: TerminalConnection):
        """处理单个连接"""
        try:
            while self.running:
                # 接收数据
                data = conn.socket.recv(4096)
                if not data:
                    break
                    
                # 添加到缓冲区
                conn.buffer.extend(data)
                
                # 处理缓冲区中的消息
                self._process_buffer(conn)
                
        except Exception as e:
            logger.error(f"处理连接错误 {conn.address}: {e}")
        finally:
            self._remove_connection(conn)
            conn.socket.close()
            
    def _process_buffer(self, conn: TerminalConnection):
        """处理缓冲区中的消息"""
        while True:
            # 查找消息开始标志
            start = conn.buffer.find(0x7E)
            if start == -1:
                break
                
            # 查找消息结束标志
            end = conn.buffer.find(0x7E, start + 1)
            if end == -1:
                break
                
            # 提取完整消息
            message = bytes(conn.buffer[start:end + 1])
            conn.buffer = conn.buffer[end + 1:]
            
            # 处理消息
            self._process_message(conn, message)
            
    def _process_message(self, conn: TerminalConnection, message: bytes):
        """处理单条消息"""
        try:
            # 解码消息
            decoded = self.protocol.decode_message(message)
            if not decoded:
                logger.warning(f"无法解码消息: {message.hex()}")
                return
                
            msg_id = decoded['msg_id']
            phone = decoded['phone']
            sequence = decoded['sequence']
            body = decoded['body']
            
            logger.info(f"收到消息: ID=0x{msg_id:04X}, Phone={phone}, Seq={sequence}")
            
            # 根据消息ID处理
            if msg_id == 0x0100:  # 终端注册
                self._handle_register(conn, phone, sequence, body)
            elif msg_id == 0x0102:  # 终端鉴权
                self._handle_auth(conn, phone, sequence, body)
            elif msg_id == 0x0002:  # 心跳
                self._handle_heartbeat(conn, phone, sequence)
            elif msg_id == 0x0200:  # 位置汇报
                self._handle_position_report(conn, phone, sequence, body)
            elif msg_id == 0x0001:  # 终端通用应答
                logger.info(f"收到终端应答: {body.hex()}")
            else:
                logger.warning(f"未处理的消息类型: 0x{msg_id:04X}")
                
        except Exception as e:
            logger.error(f"处理消息错误: {e}")
            
    def _handle_register(self, conn: TerminalConnection, phone: str, sequence: int, body: bytes):
        """处理终端注册"""
        try:
            # 解析注册信息
            if len(body) >= 25:
                province_id = struct.unpack('>H', body[0:2])[0]
                city_id = struct.unpack('>H', body[2:4])[0]
                manufacturer_id = body[4:9]
                terminal_model = body[9:17].rstrip(b'\x00')
                terminal_id = body[17:24].rstrip(b'\x00').decode('ascii')
                
                # 车牌信息
                plate_color = body[24] if len(body) > 24 else 0
                plate_number = body[25:].decode('gbk') if len(body) > 25 else ''
                
                logger.info(f"终端注册: ID={terminal_id}, Model={terminal_model}, Plate={plate_number}")
                
                # 生成鉴权码
                auth_code = f"AUTH_{terminal_id}_{int(time.time())}"
                
                # 更新连接信息
                conn.terminal_id = terminal_id
                conn.phone = phone
                conn.auth_code = auth_code
                
                # 添加到连接列表
                self.connections[terminal_id] = conn
                
                # 发送注册应答
                reply = self.protocol.build_register_reply(phone, sequence, 0, auth_code)
                conn.socket.send(reply)
                
                # 更新状态回调
                if self.status_callback:
                    self.status_callback(terminal_id, 'registered', {
                        'phone': phone,
                        'model': terminal_model.decode('ascii', errors='ignore'),
                        'plate': plate_number
                    })
                    
        except Exception as e:
            logger.error(f"处理注册错误: {e}")
            # 发送失败应答
            reply = self.protocol.build_register_reply(phone, sequence, 1)
            conn.socket.send(reply)
            
    def _handle_auth(self, conn: TerminalConnection, phone: str, sequence: int, body: bytes):
        """处理终端鉴权"""
        try:
            auth_code = body.decode('gbk')
            logger.info(f"终端鉴权: {auth_code}")
            
            # 验证鉴权码
            if conn.auth_code == auth_code:
                conn.is_authenticated = True
                result = 0  # 成功
                
                # 更新状态
                if self.status_callback:
                    self.status_callback(conn.terminal_id, 'authenticated', {})
            else:
                result = 1  # 失败
                
            # 发送通用应答
            reply = self.protocol.build_platform_common_reply(phone, sequence, 0x0102, result)
            conn.socket.send(reply)
            
        except Exception as e:
            logger.error(f"处理鉴权错误: {e}")
            
    def _handle_heartbeat(self, conn: TerminalConnection, phone: str, sequence: int):
        """处理心跳"""
        conn.last_heartbeat = time.time()
        logger.debug(f"收到心跳: {conn.terminal_id}")
        
        # 发送通用应答
        reply = self.protocol.build_platform_common_reply(phone, sequence, 0x0002, 0)
        conn.socket.send(reply)
        
    def _handle_position_report(self, conn: TerminalConnection, phone: str, sequence: int, body: bytes):
        """处理位置汇报"""
        try:
            # 解析位置数据
            position = self.protocol.parse_position_data(body)
            position['terminal_id'] = conn.terminal_id
            position['phone'] = phone
            position['report_time'] = datetime.now().isoformat()
            
            logger.info(f"位置汇报: {conn.terminal_id} - Lat:{position['latitude']}, Lng:{position['longitude']}")
            
            # 更新最后位置
            conn.last_position = position
            
            # 调用位置回调
            if self.position_callback:
                self.position_callback(conn.terminal_id, position)
                
            # 发送通用应答
            reply = self.protocol.build_platform_common_reply(phone, sequence, 0x0200, 0)
            conn.socket.send(reply)
            
        except Exception as e:
            logger.error(f"处理位置汇报错误: {e}")
            
    def _check_heartbeat(self):
        """检查心跳超时"""
        while self.running:
            try:
                current_time = time.time()
                timeout_connections = []
                
                for terminal_id, conn in self.connections.items():
                    if current_time - conn.last_heartbeat > 180:  # 3分钟超时
                        timeout_connections.append(terminal_id)
                        
                # 处理超时连接
                for terminal_id in timeout_connections:
                    logger.warning(f"终端心跳超时: {terminal_id}")
                    if terminal_id in self.connections:
                        conn = self.connections[terminal_id]
                        self._remove_connection(conn)
                        conn.socket.close()
                        
                        # 更新状态
                        if self.status_callback:
                            self.status_callback(terminal_id, 'offline', {})
                            
            except Exception as e:
                logger.error(f"心跳检查错误: {e}")
                
            time.sleep(30)  # 每30秒检查一次
            
    def _remove_connection(self, conn: TerminalConnection):
        """移除连接"""
        if conn.terminal_id and conn.terminal_id in self.connections:
            del self.connections[conn.terminal_id]
            logger.info(f"连接断开: {conn.terminal_id}")
            
    def send_text_message(self, terminal_id: str, text: str) -> bool:
        """发送文本消息到终端"""
        if terminal_id not in self.connections:
            return False
            
        conn = self.connections[terminal_id]
        if not conn.is_authenticated or not conn.phone:
            return False
            
        try:
            # 构建文本消息
            body = b'\x00' + text.encode('gbk')  # 标志位0 + 文本内容
            message = self.protocol.encode_message(0x8300, conn.phone, body)
            conn.socket.send(message)
            return True
        except Exception as e:
            logger.error(f"发送文本消息错误: {e}")
            return False
            
    def query_position(self, terminal_id: str) -> bool:
        """查询终端位置"""
        if terminal_id not in self.connections:
            return False
            
        conn = self.connections[terminal_id]
        if not conn.is_authenticated or not conn.phone:
            return False
            
        try:
            # 发送位置查询
            message = self.protocol.encode_message(0x8201, conn.phone, b'')
            conn.socket.send(message)
            return True
        except Exception as e:
            logger.error(f"查询位置错误: {e}")
            return False
            
    def get_terminal_status(self, terminal_id: str) -> Optional[Dict]:
        """获取终端状态"""
        if terminal_id not in self.connections:
            return None
            
        conn = self.connections[terminal_id]
        return {
            'terminal_id': terminal_id,
            'phone': conn.phone,
            'online': True,
            'authenticated': conn.is_authenticated,
            'last_heartbeat': datetime.fromtimestamp(conn.last_heartbeat).isoformat(),
            'last_position': conn.last_position
        }
        
    def get_all_terminals(self) -> Dict[str, Dict]:
        """获取所有终端状态"""
        result = {}
        for terminal_id in self.connections:
            status = self.get_terminal_status(terminal_id)
            if status:
                result[terminal_id] = status
        return result

# 添加必要的导入
import struct