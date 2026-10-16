import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'

import { assignmentQuery, AssignmentTypeBadge, DeadlineText } from '@/entities/assignment'
import { CourseBreadcrumbs, courseQuery } from '@/entities/course'
import { useIsTeacher } from '@/entities/session'
import { ASSIGNMENT_TYPE, scaleLabel } from '@/shared/lib/format'
import { Button } from '@/shared/ui/button'
import { PencilIcon } from '@/shared/ui/icons'
import { FileList } from '@/shared/ui/kit/file-list'
import { Markdown } from '@/shared/ui/kit/markdown'
import { PageHeader } from '@/shared/ui/kit/page-header'
import { QueryState } from '@/shared/ui/kit/query-state'
import { Skeleton } from '@/shared/ui/skeleton'

import { StudentSubmission } from './student-submission'
import { StudentsTable } from './students-table'

export function AssignmentPage() {
  const { courseId = '', assignmentId = '' } = useParams()
  const query = useQuery(assignmentQuery(courseId, assignmentId))
  const course = useQuery(courseQuery(courseId))
  const isTeacher = useIsTeacher()

  return (
    <QueryState
      query={query}
      loading={
        <>
          <PageHeader crumbs={<Skeleton className="h-4 w-56" />} title={<Skeleton className="h-8 w-80" />} description={<Skeleton className="h-4 w-48" />} />
          <Skeleton className="h-40 rounded-2xl" />
        </>
      }
    >
      {(a) => (
        <>
          <PageHeader
            crumbs={<CourseBreadcrumbs course={course.data} current={a.title} />}
            leading={<AssignmentTypeBadge type={a.type} />}
            title={a.title}
            description={
              <span className="flex flex-wrap gap-x-4 gap-y-1">
                <DeadlineText type={a.deadline_type} at={a.deadline_at} />
                <span>шкала {scaleLabel(a.scale)}</span>
              </span>
            }
            actions={
              isTeacher &&
              !course.data?.is_archived && (
                <Button asChild variant="outline">
                  <Link to="edit">
                    <PencilIcon data-icon="inline-start" />
                    Изменить
                  </Link>
                </Button>
              )
            }
          />
          <article className="flex flex-col gap-4">
            <span className="sr-only">{ASSIGNMENT_TYPE[a.type].long}</span>
            {a.grading_note && (
              <p className="max-w-prose border-l-2 border-deadline/60 pl-4 text-sm">
                <span className="text-muted-foreground">Критерии: </span>
                {a.grading_note}
              </p>
            )}
            {a.description ? <Markdown>{a.description}</Markdown> : <p className="text-sm text-muted-foreground">Описания нет.</p>}
            <FileList files={a.files} />
          </article>
          {isTeacher ? (
            course.data && <StudentsTable assignment={a} groups={course.data.groups} />
          ) : (
            <StudentSubmission assignment={a} archived={course.data?.is_archived ?? false} />
          )}
        </>
      )}
    </QueryState>
  )
}
