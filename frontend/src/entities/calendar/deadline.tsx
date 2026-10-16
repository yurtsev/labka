import type { CalendarItem } from '@/shared/api'
import { hm } from '@/shared/lib/date'
import { ASSIGNMENT_TYPE } from '@/shared/lib/format'
import { cn } from '@/shared/lib/utils'
import { CheckIcon, FlagIcon, HourglassIcon, RotateCcwIcon, TriangleAlertIcon, type Icon } from '@/shared/ui/icons'

export type DeadlineState = 'todo' | 'overdue' | 'revision' | 'review' | 'accepted' | 'teacher'

/** Что студенту делать с дедлайном: глагол, иконка и цвет плашки. */
export const DEADLINE_STATE: Record<DeadlineState, { label: string; icon: Icon; chip: string; dot: string }> = {
  todo: { label: 'Сдать', icon: FlagIcon, chip: 'bg-deadline text-on-event', dot: 'bg-deadline' },
  overdue: { label: 'Просрочено', icon: TriangleAlertIcon, chip: 'bg-[#f28b82] text-on-event', dot: 'bg-[#f28b82]' },
  revision: { label: 'Доработать', icon: RotateCcwIcon, chip: 'bg-[#fcad70] text-on-event', dot: 'bg-[#fcad70]' },
  review: { label: 'На проверке', icon: HourglassIcon, chip: 'border border-deadline/80 text-deadline', dot: 'border-2 border-deadline' },
  accepted: { label: 'Принято', icon: CheckIcon, chip: 'border border-border text-muted-foreground', dot: 'border-2 border-muted-foreground' },
  teacher: { label: 'Срок сдачи', icon: FlagIcon, chip: 'bg-deadline text-on-event', dot: 'bg-deadline' },
}

/** Момент дедлайна: день и время по МСК. */
export const deadlineDate = (item: CalendarItem) => new Date(`${item.day}T${item.starts_at ?? '23:59:00'}+03:00`)

export function deadlineState(item: CalendarItem, now = new Date()): DeadlineState {
  const status = item.deadline?.my_status
  if (status === undefined || status === null) return 'teacher'
  if (status === 'accepted') return 'accepted'
  if (status === 'on_review') return 'review'
  if (status === 'revision') return deadlineDate(item) < now ? 'overdue' : 'revision'
  return deadlineDate(item) < now ? 'overdue' : 'todo'
}

/** Подпись для подсказки: «Сдать до 12:00 · ПЗ «Нормализация» · Базы данных». */
export function deadlineHint(item: CalendarItem) {
  const d = item.deadline!
  const st = DEADLINE_STATE[deadlineState(item)]
  return `${st.label} · до ${item.starts_at ? hm(item.starts_at) : 'конца дня'} · ${ASSIGNMENT_TYPE[d.type].short} «${d.title}» · ${d.course.name}`
}

/** Плашка дедлайна: иконка статуса, время и название задания. */
export function DeadlineChip({ item, onClick, className, withLabel }: { item: CalendarItem; onClick?: () => void; className?: string; withLabel?: boolean }) {
  const state = DEADLINE_STATE[deadlineState(item)]
  const StateIcon = state.icon
  return (
    <button
      type="button"
      title={deadlineHint(item)}
      onClick={(e) => {
        e.stopPropagation()
        onClick?.()
      }}
      className={cn(
        'flex h-[22px] w-full min-w-0 shrink-0 items-center gap-1 rounded-full px-2 text-left text-xs outline-none hover:brightness-110 focus-visible:ring-2 focus-visible:ring-ring',
        state.chip,
        className,
      )}
    >
      <StateIcon className="size-3.5 shrink-0" />
      {withLabel && <span className="shrink-0 font-medium">{state.label}</span>}
      {item.starts_at && <span className="shrink-0 tabular-nums opacity-90">{hm(item.starts_at)}</span>}
      <span className="truncate font-medium">{item.deadline!.title}</span>
    </button>
  )
}
