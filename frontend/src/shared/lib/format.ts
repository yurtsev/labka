import type {
  AssignmentType,
  DeadlineType,
  ExamType,
  Grade,
  LessonType,
  ProgressStatus,
  Scale,
  ScheduleRepeat,
} from '@/shared/api'

type Named = { last_name: string; first_name: string; middle_name: string | null }

/** «Петров Павел Андреевич». */
export const fullName = (p: Named) => [p.last_name, p.first_name, p.middle_name].filter(Boolean).join(' ')

/** «Петров П.А.». */
export const shortName = (p: Named) =>
  `${p.last_name} ${p.first_name[0]}.${p.middle_name ? `${p.middle_name[0]}.` : ''}`

export const initials = (p: Named) => `${p.last_name[0] ?? ''}${p.first_name[0] ?? ''}`

export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} КБ`
  return `${(bytes / 1024 / 1024).toFixed(1).replace(/\.0$/, '').replace('.', ',')} МБ`
}

export const ASSIGNMENT_TYPE: Record<AssignmentType, { short: string; long: string }> = {
  lab: { short: 'Лаба', long: 'Лабораторная работа' },
  practice: { short: 'ПЗ', long: 'Практическое занятие' },
  hw: { short: 'ДЗ', long: 'Домашнее задание' },
}

export const DEADLINE_TYPE: Record<DeadlineType, string> = {
  none: 'без дедлайна',
  soft: 'мягкий',
  hard: 'жёсткий',
}

export const STATUS: Record<ProgressStatus, string> = {
  not_submitted: 'не сдано',
  on_review: 'на проверке',
  revision: 'на доработку',
  accepted: 'принято',
}

export const LESSON_TYPE: Record<LessonType, string> = { lab: 'Лаба', practice: 'ПЗ' }

export const EXAM_TYPE: Record<ExamType, string> = {
  credit: 'Зачёт',
  graded_credit: 'Дифф. зачёт',
  exam: 'Экзамен',
}

export const REPEAT: Record<ScheduleRepeat, string> = {
  weekly: 'каждую неделю',
  even: 'по чётным',
  odd: 'по нечётным',
}

export const WEEKDAYS = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
export const WEEKDAYS_SHORT = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

export function scaleLabel(scale: Scale): string {
  return scale.type === 'binary' ? 'зачёт / незачёт' : `${scale.min}–${scale.max}`
}

export function gradeLabel(grade: Partial<Grade> | null | undefined): string | null {
  if (!grade) return null
  if (grade.score !== null && grade.score !== undefined) return String(grade.score)
  if (grade.passed !== null && grade.passed !== undefined) return grade.passed ? 'зачёт' : 'незачёт'
  return null
}
