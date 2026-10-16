import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'

import { homeQuery } from '@/entities/course'
import { pluralize } from '@/shared/lib/date'
import { Button } from '@/shared/ui/button'
import { InboxIcon, SettingsIcon } from '@/shared/ui/icons'
import { QueryState } from '@/shared/ui/kit/query-state'

import { CourseCard, CourseGrid, HomeHeader, homeGrid, HomeSkeleton, LessonPanel, Panel } from './parts'

export function TeacherHome() {
  const query = useQuery(homeQuery)
  return (
    <>
    <HomeHeader teacher />
    <QueryState query={query} loading={<HomeSkeleton />}>
      {(home) => (
        <div className={homeGrid}>
          <CourseGrid count={home.courses.length} teacher>
            {home.courses.map((c) => (
              <CourseCard
                key={c.id}
                course={c}
                subtitle={c.groups.map((g) => g.name).join(', ') || 'Группы не добавлены'}
                actions={[
                  { to: `/reviews?course=${c.id}`, label: 'Проверка работ', icon: <InboxIcon /> },
                  { to: `/courses/${c.id}/settings`, label: 'Настройки курса', icon: <SettingsIcon /> },
                ]}
              >
                <p className={c.pending_reviews ? 'font-medium text-primary' : 'text-muted-foreground'}>
                  {c.pending_reviews ? `${pluralize(c.pending_reviews, ['работа ждёт', 'работы ждут', 'работ ждут'])} проверки` : 'Все работы проверены'}
                </p>
              </CourseCard>
            ))}
          </CourseGrid>
          <aside className="flex flex-col gap-6" aria-label="Сводка">
            <Panel
              title="Проверка работ"
              footer={
                <Button variant="ghost" asChild>
                  <Link to="/reviews">Открыть очередь</Link>
                </Button>
              }
            >
              <p className="flex items-center gap-4 px-6 pb-6 text-sm">
                <span className="grid size-10 shrink-0 place-items-center rounded-full bg-nav-active text-on-nav-active">
                  <InboxIcon className="size-5" />
                </span>
                {home.pending_reviews ? `${pluralize(home.pending_reviews, ['работа ждёт', 'работы ждут', 'работ ждут'])} проверки` : 'Новых работ нет'}
              </p>
            </Panel>
            <LessonPanel lessons={home.upcoming_lessons} withGroup />
          </aside>
        </div>
      )}
    </QueryState>
    </>
  )
}
