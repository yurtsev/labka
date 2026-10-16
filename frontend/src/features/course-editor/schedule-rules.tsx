import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { courseScheduleQuery, slotsQuery } from '@/entities/schedule'
import { client, unwrap } from '@/shared/api'
import type { Course, Rule } from '@/shared/api'
import { hm } from '@/shared/lib/date'
import { toastError } from '@/shared/lib/form'
import { LESSON_TYPE, REPEAT, WEEKDAYS } from '@/shared/lib/format'
import { Button } from '@/shared/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/shared/ui/dialog'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/shared/ui/field'
import { CalendarPlusIcon, PencilIcon, Trash2Icon } from '@/shared/ui/icons'
import { Input } from '@/shared/ui/input'
import { EmptyState, QueryState } from '@/shared/ui/kit/query-state'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select'
import { Skeleton } from '@/shared/ui/skeleton'
import { Spinner } from '@/shared/ui/spinner'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'

const schema = z.object({
  group_id: z.string().min(1, 'Выберите группу'),
  lesson_type: z.enum(['lab', 'practice']),
  weekday: z.string().min(1),
  slot: z.string().min(1, 'Выберите пару'),
  repeat: z.enum(['weekly', 'even', 'odd']),
  room: z.string().max(64, 'Не длиннее 64 символов'),
})
type Values = z.infer<typeof schema>

function SelectField<T extends string>({ id, label, value, onChange, options, error }: { id: string; label: string; value: T; onChange: (v: T) => void; options: [string, string][]; error?: { message?: string } }) {
  return (
    <Field data-invalid={!!error}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Select value={value} onValueChange={(v) => onChange(v as T)}>
        <SelectTrigger id={id} aria-invalid={!!error} className="w-full">
          <SelectValue placeholder="Выберите" />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            {options.map(([v, l]) => (
              <SelectItem key={v} value={v}>
                {l}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
      <FieldError errors={[error]} />
    </Field>
  )
}

function RuleDialog({ course, rule, onClose }: { course: Course; rule: Rule | 'new' | null; onClose: () => void }) {
  const queryClient = useQueryClient()
  const slots = useQuery(slotsQuery)
  const existing = rule && rule !== 'new' ? rule : null
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    values: rule
      ? {
          group_id: existing?.group.id ?? course.groups[0]?.id ?? '',
          lesson_type: existing?.lesson_type ?? 'lab',
          weekday: String(existing?.weekday ?? 1),
          slot: existing?.slot ? String(existing.slot) : '',
          repeat: existing?.repeat ?? 'weekly',
          room: existing?.room ?? '',
        }
      : undefined,
  })
  const save = useMutation({
    mutationFn: (v: Values) => {
      const body = { group_id: v.group_id, lesson_type: v.lesson_type, weekday: Number(v.weekday), slot: Number(v.slot), repeat: v.repeat, room: v.room.trim() || null }
      return existing
        ? unwrap(client.PUT('/api/courses/{course_id}/schedule/rules/{rule_id}', { params: { path: { course_id: course.id, rule_id: existing.id } }, body }))
        : unwrap(client.POST('/api/courses/{course_id}/schedule/rules', { params: { path: { course_id: course.id } }, body }))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['course', course.id, 'schedule'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      toast.success(existing ? 'Правило изменено' : 'Правило добавлено')
      onClose()
    },
    onError: toastError,
  })
  const { errors } = form.formState
  const c = form.control
  return (
    <Dialog open={rule !== null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <form noValidate onSubmit={form.handleSubmit((v) => save.mutate(v))} className="flex flex-col gap-6">
          <DialogHeader>
            <DialogTitle>{existing ? 'Изменить правило' : 'Новое правило расписания'}</DialogTitle>
            <DialogDescription>Занятие повторяется до конца семестра; время задаёт сетка пар.</DialogDescription>
          </DialogHeader>
          <FieldGroup className="grid gap-x-4 gap-y-6 sm:grid-cols-2">
            <Controller control={c} name="group_id" render={({ field }) => <SelectField id="rule-group" label="Группа" value={field.value} onChange={field.onChange} options={course.groups.map((g) => [g.id, g.name])} error={errors.group_id} />} />
            <Controller control={c} name="lesson_type" render={({ field }) => <SelectField id="rule-type" label="Тип занятия" value={field.value} onChange={field.onChange} options={Object.entries(LESSON_TYPE)} />} />
            <Controller control={c} name="weekday" render={({ field }) => <SelectField id="rule-weekday" label="День недели" value={field.value} onChange={field.onChange} options={WEEKDAYS.slice(0, 6).map((d, i) => [String(i + 1), d])} />} />
            <Controller
              control={c}
              name="slot"
              render={({ field }) => (
                <SelectField id="rule-slot" label="Пара" value={field.value} onChange={field.onChange} error={errors.slot} options={(slots.data?.items ?? []).map((s) => [String(s.number), `${s.number} пара, ${hm(s.starts_at)}–${hm(s.ends_at)}`])} />
              )}
            />
            <Controller control={c} name="repeat" render={({ field }) => <SelectField id="rule-repeat" label="Повтор" value={field.value} onChange={field.onChange} options={Object.entries(REPEAT)} />} />
            <Field data-invalid={!!errors.room}>
              <FieldLabel htmlFor="rule-room">Аудитория</FieldLabel>
              <Input id="rule-room" aria-invalid={!!errors.room} {...form.register('room')} />
              <FieldError errors={[errors.room]} />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose}>
              Отмена
            </Button>
            <Button type="submit" disabled={save.isPending}>
              {save.isPending && <Spinner data-icon="inline-start" />}
              Сохранить
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

/** Правила расписания курса: таблица с добавлением, правкой и удалением. */
export function ScheduleRules({ course }: { course: Course }) {
  const query = useQuery(courseScheduleQuery(course.id))
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState<Rule | 'new' | null>(null)
  const remove = useMutation({
    mutationFn: (id: string) => unwrap(client.DELETE('/api/courses/{course_id}/schedule/rules/{rule_id}', { params: { path: { course_id: course.id, rule_id: id } } })),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['course', course.id, 'schedule'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      toast.success('Правило удалено')
    },
    onError: toastError,
  })
  const readOnly = course.is_archived
  return (
    <div className="flex flex-col gap-4">
      <QueryState
        query={query}
        loading={<Skeleton className="h-40" />}
        isEmpty={(d) => d.rules.length === 0}
        empty={<EmptyState icon={<CalendarPlusIcon />} title="Правил пока нет" description="Добавьте первое — занятия появятся в календаре студентов." />}
      >
        {(s) => (
          <div className="overflow-x-auto rounded-2xl border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Группа</TableHead>
                  <TableHead>Тип</TableHead>
                  <TableHead>День</TableHead>
                  <TableHead>Время</TableHead>
                  <TableHead>Повтор</TableHead>
                  <TableHead>Ауд.</TableHead>
                  <TableHead className="w-20" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {s.rules.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell>{r.group.name}</TableCell>
                    <TableCell>{LESSON_TYPE[r.lesson_type]}</TableCell>
                    <TableCell>{WEEKDAYS[r.weekday - 1]}</TableCell>
                    <TableCell className="tabular-nums">
                      {hm(r.starts_at)}–{hm(r.ends_at)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{REPEAT[r.repeat]}</TableCell>
                    <TableCell>{r.room ?? '—'}</TableCell>
                    <TableCell>
                      {!readOnly && (
                        <span className="flex justify-end">
                          <Button variant="ghost" size="icon-sm" aria-label="Изменить правило" onClick={() => setEditing(r)}>
                            <PencilIcon />
                          </Button>
                          <Button variant="ghost" size="icon-sm" aria-label="Удалить правило" disabled={remove.isPending} onClick={() => remove.mutate(r.id)}>
                            <Trash2Icon />
                          </Button>
                        </span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </QueryState>
      {!readOnly && (
        <Button variant="outline" className="w-fit" disabled={course.groups.length === 0} onClick={() => setEditing('new')}>
          <CalendarPlusIcon data-icon="inline-start" />
          Добавить правило
        </Button>
      )}
      <RuleDialog course={course} rule={editing} onClose={() => setEditing(null)} />
    </div>
  )
}
