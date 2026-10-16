import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { NavLink, useMatch } from 'react-router'

import { coursesQuery } from '@/entities/course'
import { queueQuery } from '@/entities/review'
import { useIsTeacher } from '@/entities/session'
import { colorFor } from '@/shared/lib/color'
import { cn } from '@/shared/lib/utils'
import {
  ArchiveIcon,
  CalendarDaysIcon,
  CalendarFilledIcon,
  HomeFilledIcon,
  HouseIcon,
  InboxFilledIcon,
  InboxIcon,
  PlusIcon,
  SettingsIcon,
  type Icon,
} from '@/shared/ui/icons'
import { Skeleton } from '@/shared/ui/skeleton'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/shared/ui/tooltip'

type ItemProps = {
  to: string
  label: string
  icon: ReactNode
  end?: boolean
  badge?: number | null
  rail: boolean
  onNavigate?: () => void
}

function Item({ to, label, icon, end, badge, rail, onNavigate }: ItemProps) {
  // Класс считаем строкой заранее: подсказка (Slot) не умеет склеивать className-функцию NavLink.
  const active = Boolean(useMatch({ path: to, end: end ?? false }))
  // Разметка одна в обоих режимах, иначе пункт пересоздаётся и анимация ломается.
  // Иконка всегда на оси 36 px (как бургер в шапке); при сворачивании сжимается только ширина
  // подложки — вместе с шириной панели — до круга 48 px, а подпись гаснет.
  return (
    <li className="relative">
      <Tooltip open={rail ? undefined : false}>
        <TooltipTrigger asChild>
          <NavLink
            to={to}
            end={end}
            onClick={onNavigate}
            aria-label={label}
            className={cn(
              'mx-3 flex h-12 items-center gap-3 overflow-hidden rounded-full pr-4 pl-2 text-sm font-medium whitespace-nowrap outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring',
              active ? 'bg-nav-active text-on-nav-active' : 'text-foreground hover:bg-foreground/8',
            )}
          >
            <span className="grid size-8 shrink-0 place-items-center [&_svg]:size-6">{icon}</span>
            <span className={cn('min-w-0 flex-1 truncate transition-opacity duration-200', rail && 'opacity-0')}>{label}</span>
            {badge ? <span className={cn('text-xs tabular-nums transition-opacity duration-200', rail && 'opacity-0')}>{badge}</span> : null}
          </NavLink>
        </TooltipTrigger>
        <TooltipContent side="right">{label}</TooltipContent>
      </Tooltip>
      {badge ? (
        <span className={cn('pointer-events-none absolute top-2 left-[42px] size-2 rounded-full bg-now transition-opacity duration-200', !rail && 'opacity-0')} />
      ) : null}
    </li>
  )
}

/** Иконка из пары «контур / заливка»: заливка у выбранного раздела, как в Gmail и Classroom. */
function NavIcon({ path, end, outline: Outline, filled: Filled }: { path: string; end?: boolean; outline: Icon; filled: Icon }) {
  const active = useMatch({ path, end: end ?? false })
  return active ? <Filled /> : <Outline />
}

function CourseLetter({ id, name }: { id: string; name: string }) {
  return (
    <span className="grid size-8 place-items-center rounded-full text-sm font-medium text-white" style={{ backgroundColor: colorFor(id) }}>
      {name.trim()[0]?.toUpperCase()}
    </span>
  )
}

/** Навигация в духе Google Classroom: разделы, список курсов, архив и настройки. В узком режиме — только иконки. */
export function NavDrawer({ rail = false, onNavigate }: { rail?: boolean; onNavigate?: () => void }) {
  const isTeacher = useIsTeacher()
  const courses = useQuery(coursesQuery(false, 1, 50))
  const queue = useQuery({ ...queueQuery({ course_id: null, assignment_id: null }, 1, 1), enabled: isTeacher })
  const p = { rail, onNavigate }
  return (
    <nav aria-label="Основная навигация" className="flex min-h-0 flex-1 flex-col overflow-hidden py-2">
      <ul className="flex flex-col gap-1">
        <Item {...p} to="/" end label="Главная" icon={<NavIcon path="/" end outline={HouseIcon} filled={HomeFilledIcon} />} />
        <Item {...p} to="/calendar" label="Календарь" icon={<NavIcon path="/calendar" outline={CalendarDaysIcon} filled={CalendarFilledIcon} />} />
        {isTeacher && (
          <Item {...p} to="/reviews" label="Проверка работ" badge={queue.data?.total} icon={<NavIcon path="/reviews" outline={InboxIcon} filled={InboxFilledIcon} />} />
        )}
      </ul>
      <div className="mx-4 my-2 border-t" />
      <p className={cn('h-8 overflow-hidden px-6 pt-2 text-sm font-medium whitespace-nowrap text-muted-foreground transition-opacity duration-200', rail && 'opacity-0')} aria-hidden={rail}>
        {isTeacher ? 'Преподавание' : 'Мои курсы'}
      </p>
      {/* Список курсов прокручивается сам; архив и настройки прижаты к низу и не сдвигаются при загрузке. */}
      <ul className="flex min-h-0 flex-1 flex-col gap-1 overflow-x-hidden overflow-y-auto">
        {courses.isPending &&
          Array.from({ length: 3 }, (_, i) => (
            <li key={i} className="mx-5 flex h-12 items-center gap-3 overflow-hidden">
              <Skeleton className="size-8 shrink-0 rounded-full" />
              <Skeleton className={cn('h-4 flex-1 transition-opacity', rail && 'opacity-0')} />
            </li>
          ))}
        {courses.data?.items.map((c) => (
          <Item key={c.id} {...p} to={`/courses/${c.id}`} label={c.name} icon={<CourseLetter id={c.id} name={c.name} />} />
        ))}
        {isTeacher && <Item {...p} to="/courses/new" label="Создать курс" icon={<PlusIcon />} />}
      </ul>
      <div className="mx-4 my-2 border-t" />
      <ul className="flex flex-col gap-1">
        <Item {...p} to="/courses/archive" label="Архив курсов" icon={<ArchiveIcon />} />
        <Item {...p} to="/profile" label="Настройки профиля" icon={<SettingsIcon />} />
      </ul>
    </nav>
  )
}
