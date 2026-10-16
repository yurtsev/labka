import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router'

import { sessionQuery } from '@/entities/session'
import { ErrorState } from '@/shared/ui/kit/query-state'
import { Spinner } from '@/shared/ui/spinner'

function FullScreen({ children }: { children: ReactNode }) {
  return <div className="grid min-h-svh place-items-center p-4">{children}</div>
}

/** Пускает только вошедших; остальных отправляет на вход и помнит, куда шли. */
export function RequireAuth() {
  const session = useQuery(sessionQuery)
  const location = useLocation()
  if (session.isPending) {
    return (
      <FullScreen>
        <Spinner className="size-6 text-muted-foreground" />
      </FullScreen>
    )
  }
  if (session.isError) {
    return (
      <FullScreen>
        <ErrorState error={session.error} onRetry={() => session.refetch()} />
      </FullScreen>
    )
  }
  if (!session.data) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  return <Outlet />
}

/** Вход и регистрация — только для гостей. */
export function GuestOnly() {
  const session = useQuery(sessionQuery)
  if (session.isPending) return null
  if (session.data) return <Navigate to="/" replace />
  return <Outlet />
}

/** Экраны преподавателя. */
export function TeacherOnly() {
  const session = useQuery(sessionQuery)
  if (session.data?.role !== 'teacher') return <Navigate to="/" replace />
  return <Outlet />
}
