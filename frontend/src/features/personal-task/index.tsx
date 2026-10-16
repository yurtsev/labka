import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { client, unwrap } from '@/shared/api'
import { toastError } from '@/shared/lib/form'
import { requiredText } from '@/shared/lib/validation'
import { Button } from '@/shared/ui/button'
import { Checkbox } from '@/shared/ui/checkbox'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/shared/ui/dialog'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/shared/ui/field'
import { Trash2Icon } from '@/shared/ui/icons'
import { Input } from '@/shared/ui/input'
import { Spinner } from '@/shared/ui/spinner'

const schema = z.object({
  title: requiredText('Назовите задачу').pipe(z.string().max(200, 'Не длиннее 200 символов')),
  due_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Укажите дату'),
  due_time: z.string(),
})
type Values = z.infer<typeof schema>

export type TaskDraft = { id?: string; title: string; due_date: string; due_time: string | null; is_done?: boolean }

const invalidate = (qc: ReturnType<typeof useQueryClient>) => qc.invalidateQueries({ queryKey: ['calendar'] })

/** Создание и правка личной задачи; у существующей — ещё «сделано» и удаление. */
export function TaskDialog({ task, onClose }: { task: TaskDraft | null; onClose: () => void }) {
  const queryClient = useQueryClient()
  const editing = Boolean(task?.id)
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    values: task ? { title: task.title, due_date: task.due_date, due_time: task.due_time?.slice(0, 5) ?? '' } : undefined,
  })

  const save = useMutation({
    mutationFn: (v: Values) => {
      const body = { title: v.title, due_date: v.due_date, due_time: v.due_time ? `${v.due_time}:00` : null }
      return task?.id
        ? unwrap(client.PUT('/api/personal-tasks/{task_id}', { params: { path: { task_id: task.id } }, body }))
        : unwrap(client.POST('/api/personal-tasks', { body }))
    },
    onSuccess: () => {
      invalidate(queryClient)
      toast.success(editing ? 'Задача сохранена' : 'Задача добавлена')
      onClose()
    },
    onError: toastError,
  })
  const remove = useMutation({
    mutationFn: () => unwrap(client.DELETE('/api/personal-tasks/{task_id}', { params: { path: { task_id: task!.id! } } })),
    onSuccess: () => {
      invalidate(queryClient)
      toast.success('Задача удалена')
      onClose()
    },
    onError: toastError,
  })
  const toggle = useToggleTask()

  const { errors } = form.formState
  return (
    <Dialog open={task !== null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-md">
        <form noValidate onSubmit={form.handleSubmit((v) => save.mutate(v))} className="flex flex-col gap-6">
          <DialogHeader>
            <DialogTitle>{editing ? 'Личная задача' : 'Новая задача'}</DialogTitle>
            <DialogDescription>Видна только вам, в календаре — зелёным.</DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field data-invalid={!!errors.title}>
              <FieldLabel htmlFor="task-title">Что сделать</FieldLabel>
              <Input id="task-title" autoFocus aria-invalid={!!errors.title} {...form.register('title')} />
              <FieldError errors={[errors.title]} />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field data-invalid={!!errors.due_date}>
                <FieldLabel htmlFor="task-date">Дата</FieldLabel>
                <Input id="task-date" type="date" aria-invalid={!!errors.due_date} {...form.register('due_date')} />
                <FieldError errors={[errors.due_date]} />
              </Field>
              <Field>
                <FieldLabel htmlFor="task-time">Время</FieldLabel>
                <Input id="task-time" type="time" {...form.register('due_time')} />
                <FieldDescription>Необязательно</FieldDescription>
              </Field>
            </div>
            {editing && (
              <Field orientation="horizontal">
                <Checkbox
                  id="task-done"
                  checked={task!.is_done}
                  onCheckedChange={(c) => {
                    toggle.mutate({ id: task!.id!, is_done: c === true })
                    onClose()
                  }}
                />
                <FieldLabel htmlFor="task-done" className="font-normal">
                  Сделано
                </FieldLabel>
              </Field>
            )}
          </FieldGroup>
          <DialogFooter className="sm:justify-between">
            {editing ? (
              <Button type="button" variant="ghost" className="text-destructive" disabled={remove.isPending} onClick={() => remove.mutate()}>
                <Trash2Icon data-icon="inline-start" />
                Удалить
              </Button>
            ) : (
              <span />
            )}
            <div className="flex gap-2">
              <Button type="button" variant="ghost" onClick={onClose}>
                Отмена
              </Button>
              <Button type="submit" disabled={save.isPending}>
                {save.isPending && <Spinner data-icon="inline-start" />}
                Сохранить
              </Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

/** Отметка «сделано» сразу меняет календарь, не дожидаясь ответа сервера. */
export function useToggleTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, is_done }: { id: string; is_done: boolean }) =>
      unwrap(client.PATCH('/api/personal-tasks/{task_id}/done', { params: { path: { task_id: id } }, body: { is_done } })),
    onMutate: async ({ id, is_done }) => {
      await queryClient.cancelQueries({ queryKey: ['calendar'] })
      const snapshot = queryClient.getQueriesData({ queryKey: ['calendar'] })
      queryClient.setQueriesData<{ items: { task: { id: string; is_done: boolean } | null }[] }>({ queryKey: ['calendar'] }, (old) =>
        old ? { ...old, items: old.items.map((i) => (i.task?.id === id ? { ...i, task: { ...i.task, is_done } } : i)) } : old,
      )
      return { snapshot }
    },
    onError: (e, _v, ctx) => {
      ctx?.snapshot.forEach(([key, data]) => queryClient.setQueryData(key, data))
      toastError(e)
    },
    onSettled: () => invalidate(queryClient),
  })
}
