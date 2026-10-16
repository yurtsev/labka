
import type { AssignmentType, DeadlineType, Progress, ProgressStatus } from '@/shared/api'
import { formatDateTime, relativeDeadline } from '@/shared/lib/date'
import { ASSIGNMENT_TYPE, DEADLINE_TYPE, gradeLabel, STATUS } from '@/shared/lib/format'
import { cn } from '@/shared/lib/utils'
import { Badge } from '@/shared/ui/badge'
import { CheckIcon, ClockAlertIcon, HourglassIcon, MinusIcon, RotateCcwIcon } from '@/shared/ui/icons'

export function AssignmentTypeBadge({ type, className }: { type: AssignmentType; className?: string }) {
  return (
    <Badge variant="outline" className={cn('w-14 text-muted-foreground', className)} title={ASSIGNMENT_TYPE[type].long}>
      {ASSIGNMENT_TYPE[type].short}
    </Badge>
  )
}

const STATUS_VIEW = {
  accepted: { variant: 'task', icon: CheckIcon },
  on_review: { variant: 'lesson', icon: HourglassIcon },
  revision: { variant: 'deadline', icon: RotateCcwIcon },
  not_submitted: { variant: 'outline', icon: MinusIcon },
} as const

export function StatusBadge({ status, className }: { status: ProgressStatus; className?: string }) {
  const { variant, icon: Icon } = STATUS_VIEW[status]
  return (
    <Badge variant={variant} className={cn(status === 'not_submitted' && 'text-muted-foreground', className)}>
      <Icon data-icon="inline-start" aria-hidden />
      {STATUS[status]}
    </Badge>
  )
}

/** Статус и текущая оценка студента по заданию. */
export function ProgressView({ progress }: { progress: Progress }) {
  const grade = gradeLabel(progress.grade)
  return (
    <span className="flex items-center gap-2">
      <StatusBadge status={progress.status} />
      {grade && (
        <span className="text-sm font-medium tabular-nums" aria-label={`оценка ${grade}`}>
          {grade}
        </span>
      )}
    </span>
  )
}

export function LateBadge() {
  return (
    <Badge variant="exam">
      <ClockAlertIcon data-icon="inline-start" aria-hidden />
      просрочено
    </Badge>
  )
}

/** «до 12 октября, 23:59 · жёсткий» с подсказкой, сколько осталось. */
export function DeadlineText({ type, at, className }: { type: DeadlineType; at: string | null; className?: string }) {
  if (type === 'none' || !at) return <span className={cn('text-muted-foreground', className)}>без дедлайна</span>
  const passed = new Date(at) < new Date()
  return (
    <span className={cn('tabular-nums', className)} title={relativeDeadline(at)}>
      <span className={passed ? 'text-muted-foreground' : undefined}>до {formatDateTime(at)}</span>
      <span className={cn('text-muted-foreground', type === 'hard' && !passed && 'text-deadline')}> · {DEADLINE_TYPE[type]}</span>
    </span>
  )
}
