import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'

import { notificationHref } from '@/entities/notification'
import { subscribeLive } from '@/shared/api/live'

/** Слушает новые уведомления: обновляет счётчик и показывает всплывающую подсказку. */
export function LiveNotifications() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  useEffect(
    () =>
      subscribeLive((msg) => {
        if (msg.type === 'ready' || msg.type === 'notification') {
          queryClient.setQueryData(['notifications', 'unread-count'], { unread_count: msg.unread_count })
        }
        if (msg.type === 'notification') {
          const n = msg.notification
          queryClient.invalidateQueries({ queryKey: ['notifications'], refetchType: 'active' })
          toast(n.title, {
            description: n.course ? `${n.text} · ${n.course.name}` : n.text,
            action: { label: 'Открыть', onClick: () => navigate(notificationHref(n)) },
          })
        }
        if (msg.type === 'resync') queryClient.invalidateQueries({ queryKey: ['notifications'] })
      }),
    [queryClient, navigate],
  )
  return null
}
