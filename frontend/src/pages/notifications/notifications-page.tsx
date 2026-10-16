import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'motion/react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { markAllRead, markRead, notificationHref, notificationIcon, notificationsQuery } from '@/entities/notification'
import type { Notification } from '@/shared/api'
import { relativePast } from '@/shared/lib/date'
import { toastError } from '@/shared/lib/form'
import { usePage } from '@/shared/lib/hooks/use-page'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'
import { BellOffIcon, CheckCheckIcon } from '@/shared/ui/icons'
import { PageHeader, row, surface } from '@/shared/ui/kit/page-header'
import { Pager } from '@/shared/ui/kit/pager'
import { EmptyState, QueryState } from '@/shared/ui/kit/query-state'
import { Skeleton } from '@/shared/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/shared/ui/tabs'

function Row({ n, onOpen }: { n: Notification; onOpen: () => void }) {
  const Icon = notificationIcon(n.type)
  return (
    <button
      type="button"
      onClick={onOpen}
      className={cn(
        row,
        'items-start',
        n.is_read && 'bg-background',
      )}
    >
      <span className={cn('grid size-10 shrink-0 place-items-center rounded-full', !n.is_read ? 'bg-nav-active text-on-nav-active' : 'bg-surface-high text-muted-foreground')}>
        <Icon className="size-5" aria-hidden />
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-1 py-0.5">
        <span className="flex items-baseline justify-between gap-3">
          <span className={cn('text-sm', !n.is_read ? 'font-medium' : 'text-muted-foreground')}>
            {n.title}
            {!n.is_read && <span className="sr-only">, не прочитано</span>}
          </span>
          <time className="shrink-0 text-xs text-muted-foreground" dateTime={n.created_at}>
            {relativePast(n.created_at)}
          </time>
        </span>
        <span className={cn('text-sm', n.is_read && 'text-muted-foreground')}>{n.text}</span>
        {n.course && <span className="text-xs text-muted-foreground">{n.course.name}</span>}
      </span>
    </button>
  )
}

export function NotificationsPage() {
  const [unread, setUnread] = useState(false)
  const [page, setPage] = usePage()
  const query = useQuery({ ...notificationsQuery(unread, page), placeholderData: (prev) => prev })
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['notifications'] })

  const readAll = useMutation({ mutationFn: markAllRead, onSuccess: refresh, onError: toastError })
  const open = (n: Notification) => {
    if (!n.is_read) markRead(n.id).then(refresh).catch(toastError)
    navigate(notificationHref(n))
  }

  const hasUnread = query.data?.items.some((n) => !n.is_read)
  return (
    <>
      <PageHeader
        title="Уведомления"
        actions={
          <Button variant="outline" disabled={!hasUnread || readAll.isPending} onClick={() => readAll.mutate()}>
            <CheckCheckIcon data-icon="inline-start" />
            Прочитать все
          </Button>
        }
      />
      <Tabs
        value={unread ? 'unread' : 'all'}
        onValueChange={(v) => {
          setUnread(v === 'unread')
          setPage(1)
        }}
      >
        <TabsList className="-mt-4">
          <TabsTrigger value="all">Все</TabsTrigger>
          <TabsTrigger value="unread">Непрочитанные</TabsTrigger>
        </TabsList>
      </Tabs>
      <QueryState
        query={query}
        loading={
<Skeleton className="h-[30rem] rounded-2xl" />
        }
        isEmpty={(d) => d.items.length === 0}
        empty={<EmptyState icon={<BellOffIcon />} title={unread ? 'Всё прочитано' : 'Уведомлений пока нет'} description="Здесь появятся новые задания, проверки и изменения расписания." />}
      >
        {(data) => (
          <>
          <ul className={cn(surface, 'divide-y')}>
            <AnimatePresence initial={false}>
              {data.items.map((n) => (
                <motion.li key={n.id} layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
                  <Row n={n} onOpen={() => open(n)} />
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
          <Pager page={data.page} pages={data.pages} total={data.total} onChange={setPage} />
          </>
        )}
      </QueryState>
    </>
  )
}
