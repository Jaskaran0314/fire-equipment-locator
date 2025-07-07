// pages/device-edit/device-edit.js
const { get, post, put } = require('../../utils/request')
const { API, DEVICE_TYPES } = require('../../utils/config')

Page({
  data: {
    isEdit: false,
    deviceId: '',
    formData: {
      device_name: '',
      device_id: '',
      organization: '',
      contact_person: '',
      contact_phone: '',
      device_type: '',
      terminal_id: ''
    },
    deviceTypes: DEVICE_TYPES,
    typeIndex: 0,
    terminals: [],
    terminalIndex: -1,
    loading: false
  },

  onLoad(options) {
    if (options.id) {
      // 编辑模式
      this.setData({
        isEdit: true,
        deviceId: options.id
      })
      this.loadDevice(options.id)
    } else {
      // 新增模式，生成设备ID
      this.setData({
        'formData.device_id': this.generateDeviceId()
      })
    }
    
    // 加载可用终端
    this.loadTerminals()
  },

  // 生成设备ID
  generateDeviceId() {
    const timestamp = Date.now()
    const random = Math.floor(Math.random() * 1000)
    return `DEV${timestamp}${random}`
  },

  // 加载设备信息
  async loadDevice(deviceId) {
    try {
      const res = await get(API.DEVICE_DETAIL(deviceId))
      const device = res.data
      
      // 设置表单数据
      this.setData({
        formData: {
          device_name: device.device_name,
          device_id: device.device_id,
          organization: device.organization,
          contact_person: device.contact_person,
          contact_phone: device.contact_phone,
          device_type: device.device_type,
          terminal_id: device.terminal_id || ''
        }
      })
      
      // 设置设备类型选择器
      const typeIndex = DEVICE_TYPES.indexOf(device.device_type)
      if (typeIndex >= 0) {
        this.setData({ typeIndex })
      }
      
      // 设置终端选择器
      if (device.terminal_id) {
        const terminalIndex = this.data.terminals.findIndex(t => t.terminal_id === device.terminal_id)
        if (terminalIndex >= 0) {
          this.setData({ terminalIndex })
        }
      }
    } catch (err) {
      wx.showToast({
        title: '加载设备信息失败',
        icon: 'none'
      })
      console.error('加载设备信息失败:', err)
    }
  },

  // 加载可用终端
  async loadTerminals() {
    try {
      const res = await get(API.TERMINALS)
      // 只显示未绑定的终端
      const terminals = res.data.filter(t => !t.bound_device_id || t.bound_device_id === this.data.deviceId)
      
      this.setData({ terminals })
      
      // 如果是编辑模式且有绑定终端，设置选择器
      if (this.data.isEdit && this.data.formData.terminal_id) {
        const index = terminals.findIndex(t => t.terminal_id === this.data.formData.terminal_id)
        if (index >= 0) {
          this.setData({ terminalIndex: index })
        }
      }
    } catch (err) {
      console.error('加载终端列表失败:', err)
    }
  },

  // 输入处理
  onInput(e) {
    const { field } = e.currentTarget.dataset
    const { value } = e.detail
    this.setData({
      [`formData.${field}`]: value
    })
  },

  // 设备类型选择
  onTypeChange(e) {
    const index = e.detail.value
    this.setData({
      typeIndex: index,
      'formData.device_type': DEVICE_TYPES[index]
    })
  },

  // 终端选择
  onTerminalChange(e) {
    const index = e.detail.value
    const terminal = this.data.terminals[index]
    
    this.setData({
      terminalIndex: index,
      'formData.terminal_id': terminal ? terminal.terminal_id : ''
    })
  },

  // 验证表单
  validateForm() {
    const { formData } = this.data
    
    if (!formData.device_name) {
      wx.showToast({
        title: '请输入设备名称',
        icon: 'none'
      })
      return false
    }
    
    if (!formData.device_id) {
      wx.showToast({
        title: '请输入设备ID',
        icon: 'none'
      })
      return false
    }
    
    if (!formData.organization) {
      wx.showToast({
        title: '请输入所属机构',
        icon: 'none'
      })
      return false
    }
    
    if (!formData.contact_person) {
      wx.showToast({
        title: '请输入联系人',
        icon: 'none'
      })
      return false
    }
    
    if (!formData.contact_phone) {
      wx.showToast({
        title: '请输入联系方式',
        icon: 'none'
      })
      return false
    }
    
    // 验证手机号格式
    const phoneReg = /^1[3-9]\d{9}$/
    if (!phoneReg.test(formData.contact_phone)) {
      wx.showToast({
        title: '请输入正确的手机号',
        icon: 'none'
      })
      return false
    }
    
    if (!formData.device_type) {
      wx.showToast({
        title: '请选择设备类型',
        icon: 'none'
      })
      return false
    }
    
    return true
  },

  // 保存设备
  async save() {
    if (!this.validateForm()) {
      return
    }
    
    this.setData({ loading: true })
    
    try {
      if (this.data.isEdit) {
        // 更新设备
        await put(API.DEVICE_DETAIL(this.data.deviceId), this.data.formData)
        wx.showToast({
          title: '更新成功',
          icon: 'success'
        })
      } else {
        // 创建设备
        await post(API.DEVICES, this.data.formData)
        wx.showToast({
          title: '创建成功',
          icon: 'success'
        })
      }
      
      // 返回上一页
      setTimeout(() => {
        wx.navigateBack()
      }, 500)
      
    } catch (err) {
      console.error('保存设备失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  // 取消
  cancel() {
    wx.navigateBack()
  }
})