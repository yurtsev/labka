import { DEADLINE_STATE, deadlineState, eventMeta, eventTime, eventTitle, KIND_BG } from '@/entities/calendar'
import type { CalendarItem } from '@/shared/api'
import type { Calendar } from '@/shared/api'

import { formatMonthShort, formatWeekday, isoDay } from '@/shared/lib/date'
import { cn } from '@/shared/lib/utils'
import { CalendarDaysIcon } from '@/shared/ui/icons'
import { EmptyState } from '@/shared/ui/kit/query-state'

import { groupByDay, type Handlers } from './model'

/** Статус дедлайна маленькой плашкой: иконка и глагол. */
export function DeadlineStatus({ item }: { item: CalendarItem }) {
  const st = DEADLINE_STATE[deadlineState(item)]
  const StIcon = st.icon
  return (
    <span className={cn('inline-flex h-6 shrink-0 items-center gap-1 rounded-full px-2 text-xs font-medium', st.chip)}>
      <StIcon className="size-3.5" />
      {st.label}
    </span>
  )
}

/** Вид «Расписание»: события месяца списком по дням, как в Google Календаре. */
export function ScheduleList({ cal, month, h }: { cal: Calendar; month: string; h: Handlers }) {
  const today = isoDay()
  // Как в Google: список начинается с выбранного дня и идёт до конца месяца.
  const days = [...groupByDay(cal.items.filter((i) => i.day.slice(0, 7) === month.slice(0, 7) && i.day >= month)).entries()].sort(([a], [b]) => a.localeCompare(b))
  if (days.length === 0)
    return (
      <div className="flex flex-1 items-center justify-center">
        <EmptyState icon={<CalendarDaysIcon />} title="До конца месяца событий нет" description="Перейдите к другому месяцу стрелками в шапке." />
      </div>
    )
  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-2 py-2 sm:px-4">
      <ul className="flex flex-col">
        {days.map(([day, items]) => (
          <li key={day} className="flex gap-2 border-b py-2 last:border-b-0">
            <button
              type="button"
              onClick={() => h.toDay(day)}
              className="flex w-24 shrink-0 items-start gap-2 self-start rounded-full py-1 pr-2 pl-1 text-left outline-none hover:bg-foreground/8 focus-visible:ring-2 focus-visible:ring-ring sm:w-32"
            >
              <span
                className={cn(
                  'grid size-8 shrink-0 place-items-center rounded-full text-[22px] leading-none tabular-nums',
                  day === today && 'bg-primary text-primary-foreground',
                )}
              >
                {Number(day.slice(8))}
              </span>
              <span className={cn('pt-1.5 text-[11px] font-medium uppercase', day === today ? 'text-primary' : 'text-muted-foreground')}>
                {formatMonthShort(day)}, {formatWeekday(day)}
              </span>
            </button>
            <ul className="flex min-w-0 flex-1 flex-col">
              {items.map((item, k) => {
                const meta = eventMeta(item, { withGroup: h.withGroup })
                return (
                  <li key={k}>
                    <button
                      type="button"
                      onClick={() => h.open(item)}
                      className="flex w-full items-start gap-4 rounded-full px-3 py-2 text-left text-sm outline-none hover:bg-foreground/8 focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <span className={cn('mt-1.5 size-3 shrink-0 rounded-full', item.deadline ? DEADLINE_STATE[deadlineState(item)].dot : KIND_BG[item.kind])} />
                      <span className="w-28 shrink-0 text-muted-foreground tabular-nums sm:w-36">{eventTime(item) || 'Весь день'}</span>
                      <span className="min-w-0 flex-1">
                        <span className="flex min-w-0 items-center gap-2">
                          <span className={cn('truncate font-medium', item.task?.is_done && 'text-muted-foreground line-through')}>{eventTitle(item)}</span>
                          {item.deadline && <DeadlineStatus item={item} />}
                        </span>
                        {meta && <span className="block truncate text-muted-foreground">{meta}</span>}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </li>
        ))}
      </ul>
    </div>
  )
}
