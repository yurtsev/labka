import { useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'motion/react'
import { useState } from 'react'
import { Link } from 'react-router'

import { AssignmentTypeBadge, DeadlineText, ProgressView, feedQuery } from '@/entities/assignment'
import { useIsTeacher } from '@/entities/session'
import { AnnouncementActions, CreateAnnouncementButton } from '@/features/announcement-editor'
import type { AssignmentType, FeedAssignment, FeedEntry } from '@/shared/api'
import { relativePast } from '@/shared/lib/date'
import { Button } from '@/shared/ui/button'
import { cn } from '@/shared/lib/utils'
import { InboxIcon, MegaphoneIcon, PlusIcon } from '@/shared/ui/icons'
import { row, Section, surface } from '@/shared/ui/kit/page-header'
import { Pager } from '@/shared/ui/kit/pager'
import { EmptyState, QueryState } from '@/shared/ui/kit/query-state'
import { Skeleton } from '@/shared/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/shared/ui/toggle-group'

const FILTERS: { value: AssignmentType | 'all'; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'lab', label: 'Лабы' },
  { value: 'practice', label: 'ПЗ' },
  { value: 'hw', label: 'ДЗ' },
]

function TeacherSummary({ a }: { a: FeedAssignment }) {
  const s = a.summary!
  return (
    <span className="text-xs text-muted-foreground tabular-nums">
      сдали {s.submitted}/{s.students}
      {s.on_review > 0 && <span className="text-lesson"> · ждут проверки {s.on_review}</span>}
      {' · '}приняты {s.accepted}
    </span>
  )
}

function FeedItem({ courseId, entry, editable }: { courseId: string; entry: FeedEntry; editable: boolean }) {
  if (entry.announcement) {
    const n = entry.announcement
    return (
      <div className={cn(row, 'items-start hover:bg-transparent')}>
        <span className="grid h-6 w-14 shrink-0 place-items-center">
          <MegaphoneIcon className="size-5 text-deadline" aria-hidden />
        </span>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <p className="text-sm whitespace-pre-line">{n.text}</p>
          <span className="text-xs text-muted-foreground">
            {relativePast(n.created_at)}
            {n.updated_at !== n.created_at && ' · изменено'}
          </span>
        </div>
        {editable && <AnnouncementActions courseId={courseId} announcement={n} />}
      </div>
    )
  }
  const a = entry.assignment!
  return (
    <Link
      to={`/courses/${courseId}/assignments/${a.id}`}
      className={cn(row, 'flex-wrap sm:flex-nowrap')}
    >
      <span className="flex min-w-0 flex-1 items-center gap-4">
        <AssignmentTypeBadge type={a.type} />
        <span className="flex min-w-0 flex-col gap-1">
          <span className="truncate text-sm font-medium">{a.title}</span>
          <DeadlineText type={a.deadline_type} at={a.deadline_at} className="text-xs" />
        </span>
      </span>
      <span className="shrink-0 pl-18 sm:pl-0">{a.my_progress ? <ProgressView progress={a.my_progress} /> : <TeacherSummary a={a} />}</span>
    </Link>
  )
}

/** Лента курса: задания и объявления, новые сверху, с фильтром по типу задания. */
export function CourseFeed({ courseId, archived }: { courseId: string; archived: boolean }) {
  const [type, setType] = useState<AssignmentType | 'all'>('all')
  const [page, setPage] = useState(1)
  const query = useQuery({ ...feedQuery(courseId, type === 'all' ? null : type, page), placeholderData: (prev) => prev })
  const isTeacher = useIsTeacher()
  const editable = isTeacher && !archived

  return (
    <Section
      title="Лента"
      actions={
        // Фильтры и действия — в строке заголовка: так список ленты и «Материалы» справа начинаются с одной линии.
        <div className="flex flex-wrap items-center gap-2">
          <ToggleGroup
            type="single"
            variant="outline"
            spacing={2}
            value={type}
            onValueChange={(v) => {
              if (!v) return
              setType(v as AssignmentType | 'all')
              setPage(1)
            }}
            aria-label="Фильтр по типу задания"
          >
            {FILTERS.map((f) => (
              <ToggleGroupItem key={f.value} value={f.value}>
                {f.label}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
          {editable && (
            <>
              <CreateAnnouncementButton courseId={courseId}>
                <Button variant="outline">
                  <MegaphoneIcon data-icon="inline-start" />
                  Объявление
                </Button>
              </CreateAnnouncementButton>
              <Button asChild>
                <Link to={`/courses/${courseId}/assignments/new`}>
                  <PlusIcon data-icon="inline-start" />
                  Задание
                </Link>
              </Button>
            </>
          )}
        </div>
      }
    >
      <QueryState
        query={query}
        loading={
<Skeleton className="h-96 rounded-2xl" />
        }
        isEmpty={(d) => d.items.length === 0}
        empty={<EmptyState icon={<InboxIcon />} title="Пока пусто" description={type === 'all' ? 'Задания и объявления появятся здесь.' : 'Заданий этого типа нет.'} />}
      >
        {(feed) => (
          <>
          <ul className={cn(surface, 'divide-y transition-opacity', query.isPlaceholderData && 'opacity-60')}>
            <AnimatePresence initial={false}>
              {feed.items.map((e) => (
                <motion.li
                  key={e.assignment?.id ?? e.announcement!.id}
                  layout
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <FeedItem courseId={courseId} entry={e} editable={editable} />
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
          <Pager page={feed.page} pages={feed.pages} onChange={setPage} />
          </>
        )}
      </QueryState>
    </Section>
  )
}
