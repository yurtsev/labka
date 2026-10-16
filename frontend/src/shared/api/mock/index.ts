import { LIMITS } from '@/shared/config'
import { addDays, daysBetween, isoDay, startOfMonth, startOfWeek, weekday } from '@/shared/lib/date'
import { fileSize } from '@/shared/lib/format'

import type {
  Assignment,
  Attempt,
  CalendarItem,
  CalendarView,
  CalendarWeek,
  Course,
  CoursePreview,
  FeedEntry,
  HomeLesson,
  Material,
  Notification,
  Profile,
  Progress,
  ProgressStatus,
  QueueItem,
  ReviewAttempt,
  Scale,
  Semester,
  StudentRow,
  Summary,
  User,
} from '../types'

import {
  createDb,
  type MockAssignment,
  type MockAttempt,
  type MockCourse,
  type MockFile,
  type MockUser,
  SLOTS,
  uid,
} from './db'

// Демо-backend: отвечает на те же пути и в том же формате, что настоящий API.
// Режим включён, пока VITE_API_MODE не равен `real`.
// В адресной строке можно добавить `?mock=error`, `?mock=empty` или `?mock=slow`,
// чтобы посмотреть экраны в состоянии ошибки, без данных или долгой загрузки.

const data = createDb()
const SESSION_KEY = 'labka.demo.session'

class HttpError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

const notFound = (what = 'Не найдено') => new HttpError(404, 'not_found', what)
const forbidden = () => new HttpError(403, 'forbidden', 'Нет доступа')

// ── Сессия ────────────────────────────────────────────────────────────────

function sessionUser(): MockUser | null {
  let id: string | null = null
  try {
    id = localStorage.getItem(SESSION_KEY)
  } catch {
    id = null
  }
  return data.users.find((u) => u.id === id && u.is_active) ?? null
}

function setSession(user: MockUser | null) {
  try {
    if (user) localStorage.setItem(SESSION_KEY, user.id)
    else localStorage.removeItem(SESSION_KEY)
  } catch {
    // Без localStorage вход живёт до перезагрузки — для демо достаточно.
  }
}

function requireUser(): MockUser {
  const u = sessionUser()
  if (!u) throw new HttpError(401, 'auth.not_authenticated', 'Войдите в аккаунт')
  return u
}

// ── Представления ─────────────────────────────────────────────────────────

const toUser = (u: MockUser): User => ({
  id: u.id,
  last_name: u.last_name,
  first_name: u.first_name,
  middle_name: u.middle_name,
  email: u.email,
  role: u.role,
})

const person = (u: MockUser) => ({ id: u.id, last_name: u.last_name, first_name: u.first_name, middle_name: u.middle_name })

const userById = (id: string) => data.users.find((u) => u.id === id)!
const groupById = (id: string) => data.groups.find((g) => g.id === id)!
const groupRef = (id: string) => ({ id, name: groupById(id).name })
const courseRef = (c: MockCourse) => ({ id: c.id, name: c.name })

const DEMO_URL = 'data:text/plain;charset=utf-8,' + encodeURIComponent('Демонстрационный файл Labka')
const fileOut = (f: MockFile) => ({ ...f, download_url: DEMO_URL })

const toProfile = (u: MockUser): Profile => ({
  ...toUser(u),
  group: u.group_id ? { id: u.group_id, name: groupById(u.group_id).name } : null,
  department: u.department ? { id: 'dep', name: u.department } : null,
  avatar_url: u.avatar_url,
})

const toCourse = (c: MockCourse): Course => ({
  id: c.id,
  name: c.name,
  description: c.description,
  teacher: person(userById(c.teacher_id)),
  semester: c.semester,
  scale: c.scale,
  grading_note: c.grading_note,
  is_archived: c.is_archived,
  groups: c.group_ids.map(groupRef),
})

// ── Доступ ────────────────────────────────────────────────────────────────

function visibleCourses(u: MockUser): MockCourse[] {
  if (u.role === 'teacher') return data.courses.filter((c) => c.teacher_id === u.id)
  if (u.role === 'student') return data.courses.filter((c) => u.group_id && c.group_ids.includes(u.group_id))
  return []
}

function courseFor(u: MockUser, id: string): MockCourse {
  const c = data.courses.find((x) => x.id === id)
  if (!c) throw notFound('Курс не найден')
  if (!visibleCourses(u).includes(c)) throw forbidden()
  return c
}

function ownCourse(u: MockUser, id: string, { writable = true } = {}): MockCourse {
  const c = courseFor(u, id)
  if (u.role !== 'teacher') throw forbidden()
  if (writable && c.is_archived) throw new HttpError(409, 'course.archived', 'Курс в архиве — изменения недоступны')
  return c
}

function assignmentFor(u: MockUser, courseId: string, id: string): [MockCourse, MockAssignment] {
  const c = courseFor(u, courseId)
  const a = data.assignments.find((x) => x.id === id && x.course_id === c.id)
  if (!a) throw notFound('Задание не найдено')
  return [c, a]
}

// ── Статусы и сводки ──────────────────────────────────────────────────────

const attemptsOf = (assignmentId: string, studentId: string) =>
  data.attempts.filter((a) => a.assignment_id === assignmentId && a.student_id === studentId).sort((a, b) => a.number - b.number)

type SubmitWindow = 'open' | 'late' | 'closed' | 'accepted'

/** Окно сдачи — как `GradingService.submit_window` на бэке. */
function submitWindow(a: MockAssignment, status: ProgressStatus, firstSubmittedAt: string | null, now = new Date()): SubmitWindow {
  if (status === 'accepted') return 'accepted'
  if (a.deadline_at === null || now <= new Date(a.deadline_at)) return 'open'
  if (a.deadline_type !== 'hard') return 'late'
  const inTime = firstSubmittedAt !== null && new Date(firstSubmittedAt) <= new Date(a.deadline_at)
  return status === 'revision' && inTime ? 'open' : 'closed'
}

function progress(a: MockAssignment, studentId: string): Progress {
  const list = attemptsOf(a.id, studentId)
  const last = list.at(-1)
  let status: ProgressStatus = 'not_submitted'
  if (last) status = last.review ? (last.review.verdict === 'accepted' ? 'accepted' : 'revision') : 'on_review'
  const window = submitWindow(a, status, list[0]?.created_at ?? null)
  const graded = [...list].reverse().find((x) => x.review && (x.review.score !== null || x.review.passed !== null))
  return {
    status,
    grade: graded ? { score: graded.review!.score, passed: graded.review!.passed } : null,
    attempts: list.length,
    last_submitted_at: last?.created_at ?? null,
    last_is_late: last?.is_late ?? false,
    can_submit: window === 'open' || window === 'late',
  }
}

const courseStudents = (c: MockCourse) =>
  data.users.filter((u) => u.role === 'student' && u.is_active && u.group_id && c.group_ids.includes(u.group_id))

function summary(a: MockAssignment): Summary {
  const c = data.courses.find((x) => x.id === a.course_id)!
  const ps = courseStudents(c).map((s) => progress(a, s.id))
  return {
    students: ps.length,
    submitted: ps.filter((p) => p.attempts > 0).length,
    on_review: ps.filter((p) => p.status === 'on_review').length,
    accepted: ps.filter((p) => p.status === 'accepted').length,
  }
}

const scaleOf = (a: MockAssignment): Scale => a.own_scale ?? data.courses.find((c) => c.id === a.course_id)!.scale

function toAssignment(u: MockUser, a: MockAssignment): Assignment {
  const isStudent = u.role === 'student'
  return {
    id: a.id,
    course_id: a.course_id,
    type: a.type,
    title: a.title,
    description: a.description,
    deadline_type: a.deadline_type,
    deadline_at: a.deadline_at,
    scale: scaleOf(a),
    has_own_scale: a.own_scale !== null,
    grading_note: a.grading_note,
    created_at: a.created_at,
    updated_at: a.updated_at,
    files: a.files.map(fileOut),
    my_progress: isStudent ? progress(a, u.id) : null,
    summary: isStudent ? null : summary(a),
    attempts_total: isStudent ? null : data.attempts.filter((x) => x.assignment_id === a.id).length,
  }
}

const reviewOut = (x: MockAttempt) =>
  x.review
    ? {
        verdict: x.review.verdict,
        grade: x.review.score !== null || x.review.passed !== null ? { score: x.review.score, passed: x.review.passed } : null,
        comment: x.review.comment,
        created_at: x.review.created_at,
        updated_at: x.review.updated_at,
      }
    : null

const toAttempt = (x: MockAttempt): Attempt & ReviewAttempt => ({
  id: x.id,
  number: x.number,
  comment: x.comment,
  is_late: x.is_late,
  created_at: x.created_at,
  files: x.files.map(fileOut),
  review: reviewOut(x),
})

// ── Расписание ────────────────────────────────────────────────────────────

const slot = (n: number) => SLOTS.find((s) => s.number === n)!

function weekInfo(weekStart: string, semesters: Semester[]): CalendarWeek {
  const ends_on = addDays(weekStart, 6)
  const sem = semesters.find((s) => s.starts_on <= ends_on && s.ends_on >= weekStart)
  if (!sem) return { starts_on: weekStart, ends_on, term: null, number: null, is_even: null }
  const number = Math.floor(daysBetween(startOfWeek(sem.starts_on), weekStart) / 7) + 1
  return { starts_on: weekStart, ends_on, term: sem.term, number, is_even: number % 2 === 0 }
}

/** Занятия курса на отрезке дней: из правил семестра и разовых занятий. */
function lessons(c: MockCourse, from: string, to: string, groupId?: string) {
  const out: { day: string; slot: number; lesson_type: 'lab' | 'practice'; room: string | null; group_id: string; is_extra: boolean }[] = []
  if (c.is_archived) return out
  const { starts_on, classes_end_on } = c.semester
  for (let d = from; d <= to; d = addDays(d, 1)) {
    if (d < starts_on || d > classes_end_on) continue
    const w = weekInfo(startOfWeek(d), [c.semester])
    for (const r of data.rules) {
      if (r.course_id !== c.id || (groupId && r.group_id !== groupId) || r.weekday !== weekday(d)) continue
      if (r.repeat === 'even' && !w.is_even) continue
      if (r.repeat === 'odd' && w.is_even) continue
      out.push({ day: d, slot: r.slot, lesson_type: r.lesson_type, room: r.room, group_id: r.group_id, is_extra: false })
    }
  }
  for (const e of data.extras) {
    if (e.course_id === c.id && (!groupId || e.group_id === groupId) && e.day >= from && e.day <= to) {
      out.push({ day: e.day, slot: e.slot, lesson_type: e.lesson_type, room: e.room, group_id: e.group_id, is_extra: true })
    }
  }
  return out
}

function calendarPeriod(view: CalendarView, date: string) {
  if (view === 'day') return { starts_on: date, ends_on: date, prev: addDays(date, -1), next: addDays(date, 1) }
  if (view === 'week') {
    const s = startOfWeek(date)
    return { starts_on: s, ends_on: addDays(s, 6), prev: addDays(s, -7), next: addDays(s, 7) }
  }
  const first = startOfMonth(date)
  const nextMonth = startOfMonth(addDays(first, 32))
  const prevMonth = startOfMonth(addDays(first, -1))
  const starts_on = startOfWeek(first)
  const ends_on = addDays(startOfWeek(addDays(nextMonth, -1)), 6)
  return { starts_on, ends_on, prev: prevMonth, next: nextMonth }
}

function calendarItems(u: MockUser, from: string, to: string): CalendarItem[] {
  const items: CalendarItem[] = []
  const courses = visibleCourses(u).filter((c) => !c.is_archived)
  const groupId = u.role === 'student' ? u.group_id! : undefined
  for (const c of courses) {
    for (const l of lessons(c, from, to, groupId)) {
      const s = slot(l.slot)
      items.push({
        kind: 'lesson',
        day: l.day,
        starts_at: s.starts_at,
        ends_at: s.ends_at,
        lesson: { course: courseRef(c), group: groupRef(l.group_id), lesson_type: l.lesson_type, slot: l.slot, room: l.room, is_extra: l.is_extra },
        exam: null,
        deadline: null,
        task: null,
      })
    }
    for (const x of data.exams) {
      if (x.course_id !== c.id || (groupId && x.group_id !== groupId) || x.day < from || x.day > to) continue
      const s = slot(x.slot)
      items.push({
        kind: 'exam',
        day: x.day,
        starts_at: s.starts_at,
        ends_at: s.ends_at,
        lesson: null,
        exam: { course: courseRef(c), group: groupRef(x.group_id), exam_type: x.exam_type, slot: x.slot, room: x.room },
        deadline: null,
        task: null,
      })
    }
    for (const a of data.assignments) {
      if (a.course_id !== c.id || !a.deadline_at) continue
      const day = isoDay(new Date(a.deadline_at))
      if (day < from || day > to) continue
      items.push({
        kind: 'deadline',
        day,
        starts_at: a.deadline_at.slice(11, 19),
        ends_at: null,
        lesson: null,
        exam: null,
        deadline: {
          assignment_id: a.id,
          title: a.title,
          type: a.type,
          deadline_type: a.deadline_type,
          course: courseRef(c),
          my_status: u.role === 'student' ? progress(a, u.id).status : null,
        },
        task: null,
      })
    }
  }
  if (u.role === 'student') {
    for (const t of data.tasks) {
      if (t.student_id !== u.id || t.due_date < from || t.due_date > to) continue
      items.push({
        kind: 'task',
        day: t.due_date,
        starts_at: t.due_time,
        ends_at: null,
        lesson: null,
        exam: null,
        deadline: null,
        task: { id: t.id, title: t.title, is_done: t.is_done },
      })
    }
  }
  const order = { exam: 0, lesson: 1, deadline: 2, task: 3 }
  return items.sort(
    (a, b) => a.day.localeCompare(b.day) || (a.starts_at ?? '99').localeCompare(b.starts_at ?? '99') || order[a.kind] - order[b.kind],
  )
}

function upcomingLessons(u: MockUser, limit: number): HomeLesson[] {
  const today = isoDay()
  const nowTime = new Date().toLocaleTimeString('ru-RU', { timeZone: 'Europe/Moscow', hour12: false })
  return calendarItems(u, today, addDays(today, 28))
    .filter((i) => i.kind === 'lesson' && (i.day > today || (i.ends_at ?? '') > nowTime))
    .slice(0, limit)
    .map((i) => ({
      day: i.day,
      starts_at: i.starts_at!,
      ends_at: i.ends_at!,
      slot: i.lesson!.slot,
      lesson_type: i.lesson!.lesson_type,
      room: i.lesson!.room,
      is_extra: i.lesson!.is_extra,
      course: i.lesson!.course,
      group: i.lesson!.group,
    }))
}

// ── Прочее ────────────────────────────────────────────────────────────────

function paginate<T>(items: T[], q: URLSearchParams) {
  const per_page = Math.min(Number(q.get('per_page') ?? 20), 100)
  const page = Math.max(Number(q.get('page') ?? 1), 1)
  return {
    items: items.slice((page - 1) * per_page, page * per_page),
    page,
    per_page,
    total: items.length,
    pages: Math.max(1, Math.ceil(items.length / per_page)),
  }
}

const pendingFor = (courseIds: string[]) =>
  data.attempts.filter((x) => {
    if (x.review) return false
    const a = data.assignments.find((y) => y.id === x.assignment_id)!
    if (!courseIds.includes(a.course_id)) return false
    return attemptsOf(a.id, x.student_id).at(-1)?.id === x.id
  })

function toNotification(n: (typeof data.notifications)[number]): Notification {
  const c = n.course_id ? data.courses.find((x) => x.id === n.course_id)! : null
  return { id: n.id, type: n.type, title: n.title, text: n.text, course: c ? courseRef(c) : null, target: n.target, is_read: n.is_read, created_at: n.created_at }
}

function notify(userIds: string[], partial: Omit<(typeof data.notifications)[number], 'id' | 'user_id' | 'is_read' | 'created_at'>) {
  const created_at = new Date().toISOString()
  for (const user_id of userIds) {
    data.notifications.unshift({ id: uid('n'), user_id, is_read: false, created_at, ...partial })
  }
}

const target = (section: (typeof data.notifications)[number]['target']['section'], t: Partial<(typeof data.notifications)[number]['target']> = {}) => ({
  section,
  course_id: null,
  assignment_id: null,
  submission_id: null,
  student_id: null,
  day: null,
  ...t,
})

/** Локальные ссылки на выбранные файлы: в демо аватарка показывается без сервера. */
export const mockPreviews = new Map<string, string>()

/** Учётные записи демо-данных: живут в модуле моков, в сборку с настоящим API не попадают. */
export const DEMO_ACCOUNTS = {
  student: { email: 'student@labka.ru', password: 'labka2026' },
  teacher: { email: 'teacher@labka.ru', password: 'labka2026' },
}

const pendingUploads = new Map<string, { size: number; type: string }>()

function startUpload(body: { content_type: string; file_size: number }) {
  if (body.file_size > LIMITS.maxFileSizeBytes) throw new HttpError(422, 'upload.too_large', `Файл больше ${fileSize(LIMITS.maxFileSizeBytes)}`)
  const key = uid('upload')
  pendingUploads.set(key, { size: body.file_size, type: body.content_type })
  return { key, url: 'mock://upload', fields: {} }
}

function takeFiles(files: { key: string; file_name: string }[] = []): MockFile[] {
  return files.map((f) => {
    const meta = pendingUploads.get(f.key) ?? { size: 1024, type: 'application/octet-stream' }
    pendingUploads.delete(f.key)
    return { id: uid('f'), file_name: f.file_name, file_size: meta.size, content_type: meta.type }
  })
}

const isDemoEmpty = () => new URLSearchParams(location.search).get('mock') === 'empty'

// ── Маршруты ──────────────────────────────────────────────────────────────

type Ctx = { params: Record<string, string>; query: URLSearchParams; body: any }
type Handler = (ctx: Ctx) => unknown
const routes: { method: string; pattern: RegExp; keys: string[]; handler: Handler }[] = []

function on(method: string, path: string, handler: Handler) {
  const keys: string[] = []
  const pattern = new RegExp(
    '^' + path.replace(/\{(\w+)\}/g, (_, k: string) => (keys.push(k), '([^/]+)')) + '$',
  )
  routes.push({ method, pattern, keys, handler })
}

// auth
on('POST', '/api/auth/login', ({ body }) => {
  const u = data.users.find((x) => x.email === String(body.email).trim().toLowerCase())
  if (!u || u.password !== body.password || u.role === 'admin') throw new HttpError(401, 'auth.invalid_credentials', 'Неверный email или пароль')
  if (!u.is_active) throw new HttpError(403, 'auth.account_deactivated', 'Аккаунт деактивирован')
  setSession(u)
  return toUser(u)
})
on('POST', '/api/auth/register', ({ body }) => {
  const email = String(body.email).trim().toLowerCase()
  const g = data.groups.find((x) => x.code.toLowerCase() === String(body.group_code).trim().toLowerCase())
  if (!g) throw new HttpError(422, 'auth.invalid_group_code', 'Неверный код группы')
  if (data.users.some((u) => u.email === email)) throw new HttpError(409, 'auth.email_already_registered', 'Аккаунт с этой почтой уже зарегистрирован')
  if (!g.emails.includes(email)) throw new HttpError(422, 'auth.email_not_invited', 'Этой почты нет в списке группы')
  const u: MockUser = {
    id: uid('u'),
    last_name: body.last_name,
    first_name: body.first_name,
    middle_name: body.middle_name ?? null,
    email,
    password: body.password,
    role: 'student',
    group_id: g.id,
    department: null,
    avatar_url: null,
    is_active: true,
  }
  data.users.push(u)
  setSession(u)
  return toUser(u)
})
on('POST', '/api/auth/logout', () => (setSession(null), {}))
on('POST', '/api/auth/refresh', () => (requireUser(), {}))
on('GET', '/api/auth/me', () => toUser(requireUser()))
on('POST', '/api/auth/password', ({ body }) => {
  const u = requireUser()
  if (u.password !== body.current_password) throw new HttpError(422, 'auth.wrong_current_password', 'Неверный текущий пароль')
  u.password = body.new_password
  return {}
})

// profile
on('GET', '/api/profile', () => toProfile(requireUser()))
on('POST', '/api/profile/avatar/uploads', ({ body }) => {
  requireUser()
  if (!/^image\/(png|jpeg|webp|gif)$/.test(body.content_type)) throw new HttpError(422, 'profile.avatar_type', 'Аватарка — только PNG, JPEG, WebP или GIF')
  return startUpload(body)
})
on('PUT', '/api/profile/avatar', ({ body }) => {
  const u = requireUser()
  u.avatar_url = mockPreviews.get(body.key) ?? null
  pendingUploads.delete(body.key)
  return toProfile(u)
})
on('DELETE', '/api/profile/avatar', () => {
  const u = requireUser()
  u.avatar_url = null
  return toProfile(u)
})

// home
on('GET', '/api/home', () => {
  const u = requireUser()
  const courses = isDemoEmpty() ? [] : visibleCourses(u).filter((c) => !c.is_archived)
  if (u.role === 'teacher') {
    const pending = pendingFor(courses.map((c) => c.id))
    return {
      nearest_deadline: null,
      upcoming_deadlines: [],
      pending_reviews: pending.length,
      upcoming_lessons: isDemoEmpty() ? [] : upcomingLessons(u, 3),
      courses: courses.map((c) => ({
        id: c.id,
        name: c.name,
        teacher: person(userById(c.teacher_id)),
        groups: c.group_ids.map(groupRef),
        not_submitted: null,
        pending_reviews: pendingFor([c.id]).length,
      })),
      courses_total: courses.length,
    }
  }
  const now = new Date().toISOString()
  const deadlines = data.assignments
    .filter((a) => courses.some((c) => c.id === a.course_id) && a.deadline_at && new Date(a.deadline_at).toISOString() > now)
    .map((a) => ({ a, p: progress(a, u.id) }))
    .filter(({ p }) => p.status === 'not_submitted' || p.status === 'revision')
    .sort((x, y) => new Date(x.a.deadline_at!).getTime() - new Date(y.a.deadline_at!).getTime())
    .map(({ a, p }) => {
      const c = courses.find((x) => x.id === a.course_id)!
      return {
        assignment_id: a.id,
        title: a.title,
        type: a.type,
        deadline_type: a.deadline_type,
        deadline_at: a.deadline_at!,
        course: courseRef(c),
        teacher: person(userById(c.teacher_id)),
        status: p.status,
      }
    })
  return {
    nearest_deadline: deadlines[0] ?? null,
    upcoming_deadlines: deadlines.slice(1, 4),
    pending_reviews: null,
    upcoming_lessons: isDemoEmpty() ? [] : upcomingLessons(u, 3),
    courses: courses.map((c) => ({
      id: c.id,
      name: c.name,
      teacher: person(userById(c.teacher_id)),
      groups: [],
      not_submitted: data.assignments.filter((a) => a.course_id === c.id && progress(a, u.id).status === 'not_submitted').length,
      pending_reviews: null,
    })),
    courses_total: courses.length,
  }
})

// courses
on('GET', '/api/courses', ({ query }) => {
  const u = requireUser()
  const archived = query.get('archived') === 'true'
  const list: CoursePreview[] = visibleCourses(u)
    .filter((c) => c.is_archived === archived)
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .map((c) => ({
      id: c.id,
      name: c.name,
      teacher: person(userById(c.teacher_id)),
      semester: c.semester,
      is_archived: c.is_archived,
      groups: c.group_ids.map(groupRef),
      pending_reviews: u.role === 'teacher' ? pendingFor([c.id]).length : null,
    }))
  return paginate(isDemoEmpty() ? [] : list, query)
})
on('GET', '/api/courses/available-groups', ({ query }) => {
  const u = requireUser()
  if (u.role !== 'teacher') throw forbidden()
  const q = (query.get('query') ?? '').toLowerCase()
  return paginate(data.groups.filter((g) => g.name.toLowerCase().includes(q)).map((g) => ({ id: g.id, name: g.name })), query)
})
on('POST', '/api/courses', ({ body }) => {
  const u = requireUser()
  if (u.role !== 'teacher') throw forbidden()
  if (!body.group_ids?.length) throw new HttpError(422, 'course.no_groups', 'Выберите хотя бы одну группу')
  const sem = data.courses[0].semester
  const c: MockCourse = {
    id: uid('c'),
    name: body.name,
    description: body.description ?? null,
    teacher_id: u.id,
    semester: sem,
    scale: body.scale.type === 'binary' ? { type: 'binary', min: null, max: null } : { type: 'range', min: body.scale.min, max: body.scale.max },
    grading_note: body.grading_note ?? null,
    is_archived: false,
    group_ids: body.group_ids,
    created_at: new Date().toISOString(),
  }
  data.courses.push(c)
  return toCourse(c)
})
on('GET', '/api/courses/{course_id}', ({ params }) => toCourse(courseFor(requireUser(), params.course_id)))
on('PUT', '/api/courses/{course_id}', ({ params, body }) => {
  const c = ownCourse(requireUser(), params.course_id)
  Object.assign(c, {
    name: body.name,
    description: body.description ?? null,
    grading_note: body.grading_note ?? null,
    scale: body.scale.type === 'binary' ? { type: 'binary', min: null, max: null } : { type: 'range', min: body.scale.min, max: body.scale.max },
  })
  return toCourse(c)
})
on('POST', '/api/courses/{course_id}/groups', ({ params, body }) => {
  const c = ownCourse(requireUser(), params.course_id)
  if (c.group_ids.includes(body.group_id)) throw new HttpError(409, 'course.group_exists', 'Группа уже в курсе')
  c.group_ids.push(body.group_id)
  return toCourse(c)
})
on('DELETE', '/api/courses/{course_id}/groups/{group_id}', ({ params }) => {
  const c = ownCourse(requireUser(), params.course_id)
  c.group_ids = c.group_ids.filter((g) => g !== params.group_id)
  return toCourse(c)
})
on('POST', '/api/courses/{course_id}/archive', ({ params }) => {
  const c = ownCourse(requireUser(), params.course_id)
  c.is_archived = true
  return toCourse(c)
})
on('POST', '/api/courses/{course_id}/unarchive', ({ params }) => {
  const c = ownCourse(requireUser(), params.course_id, { writable: false })
  c.is_archived = false
  return toCourse(c)
})

// materials
const toMaterial = (m: (typeof data.materials)[number]): Material => ({ ...m, files: m.files.map(fileOut) })
on('GET', '/api/courses/{course_id}/materials', ({ params, query }) => {
  const c = courseFor(requireUser(), params.course_id)
  return paginate(data.materials.filter((m) => m.course_id === c.id).sort((a, b) => a.created_at.localeCompare(b.created_at)).map(toMaterial), query)
})
on('POST', '/api/courses/{course_id}/materials/uploads', ({ params, body }) => (ownCourse(requireUser(), params.course_id), startUpload(body)))
on('POST', '/api/courses/{course_id}/materials', ({ params, body }) => {
  const c = ownCourse(requireUser(), params.course_id)
  const now = new Date().toISOString()
  const m = { id: uid('m'), course_id: c.id, title: body.title, text: body.text ?? null, created_at: now, updated_at: now, files: takeFiles(body.files) }
  data.materials.push(m)
  notify(courseStudents(c).map((s) => s.id), { type: 'material_added', title: 'Новый материал', text: `«${m.title}» в курсе «${c.name}»`, course_id: c.id, target: target('materials', { course_id: c.id }) })
  return toMaterial(m)
})
on('PUT', '/api/courses/{course_id}/materials/{material_id}', ({ params, body }) => {
  const c = ownCourse(requireUser(), params.course_id)
  const m = data.materials.find((x) => x.id === params.material_id && x.course_id === c.id)
  if (!m) throw notFound('Материал не найден')
  Object.assign(m, { title: body.title, text: body.text ?? null, updated_at: new Date().toISOString() })
  return toMaterial(m)
})
on('DELETE', '/api/courses/{course_id}/materials/{material_id}', ({ params }) => {
  const c = ownCourse(requireUser(), params.course_id)
  data.materials = data.materials.filter((x) => !(x.id === params.material_id && x.course_id === c.id))
  return {}
})

// feed and announcements
on('GET', '/api/courses/{course_id}/feed', ({ params, query }) => {
  const u = requireUser()
  const c = courseFor(u, params.course_id)
  const type = query.get('type')
  const entries: (FeedEntry & { at: string })[] = []
  for (const a of data.assignments) {
    if (a.course_id !== c.id || (type && a.type !== type)) continue
    const full = toAssignment(u, a)
    entries.push({
      at: a.created_at,
      kind: 'assignment',
      announcement: null,
      assignment: {
        id: a.id,
        type: a.type,
        title: a.title,
        deadline_type: a.deadline_type,
        deadline_at: a.deadline_at,
        created_at: a.created_at,
        my_progress: full.my_progress,
        summary: full.summary,
      },
    })
  }
  if (!type) {
    for (const n of data.announcements) {
      if (n.course_id === c.id) entries.push({ at: n.created_at, kind: 'announcement', assignment: null, announcement: { id: n.id, text: n.text, created_at: n.created_at, updated_at: n.updated_at } })
    }
  }
  entries.sort((a, b) => b.at.localeCompare(a.at))
  return paginate(entries.map(({ at: _at, ...e }) => e), query)
})
on('POST', '/api/courses/{course_id}/announcements', ({ params, body }) => {
  const c = ownCourse(requireUser(), params.course_id)
  const now = new Date().toISOString()
  const a = { id: uid('a'), course_id: c.id, text: body.text, created_at: now, updated_at: now }
  data.announcements.push(a)
  notify(courseStudents(c).map((s) => s.id), { type: 'announcement_created', title: 'Новое объявление', text: a.text, course_id: c.id, target: target('course_feed', { course_id: c.id }) })
  return { id: a.id, text: a.text, created_at: a.created_at, updated_at: a.updated_at }
})
on('PUT', '/api/courses/{course_id}/announcements/{announcement_id}', ({ params, body }) => {
  const c = ownCourse(requireUser(), params.course_id)
  const a = data.announcements.find((x) => x.id === params.announcement_id && x.course_id === c.id)
  if (!a) throw notFound('Объявление не найдено')
  Object.assign(a, { text: body.text, updated_at: new Date().toISOString() })
  return { id: a.id, text: a.text, created_at: a.created_at, updated_at: a.updated_at }
})
on('DELETE', '/api/courses/{course_id}/announcements/{announcement_id}', ({ params }) => {
  const c = ownCourse(requireUser(), params.course_id)
  data.announcements = data.announcements.filter((x) => !(x.id === params.announcement_id && x.course_id === c.id))
  return {}
})

// assignments
on('POST', '/api/courses/{course_id}/assignments/uploads', ({ params, body }) => (ownCourse(requireUser(), params.course_id), startUpload(body)))
on('POST', '/api/courses/{course_id}/assignments', ({ params, body }) => {
  const c = ownCourse(requireUser(), params.course_id)
  const now = new Date().toISOString()
  const a: MockAssignment = {
    id: uid('as'),
    course_id: c.id,
    type: body.type,
    title: body.title,
    description: body.description ?? null,
    deadline_type: body.deadline_type,
    deadline_at: body.deadline_type === 'none' ? null : body.deadline_at,
    own_scale: body.scale ? { type: body.scale.type, min: body.scale.min ?? null, max: body.scale.max ?? null } : null,
    grading_note: body.grading_note ?? null,
    created_at: now,
    updated_at: now,
    files: takeFiles(body.files),
  }
  data.assignments.push(a)
  notify(courseStudents(c).map((s) => s.id), { type: 'assignment_created', title: 'Новое задание', text: `«${a.title}»`, course_id: c.id, target: target('assignment', { course_id: c.id, assignment_id: a.id }) })
  return toAssignment(requireUser(), a)
})
on('GET', '/api/courses/{course_id}/assignments/{assignment_id}', ({ params }) => {
  const u = requireUser()
  const [, a] = assignmentFor(u, params.course_id, params.assignment_id)
  return toAssignment(u, a)
})
on('PUT', '/api/courses/{course_id}/assignments/{assignment_id}', ({ params, body }) => {
  const u = requireUser()
  ownCourse(u, params.course_id)
  const [c, a] = assignmentFor(u, params.course_id, params.assignment_id)
  const hasAttempts = data.attempts.some((x) => x.assignment_id === a.id)
  const nextScale = body.scale ? { type: body.scale.type, min: body.scale.min ?? null, max: body.scale.max ?? null } : null
  if (hasAttempts && JSON.stringify(nextScale) !== JSON.stringify(a.own_scale)) {
    throw new HttpError(409, 'assignment.scale_locked', 'Шкалу нельзя изменить: по заданию уже есть попытки')
  }
  Object.assign(a, {
    type: body.type,
    title: body.title,
    description: body.description ?? null,
    deadline_type: body.deadline_type,
    deadline_at: body.deadline_type === 'none' ? null : body.deadline_at,
    own_scale: nextScale,
    grading_note: body.grading_note ?? null,
    updated_at: new Date().toISOString(),
  })
  notify(courseStudents(c).map((s) => s.id), { type: 'assignment_updated', title: 'Задание изменено', text: `«${a.title}»`, course_id: c.id, target: target('assignment', { course_id: c.id, assignment_id: a.id }) })
  return toAssignment(u, a)
})
on('DELETE', '/api/courses/{course_id}/assignments/{assignment_id}', ({ params }) => {
  const u = requireUser()
  ownCourse(u, params.course_id)
  const [, a] = assignmentFor(u, params.course_id, params.assignment_id)
  data.assignments = data.assignments.filter((x) => x.id !== a.id)
  data.attempts = data.attempts.filter((x) => x.assignment_id !== a.id)
  return {}
})
on('POST', '/api/courses/{course_id}/assignments/{assignment_id}/files', ({ params, body }) => {
  const u = requireUser()
  ownCourse(u, params.course_id)
  const [, a] = assignmentFor(u, params.course_id, params.assignment_id)
  a.files.push(...takeFiles([body]))
  a.updated_at = new Date().toISOString()
  return toAssignment(u, a)
})
on('DELETE', '/api/courses/{course_id}/assignments/{assignment_id}/files/{file_id}', ({ params }) => {
  const u = requireUser()
  ownCourse(u, params.course_id)
  const [, a] = assignmentFor(u, params.course_id, params.assignment_id)
  a.files = a.files.filter((f) => f.id !== params.file_id)
  a.updated_at = new Date().toISOString()
  return {}
})
on('GET', '/api/courses/{course_id}/assignments/{assignment_id}/students', ({ params, query }) => {
  const u = requireUser()
  ownCourse(u, params.course_id, { writable: false })
  const [c, a] = assignmentFor(u, params.course_id, params.assignment_id)
  const group = query.get('group_id')
  const status = query.get('status')
  const rows: StudentRow[] = courseStudents(c)
    .filter((s) => !group || s.group_id === group)
    .map((s) => ({
      student_id: s.id,
      last_name: s.last_name,
      first_name: s.first_name,
      middle_name: s.middle_name,
      group_id: s.group_id!,
      group_name: groupById(s.group_id!).name,
      progress: progress(a, s.id),
    }))
    .filter((r) => !status || r.progress.status === status)
    .sort((x, y) => x.group_name.localeCompare(y.group_name) || x.last_name.localeCompare(y.last_name))
  return paginate(rows, query)
})

// submissions
on('POST', '/api/courses/{course_id}/assignments/{assignment_id}/submissions/uploads', ({ params, body }) => {
  const u = requireUser()
  assignmentFor(u, params.course_id, params.assignment_id)
  return startUpload(body)
})
on('POST', '/api/courses/{course_id}/assignments/{assignment_id}/submissions', ({ params, body }) => {
  const u = requireUser()
  if (u.role !== 'student') throw forbidden()
  const [c, a] = assignmentFor(u, params.course_id, params.assignment_id)
  if (c.is_archived) throw new HttpError(409, 'course.archived', 'Курс в архиве — сдача недоступна')
  const p = progress(a, u.id)
  const now = new Date()
  const window = submitWindow(a, p.status, attemptsOf(a.id, u.id)[0]?.created_at ?? null, now)
  if (window === 'accepted') throw new HttpError(409, 'submission.accepted', 'Работа уже принята')
  if (window === 'closed') throw new HttpError(409, 'submission.deadline_passed', 'Срок сдачи истёк')
  const files = takeFiles(body.files)
  if (!files.length && !body.comment?.trim()) throw new HttpError(422, 'submission.empty', 'Прикрепите файл или напишите комментарий')
  const x: MockAttempt = {
    id: uid('sb'),
    assignment_id: a.id,
    student_id: u.id,
    number: p.attempts + 1,
    comment: body.comment?.trim() || null,
    is_late: window === 'late',
    created_at: now.toISOString(),
    files,
    review: null,
  }
  data.attempts.push(x)
  notify([c.teacher_id], {
    type: 'submission_created',
    title: 'Новая попытка',
    text: `${u.last_name} ${u.first_name[0]}. — «${a.title}», попытка ${x.number}`,
    course_id: c.id,
    target: target('review', { course_id: c.id, assignment_id: a.id, submission_id: x.id, student_id: u.id }),
  })
  return toAttempt(x)
})
on('GET', '/api/courses/{course_id}/assignments/{assignment_id}/submissions', ({ params }) => {
  const u = requireUser()
  const [, a] = assignmentFor(u, params.course_id, params.assignment_id)
  return { items: attemptsOf(a.id, u.id).reverse().map(toAttempt) }
})

// reviews
on('GET', '/api/reviews/queue', ({ query }) => {
  const u = requireUser()
  if (u.role !== 'teacher') throw forbidden()
  const courseId = query.get('course_id')
  const assignmentId = query.get('assignment_id')
  const ids = visibleCourses(u).filter((c) => !courseId || c.id === courseId).map((c) => c.id)
  const items: QueueItem[] = pendingFor(isDemoEmpty() ? [] : ids)
    .filter((x) => !assignmentId || x.assignment_id === assignmentId)
    .sort((a, b) => a.created_at.localeCompare(b.created_at))
    .map((x) => {
      const a = data.assignments.find((y) => y.id === x.assignment_id)!
      const c = data.courses.find((y) => y.id === a.course_id)!
      const s = userById(x.student_id)
      return {
        submission_id: x.id,
        number: x.number,
        created_at: x.created_at,
        is_late: x.is_late,
        student: person(s),
        group: groupRef(s.group_id!),
        in_course: c.group_ids.includes(s.group_id!),
        course: { id: c.id, name: c.name },
        assignment: { id: a.id, type: a.type, title: a.title },
      }
    })
  return paginate(items, query)
})
on('GET', '/api/courses/{course_id}/assignments/{assignment_id}/students/{student_id}/submissions', ({ params }) => {
  const u = requireUser()
  ownCourse(u, params.course_id, { writable: false })
  const [, a] = assignmentFor(u, params.course_id, params.assignment_id)
  const s = data.users.find((x) => x.id === params.student_id && x.role === 'student')
  if (!s) throw notFound('Студент не найден')
  return {
    student: person(s),
    assignment: { id: a.id, type: a.type, title: a.title },
    scale: scaleOf(a),
    attempts: attemptsOf(a.id, s.id).reverse().map(toAttempt),
  }
})
function reviewHandler(correct: boolean): Handler {
  return ({ params, body }) => {
    const u = requireUser()
    const c = ownCourse(u, params.course_id)
    const [, a] = assignmentFor(u, params.course_id, params.assignment_id)
    const x = data.attempts.find((y) => y.id === params.submission_id && y.assignment_id === a.id)
    if (!x) throw notFound('Попытка не найдена')
    const scale = scaleOf(a)
    const grade = body.grade ?? {}
    if (scale.type === 'range' && grade.score != null && (grade.score < scale.min! || grade.score > scale.max!)) {
      throw new HttpError(422, 'review.grade_out_of_scale', `Оценка должна быть от ${scale.min} до ${scale.max}`)
    }
    const now = new Date().toISOString()
    if (correct) {
      if (!x.review) throw new HttpError(409, 'review.not_reviewed', 'Попытка ещё не проверена')
      Object.assign(x.review, { score: grade.score ?? null, passed: grade.passed ?? null, comment: body.comment ?? null, updated_at: now })
    } else {
      if (x.review) throw new HttpError(409, 'review.already_reviewed', 'Попытка уже проверена')
      if (attemptsOf(a.id, x.student_id).at(-1)?.id !== x.id) throw new HttpError(409, 'review.not_last', 'Проверяется только последняя попытка')
      if (body.verdict === 'accepted' && grade.score == null && grade.passed == null) {
        throw new HttpError(422, 'review.grade_required', 'При вердикте «принято» нужна оценка')
      }
      x.review = { verdict: body.verdict, score: grade.score ?? null, passed: grade.passed ?? null, comment: body.comment ?? null, created_at: now, updated_at: now }
    }
    const verdict = x.review!.verdict === 'accepted' ? 'принято' : 'на доработку'
    notify([x.student_id], {
      type: correct ? 'grade_changed' : 'submission_reviewed',
      title: correct ? 'Оценка изменена' : 'Работа проверена',
      text: `«${a.title}»: ${verdict}`,
      course_id: c.id,
      target: target('assignment', { course_id: c.id, assignment_id: a.id }),
    })
    return toAttempt(x)
  }
}
on('POST', '/api/courses/{course_id}/assignments/{assignment_id}/submissions/{submission_id}/review', reviewHandler(false))
on('PUT', '/api/courses/{course_id}/assignments/{assignment_id}/submissions/{submission_id}/review', reviewHandler(true))

// schedule
on('GET', '/api/schedule/slots', () => ({ items: SLOTS }))
on('GET', '/api/courses/{course_id}/schedule', ({ params }) => {
  const u = requireUser()
  const c = courseFor(u, params.course_id)
  const mine = (g: string) => u.role !== 'student' || g === u.group_id
  const ruleOut = (r: (typeof data.rules)[number]) => ({
    id: r.id,
    group: groupRef(r.group_id),
    lesson_type: r.lesson_type,
    weekday: r.weekday,
    slot: r.slot,
    starts_at: slot(r.slot).starts_at,
    ends_at: slot(r.slot).ends_at,
    repeat: r.repeat,
    room: r.room,
  })
  return {
    semester: c.semester,
    rules: data.rules.filter((r) => r.course_id === c.id && mine(r.group_id)).sort((a, b) => a.weekday - b.weekday || a.slot - b.slot).map(ruleOut),
    extras: data.extras
      .filter((e) => e.course_id === c.id && mine(e.group_id))
      .map((e) => ({ id: e.id, group: groupRef(e.group_id), lesson_type: e.lesson_type, day: e.day, slot: e.slot, starts_at: slot(e.slot).starts_at, ends_at: slot(e.slot).ends_at, room: e.room })),
  }
})
function ruleOutOf(r: (typeof data.rules)[number]) {
  return { id: r.id, group: groupRef(r.group_id), lesson_type: r.lesson_type, weekday: r.weekday, slot: r.slot, starts_at: slot(r.slot).starts_at, ends_at: slot(r.slot).ends_at, repeat: r.repeat, room: r.room }
}
on('POST', '/api/courses/{course_id}/schedule/rules', ({ params, body }) => {
  const c = ownCourse(requireUser(), params.course_id)
  if (!c.group_ids.includes(body.group_id)) throw new HttpError(422, 'schedule.group_not_in_course', 'Группа не состоит в курсе')
  const r = { id: uid('r'), course_id: c.id, group_id: body.group_id, lesson_type: body.lesson_type, weekday: body.weekday, slot: body.slot, repeat: body.repeat, room: body.room || null }
  data.rules.push(r)
  return ruleOutOf(r)
})
on('PUT', '/api/courses/{course_id}/schedule/rules/{rule_id}', ({ params, body }) => {
  const c = ownCourse(requireUser(), params.course_id)
  const r = data.rules.find((x) => x.id === params.rule_id && x.course_id === c.id)
  if (!r) throw notFound('Правило не найдено')
  Object.assign(r, { group_id: body.group_id, lesson_type: body.lesson_type, weekday: body.weekday, slot: body.slot, repeat: body.repeat, room: body.room || null })
  return ruleOutOf(r)
})
on('DELETE', '/api/courses/{course_id}/schedule/rules/{rule_id}', ({ params }) => {
  const c = ownCourse(requireUser(), params.course_id)
  data.rules = data.rules.filter((x) => !(x.id === params.rule_id && x.course_id === c.id))
  return {}
})

// exams
on('GET', '/api/courses/{course_id}/exams', ({ params }) => {
  const u = requireUser()
  const c = courseFor(u, params.course_id)
  return {
    items: data.exams
      .filter((x) => x.course_id === c.id && (u.role !== 'student' || x.group_id === u.group_id))
      .map((x) => ({ id: x.id, group: groupRef(x.group_id), exam_type: x.exam_type, day: x.day, slot: x.slot, starts_at: slot(x.slot).starts_at, ends_at: slot(x.slot).ends_at, room: x.room })),
  }
})

const examOut = (x: (typeof data.exams)[number]) => ({ id: x.id, group: groupRef(x.group_id), exam_type: x.exam_type, day: x.day, slot: x.slot, starts_at: slot(x.slot).starts_at, ends_at: slot(x.slot).ends_at, room: x.room })
const extraOut = (e: (typeof data.extras)[number]) => ({ id: e.id, group: groupRef(e.group_id), lesson_type: e.lesson_type, day: e.day, slot: e.slot, starts_at: slot(e.slot).starts_at, ends_at: slot(e.slot).ends_at, room: e.room })
function checkDay(c: MockCourse, day: string, until: string) {
  if (day < c.semester.starts_on || day > until) throw new HttpError(422, 'schedule.out_of_semester', 'Дата вне семестра курса')
}
on('POST', '/api/courses/{course_id}/exams', ({ params, body }) => {
  const c = ownCourse(requireUser(), params.course_id)
  checkDay(c, body.day, c.semester.ends_on)
  if (data.exams.some((x) => x.course_id === c.id && x.group_id === body.group_id)) throw new HttpError(409, 'exam.exists', 'У группы уже есть итоговый контроль в этом курсе')
  const x = { id: uid('x'), course_id: c.id, group_id: body.group_id, exam_type: body.exam_type, day: body.day, slot: body.slot, room: body.room || null }
  data.exams.push(x)
  return examOut(x)
})
on('PUT', '/api/courses/{course_id}/exams/{exam_id}', ({ params, body }) => {
  const c = ownCourse(requireUser(), params.course_id)
  const x = data.exams.find((y) => y.id === params.exam_id && y.course_id === c.id)
  if (!x) throw notFound('Экзамен не найден')
  checkDay(c, body.day, c.semester.ends_on)
  Object.assign(x, { group_id: body.group_id, exam_type: body.exam_type, day: body.day, slot: body.slot, room: body.room || null })
  return examOut(x)
})
on('DELETE', '/api/courses/{course_id}/exams/{exam_id}', ({ params }) => {
  const c = ownCourse(requireUser(), params.course_id)
  data.exams = data.exams.filter((y) => !(y.id === params.exam_id && y.course_id === c.id))
  return {}
})
on('POST', '/api/courses/{course_id}/schedule/extras', ({ params, body }) => {
  const c = ownCourse(requireUser(), params.course_id)
  checkDay(c, body.day, c.semester.classes_end_on)
  const e = { id: uid('e'), course_id: c.id, group_id: body.group_id, lesson_type: body.lesson_type, day: body.day, slot: body.slot, room: body.room || null }
  data.extras.push(e)
  return extraOut(e)
})
on('PUT', '/api/courses/{course_id}/schedule/extras/{extra_id}', ({ params, body }) => {
  const c = ownCourse(requireUser(), params.course_id)
  const e = data.extras.find((y) => y.id === params.extra_id && y.course_id === c.id)
  if (!e) throw notFound('Занятие не найдено')
  checkDay(c, body.day, c.semester.classes_end_on)
  Object.assign(e, { group_id: body.group_id, lesson_type: body.lesson_type, day: body.day, slot: body.slot, room: body.room || null })
  return extraOut(e)
})
on('DELETE', '/api/courses/{course_id}/schedule/extras/{extra_id}', ({ params }) => {
  const c = ownCourse(requireUser(), params.course_id)
  data.extras = data.extras.filter((y) => !(y.id === params.extra_id && y.course_id === c.id))
  return {}
})

// material files
on('POST', '/api/courses/{course_id}/materials/{material_id}/files', ({ params, body }) => {
  const c = ownCourse(requireUser(), params.course_id)
  const m = data.materials.find((x) => x.id === params.material_id && x.course_id === c.id)
  if (!m) throw notFound('Материал не найден')
  m.files.push(...takeFiles([body]))
  m.updated_at = new Date().toISOString()
  return toMaterial(m)
})
on('DELETE', '/api/courses/{course_id}/materials/{material_id}/files/{file_id}', ({ params }) => {
  const c = ownCourse(requireUser(), params.course_id)
  const m = data.materials.find((x) => x.id === params.material_id && x.course_id === c.id)
  if (!m) throw notFound('Материал не найден')
  m.files = m.files.filter((f) => f.id !== params.file_id)
  return {}
})

// calendar and personal tasks
on('GET', '/api/calendar', ({ query }) => {
  const u = requireUser()
  const view = (query.get('view') ?? 'week') as CalendarView
  const date = query.get('date') ?? isoDay()
  const period = calendarPeriod(view, date)
  const semesters = [...new Map(visibleCourses(u).map((c) => [`${c.semester.term}${c.semester.year}`, c.semester])).values()]
  const weeks: CalendarWeek[] = []
  for (let w = startOfWeek(period.starts_on); w <= period.ends_on; w = addDays(w, 7)) weeks.push(weekInfo(w, semesters))
  return { period: { view, ...period }, weeks, items: isDemoEmpty() ? [] : calendarItems(u, period.starts_on, period.ends_on) }
})
const taskOut = (t: (typeof data.tasks)[number]) => ({ id: t.id, title: t.title, due_date: t.due_date, due_time: t.due_time, is_done: t.is_done, created_at: t.created_at })
function ownTask(id: string) {
  const u = requireUser()
  const t = data.tasks.find((x) => x.id === id && x.student_id === u.id)
  if (!t) throw notFound('Задача не найдена')
  return t
}
on('GET', '/api/personal-tasks', ({ query }) => {
  const u = requireUser()
  const from = query.get('from')!
  const to = query.get('to')!
  return { items: data.tasks.filter((t) => t.student_id === u.id && t.due_date >= from && t.due_date <= to).map(taskOut) }
})
on('POST', '/api/personal-tasks', ({ body }) => {
  const u = requireUser()
  if (u.role !== 'student') throw forbidden()
  const t = { id: uid('t'), student_id: u.id, title: body.title, due_date: body.due_date, due_time: body.due_time ?? null, is_done: false, created_at: new Date().toISOString() }
  data.tasks.push(t)
  return taskOut(t)
})
on('PUT', '/api/personal-tasks/{task_id}', ({ params, body }) => {
  const t = ownTask(params.task_id)
  Object.assign(t, { title: body.title, due_date: body.due_date, due_time: body.due_time ?? null })
  return taskOut(t)
})
on('PATCH', '/api/personal-tasks/{task_id}/done', ({ params, body }) => {
  const t = ownTask(params.task_id)
  t.is_done = Boolean(body.is_done)
  return taskOut(t)
})
on('DELETE', '/api/personal-tasks/{task_id}', ({ params }) => {
  const t = ownTask(params.task_id)
  data.tasks = data.tasks.filter((x) => x !== t)
  return {}
})

// notifications
const mine = (u: MockUser) => data.notifications.filter((n) => n.user_id === u.id).sort((a, b) => b.created_at.localeCompare(a.created_at))
on('GET', '/api/notifications', ({ query }) => {
  const u = requireUser()
  const list = isDemoEmpty() ? [] : mine(u).filter((n) => query.get('unread') !== 'true' || !n.is_read)
  return paginate(list.map(toNotification), query)
})
on('GET', '/api/notifications/unread-count', () => ({ unread_count: isDemoEmpty() ? 0 : mine(requireUser()).filter((n) => !n.is_read).length }))
on('POST', '/api/notifications/read-all', () => {
  const list = mine(requireUser()).filter((n) => !n.is_read)
  list.forEach((n) => (n.is_read = true))
  return { marked: list.length, unread_count: 0 }
})
on('POST', '/api/notifications/{notification_id}/read', ({ params }) => {
  const n = mine(requireUser()).find((x) => x.id === params.notification_id)
  if (!n) throw notFound('Уведомление не найдено')
  n.is_read = true
  return toNotification(n)
})

// ── fetch ─────────────────────────────────────────────────────────────────

const json = (status: number, body: unknown) =>
  new Response(status === 204 ? null : JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

export async function mockFetch(request: Request): Promise<Response> {
  const url = new URL(request.url, location.origin)
  const demo = new URLSearchParams(location.search).get('mock')
  await sleep(demo === 'slow' ? 2500 : 180 + Math.random() * 320)

  const route = routes.find((r) => r.method === request.method && r.pattern.test(url.pathname))
  if (!route) return json(404, { error: { code: 'http.404', message: 'Не найдено', details: null, request_id: 'demo' } })

  if (demo === 'error' && request.method === 'GET' && !url.pathname.startsWith('/api/auth')) {
    return json(503, { error: { code: 'demo.unavailable', message: 'Сервер временно недоступен', details: null, request_id: 'demo' } })
  }

  const match = url.pathname.match(route.pattern)!
  const params = Object.fromEntries(route.keys.map((k, i) => [k, decodeURIComponent(match[i + 1])]))
  const text = request.method === 'GET' ? '' : await request.text()
  try {
    const result = route.handler({ params, query: url.searchParams, body: text ? JSON.parse(text) : {} })
    return json(200, structuredClone(result))
  } catch (e) {
    if (e instanceof HttpError) return json(e.status, { error: { code: e.code, message: e.message, details: null, request_id: 'demo' } })
    console.error(e)
    return json(500, { error: { code: 'internal', message: 'Внутренняя ошибка', details: null, request_id: 'demo' } })
  }
}



/** Демо-WebSocket: через 25 секунд после входа приходит одно новое уведомление. */
export function mockLive(onMessage: (msg: { type: 'notification'; notification: Notification; unread_count: number }) => void) {
  const timer = setTimeout(() => {
    const u = sessionUser()
    if (!u) return
    if (u.role === 'teacher') {
      const a = data.assignments.find((x) => x.course_id === 'c-algo' && x.title === 'Двоичные деревья поиска')!
      notify([u.id], {
        type: 'submission_created',
        title: 'Новая попытка',
        text: `Белова М. — «${a.title}», попытка 1`,
        course_id: 'c-algo',
        target: target('assignment', { course_id: 'c-algo', assignment_id: a.id }),
      })
    } else {
      const c = data.courses.find((x) => x.id === 'c-os')!
      notify([u.id], {
        type: 'announcement_created',
        title: 'Новое объявление',
        text: 'Завтра практика в 207 начнётся на 15 минут позже.',
        course_id: c.id,
        target: target('course_feed', { course_id: c.id }),
      })
    }
    const list = mine(u)
    onMessage({ type: 'notification', notification: toNotification(list[0]), unread_count: list.filter((n) => !n.is_read).length })
  }, 25_000)
  return () => clearTimeout(timer)
}
