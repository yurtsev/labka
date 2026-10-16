import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { availableGroupsQuery } from '@/entities/course'
import { client, unwrap } from '@/shared/api'
import type { Course } from '@/shared/api'
import { toastError } from '@/shared/lib/form'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuTrigger } from '@/shared/ui/dropdown-menu'
import { PlusIcon, XIcon } from '@/shared/ui/icons'

/** Группы курса: добавить из прикреплённых к преподавателю или убрать. */
export function CourseGroups({ course }: { course: Course }) {
  const queryClient = useQueryClient()
  const groups = useQuery(availableGroupsQuery)
  const path = { course_id: course.id }
  const onSuccess = (c: Course) => {
    queryClient.setQueryData(['course', course.id], c)
    queryClient.invalidateQueries({ queryKey: ['home'] })
  }
  const add = useMutation({
    mutationFn: (group_id: string) => unwrap(client.POST('/api/courses/{course_id}/groups', { params: { path }, body: { group_id } })),
    onSuccess: (c) => (onSuccess(c), toast.success('Группа добавлена', { description: 'Студенты получат уведомление.' })),
    onError: toastError,
  })
  const remove = useMutation({
    mutationFn: (group_id: string) => unwrap(client.DELETE('/api/courses/{course_id}/groups/{group_id}', { params: { path: { ...path, group_id } } })),
    onSuccess,
    onError: toastError,
  })
  const free = groups.data?.items.filter((g) => !course.groups.some((x) => x.id === g.id)) ?? []

  return (
    <div className="flex flex-wrap items-center gap-2">
      {course.groups.map((g) => (
        <Badge key={g.id} variant="secondary" className="h-8 gap-1 rounded-lg pr-1 pl-3 text-sm">
          {g.name}
          <Button
            variant="ghost"
            size="icon-xs"
            className="size-5"
            aria-label={`Убрать ${g.name}`}
            disabled={course.is_archived || remove.isPending}
            onClick={() => remove.mutate(g.id)}
          >
            <XIcon />
          </Button>
        </Badge>
      ))}
      {course.groups.length === 0 && <span className="text-sm text-muted-foreground">Групп нет — курс видите только вы</span>}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" disabled={course.is_archived || free.length === 0}>
            <PlusIcon data-icon="inline-start" />
            Группа
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuGroup>
            {free.map((g) => (
              <DropdownMenuItem key={g.id} onSelect={() => add.mutate(g.id)}>
                {g.name}
              </DropdownMenuItem>
            ))}
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
