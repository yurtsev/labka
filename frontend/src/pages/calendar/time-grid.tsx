import { useEffect, useLayoutEffect, useRef, useState } from 'react'

import { DeadlineChip, eventMeta, eventTime, eventTitle, KIND_BG } from '@/entities/calendar'
import type { CalendarItem } from '@/shared/api'
import { formatDayLong, formatWeekday, fromMinutes, hm, isoDay, minutesOf } from '@/shared/lib/date'
import { cn } from '@/shared/lib/utils'
import { TaskAltIcon } from '@/shared/ui/icons'

import { groupByDay, HOUR, layoutDay, type Handlers } from './model'

const HOURS = Array.from({ length: 24 }, (_, h) => h)

function useNowMinutes() {
  const [now, setNow] = useState(() => minutesOf())
  useEffect(() => {
    const t = setInterval(() => setNow(minutesOf()), 60_000)
    return () => clearInterval(t)
  }, [])
  return now
}

/** Шапка колонки: день недели и число, сегодня — в синем круге. */
function DayHead({ day, h, big }: { day: string; h: Handlers; big?: boolean }) {
  const today = day === isoDay()
  return (
    <div className="flex flex-col items-center gap-1 pt-2 pb-1">
      <span className={cn('text-[11px] font-medium tracking-wide uppercase', today ? 'text-primary' : 'text-muted-foreground')}>{formatWeekday(day)}</span>
      <button
        type="button"
        onClick={() => h.toDay(day)}
        aria-label={`${formatDayLong(day)}: открыть день`}
        className={cn(
          'grid place-items-center rounded-full leading-none tabular-nums outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring',
          big ? 'size-12 text-[26px]' : 'size-11 text-[24px]',
          today ? 'bg-primary text-primary-foreground hover:bg-primary/90' : 'text-foreground hover:bg-foreground/8',
        )}
      >
        {Number(day.slice(8))}
      </button>
    </div>
  )
}

function AllDayChip({ item, h }: { item: CalendarItem; h: Handlers }) {
  const done = item.task?.is_done
  return (
    <button
      type="button"
      onClick={() => h.open(item)}
      className={cn(
        'h-[22px] w-full shrink-0 truncate rounded-full px-2 text-left text-xs font-medium text-on-event outline-none hover:brightness-110 focus-visible:ring-2 focus-visible:ring-ring',
        KIND_BG[item.kind],
        done && 'line-through opacity-60',
      )}
    >
      {item.task && <TaskAltIcon className="mr-1 inline size-3.5 align-[-3px]" />}
      {item.starts_at && <span className="mr-1 font-normal tabular-nums">{hm(item.starts_at)}</span>}
      {eventTitle(item)}
    </button>
  )
}

/** Сетка времени на один или семь дней. */
export function TimeGrid({ days, items, h }: { days: string[]; items: CalendarItem[]; h: Handlers }) {
  const byDay = groupByDay(items)
  const scroller = useRef<HTMLDivElement>(null)
  const now = useNowMinutes()
  const today = isoDay()
  // Над шкалой — дедлайны и личные задачи (это моменты, а не интервалы): так их не теснят занятия.
  // Сначала без времени, затем по времени.
  const allDay = days.map((d) =>
    (byDay.get(d) ?? []).filter((i) => !i.starts_at || i.deadline || i.task).sort((a, b) => (a.starts_at ?? '').localeCompare(b.starts_at ?? '')),
  )
  const hasAllDay = allDay.some((l) => l.length > 0)
  const cols = { gridTemplateColumns: `56px repeat(${days.length}, minmax(0, 1fr))` }

  // Как Google: при открытии прокручиваем к рабочему дню или к текущему времени.
  useLayoutEffect(() => {
    const el = scroller.current
    if (!el) return
    const target = days.includes(today) && now >= 9 * 60 ? now - 120 : 7 * 60
    el.scrollTop = (target / 60) * HOUR
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days.length, days[0]])

  const createAt = (day: string, e: React.MouseEvent<HTMLDivElement>) => {
    if (!h.create || e.target !== e.currentTarget) return
    const y = e.clientY - e.currentTarget.getBoundingClientRect().top
    const minutes = Math.min(Math.floor((y / HOUR) * 2) * 30, 23 * 60 + 30)
    h.create(day, fromMinutes(minutes))
  }

  return (
    <div ref={scroller} className="min-h-0 flex-1 overflow-y-auto">
      <div className="sticky top-0 z-30 grid border-b bg-background" style={cols}>
        <div className="flex items-end justify-end pr-2 pb-1 text-[10px] text-muted-foreground">GMT+03</div>
        {days.map((d, i) => (
          <div key={d} className="border-l border-transparent">
            <DayHead day={d} h={h} big={days.length === 1} />
            {hasAllDay && (
              <div className={cn('flex min-h-6 flex-col gap-0.5 border-l px-0.5 pb-1', i === 0 && 'border-l-border')}>
                {allDay[i].map((item, k) =>
                  item.deadline ? (
                    <DeadlineChip key={k} item={item} withLabel={days.length === 1} onClick={() => h.open(item)} />
                  ) : (
                    <AllDayChip key={k} item={item} h={h} />
                  ),
                )}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="relative grid" style={{ ...cols, height: HOUR * 24 }}>
          <div className="relative">
            {HOURS.slice(1).map((hr) => (
              <span key={hr} className="absolute right-2 -translate-y-1/2 text-[11px] text-muted-foreground tabular-nums" style={{ top: hr * HOUR }}>
                {String(hr).padStart(2, '0')}:00
              </span>
            ))}
          </div>
          {days.map((d) => {
            const placed = layoutDay(byDay.get(d) ?? [])
            return (
              <div
                key={d}
                role="presentation"
                className={cn('relative border-l', h.create && 'cursor-cell')}
                style={{ backgroundImage: `repeating-linear-gradient(to bottom, transparent 0, transparent ${HOUR - 1}px, var(--border) ${HOUR - 1}px, var(--border) ${HOUR}px)` }}
                onClick={(e) => createAt(d, e)}
              >
                {placed.map(({ item, start, end, left, width, point }, k) => {
                  const height = ((end - start) / 60) * HOUR
                  const short = height < 40
                  const done = item.task?.is_done
                  const meta = eventMeta(item, { withGroup: h.withGroup })
                  return (
                    <button
                      key={k}
                      type="button"
                      title={`${eventTitle(item)}, ${eventTime(item)}`}
                      onClick={() => h.open(item)}
                      className={cn(
                        'absolute overflow-hidden rounded-[4px] border border-background px-1.5 text-left text-xs leading-4 text-on-event outline-none hover:z-10 hover:shadow-elevation-2 focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-ring',
                        KIND_BG[item.kind],
                        point ? 'rounded-full px-2 py-[3px]' : short ? 'py-0' : 'py-1',
                        done && 'opacity-60',
                      )}
                      style={{
                        top: (start / 60) * HOUR,
                        height: Math.max(height, 18),
                        left: `calc(${left * 100}% + 1px)`,
                        width: `calc(${width * 100}% - ${left + width > 0.99 ? 10 : 2}px)`,
                        zIndex: point ? 2 : 1,
                      }}
                    >
                      {point ? (
                        <span className="flex items-center gap-1">
                          <TaskAltIcon className="size-3.5 shrink-0" />
                          <span className={cn('truncate font-medium', done && 'line-through')}>{eventTitle(item)}</span>
                        </span>
                      ) : short ? (
                        <span className={cn('block truncate', done && 'line-through')}>
                          <span className="font-medium">{eventTitle(item)}</span>, {eventTime(item)}
                        </span>
                      ) : (
                        <>
                          <span className={cn('block font-medium', height < 64 ? 'truncate' : 'line-clamp-2', done && 'line-through')}>{eventTitle(item)}</span>
                          <span className="block truncate">{eventTime(item)}</span>
                          {meta && height >= 64 && <span className="block truncate">{meta}</span>}
                        </>
                      )}
                    </button>
                  )
                })}
                {d === today && (
                  <div className="pointer-events-none absolute inset-x-0 z-20 h-0.5 bg-now" style={{ top: (now / 60) * HOUR }}>
                    <span className="absolute -top-[5px] -left-[6px] size-3 rounded-full bg-now" />
                  </div>
                )}
              </div>
            )
          })}
      </div>
    </div>
  )
}
