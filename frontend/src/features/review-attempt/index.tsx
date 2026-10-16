import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Controller, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { client, unwrap } from '@/shared/api'
import type { ReviewAttempt, Scale } from '@/shared/api'
import { toastError } from '@/shared/lib/form'
import { Button } from '@/shared/ui/button'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel, FieldLegend, FieldSet } from '@/shared/ui/field'
import { Input } from '@/shared/ui/input'
import { Spinner } from '@/shared/ui/spinner'
import { Textarea } from '@/shared/ui/textarea'
import { ToggleGroup, ToggleGroupItem } from '@/shared/ui/toggle-group'

const makeSchema = (scale: Scale) =>
  z
    .object({
      verdict: z.enum(['accepted', 'revision']),
      score: z.string(),
      passed: z.enum(['', 'yes', 'no']),
      comment: z.string(),
    })
    .superRefine((v, ctx) => {
      if (scale.type === 'range') {
        if (v.score === '') {
          if (v.verdict === 'accepted') ctx.addIssue({ code: 'custom', path: ['score'], message: 'При «принято» оценка обязательна' })
          return
        }
        const n = Number(v.score)
        if (!Number.isInteger(n) || n < scale.min! || n > scale.max!) ctx.addIssue({ code: 'custom', path: ['score'], message: `Целое число от ${scale.min} до ${scale.max}` })
      } else if (v.verdict === 'accepted' && !v.passed) {
        ctx.addIssue({ code: 'custom', path: ['passed'], message: 'При «принято» отметьте зачёт или незачёт' })
      }
    })
type Values = z.infer<ReturnType<typeof makeSchema>>

type Props = {
  path: { course_id: string; assignment_id: string }
  attempt: ReviewAttempt
  scale: Scale
  onSaved: () => void
  next?: { label: string; onClick: () => void }
}

/** Проверка попытки: вердикт, оценка по шкале задания и комментарий. У проверенной — исправление оценки. */
export function ReviewForm({ path, attempt, scale, onSaved, next }: Props) {
  const queryClient = useQueryClient()
  const correcting = attempt.review !== null
  const r = attempt.review
  const form = useForm<Values>({
    resolver: zodResolver(makeSchema(scale)),
    values: {
      verdict: r?.verdict ?? 'accepted',
      score: r?.grade?.score != null ? String(r.grade.score) : '',
      passed: r?.grade?.passed == null ? '' : r.grade.passed ? 'yes' : 'no',
      comment: r?.comment ?? '',
    },
  })
  const mutation = useMutation({
    mutationFn: (v: Values) => {
      const grade = scale.type === 'range' ? (v.score === '' ? undefined : { score: Number(v.score) }) : v.passed ? { passed: v.passed === 'yes' } : undefined
      const p = { params: { path: { ...path, submission_id: attempt.id } } }
      return correcting
        ? unwrap(client.PUT('/api/courses/{course_id}/assignments/{assignment_id}/submissions/{submission_id}/review', { ...p, body: { grade, comment: v.comment.trim() || null } }))
        : unwrap(client.POST('/api/courses/{course_id}/assignments/{assignment_id}/submissions/{submission_id}/review', { ...p, body: { verdict: v.verdict, grade, comment: v.comment.trim() || null } }))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['course', path.course_id] })
      queryClient.invalidateQueries({ queryKey: ['review-queue'] })
      queryClient.invalidateQueries({ queryKey: ['home'] })
      toast.success(correcting ? 'Оценка исправлена' : 'Проверка сохранена', { description: 'Студент получил уведомление.' })
      onSaved()
    },
    onError: toastError,
  })
  const { errors } = form.formState
  const verdict = form.watch('verdict')

  return (
    <form noValidate onSubmit={form.handleSubmit((v) => mutation.mutate(v))}>
      <FieldGroup>
        <FieldSet disabled={correcting}>
          <FieldLegend variant="label">Вердикт</FieldLegend>
          <Controller
            control={form.control}
            name="verdict"
            render={({ field }) => (
              <ToggleGroup type="single" variant="outline" value={field.value} onValueChange={(x) => x && field.onChange(x)} disabled={correcting} className="w-fit">
                <ToggleGroupItem value="accepted">
                  Принято
                </ToggleGroupItem>
                <ToggleGroupItem value="revision">
                  На доработку
                </ToggleGroupItem>
              </ToggleGroup>
            )}
          />
          {correcting && <FieldDescription>Вердикт после проверки не меняется — можно исправить оценку и комментарий.</FieldDescription>}
        </FieldSet>
        {scale.type === 'range' ? (
          <Field data-invalid={!!errors.score} className="max-w-48">
            <FieldLabel htmlFor="review-score">
              Оценка ({scale.min}–{scale.max})
            </FieldLabel>
            <Input id="review-score" type="number" inputMode="numeric" min={scale.min!} max={scale.max!} aria-invalid={!!errors.score} {...form.register('score')} />
            {!errors.score && verdict === 'revision' && <FieldDescription>Необязательно</FieldDescription>}
            <FieldError errors={[errors.score]} />
          </Field>
        ) : (
          <FieldSet data-invalid={!!errors.passed}>
            <FieldLegend variant="label">Результат</FieldLegend>
            <Controller
              control={form.control}
              name="passed"
              render={({ field }) => (
                <ToggleGroup type="single" variant="outline" value={field.value} onValueChange={(x) => field.onChange(x)} className="w-fit">
                  <ToggleGroupItem value="yes">Зачёт</ToggleGroupItem>
                  <ToggleGroupItem value="no">Незачёт</ToggleGroupItem>
                </ToggleGroup>
              )}
            />
            <FieldError errors={[errors.passed]} />
          </FieldSet>
        )}
        <Field data-invalid={!!errors.comment}>
          <FieldLabel htmlFor="review-comment">Комментарий</FieldLabel>
          <Textarea id="review-comment" rows={4} placeholder="Что хорошо, что исправить" aria-invalid={!!errors.comment} {...form.register('comment')} />
          <FieldDescription>Поддерживается markdown.</FieldDescription>
          <FieldError errors={[errors.comment]} />
        </Field>
        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending && <Spinner data-icon="inline-start" />}
            {correcting ? 'Исправить оценку' : 'Сохранить'}
          </Button>
          {next && (
            <Button type="button" variant="outline" onClick={next.onClick}>
              {next.label}
            </Button>
          )}
        </div>
      </FieldGroup>
    </form>
  )
}
