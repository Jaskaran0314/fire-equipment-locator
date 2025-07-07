/**
 * HTTP请求工具函数
 */
const { BASE_URL } = require('./config')

/**
 * 请求封装
 */
function request(options) {
  return new Promise((resolve, reject) => {
    // 显示加载中
    wx.showLoading({
      title: '加载中...',
      mask: true
    })
    
    // 获取token
    const token = wx.getStorageSync('token')
    
    wx.request({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'content-type': options.contentType || 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
        ...options.header
      },
      success: (res) => {
        wx.hideLoading()
        
        if (res.statusCode === 200) {
          if (res.data.code === 200) {
            resolve(res.data)
          } else if (res.data.code === 401) {
            // 未授权，跳转登录
            wx.removeStorageSync('token')
            wx.removeStorageSync('userInfo')
            wx.redirectTo({
              url: '/pages/login/login'
            })
            reject(res.data)
          } else {
            wx.showToast({
              title: res.data.message || '请求失败',
              icon: 'none'
            })
            reject(res.data)
          }
        } else {
          wx.showToast({
            title: '网络错误',
            icon: 'none'
          })
          reject(res)
        }
      },
      fail: (err) => {
        wx.hideLoading()
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        })
        reject(err)
      }
    })
  })
}

/**
 * GET请求
 */
function get(url, data) {
  return request({
    url,
    method: 'GET',
    data
  })
}

/**
 * POST请求
 */
function post(url, data) {
  return request({
    url,
    method: 'POST',
    data
  })
}

/**
 * PUT请求
 */
function put(url, data) {
  return request({
    url,
    method: 'PUT',
    data
  })
}

/**
 * DELETE请求
 */
function del(url, data) {
  return request({
    url,
    method: 'DELETE',
    data
  })
}

module.exports = {
  request,
  get,
  post,
  put,
  del
}