import { addDays, isoDay, startOfWeek } from '@/shared/lib/date'

import type {
  AssignmentType,
  DeadlineType,
  ExamType,
  LessonType,
  NotificationType,
  ReviewVerdict,
  Scale,
  ScheduleRepeat,
  Semester,
  UserRole,
} from '../types'

// Демонстрационная база в памяти браузера. Даты считаются от сегодняшнего дня,
// поэтому дедлайны и занятия всегда «рядом». После перезагрузки страницы база
// собирается заново.

export type MockFile = { id: string; file_name: string; file_size: number; content_type: string }

export type MockUser = {
  id: string
  last_name: string
  first_name: string
  middle_name: string | null
  email: string
  password: string
  role: UserRole
  group_id: string | null
  department: string | null
  avatar_url: string | null
  is_active: boolean
}

export type MockGroup = { id: string; name: string; code: string; emails: string[] }

export type MockCourse = {
  id: string
  name: string
  description: string | null
  teacher_id: string
  semester: Semester
  scale: Scale
  grading_note: string | null
  is_archived: boolean
  group_ids: string[]
  created_at: string
}

export type MockMaterial = {
  id: string
  course_id: string
  title: string
  text: string | null
  created_at: string
  updated_at: string
  files: MockFile[]
}

export type MockAnnouncement = { id: string; course_id: string; text: string; created_at: string; updated_at: string }

export type MockAssignment = {
  id: string
  course_id: string
  type: AssignmentType
  title: string
  description: string | null
  deadline_type: DeadlineType
  deadline_at: string | null
  own_scale: Scale | null
  grading_note: string | null
  created_at: string
  updated_at: string
  files: MockFile[]
}

export type MockReview = {
  verdict: ReviewVerdict
  score: number | null
  passed: boolean | null
  comment: string | null
  created_at: string
  updated_at: string
}

export type MockAttempt = {
  id: string
  assignment_id: string
  student_id: string
  number: number
  comment: string | null
  is_late: boolean
  created_at: string
  files: MockFile[]
  review: MockReview | null
}

export type MockRule = {
  id: string
  course_id: string
  group_id: string
  lesson_type: LessonType
  weekday: number
  slot: number
  repeat: ScheduleRepeat
  room: string | null
}

export type MockExtra = {
  id: string
  course_id: string
  group_id: string
  lesson_type: LessonType
  day: string
  slot: number
  room: string | null
}

export type MockExam = {
  id: string
  course_id: string
  group_id: string
  exam_type: ExamType
  day: string
  slot: number
  room: string | null
}

export type MockTask = {
  id: string
  student_id: string
  title: string
  due_date: string
  due_time: string | null
  is_done: boolean
  created_at: string
}

export type MockNotification = {
  id: string
  user_id: string
  type: NotificationType
  title: string
  text: string
  course_id: string | null
  target: {
    section: 'course_feed' | 'assignment' | 'materials' | 'schedule' | 'calendar' | 'review'
    course_id: string | null
    assignment_id: string | null
    submission_id: string | null
    student_id: string | null
    day: string | null
  }
  is_read: boolean
  created_at: string
}

export const SLOTS = [
  { number: 1, starts_at: '09:30:00', ends_at: '11:00:00' },
  { number: 2, starts_at: '11:15:00', ends_at: '12:45:00' },
  { number: 3, starts_at: '13:00:00', ends_at: '14:30:00' },
  { number: 4, starts_at: '15:10:00', ends_at: '16:40:00' },
  { number: 5, starts_at: '16:55:00', ends_at: '18:25:00' },
]

let seq = 0
export const uid = (prefix = 'id') => `${prefix}-${(++seq).toString(36)}-${Math.random().toString(36).slice(2, 8)}`

/** Момент по МСК: день + «ЧЧ:ММ». */
export const msk = (day: string, time: string) => `${day}T${time}:00+03:00`

/** Момент в UTC через `minutes` от текущего. */
const ago = (minutes: number) => new Date(Date.now() - minutes * 60_000).toISOString()

/** Текущий семестр по дате: осенний — сентябрь–январь, весенний — февраль–июль. */
export function currentSemester(today = isoDay()): Semester {
  const year = Number(today.slice(0, 4))
  const month = Number(today.slice(5, 7))
  if (month >= 2 && month <= 7) {
    return { term: 'spring', year, starts_on: `${year}-02-01`, classes_end_on: `${year}-06-10`, ends_on: `${year}-07-10` }
  }
  const y = month === 1 ? year - 1 : year
  return { term: 'autumn', year: y, starts_on: `${y}-09-01`, classes_end_on: `${y}-12-30`, ends_on: `${y + 1}-01-31` }
}

function file(file_name: string, file_size: number, content_type: string): MockFile {
  return { id: uid('f'), file_name, file_size, content_type }
}

const PDF = 'application/pdf'
const DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
const PY = 'text/x-python'

export type MockDb = ReturnType<typeof createDb>

export function createDb() {
  const today = isoDay()
  const semester = currentSemester(today)
  const past = { term: 'spring' as const, year: semester.year, starts_on: `${semester.year}-02-01`, classes_end_on: `${semester.year}-06-10`, ends_on: `${semester.year}-07-10` }

  // Группы и пользователи
  const g1: MockGroup = { id: 'g-bvt2401', name: 'БВТ2401', code: 'BVT-7Q4K', emails: [] }
  const g2: MockGroup = { id: 'g-bvt2402', name: 'БВТ2402', code: 'BVT-2M9X', emails: [] }
  const g3: MockGroup = { id: 'g-bvt2403', name: 'БВТ2403', code: 'BVT-5J1R', emails: [] }
  const groups = [g1, g2, g3]

  const person = (
    id: string,
    last_name: string,
    first_name: string,
    middle_name: string,
    email: string,
    role: UserRole,
    extra: Partial<MockUser> = {},
  ): MockUser => ({
    id,
    last_name,
    first_name,
    middle_name,
    email,
    password: 'labka2026',
    role,
    group_id: null,
    department: null,
    avatar_url: null,
    is_active: true,
    ...extra,
  })

  const student = person('u-student', 'Смирнова', 'Анна', 'Сергеевна', 'student@labka.ru', 'student', { group_id: g1.id })
  const teacher = person('u-teacher', 'Петров', 'Павел', 'Андреевич', 'teacher@labka.ru', 'teacher', {
    department: 'Кафедра вычислительной техники',
  })
  const sokolova = person('u-sokolova', 'Соколова', 'Елена', 'Викторовна', 'sokolova@labka.ru', 'teacher', {
    department: 'Кафедра сетей и телекоммуникаций',
  })
  const kuznetsov = person('u-kuznetsov', 'Кузнецов', 'Игорь', 'Олегович', 'kuznetsov@labka.ru', 'teacher', {
    department: 'Кафедра вычислительной техники',
  })

  const classmates: [string, string, string, string][] = [
    ['Алексеев', 'Дмитрий', 'Игоревич', g1.id],
    ['Белова', 'Мария', 'Александровна', g1.id],
    ['Волков', 'Никита', 'Сергеевич', g1.id],
    ['Григорьева', 'Ольга', 'Павловна', g1.id],
    ['Денисов', 'Артём', 'Викторович', g1.id],
    ['Егорова', 'Софья', 'Андреевна', g1.id],
    ['Жуков', 'Илья', 'Романович', g2.id],
    ['Зайцева', 'Полина', 'Дмитриевна', g2.id],
    ['Иванов', 'Кирилл', 'Олегович', g2.id],
    ['Комарова', 'Вероника', 'Ильинична', g2.id],
    ['Лебедев', 'Максим', 'Андреевич', g2.id],
    ['Морозова', 'Дарья', 'Евгеньевна', g2.id],
  ]
  const others = classmates.map(([l, f, m, g], i) =>
    person(`u-s${i + 1}`, l, f, m, `s${i + 1}@labka.ru`, 'student', { group_id: g }),
  )
  const users = [student, teacher, sokolova, kuznetsov, ...others]
  g1.emails = users.filter((u) => u.group_id === g1.id).map((u) => u.email).concat('new.student@labka.ru')
  g2.emails = users.filter((u) => u.group_id === g2.id).map((u) => u.email)

  // Курсы
  const range = (min: number, max: number): Scale => ({ type: 'range', min, max })
  const binary: Scale = { type: 'binary', min: null, max: null }
  const created = (days: number) => msk(addDays(semester.starts_on, days), '10:00')

  const algo: MockCourse = {
    id: 'c-algo',
    name: 'Алгоритмы и структуры данных',
    description: 'Сложность алгоритмов, сортировки, деревья, хеш-таблицы и графы. Лабораторные сдаются на Python или C++.',
    teacher_id: teacher.id,
    semester,
    scale: range(2, 5),
    grading_note: '3 — программа работает, 4 — плюс тесты, 5 — плюс защита у доски',
    is_archived: false,
    group_ids: [g1.id, g2.id],
    created_at: created(-5),
  }
  const db: MockCourse = {
    id: 'c-db',
    name: 'Базы данных',
    description: 'Реляционная модель, SQL, нормализация, индексы и транзакции на PostgreSQL.',
    teacher_id: teacher.id,
    semester,
    scale: range(2, 5),
    grading_note: 'Оценка за работу — среднее за запросы и отчёт',
    is_archived: false,
    group_ids: [g1.id],
    created_at: created(-4),
  }
  const nets: MockCourse = {
    id: 'c-nets',
    name: 'Компьютерные сети',
    description: 'Модель OSI, адресация, маршрутизация, анализ трафика в Wireshark.',
    teacher_id: sokolova.id,
    semester,
    scale: binary,
    grading_note: 'Работа зачтена, если отчёт содержит все снимки трафика и выводы',
    is_archived: false,
    group_ids: [g1.id],
    created_at: created(-3),
  }
  const os: MockCourse = {
    id: 'c-os',
    name: 'Операционные системы',
    description: 'Процессы и потоки, планирование, память, файловые системы. Практика в Linux.',
    teacher_id: kuznetsov.id,
    semester,
    scale: range(2, 5),
    grading_note: null,
    is_archived: false,
    group_ids: [g1.id],
    created_at: created(-2),
  }
  const discrete: MockCourse = {
    id: 'c-discrete',
    name: 'Дискретная математика',
    description: 'Множества, комбинаторика, графы и булевы функции.',
    teacher_id: teacher.id,
    semester: past,
    scale: range(2, 5),
    grading_note: null,
    is_archived: true,
    group_ids: [g1.id, g2.id],
    created_at: msk(past.starts_on, '10:00'),
  }
  const courses = [algo, db, nets, os, discrete]

  // Материалы и объявления
  const materials: MockMaterial[] = [
    {
      id: uid('m'),
      course_id: algo.id,
      title: 'Учебник',
      text: 'Кормен, Лейзерсон, Ривест, Штайн — «Алгоритмы: построение и анализ». Главы 1–4 к первой лабораторной.',
      created_at: created(0),
      updated_at: created(0),
      files: [file('Кормен_главы_1-4.pdf', 8_400_000, PDF)],
    },
    {
      id: uid('m'),
      course_id: algo.id,
      title: 'Оформление отчётов',
      text: 'Шаблон отчёта и требования к коду: тесты, README, понятные имена. Пример хорошего отчёта — в [репозитории кафедры](https://example.org).',
      created_at: created(2),
      updated_at: created(9),
      files: [file('Шаблон_отчёта.docx', 64_000, DOCX), file('Методичка.pdf', 1_200_000, PDF)],
    },
    {
      id: uid('m'),
      course_id: db.id,
      title: 'Учебная база «Университет»',
      text: 'Дамп для всех лабораторных. Восстановить: `psql -f university.sql`.',
      created_at: created(1),
      updated_at: created(1),
      files: [file('university.sql', 420_000, 'application/sql')],
    },
    {
      id: uid('m'),
      course_id: nets.id,
      title: 'Wireshark: быстрый старт',
      text: 'Установка, фильтры отображения и сохранение снимков.',
      created_at: created(1),
      updated_at: created(1),
      files: [file('wireshark_quickstart.pdf', 2_100_000, PDF)],
    },
  ]

  const announcements: MockAnnouncement[] = [
    {
      id: uid('a'),
      course_id: algo.id,
      text: 'Пара в четверг переносится на третью, аудитория та же. Защиты лабораторной по сортировкам — на этой же паре.',
      created_at: ago(60 * 26),
      updated_at: ago(60 * 26),
    },
    {
      id: uid('a'),
      course_id: db.id,
      text: 'К следующему занятию поставьте PostgreSQL 18 и восстановите учебную базу из материалов курса.',
      created_at: ago(60 * 24 * 6),
      updated_at: ago(60 * 24 * 6),
    },
    {
      id: uid('a'),
      course_id: nets.id,
      text: 'Отчёты принимаются только в PDF, снимки трафика прикладывайте отдельными файлами .pcapng.',
      created_at: ago(60 * 24 * 9),
      updated_at: ago(60 * 24 * 9),
    },
  ]

  // Задания
  const assignment = (
    course: MockCourse,
    type: AssignmentType,
    title: string,
    deadline: { type: DeadlineType; day?: number; time?: string },
    extra: Partial<MockAssignment> = {},
  ): MockAssignment => {
    const at = created(Math.max(0, (deadline.day ?? 0) + 40 - 30))
    return {
      id: uid('as'),
      course_id: course.id,
      type,
      title,
      description: null,
      deadline_type: deadline.type,
      deadline_at: deadline.type === 'none' ? null : msk(addDays(today, deadline.day ?? 0), deadline.time ?? '23:59'),
      own_scale: null,
      grading_note: null,
      created_at: at < new Date().toISOString() ? at : ago(60 * 24 * 3),
      updated_at: at < new Date().toISOString() ? at : ago(60 * 24 * 3),
      files: [],
      ...extra,
    }
  }

  const aSort = assignment(algo, 'lab', 'Сортировки', { type: 'hard', day: -6 }, {
    description:
      'Реализуйте сортировку вставками, слиянием и быструю сортировку.\n\n' +
      '- Сравните время работы на массивах от 10³ до 10⁶ элементов.\n' +
      '- Постройте график и объясните результат.\n' +
      '- Покройте функции тестами.\n\n' +
      'Код — в репозитории, ссылку и отчёт приложите к попытке.',
    files: [file('Указания_к_лабе_1.pdf', 310_000, PDF)],
  })
  const aRec = assignment(algo, 'practice', 'Рекурсия и мемоизация', { type: 'soft', day: 2, time: '18:00' }, {
    description: 'Решите задачи 1–6 из методички. Для задач 4–6 сравните наивную рекурсию и вариант с мемоизацией.',
  })
  const aTrees = assignment(algo, 'lab', 'Двоичные деревья поиска', { type: 'hard', day: 9 }, {
    description:
      'Реализуйте BST со вставкой, удалением и обходами. Дополнительно — АВЛ-дерево с балансировкой.\n\n' +
      'Для оценки 5 нужна защита: объясните повороты на примере.',
    files: [file('Указания_к_лабе_2.pdf', 280_000, PDF)],
  })
  const aHash = assignment(algo, 'hw', 'Хеш-таблицы', { type: 'soft', day: 16 }, {
    description: 'Сравните открытую адресацию и метод цепочек на 10⁵ случайных ключей.',
  })
  const aGraphs = assignment(algo, 'lab', 'Графы', { type: 'none' }, {
    description: 'Обход в ширину и глубину, алгоритм Дейкстры. Срок — до конца семестра.',
  })
  const aSql = assignment(db, 'lab', 'Запросы SELECT', { type: 'hard', day: -12 }, {
    description: 'Напишите 15 запросов к учебной базе. Список — в указаниях.',
    files: [file('Запросы_SELECT.pdf', 150_000, PDF)],
  })
  const aIdx = assignment(db, 'hw', 'Индексы', { type: 'soft', day: 4 }, {
    description: 'Найдите три медленных запроса и ускорьте их индексами. Приложите EXPLAIN ANALYZE до и после.',
  })
  const aNorm = assignment(db, 'practice', 'Нормализация', { type: 'soft', day: -2 }, {
    description: 'Приведите схему из задания к 3НФ, обоснуйте каждый шаг.',
  })
  const aTcp = assignment(nets, 'lab', 'Анализ TCP-рукопожатия', { type: 'hard', day: 6, time: '12:00' }, {
    description: 'Снимите трафик установки TCP-соединения и разберите флаги SYN, SYN-ACK, ACK.',
  })
  const aDns = assignment(nets, 'practice', 'DNS-запросы', { type: 'soft', day: -9 })
  const aProc = assignment(os, 'lab', 'Процессы и сигналы', { type: 'hard', day: 1, time: '23:59' }, {
    description: 'Напишите программу, которая порождает дочерние процессы и обрабатывает SIGINT и SIGTERM.',
  })
  const aSched = assignment(os, 'hw', 'Планировщики', { type: 'soft', day: 12 })
  const aOld = assignment(discrete, 'lab', 'Булевы функции', { type: 'hard', day: -150 })

  const assignments = [aSort, aRec, aTrees, aHash, aGraphs, aSql, aIdx, aNorm, aTcp, aDns, aProc, aSched, aOld]
  aRec.grading_note = '4 — все задачи решены, 5 — плюс сравнение времени'

  // Попытки
  const attempts: MockAttempt[] = []
  const attempt = (
    a: MockAssignment,
    s: MockUser,
    minutesAgo: number,
    comment: string | null,
    files: MockFile[],
    review?: { verdict: ReviewVerdict; score?: number; passed?: boolean; comment?: string | null; after?: number },
  ) => {
    const number = attempts.filter((x) => x.assignment_id === a.id && x.student_id === s.id).length + 1
    const createdAt = ago(minutesAgo)
    const reviewedAt = review ? ago(Math.max(1, minutesAgo - (review.after ?? 120))) : null
    attempts.push({
      id: uid('sb'),
      assignment_id: a.id,
      student_id: s.id,
      number,
      comment,
      is_late: a.deadline_type === 'soft' && a.deadline_at !== null && createdAt > new Date(a.deadline_at).toISOString(),
      created_at: createdAt,
      files,
      review: review
        ? {
            verdict: review.verdict,
            score: review.score ?? null,
            passed: review.passed ?? null,
            comment: review.comment ?? null,
            created_at: reviewedAt!,
            updated_at: reviewedAt!,
          }
        : null,
    })
  }

  const day = 60 * 24
  // Анна: сортировки приняты со второй попытки
  attempt(aSort, student, day * 10, 'Первая версия, без тестов', [file('sorts.py', 4_200, PY)], {
    verdict: 'revision',
    score: 3,
    comment: 'Работает, но нет тестов и графика. Доделайте — поставлю выше.',
    after: day,
  })
  attempt(aSort, student, day * 8, 'Добавила тесты и график сравнения', [file('sorts.py', 6_100, PY), file('report.pdf', 540_000, PDF)], {
    verdict: 'accepted',
    score: 5,
    comment: 'Отличная работа и защита.',
    after: day,
  })
  // Анна: рекурсия на проверке
  attempt(aRec, student, 60 * 5, 'Задачи 1–6, сравнение в конце отчёта', [file('recursion.ipynb', 88_000, 'application/x-ipynb+json')])
  // Анна: БД
  attempt(aSql, student, day * 14, null, [file('queries.sql', 9_800, 'application/sql')], {
    verdict: 'accepted',
    score: 4,
    comment: 'Запросы 12 и 14 можно было без подзапросов.',
  })
  attempt(aNorm, student, day * 4, 'Первая версия схемы', [file('normalization.pdf', 210_000, PDF)], {
    verdict: 'revision',
    comment: 'Таблица «Занятия» всё ещё не в 3НФ: преподаватель зависит от курса, а не от ключа.',
  })
  // Анна: сети
  attempt(aDns, student, day * 10, null, [file('dns_report.pdf', 1_400_000, PDF), file('dns.pcapng', 320_000, 'application/octet-stream')], {
    verdict: 'accepted',
    passed: true,
  })
  attempt(aOld, student, day * 160, null, [file('boolean.pdf', 300_000, PDF)], { verdict: 'accepted', score: 5 })

  // Одногруппники — чтобы у преподавателя были очередь и таблицы
  const pick = <T,>(list: T[], i: number) => list[i % list.length]
  others.forEach((s, i) => {
    const inAlgo = algo.group_ids.includes(s.group_id!)
    if (inAlgo) {
      if (i % 5 !== 4) {
        attempt(aSort, s, day * (9 - (i % 4)), pick(['Готово', 'Отчёт и код', null], i), [file('sorts.py', 4_000 + i * 100, PY)],
          i % 3 === 0 ? undefined : { verdict: i % 4 === 1 ? 'revision' : 'accepted', score: 3 + (i % 3), comment: i % 4 === 1 ? 'Нет сравнения времени' : null },
        )
      }
      if (i % 3 !== 2) {
        attempt(aRec, s, 60 * (3 + i * 7), pick(['Все задачи', 'Без 6-й задачи', null], i), [file('recursion.py', 3_000 + i * 50, PY)])
      }
      if (i % 4 === 0) {
        attempt(aTrees, s, 60 * (2 + i), 'Сделал заранее, АВЛ тоже есть', [file('bst.cpp', 12_000, 'text/x-c++src')])
      }
    }
    if (db.group_ids.includes(s.group_id!) && i % 2 === 0) {
      attempt(aIdx, s, 60 * (20 + i * 3), 'EXPLAIN до и после в отчёте', [file('indexes.pdf', 400_000, PDF)])
    }
  })

  // Расписание: правила на семестр
  const rule = (c: MockCourse, g: MockGroup, lesson_type: LessonType, weekday: number, slot: number, repeat: ScheduleRepeat, room: string): MockRule => ({
    id: uid('r'),
    course_id: c.id,
    group_id: g.id,
    lesson_type,
    weekday,
    slot,
    repeat,
    room,
  })
  const rules: MockRule[] = [
    rule(algo, g1, 'lab', 2, 2, 'weekly', '305'),
    rule(algo, g2, 'lab', 2, 3, 'weekly', '305'),
    rule(algo, g1, 'practice', 4, 3, 'even', '214'),
    rule(algo, g2, 'practice', 4, 4, 'odd', '214'),
    rule(db, g1, 'practice', 3, 1, 'weekly', '112'),
    rule(db, g1, 'lab', 5, 2, 'odd', '118'),
    rule(nets, g1, 'lab', 4, 1, 'weekly', '410'),
    rule(os, g1, 'lab', 1, 4, 'weekly', '207'),
    rule(os, g1, 'practice', 5, 3, 'even', '207'),
  ]
  const extras: MockExtra[] = [
    { id: uid('e'), course_id: algo.id, group_id: g1.id, lesson_type: 'lab', day: addDays(startOfWeek(today), 12), slot: 5, room: '305' },
  ]
  const exams: MockExam[] = [
    { id: uid('x'), course_id: algo.id, group_id: g1.id, exam_type: 'exam', day: `${semester.year + 1}-01-14`, slot: 2, room: '101' },
    { id: uid('x'), course_id: algo.id, group_id: g2.id, exam_type: 'exam', day: `${semester.year + 1}-01-15`, slot: 2, room: '101' },
    { id: uid('x'), course_id: nets.id, group_id: g1.id, exam_type: 'credit', day: `${semester.year}-12-26`, slot: 3, room: '410' },
    { id: uid('x'), course_id: db.id, group_id: g1.id, exam_type: 'graded_credit', day: `${semester.year}-12-24`, slot: 2, room: '112' },
  ]

  // Личные задачи студента
  const tasks: MockTask[] = [
    { id: uid('t'), student_id: student.id, title: 'Начать лабу по графам', due_date: addDays(today, 3), due_time: null, is_done: false, created_at: ago(day) },
    { id: uid('t'), student_id: student.id, title: 'Записаться на защиту по деревьям', due_date: addDays(today, 1), due_time: '12:00:00', is_done: false, created_at: ago(day * 2) },
    { id: uid('t'), student_id: student.id, title: 'Купить флешку для Wireshark-дампов', due_date: addDays(today, -1), due_time: null, is_done: true, created_at: ago(day * 4) },
    { id: uid('t'), student_id: student.id, title: 'Повторить нормальные формы', due_date: today, due_time: '20:00:00', is_done: false, created_at: ago(60 * 3) },
  ]

  // Уведомления
  const target = (section: MockNotification['target']['section'], t: Partial<MockNotification['target']> = {}) => ({
    section,
    course_id: null,
    assignment_id: null,
    submission_id: null,
    student_id: null,
    day: null,
    ...t,
  })
  const n = (
    user: MockUser,
    type: NotificationType,
    title: string,
    text: string,
    course: MockCourse | null,
    t: MockNotification['target'],
    minutesAgo: number,
    is_read = false,
  ): MockNotification => ({ id: uid('n'), user_id: user.id, type, title, text, course_id: course?.id ?? null, target: t, is_read, created_at: ago(minutesAgo) })

  const notifications: MockNotification[] = [
    n(student, 'deadline_reminder', 'Скоро дедлайн', 'Лаба «Процессы и сигналы» — сдать до завтра 23:59', os, target('assignment', { course_id: os.id, assignment_id: aProc.id }), 40),
    n(student, 'announcement_created', 'Новое объявление', 'Пара в четверг переносится на третью, аудитория та же.', algo, target('course_feed', { course_id: algo.id }), 60 * 26),
    n(student, 'submission_reviewed', 'Работа проверена', 'ПЗ «Нормализация»: на доработку', db, target('assignment', { course_id: db.id, assignment_id: aNorm.id }), 60 * 30),
    n(student, 'assignment_created', 'Новое задание', 'Лаба «Двоичные деревья поиска», жёсткий дедлайн', algo, target('assignment', { course_id: algo.id, assignment_id: aTrees.id }), day * 2, true),
    n(student, 'schedule_changed', 'Расписание изменено', 'Добавлено занятие: лаба по алгоритмам, 5 пара', algo, target('calendar', { course_id: algo.id, day: extras[0].day }), day * 3, true),
    n(student, 'exam_assigned', 'Назначен экзамен', `Экзамен по алгоритмам — 14 января, 2 пара, ауд. 101`, algo, target('calendar', { course_id: algo.id, day: exams[0].day }), day * 5, true),
    n(student, 'material_added', 'Новый материал', '«Оформление отчётов» в курсе «Алгоритмы и структуры данных»', algo, target('materials', { course_id: algo.id }), day * 7, true),
    n(student, 'submission_reviewed', 'Работа проверена', 'Лаба «Сортировки»: принято, оценка 5', algo, target('assignment', { course_id: algo.id, assignment_id: aSort.id }), day * 7, true),
  ]
  const queueForTeacher = attempts.filter((a) => !a.review && [algo.id, db.id].includes(assignments.find((x) => x.id === a.assignment_id)!.course_id))
  queueForTeacher
    .slice()
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, 5)
    .forEach((a, i) => {
      const s = users.find((u) => u.id === a.student_id)!
      const as = assignments.find((x) => x.id === a.assignment_id)!
      const c = courses.find((x) => x.id === as.course_id)!
      notifications.push(
        n(teacher, 'submission_created', 'Новая попытка', `${s.last_name} ${s.first_name[0]}. — «${as.title}», попытка ${a.number}`, c,
          target('review', { course_id: c.id, assignment_id: as.id, submission_id: a.id, student_id: s.id }),
          Math.round((Date.now() - new Date(a.created_at).getTime()) / 60_000), i > 2),
      )
    })

  return {
    groups,
    users,
    courses,
    materials,
    announcements,
    assignments,
    attempts,
    rules,
    extras,
    exams,
    tasks,
    notifications,
  }
}
