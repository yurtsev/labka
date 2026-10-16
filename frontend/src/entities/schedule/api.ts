import { queryOptions } from '@tanstack/react-query'

import { client, unwrap } from '@/shared/api'

export const courseScheduleQuery = (courseId: string) =>
  queryOptions({
    queryKey: ['course', courseId, 'schedule'],
    queryFn: () => unwrap(client.GET('/api/courses/{course_id}/schedule', { params: { path: { course_id: courseId } } })),
  })

export const slotsQuery = queryOptions({
  queryKey: ['slots'],
  queryFn: () => unwrap(client.GET('/api/schedule/slots')),
  staleTime: Infinity,
})
