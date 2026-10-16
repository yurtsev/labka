import { useEffect, useRef, useState } from 'react'

import { DeadlineChip, eventTitle, KIND_BG } from '@/entities/calendar'
import type { Calendar, CalendarItem } from '@/shared/api'
import { addDays, formatDayLong, formatMonthShort, formatWeekday, hm, isoDay } from '@/shared/lib/date'
import { cn } from '@/shared/lib/utils'
import { Popover, PopoverContent, PopoverTrigger } from '@/shared/ui/popover'

import { groupByDay, type Handlers } from './model'

const CHIP = 22

/** Строка события в месяце: со временем — точка и время, без времени — цветная плашка. */
export function MonthChip({ item, h }: { item: CalendarItem; h: Handlers }) {
  if (item.deadline) return <DeadlineChip item={item} className="h-5" onClick={() => h.open(item)} />
  const done = item.task?.is_done
  const timed = Boolean(item.starts_at)
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation()
        h.open(item)
      }}
      className={cn(
        'flex h-5 w-full min-w-0 shrink-0 items-center gap-1.5 rounded-[4px] px-1.5 text-left text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring',
        timed ? 'hover:bg-foreground/8' : cn(KIND_BG[item.kind], 'font-medium text-on-event hover:brightness-110'),
        done && 'opacity-60',
      )}
    >
      {timed && <span className={cn('size-2 shrink-0 rounded-full', KIND_BG[item.kind])} />}
      {timed && <span className="shrink-0 text-muted-foreground tabular-nums">{hm(item.starts_at!)}</span>}
      <span className={cn('truncate', timed && 'font-medium', done && 'line-through')}>{eventTitle(item)}</span>
    </button>
  )
}

/** Сколько строк событий помещается в ячейке: считаем по высоте строки сетки. */
function useCapacity(rows: number) {
  const ref = useRef<HTMLDivElement>(null)
  const [cap, setCap] = useState(3)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver(() => setCap(Math.max(1, Math.floor((el.clientHeight / rows - 30) / CHIP))))
    ro.observe(el)
    return () => ro.disconnect()
  }, [rows])
  return [ref, cap] as const
}

export function MonthGrid({ cal, month, h }: { cal: Calendar; month: string; h: Handlers }) {
  const byDay = groupByDay(cal.items)
  const today = isoDay()
  const days: string[] = []
  for (let d = cal.period.starts_on; d <= cal.period.ends_on; d = addDays(d, 1)) days.push(d)
  const rows = days.length / 7
  const [ref, cap] = useCapacity(rows)

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="grid shrink-0 grid-cols-7">
        {days.slice(0, 7).map((d) => (
          <div key={d} className="border-l pt-2 text-center text-[11px] font-medium tracking-wide text-muted-foreground uppercase first:border-l-0">
            {formatWeekday(d)}
          </div>
        ))}
      </div>
      <div ref={ref} className="grid min-h-0 flex-1 grid-cols-7" style={{ gridTemplateRows: `repeat(${rows}, minmax(0, 1fr))` }}>
        {days.map((d, i) => {
          const items = byDay.get(d) ?? []
          const outside = d.slice(0, 7) !== month.slice(0, 7)
          const fits = items.length <= cap ? items.length : cap - 1
          const label = d.endsWith('-01') ? `${Number(d.slice(8))} ${formatMonthShort(d)}` : String(Number(d.slice(8)))
          return (
            <div
              key={d}
              role="presentation"
              onClick={() => h.create?.(d)}
              className={cn('flex min-h-0 flex-col gap-px overflow-hidden border-b border-l px-1 pb-1', i % 7 === 0 && 'border-l-0', h.create && 'cursor-cell')}
            >
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  h.toDay(d)
                }}
                aria-label={`${formatDayLong(d)}: открыть день`}
                className={cn(
                  'mx-auto my-1 grid h-6 min-w-6 shrink-0 place-items-center rounded-full px-1.5 text-xs font-medium tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  d === today ? 'bg-primary text-primary-foreground' : outside ? 'text-muted-foreground/70 hover:bg-foreground/8' : 'hover:bg-foreground/8',
                )}
              >
                {label}
              </button>
              {items.slice(0, fits).map((item, k) => (
                <MonthChip key={k} item={item} h={h} />
              ))}
              {items.length > fits && (
                <Popover>
                  <PopoverTrigger asChild>
                    <button
                      type="button"
                      onClick={(e) => e.stopPropagation()}
                      className="h-5 shrink-0 rounded-[4px] px-1.5 text-left text-xs font-medium hover:bg-foreground/8 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                    >
                      Ещё {items.length - fits}
                    </button>
                  </PopoverTrigger>
                  <PopoverContent className="w-64 gap-1 rounded-2xl p-3" onClick={(e) => e.stopPropagation()}>
                    <p className="text-center text-[11px] font-medium text-muted-foreground uppercase">{formatWeekday(d)}</p>
                    <p className="mb-2 text-center text-[26px] leading-none">{Number(d.slice(8))}</p>
                    {items.map((item, k) => (
                      <MonthChip key={k} item={item} h={h} />
                    ))}
                  </PopoverContent>
                </Popover>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
