import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useMatch } from 'react-router'

import { notificationsQuery, unreadCountQuery } from '@/entities/notification'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'
import { BellIcon, MenuIcon, ScienceIcon } from '@/shared/ui/icons'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/shared/ui/tooltip'

import { AccountMenu } from './account-menu'
import { useShell } from './shell-context'

/** Шапка как в продуктах Google: меню, логотип, место под элементы страницы, уведомления и аккаунт. */
export function TopBar({ onMenu }: { onMenu: () => void }) {
  const { setSlot } = useShell()
  const unread = useQuery(unreadCountQuery)
  const count = unread.data?.unread_count ?? 0
  const onCalendar = useMatch('/calendar')
  const queryClient = useQueryClient()
  // Список уведомлений грузим, пока курсор на колокольчике: к клику он уже готов.
  const prefetch = () => queryClient.prefetchQuery(notificationsQuery(false, 1))
  // Бургер на оси 36 px — той же, что иконки навигации под ним.
  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center gap-1 bg-background pr-2 pl-3 sm:pr-4">
      <Tooltip>
        <TooltipTrigger asChild>
          <Button variant="ghost" size="icon-lg" aria-label="Главное меню" onClick={onMenu}>
            <MenuIcon />
          </Button>
        </TooltipTrigger>
        <TooltipContent>Главное меню</TooltipContent>
      </Tooltip>
      <Link
        to="/"
        className={cn(
          'mr-2 shrink-0 items-center gap-2 rounded-full py-1 pr-3 pl-1 outline-none focus-visible:ring-2 focus-visible:ring-ring sm:mr-6',
          onCalendar ? 'hidden sm:flex' : 'flex',
        )}
      >
        <span className="grid size-10 place-items-center">
          <ScienceIcon className="size-8 text-primary" />
        </span>
        <span className="text-[22px] leading-none text-foreground/90">{onCalendar ? 'Календарь' : 'Labka'}</span>
      </Link>
      <div ref={setSlot} className="flex min-w-0 flex-1 items-center gap-2" />
      <Tooltip>
        <TooltipTrigger asChild>
          <Button variant="ghost" size="icon-lg" className={cn('relative', onCalendar && 'max-sm:hidden')} asChild>
            <Link to="/notifications" onMouseEnter={prefetch} onFocus={prefetch} aria-label={count ? `Уведомления, непрочитанных: ${count}` : 'Уведомления'}>
              <BellIcon />
              {count > 0 && (
                <span className="absolute top-1.5 right-1.5 grid h-4 min-w-4 place-items-center rounded-full bg-now px-1 text-[11px] leading-none font-medium text-white tabular-nums">
                  {count > 99 ? '99+' : count}
                </span>
              )}
            </Link>
          </Button>
        </TooltipTrigger>
        <TooltipContent>Уведомления</TooltipContent>
      </Tooltip>
      <AccountMenu />
    </header>
  )
}
