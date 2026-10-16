// Перечень снимков: имя файла, роль, адрес и подготовка страницы перед снимком.
// Идентификаторы курсов и заданий зависят от данных, поэтому переходим кликами по названиям.
const openCourse = async (page, name) => {
  await page.goto(page.url().replace(/\/[^/]*$/, '/'))
  await page.getByRole('link', { name: new RegExp('^' + name) }).first().click()
  await page.waitForLoadState('networkidle')
}
const course = (name, then) => async (page) => {
  await openCourse(page, name)
  if (then) await then(page)
}
const courseSub = (name, sub) => async (page) => {
  await openCourse(page, name)
  await page.goto(page.url() + sub)
  await page.waitForLoadState('networkidle')
}
const openAssignment = (title) => async (page) => {
  await page.getByRole('link', { name: new RegExp(title) }).first().click()
  await page.waitForLoadState('networkidle')
}

export default [
  { name: '01-login', path: '/login', fullPage: false },
  { name: '02-register', path: '/register', fullPage: false },
  {
    name: '02b-register-validation',
    path: '/register',
    fullPage: false,
    prepare: async (page) => {
      await page.getByLabel('Email').fill('anna@')
      await page.getByLabel('Пароль', { exact: true }).fill('123')
      await page.getByLabel('Повтор пароля').fill('1234')
      await page.getByRole('button', { name: 'Зарегистрироваться' }).click()
    },
  },
  { name: '03-student-home', as: 'student', path: '/' },
  { name: '04-student-course', as: 'student', path: '/', prepare: course('Алгоритмы') },
  { name: '05-student-assignment', as: 'student', path: '/', prepare: course('Алгоритмы', openAssignment('Сортировки')) },
  { name: '06-student-assignment-submit', as: 'student', path: '/', prepare: course('Базы данных', openAssignment('Нормализация')) },
  { name: '07-student-calendar-week', as: 'student', path: '/calendar?view=week' },
  { name: '08-student-calendar-month', as: 'student', path: '/calendar?view=month' },
  { name: '08b-student-calendar-day', as: 'student', path: '/calendar?view=day' },
  { name: '08c-student-calendar-schedule', as: 'student', path: '/calendar?view=schedule' },
  {
    name: '08d-student-event-card',
    as: 'student',
    path: '/calendar?view=week',
    prepare: async (page) => page.locator('section[aria-label="Календарь"] button', { hasText: 'Базы данных' }).first().click(),
  },
  {
    name: '09-student-task-dialog',
    as: 'student',
    path: '/calendar?view=week',
    fullPage: false,
    prepare: async (page) => page.getByRole('button', { name: 'Создать', exact: true }).click(),
  },
  { name: '10-student-notifications', as: 'student', path: '/notifications' },
  { name: '11-student-profile', as: 'student', path: '/profile' },
  { name: '12-student-archive', as: 'student', path: '/courses/archive' },
  // Состояния экранов: ответы API подменяются, поэтому снимки получаются в любом режиме.
  {
    name: '13-state-loading',
    as: 'student',
    path: '/',
    wait: 800,
    idle: false,
    fullPage: false,
    intercept: (page) => page.route('**/api/home', () => new Promise(() => {})),
  },
  {
    name: '14-state-error',
    as: 'student',
    path: '/notifications',
    wait: 2500,
    fullPage: false,
    intercept: (page) =>
      page.route('**/api/notifications?**', (r) =>
        r.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: { code: 'unavailable', message: 'Сервер временно недоступен', details: {}, request_id: '-' } }) }),
      ),
  },
  {
    name: '15-state-empty',
    as: 'student',
    path: '/',
    fullPage: false,
    intercept: (page) =>
      page.route('**/api/home', (r) =>
        r.fulfill({ contentType: 'application/json', body: JSON.stringify({ nearest_deadline: null, upcoming_deadlines: [], pending_reviews: null, upcoming_lessons: [], courses: [], courses_total: 0 }) }),
      ),
  },
  { name: '16-not-found', as: 'student', path: '/nope', fullPage: false },
  { name: '17-mobile-home', as: 'student', path: '/', viewport: { width: 390, height: 844 } },
  {
    name: '18-mobile-menu',
    as: 'student',
    path: '/',
    viewport: { width: 390, height: 844 },
    fullPage: false,
    prepare: async (page) => page.getByRole('button', { name: 'Главное меню' }).click(),
  },
  { name: '20-teacher-home', as: 'teacher', path: '/' },
  { name: '21-teacher-course', as: 'teacher', path: '/', prepare: course('Алгоритмы') },
  { name: '22-teacher-assignment-students', as: 'teacher', path: '/', prepare: course('Алгоритмы', openAssignment('Сортировки')) },
  { name: '23-teacher-review-queue', as: 'teacher', path: '/reviews' },
  {
    name: '24-teacher-review',
    as: 'teacher',
    path: '/reviews',
    prepare: async (page) => {
      await page.getByRole('row').nth(1).click()
      await page.waitForLoadState('networkidle')
    },
  },
  { name: '25-teacher-assignment-new', as: 'teacher', path: '/', prepare: courseSub('Алгоритмы', '/assignments/new') },
  {
    name: '26-teacher-assignment-edit',
    as: 'teacher',
    path: '/',
    prepare: async (page) => {
      await openCourse(page, 'Алгоритмы')
      await openAssignment('Рекурсия')(page)
      await page.getByRole('link', { name: 'Изменить' }).click()
      await page.waitForLoadState('networkidle')
    },
  },
  { name: '27-teacher-course-new', as: 'teacher', path: '/courses/new' },
  { name: '28-teacher-course-settings', as: 'teacher', path: '/', prepare: courseSub('Алгоритмы', '/settings') },
  { name: '29-teacher-calendar', as: 'teacher', path: '/calendar?view=week' },
  {
    name: '31-teacher-material-edit',
    as: 'teacher',
    path: '/',
    fullPage: false,
    prepare: course('Алгоритмы', async (page) => page.getByRole('button', { name: /Изменить «Учебник»/ }).click()),
  },
  { name: '32-teacher-notifications', as: 'teacher', path: '/notifications' },
]
