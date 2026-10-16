import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { DEADLINE_STATE, deadlineDate, deadlineState, eventTime, eventTitle, KIND_BG, KIND_LABEL } from '@/entities/calendar'
import { useToggleTask } from '@/features/personal-task'
import type { CalendarItem } from '@/shared/api'
import { formatDayLong, relativeDeadline } from '@/shared/lib/date'
import { ASSIGNMENT_TYPE, DEADLINE_TYPE } from '@/shared/lib/format'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/shared/ui/dialog'
import {
  AssignmentIcon,
  BookOpenIcon,
  CalendarSyncIcon,
  FlagIcon,
  GroupIcon,
  LocationIcon,
  PencilIcon,
  TaskAltIcon,
} from '@/shared/ui/icons'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/shared/ui/tooltip'

import { DeadlineStatus } from './schedule-list'

function Row({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <li className="flex items-start gap-5 text-sm">
      <span className="grid size-5 shrink-0 place-items-center text-muted-foreground [&_svg]:size-5">{icon}</span>
      <span className="min-w-0 pt-px">{children}</span>
    </li>
  )
}

type Props = { item: CalendarItem | null; onClose: () => void; onEditTask: (item: CalendarItem) => void; withGroup: boolean }

/** Карточка события, как всплывающая карточка Google Календаря. */
export function EventDialog({ item, onClose, onEditTask, withGroup }: Props) {
  const toggle = useToggleTask()
  const x = item?.lesson ?? item?.exam
  return (
    <Dialog open={!!item} onOpenChange={(o) => !o && onClose()}>
      <DialogContent overlayClassName="bg-black/20" className="gap-4 rounded-[28px] p-0 pb-5 sm:max-w-[448px]">
        {item && (
          <>
            <div className="flex h-[72px] items-start justify-end gap-1 pt-4 pr-16 pl-4">
              {item.task && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" aria-label="Изменить задачу" onClick={() => onEditTask(item)}>
                      <PencilIcon />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Изменить</TooltipContent>
                </Tooltip>
              )}
            </div>
            <div className="flex gap-5 px-6">
              <span className={cn('mt-2 size-4 shrink-0 rounded-[4px]', item.deadline ? DEADLINE_STATE[deadlineState(item)].dot : KIND_BG[item.kind])} />
              <div className="min-w-0">
                <DialogTitle className={cn('pr-0 text-[22px] leading-7', item.task?.is_done && 'text-muted-foreground line-through')}>{eventTitle(item)}</DialogTitle>
                <DialogDescription className="mt-1">
                  {formatDayLong(item.day)}
                  {eventTime(item) ? ` · ${eventTime(item)}` : ' · весь день'}
                </DialogDescription>
              </div>
            </div>
            <ul className="flex flex-col gap-4 px-6 pt-2">
              {item.lesson && (
                <Row icon={<BookOpenIcon />}>
                  {ASSIGNMENT_TYPE[item.lesson.lesson_type].long}
                  {item.lesson.slot ? `, ${item.lesson.slot}-я пара` : ''}
                </Row>
              )}
              {item.lesson?.is_extra && <Row icon={<CalendarSyncIcon />}>Разовое занятие вне расписания</Row>}
              {x?.room && <Row icon={<LocationIcon />}>Аудитория {x.room}</Row>}
              {x && withGroup && <Row icon={<GroupIcon />}>{x.group.name}</Row>}
              {item.deadline && (
                <>
                  <li className="flex flex-wrap items-center gap-x-3 gap-y-2 pl-10 text-sm">
                    <DeadlineStatus item={item} />
                    <span className={cn(deadlineState(item) === 'overdue' ? 'font-medium text-[#f28b82]' : 'text-muted-foreground')}>
                      {relativeDeadline(deadlineDate(item).toISOString())}
                    </span>
                  </li>
                  <Row icon={<AssignmentIcon />}>
                    {ASSIGNMENT_TYPE[item.deadline.type].long} · {item.deadline.course.name}
                  </Row>
                  <Row icon={<FlagIcon />}>
                    {DEADLINE_TYPE[item.deadline.deadline_type][0].toUpperCase() + DEADLINE_TYPE[item.deadline.deadline_type].slice(1)} дедлайн
                    {item.deadline.deadline_type === 'hard' ? ': после срока принимается только доработка попытки, отправленной вовремя' : item.deadline.deadline_type === 'soft' ? ': после срока сдать можно, с пометкой «просрочено»' : ''}
                  </Row>
                </>
              )}
              {item.task && <Row icon={<TaskAltIcon />}>{item.task.is_done ? 'Выполнена' : 'Личная задача, видна только вам'}</Row>}
              <Row icon={<span className={cn('size-3 rounded-full', KIND_BG[item.kind])} />}>{KIND_LABEL[item.kind]}</Row>
            </ul>
            <div className="flex justify-end gap-2 px-6 pt-2">
              {x && (
                <Button variant="ghost" asChild>
                  <Link to={`/courses/${x.course.id}`} onClick={onClose}>
                    Открыть курс
                  </Link>
                </Button>
              )}
              {item.deadline && (
                <Button asChild>
                  <Link to={`/courses/${item.deadline.course.id}/assignments/${item.deadline.assignment_id}`} onClick={onClose}>
                    Открыть задание
                  </Link>
                </Button>
              )}
              {item.task && (
                <Button
                  variant={item.task.is_done ? 'ghost' : 'default'}
                  onClick={() => {
                    toggle.mutate({ id: item.task!.id, is_done: !item.task!.is_done })
                    onClose()
                  }}
                >
                  {item.task.is_done ? 'Вернуть в невыполненные' : 'Отметить как выполненную'}
                </Button>
              )}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
