// pages/device-list/device-list.js
const { get } = require('../../utils/request')
const { API } = require('../../utils/config')

Page({
  data: {
    devices: [],
    loading: false,
    userInfo: null
  },

  onLoad() {
    this.setData({
      userInfo: getApp().globalData.userInfo
    })
  },

  onShow() {
    this.loadDevices()
  },

  // 加载设备列表
  async loadDevices() {
    this.setData({ loading: true })
    
    try {
      const res = await get(API.DEVICES)
      this.setData({
        devices: res.data
      })
    } catch (err) {
      console.error('加载设备列表失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  // 下拉刷新
  async onPullDownRefresh() {
    await this.loadDevices()
    wx.stopPullDownRefresh()
  },

  // 跳转到设备详情
  goToDetail(e) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/device-detail/device-detail?id=${id}`
    })
  },

  // 跳转到新增设备
  goToAdd() {
    wx.navigateTo({
      url: '/pages/device-edit/device-edit'
    })
  },

  // 跳转到地图页
  goToMap(e) {
    const { device } = e.currentTarget.dataset
    const params = encodeURIComponent(JSON.stringify(device))
    wx.navigateTo({
      url: `/pages/map/map?device=${params}`
    })
  },

  // 跳转到轨迹页
  goToTrack(e) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/track/track?deviceId=${id}`
    })
  },

  // 格式化状态
  formatStatus(device) {
    if (device.terminal_status === 'unbound') {
      return '未绑定'
    } else if (device.terminal_status === 'online') {
      return '在线'
    } else {
      return '离线'
    }
  },

  // 获取状态样式
  getStatusClass(device) {
    if (device.terminal_status === 'unbound') {
      return 'status-unbound'
    } else if (device.terminal_status === 'online') {
      return 'status-online'
    } else {
      return 'status-offline'
    }
  },

  // 是否有报警
  hasAlarm(device) {
    return device.active_alarms && device.active_alarms.length > 0
  }
})