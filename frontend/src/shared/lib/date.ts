// Время в приложении показывается по МСК: дедлайны приходят с +03:00, настенное
// время занятий и задач — уже московское.
const TZ = 'Europe/Moscow'

const fmt = (opts: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat('ru-RU', { timeZone: TZ, ...opts })

const dayMonth = fmt({ day: 'numeric', month: 'long' })
const dayMonthShort = fmt({ day: '2-digit', month: '2-digit' })
const weekdayShort = fmt({ weekday: 'short' })
const time = fmt({ hour: '2-digit', minute: '2-digit' })
const full = fmt({ day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })
const monthYear = fmt({ month: 'long', year: 'numeric' })

/** Дата в формате YYYY-MM-DD по московскому календарю. */
export function isoDay(d: Date = new Date()): string {
  return fmt({ year: 'numeric', month: '2-digit', day: '2-digit' }).format(d).split('.').reverse().join('-')
}

/** Полдень по МСК заданного дня: безопасная точка для арифметики дат. */
export function dayToDate(day: string): Date {
  return new Date(`${day}T12:00:00+03:00`)
}

export function addDays(day: string, n: number): string {
  const d = dayToDate(day)
  d.setUTCDate(d.getUTCDate() + n)
  return isoDay(d)
}

/** 1 — понедельник … 7 — воскресенье. */
export function weekday(day: string): number {
  const w = dayToDate(day).getUTCDay()
  return w === 0 ? 7 : w
}

export function startOfWeek(day: string): string {
  return addDays(day, 1 - weekday(day))
}

export function startOfMonth(day: string): string {
  return `${day.slice(0, 8)}01`
}

export function daysBetween(a: string, b: string): number {
  return Math.round((dayToDate(b).getTime() - dayToDate(a).getTime()) / 86_400_000)
}

export const formatDay = (day: string) => dayMonth.format(dayToDate(day))
export const formatDayShort = (day: string) => dayMonthShort.format(dayToDate(day))
export const formatWeekday = (day: string) => weekdayShort.format(dayToDate(day))
export const formatMonthYear = (day: string) => {
  const s = monthYear.format(dayToDate(day)).replace(' г.', '')
  return s[0].toUpperCase() + s.slice(1)
}
export const formatDateTime = (iso: string) => full.format(new Date(iso))
export const formatTime = (iso: string) => time.format(new Date(iso))
/** «10:30» из «10:30:00». */
export const hm = (t: string) => t.slice(0, 5)

export function formatDateTimeShort(iso: string): string {
  const d = new Date(iso)
  return `${dayMonthShort.format(d)} ${time.format(d)}`
}

const plural = (n: number, one: string, few: string, many: string) => {
  const m10 = n % 10
  const m100 = n % 100
  if (m10 === 1 && m100 !== 11) return one
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few
  return many
}

export function pluralize(n: number, forms: [string, string, string]): string {
  return `${n} ${plural(n, ...forms)}`
}

/** «через 2 дня 4 ч», «через 35 мин», «просрочено на 3 дня». */
export function relativeDeadline(iso: string, now = new Date()): string {
  const diff = new Date(iso).getTime() - now.getTime()
  const abs = Math.abs(diff)
  const minutes = Math.floor(abs / 60_000)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  let text: string
  if (days >= 1) {
    const h = hours % 24
    text = pluralize(days, ['день', 'дня', 'дней']) + (days < 3 && h ? ` ${h} ч` : '')
  } else if (hours >= 1) {
    text = `${hours} ч ${minutes % 60} мин`
  } else {
    text = `${Math.max(minutes, 1)} мин`
  }
  return diff >= 0 ? `через ${text}` : `просрочено на ${text}`
}

/** «только что», «5 мин назад», «вчера», «12 октября». */
export function relativePast(iso: string, now = new Date()): string {
  const diff = now.getTime() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60_000)
  if (minutes < 1) return 'только что'
  if (minutes < 60) return `${minutes} мин назад`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} ч назад`
  const today = isoDay(now)
  const day = isoDay(new Date(iso))
  if (daysBetween(day, today) === 1) return `вчера, ${formatTime(iso)}`
  return formatDay(day)
}

/** «Сегодня», «Завтра» или «чт, 16 октября». */
export function dayLabel(day: string, today = isoDay()): string {
  const diff = daysBetween(today, day)
  if (diff === 0) return 'Сегодня'
  if (diff === 1) return 'Завтра'
  if (diff === -1) return 'Вчера'
  const w = formatWeekday(day)
  return `${w[0].toUpperCase()}${w.slice(1)}, ${formatDay(day)}`
}

const clock = fmt({ hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })

/** Минуты от начала суток по МСК: «11:15:00» → 675; без аргумента — текущее время. */
export function minutesOf(t?: string): number {
  const s = t ?? clock.format(new Date())
  const [h, m] = s.split(':').map(Number)
  return h * 60 + m
}

/** «09:30» из минут от начала суток. */
export const fromMinutes = (m: number) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`

const weekdayLong = fmt({ weekday: 'long' })
const monthShort = fmt({ month: 'short' })

/** «Четверг, 15 октября». */
export function formatDayLong(day: string): string {
  const w = weekdayLong.format(dayToDate(day))
  return `${w[0].toUpperCase()}${w.slice(1)}, ${formatDay(day)}`
}

/** «окт.» */
export const formatMonthShort = (day: string) => monthShort.format(dayToDate(day))
