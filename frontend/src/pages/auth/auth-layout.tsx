import type { ReactNode } from 'react'

import { ScienceIcon } from '@/shared/ui/icons'

/** Экран гостя по образцу входа в аккаунт Google: карточка, слева заголовок, справа форма. */
export function AuthLayout({ title, description, children, footer }: { title: string; description?: ReactNode; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center px-4 py-8 sm:px-6">
      <main className="grid w-full max-w-[1040px] gap-8 rounded-[28px] bg-card px-6 py-9 sm:px-10 md:grid-cols-2 md:gap-12 md:px-11 md:py-12">
        <div className="flex flex-col gap-4">
          <ScienceIcon className="size-12 text-primary" />
          <h1 className="text-[36px] leading-[44px] font-normal">{title}</h1>
          {description ? (
            <p className="text-base text-foreground/90">{description}</p>
          ) : (
            <p className="text-base text-foreground/90">Labka: занятия, задания и дедлайны в одном месте</p>
          )}
        </div>
        <div className="flex flex-col gap-6 md:pt-24">
          {children}
          {footer && <div className="text-sm text-muted-foreground">{footer}</div>}
        </div>
      </main>
      <footer className="mt-4 flex w-full max-w-[1040px] justify-between px-4 text-xs text-muted-foreground">
        <span>Русский</span>
        <span>Учебная платформа Labka</span>
      </footer>
    </div>
  )
}
