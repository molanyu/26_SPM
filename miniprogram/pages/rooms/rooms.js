const { request } = require('../../utils/request')
const session = require('../../utils/session')
const { formatDateTime } = require('../../utils/format')

Page({
  data: {
    user: null,
    rooms: [],
    loading: false,
    lastRefreshed: '',
  },

  onShow() {
    if (!session.getToken()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    this.loadPage()
  },

  async loadPage() {
    this.setData({ loading: true })
    try {
      const [user, rooms] = await Promise.all([
        request({ url: '/student/me' }),
        request({ url: '/student/rooms?page=1&page_size=50' }),
      ])
      session.setUser(user)
      this.setData({
        user,
        rooms: rooms.items || [],
        lastRefreshed: formatDateTime(new Date()),
      })
    } catch (error) {
      wx.showToast({ title: error.message || '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  goToRoom(event) {
    const { roomId, roomName } = event.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/seats/seats?roomId=${roomId}&roomName=${encodeURIComponent(roomName)}`,
    })
  },

  goToReservations() {
    wx.navigateTo({ url: '/pages/reservations/reservations' })
  },

  goToCheckin() {
    wx.navigateTo({ url: '/pages/checkin/checkin' })
  },

  goToAssistant() {
    wx.navigateTo({ url: '/pages/assistant/assistant' })
  },

  logout() {
    session.clearSession()
    wx.redirectTo({ url: '/pages/login/login' })
  },
})
