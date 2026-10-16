import { useQuery } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router'

import { AssignmentTypeBadge, LateBadge } from '@/entities/assignment'
import { coursesQuery } from '@/entities/course'
import { queueQuery, reviewHref } from '@/entities/review'
import { formatDateTimeShort, relativePast } from '@/shared/lib/date'
import { shortName } from '@/shared/lib/format'
import { usePage } from '@/shared/lib/hooks/use-page'
import { Badge } from '@/shared/ui/badge'
import { cn } from '@/shared/lib/utils'
import { InboxIcon } from '@/shared/ui/icons'
import { PageHeader, surface, Toolbar } from '@/shared/ui/kit/page-header'
import { Pager } from '@/shared/ui/kit/pager'
import { EmptyState, QueryState } from '@/shared/ui/kit/query-state'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select'
import { Skeleton } from '@/shared/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'

const ALL = 'all'

export function ReviewQueuePage() {
  const [params, setParams] = useSearchParams()
  const course = params.get('course') ?? ALL
  const assignment = params.get('assignment') ?? ALL
  const [page, setPage] = usePage()
  const courses = useQuery(coursesQuery(false, 1, 100))
  const all = useQuery(queueQuery({ course_id: null, assignment_id: null }, 1, 100))
  const query = useQuery({
    ...queueQuery({ course_id: course === ALL ? null : course, assignment_id: assignment === ALL ? null : assignment }, page),
    placeholderData: (prev) => prev,
  })
  const navigate = useNavigate()

  const assignments = [...new Map((all.data?.items ?? []).filter((q) => course === ALL || q.course.id === course).map((q) => [q.assignment.id, q.assignment])).values()]

  return (
    <>
      <PageHeader title="Проверка" description="Непроверенные попытки по всем курсам, старые сверху." />
      <Toolbar>
        <Select value={course} onValueChange={(v) => setParams(v === ALL ? {} : { course: v })}>
          <SelectTrigger className="w-72" aria-label="Курс">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectItem value={ALL}>Все курсы</SelectItem>
              {courses.data?.items.map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
        <Select value={assignment} onValueChange={(v) => setParams({ ...(course !== ALL && { course }), ...(v !== ALL && { assignment: v }) })}>
          <SelectTrigger className="w-72" aria-label="Задание">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectItem value={ALL}>Все задания</SelectItem>
              {assignments.map((a) => (
                <SelectItem key={a.id} value={a.id}>
                  {a.title}
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
        empty={<EmptyState icon={<InboxIcon />} title="Всё проверено" description="Новые попытки появятся здесь и в уведомлениях." />}
      >
        {(data) => (
          <>
          <div className={cn(surface, 'overflow-x-auto')}>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Студент</TableHead>
                  <TableHead className="hidden lg:table-cell">Курс</TableHead>
                  <TableHead>Задание</TableHead>
                  <TableHead className="text-right">Попытка</TableHead>
                  <TableHead>Отправлена</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((q) => (
                  <TableRow
                    key={q.submission_id}
                    tabIndex={0}
                    className="cursor-pointer focus-visible:bg-foreground/8 focus-visible:outline-none"
                    onClick={() => navigate(reviewHref(q))}
                    onKeyDown={(e) => e.key === 'Enter' && navigate(reviewHref(q))}
                  >
                    <TableCell>
                      <span className="flex flex-col">
                        <span className="font-medium">{shortName(q.student)}</span>
                        <span className="flex items-center gap-2 text-xs text-muted-foreground">
                          {q.group.name}
                          {!q.in_course && <Badge variant="outline" title="Группа студента больше не в курсе">вне курса</Badge>}
                        </span>
                      </span>
                    </TableCell>
                    <TableCell className="hidden text-muted-foreground lg:table-cell">{q.course.name}</TableCell>
                    <TableCell>
                      <span className="flex items-center gap-2">
                        <AssignmentTypeBadge type={q.assignment.type} />
                        <span className="truncate">{q.assignment.title}</span>
                      </span>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{q.number}</TableCell>
                    <TableCell>
                      <span className="flex items-center gap-2 whitespace-nowrap text-muted-foreground" title={formatDateTimeShort(q.created_at)}>
                        {relativePast(q.created_at)}
                        {q.is_late && <LateBadge />}
                      </span>
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
    </>
  )
}
