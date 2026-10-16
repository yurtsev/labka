import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { StatusBadge } from '@/entities/assignment'
import { UserAvatar } from '@/entities/user'
import type { HomeCourse, HomeDeadline, HomeLesson } from '@/shared/api'
import { colorFor } from '@/shared/lib/color'
import { dayLabel, formatDateTime, hm, isoDay, relativeDeadline } from '@/shared/lib/date'
import { ASSIGNMENT_TYPE, LESSON_TYPE, shortName } from '@/shared/lib/format'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'
import { ArchiveIcon, BookOpenIcon, PlusIcon } from '@/shared/ui/icons'
import { PageHeader } from '@/shared/ui/kit/page-header'
import { EmptyState } from '@/shared/ui/kit/query-state'
import { Skeleton } from '@/shared/ui/skeleton'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/shared/ui/tooltip'

/** Карточка-панель справа: заголовок, список и ссылка внизу, как виджеты Google. */
export function Panel({ title, footer, children }: { title: string; footer?: ReactNode; children: ReactNode }) {
  return (
    <section className="flex flex-col overflow-hidden rounded-2xl border bg-card">
      <h2 className="px-6 pt-6 pb-2 text-base leading-6 font-medium">{title}</h2>
      {children}
      {footer && <div className="flex justify-end border-t px-4 py-2">{footer}</div>}
    </section>
  )
}

const row = 'flex items-start gap-4 px-6 py-3 outline-none transition-colors hover:bg-foreground/4 focus-visible:bg-foreground/8'

export function LessonPanel({ lessons, withGroup }: { lessons: HomeLesson[]; withGroup?: boolean }) {
  return (
    <Panel
      title="Ближайшие занятия"
      footer={
        <Button variant="ghost" asChild>
          <Link to="/calendar">Открыть календарь</Link>
        </Button>
      }
    >
      {lessons.length === 0 ? (
        <p className="px-6 pb-6 text-sm text-muted-foreground">Занятий в ближайшие недели нет.</p>
      ) : (
        <ul className="pb-2">
          {lessons.map((l, i) => (
            <li key={i}>
              <Link to={`/calendar?view=day&date=${l.day}`} className={row}>
                <span className="mt-1 h-10 w-1 shrink-0 rounded-full" style={{ backgroundColor: colorFor(l.course.id) }} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm leading-5 font-medium">{l.course.name}</span>
                  <span className="block truncate text-xs text-muted-foreground">
                    <span className={cn(l.day === isoDay() && 'font-medium text-primary')}>{dayLabel(l.day)}</span>, {hm(l.starts_at)}–{hm(l.ends_at)}
                  </span>
                  <span className="block truncate text-xs text-muted-foreground">
                    {[LESSON_TYPE[l.lesson_type], l.room && `ауд. ${l.room}`, withGroup && l.group.name, l.is_extra && 'разовое'].filter(Boolean).join(' · ')}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}

export function DeadlinePanel({ deadlines }: { deadlines: HomeDeadline[] }) {
  const now = new Date()
  return (
    <Panel
      title="Скоро сдавать"
      footer={
        <Button variant="ghost" asChild>
          <Link to="/calendar?view=schedule">Все сроки</Link>
        </Button>
      }
    >
      {deadlines.length === 0 ? (
        <p className="px-6 pb-6 text-sm text-muted-foreground">Ничего не горит: все работы сданы.</p>
      ) : (
        <ul className="pb-2">
          {deadlines.map((d) => {
            const urgent = new Date(d.deadline_at).getTime() - now.getTime() < 36 * 3600_000
            return (
              <li key={d.assignment_id}>
                <Link to={`/courses/${d.course.id}/assignments/${d.assignment_id}`} className={row}>
                  <span className="grid size-10 shrink-0 place-items-center rounded-full bg-surface-highest text-xs font-medium text-muted-foreground">
                    {ASSIGNMENT_TYPE[d.type].short}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm leading-5 font-medium">{d.title}</span>
                    <span className="block truncate text-xs text-muted-foreground">{d.course.name}</span>
                    <span className="mt-1 flex flex-wrap items-center gap-x-1 gap-y-1 text-xs">
                      <span className={urgent ? 'font-medium text-[#f28b82]' : 'text-muted-foreground'}>
                        {relativeDeadline(d.deadline_at, now)}
                      </span>
                      <span className="text-muted-foreground">· {formatDateTime(d.deadline_at)}</span>
                      {d.status === 'revision' && <StatusBadge status="revision" className="ml-1" />}
                    </span>
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </Panel>
  )
}

type CardAction = { to: string; label: string; icon: ReactNode }

/** Карточка курса, как в Google Classroom: цветная обложка, преподаватель, сводка и быстрые действия. */
export function CourseCard({ course, subtitle, children, actions }: { course: HomeCourse; subtitle: string; children: ReactNode; actions: CardAction[] }) {
  const color = colorFor(course.id)
  return (
    <li className="group relative flex h-64 flex-col overflow-hidden rounded-2xl border bg-card transition-shadow hover:shadow-elevation-2 focus-within:shadow-elevation-2">
      <div className="relative h-24 shrink-0 px-4 pt-4 pr-20" style={{ background: `linear-gradient(135deg, ${color}, color-mix(in srgb, ${color}, black 25%))` }}>
        <Link
          to={`/courses/${course.id}`}
          className="block truncate text-[22px] leading-8 text-white outline-none after:absolute after:inset-0 after:z-0 hover:underline focus-visible:underline"
        >
          {course.name}
        </Link>
        <p className="truncate text-sm text-white/85">{subtitle}</p>
      </div>
      <UserAvatar person={course.teacher} className="absolute top-16 right-4 z-[1] size-16 border-4 border-card text-lg [&_[data-slot=avatar-fallback]]:text-lg" />
      <div className="pointer-events-none relative z-[1] min-w-0 flex-1 px-4 pt-4 pr-24 text-sm">{children}</div>
      <div className="relative z-[1] flex h-14 shrink-0 items-center justify-end gap-1 border-t px-2">
        {actions.map((a) => (
          <Tooltip key={a.to}>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" asChild>
                <Link to={a.to} aria-label={a.label}>
                  {a.icon}
                </Link>
              </Button>
            </TooltipTrigger>
            <TooltipContent>{a.label}</TooltipContent>
          </Tooltip>
        ))}
      </div>
    </li>
  )
}

/** Шапка главной: заголовок и действия — как у остальных страниц. */
export function HomeHeader({ teacher }: { teacher?: boolean }) {
  return (
    <PageHeader
      title="Мои курсы"
      actions={
        <>
          <Button variant="outline" asChild>
            <Link to="/courses/archive">
              <ArchiveIcon data-icon="inline-start" />
              Архив
            </Link>
          </Button>
          {teacher && (
            <Button asChild>
              <Link to="/courses/new">
                <PlusIcon data-icon="inline-start" />
                Создать курс
              </Link>
            </Button>
          )}
        </>
      }
    />
  )
}

/** Сетка карточек курсов или пустое состояние. */
export function CourseGrid({ count, teacher, children }: { count: number; teacher?: boolean; children: ReactNode }) {
  if (count === 0)
    return (
      <EmptyState
        icon={<BookOpenIcon />}
        title={teacher ? 'У вас пока нет курсов' : 'Вас пока не добавили ни в один курс'}
        description={teacher ? 'Создайте курс и добавьте в него группы.' : 'Курсы появятся здесь, когда преподаватель добавит вашу группу.'}
      />
    )
  return <ul className="grid min-w-0 grid-cols-[repeat(auto-fill,minmax(16rem,1fr))] content-start gap-6">{children}</ul>
}

/** Две колонки главной: курсы и сводка справа (320 px), верхние края на одной линии. */
export const homeGrid = 'grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]'

export const teacherName = (c: HomeCourse) => shortName(c.teacher)

export function HomeSkeleton() {
  return (
    <div className={homeGrid}>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(16rem,1fr))] gap-6">
        {Array.from({ length: 3 }, (_, i) => (
          <Skeleton key={i} className="h-64 rounded-2xl" />
        ))}
      </div>
      <div className="flex flex-col gap-6">
        <Skeleton className="h-72 rounded-2xl" />
        <Skeleton className="h-72 rounded-2xl" />
      </div>
    </div>
  )
}
