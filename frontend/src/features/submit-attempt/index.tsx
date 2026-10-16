import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Controller, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { client, unwrap, uploadFiles } from '@/shared/api'
import { toastError } from '@/shared/lib/form'
import { Alert, AlertTitle } from '@/shared/ui/alert'
import { Button } from '@/shared/ui/button'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/shared/ui/field'
import { filesSchema } from '@/shared/lib/validation'
import { SendIcon, TriangleAlertIcon } from '@/shared/ui/icons'
import { FilePicker } from '@/shared/ui/kit/file-picker'
import { Spinner } from '@/shared/ui/spinner'
import { Textarea } from '@/shared/ui/textarea'

const schema = z
  .object({
    comment: z.string(),
    files: filesSchema,
  })
  .refine((v) => v.comment.trim() || v.files.length, { path: ['files'], message: 'Прикрепите файл или напишите комментарий' })
type Values = z.infer<typeof schema>

/** Отправка попытки: файлы грузятся в хранилище только по кнопке, затем создаётся попытка. */
export function SubmitAttemptForm({ courseId, assignmentId, late }: { courseId: string; assignmentId: string; late: boolean }) {
  const queryClient = useQueryClient()
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { comment: '', files: [] } })
  const mutation = useMutation({
    mutationFn: async (v: Values) => {
      const path = { course_id: courseId, assignment_id: assignmentId }
      const files = await uploadFiles(v.files, (body) =>
        unwrap(client.POST('/api/courses/{course_id}/assignments/{assignment_id}/submissions/uploads', { params: { path }, body })),
      )
      return unwrap(
        client.POST('/api/courses/{course_id}/assignments/{assignment_id}/submissions', { params: { path }, body: { comment: v.comment.trim() || null, files } }),
      )
    },
    onSuccess: (attempt) => {
      queryClient.invalidateQueries({ queryKey: ['course', courseId] })
      queryClient.invalidateQueries({ queryKey: ['home'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      toast.success(`Попытка ${attempt.number} отправлена`, { description: 'Преподаватель получил уведомление.' })
      form.reset()
    },
    onError: toastError,
  })
  const { errors } = form.formState
  const pending = mutation.isPending
  return (
    <form noValidate onSubmit={form.handleSubmit((v) => mutation.mutate(v))}>
      <FieldGroup>
        {late && (
          <Alert className="border-deadline/40 text-deadline">
            <TriangleAlertIcon />
            <AlertTitle>Мягкий дедлайн прошёл — попытка будет отмечена как просроченная</AlertTitle>
          </Alert>
        )}
        <Field data-invalid={!!errors.comment}>
          <FieldLabel htmlFor="attempt-comment">Комментарий</FieldLabel>
          <Textarea
            id="attempt-comment"
            rows={3}
            placeholder="Что сделано, ссылка на репозиторий, вопросы преподавателю"
            disabled={pending}
            aria-invalid={!!errors.comment}
            {...form.register('comment')}
          />
          <FieldError errors={[errors.comment]} />
        </Field>
        <Field data-invalid={!!errors.files}>
          <FieldLabel>Файлы</FieldLabel>
          <Controller
            control={form.control}
            name="files"
            render={({ field }) => <FilePicker value={field.value} onChange={field.onChange} disabled={pending} invalid={!!errors.files} />}
          />
          <FieldError errors={[errors.files]} />
        </Field>
        <Button type="submit" className="w-fit" disabled={pending}>
          {pending ? <Spinner data-icon="inline-start" /> : <SendIcon data-icon="inline-start" />}
          {pending ? 'Отправляем…' : 'Отправить'}
        </Button>
      </FieldGroup>
    </form>
  )
}
