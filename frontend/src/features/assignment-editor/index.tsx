import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { z } from 'zod'

import { client, unwrap, uploadFiles } from '@/shared/api'
import type { Assignment, Course } from '@/shared/api'
import { isoDay, pluralize } from '@/shared/lib/date'
import { toastError } from '@/shared/lib/form'
import { ASSIGNMENT_TYPE, fileSize, scaleLabel } from '@/shared/lib/format'
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
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel, FieldLegend, FieldSet } from '@/shared/ui/field'
import { LockIcon, Trash2Icon, XIcon } from '@/shared/ui/icons'
import { Input } from '@/shared/ui/input'
import { FilePicker } from '@/shared/ui/kit/file-picker'
import { Markdown } from '@/shared/ui/kit/markdown'
import { Spinner } from '@/shared/ui/spinner'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui/tabs'
import { Textarea } from '@/shared/ui/textarea'
import { ToggleGroup, ToggleGroupItem } from '@/shared/ui/toggle-group'

const schema = z
  .object({
    type: z.enum(['lab', 'practice', 'hw']),
    title: requiredText('Введите название'),
    description: z.string(),
    deadline_type: z.enum(['none', 'soft', 'hard']),
    deadline_day: z.string(),
    deadline_time: z.string(),
    scale_mode: z.enum(['course', 'range', 'binary']),
    min: z.string(),
    max: z.string(),
    grading_note: z.string(),
    files: filesSchema,
  })
  .superRefine((v, ctx) => {
    if (v.deadline_type !== 'none') {
      if (!v.deadline_day) ctx.addIssue({ code: 'custom', path: ['deadline_day'], message: 'Укажите дату' })
      if (!v.deadline_time) ctx.addIssue({ code: 'custom', path: ['deadline_time'], message: 'Укажите время' })
    }
    if (v.scale_mode === 'range') {
      const min = Number(v.min)
      const max = Number(v.max)
      if (!Number.isInteger(min) || v.min === '') ctx.addIssue({ code: 'custom', path: ['min'], message: 'Целое число' })
      if (!Number.isInteger(max) || v.max === '') ctx.addIssue({ code: 'custom', path: ['max'], message: 'Целое число' })
      else if (min >= max) ctx.addIssue({ code: 'custom', path: ['max'], message: 'Больше минимума' })
    }
  })
type Values = z.infer<typeof schema>

function toValues(a?: Assignment): Values {
  const own = a?.has_own_scale ? a.scale : null
  return {
    type: a?.type ?? 'lab',
    title: a?.title ?? '',
    description: a?.description ?? '',
    deadline_type: a?.deadline_type ?? 'hard',
    deadline_day: a?.deadline_at?.slice(0, 10) ?? '',
    deadline_time: a?.deadline_at?.slice(11, 16) ?? '23:59',
    scale_mode: own ? own.type : 'course',
    min: String(own?.min ?? 2),
    max: String(own?.max ?? 5),
    grading_note: a?.grading_note ?? '',
    files: [],
  }
}

/** Создание и правка задания. Дедлайн вводится по МСК. */
export function AssignmentForm({ course, assignment }: { course: Course; assignment?: Assignment }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [existingFiles, setExistingFiles] = useState(assignment?.files ?? [])
  const scaleLocked = (assignment?.attempts_total ?? 0) > 0
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: toValues(assignment) })
  const { errors } = form.formState
  const v = form.watch()

  const save = useMutation({
    mutationFn: async (v: Values) => {
      const path = { course_id: course.id }
      const files = await uploadFiles(v.files, (body) => unwrap(client.POST('/api/courses/{course_id}/assignments/uploads', { params: { path }, body })))
      const body = {
        type: v.type,
        title: v.title,
        description: v.description.trim() || null,
        deadline_type: v.deadline_type,
        deadline_at: v.deadline_type === 'none' ? null : `${v.deadline_day}T${v.deadline_time}:00+03:00`,
        scale: v.scale_mode === 'course' ? null : v.scale_mode === 'binary' ? { type: 'binary' as const } : { type: 'range' as const, min: Number(v.min), max: Number(v.max) },
        grading_note: v.grading_note.trim() || null,
      }
      if (!assignment) return unwrap(client.POST('/api/courses/{course_id}/assignments', { params: { path }, body: { ...body, files } }))
      const apath = { ...path, assignment_id: assignment.id }
      const removed = assignment.files.filter((f) => !existingFiles.some((x) => x.id === f.id))
      await Promise.all(removed.map((f) => unwrap(client.DELETE('/api/courses/{course_id}/assignments/{assignment_id}/files/{file_id}', { params: { path: { ...apath, file_id: f.id } } }))))
      for (const f of files) await unwrap(client.POST('/api/courses/{course_id}/assignments/{assignment_id}/files', { params: { path: apath }, body: f }))
      return unwrap(client.PUT('/api/courses/{course_id}/assignments/{assignment_id}', { params: { path: apath }, body }))
    },
    onSuccess: (a) => {
      queryClient.invalidateQueries({ queryKey: ['course', course.id] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      toast.success(assignment ? 'Задание сохранено' : 'Задание опубликовано', { description: 'Студенты получили уведомление.' })
      navigate(`/courses/${course.id}/assignments/${a.id}`)
    },
    onError: toastError,
  })

  return (
    <form noValidate onSubmit={form.handleSubmit((v) => save.mutate(v))} className="rounded-2xl border bg-card p-6">
      <FieldGroup>
        <FieldSet>
          <FieldLegend variant="label">Тип</FieldLegend>
          <Controller
            control={form.control}
            name="type"
            render={({ field }) => (
              <ToggleGroup type="single" variant="outline" value={field.value} onValueChange={(x) => x && field.onChange(x)} className="w-fit">
                {(['lab', 'practice', 'hw'] as const).map((t) => (
                  <ToggleGroupItem key={t} value={t}>
                    {ASSIGNMENT_TYPE[t].long}
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
            )}
          />
        </FieldSet>
        <Field data-invalid={!!errors.title}>
          <FieldLabel htmlFor="a-title">Название</FieldLabel>
          <Input id="a-title" aria-invalid={!!errors.title} {...form.register('title')} />
          <FieldError errors={[errors.title]} />
        </Field>
        <Field>
          <FieldLabel htmlFor="a-description">Описание</FieldLabel>
          <Tabs defaultValue="write">
            <TabsList>
              <TabsTrigger value="write">Текст</TabsTrigger>
              <TabsTrigger value="preview">Предпросмотр</TabsTrigger>
            </TabsList>
            <TabsContent value="write">
              <Textarea id="a-description" rows={8} className="font-mono text-sm" {...form.register('description')} />
            </TabsContent>
            <TabsContent value="preview">
              <div className="min-h-40 rounded-[4px] border border-input px-4 py-3">
                {v.description.trim() ? <Markdown>{v.description}</Markdown> : <p className="text-sm text-muted-foreground">Нечего показывать</p>}
              </div>
            </TabsContent>
          </Tabs>
          <FieldDescription>Markdown: **жирный**, списки, ссылки, `код`.</FieldDescription>
        </Field>
        <Field data-invalid={!!errors.files}>
          <FieldLabel>Файлы</FieldLabel>
          {existingFiles.length > 0 && (
            <ul className="flex flex-col gap-2">
              {existingFiles.map((f) => (
                <li key={f.id} className="flex h-10 items-center gap-2 rounded-lg border pr-1 pl-3 text-sm">
                  <FileTypeIcon fileName={f.file_name} contentType={f.content_type} className="size-5 shrink-0" />
                  <span className="min-w-0 flex-1 truncate">{f.file_name}</span>
                  <span className="text-xs text-muted-foreground tabular-nums">{fileSize(f.file_size)}</span>
                  <Button type="button" variant="ghost" size="icon-sm" aria-label={`Убрать ${f.file_name}`} onClick={() => setExistingFiles((fs) => fs.filter((x) => x.id !== f.id))}>
                    <XIcon />
                  </Button>
                </li>
              ))}
            </ul>
          )}
          <Controller control={form.control} name="files" render={({ field }) => <FilePicker value={field.value} onChange={field.onChange} invalid={!!errors.files} />} />
          <FieldError errors={[errors.files]} />
        </Field>
        <FieldSet>
          <FieldLegend variant="label">Дедлайн</FieldLegend>
          <Controller
            control={form.control}
            name="deadline_type"
            render={({ field }) => (
              <ToggleGroup type="single" variant="outline" value={field.value} onValueChange={(x) => x && field.onChange(x)} className="w-fit">
                <ToggleGroupItem value="none">Без дедлайна</ToggleGroupItem>
                <ToggleGroupItem value="soft">Мягкий</ToggleGroupItem>
                <ToggleGroupItem value="hard">Жёсткий</ToggleGroupItem>
              </ToggleGroup>
            )}
          />
          {v.deadline_type !== 'none' && (
            <div className="grid max-w-sm grid-cols-2 gap-4 animate-in fade-in-0 slide-in-from-top-1">
              <Field data-invalid={!!errors.deadline_day}>
                <FieldLabel htmlFor="a-day">Дата</FieldLabel>
                <Input id="a-day" type="date" min={assignment ? undefined : isoDay()} aria-invalid={!!errors.deadline_day} {...form.register('deadline_day')} />
                <FieldError errors={[errors.deadline_day]} />
              </Field>
              <Field data-invalid={!!errors.deadline_time}>
                <FieldLabel htmlFor="a-time">Время, МСК</FieldLabel>
                <Input id="a-time" type="time" aria-invalid={!!errors.deadline_time} {...form.register('deadline_time')} />
                <FieldError errors={[errors.deadline_time]} />
              </Field>
            </div>
          )}
          <FieldDescription>
            {v.deadline_type === 'soft' && 'После срока сдать можно, но попытка будет отмечена как просроченная.'}
            {v.deadline_type === 'hard' && 'После срока сдать нельзя, если до него не было ни одной попытки.'}
            {v.deadline_type === 'none' && 'Задание не попадёт в календарь и напоминания.'}
          </FieldDescription>
        </FieldSet>
        <FieldSet disabled={scaleLocked}>
          <FieldLegend variant="label" className="flex items-center gap-2">
            Шкала {scaleLocked && <LockIcon className="size-3.5 text-muted-foreground" aria-hidden />}
          </FieldLegend>
          <Controller
            control={form.control}
            name="scale_mode"
            render={({ field }) => (
              <ToggleGroup type="single" variant="outline" disabled={scaleLocked} value={field.value} onValueChange={(x) => x && field.onChange(x)} className="w-fit">
                <ToggleGroupItem value="course">Как в курсе ({scaleLabel(course.scale)})</ToggleGroupItem>
                <ToggleGroupItem value="range">Своя оценка</ToggleGroupItem>
                <ToggleGroupItem value="binary">Зачёт</ToggleGroupItem>
              </ToggleGroup>
            )}
          />
          {v.scale_mode === 'range' && (
            <div className="grid max-w-xs grid-cols-2 gap-4">
              <Field data-invalid={!!errors.min}>
                <FieldLabel htmlFor="a-min">От</FieldLabel>
                <Input id="a-min" type="number" aria-invalid={!!errors.min} {...form.register('min')} />
                <FieldError errors={[errors.min]} />
              </Field>
              <Field data-invalid={!!errors.max}>
                <FieldLabel htmlFor="a-max">До</FieldLabel>
                <Input id="a-max" type="number" aria-invalid={!!errors.max} {...form.register('max')} />
                <FieldError errors={[errors.max]} />
              </Field>
            </div>
          )}
          {scaleLocked && <FieldDescription>Шкалу нельзя изменить: по заданию уже есть попытки студентов.</FieldDescription>}
        </FieldSet>
        <Field>
          <FieldLabel htmlFor="a-note">Пояснение к оценке</FieldLabel>
          <Textarea id="a-note" rows={2} {...form.register('grading_note')} />
        </Field>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-6">
          <div className="flex gap-2">
            <Button type="submit" disabled={save.isPending}>
              {save.isPending && <Spinner data-icon="inline-start" />}
              {assignment ? 'Сохранить' : 'Опубликовать'}
            </Button>
            <Button type="button" variant="ghost" onClick={() => navigate(-1)}>
              Отмена
            </Button>
          </div>
          {assignment && <DeleteAssignment course={course} assignment={assignment} />}
        </div>
      </FieldGroup>
    </form>
  )
}

function DeleteAssignment({ course, assignment }: { course: Course; assignment: Assignment }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const n = assignment.attempts_total ?? 0
  const mutation = useMutation({
    mutationFn: () => unwrap(client.DELETE('/api/courses/{course_id}/assignments/{assignment_id}', { params: { path: { course_id: course.id, assignment_id: assignment.id } } })),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['course', course.id] })
      queryClient.invalidateQueries({ queryKey: ['review-queue'] })
      toast.success('Задание удалено')
      navigate(`/courses/${course.id}`, { replace: true })
    },
    onError: toastError,
  })
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button type="button" variant="ghost" className="text-destructive">
          <Trash2Icon data-icon="inline-start" />
          Удалить
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Удалить «{assignment.title}»?</AlertDialogTitle>
          <AlertDialogDescription>
            {n > 0 ? `Будут удалены все попытки студентов (${pluralize(n, ['попытка', 'попытки', 'попыток'])}) вместе с файлами.` : 'Попыток по заданию нет.'} Это нельзя отменить.
          </AlertDialogDescription>
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
