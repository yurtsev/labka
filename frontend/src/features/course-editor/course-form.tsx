import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery } from '@tanstack/react-query'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'

import { availableGroupsQuery } from '@/entities/course'
import type { Course } from '@/shared/api'
import { requiredText } from '@/shared/lib/validation'
import { Button } from '@/shared/ui/button'
import { Checkbox } from '@/shared/ui/checkbox'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel, FieldLegend, FieldSet } from '@/shared/ui/field'
import { Input } from '@/shared/ui/input'
import { Skeleton } from '@/shared/ui/skeleton'
import { Spinner } from '@/shared/ui/spinner'
import { Textarea } from '@/shared/ui/textarea'
import { ToggleGroup, ToggleGroupItem } from '@/shared/ui/toggle-group'

const schema = z
  .object({
    name: requiredText('Введите название'),
    description: z.string(),
    grading_note: z.string(),
    scale_type: z.enum(['range', 'binary']),
    min: z.coerce.number<string>().int('Целое число'),
    max: z.coerce.number<string>().int('Целое число'),
    group_ids: z.array(z.string()),
    withGroups: z.boolean(),
  })
  .refine((v) => v.scale_type === 'binary' || v.min < v.max, { path: ['max'], message: 'Максимум должен быть больше минимума' })
  .refine((v) => v.scale_type === 'binary' || v.min >= 0, { path: ['min'], message: 'Не меньше 0' })
  .refine((v) => !v.withGroups || v.group_ids.length > 0, { path: ['group_ids'], message: 'Выберите хотя бы одну группу' })

type Input = z.input<typeof schema>
type Output = z.output<typeof schema>

export type CourseFormValues = {
  name: string
  description: string | null
  grading_note: string | null
  scale: { type: 'range'; min: number; max: number } | { type: 'binary' }
  group_ids: string[]
}

/** Название, описание, шкала и пояснение к оценке; при создании — ещё группы. */
export function CourseForm({
  course,
  pending,
  submitLabel,
  onSubmit,
}: {
  course?: Course
  pending: boolean
  submitLabel: string
  onSubmit: (v: CourseFormValues) => void
}) {
  const withGroups = !course
  const groups = useQuery({ ...availableGroupsQuery, enabled: withGroups })
  const form = useForm<Input, unknown, Output>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: course?.name ?? '',
      description: course?.description ?? '',
      grading_note: course?.grading_note ?? '',
      scale_type: course?.scale.type ?? 'range',
      min: String(course?.scale.min ?? 2),
      max: String(course?.scale.max ?? 5),
      group_ids: [],
      withGroups,
    },
  })
  const { errors } = form.formState
  const scaleType = form.watch('scale_type')

  return (
    <form
      noValidate
      onSubmit={form.handleSubmit((v) =>
        onSubmit({
          name: v.name,
          description: v.description.trim() || null,
          grading_note: v.grading_note.trim() || null,
          scale: v.scale_type === 'binary' ? { type: 'binary' } : { type: 'range', min: v.min, max: v.max },
          group_ids: v.group_ids,
        }),
      )}
    >
      <FieldGroup>
        <Field data-invalid={!!errors.name}>
          <FieldLabel htmlFor="course-name">Название</FieldLabel>
          <Input id="course-name" aria-invalid={!!errors.name} {...form.register('name')} />
          <FieldError errors={[errors.name]} />
        </Field>
        <Field>
          <FieldLabel htmlFor="course-description">Описание</FieldLabel>
          <Textarea id="course-description" rows={3} {...form.register('description')} />
        </Field>
        {withGroups && (
          <FieldSet data-invalid={!!errors.group_ids}>
            <FieldLegend variant="label">Группы</FieldLegend>
            <FieldDescription>Из прикреплённых к вам администратором.</FieldDescription>
            {groups.isPending ? (
              <Skeleton className="h-10" />
            ) : (
              <Controller
                control={form.control}
                name="group_ids"
                render={({ field }) => (
                  <div className="flex min-h-10 flex-wrap items-center gap-x-6 gap-y-4">
                    {groups.data?.items.map((g) => (
                      <Field key={g.id} orientation="horizontal" className="w-auto">
                        <Checkbox
                          id={`group-${g.id}`}
                          checked={field.value.includes(g.id)}
                          onCheckedChange={(c) => field.onChange(c ? [...field.value, g.id] : field.value.filter((x) => x !== g.id))}
                        />
                        <FieldLabel htmlFor={`group-${g.id}`} className="font-normal">
                          {g.name}
                        </FieldLabel>
                      </Field>
                    ))}
                  </div>
                )}
              />
            )}
            <FieldError errors={[errors.group_ids]} />
          </FieldSet>
        )}
        <FieldSet>
          <FieldLegend variant="label">Шкала по умолчанию</FieldLegend>
          <Controller
            control={form.control}
            name="scale_type"
            render={({ field }) => (
              <ToggleGroup type="single" variant="outline" value={field.value} onValueChange={(v) => v && field.onChange(v)} className="w-fit">
                <ToggleGroupItem value="range">
                  Оценка в диапазоне
                </ToggleGroupItem>
                <ToggleGroupItem value="binary">
                  Зачёт / незачёт
                </ToggleGroupItem>
              </ToggleGroup>
            )}
          />
          {scaleType === 'range' && (
            <div className="grid max-w-xs grid-cols-2 gap-4 animate-in fade-in-0 slide-in-from-top-1">
              <Field data-invalid={!!errors.min}>
                <FieldLabel htmlFor="scale-min">От</FieldLabel>
                <Input id="scale-min" type="number" inputMode="numeric" aria-invalid={!!errors.min} {...form.register('min')} />
                <FieldError errors={[errors.min]} />
              </Field>
              <Field data-invalid={!!errors.max}>
                <FieldLabel htmlFor="scale-max">До</FieldLabel>
                <Input id="scale-max" type="number" inputMode="numeric" aria-invalid={!!errors.max} {...form.register('max')} />
                <FieldError errors={[errors.max]} />
              </Field>
            </div>
          )}
        </FieldSet>
        <Field>
          <FieldLabel htmlFor="grading-note">Пояснение к оценке</FieldLabel>
          <Textarea id="grading-note" rows={2} placeholder="например, «3 — работает, 4 — плюс тесты, 5 — плюс защита»" {...form.register('grading_note')} />
        </Field>
        <Button type="submit" className="w-fit" disabled={pending}>
          {pending && <Spinner data-icon="inline-start" />}
          {submitLabel}
        </Button>
      </FieldGroup>
    </form>
  )
}
