import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router'

import { logout, useUser } from '@/entities/session'
import { profileQuery, UserAvatar } from '@/entities/user'
import { toastError } from '@/shared/lib/form'
import { fullName } from '@/shared/lib/format'
import { Button } from '@/shared/ui/button'
import { LogOutIcon } from '@/shared/ui/icons'
import { Popover, PopoverContent, PopoverTrigger } from '@/shared/ui/popover'

const ROLE = { student: 'Студент', teacher: 'Преподаватель' } as const

/** Карточка аккаунта по клику на аватар, как в продуктах Google. */
export function AccountMenu() {
  const user = useUser()
  const profile = useQuery(profileQuery)
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
  const affiliation = profile.data?.group?.name ?? profile.data?.department?.name
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={`Аккаунт: ${fullName(user)}`}
          className="ml-1 grid size-12 place-items-center rounded-full outline-none hover:bg-foreground/8 focus-visible:ring-2 focus-visible:ring-ring"
        >
          <UserAvatar person={user} src={profile.data?.avatar_url} className="size-8" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" sideOffset={4} className="w-[min(22rem,calc(100vw-1rem))] gap-0 rounded-[28px] bg-card p-2">
        <p className="truncate px-4 pt-2 pb-3 text-center text-sm text-muted-foreground">{user.email}</p>
        <div className="flex flex-col items-center gap-3 rounded-3xl bg-background px-4 py-5">
          <UserAvatar person={user} src={profile.data?.avatar_url} className="size-20 text-2xl [&_[data-slot=avatar-fallback]]:text-2xl" />
          <div className="text-center">
            <p className="text-[22px] leading-7">Здравствуйте, {user.first_name}!</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {ROLE[user.role as keyof typeof ROLE] ?? ''}
              {affiliation ? ` · ${affiliation}` : ''}
            </p>
          </div>
          <Button variant="outline" asChild>
            <Link to="/profile">Управление профилем</Link>
          </Button>
        </div>
        <button
          type="button"
          onClick={() => exit.mutate()}
          disabled={exit.isPending}
          className="mt-2 flex w-full items-center gap-3 rounded-full px-5 py-3 text-sm outline-none hover:bg-foreground/8 focus-visible:bg-foreground/12 disabled:opacity-50"
        >
          <LogOutIcon className="size-5 text-muted-foreground" />
          Выйти
        </button>
      </PopoverContent>
    </Popover>
  )
}
