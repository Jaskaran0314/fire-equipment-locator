// pages/map/map.js
const { get, post } = require('../../utils/request')
const { API, MAP_CONFIG } = require('../../utils/config')

Page({
  data: {
    devices: [],
    selectedDevice: null,
    latitude: MAP_CONFIG.DEFAULT_CENTER.latitude,
    longitude: MAP_CONFIG.DEFAULT_CENTER.longitude,
    scale: MAP_CONFIG.DEFAULT_ZOOM,
    markers: [],
    showConfirmDialog: false,
    confirmLocation: null
  },

  onLoad(options) {
    // 如果传入了设备参数，只显示该设备
    if (options.device) {
      const device = JSON.parse(decodeURIComponent(options.device))
      this.setData({
        selectedDevice: device,
        devices: [device]
      })
      this.updateMarkers([device])
      
      // 如果设备有位置，定位到设备位置
      if (device.last_position) {
        this.setData({
          latitude: device.last_position.lat,
          longitude: device.last_position.lng
        })
      }
    } else {
      // 显示所有设备
      this.loadAllDevices()
    }
    
    // 获取地图上下文
    this.mapCtx = wx.createMapContext('map')
  },

  // 加载所有设备
  async loadAllDevices() {
    try {
      const res = await get(API.DEVICES)
      const devices = res.data.filter(d => d.last_position)
      this.setData({ devices })
      this.updateMarkers(devices)
      
      // 如果有设备，显示所有设备
      if (devices.length > 0) {
        this.showAllDevices()
      }
    } catch (err) {
      console.error('加载设备失败:', err)
    }
  },

  // 更新地图标记
  updateMarkers(devices) {
    const markers = devices.map((device, index) => {
      const marker = {
        id: index,
        latitude: device.last_position.lat,
        longitude: device.last_position.lng,
        title: device.device_name,
        iconPath: '/images/marker.png',
        width: 40,
        height: 40,
        callout: {
          content: `${device.device_name}\n${device.device_id}`,
          padding: 10,
          borderRadius: 5,
          display: 'BYCLICK'
        }
      }
      
      // 如果有报警，使用红色标记
      if (device.active_alarms && device.active_alarms.length > 0) {
        marker.iconPath = '/images/marker-alarm.png'
      }
      
      // 如果是确认的位置，添加范围圈
      if (device.location) {
        // 添加范围标记（这里只是示例，实际需要使用circles）
        marker.label = {
          content: '确认位置',
          anchorX: 0,
          anchorY: -35,
          bgColor: '#fff',
          borderRadius: 3,
          borderWidth: 1,
          borderColor: '#ccc',
          padding: 5
        }
      }
      
      return marker
    })
    
    this.setData({ markers })
  },

  // 显示所有设备
  showAllDevices() {
    this.mapCtx.includePoints({
      points: this.data.markers.map(m => ({
        latitude: m.latitude,
        longitude: m.longitude
      })),
      padding: [50, 50, 50, 50]
    })
  },

  // 标记点击事件
  onMarkerTap(e) {
    const { markerId } = e.detail
    const device = this.data.devices[markerId]
    if (device) {
      this.setData({ selectedDevice: device })
      this.showDeviceInfo(device)
    }
  },

  // 显示设备信息
  showDeviceInfo(device) {
    wx.showModal({
      title: device.device_name,
      content: `设备ID: ${device.device_id}\n所属机构: ${device.organization}\n联系人: ${device.contact_person}\n状态: ${device.terminal_status === 'online' ? '在线' : '离线'}`,
      confirmText: '确认位置',
      cancelText: '关闭',
      success: (res) => {
        if (res.confirm) {
          this.confirmDeviceLocation(device)
        }
      }
    })
  },

  // 地图点击事件
  onMapTap(e) {
    // 如果已选择设备，可以确认新位置
    if (this.data.selectedDevice) {
      const { latitude, longitude } = e.detail
      this.setData({
        confirmLocation: { lat: latitude, lng: longitude },
        showConfirmDialog: true
      })
    }
  },

  // 确认设备位置
  async confirmDeviceLocation(device) {
    if (!device) return
    
    wx.showModal({
      title: '确认设备位置',
      content: '是否将当前位置设为设备的确认位置？超过20米将触发报警。',
      success: async (res) => {
        if (res.confirm) {
          const location = device.last_position || {
            lat: this.data.latitude,
            lng: this.data.longitude
          }
          
          try {
            await post(API.DEVICE_CONFIRM_LOCATION(device.device_id), {
              location
            })
            
            wx.showToast({
              title: '位置确认成功',
              icon: 'success'
            })
            
            // 刷新设备列表
            if (this.data.devices.length > 1) {
              this.loadAllDevices()
            }
          } catch (err) {
            console.error('确认位置失败:', err)
          }
        }
      }
    })
  },

  // 确认新位置
  async confirmNewLocation() {
    const { selectedDevice, confirmLocation } = this.data
    if (!selectedDevice || !confirmLocation) return
    
    try {
      await post(API.DEVICE_CONFIRM_LOCATION(selectedDevice.device_id), {
        location: confirmLocation
      })
      
      wx.showToast({
        title: '位置确认成功',
        icon: 'success'
      })
      
      this.setData({
        showConfirmDialog: false,
        confirmLocation: null
      })
      
      // 刷新设备
      this.loadAllDevices()
    } catch (err) {
      console.error('确认位置失败:', err)
    }
  },

  // 取消确认
  cancelConfirm() {
    this.setData({
      showConfirmDialog: false,
      confirmLocation: null
    })
  },

  // 定位到当前位置
  moveToLocation() {
    wx.getLocation({
      type: 'gcj02',
      success: (res) => {
        this.setData({
          latitude: res.latitude,
          longitude: res.longitude,
          scale: 16
        })
      },
      fail: () => {
        wx.showToast({
          title: '获取位置失败',
          icon: 'none'
        })
      }
    })
  }
})