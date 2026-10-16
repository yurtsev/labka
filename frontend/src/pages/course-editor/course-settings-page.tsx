import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router'
import { toast } from 'sonner'

import { CourseBreadcrumbs, courseQuery } from '@/entities/course'
import { CourseExams, CourseForm, CourseGroups, ExtraLessons, ScheduleRules, type CourseFormValues } from '@/features/course-editor'
import { client, unwrap } from '@/shared/api'
import type { Course } from '@/shared/api'
import { toastError } from '@/shared/lib/form'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/shared/ui/alert-dialog'
import { Button } from '@/shared/ui/button'
import { ArchiveIcon, ArchiveRestoreIcon } from '@/shared/ui/icons'
import { PageHeader, Section } from '@/shared/ui/kit/page-header'
import { QueryState } from '@/shared/ui/kit/query-state'
import { Skeleton } from '@/shared/ui/skeleton'

function ArchiveButton({ course }: { course: Course }) {
  const queryClient = useQueryClient()
  const path = { course_id: course.id }
  const mutation = useMutation({
    mutationFn: () =>
      course.is_archived
        ? unwrap(client.POST('/api/courses/{course_id}/unarchive', { params: { path } }))
        : unwrap(client.POST('/api/courses/{course_id}/archive', { params: { path } })),
    onSuccess: (c) => {
      queryClient.setQueryData(['course', c.id], c)
      queryClient.invalidateQueries({ queryKey: ['home'] })
      queryClient.invalidateQueries({ queryKey: ['courses'] })
      toast.success(c.is_archived ? 'Курс отправлен в архив' : 'Курс возвращён из архива')
    },
    onError: toastError,
  })
  if (course.is_archived) {
    return (
      <Button variant="outline" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
        <ArchiveRestoreIcon data-icon="inline-start" />
        Вернуть из архива
      </Button>
    )
  }
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="outline">
          <ArchiveIcon data-icon="inline-start" />
          Отправить в архив
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Отправить курс в архив?</AlertDialogTitle>
          <AlertDialogDescription>Курс станет только для чтения: студенты не смогут сдавать работы, а занятия пропадут из календаря. Вернуть можно в любой момент.</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Отмена</AlertDialogCancel>
          <AlertDialogAction onClick={() => mutation.mutate()}>В архив</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

export function CourseSettingsPage() {
  const { courseId = '' } = useParams()
  const query = useQuery(courseQuery(courseId))
  const queryClient = useQueryClient()
  const save = useMutation({
    mutationFn: ({ group_ids: _g, ...body }: CourseFormValues) => unwrap(client.PUT('/api/courses/{course_id}', { params: { path: { course_id: courseId } }, body })),
    onSuccess: (c) => {
      queryClient.setQueryData(['course', c.id], c)
      queryClient.invalidateQueries({ queryKey: ['home'] })
      toast.success('Настройки сохранены')
    },
    onError: toastError,
  })

  return (
    <QueryState
      query={query}
      loading={
        <>
          <PageHeader crumbs={<Skeleton className="h-4 w-56" />} title="Настройки курса" />
          <Skeleton className="h-96 rounded-2xl" />
        </>
      }
    >
      {(course) => (
        <>
          <PageHeader crumbs={<CourseBreadcrumbs course={course} current="Настройки" />} title="Настройки курса" actions={<ArchiveButton course={course} />} />
          <Section title="Основное">
            <div className="rounded-2xl border bg-card p-6">
              <CourseForm key={course.id + String(course.is_archived)} course={course} pending={save.isPending} submitLabel="Сохранить" onSubmit={(v) => save.mutate(v)} />
            </div>
          </Section>
          <Section title="Группы">
            <div className="rounded-2xl border bg-card p-6">
              <CourseGroups course={course} />
            </div>
          </Section>
          <Section title="Правила расписания">
            <ScheduleRules course={course} />
          </Section>
          <Section title="Разовые занятия">
            <ExtraLessons course={course} />
          </Section>
          <Section title="Зачёты и экзамены">
            <CourseExams course={course} />
          </Section>
        </>
      )}
    </QueryState>
  )
}
