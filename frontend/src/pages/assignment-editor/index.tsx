import { useQuery } from '@tanstack/react-query'
import { Navigate, useParams } from 'react-router'

import { assignmentQuery } from '@/entities/assignment'
import { CourseBreadcrumbs, courseQuery } from '@/entities/course'
import { AssignmentForm } from '@/features/assignment-editor'
import { PageHeader } from '@/shared/ui/kit/page-header'
import { QueryState } from '@/shared/ui/kit/query-state'
import { Skeleton } from '@/shared/ui/skeleton'

export function NewAssignmentPage() {
  const { courseId = '' } = useParams()
  const course = useQuery(courseQuery(courseId))
  return (
    <QueryState query={course} loading={<Skeleton className="h-96 rounded-2xl" />}>
      {(c) =>
        c.is_archived ? (
          <Navigate to={`/courses/${c.id}`} replace />
        ) : (
          <>
            <PageHeader
              crumbs={<CourseBreadcrumbs course={c} current="Новое задание" />}
              title="Новое задание"
              description="Студенты курса получат уведомление сразу после публикации."
            />
            <AssignmentForm course={c} />
          </>
        )
      }
    </QueryState>
  )
}

export function EditAssignmentPage() {
  const { courseId = '', assignmentId = '' } = useParams()
  const course = useQuery(courseQuery(courseId))
  const assignment = useQuery(assignmentQuery(courseId, assignmentId))
  return (
    <QueryState query={assignment} loading={<Skeleton className="h-96 rounded-2xl" />}>
      {(a) =>
        course.data ? (
          <>
            <PageHeader crumbs={<CourseBreadcrumbs course={course.data} current={a.title} />} title="Изменить задание" />
            <AssignmentForm course={course.data} assignment={a} />
          </>
        ) : (
          <Skeleton className="h-96 rounded-2xl" />
        )
      }
    </QueryState>
  )
}
