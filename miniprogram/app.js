// app.js
App({
  onLaunch() {
    // 展示本地存储能力
    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)

    // 检查登录状态
    this.checkLogin()
  },
  
  checkLogin() {
    // 检查是否有用户信息
    const userInfo = wx.getStorageSync('userInfo')
    if (!userInfo) {
      // 未登录，跳转到登录页
      wx.redirectTo({
        url: '/pages/login/login'
      })
    } else {
      this.globalData.userInfo = userInfo
    }
  },
  
  globalData: {
    userInfo: null,
    systemInfo: null
  }
})
