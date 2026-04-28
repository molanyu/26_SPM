const { request } = require('../../utils/request')
const session = require('../../utils/session')
const { formatDateTime } = require('../../utils/format')

Page({
  data: {
    currentItems: [],
    historyItems: [],
    cancelReason: '学生端主动取消',
    loading: false,
  },

  onShow() {
    if (!session.getToken()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    this.loadReservations()
  },

  onCancelReasonInput(event) {
    this.setData({ cancelReason: event.detail.value })
  },

  async loadReservations() {
    this.setData({ loading: true })
    try {
      const [currentResult, historyResult] = await Promise.all([
        request({ url: '/student/reservations/current' }),
        request({ url: '/student/reservations/history?page=1&page_size=20' }),
      ])
      this.setData({
        currentItems: this.decorateReservations(currentResult.items || []),
        historyItems: this.decorateReservations(historyResult.items || []),
      })
    } catch (error) {
      wx.showToast({ title: error.message || '加载预约失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  async cancelReservation(event) {
    const reservationId = Number(event.currentTarget.dataset.reservationId)
    const reason = (this.data.cancelReason || '').trim() || '学生端主动取消'
    try {
      await request({
        url: `/student/reservations/${reservationId}/cancel`,
        method: 'POST',
        data: { reason },
      })
      wx.showToast({ title: '取消成功', icon: 'none' })
      this.loadReservations()
    } catch (error) {
      wx.showToast({ title: error.message || '取消失败', icon: 'none' })
    }
  },

  goToRooms() {
    wx.navigateTo({ url: '/pages/rooms/rooms' })
  },

  goToCheckin() {
    wx.navigateTo({ url: '/pages/checkin/checkin' })
  },

  goToAssistant() {
    wx.navigateTo({ url: '/pages/assistant/assistant' })
  },

  async rebookReservation(event) {
    const seatId = Number(event.currentTarget.dataset.seatId)
    const startTime = String(event.currentTarget.dataset.startTime || '')
    const endTime = String(event.currentTarget.dataset.endTime || '')
    try {
      const result = await request({
        url: '/student/reservations',
        method: 'POST',
        data: {
          seat_id: seatId,
          start_time: startTime,
          end_time: endTime,
        },
      })
      wx.showToast({ title: `再次预约成功 #${result.data.reservation_id}`, icon: 'none' })
      this.loadReservations()
    } catch (error) {
      wx.showToast({ title: error.message || '再次预约失败', icon: 'none' })
    }
  },

  decorateReservations(items) {
    return items.map((item) => ({
      ...item,
      startLabel: formatDateTime(item.start_time),
      endLabel: formatDateTime(item.end_time),
      canCancel: item.status === 'BOOKED',
      canRebook: true,
    }))
  },
})
