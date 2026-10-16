import { queryOptions } from '@tanstack/react-query'

import { client, unwrap } from '@/shared/api'

export const myAttemptsQuery = (courseId: string, assignmentId: string) =>
  queryOptions({
    queryKey: ['course', courseId, 'assignment', assignmentId, 'my-attempts'],
    queryFn: () =>
      unwrap(
        client.GET('/api/courses/{course_id}/assignments/{assignment_id}/submissions', {
          params: { path: { course_id: courseId, assignment_id: assignmentId } },
        }),
      ),
  })
