// pages/device-detail/device-detail.js
const { get, del } = require('../../utils/request')
const { API } = require('../../utils/config')

Page({
  data: {
    deviceId: '',
    device: null,
    loading: false,
    userInfo: null
  },

  onLoad(options) {
    if (options.id) {
      this.setData({
        deviceId: options.id,
        userInfo: getApp().globalData.userInfo
      })
      this.loadDevice()
    } else {
      wx.showToast({
        title: '设备ID不能为空',
        icon: 'none'
      })
      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
    }
  },

  onShow() {
    // 页面显示时刷新数据
    if (this.data.deviceId) {
      this.loadDevice()
    }
  },

  // 加载设备详情
  async loadDevice() {
    this.setData({ loading: true })
    
    try {
      const res = await get(API.DEVICE_DETAIL(this.data.deviceId))
      this.setData({
        device: res.data
      })
    } catch (err) {
      console.error('加载设备详情失败:', err)
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      })
    } finally {
      this.setData({ loading: false })
    }
  },

  // 下拉刷新
  async onPullDownRefresh() {
    await this.loadDevice()
    wx.stopPullDownRefresh()
  },

  // 编辑设备
  editDevice() {
    wx.navigateTo({
      url: `/pages/device-edit/device-edit?id=${this.data.deviceId}`
    })
  },

  // 删除设备
  deleteDevice() {
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这个设备吗？删除后无法恢复。',
      confirmText: '删除',
      confirmColor: '#ff4444',
      success: async (res) => {
        if (res.confirm) {
          try {
            await del(API.DEVICE_DETAIL(this.data.deviceId))
            wx.showToast({
              title: '删除成功',
              icon: 'success'
            })
            
            // 返回上一页
            setTimeout(() => {
              wx.navigateBack()
            }, 500)
          } catch (err) {
            console.error('删除设备失败:', err)
          }
        }
      }
    })
  },

  // 查看地图位置
  goToMap() {
    const { device } = this.data
    if (device.last_position || device.location) {
      const params = encodeURIComponent(JSON.stringify(device))
      wx.navigateTo({
        url: `/pages/map/map?device=${params}`
      })
    } else {
      wx.showToast({
        title: '暂无位置信息',
        icon: 'none'
      })
    }
  },

  // 查看轨迹
  goToTrack() {
    if (this.data.device.terminal_status === 'online') {
      wx.navigateTo({
        url: `/pages/track/track?deviceId=${this.data.deviceId}`
      })
    } else {
      wx.showToast({
        title: '设备离线或未绑定终端',
        icon: 'none'
      })
    }
  },

  // 拨打电话
  makePhoneCall() {
    const { device } = this.data
    if (device && device.contact_phone) {
      wx.makePhoneCall({
        phoneNumber: device.contact_phone,
        fail: (err) => {
          console.error('拨打电话失败:', err)
        }
      })
    }
  },

  // 格式化时间
  formatTime(timeStr) {
    if (!timeStr) return '无'
    
    const date = new Date(timeStr)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hour = String(date.getHours()).padStart(2, '0')
    const minute = String(date.getMinutes()).padStart(2, '0')
    
    return `${year}-${month}-${day} ${hour}:${minute}`
  },

  // 获取状态文本
  getStatusText(device) {
    if (!device) return ''
    
    if (device.terminal_status === 'unbound') {
      return '未绑定终端'
    } else if (device.terminal_status === 'online') {
      return '在线'
    } else {
      return '离线'
    }
  },

  // 获取状态样式
  getStatusClass(device) {
    if (!device) return ''
    
    if (device.terminal_status === 'unbound') {
      return 'status-unbound'
    } else if (device.terminal_status === 'online') {
      return 'status-online'
    } else {
      return 'status-offline'
    }
  }
})