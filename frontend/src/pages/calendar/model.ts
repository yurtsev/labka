import { useState } from 'react'

import type { CalendarItem } from '@/shared/api'
import { minutesOf } from '@/shared/lib/date'

export type View = 'day' | 'week' | 'month' | 'schedule'
export type Kind = CalendarItem['kind']

export const VIEWS: { id: View; label: string; key: string }[] = [
  { id: 'day', label: 'День', key: 'D' },
  { id: 'week', label: 'Неделя', key: 'W' },
  { id: 'month', label: 'Месяц', key: 'M' },
  { id: 'schedule', label: 'Расписание', key: 'A' },
]

export const HOUR = 48
/** Высота метки дедлайна или задачи со временем, в минутах сетки (≈ 22 px). */
const POINT = 28

export type Handlers = {
  open: (item: CalendarItem) => void
  /** Есть только у студента: клик по пустому месту создаёт личную задачу. */
  create?: (day: string, time?: string) => void
  toDay: (day: string) => void
  withGroup: boolean
}

export type Placed = { item: CalendarItem; start: number; end: number; left: number; width: number; point: boolean }

/** Доля колонки под занятие, когда рядом стоят метки дедлайнов и задач. */
const SPLIT = 0.5

const overlaps = (a: { start: number; end: number }, b: { start: number; end: number }) => a.start < b.end && b.start < a.end

/**
 * Раскладка дня. Занятия и экзамены — блоки на свой интервал; пересекающиеся стоят рядом.
 * Задачи со временем — короткие метки: друг под другом и никогда поверх занятий:
 * если метка попадает на занятие, занятие сужается влево, а метка встаёт справа.
 */
export function layoutDay(items: CalendarItem[]): Placed[] {
  // Дедлайны и задачи — моменты, а не интервалы: они в строке над шкалой, здесь их нет.
  const timed = items.filter((i) => i.starts_at && !i.deadline && !i.task)
  const blocks = timed
    .filter((i) => i.ends_at && !i.deadline && !i.task)
    .map((item) => {
      const start = minutesOf(item.starts_at!)
      return { item, start, end: Math.max(minutesOf(item.ends_at!), start + 15), left: 0, width: 1, point: false }
    })
    .sort((a, b) => a.start - b.start || b.end - a.end)

  // Пересекающиеся блоки — по колонкам, как в Google Календаре.
  let cluster: Placed[] = []
  let columns: number[] = []
  let clusterEnd = -1
  const flush = () => {
    cluster.forEach((p) => {
      p.width = 1 / columns.length
      p.left *= p.width
    })
    cluster = []
    columns = []
  }
  for (const p of blocks) {
    if (p.start >= clusterEnd) flush()
    let col = columns.findIndex((end) => end <= p.start)
    if (col === -1) col = columns.push(0) - 1
    columns[col] = p.end
    p.left = col
    cluster.push(p)
    clusterEnd = Math.max(clusterEnd, p.end)
  }
  flush()

  // Метки: по времени, наезжающие сдвигаются вниз стопкой.
  const points: Placed[] = []
  for (const item of timed.filter((i) => !blocks.some((b) => b.item === i)).sort((a, b) => a.starts_at!.localeCompare(b.starts_at!))) {
    let start = Math.min(minutesOf(item.starts_at!), 24 * 60 - POINT)
    const prev = points.at(-1)
    if (prev && start < prev.end) start = prev.end
    points.push({ item, start, end: start + POINT, left: 0, width: 1, point: true })
  }
  for (const p of points) {
    if (!blocks.some((b) => overlaps(b, p))) continue
    p.left = SPLIT
    p.width = 1 - SPLIT
  }
  for (const b of blocks) {
    if (!points.some((p) => overlaps(b, p))) continue
    b.left *= SPLIT
    b.width *= SPLIT
  }
  return [...blocks, ...points]
}

export function groupByDay(items: CalendarItem[]) {
  const m = new Map<string, CalendarItem[]>()
  for (const i of items) m.set(i.day, [...(m.get(i.day) ?? []), i])
  for (const list of m.values()) list.sort((a, b) => (a.starts_at ?? '').localeCompare(b.starts_at ?? ''))
  return m
}

const STORAGE = 'labka:calendar-hidden'

/** Какие календари скрыты в «Моих календарях»; выбор запоминается в браузере. */
export function useHiddenKinds() {
  const [hidden, setHidden] = useState<Set<Kind>>(() => {
    try {
      return new Set(JSON.parse(localStorage.getItem(STORAGE) ?? '[]'))
    } catch {
      return new Set()
    }
  })
  const toggle = (k: Kind) =>
    setHidden((prev) => {
      const next = new Set(prev)
      if (next.has(k)) next.delete(k)
      else next.add(k)
      try {
        localStorage.setItem(STORAGE, JSON.stringify([...next]))
      } catch {
        /* не запомнили — ничего страшного */
      }
      return next
    })
  return [hidden, toggle] as const
}
