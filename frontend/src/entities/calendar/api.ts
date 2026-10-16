import { queryOptions } from '@tanstack/react-query'

import { client, unwrap } from '@/shared/api'
import type { CalendarView } from '@/shared/api'

export const calendarQuery = (view: CalendarView, date: string) =>
  queryOptions({
    queryKey: ['calendar', view, date],
    queryFn: () => unwrap(client.GET('/api/calendar', { params: { query: { view, date } } })),
    placeholderData: (prev) => prev,
  })
