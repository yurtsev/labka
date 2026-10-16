import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'

import { CourseForm, type CourseFormValues } from '@/features/course-editor'
import { client, unwrap } from '@/shared/api'
import { toastError } from '@/shared/lib/form'
import { PageHeader } from '@/shared/ui/kit/page-header'

export function NewCoursePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (v: CourseFormValues) => unwrap(client.POST('/api/courses', { body: v })),
    onSuccess: (c) => {
      queryClient.invalidateQueries({ queryKey: ['home'] })
      queryClient.invalidateQueries({ queryKey: ['courses'] })
      toast.success('Курс создан')
      navigate(`/courses/${c.id}`)
    },
    onError: toastError,
  })
  return (
    <>
      <PageHeader title="Новый курс" description="Курс привязывается к текущему семестру. Расписание можно добавить в настройках после создания." />
      <div className="rounded-2xl border bg-card p-6">
        <CourseForm pending={mutation.isPending} submitLabel="Создать курс" onSubmit={(v) => mutation.mutate(v)} />
      </div>
    </>
  )
}
