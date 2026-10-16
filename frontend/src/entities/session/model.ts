import { useSuspenseQuery } from '@tanstack/react-query'

import type { User } from '@/shared/api'

import { sessionQuery } from './api'

/** Текущий пользователь внутри защищённых маршрутов: там он всегда есть. */
export function useUser(): User {
  const { data } = useSuspenseQuery(sessionQuery)
  if (!data) throw new Error('useUser вызван вне защищённого маршрута')
  return data
}

export const useIsTeacher = () => useUser().role === 'teacher'
