import { queryOptions } from '@tanstack/react-query'

import { ApiError, client, unwrap } from '@/shared/api'
import type { User } from '@/shared/api'

export const sessionQuery = queryOptions({
  queryKey: ['session'],
  queryFn: async (): Promise<User | null> => {
    try {
      return await unwrap(client.GET('/api/auth/me'))
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return null
      throw e
    }
  },
  staleTime: Infinity,
  retry: false,
})

export const login = (body: { email: string; password: string }) => unwrap(client.POST('/api/auth/login', { body }))

export const register = (body: {
  email: string
  group_code: string
  last_name: string
  first_name: string
  middle_name?: string | null
  password: string
}) => unwrap(client.POST('/api/auth/register', { body }))

export const logout = () => unwrap(client.POST('/api/auth/logout'))

export const changePassword = (body: { current_password: string; new_password: string }) =>
  unwrap(client.POST('/api/auth/password', { body }))
