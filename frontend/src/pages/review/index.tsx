import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { LateBadge, StatusBadge } from '@/entities/assignment'
import { CourseBreadcrumbs, courseQuery } from '@/entities/course'
import { queueQuery, reviewHref, studentAttemptsQuery } from '@/entities/review'
import { ReviewForm } from '@/features/review-attempt'
import type { ReviewAttempt } from '@/shared/api'
import { formatDateTime, formatDateTimeShort } from '@/shared/lib/date'
import { fullName, gradeLabel, scaleLabel } from '@/shared/lib/format'
import { cn } from '@/shared/lib/utils'
import { SendIcon } from '@/shared/ui/icons'
import { FileList } from '@/shared/ui/kit/file-list'
import { Markdown } from '@/shared/ui/kit/markdown'
import { PageHeader, row, surface } from '@/shared/ui/kit/page-header'
import { EmptyState, QueryState } from '@/shared/ui/kit/query-state'
import { Skeleton } from '@/shared/ui/skeleton'


const statusOf = (a: ReviewAttempt) => (a.review ? (a.review.verdict === 'accepted' ? 'accepted' : 'revision') : 'on_review')

export function ReviewPage() {
  const { courseId = '', assignmentId = '', studentId = '' } = useParams()
  const query = useQuery(studentAttemptsQuery(courseId, assignmentId, studentId))
  const course = useQuery(courseQuery(courseId))
  const queue = useQuery(queueQuery({ course_id: null, assignment_id: null }, 1, 5))
  const navigate = useNavigate()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const nextInQueue = queue.data?.items.find((q) => !(q.student.id === studentId && q.assignment.id === assignmentId))

  return (
    <QueryState
      query={query}
      loading={
        <>
          <PageHeader crumbs={<Skeleton className="h-4 w-56" />} title={<Skeleton className="h-8 w-80" />} />
          <Skeleton className="h-96 rounded-2xl" />
        </>
      }
    >
      {(data) => {
        const selected = data.attempts.find((a) => a.id === selectedId) ?? data.attempts[0]
        const isLast = selected?.id === data.attempts[0]?.id
        return (
          <>
            <PageHeader
              crumbs={<CourseBreadcrumbs course={course.data} current={data.assignment.title} />}
              title={fullName(data.student)}
              description={`«${data.assignment.title}» · шкала ${scaleLabel(data.scale)}`}
            />
            {!selected ? (
              <EmptyState icon={<SendIcon />} title="Студент ещё ничего не отправил" />
            ) : (
              <div className="grid items-start gap-8 lg:grid-cols-[20rem_minmax(0,1fr)]">
                <nav aria-label="Попытки" className={cn(surface, 'flex flex-col divide-y')}>
                  {data.attempts.map((a) => (
                    <button
                      key={a.id}
                      type="button"
                      onClick={() => setSelectedId(a.id)}
                      aria-current={a.id === selected.id}
                      className={cn(
                        row,
                        'justify-between text-sm',
                        a.id === selected.id && 'bg-primary/12 hover:bg-primary/12',
                      )}
                    >
                      <span className="flex flex-col gap-1">
                        <span className="font-medium tabular-nums">Попытка {a.number}</span>
                        <span className="text-xs text-muted-foreground tabular-nums">{formatDateTimeShort(a.created_at)}</span>
                      </span>
                      <StatusBadge status={statusOf(a)} />
                    </button>
                  ))}
                </nav>
                <div className="flex flex-col gap-8">
                  <section className="flex flex-col gap-4 rounded-2xl border bg-card p-6">
                    <header className="flex flex-wrap items-center gap-3">
                      <h2 className="text-base font-medium">Попытка {selected.number}</h2>
                      <span className="text-sm text-muted-foreground tabular-nums">{formatDateTime(selected.created_at)}</span>
                      {selected.is_late && <LateBadge />}
                      {selected.review && gradeLabel(selected.review.grade) && (
                        <span className="ml-auto text-sm">
                          оценка <span className="font-medium tabular-nums">{gradeLabel(selected.review.grade)}</span>
                        </span>
                      )}
                    </header>
                    {selected.comment ? (
                      <p className="text-sm">
                        <span className="text-muted-foreground">Комментарий студента: </span>
                        {selected.comment}
                      </p>
                    ) : (
                      <p className="text-sm text-muted-foreground">Без комментария</p>
                    )}
                    <FileList files={selected.files} />
                    {selected.review?.comment && !isLast && (
                      <div className="border-l-2 border-primary/60 pl-4">
                        <Markdown className="text-muted-foreground">{selected.review.comment}</Markdown>
                      </div>
                    )}
                  </section>
                  {isLast || selected.review ? (
                    <ReviewForm
                      key={selected.id}
                      path={{ course_id: courseId, assignment_id: assignmentId }}
                      attempt={selected}
                      scale={data.scale}
                      onSaved={() => query.refetch()}
                      next={
                        nextInQueue
                          ? { label: 'Следующая в очереди', onClick: () => (setSelectedId(null), navigate(reviewHref(nextInQueue))) }
                          : undefined
                      }
                    />
                  ) : (
                    <p className="text-sm text-muted-foreground">Проверяется только последняя попытка.</p>
                  )}
                </div>
              </div>
            )}
          </>
        )
      }}
    </QueryState>
  )
}
