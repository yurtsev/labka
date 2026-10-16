import type { CalendarItem } from '@/shared/api'
import { hm } from '@/shared/lib/date'
import { ASSIGNMENT_TYPE, EXAM_TYPE, LESSON_TYPE } from '@/shared/lib/format'

export const KIND_LABEL: Record<CalendarItem['kind'], string> = {
  lesson: 'Занятия',
  deadline: 'Дедлайны',
  task: 'Личные задачи',
  exam: 'Зачёты и экзамены',
}

/** Цвет вида события: заливка, текст и точка. */
export const KIND_BG: Record<CalendarItem['kind'], string> = {
  lesson: 'bg-lesson',
  deadline: 'bg-deadline',
  task: 'bg-task',
  exam: 'bg-exam',
}

export const KIND_COLOR: Record<CalendarItem['kind'], string> = {
  lesson: 'text-lesson',
  deadline: 'text-deadline',
  task: 'text-task',
  exam: 'text-exam',
}

/** Заголовок события в сетке: у занятия — курс, у дедлайна — задание, у задачи — её текст. */
export function eventTitle(item: CalendarItem): string {
  if (item.lesson) return item.lesson.course.name
  if (item.exam) return `${EXAM_TYPE[item.exam.exam_type]}: ${item.exam.course.name}`
  if (item.deadline) return `${ASSIGNMENT_TYPE[item.deadline.type].short} «${item.deadline.title}»`
  return item.task!.title
}

/** «11:15–12:45» или «до 18:00»; пусто — событие на весь день. */
export function eventTime(item: CalendarItem): string {
  if (!item.starts_at) return ''
  if (item.deadline) return `до ${hm(item.starts_at)}`
  return hm(item.starts_at) + (item.ends_at ? `–${hm(item.ends_at)}` : '')
}

/** Вторая строка: вид занятия, аудитория, группа или курс дедлайна. */
export function eventMeta(item: CalendarItem, { withGroup = false } = {}): string {
  if (item.lesson) {
    const l = item.lesson
    return [LESSON_TYPE[l.lesson_type], l.room && `ауд. ${l.room}`, withGroup && l.group.name].filter(Boolean).join(', ')
  }
  if (item.exam) return [item.exam.room && `ауд. ${item.exam.room}`, withGroup && item.exam.group.name].filter(Boolean).join(', ')
  if (item.deadline) return item.deadline.course.name
  return ''
}
