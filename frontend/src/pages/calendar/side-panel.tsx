import { useState } from 'react'

import { DEADLINE_STATE, KIND_BG, KIND_LABEL, type DeadlineState } from '@/entities/calendar'
import { addDays, formatDayLong, formatMonthYear, formatWeekday, isoDay, startOfMonth, startOfWeek } from '@/shared/lib/date'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'
import { CheckIcon, ChevronLeftIcon, ChevronRightIcon, PlusIcon } from '@/shared/ui/icons'

import type { Kind } from './model'

/** Мини-календарь месяца, как в левой панели Google Календаря. */
function MiniMonth({ date, range, onPick }: { date: string; range: [string, string]; onPick: (day: string) => void }) {
  const [month, setMonth] = useState(startOfMonth(date))
  const [synced, setSynced] = useState(date)
  if (synced !== date) {
    setSynced(date)
    setMonth(startOfMonth(date))
  }
  const today = isoDay()
  const first = startOfWeek(month)
  const days = Array.from({ length: 42 }, (_, i) => addDays(first, i))
  return (
    <div className="px-2">
      <div className="flex items-center justify-between pl-2">
        <span className="text-sm font-medium">{formatMonthYear(month)}</span>
        <div className="flex">
          <Button variant="ghost" size="icon-sm" aria-label="Предыдущий месяц" onClick={() => setMonth(startOfMonth(addDays(month, -1)))}>
            <ChevronLeftIcon />
          </Button>
          <Button variant="ghost" size="icon-sm" aria-label="Следующий месяц" onClick={() => setMonth(startOfMonth(addDays(month, 32)))}>
            <ChevronRightIcon />
          </Button>
        </div>
      </div>
      <div className="grid grid-cols-7 text-center text-[11px]">
        {days.slice(0, 7).map((d) => (
          <span key={d} className="py-1 font-medium text-muted-foreground">
            {formatWeekday(d)[0].toUpperCase()}
          </span>
        ))}
        {days.map((d) => {
          const inRange = d >= range[0] && d <= range[1]
          return (
            <button
              key={d}
              type="button"
              onClick={() => onPick(d)}
              aria-label={formatDayLong(d)}
              className={cn(
                'mx-auto grid size-7 place-items-center rounded-full tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-ring',
                d.slice(0, 7) !== month.slice(0, 7) && 'text-muted-foreground/70',
                d === today ? 'bg-primary font-medium text-primary-foreground' : inRange ? 'bg-nav-active text-on-nav-active' : 'hover:bg-foreground/8',
              )}
            >
              {Number(d.slice(8))}
            </button>
          )
        })}
      </div>
    </div>
  )
}

type Props = {
  date: string
  range: [string, string]
  kinds: Kind[]
  hidden: Set<Kind>
  onToggle: (k: Kind) => void
  onPick: (day: string) => void
  onCreate?: () => void
  /** Показать подсказку по статусам дедлайнов (у студента). */
  statuses?: boolean
}

/** Левая панель календаря: «Создать», мини-календарь и «Мои календари». */
export function SidePanel({ date, range, kinds, hidden, onToggle, onPick, onCreate, statuses }: Props) {
  return (
    <aside className="hidden w-64 shrink-0 flex-col gap-4 overflow-y-auto pt-2 pb-4 lg:flex" aria-label="Панель календаря">
      {onCreate && (
        <button
          type="button"
          onClick={onCreate}
          className="ml-2 flex h-14 w-fit items-center gap-3 rounded-2xl bg-surface-high pr-6 pl-4 text-sm font-medium shadow-elevation-1 outline-none transition-shadow hover:bg-surface-highest hover:shadow-elevation-2 focus-visible:ring-2 focus-visible:ring-ring"
        >
          <PlusIcon className="size-6 text-primary" />
          Создать
        </button>
      )}
      <MiniMonth date={date} range={range} onPick={onPick} />
      <section className="px-2">
        <h2 className="px-2 py-2 text-sm font-medium">Мои календари</h2>
        <ul>
          {kinds.map((k) => {
            const on = !hidden.has(k)
            return (
              <li key={k}>
                <button
                  type="button"
                  role="checkbox"
                  aria-checked={on}
                  onClick={() => onToggle(k)}
                  className="flex h-9 w-full items-center gap-3 rounded-full px-3 text-sm outline-none hover:bg-foreground/8 focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className={cn('grid size-[18px] place-items-center rounded-[3px] border-2', on ? cn(KIND_BG[k], 'border-transparent text-on-event') : 'border-current text-muted-foreground')}>
                    {on && <CheckIcon className="size-4" />}
                  </span>
                  {KIND_LABEL[k]}
                </button>
              </li>
            )
          })}
        </ul>
      </section>
      {statuses && (
        <section className="px-2">
          <h2 className="px-2 py-2 text-sm font-medium">Дедлайны</h2>
          <ul className="flex flex-col gap-1.5 px-3">
            {(['todo', 'revision', 'overdue', 'review', 'accepted'] as DeadlineState[]).map((k) => {
              const st = DEADLINE_STATE[k]
              const StIcon = st.icon
              return (
                <li key={k} className="flex items-center gap-3 text-sm">
                  <span className={cn('grid size-[22px] place-items-center rounded-full', st.chip)}>
                    <StIcon className="size-3.5" />
                  </span>
                  {st.label}
                </li>
              )
            })}
          </ul>
        </section>
      )}
    </aside>
  )
}
