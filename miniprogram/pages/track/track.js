// pages/track/track.js
const { get } = require('../../utils/request')
const { API, MAP_CONFIG } = require('../../utils/config')

Page({
  data: {
    deviceId: '',
    device: null,
    tracks: [],
    polyline: [],
    markers: [],
    latitude: MAP_CONFIG.DEFAULT_CENTER.latitude,
    longitude: MAP_CONFIG.DEFAULT_CENTER.longitude,
    scale: MAP_CONFIG.DEFAULT_ZOOM,
    startDate: '',
    endDate: '',
    loading: false,
    playing: false,
    playIndex: 0,
    playTimer: null
  },

  onLoad(options) {
    if (options.deviceId) {
      this.setData({ deviceId: options.deviceId })
      
      // 设置默认时间范围（最近24小时）
      const now = new Date()
      const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000)
      
      this.setData({
        startDate: this.formatDate(yesterday),
        endDate: this.formatDate(now)
      })
      
      // 加载设备信息和轨迹
      this.loadDevice()
      this.loadTracks()
    } else {
      wx.showToast({
        title: '设备ID不能为空',
        icon: 'none'
      })
      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
    }
    
    // 获取地图上下文
    this.mapCtx = wx.createMapContext('trackMap')
  },

  onUnload() {
    // 清理定时器
    if (this.data.playTimer) {
      clearInterval(this.data.playTimer)
    }
  },

  // 加载设备信息
  async loadDevice() {
    try {
      const res = await get(API.DEVICE_DETAIL(this.data.deviceId))
      this.setData({ device: res.data })
    } catch (err) {
      console.error('加载设备信息失败:', err)
    }
  },

  // 加载轨迹数据
  async loadTracks() {
    this.setData({ loading: true })
    
    try {
      // 构建时间参数
      const startTime = new Date(this.data.startDate + ' 00:00:00').toISOString()
      const endTime = new Date(this.data.endDate + ' 23:59:59').toISOString()
      
      const res = await get(API.DEVICE_TRACKS(this.data.deviceId), {
        start_time: startTime,
        end_time: endTime
      })
      
      const tracks = res.data
      
      if (tracks.length > 0) {
        // 生成轨迹线
        const points = tracks.map(track => ({
          longitude: track.location.lng,
          latitude: track.location.lat
        }))
        
        const polyline = [{
          points: points,
          color: '#1989FA',
          width: 4,
          dottedLine: false
        }]
        
        // 生成标记点（起点和终点）
        const markers = []
        
        // 起点
        markers.push({
          id: 0,
          latitude: tracks[tracks.length - 1].location.lat,
          longitude: tracks[tracks.length - 1].location.lng,
          iconPath: '/images/start-marker.png',
          width: 30,
          height: 30,
          label: {
            content: '起点',
            anchorY: -35,
            bgColor: '#fff',
            padding: 5,
            borderRadius: 3,
            borderWidth: 1,
            borderColor: '#ccc'
          }
        })
        
        // 终点
        markers.push({
          id: 1,
          latitude: tracks[0].location.lat,
          longitude: tracks[0].location.lng,
          iconPath: '/images/end-marker.png',
          width: 30,
          height: 30,
          label: {
            content: '终点',
            anchorY: -35,
            bgColor: '#fff',
            padding: 5,
            borderRadius: 3,
            borderWidth: 1,
            borderColor: '#ccc'
          }
        })
        
        this.setData({
          tracks: tracks.reverse(), // 倒序，使最早的在前
          polyline,
          markers
        })
        
        // 显示全部轨迹
        this.showFullTrack()
      } else {
        wx.showToast({
          title: '该时间段内无轨迹数据',
          icon: 'none'
        })
        this.setData({
          tracks: [],
          polyline: [],
          markers: []
        })
      }
    } catch (err) {
      console.error('加载轨迹失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  // 显示完整轨迹
  showFullTrack() {
    if (this.data.tracks.length === 0) return
    
    const points = this.data.tracks.map(track => ({
      latitude: track.location.lat,
      longitude: track.location.lng
    }))
    
    this.mapCtx.includePoints({
      points,
      padding: [50, 50, 50, 50]
    })
  },

  // 开始日期选择
  onStartDateChange(e) {
    this.setData({
      startDate: e.detail.value
    })
  },

  // 结束日期选择
  onEndDateChange(e) {
    this.setData({
      endDate: e.detail.value
    })
  },

  // 查询轨迹
  queryTracks() {
    // 验证日期
    const start = new Date(this.data.startDate)
    const end = new Date(this.data.endDate)
    
    if (start > end) {
      wx.showToast({
        title: '开始日期不能大于结束日期',
        icon: 'none'
      })
      return
    }
    
    // 重新加载轨迹
    this.loadTracks()
  },

  // 播放轨迹
  playTrack() {
    if (this.data.tracks.length === 0) {
      wx.showToast({
        title: '无轨迹数据',
        icon: 'none'
      })
      return
    }
    
    this.setData({
      playing: true,
      playIndex: 0
    })
    
    // 添加移动标记
    const track = this.data.tracks[0]
    const movingMarker = {
      id: 999,
      latitude: track.location.lat,
      longitude: track.location.lng,
      iconPath: '/images/car.png',
      width: 40,
      height: 40,
      rotate: track.direction || 0
    }
    
    const markers = [...this.data.markers, movingMarker]
    this.setData({ markers })
    
    // 开始播放
    this.data.playTimer = setInterval(() => {
      this.moveNext()
    }, 1000)
  },

  // 停止播放
  stopTrack() {
    if (this.data.playTimer) {
      clearInterval(this.data.playTimer)
      this.data.playTimer = null
    }
    
    this.setData({
      playing: false,
      playIndex: 0
    })
    
    // 移除移动标记
    const markers = this.data.markers.filter(m => m.id !== 999)
    this.setData({ markers })
  },

  // 移动到下一个点
  moveNext() {
    const { tracks, playIndex } = this.data
    
    if (playIndex >= tracks.length - 1) {
      // 播放结束
      this.stopTrack()
      wx.showToast({
        title: '轨迹播放完成',
        icon: 'none'
      })
      return
    }
    
    const nextIndex = playIndex + 1
    const track = tracks[nextIndex]
    
    // 更新移动标记位置
    const markers = this.data.markers.map(marker => {
      if (marker.id === 999) {
        return {
          ...marker,
          latitude: track.location.lat,
          longitude: track.location.lng,
          rotate: track.direction || 0
        }
      }
      return marker
    })
    
    this.setData({
      markers,
      playIndex: nextIndex,
      latitude: track.location.lat,
      longitude: track.location.lng
    })
  },

  // 格式化日期
  formatDate(date) {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  },

  // 格式化时间
  formatTime(timeStr) {
    if (!timeStr) return ''
    
    const date = new Date(timeStr)
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hour = String(date.getHours()).padStart(2, '0')
    const minute = String(date.getMinutes()).padStart(2, '0')
    const second = String(date.getSeconds()).padStart(2, '0')
    
    return `${month}-${day} ${hour}:${minute}:${second}`
  },

  // 计算总里程
  getTotalDistance() {
    const { tracks } = this.data
    if (tracks.length < 2) return '0'
    
    let totalDistance = 0
    for (let i = 1; i < tracks.length; i++) {
      const prev = tracks[i - 1].location
      const curr = tracks[i].location
      
      // 简单的距离计算（实际应该使用更精确的算法）
      const distance = Math.sqrt(
        Math.pow((curr.lat - prev.lat) * 111000, 2) +
        Math.pow((curr.lng - prev.lng) * 111000 * Math.cos(curr.lat * Math.PI / 180), 2)
      )
      
      totalDistance += distance
    }
    
    // 转换为公里
    return (totalDistance / 1000).toFixed(2)
  }
})