import { useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'motion/react'

import { ProgressView } from '@/entities/assignment'
import { AttemptCard, myAttemptsQuery } from '@/entities/submission'
import { SubmitAttemptForm } from '@/features/submit-attempt'
import type { Assignment } from '@/shared/api'
import { ArchiveIcon, CircleCheckIcon, LockIcon, SendIcon } from '@/shared/ui/icons'
import { Section } from '@/shared/ui/kit/page-header'
import { EmptyState, QueryState } from '@/shared/ui/kit/query-state'
import { Skeleton } from '@/shared/ui/skeleton'

function Blocked({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      {icon}
      {text}
    </div>
  )
}

/** «Моя сдача»: статус, форма новой попытки и история. */
export function StudentSubmission({ assignment, archived }: { assignment: Assignment; archived: boolean }) {
  const history = useQuery(myAttemptsQuery(assignment.course_id, assignment.id))
  const progress = assignment.my_progress!
  const passed = assignment.deadline_at !== null && new Date(assignment.deadline_at) < new Date()

  // Можно ли сдавать, решает бэк (`my_progress.can_submit`); здесь — только какое объяснение показать.
  let blocked: React.ReactNode = null
  if (archived) blocked = <Blocked icon={<ArchiveIcon className="size-4 text-muted-foreground" />} text="Курс в архиве — сдача недоступна" />
  else if (progress.status === 'accepted') blocked = <Blocked icon={<CircleCheckIcon className="size-4 text-task" />} text="Работа принята" />
  else if (!progress.can_submit)
    blocked = (
      <Blocked
        icon={<LockIcon className="size-4 text-exam" />}
        text={progress.attempts > 0 ? 'Срок сдачи истёк: новая попытка возможна, только если преподаватель вернёт работу на доработку' : 'Срок сдачи истёк'}
      />
    )

  return (
    <>
    <Section title="Моя сдача" actions={<ProgressView progress={progress} />}>
      <div className="flex flex-col gap-6 rounded-2xl border bg-card p-6">
        {blocked ?? (
          <SubmitAttemptForm courseId={assignment.course_id} assignmentId={assignment.id} late={passed && assignment.deadline_type === 'soft'} />
        )}
      </div>
    </Section>
    <Section title="История попыток">
      <QueryState
        query={history}
        loading={<Skeleton className="h-24" />}
        isEmpty={(d) => d.items.length === 0}
        empty={<EmptyState icon={<SendIcon />} title="Попыток пока нет" description="Отправленные работы и ответы преподавателя появятся здесь." />}
      >
        {(d) => (
          <ul className="flex flex-col gap-4">
            <AnimatePresence initial={false}>
              {d.items.map((a) => (
                <motion.li key={a.id} layout initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.22 }}>
                  <AttemptCard attempt={a} />
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        )}
      </QueryState>
    </Section>
    </>
  )
}
