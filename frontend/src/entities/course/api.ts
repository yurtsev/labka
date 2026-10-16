import { queryOptions } from '@tanstack/react-query'

import { client, unwrap } from '@/shared/api'

export const homeQuery = queryOptions({
  queryKey: ['home'],
  queryFn: () => unwrap(client.GET('/api/home')),
})

export const coursesQuery = (archived: boolean, page = 1, perPage = 20) =>
  queryOptions({
    queryKey: ['courses', { archived }, page, perPage],
    queryFn: () => unwrap(client.GET('/api/courses', { params: { query: { archived, page, per_page: perPage } } })),
  })

export const courseQuery = (courseId: string) =>
  queryOptions({
    queryKey: ['course', courseId],
    queryFn: () => unwrap(client.GET('/api/courses/{course_id}', { params: { path: { course_id: courseId } } })),
  })

export const materialsQuery = (courseId: string) =>
  queryOptions({
    queryKey: ['course', courseId, 'materials'],
    queryFn: () =>
      unwrap(client.GET('/api/courses/{course_id}/materials', { params: { path: { course_id: courseId }, query: { per_page: 100 } } })),
  })

export const availableGroupsQuery = queryOptions({
  queryKey: ['available-groups'],
  queryFn: () => unwrap(client.GET('/api/courses/available-groups', { params: { query: { per_page: 100 } } })),
})

export const examsQuery = (courseId: string) =>
  queryOptions({
    queryKey: ['course', courseId, 'exams'],
    queryFn: () => unwrap(client.GET('/api/courses/{course_id}/exams', { params: { path: { course_id: courseId } } })),
  })
