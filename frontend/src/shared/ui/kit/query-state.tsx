import type { UseQueryResult } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { ApiError } from '@/shared/api'
import { Button } from '@/shared/ui/button'
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/shared/ui/empty'
import { CloudOffIcon, RotateCwIcon } from '@/shared/ui/icons'

type Props<T> = {
  query: UseQueryResult<T>
  /** Заглушка на время загрузки — скелет будущего содержимого. */
  loading: ReactNode
  /** Показать пустое состояние, если данных нет. */
  isEmpty?: (data: T) => boolean
  empty?: ReactNode
  children: (data: T) => ReactNode
}

/** Загрузка, ошибка, пусто или данные — единый каркас для экранов с запросом. */
export function QueryState<T>({ query, loading, isEmpty, empty, children }: Props<T>) {
  if (query.isPending) return <>{loading}</>
  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  if (isEmpty?.(query.data) && empty) return <>{empty}</>
  return <>{children(query.data)}</>
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof ApiError ? error.message : 'Не удалось загрузить данные'
  const notFound = error instanceof ApiError && (error.status === 404 || error.status === 403)
  return (
    <Empty className="flex-none rounded-2xl border border-dashed py-12">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <CloudOffIcon />
        </EmptyMedia>
        <EmptyTitle>{notFound ? 'Страница недоступна' : 'Не получилось загрузить'}</EmptyTitle>
        <EmptyDescription>{message}</EmptyDescription>
      </EmptyHeader>
      {onRetry && !notFound && (
        <EmptyContent>
          <Button variant="outline" onClick={onRetry}>
            <RotateCwIcon data-icon="inline-start" />
            Повторить
          </Button>
        </EmptyContent>
      )}
    </Empty>
  )
}

export function EmptyState({ icon, title, description, children }: { icon: ReactNode; title: ReactNode; description?: ReactNode; children?: ReactNode }) {
  return (
    <Empty className="flex-none rounded-2xl border border-dashed py-12">
      <EmptyHeader>
        <EmptyMedia variant="icon">{icon}</EmptyMedia>
        <EmptyTitle>{title}</EmptyTitle>
        {description && <EmptyDescription>{description}</EmptyDescription>}
      </EmptyHeader>
      {children && <EmptyContent>{children}</EmptyContent>}
    </Empty>
  )
}
