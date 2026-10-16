import { queryOptions } from '@tanstack/react-query'

import { client, unwrap } from '@/shared/api'

export const notificationsQuery = (unread: boolean, page = 1) =>
  queryOptions({
    queryKey: ['notifications', { unread }, page],
    queryFn: () => unwrap(client.GET('/api/notifications', { params: { query: { page, per_page: 20, ...(unread ? { unread } : {}) } } })),
  })

export const unreadCountQuery = queryOptions({
  queryKey: ['notifications', 'unread-count'],
  queryFn: () => unwrap(client.GET('/api/notifications/unread-count')),
  refetchInterval: 60_000,
})

export const markRead = (id: string) =>
  unwrap(client.POST('/api/notifications/{notification_id}/read', { params: { path: { notification_id: id } } }))

export const markAllRead = () => unwrap(client.POST('/api/notifications/read-all'))
