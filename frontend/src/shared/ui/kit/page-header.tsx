import type { ReactNode } from 'react'

import { cn } from '@/shared/lib/utils'

/*
 * Сетка страниц — одна на всё приложение, шаг 8 px:
 * - шапка страницы: строка крошек 24 px (есть всегда, даже пустая — заголовок на любой странице
 *   стоит на одной высоте), отступ 8, строка заголовка 40 px (32/40), описание 14/20;
 * - между блоками страницы 32 px (задаёт каркас), внутри секции заголовок → содержимое 16 px;
 * - поверхности (списки, таблицы, карточки) — скругление 16, рамка, поля строк 24 по бокам.
 */

type Props = {
  title: ReactNode
  /** Строка над заголовком: хлебные крошки или их скелет. */
  crumbs?: ReactNode
  /** Метка слева от заголовка (например, тип задания). */
  leading?: ReactNode
  description?: ReactNode
  actions?: ReactNode
  className?: string
}

export function PageHeader({ title, crumbs, leading, description, actions, className }: Props) {
  return (
    <header className={cn('flex flex-col gap-2', className)}>
      <div className="flex h-6 min-w-0 items-center">{crumbs}</div>
      <div className="flex min-h-10 flex-wrap items-center justify-between gap-x-6 gap-y-4">
        <div className="flex min-w-0 items-center gap-3">
          {leading}
          <h1 className="min-w-0 text-[32px] leading-10 font-normal">{title}</h1>
        </div>
        {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {description && <div className="text-sm leading-5 text-muted-foreground">{description}</div>}
    </header>
  )
}

export function Section({ title, actions, children, className }: { title: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn('flex flex-col gap-4', className)}>
      <div className="flex min-h-10 flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <h2 className="text-[22px] leading-7 font-normal">{title}</h2>
        {actions}
      </div>
      {children}
    </section>
  )
}

/** Поверхность для списков и таблиц: скругление 16, рамка, строки через разделитель. */
export const surface = 'overflow-hidden rounded-2xl border bg-card'

/** Строка списка на поверхности: поля 24 по бокам и 16 сверху и снизу, подсветка по наведению. */
export const row =
  'flex w-full items-center gap-4 px-6 py-4 text-left outline-none transition-colors hover:bg-foreground/4 focus-visible:bg-foreground/8'

/** Ряд фильтров над списком. */
export function Toolbar({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('flex flex-wrap items-center gap-2', className)}>{children}</div>
}
