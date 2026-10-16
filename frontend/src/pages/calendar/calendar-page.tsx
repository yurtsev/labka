import { useQuery } from '@tanstack/react-query'
import { motion, useReducedMotion } from 'motion/react'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router'

import { calendarQuery } from '@/entities/calendar'
import { useIsTeacher } from '@/entities/session'
import { TaskDialog, type TaskDraft } from '@/features/personal-task'
import type { Calendar, CalendarItem, CalendarView } from '@/shared/api'
import { addDays, formatDay, formatMonthShort, formatMonthYear, isoDay } from '@/shared/lib/date'
import { cn } from '@/shared/lib/utils'
import { ArrowDropDownIcon, GridViewIcon, ChevronLeftIcon, ChevronRightIcon, PlusIcon, TodayIcon } from '@/shared/ui/icons'
import { HeaderPortal, useShell } from '@/widgets/app-shell'
import { Button } from '@/shared/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuShortcut,
  DropdownMenuTrigger,
} from '@/shared/ui/dropdown-menu'
import { ErrorState } from '@/shared/ui/kit/query-state'
import { Skeleton } from '@/shared/ui/skeleton'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/shared/ui/tooltip'

import { EventDialog } from './event-dialog'
import { VIEWS, useHiddenKinds, type Handlers, type Kind, type View } from './model'
import { MonthGrid } from './month-grid'
import { ScheduleList } from './schedule-list'
import { SidePanel } from './side-panel'
import { TimeGrid } from './time-grid'

const API_VIEW: Record<View, CalendarView> = { day: 'day', week: 'week', month: 'month', schedule: 'month' }

/** Заголовок периода, как в шапке Google Календаря. */
function periodTitle(view: View, date: string, cal?: Calendar) {
  if (view === 'day') return `${formatDay(date)} ${date.slice(0, 4)} г.`
  if (view !== 'week' || !cal) return formatMonthYear(date)
  const { starts_on: a, ends_on: b } = cal.period
  if (a.slice(0, 7) === b.slice(0, 7)) return formatMonthYear(a)
  const m = (d: string) => formatMonthShort(d).replace('.', '')
  const mm = `${m(a)[0].toUpperCase()}${m(a).slice(1)} – ${m(b)}`
  return a.slice(0, 4) === b.slice(0, 4) ? `${mm} ${b.slice(0, 4)}` : `${mm} ${a.slice(0, 4)}–${b.slice(0, 4)}`
}

function weekNote(cal?: Calendar) {
  const w = cal?.weeks[0]
  if (!cal || cal.period.view === 'month') return null
  if (!w?.number) return 'Вне семестра'
  return `${w.number}-я неделя, ${w.is_even ? 'чётная' : 'нечётная'}`
}

function isTyping(e: KeyboardEvent) {
  const t = e.target as HTMLElement
  return t.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName) || document.querySelector('[role=dialog]')
}

export function CalendarPage() {
  const [params, setParams] = useSearchParams()
  const raw = params.get('view')
  // На телефоне, как у Google, по умолчанию — день: семь колонок не помещаются.
  const view: View = VIEWS.some((v) => v.id === raw) ? (raw as View) : window.innerWidth < 768 ? 'day' : 'week'
  const date = params.get('date') ?? isoDay()
  const query = useQuery(calendarQuery(API_VIEW[view], date))
  const cal = query.data
  const isTeacher = useIsTeacher()
  const reduce = useReducedMotion()
  const { panel } = useShell()
  const [hidden, toggleKind] = useHiddenKinds()
  const [task, setTask] = useState<TaskDraft | null>(null)
  const [event, setEvent] = useState<CalendarItem | null>(null)

  const go = (next: Partial<{ view: View; date: string }>) => setParams({ view: next.view ?? view, date: next.date ?? date })
  const shift = (dir: 1 | -1) => cal && go({ date: dir === 1 ? cal.period.next : cal.period.prev })
  const kinds: Kind[] = isTeacher ? ['lesson', 'exam', 'deadline'] : ['lesson', 'exam', 'deadline', 'task']
  const items = cal?.items.filter((i) => !hidden.has(i.kind)) ?? []
  const createTask = isTeacher ? undefined : (day: string, time?: string) => setTask({ title: '', due_date: day, due_time: time ?? null })

  const h: Handlers = {
    withGroup: isTeacher,
    create: createTask,
    toDay: (d) => go({ view: 'day', date: d }),
    open: setEvent,
  }

  // Горячие клавиши Google Календаря: T, D/W/M/A, J/N и K/P, C.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || isTyping(e)) return
      const k = e.key.toLowerCase()
      const byKey: Record<string, () => void> = {
        t: () => go({ date: isoDay() }),
        d: () => go({ view: 'day' }),
        w: () => go({ view: 'week' }),
        m: () => go({ view: 'month' }),
        a: () => go({ view: 'schedule' }),
        j: () => shift(1),
        n: () => shift(1),
        k: () => shift(-1),
        p: () => shift(-1),
        c: () => createTask?.(date),
      }
      if (byKey[k]) {
        e.preventDefault()
        byKey[k]()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  const days = cal ? Array.from({ length: view === 'day' ? 1 : 7 }, (_, i) => addDays(cal.period.starts_on, i)) : []
  const current = VIEWS.find((v) => v.id === view)!
  const note = weekNote(cal)

  return (
    <div className="flex min-h-0 flex-1">
      <HeaderPortal>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="outline" className="hidden border-outline px-5 text-foreground sm:inline-flex" onClick={() => go({ date: isoDay() })}>
              Сегодня
            </Button>
          </TooltipTrigger>
          <TooltipContent>{formatDay(isoDay())} (T)</TooltipContent>
        </Tooltip>
        <Button variant="ghost" size="icon" className="sm:hidden" aria-label="Сегодня" onClick={() => go({ date: isoDay() })}>
          <TodayIcon />
        </Button>
        <div className="flex">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Назад" disabled={!cal} onClick={() => shift(-1)}>
                <ChevronLeftIcon />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Назад (K)</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Вперёд" disabled={!cal} onClick={() => shift(1)}>
                <ChevronRightIcon />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Вперёд (J)</TooltipContent>
          </Tooltip>
        </div>
        <h1 className="min-w-0 truncate text-base sm:text-[22px]">
          <span className="max-sm:hidden">{periodTitle(view, date, cal)}</span>
          <span className="sm:hidden">{view === 'day' ? `${Number(date.slice(8))} ${formatMonthShort(date)}` : periodTitle(view, date, cal).replace(/ \d{4}.*$/, '')}</span>
        </h1>
        {note && <span className="hidden shrink-0 text-sm text-muted-foreground xl:inline">{note}</span>}
        <div className="flex-1" />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="border-outline px-2.5 text-foreground sm:pr-2.5 sm:pl-5" aria-label={`Вид: ${current.label}`}>
              <GridViewIcon className="sm:hidden" />
              <span className="max-sm:hidden">{current.label}</span>
              <ArrowDropDownIcon className="max-sm:hidden" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52">
            <DropdownMenuRadioGroup value={view} onValueChange={(v) => go({ view: v as View })}>
              {VIEWS.map((v) => (
                <DropdownMenuRadioItem key={v.id} value={v.id} className="pr-4 pl-4 [&>[data-slot=dropdown-menu-radio-item-indicator]]:hidden data-[state=checked]:bg-primary/12">
                  {v.label}
                  <DropdownMenuShortcut>{v.key}</DropdownMenuShortcut>
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </HeaderPortal>

      {panel.calendar && (
        <SidePanel
          date={date}
          range={[date, date]}
          kinds={kinds}
          hidden={hidden}
          onToggle={toggleKind}
          onPick={(d) => go({ date: d })}
          onCreate={createTask && (() => createTask(date))}
          statuses={!isTeacher}
        />
      )}

      <section
        aria-label="Календарь"
        className={cn('flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-background md:mr-2 md:mb-2 md:rounded-3xl md:border', query.isPlaceholderData && 'opacity-70')}
      >
        {query.isError ? (
          <div className="m-auto">
            <ErrorState error={query.error} onRetry={() => query.refetch()} />
          </div>
        ) : !cal ? (
          <Skeleton className="m-4 flex-1 rounded-2xl" />
        ) : (
          <motion.div
            key={`${view}-${cal.period.starts_on}`}
            initial={reduce ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.15 }}
            className="flex min-h-0 flex-1 flex-col"
          >
            {view === 'month' ? (
              <MonthGrid cal={{ ...cal, items }} month={date} h={h} />
            ) : view === 'schedule' ? (
              <ScheduleList cal={{ ...cal, items }} month={date} h={h} />
            ) : (
              <TimeGrid days={days} items={items} h={h} />
            )}
          </motion.div>
        )}
      </section>

      {createTask && (
        <Button
          size="icon-lg"
          className="fixed right-4 bottom-4 z-30 size-14 rounded-2xl bg-primary-container text-on-primary-container shadow-elevation-3 lg:hidden"
          aria-label="Создать задачу"
          onClick={() => createTask(date)}
        >
          <PlusIcon className="size-6" />
        </Button>
      )}

      <TaskDialog task={task} onClose={() => setTask(null)} />
      <EventDialog
        item={event}
        withGroup={isTeacher}
        onClose={() => setEvent(null)}
        onEditTask={(i) => {
          setEvent(null)
          setTask({ id: i.task!.id, title: i.task!.title, due_date: i.day, due_time: i.starts_at, is_done: i.task!.is_done })
        }}
      />
    </div>
  )
}
