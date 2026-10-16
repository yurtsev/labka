import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'

import { coursesQuery } from '@/entities/course'
import { usePage } from '@/shared/lib/hooks/use-page'
import { shortName } from '@/shared/lib/format'
import { cn } from '@/shared/lib/utils'
import { ArchiveIcon } from '@/shared/ui/icons'
import { PageHeader, row, surface } from '@/shared/ui/kit/page-header'
import { Pager } from '@/shared/ui/kit/pager'
import { EmptyState, QueryState } from '@/shared/ui/kit/query-state'
import { Skeleton } from '@/shared/ui/skeleton'

const TERM = { autumn: 'Осень', spring: 'Весна' }

export function ArchivePage() {
  const [page, setPage] = usePage()
  const query = useQuery({ ...coursesQuery(true, page), placeholderData: (prev) => prev })
  return (
    <>
      <PageHeader title="Архив курсов" description="Прошедшие курсы доступны только для чтения." />
      <QueryState
        query={query}
        loading={<Skeleton className="h-60 rounded-2xl" />}
        isEmpty={(d) => d.items.length === 0}
        empty={<EmptyState icon={<ArchiveIcon />} title="В архиве пусто" />}
      >
        {(data) => (
          <>
          <ul className={cn(surface, 'divide-y')}>
            {data.items.map((c) => (
              <li key={c.id}>
                <Link to={`/courses/${c.id}`} className={cn(row, 'justify-between')}>
                  <span className="flex min-w-0 flex-col gap-1">
                    <span className="font-medium">{c.name}</span>
                    <span className="text-sm text-muted-foreground">
                      {shortName(c.teacher)} · {c.groups.map((g) => g.name).join(', ')}
                    </span>
                  </span>
                  <span className="shrink-0 text-sm text-muted-foreground">
                    {TERM[c.semester.term]} {c.semester.year}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          <Pager page={data.page} pages={data.pages} total={data.total} onChange={setPage} />
          </>
        )}
      </QueryState>
    </>
  )
}
