const session = require('./utils/session')

App({
  onLaunch() {},

  ensureStudentSession() {
    return !!session.getToken()
  },
})
