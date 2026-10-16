import { queryOptions } from '@tanstack/react-query'

import { client, unwrap } from '@/shared/api'
import type { QueueItem } from '@/shared/api'

export const queueQuery = (filter: { course_id: string | null; assignment_id: string | null }, page = 1, perPage = 20) =>
  queryOptions({
    queryKey: ['review-queue', filter, page, perPage],
    queryFn: () =>
      unwrap(
        client.GET('/api/reviews/queue', {
          params: {
            query: {
              page,
              per_page: perPage,
              ...(filter.course_id ? { course_id: filter.course_id } : {}),
              ...(filter.assignment_id ? { assignment_id: filter.assignment_id } : {}),
            },
          },
        }),
      ),
  })

export const studentAttemptsQuery = (courseId: string, assignmentId: string, studentId: string) =>
  queryOptions({
    queryKey: ['course', courseId, 'assignment', assignmentId, 'student', studentId],
    queryFn: () =>
      unwrap(
        client.GET('/api/courses/{course_id}/assignments/{assignment_id}/students/{student_id}/submissions', {
          params: { path: { course_id: courseId, assignment_id: assignmentId, student_id: studentId } },
        }),
      ),
  })

export const reviewHref = (q: QueueItem) => `/courses/${q.course.id}/assignments/${q.assignment.id}/students/${q.student.id}`
