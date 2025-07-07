/**
 * 全局配置文件
 */

// API基础地址
const BASE_URL = 'http://localhost:5000/api'

// API接口定义
const API = {
  // 认证相关
  LOGIN: '/auth/login',
  LOGOUT: '/auth/logout',
  CURRENT_USER: '/auth/current',
  
  // 用户管理
  USERS: '/users',
  USER_DETAIL: (id) => `/users/${id}`,
  
  // 设备管理
  DEVICES: '/devices',
  DEVICE_DETAIL: (id) => `/devices/${id}`,
  DEVICE_CONFIRM_LOCATION: (id) => `/devices/${id}/confirm-location`,
  DEVICE_TRACKS: (id) => `/devices/${id}/tracks`,
  
  // 终端管理
  TERMINALS: '/terminals',
  ALL_TERMINALS: '/terminals/all',
  
  // 报警管理
  ALARMS: '/alarms',
}

// 地图配置
const MAP_CONFIG = {
  // 默认中心点（北京）
  DEFAULT_CENTER: {
    latitude: 39.9042,
    longitude: 116.4074
  },
  // 默认缩放级别
  DEFAULT_ZOOM: 15
}

// 报警类型
const ALARM_TYPES = {
  move: '移动报警',
  offline: '掉线报警'
}

// 设备类型
const DEVICE_TYPES = [
  '焊接设备',
  '切割设备',
  '热处理设备',
  '其他动火设备'
]

module.exports = {
  BASE_URL,
  API,
  MAP_CONFIG,
  ALARM_TYPES,
  DEVICE_TYPES
}