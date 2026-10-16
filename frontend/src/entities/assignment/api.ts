import { queryOptions } from '@tanstack/react-query'

import { client, unwrap } from '@/shared/api'
import type { AssignmentType, ProgressStatus } from '@/shared/api'

export const feedQuery = (courseId: string, type: AssignmentType | null, page = 1) =>
  queryOptions({
    queryKey: ['course', courseId, 'feed', type, page],
    queryFn: () =>
      unwrap(
        client.GET('/api/courses/{course_id}/feed', {
          params: { path: { course_id: courseId }, query: { page, per_page: 20, ...(type ? { type } : {}) } },
        }),
      ),
  })

export const assignmentQuery = (courseId: string, assignmentId: string) =>
  queryOptions({
    queryKey: ['course', courseId, 'assignment', assignmentId],
    queryFn: () =>
      unwrap(
        client.GET('/api/courses/{course_id}/assignments/{assignment_id}', {
          params: { path: { course_id: courseId, assignment_id: assignmentId } },
        }),
      ),
  })

export const studentsQuery = (courseId: string, assignmentId: string, filter: { group_id: string | null; status: ProgressStatus | null }, page = 1) =>
  queryOptions({
    queryKey: ['course', courseId, 'assignment', assignmentId, 'students', filter, page],
    queryFn: () =>
      unwrap(
        client.GET('/api/courses/{course_id}/assignments/{assignment_id}/students', {
          params: {
            path: { course_id: courseId, assignment_id: assignmentId },
            query: {
              page,
              per_page: 20,
              ...(filter.group_id ? { group_id: filter.group_id } : {}),
              ...(filter.status ? { status: filter.status } : {}),
            },
          },
        }),
      ),
  })
