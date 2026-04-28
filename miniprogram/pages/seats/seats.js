const { request } = require('../../utils/request')
const session = require('../../utils/session')
const { combineDateTime, nextWholeHourRange } = require('../../utils/format')

Page({
  data: {
    roomId: null,
    roomName: '',
    seats: [],
    loading: false,
    date: '',
    startTime: '',
    endTime: '',
    isWindowSide: false,
    hasPowerSocket: false,
    hasTrackSocket: false,
  },

  onLoad(options) {
    const defaults = nextWholeHourRange()
    this.setData({
      roomId: Number(options.roomId),
      roomName: decodeURIComponent(options.roomName || ''),
      date: defaults.date,
      startTime: defaults.startTime,
      endTime: defaults.endTime,
    })
  },

  onShow() {
    if (!session.getToken()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    this.loadSeats()
  },

  onDateChange(event) {
    this.setData({ date: event.detail.value })
  },

  onStartTimeChange(event) {
    this.setData({ startTime: event.detail.value })
  },

  onEndTimeChange(event) {
    this.setData({ endTime: event.detail.value })
  },

  onWindowToggle(event) {
    this.setData({ isWindowSide: event.detail.value })
  },

  onPowerToggle(event) {
    this.setData({ hasPowerSocket: event.detail.value })
  },

  onTrackToggle(event) {
    this.setData({ hasTrackSocket: event.detail.value })
  },

  async loadSeats() {
    this.setData({ loading: true })
    try {
      const query = [
        `date=${encodeURIComponent(this.data.date)}`,
        `start_time=${encodeURIComponent(this.data.startTime)}`,
        `end_time=${encodeURIComponent(this.data.endTime)}`,
        `is_window_side=${this.data.isWindowSide}`,
        `has_power_socket=${this.data.hasPowerSocket}`,
        `has_track_socket=${this.data.hasTrackSocket}`,
      ].join('&')

      const result = await request({
        url: `/student/rooms/${this.data.roomId}/seats?${query}`,
      })
      this.setData({
        seats: (result.items || []).map((item) => ({
          ...item,
          windowLabel: item.is_window_side ? '是' : '否',
          powerLabel: item.has_power_socket ? '是' : '否',
          trackLabel: item.has_track_socket ? '是' : '否',
        })),
      })
    } catch (error) {
      wx.showToast({ title: error.message || '加载座位失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  async createReservation(event) {
    const seatId = Number(event.currentTarget.dataset.seatId)
    try {
      const result = await request({
        url: '/student/reservations',
        method: 'POST',
        data: {
          seat_id: seatId,
          start_time: combineDateTime(this.data.date, this.data.startTime),
          end_time: combineDateTime(this.data.date, this.data.endTime),
        },
      })
      wx.showToast({ title: `预约成功 #${result.data.reservation_id}`, icon: 'none' })
      wx.navigateTo({ url: '/pages/reservations/reservations' })
    } catch (error) {
      wx.showToast({ title: error.message || '预约失败', icon: 'none' })
    }
  },

  goToRooms() {
    wx.navigateBack()
  },

  goToReservations() {
    wx.navigateTo({ url: '/pages/reservations/reservations' })
  },
})
