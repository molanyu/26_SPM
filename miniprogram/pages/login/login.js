const { request } = require('../../utils/request')
const session = require('../../utils/session')

Page({
  data: {
    studentNo: '',
    password: '',
    loading: false,
  },

  onShow() {
    if (session.getToken()) {
      wx.redirectTo({ url: '/pages/rooms/rooms' })
    }
  },

  onStudentNoInput(event) {
    this.setData({ studentNo: event.detail.value })
  },

  onPasswordInput(event) {
    this.setData({ password: event.detail.value })
  },

  async submitLogin() {
    if (!this.data.studentNo.trim() || !this.data.password.trim()) {
      wx.showToast({ title: '请输入学号和密码', icon: 'none' })
      return
    }

    this.setData({ loading: true })
    try {
      const result = await request({
        url: '/student/auth/login',
        method: 'POST',
        auth: false,
        data: {
          student_no: this.data.studentNo.trim(),
          password: this.data.password,
        },
      })
      session.setToken(result.access_token)
      session.setUser(result.user)
      wx.redirectTo({ url: '/pages/rooms/rooms' })
    } catch (error) {
      wx.showToast({ title: error.message || '登录失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },
})
