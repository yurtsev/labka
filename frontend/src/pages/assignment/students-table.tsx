import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { LateBadge, ProgressView, studentsQuery } from '@/entities/assignment'
import type { Assignment, Group, ProgressStatus } from '@/shared/api'
import { formatDateTimeShort } from '@/shared/lib/date'
import { fullName, STATUS } from '@/shared/lib/format'
import { UsersIcon } from '@/shared/ui/icons'
import { Section, surface, Toolbar } from '@/shared/ui/kit/page-header'
import { Pager } from '@/shared/ui/kit/pager'
import { EmptyState, QueryState } from '@/shared/ui/kit/query-state'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select'
import { Skeleton } from '@/shared/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'

const ALL = 'all'

/** Таблица студентов по заданию с фильтрами; клик по строке открывает проверку. */
export function StudentsTable({ assignment, groups }: { assignment: Assignment; groups: Group[] }) {
  const [group, setGroup] = useState(ALL)
  const [status, setStatus] = useState(ALL)
  const [page, setPage] = useState(1)
  const navigate = useNavigate()
  const query = useQuery({
    ...studentsQuery(assignment.course_id, assignment.id, {
      group_id: group === ALL ? null : group,
      status: status === ALL ? null : (status as ProgressStatus),
    }, page),
    placeholderData: (prev) => prev,
  })
  const s = assignment.summary!

  return (
    <Section
      title="Студенты"
      actions={
        <span className="text-sm text-muted-foreground tabular-nums">
          сдали {s.submitted}/{s.students} · ждут проверки {s.on_review} · приняты {s.accepted}
        </span>
      }
    >
      <Toolbar>
        <Select value={group} onValueChange={(v) => (setGroup(v), setPage(1))}>
          <SelectTrigger className="w-48" aria-label="Группа">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectItem value={ALL}>Все группы</SelectItem>
              {groups.map((g) => (
                <SelectItem key={g.id} value={g.id}>
                  {g.name}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={(v) => (setStatus(v), setPage(1))}>
          <SelectTrigger className="w-48" aria-label="Статус">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectItem value={ALL}>Все статусы</SelectItem>
              {(Object.keys(STATUS) as ProgressStatus[]).map((k) => (
                <SelectItem key={k} value={k}>
                  {STATUS[k][0].toUpperCase() + STATUS[k].slice(1)}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
      </Toolbar>
      <QueryState
        query={query}
        loading={<Skeleton className="h-96 rounded-2xl" />}
        isEmpty={(d) => d.items.length === 0}
        empty={<EmptyState icon={<UsersIcon />} title="Никого не нашлось" description="Попробуйте другой фильтр." />}
      >
        {(data) => (
          <>
          <div className={surface}>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Студент</TableHead>
                  <TableHead className="hidden sm:table-cell">Группа</TableHead>
                  <TableHead>Статус</TableHead>
                  <TableHead className="hidden text-right md:table-cell">Попыток</TableHead>
                  <TableHead className="hidden md:table-cell">Последняя</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((r) => (
                  <TableRow
                    key={r.student_id}
                    tabIndex={0}
                    className="cursor-pointer focus-visible:bg-foreground/8 focus-visible:outline-none"
                    onClick={() => navigate(`students/${r.student_id}`)}
                    onKeyDown={(e) => e.key === 'Enter' && navigate(`students/${r.student_id}`)}
                  >
                    <TableCell className="font-medium">{fullName(r)}</TableCell>
                    <TableCell className="hidden text-muted-foreground sm:table-cell">{r.group_name}</TableCell>
                    <TableCell>
                      <ProgressView progress={r.progress} />
                    </TableCell>
                    <TableCell className="hidden text-right tabular-nums md:table-cell">{r.progress.attempts}</TableCell>
                    <TableCell className="hidden md:table-cell">
                      {r.progress.last_submitted_at ? (
                        <span className="flex items-center gap-2 text-muted-foreground tabular-nums">
                          {formatDateTimeShort(r.progress.last_submitted_at)}
                          {r.progress.last_is_late && <LateBadge />}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <Pager page={data.page} pages={data.pages} total={data.total} onChange={setPage} />
          </>
        )}
      </QueryState>
    </Section>
  )
}
