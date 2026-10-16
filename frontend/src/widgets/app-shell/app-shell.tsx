import { Suspense, useEffect, useRef, useState } from 'react'
import { Outlet, useLocation, useMatch } from 'react-router'

import { useIsMobile } from '@/shared/lib/hooks/use-mobile'
import { cn } from '@/shared/lib/utils'
import { Sheet, SheetContent, SheetTitle } from '@/shared/ui/sheet'
import { Spinner } from '@/shared/ui/spinner'

import { Footer } from './footer'
import { LiveNotifications } from './live-notifications'
import { NavDrawer } from './nav-drawer'
import { ShellProvider, useShell } from './shell-context'
import { TopBar } from './top-bar'

function Layout() {
  const { pathname } = useLocation()
  const mainRef = useRef<HTMLElement>(null)
  const isMobile = useIsMobile()
  const { panel, togglePanel } = useShell()
  const [sheetOpen, setSheetOpen] = useState(false)
  // Календарь занимает весь экран и держит свою левую панель, как Google Календарь;
  // основная навигация при этом сжимается до полосы иконок.
  const fullScreen = Boolean(useMatch('/calendar'))
  const rail = fullScreen || !panel.app

  // Прокрутка живёт в <main>, а не в окне, поэтому наверх при переходе возвращаем сами.
  useEffect(() => {
    mainRef.current?.scrollTo({ top: 0 })
  }, [pathname])

  return (
    <div className="flex h-dvh flex-col overflow-hidden">
      <TopBar onMenu={isMobile ? () => setSheetOpen(true) : () => togglePanel(fullScreen ? 'calendar' : 'app')} />
      <div className="flex min-h-0 flex-1">
        {!isMobile && (
          <aside className={cn('flex shrink-0 flex-col overflow-hidden transition-[width] duration-300 ease-[cubic-bezier(0.2,0,0,1)]', rail ? 'w-[72px]' : 'w-64')}>
            <NavDrawer rail={rail} />
          </aside>
        )}
        <main
          ref={mainRef}
          id="main"
          className={cn('flex min-w-0 flex-1 flex-col', fullScreen ? 'overflow-hidden' : 'overflow-y-auto md:mr-2 md:rounded-t-3xl md:bg-card/40')}
        >
          {/* Без анимации смены страниц, как в продуктах Google: новая страница просто встаёт на место.
              Содержимое занимает минимум экран, поэтому подвал всегда ниже первого экрана и не прыгает при загрузке. */}
          <div className={cn('flex min-h-full flex-col', fullScreen && 'h-full')}>
            <div className={cn(fullScreen ? 'flex min-h-0 flex-1' : 'mx-auto flex min-h-[calc(100dvh-4rem)] w-full max-w-6xl flex-none flex-col gap-8 px-4 pt-6 pb-12 sm:px-8 sm:pt-8')}>
              <Suspense fallback={<Spinner className="m-auto size-8 text-primary" />}>
                <Outlet />
              </Suspense>
            </div>
            {!fullScreen && <Footer />}
          </div>
        </main>
      </div>
      {isMobile && (
        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <SheetContent side="left" className="w-72 gap-0 rounded-r-2xl border-0 bg-card p-0 pt-2" aria-describedby={undefined}>
            <SheetTitle className="px-7 py-4 text-[22px] font-normal">Labka</SheetTitle>
            <NavDrawer onNavigate={() => setSheetOpen(false)} />
          </SheetContent>
        </Sheet>
      )}
      <LiveNotifications />
    </div>
  )
}

/** Раскладка после входа: шапка, навигация слева, содержимое и подвал. */
export function AppShell() {
  return (
    <ShellProvider>
      <Layout />
    </ShellProvider>
  )
}
