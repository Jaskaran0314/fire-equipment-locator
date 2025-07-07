// pages/alarm/alarm.js
const { get } = require('../../utils/request')
const { API, ALARM_TYPES } = require('../../utils/config')

Page({
  data: {
    alarms: [],
    devices: [],
    selectedDeviceId: '',
    deviceIndex: -1,
    showActive: true,
    loading: false,
    alarmTypes: ALARM_TYPES
  },

  onLoad() {
    this.loadDevices()
    this.loadAlarms()
  },

  onShow() {
    // 页面显示时刷新数据
    this.loadAlarms()
  },

  // 加载设备列表
  async loadDevices() {
    try {
      const res = await get(API.DEVICES)
      const devices = [{ device_id: '', device_name: '全部设备' }, ...res.data]
      this.setData({ devices })
    } catch (err) {
      console.error('加载设备列表失败:', err)
    }
  },

  // 加载报警列表
  async loadAlarms() {
    this.setData({ loading: true })
    
    try {
      const params = {
        active_only: this.data.showActive
      }
      
      if (this.data.selectedDeviceId) {
        params.device_id = this.data.selectedDeviceId
      }
      
      const res = await get(API.ALARMS, params)
      this.setData({
        alarms: res.data
      })
    } catch (err) {
      console.error('加载报警列表失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  // 下拉刷新
  async onPullDownRefresh() {
    await this.loadAlarms()
    wx.stopPullDownRefresh()
  },

  // 设备筛选
  onDeviceChange(e) {
    const index = e.detail.value
    const device = this.data.devices[index]
    
    this.setData({
      deviceIndex: index,
      selectedDeviceId: device.device_id
    })
    
    this.loadAlarms()
  },

  // 切换显示模式
  onTabChange(e) {
    const { type } = e.currentTarget.dataset
    const showActive = type === 'active'
    
    this.setData({ showActive })
    this.loadAlarms()
  },

  // 查看设备详情
  goToDevice(e) {
    const { deviceId } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/device-detail/device-detail?id=${deviceId}`
    })
  },

  // 查看地图位置
  goToMap(e) {
    const { alarm } = e.currentTarget.dataset
    if (alarm.alarm_location) {
      // 构造设备对象用于地图显示
      const device = {
        device_id: alarm.device_id,
        device_name: alarm.device_name,
        organization: alarm.organization,
        last_position: alarm.alarm_location,
        active_alarms: [alarm]
      }
      
      const params = encodeURIComponent(JSON.stringify(device))
      wx.navigateTo({
        url: `/pages/map/map?device=${params}`
      })
    } else {
      wx.showToast({
        title: '无位置信息',
        icon: 'none'
      })
    }
  },

  // 格式化时间
  formatTime(timeStr) {
    if (!timeStr) return ''
    
    const date = new Date(timeStr)
    const now = new Date()
    const diff = now - date
    
    // 小于1小时显示分钟
    if (diff < 3600000) {
      const minutes = Math.floor(diff / 60000)
      return minutes <= 0 ? '刚刚' : `${minutes}分钟前`
    }
    
    // 小于24小时显示小时
    if (diff < 86400000) {
      const hours = Math.floor(diff / 3600000)
      return `${hours}小时前`
    }
    
    // 否则显示日期时间
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hour = String(date.getHours()).padStart(2, '0')
    const minute = String(date.getMinutes()).padStart(2, '0')
    
    if (year === now.getFullYear()) {
      return `${month}-${day} ${hour}:${minute}`
    }
    
    return `${year}-${month}-${day} ${hour}:${minute}`
  },

  // 获取报警类型文本
  getAlarmTypeText(type) {
    return this.data.alarmTypes[type] || type
  },

  // 获取报警样式
  getAlarmClass(alarm) {
    return alarm.alarm_type === 'move' ? 'alarm-move' : 'alarm-offline'
  }
})