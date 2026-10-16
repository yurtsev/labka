import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'

import { courseQuery, examsQuery, materialsQuery } from '@/entities/course'
import { courseScheduleQuery } from '@/entities/schedule'
import { useIsTeacher } from '@/entities/session'
import { CreateMaterialButton, DeleteMaterialButton, EditMaterialButton } from '@/features/material-editor'
import { colorFor } from '@/shared/lib/color'
import { cn } from '@/shared/lib/utils'
import { formatDay, hm } from '@/shared/lib/date'
import { EXAM_TYPE, LESSON_TYPE, REPEAT, scaleLabel, shortName, WEEKDAYS } from '@/shared/lib/format'
import { Alert, AlertDescription, AlertTitle } from '@/shared/ui/alert'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { ArchiveIcon, FolderOpenIcon, PlusIcon, SettingsIcon } from '@/shared/ui/icons'
import { FileList } from '@/shared/ui/kit/file-list'
import { Markdown } from '@/shared/ui/kit/markdown'
import { Section, surface } from '@/shared/ui/kit/page-header'
import { EmptyState, QueryState } from '@/shared/ui/kit/query-state'
import { Skeleton } from '@/shared/ui/skeleton'
import { CourseFeed } from '@/widgets/course-feed'

function Materials({ courseId, editable }: { courseId: string; editable: boolean }) {
  const query = useQuery(materialsQuery(courseId))
  return (
    <Section
      title="Материалы"
      className="scroll-mt-20"
      actions={
        editable && (
          <CreateMaterialButton courseId={courseId}>
            <Button variant="outline">
              <PlusIcon data-icon="inline-start" />
              Материал
            </Button>
          </CreateMaterialButton>
        )
      }
    >
      <div id="materials" />
      <QueryState
        query={query}
        loading={<Skeleton className="h-40 rounded-2xl" />}
        isEmpty={(d) => d.items.length === 0}
        empty={<EmptyState icon={<FolderOpenIcon />} title="Материалов нет" />}
      >
        {(page) => (
          <ul className={cn(surface, 'divide-y')}>
            {page.items.map((m) => (
              <li key={m.id} className="flex flex-col gap-2 px-6 py-4">
                <div className="flex min-h-6 items-start justify-between gap-2">
                  <h3 className="text-sm leading-6 font-medium">{m.title}</h3>
                  {editable && (
                    <span className="-my-2 -mr-2 flex shrink-0">
                      <EditMaterialButton courseId={courseId} material={m} />
                      <DeleteMaterialButton courseId={courseId} materialId={m.id} title={m.title} />
                    </span>
                  )}
                </div>
                {m.text && <Markdown className="text-muted-foreground">{m.text}</Markdown>}
                <FileList files={m.files} />
              </li>
            ))}
          </ul>
        )}
      </QueryState>
    </Section>
  )
}

function Schedule({ courseId, withGroup }: { courseId: string; withGroup: boolean }) {
  const schedule = useQuery(courseScheduleQuery(courseId))
  const exams = useQuery(examsQuery(courseId))
  return (
    <Section title="Расписание" className="scroll-mt-20">
      <div id="schedule" />
      <QueryState query={schedule} loading={<Skeleton className="h-40 rounded-2xl" />}>
        {(s) => (
          <div className="flex flex-col gap-4 rounded-2xl border bg-card p-6 text-sm">
            {s.rules.length === 0 && <p className="text-muted-foreground">Занятия ещё не назначены</p>}
            <ul className="flex flex-col gap-2">
              {s.rules.map((r) => (
                <li key={r.id} className="flex items-baseline justify-between gap-3">
                  <span>
                    {WEEKDAYS[r.weekday - 1]}, {hm(r.starts_at)}
                    <span className="text-muted-foreground"> · {LESSON_TYPE[r.lesson_type]}{withGroup && ` · ${r.group.name}`}</span>
                  </span>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {REPEAT[r.repeat]}
                    {r.room && `, ${r.room}`}
                  </span>
                </li>
              ))}
            </ul>
            {exams.data && exams.data.items.length > 0 && (
              <ul className="flex flex-col gap-2 border-t pt-4">
                {exams.data.items.map((x) => (
                  <li key={x.id} className="flex items-center justify-between gap-3">
                    <Badge variant="exam">{EXAM_TYPE[x.exam_type]}</Badge>
                    <span className="text-xs text-muted-foreground">
                      {formatDay(x.day)}, {hm(x.starts_at)}
                      {x.room && `, ауд. ${x.room}`}
                      {withGroup && `, ${x.group.name}`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </QueryState>
    </Section>
  )
}

export function CoursePage() {
  const { courseId = '' } = useParams()
  const query = useQuery(courseQuery(courseId))
  const isTeacher = useIsTeacher()

  return (
    <QueryState
      query={query}
      loading={
        <div className="flex flex-col gap-4">
          <Skeleton className="h-48 rounded-2xl" />
        </div>
      }
    >
      {(course) => (
        <>
          <header
            className="relative flex min-h-48 flex-col justify-end gap-1 overflow-hidden rounded-2xl px-6 pt-16 pb-6 text-white sm:px-8"
            style={{ background: `linear-gradient(135deg, ${colorFor(course.id)}, color-mix(in srgb, ${colorFor(course.id)}, black 30%))` }}
          >
            <h1 className="text-[28px] leading-9 sm:text-[36px] sm:leading-[44px]">{course.name}</h1>
            <p className="text-base text-white/90">
              {shortName(course.teacher)} · шкала {scaleLabel(course.scale)}
              {isTeacher && course.groups.length > 0 && ` · ${course.groups.map((g) => g.name).join(', ')}`}
            </p>
            {isTeacher && (
              <div className="absolute top-4 right-4 flex gap-2">
                <Button asChild className="bg-white/90 text-[#1f1f1f] hover:bg-white">
                  <Link to={`/courses/${course.id}/settings`}>
                    <SettingsIcon data-icon="inline-start" />
                    Настройки
                  </Link>
                </Button>
              </div>
            )}
          </header>
          {(course.description || course.grading_note) && (
            <div className="flex max-w-prose flex-col gap-1 text-sm">
              {course.description && <p className="text-foreground/90">{course.description}</p>}
              {course.grading_note && <p className="text-muted-foreground">Оценивание: {course.grading_note}</p>}
            </div>
          )}
          {course.is_archived && (
            <Alert>
              <ArchiveIcon />
              <AlertTitle>Курс в архиве</AlertTitle>
              <AlertDescription>Всё доступно только для чтения.</AlertDescription>
            </Alert>
          )}
          <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
            <CourseFeed courseId={course.id} archived={course.is_archived} />
            <div className="flex flex-col gap-8">
              <Materials courseId={course.id} editable={isTeacher && !course.is_archived} />
              <Schedule courseId={course.id} withGroup={isTeacher} />
            </div>
          </div>
        </>
      )}
    </QueryState>
  )
}
