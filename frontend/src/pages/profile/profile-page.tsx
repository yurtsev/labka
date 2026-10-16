import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'

import { logout } from '@/entities/session'
import { profileQuery } from '@/entities/user'
import { AvatarUpload } from '@/features/avatar-upload'
import { ChangePasswordForm } from '@/features/change-password'
import { fullName } from '@/shared/lib/format'
import { toastError } from '@/shared/lib/form'
import { Button } from '@/shared/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card'
import { LogOutIcon } from '@/shared/ui/icons'
import { PageHeader } from '@/shared/ui/kit/page-header'
import { QueryState } from '@/shared/ui/kit/query-state'
import { Skeleton } from '@/shared/ui/skeleton'

export function ProfilePage() {
  const query = useQuery(profileQuery)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const exit = useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.clear()
      queryClient.setQueryData(['session'], null)
      navigate('/login', { replace: true })
    },
    onError: toastError,
  })

  return (
    <>
      <PageHeader
        title="Профиль"
        actions={
          <Button variant="outline" onClick={() => exit.mutate()} disabled={exit.isPending}>
            <LogOutIcon data-icon="inline-start" />
            Выйти
          </Button>
        }
      />
      <QueryState query={query} loading={<Skeleton className="h-96 rounded-2xl" />}>
        {(p) => (
          <div className="grid items-start gap-8 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>{fullName(p)}</CardTitle>
                <CardDescription>{p.role === 'teacher' ? 'Преподаватель' : 'Студент'}</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-6">
                <AvatarUpload profile={p} />
                <dl className="grid grid-cols-[8rem_1fr] gap-y-2 text-sm leading-5">
                  <dt className="text-muted-foreground">{p.group ? 'Группа' : 'Кафедра'}</dt>
                  <dd>{p.group?.name ?? p.department?.name ?? '—'}</dd>
                  <dt className="text-muted-foreground">Email</dt>
                  <dd className="break-all">{p.email}</dd>
                </dl>
                <p className="text-xs text-muted-foreground">ФИО, группу и почту меняет администратор.</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Смена пароля</CardTitle>
                <CardDescription>После смены все остальные сессии завершатся.</CardDescription>
              </CardHeader>
              <CardContent>
                <ChangePasswordForm />
              </CardContent>
            </Card>
          </div>
        )}
      </QueryState>
    </>
  )
}
