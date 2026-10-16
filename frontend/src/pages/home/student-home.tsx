import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'

import { homeQuery } from '@/entities/course'
import { formatDayShort, formatTime, pluralize } from '@/shared/lib/date'
import { AssignmentIcon, CalendarDaysIcon } from '@/shared/ui/icons'
import { QueryState } from '@/shared/ui/kit/query-state'

import { CourseCard, CourseGrid, DeadlinePanel, HomeHeader, homeGrid, HomeSkeleton, LessonPanel, teacherName } from './parts'

export function StudentHome() {
  const query = useQuery(homeQuery)
  return (
    <>
    <HomeHeader />
    <QueryState query={query} loading={<HomeSkeleton />}>
      {(home) => (
        <div className={homeGrid}>
          <CourseGrid count={home.courses.length}>
            {home.courses.map((c) => {
              const due = home.upcoming_deadlines.filter((d) => d.course.id === c.id).slice(0, 2)
              return (
                <CourseCard
                  key={c.id}
                  course={c}
                  subtitle={teacherName(c)}
                  actions={[
                    { to: `/courses/${c.id}`, label: 'Задания и материалы', icon: <AssignmentIcon /> },
                    { to: '/calendar', label: 'Календарь', icon: <CalendarDaysIcon /> },
                  ]}
                >
                  {due.length > 0 ? (
                    <>
                      <p className="text-xs text-muted-foreground">Скоро сдавать</p>
                      <ul className="pointer-events-auto mt-1 flex flex-col gap-1">
                        {due.map((d) => (
                          <li key={d.assignment_id} className="truncate">
                            <Link to={`/courses/${c.id}/assignments/${d.assignment_id}`} className="hover:underline">
                              <span className="text-muted-foreground tabular-nums">
                                {formatDayShort(d.deadline_at.slice(0, 10))}, {formatTime(d.deadline_at)}
                              </span>{' '}
                              {d.title}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </>
                  ) : c.not_submitted ? (
                    <p className="text-muted-foreground">{pluralize(c.not_submitted, ['задание не сдано', 'задания не сданы', 'заданий не сдано'])}</p>
                  ) : (
                    <p className="text-muted-foreground">Всё сдано</p>
                  )}
                </CourseCard>
              )
            })}
          </CourseGrid>
          {home.courses.length > 0 && (
            <aside className="flex flex-col gap-6" aria-label="Сводка">
              <DeadlinePanel deadlines={home.upcoming_deadlines} />
              <LessonPanel lessons={home.upcoming_lessons} />
            </aside>
          )}
        </div>
      )}
    </QueryState>
    </>
  )
}
