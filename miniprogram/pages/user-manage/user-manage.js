// pages/user-manage/user-manage.js
const { get, post, put, del } = require('../../utils/request')
const { API } = require('../../utils/config')

Page({
  data: {
    userInfo: null,
    users: [],
    showUserModal: false,
    modalType: 'add', // add or edit
    editingUser: null,
    formData: {
      username: '',
      password: '',
      real_name: '',
      phone: '',
      is_admin: false
    },
    loading: false
  },

  onLoad() {
    // 获取当前用户信息
    const userInfo = getApp().globalData.userInfo
    this.setData({ userInfo })
    
    // 如果是管理员，加载用户列表
    if (userInfo && userInfo.is_admin) {
      this.loadUsers()
    }
  },

  onShow() {
    // 刷新当前用户信息
    this.loadCurrentUser()
  },

  // 加载当前用户信息
  async loadCurrentUser() {
    try {
      const res = await get(API.CURRENT_USER)
      this.setData({
        userInfo: res.data
      })
      getApp().globalData.userInfo = res.data
    } catch (err) {
      console.error('加载用户信息失败:', err)
    }
  },

  // 加载用户列表（管理员）
  async loadUsers() {
    try {
      const res = await get(API.USERS)
      this.setData({
        users: res.data
      })
    } catch (err) {
      console.error('加载用户列表失败:', err)
    }
  },

  // 下拉刷新
  async onPullDownRefresh() {
    await this.loadCurrentUser()
    if (this.data.userInfo && this.data.userInfo.is_admin) {
      await this.loadUsers()
    }
    wx.stopPullDownRefresh()
  },

  // 退出登录
  logout() {
    wx.showModal({
      title: '提示',
      content: '确定要退出登录吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await post(API.LOGOUT)
            
            // 清除存储
            wx.removeStorageSync('userInfo')
            wx.removeStorageSync('token')
            
            // 跳转到登录页
            wx.reLaunch({
              url: '/pages/login/login'
            })
          } catch (err) {
            console.error('退出登录失败:', err)
          }
        }
      }
    })
  },

  // 显示添加用户弹窗
  showAddUser() {
    this.setData({
      showUserModal: true,
      modalType: 'add',
      editingUser: null,
      formData: {
        username: '',
        password: '',
        real_name: '',
        phone: '',
        is_admin: false
      }
    })
  },

  // 显示编辑用户弹窗
  showEditUser(e) {
    const { user } = e.currentTarget.dataset
    this.setData({
      showUserModal: true,
      modalType: 'edit',
      editingUser: user,
      formData: {
        username: user.username,
        password: '',
        real_name: user.real_name,
        phone: user.phone,
        is_admin: user.is_admin
      }
    })
  },

  // 关闭弹窗
  closeModal() {
    this.setData({
      showUserModal: false
    })
  },

  // 输入处理
  onInput(e) {
    const { field } = e.currentTarget.dataset
    const { value } = e.detail
    this.setData({
      [`formData.${field}`]: value
    })
  },

  // 切换管理员权限
  onAdminChange(e) {
    this.setData({
      'formData.is_admin': e.detail.value
    })
  },

  // 验证表单
  validateForm() {
    const { formData, modalType } = this.data
    
    if (!formData.username) {
      wx.showToast({
        title: '请输入用户名',
        icon: 'none'
      })
      return false
    }
    
    if (modalType === 'add' && !formData.password) {
      wx.showToast({
        title: '请输入密码',
        icon: 'none'
      })
      return false
    }
    
    if (!formData.real_name) {
      wx.showToast({
        title: '请输入真实姓名',
        icon: 'none'
      })
      return false
    }
    
    if (!formData.phone) {
      wx.showToast({
        title: '请输入联系方式',
        icon: 'none'
      })
      return false
    }
    
    // 验证手机号格式
    const phoneReg = /^1[3-9]\d{9}$/
    if (!phoneReg.test(formData.phone)) {
      wx.showToast({
        title: '请输入正确的手机号',
        icon: 'none'
      })
      return false
    }
    
    return true
  },

  // 保存用户
  async saveUser() {
    if (!this.validateForm()) {
      return
    }
    
    this.setData({ loading: true })
    
    try {
      const { modalType, editingUser, formData } = this.data
      
      if (modalType === 'add') {
        // 创建用户
        await post(API.USERS, formData)
        wx.showToast({
          title: '创建成功',
          icon: 'success'
        })
      } else {
        // 更新用户
        const updateData = { ...formData }
        if (!updateData.password) {
          delete updateData.password
        }
        
        await put(API.USER_DETAIL(editingUser.id), updateData)
        wx.showToast({
          title: '更新成功',
          icon: 'success'
        })
      }
      
      // 关闭弹窗并刷新列表
      this.closeModal()
      this.loadUsers()
      
    } catch (err) {
      console.error('保存用户失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  // 删除用户
  deleteUser(e) {
    const { user } = e.currentTarget.dataset
    
    wx.showModal({
      title: '确认删除',
      content: `确定要删除用户"${user.real_name}"吗？`,
      success: async (res) => {
        if (res.confirm) {
          try {
            await del(API.USER_DETAIL(user.id))
            wx.showToast({
              title: '删除成功',
              icon: 'success'
            })
            this.loadUsers()
          } catch (err) {
            console.error('删除用户失败:', err)
          }
        }
      }
    })
  },

  // 拨打电话
  makePhoneCall(e) {
    const { phone } = e.currentTarget.dataset
    wx.makePhoneCall({
      phoneNumber: phone
    })
  }
})