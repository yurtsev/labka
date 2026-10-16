import type { Attempt } from '@/shared/api'
import { formatDateTime } from '@/shared/lib/date'
import { gradeLabel } from '@/shared/lib/format'
import { cn } from '@/shared/lib/utils'
import { FileList } from '@/shared/ui/kit/file-list'
import { Markdown } from '@/shared/ui/kit/markdown'

import { LateBadge, StatusBadge } from '../assignment'

/** Попытка в истории: что прислал студент и что ответил преподаватель. */
export function AttemptCard({ attempt, className }: { attempt: Attempt; className?: string }) {
  const review = attempt.review
  const grade = gradeLabel(review?.grade)
  return (
    <article className={cn('flex flex-col gap-4 rounded-2xl border bg-card p-6', className)}>
      <header className="flex min-h-6 flex-wrap items-center gap-x-3 gap-y-2">
        <span className="text-base font-medium tabular-nums">Попытка {attempt.number}</span>
        <time className="text-sm text-muted-foreground tabular-nums" dateTime={attempt.created_at}>
          {formatDateTime(attempt.created_at)}
        </time>
        {attempt.is_late && <LateBadge />}
        <span className="ml-auto flex items-center gap-2">
          <StatusBadge status={review ? (review.verdict === 'accepted' ? 'accepted' : 'revision') : 'on_review'} />
          {grade && <span className="text-sm font-medium tabular-nums">{grade}</span>}
        </span>
      </header>
      {attempt.comment && <p className="text-sm text-foreground/90">{attempt.comment}</p>}
      <FileList files={attempt.files} />
      {review?.comment && (
        <div className="border-l-2 border-primary/60 pl-4">
          <Markdown className="text-muted-foreground">{review.comment}</Markdown>
        </div>
      )}
    </article>
  )
}
