const { request } = require('../../utils/request')
const session = require('../../utils/session')

function extractScanToken(scanResult) {
  const match = /token=([^&]+)/.exec(scanResult)
  if (match) {
    return decodeURIComponent(match[1])
  }
  return scanResult
}

Page({
  data: {
    reservations: [],
    selectedReservationId: '',
    code: '',
    loading: false,
  },

  onShow() {
    if (!session.getToken()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    this.loadCurrentReservations()
  },

  onReservationChange(event) {
    const index = Number(event.detail.value)
    const selected = this.data.reservations[index]
    this.setData({
      selectedReservationId: selected ? String(selected.reservation_id) : '',
    })
  },

  onCodeInput(event) {
    this.setData({ code: event.detail.value })
  },

  async loadCurrentReservations() {
    this.setData({ loading: true })
    try {
      const result = await request({ url: '/student/reservations/current' })
      const reservations = result.items || []
      this.setData({
        reservations,
        selectedReservationId: reservations.length ? String(reservations[0].reservation_id) : '',
      })
    } catch (error) {
      wx.showToast({ title: error.message || '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  async submitCodeCheckin() {
    if (!this.data.selectedReservationId || !this.data.code.trim()) {
      wx.showToast({ title: '请选择预约并输入动态码', icon: 'none' })
      return
    }
    try {
      const result = await request({
        url: '/student/checkins/code',
        method: 'POST',
        data: {
          reservation_id: Number(this.data.selectedReservationId),
          code: this.data.code.trim(),
        },
      })
      wx.showToast({ title: `签到成功 #${result.data.checkin_record_id}`, icon: 'none' })
      this.loadCurrentReservations()
    } catch (error) {
      wx.showToast({ title: error.message || '签到失败', icon: 'none' })
    }
  },

  scanQrCode() {
    if (!this.data.selectedReservationId) {
      wx.showToast({ title: '请先选择预约', icon: 'none' })
      return
    }
    wx.scanCode({
      success: async (scanResult) => {
        const token = extractScanToken(scanResult.result || '')
        try {
          const result = await request({
            url: '/student/checkins/qrcode',
            method: 'POST',
            data: {
              reservation_id: Number(this.data.selectedReservationId),
              token,
            },
          })
          wx.showToast({ title: `签到成功 #${result.data.checkin_record_id}`, icon: 'none' })
          this.loadCurrentReservations()
        } catch (error) {
          wx.showToast({ title: error.message || '二维码签到失败', icon: 'none' })
        }
      },
      fail: () => {
        wx.showToast({ title: '扫码已取消', icon: 'none' })
      },
    })
  },

  goToRooms() {
    wx.navigateTo({ url: '/pages/rooms/rooms' })
  },

  goToReservations() {
    wx.navigateTo({ url: '/pages/reservations/reservations' })
  },

  goToAssistant() {
    wx.navigateTo({ url: '/pages/assistant/assistant' })
  },
})
