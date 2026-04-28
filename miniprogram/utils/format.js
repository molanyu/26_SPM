function pad(value) {
  return String(value).padStart(2, '0')
}

function toDateString(date) {
  const target = new Date(date)
  return `${target.getFullYear()}-${pad(target.getMonth() + 1)}-${pad(target.getDate())}`
}

function toTimeString(date) {
  const target = new Date(date)
  return `${pad(target.getHours())}:${pad(target.getMinutes())}`
}

function combineDateTime(dateText, timeText) {
  return `${dateText}T${timeText}:00`
}

function formatDateTime(value) {
  const target = new Date(value)
  return `${toDateString(target)} ${toTimeString(target)}`
}

function nextWholeHourRange() {
  const now = new Date()
  now.setMinutes(0, 0, 0)
  now.setHours(now.getHours() + 1)
  const end = new Date(now)
  end.setHours(end.getHours() + 2)
  return {
    date: toDateString(now),
    startTime: toTimeString(now),
    endTime: toTimeString(end),
  }
}

module.exports = {
  toDateString,
  toTimeString,
  combineDateTime,
  formatDateTime,
  nextWholeHourRange,
}
