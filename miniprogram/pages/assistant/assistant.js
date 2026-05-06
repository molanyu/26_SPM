const { request } = require('../../utils/request')
const session = require('../../utils/session')

Page({
  data: {
    message: '',
    loading: false,
    resultView: null,
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
        resultView: this.buildResultView(response),
      })
    } catch (error) {
      this.setData({
        resultView: {
          kind: 'error',
          title: '查询失败',
          message: error.message || '暂时无法完成查询，请稍后再试。',
        },
      })
    } finally {
      this.setData({ loading: false })
    }
  },

  buildResultView(response) {
    const result = response.result || {}
    if (response.result_type === 'CONTROLLED_FAILURE') {
      return {
        kind: 'error',
        title: '暂时没理解你的问题',
        message: result.message || '可以试试询问空座、靠窗座位或今天的预约。',
      }
    }
    if (response.result_type === 'AVAILABLE_SEAT_LIST') {
      const items = (result.items || []).map((item) => ({
        id: item.seat_id,
        title: `${item.room_name} · ${item.seat_code}`,
        subtitle: item.seat_label,
        meta: `可预约时间 ${item.available_time_range}`,
      }))
      return this.buildListView('今晚可用座位', '当前条件下没有查到可用座位。', items)
    }
    if (response.result_type === 'SEAT_ATTRIBUTE_LIST') {
      const items = (result.items || []).map((item) => ({
        id: item.seat_id,
        title: `${item.room_name} · ${item.seat_code}`,
        subtitle: item.seat_label,
        meta: this.formatSeatAttributes(item),
      }))
      return this.buildListView('符合条件的座位', '当前没有符合条件的座位。', items)
    }
    if (response.result_type === 'TODAY_MY_RESERVATION') {
      const items = (result.items || []).map((item) => ({
        id: item.reservation_id,
        title: `预约 #${item.reservation_id}`,
        subtitle: item.room_name || `自习室 ${item.room_id}`,
        meta: `${this.formatDateTime(item.start_time)} - ${this.formatDateTime(item.end_time)} · ${item.status}`,
      }))
      return this.buildListView('今天的预约', '今天暂时没有预约。', items)
    }
    return {
      kind: 'error',
      title: '结果暂不可展示',
      message: '系统返回了暂不支持的结果类型。',
    }
  },

  buildListView(title, emptyText, items) {
    if (!items.length) {
      return {
        kind: 'empty',
        title,
        message: emptyText,
      }
    }
    return {
      kind: 'list',
      title,
      items,
    }
  },

  formatSeatAttributes(item) {
    const labels = []
    if (item.is_window_side) labels.push('靠窗')
    if (item.has_power_socket) labels.push('电源插座')
    if (item.has_track_socket) labels.push('移动导轨插座')
    return labels.length ? labels.join(' / ') : '普通座位'
  },

  formatDateTime(value) {
    if (!value) return ''
    return value.replace('T', ' ').slice(0, 16)
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
