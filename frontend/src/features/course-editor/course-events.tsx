import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { examsQuery } from '@/entities/course'
import { courseScheduleQuery, slotsQuery } from '@/entities/schedule'
import { client, unwrap } from '@/shared/api'
import type { Course } from '@/shared/api'
import { formatDay, hm } from '@/shared/lib/date'
import { toastError } from '@/shared/lib/form'
import { EXAM_TYPE, LESSON_TYPE } from '@/shared/lib/format'
import { Button } from '@/shared/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/shared/ui/dialog'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/shared/ui/field'
import { CalendarPlusIcon, GraduationCapIcon, PencilIcon, Trash2Icon } from '@/shared/ui/icons'
import { Input } from '@/shared/ui/input'
import { EmptyState, QueryState } from '@/shared/ui/kit/query-state'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select'
import { Skeleton } from '@/shared/ui/skeleton'
import { Spinner } from '@/shared/ui/spinner'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'

/** Разовое занятие или экзамен: группа, вид, дата и пара из сетки. */
type Kind = 'extra' | 'exam'
type Item = { id: string; group: { id: string }; kind: string; day: string; slot: number | null; room: string | null }

const schema = z.object({
  group_id: z.string().min(1, 'Выберите группу'),
  kind: z.string().min(1),
  day: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Укажите дату'),
  slot: z.string().min(1, 'Выберите пару'),
  room: z.string().max(64, 'Не длиннее 64 символов'),
})
type Values = z.infer<typeof schema>

const KINDS: Record<Kind, Record<string, string>> = { extra: LESSON_TYPE, exam: EXAM_TYPE }

function Choice({ id, label, value, onChange, options, error }: { id: string; label: string; value: string; onChange: (v: string) => void; options: [string, string][]; error?: { message?: string } }) {
  return (
    <Field data-invalid={!!error}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Select value={value} onValueChange={onChange}>
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

function EventDialog({ course, kind, item, onClose }: { course: Course; kind: Kind; item: Item | 'new' | null; onClose: () => void }) {
  const queryClient = useQueryClient()
  const slots = useQuery(slotsQuery)
  const existing = item && item !== 'new' ? item : null
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    values: item
      ? {
          group_id: existing?.group.id ?? course.groups[0]?.id ?? '',
          kind: existing?.kind ?? Object.keys(KINDS[kind])[0],
          day: existing?.day ?? '',
          slot: existing?.slot ? String(existing.slot) : '',
          room: existing?.room ?? '',
        }
      : undefined,
  })
  const save = useMutation({
    mutationFn: async (v: Values): Promise<unknown> => {
      const base = { group_id: v.group_id, day: v.day, slot: Number(v.slot), room: v.room.trim() || null }
      const p = { course_id: course.id }
      if (kind === 'extra') {
        const body = { ...base, lesson_type: v.kind as 'lab' | 'practice' }
        return existing
          ? unwrap(client.PUT('/api/courses/{course_id}/schedule/extras/{extra_id}', { params: { path: { ...p, extra_id: existing.id } }, body }))
          : unwrap(client.POST('/api/courses/{course_id}/schedule/extras', { params: { path: p }, body }))
      }
      const body = { ...base, exam_type: v.kind as 'credit' | 'graded_credit' | 'exam' }
      return existing
        ? unwrap(client.PUT('/api/courses/{course_id}/exams/{exam_id}', { params: { path: { ...p, exam_id: existing.id } }, body }))
        : unwrap(client.POST('/api/courses/{course_id}/exams', { params: { path: p }, body }))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['course', course.id] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      toast.success('Сохранено', { description: 'Студенты получили уведомление.' })
      onClose()
    },
    onError: toastError,
  })
  const { errors } = form.formState
  const c = form.control
  const sem = course.semester
  return (
    <Dialog open={item !== null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <form noValidate onSubmit={form.handleSubmit((v) => save.mutate(v))} className="flex flex-col gap-6">
          <DialogHeader>
            <DialogTitle>{kind === 'extra' ? (existing ? 'Изменить занятие' : 'Разовое занятие') : existing ? 'Изменить зачёт или экзамен' : 'Зачёт или экзамен'}</DialogTitle>
            <DialogDescription>
              {kind === 'extra' ? 'Дополнительная пара на конкретную дату, пока идут занятия семестра.' : 'У группы в курсе одна форма итогового контроля; дата — в пределах семестра, включая сессию.'}
            </DialogDescription>
          </DialogHeader>
          <FieldGroup className="grid gap-x-4 gap-y-6 sm:grid-cols-2">
            <Controller control={c} name="group_id" render={({ field }) => <Choice id="ev-group" label="Группа" value={field.value} onChange={field.onChange} options={course.groups.map((g) => [g.id, g.name])} error={errors.group_id} />} />
            <Controller control={c} name="kind" render={({ field }) => <Choice id="ev-kind" label={kind === 'extra' ? 'Тип занятия' : 'Форма контроля'} value={field.value} onChange={field.onChange} options={Object.entries(KINDS[kind])} />} />
            <Field data-invalid={!!errors.day}>
              <FieldLabel htmlFor="ev-day">Дата</FieldLabel>
              <Input id="ev-day" type="date" min={sem.starts_on} max={kind === 'extra' ? sem.classes_end_on : sem.ends_on} aria-invalid={!!errors.day} {...form.register('day')} />
              <FieldError errors={[errors.day]} />
            </Field>
            <Controller
              control={c}
              name="slot"
              render={({ field }) => (
                <Choice id="ev-slot" label="Пара" value={field.value} onChange={field.onChange} error={errors.slot} options={(slots.data?.items ?? []).map((s) => [String(s.number), `${s.number} пара, ${hm(s.starts_at)}–${hm(s.ends_at)}`])} />
              )}
            />
            <Field data-invalid={!!errors.room}>
              <FieldLabel htmlFor="ev-room">Аудитория</FieldLabel>
              <Input id="ev-room" aria-invalid={!!errors.room} {...form.register('room')} />
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

function EventTable({ course, kind, items, empty }: { course: Course; kind: Kind; items: Item[]; empty: ReactNode }) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState<Item | 'new' | null>(null)
  const remove = useMutation({
    mutationFn: (id: string) =>
      kind === 'extra'
        ? unwrap(client.DELETE('/api/courses/{course_id}/schedule/extras/{extra_id}', { params: { path: { course_id: course.id, extra_id: id } } }))
        : unwrap(client.DELETE('/api/courses/{course_id}/exams/{exam_id}', { params: { path: { course_id: course.id, exam_id: id } } })),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['course', course.id] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      toast.success('Удалено')
    },
    onError: toastError,
  })
  const groupName = (id: string) => course.groups.find((g) => g.id === id)?.name ?? '—'
  const readOnly = course.is_archived
  return (
    <div className="flex flex-col gap-4">
      {items.length === 0 ? (
        empty
      ) : (
        <div className="overflow-x-auto rounded-2xl border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Группа</TableHead>
                <TableHead>{kind === 'extra' ? 'Тип' : 'Форма'}</TableHead>
                <TableHead>Дата</TableHead>
                <TableHead>Пара</TableHead>
                <TableHead>Ауд.</TableHead>
                <TableHead className="w-20" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((x) => (
                <TableRow key={x.id}>
                  <TableCell>{groupName(x.group.id)}</TableCell>
                  <TableCell>{KINDS[kind][x.kind]}</TableCell>
                  <TableCell>{formatDay(x.day)}</TableCell>
                  <TableCell className="tabular-nums">{x.slot ?? '—'}</TableCell>
                  <TableCell>{x.room ?? '—'}</TableCell>
                  <TableCell>
                    {!readOnly && (
                      <span className="flex justify-end">
                        <Button variant="ghost" size="icon-sm" aria-label="Изменить" onClick={() => setEditing(x)}>
                          <PencilIcon />
                        </Button>
                        <Button variant="ghost" size="icon-sm" aria-label="Удалить" disabled={remove.isPending} onClick={() => remove.mutate(x.id)}>
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
      {!readOnly && (
        <Button variant="outline" className="w-fit" disabled={course.groups.length === 0} onClick={() => setEditing('new')}>
          {kind === 'extra' ? <CalendarPlusIcon data-icon="inline-start" /> : <GraduationCapIcon data-icon="inline-start" />}
          {kind === 'extra' ? 'Добавить занятие' : 'Назначить'}
        </Button>
      )}
      <EventDialog course={course} kind={kind} item={editing} onClose={() => setEditing(null)} />
    </div>
  )
}

export function ExtraLessons({ course }: { course: Course }) {
  const query = useQuery(courseScheduleQuery(course.id))
  return (
    <QueryState query={query} loading={<Skeleton className="h-24" />}>
      {(s) => (
        <EventTable
          course={course}
          kind="extra"
          items={s.extras.map((e) => ({ id: e.id, group: e.group, kind: e.lesson_type, day: e.day, slot: e.slot, room: e.room }))}
          empty={<EmptyState icon={<CalendarPlusIcon />} title="Разовых занятий нет" description="Например, перенос пары или дополнительная консультация." />}
        />
      )}
    </QueryState>
  )
}

export function CourseExams({ course }: { course: Course }) {
  const query = useQuery(examsQuery(course.id))
  return (
    <QueryState query={query} loading={<Skeleton className="h-24" />}>
      {(d) => (
        <EventTable
          course={course}
          kind="exam"
          items={d.items.map((x) => ({ id: x.id, group: x.group, kind: x.exam_type, day: x.day, slot: x.slot, room: x.room }))}
          empty={<EmptyState icon={<GraduationCapIcon />} title="Итоговый контроль не назначен" description="Назначьте группе зачёт, дифференцированный зачёт или экзамен." />}
        />
      )}
    </QueryState>
  )
}
