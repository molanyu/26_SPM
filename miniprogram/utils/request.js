const { baseUrl } = require('./config')
const session = require('./session')

function normalizeError(res) {
  const payload = res.data || {}
  return {
    statusCode: res.statusCode,
    code: payload.code || 'request_failed',
    message: payload.message || 'Request failed.',
    details: payload.details || null,
  }
}

function request(options) {
  const {
    url,
    method = 'GET',
    data,
    auth = true,
  } = options

  return new Promise((resolve, reject) => {
    const header = {
      'Content-Type': 'application/json',
    }

    if (auth) {
      const token = session.getToken()
      if (token) {
        header.Authorization = `Bearer ${token}`
      }
    }

    wx.request({
      url: `${baseUrl}${url}`,
      method,
      data,
      header,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
          return
        }
        if (auth && res.statusCode === 401) {
          session.clearSession()
        }
        reject(normalizeError(res))
      },
      fail(err) {
        reject({
          statusCode: 0,
          code: 'network_error',
          message: err.errMsg || 'Network request failed.',
          details: null,
        })
      },
    })
  })
}

module.exports = {
  request,
}
