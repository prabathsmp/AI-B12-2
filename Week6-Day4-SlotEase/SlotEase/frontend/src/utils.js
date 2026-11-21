// Date helpers. Backend returns ISO strings with the business's offset
// (e.g. 2026-10-10T17:30:00+05:30). We display the wall-clock part as-is so
// times always match the business's timezone, whatever the viewer's timezone.

export const pad = (n) => String(n).padStart(2, '0')
export const ymd = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
export const parseYmd = (s) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d) }
export const addDays = (s, n) => { const d = parseYmd(s); d.setDate(d.getDate() + n); return ymd(d) }

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
export const WEEKDAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

export const wallDate = (iso) => iso.slice(0, 10)
export const wallTime = (iso) => iso.slice(11, 16)
export const time12 = (hhmm) => {
  const [h, m] = hhmm.split(':').map(Number)
  return `${h % 12 || 12}:${pad(m)} ${h < 12 ? 'AM' : 'PM'}`
}
export const minutesOf = (iso) => { const [h, m] = wallTime(iso).split(':').map(Number); return h * 60 + m }

export const prettyDate = (s, { long = false } = {}) => {
  const d = parseYmd(s)
  return long
    ? `${['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][d.getDay()]}, ${d.getDate()} ${MONTHS[d.getMonth()]}`
    : `${DAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}`
}
export const dayParts = (s) => { const d = parseYmd(s); return { dow: DAYS[d.getDay()], day: d.getDate(), mon: MONTHS[d.getMonth()], jsDay: d.getDay() } }
// Monday = 0 ... Sunday = 6 (matches backend)
export const weekdayIdx = (s) => (parseYmd(s).getDay() + 6) % 7
export const mondayOf = (s) => addDays(s, -weekdayIdx(s))

export const rupees = (n) => `₹${Math.round(Number(n) || 0).toLocaleString('en-IN')}`
export const monthLabel = (ym) => { const [y, m] = ym.split('-').map(Number); return `${MONTHS[m - 1]} ${y}` }
export const shiftMonth = (ym, n) => { const [y, m] = ym.split('-').map(Number); const d = new Date(y, m - 1 + n, 1); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}` }

export const initials = (name = '') => name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join('')
export const cx = (...c) => c.filter(Boolean).join(' ')
