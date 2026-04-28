const { request } = require('../../utils/request')
const session = require('../../utils/session')

Page({
  data: {
    message: '',
    loading: false,
    response: null,
    responseText: '',
    responseIntent: '',
  },

  onShow() {
    if (!session.getToken()) {
      wx.redirectTo({ url: '/pages/login/login' })
    }
  },

  onMessageInput(event) {
    this.setData({ message: event.detail.value })
  },

  async submitQuery() {
    if (!this.data.message.trim()) {
      wx.showToast({ title: '请输入查询内容', icon: 'none' })
      return
    }
    this.setData({ loading: true })
    try {
      const response = await request({
        url: '/student/assistant/query',
        method: 'POST',
        data: {
          message: this.data.message.trim(),
        },
      })
      this.setData({
        response,
        responseText: JSON.stringify(response.result, null, 2),
        responseIntent: response.intent || '未识别',
      })
    } catch (error) {
      wx.showToast({ title: error.message || '查询失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  goToRooms() {
    wx.navigateTo({ url: '/pages/rooms/rooms' })
  },

  goToReservations() {
    wx.navigateTo({ url: '/pages/reservations/reservations' })
  },

  goToCheckin() {
    wx.navigateTo({ url: '/pages/checkin/checkin' })
  },
})
