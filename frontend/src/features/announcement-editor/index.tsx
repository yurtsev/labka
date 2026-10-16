import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { client, unwrap } from '@/shared/api'
import type { FeedAnnouncement } from '@/shared/api'
import { toastError } from '@/shared/lib/form'
import { requiredText } from '@/shared/lib/validation'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/shared/ui/alert-dialog'
import { Button } from '@/shared/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/shared/ui/dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuTrigger } from '@/shared/ui/dropdown-menu'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/shared/ui/field'
import { MoreHorizontalIcon, PencilIcon, Trash2Icon } from '@/shared/ui/icons'
import { Spinner } from '@/shared/ui/spinner'
import { Textarea } from '@/shared/ui/textarea'

const schema = z.object({ text: requiredText('Напишите текст объявления') })
type Values = z.infer<typeof schema>

function AnnouncementDialog({
  courseId,
  announcement,
  open,
  onOpenChange,
  trigger,
}: {
  courseId: string
  announcement?: FeedAnnouncement
  open: boolean
  onOpenChange: (open: boolean) => void
  trigger?: ReactNode
}) {
  const queryClient = useQueryClient()
  const form = useForm<Values>({ resolver: zodResolver(schema), values: { text: announcement?.text ?? '' } })
  const mutation = useMutation({
    mutationFn: (body: Values) =>
      announcement
        ? unwrap(client.PUT('/api/courses/{course_id}/announcements/{announcement_id}', { params: { path: { course_id: courseId, announcement_id: announcement.id } }, body }))
        : unwrap(client.POST('/api/courses/{course_id}/announcements', { params: { path: { course_id: courseId } }, body })),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['course', courseId, 'feed'] })
      toast.success(announcement ? 'Объявление изменено' : 'Объявление опубликовано')
      form.reset({ text: '' })
      onOpenChange(false)
    },
    onError: toastError,
  })
  const error = form.formState.errors.text
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {trigger && <DialogTrigger asChild>{trigger}</DialogTrigger>}
      <DialogContent>
        <form noValidate onSubmit={form.handleSubmit((v) => mutation.mutate(v))} className="flex flex-col gap-6">
          <DialogHeader>
            <DialogTitle>{announcement ? 'Изменить объявление' : 'Новое объявление'}</DialogTitle>
          </DialogHeader>
          <FieldGroup>
            <Field data-invalid={!!error}>
              <FieldLabel htmlFor="announcement-text">Текст</FieldLabel>
              <Textarea id="announcement-text" rows={5} aria-invalid={!!error} {...form.register('text')} />
              <FieldError errors={[error]} />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Отмена
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending && <Spinner data-icon="inline-start" />}
              {announcement ? 'Сохранить' : 'Опубликовать'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function CreateAnnouncementButton({ courseId, children }: { courseId: string; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  return <AnnouncementDialog courseId={courseId} open={open} onOpenChange={setOpen} trigger={children} />
}

/** Меню объявления в ленте: изменить или удалить. */
export function AnnouncementActions({ courseId, announcement }: { courseId: string; announcement: FeedAnnouncement }) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const remove = useMutation({
    mutationFn: () =>
      unwrap(client.DELETE('/api/courses/{course_id}/announcements/{announcement_id}', { params: { path: { course_id: courseId, announcement_id: announcement.id } } })),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['course', courseId, 'feed'] })
      toast.success('Объявление удалено')
    },
    onError: toastError,
  })
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon-sm" aria-label="Действия с объявлением">
            <MoreHorizontalIcon />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuGroup>
            <DropdownMenuItem onSelect={() => setEditing(true)}>
              <PencilIcon />
              Изменить
            </DropdownMenuItem>
            <DropdownMenuItem variant="destructive" onSelect={() => setDeleting(true)}>
              <Trash2Icon />
              Удалить
            </DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
      <AnnouncementDialog courseId={courseId} announcement={announcement} open={editing} onOpenChange={setEditing} />
      <AlertDialog open={deleting} onOpenChange={setDeleting}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить объявление?</AlertDialogTitle>
            <AlertDialogDescription>Студенты больше не увидят его в ленте курса.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Отмена</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={() => remove.mutate()}>
              Удалить
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
