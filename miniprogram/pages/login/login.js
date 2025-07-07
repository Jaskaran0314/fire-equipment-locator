// pages/login/login.js
const { post } = require('../../utils/request')
const { API } = require('../../utils/config')

Page({
  data: {
    username: '',
    password: '',
    loading: false
  },

  onLoad() {
    // 清除存储的登录信息
    wx.removeStorageSync('userInfo')
    wx.removeStorageSync('token')
  },

  // 输入用户名
  onUsernameInput(e) {
    this.setData({
      username: e.detail.value
    })
  },

  // 输入密码
  onPasswordInput(e) {
    this.setData({
      password: e.detail.value
    })
  },

  // 登录
  async login() {
    const { username, password } = this.data
    
    if (!username || !password) {
      wx.showToast({
        title: '请输入用户名和密码',
        icon: 'none'
      })
      return
    }

    this.setData({ loading: true })

    try {
      const res = await post(API.LOGIN, {
        username,
        password
      })
      
      // 保存用户信息
      wx.setStorageSync('userInfo', res.data)
      
      // 更新全局数据
      getApp().globalData.userInfo = res.data
      
      wx.showToast({
        title: '登录成功',
        icon: 'success'
      })
      
      // 跳转到首页
      setTimeout(() => {
        wx.switchTab({
          url: '/pages/device-list/device-list'
        })
      }, 500)
      
    } catch (err) {
      console.error('登录失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  }
})