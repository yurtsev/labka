
import { Button } from '@/shared/ui/button'
import { ChevronLeftIcon, ChevronRightIcon } from '@/shared/ui/icons'

/** Переключение страниц списка: показывается, только когда страниц больше одной. */
export function Pager({ page, pages, total, onChange }: { page: number; pages: number; total?: number; onChange: (page: number) => void }) {
  if (pages <= 1) return null
  return (
    <nav aria-label="Страницы" className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
      <span className="tabular-nums">
        Страница {page} из {pages}
        {total !== undefined && ` · всего ${total}`}
      </span>
      <div className="flex gap-2">
        <Button variant="outline" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          <ChevronLeftIcon data-icon="inline-start" />
          Назад
        </Button>
        <Button variant="outline" disabled={page >= pages} onClick={() => onChange(page + 1)}>
          Вперёд
          <ChevronRightIcon data-icon="inline-end" />
        </Button>
      </div>
    </nav>
  )
}
