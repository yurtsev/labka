import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { client, unwrap, uploadFiles } from '@/shared/api'
import { toastError } from '@/shared/lib/form'
import { fileSize } from '@/shared/lib/format'
import type { Material } from '@/shared/api'
import { requiredText, filesSchema } from '@/shared/lib/validation'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/shared/ui/alert-dialog'
import { Button } from '@/shared/ui/button'
import { FileTypeIcon } from '@/shared/ui/file-icons'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/shared/ui/dialog'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/shared/ui/field'
import { PencilIcon, Trash2Icon, XIcon } from '@/shared/ui/icons'
import { Input } from '@/shared/ui/input'
import { FilePicker } from '@/shared/ui/kit/file-picker'
import { Spinner } from '@/shared/ui/spinner'
import { Textarea } from '@/shared/ui/textarea'

const schema = z
  .object({
    title: requiredText('Введите название'),
    text: z.string(),
    files: filesSchema,
  })
  .refine((v) => v.text.trim() || v.files.length, { path: ['text'], message: 'Добавьте текст или файл' })
type Values = z.infer<typeof schema>

export function CreateMaterialButton({ courseId, children }: { courseId: string; children: ReactNode }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { title: '', text: '', files: [] } })
  const mutation = useMutation({
    mutationFn: async (v: Values) => {
      const files = await uploadFiles(v.files, (body) =>
        unwrap(client.POST('/api/courses/{course_id}/materials/uploads', { params: { path: { course_id: courseId } }, body })),
      )
      return unwrap(client.POST('/api/courses/{course_id}/materials', { params: { path: { course_id: courseId } }, body: { title: v.title, text: v.text.trim() || null, files } }))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['course', courseId, 'materials'] })
      toast.success('Материал добавлен')
      form.reset()
      setOpen(false)
    },
    onError: toastError,
  })
  const { errors } = form.formState
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent>
        <form noValidate onSubmit={form.handleSubmit((v) => mutation.mutate(v))} className="flex flex-col gap-6">
          <DialogHeader>
            <DialogTitle>Новый материал</DialogTitle>
            <DialogDescription>Учебник, методичка или ссылки — студенты увидят его на странице курса.</DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field data-invalid={!!errors.title}>
              <FieldLabel htmlFor="material-title">Название</FieldLabel>
              <Input id="material-title" aria-invalid={!!errors.title} {...form.register('title')} />
              <FieldError errors={[errors.title]} />
            </Field>
            <Field data-invalid={!!errors.text}>
              <FieldLabel htmlFor="material-text">Текст</FieldLabel>
              <Textarea id="material-text" rows={4} aria-invalid={!!errors.text} {...form.register('text')} />
              <FieldDescription>Поддерживается markdown: ссылки, списки, код.</FieldDescription>
              <FieldError errors={[errors.text]} />
            </Field>
            <Field data-invalid={!!errors.files}>
              <FieldLabel>Файлы</FieldLabel>
              <Controller control={form.control} name="files" render={({ field }) => <FilePicker value={field.value} onChange={field.onChange} invalid={!!errors.files} />} />
              <FieldError errors={[errors.files]} />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Отмена
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending && <Spinner data-icon="inline-start" />}
              Добавить
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function DeleteMaterialButton({ courseId, materialId, title }: { courseId: string; materialId: string; title: string }) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: () => unwrap(client.DELETE('/api/courses/{course_id}/materials/{material_id}', { params: { path: { course_id: courseId, material_id: materialId } } })),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['course', courseId, 'materials'] })
      toast.success('Материал удалён')
    },
    onError: toastError,
  })
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label={`Удалить «${title}»`}>
          <Trash2Icon />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Удалить «{title}»?</AlertDialogTitle>
          <AlertDialogDescription>Материал удалится вместе со всеми файлами.</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Отмена</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={() => mutation.mutate()}>
            Удалить
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

const editSchema = z.object({
  title: requiredText('Введите название'),
  text: z.string(),
  files: filesSchema,
})
type EditValues = z.infer<typeof editSchema>

/** Правка материала: название и текст, удаление прикреплённых и добавление новых файлов. */
export function EditMaterialButton({ courseId, material }: { courseId: string; material: Material }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [kept, setKept] = useState(material.files)
  const form = useForm<EditValues>({ resolver: zodResolver(editSchema), values: { title: material.title, text: material.text ?? '', files: [] } })
  const mutation = useMutation({
    mutationFn: async (v: EditValues) => {
      const path = { course_id: courseId, material_id: material.id }
      const removed = material.files.filter((f) => !kept.some((k) => k.id === f.id))
      await Promise.all(
        removed.map((f) => unwrap(client.DELETE('/api/courses/{course_id}/materials/{material_id}/files/{file_id}', { params: { path: { ...path, file_id: f.id } } }))),
      )
      const added = await uploadFiles(v.files, (body) => unwrap(client.POST('/api/courses/{course_id}/materials/uploads', { params: { path: { course_id: courseId } }, body })))
      for (const f of added) await unwrap(client.POST('/api/courses/{course_id}/materials/{material_id}/files', { params: { path }, body: f }))
      return unwrap(client.PUT('/api/courses/{course_id}/materials/{material_id}', { params: { path }, body: { title: v.title, text: v.text.trim() || null } }))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['course', courseId, 'materials'] })
      toast.success('Материал сохранён')
      setOpen(false)
    },
    onError: toastError,
  })
  const { errors } = form.formState
  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o)
        if (o) setKept(material.files)
      }}
    >
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label={`Изменить «${material.title}»`}>
          <PencilIcon />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form noValidate onSubmit={form.handleSubmit((v) => mutation.mutate(v))} className="flex flex-col gap-6">
          <DialogHeader>
            <DialogTitle>Изменить материал</DialogTitle>
          </DialogHeader>
          <FieldGroup>
            <Field data-invalid={!!errors.title}>
              <FieldLabel htmlFor="edit-material-title">Название</FieldLabel>
              <Input id="edit-material-title" aria-invalid={!!errors.title} {...form.register('title')} />
              <FieldError errors={[errors.title]} />
            </Field>
            <Field>
              <FieldLabel htmlFor="edit-material-text">Текст</FieldLabel>
              <Textarea id="edit-material-text" rows={4} {...form.register('text')} />
              <FieldDescription>Поддерживается markdown.</FieldDescription>
            </Field>
            <Field data-invalid={!!errors.files}>
              <FieldLabel>Файлы</FieldLabel>
              {kept.length > 0 && (
                <ul className="flex flex-col gap-2">
                  {kept.map((f) => (
                    <li key={f.id} className="flex h-10 items-center gap-2 rounded-lg border pr-1 pl-3 text-sm">
                      <FileTypeIcon fileName={f.file_name} contentType={f.content_type} className="size-5 shrink-0" />
                  <span className="min-w-0 flex-1 truncate">{f.file_name}</span>
                      <span className="text-xs text-muted-foreground tabular-nums">{fileSize(f.file_size)}</span>
                      <Button type="button" variant="ghost" size="icon-sm" aria-label={`Убрать ${f.file_name}`} onClick={() => setKept((fs) => fs.filter((x) => x.id !== f.id))}>
                        <XIcon />
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
              <Controller control={form.control} name="files" render={({ field }) => <FilePicker value={field.value} onChange={field.onChange} invalid={!!errors.files} />} />
              <FieldError errors={[errors.files]} />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Отмена
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending && <Spinner data-icon="inline-start" />}
              Сохранить
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
