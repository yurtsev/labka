import { Link } from 'react-router'

import { Button } from '@/shared/ui/button'
import { CompassIcon } from '@/shared/ui/icons'
import { EmptyState } from '@/shared/ui/kit/query-state'

export function NotFoundPage() {
  return (
    <div className="grid min-h-[60svh] place-items-center">
      <EmptyState icon={<CompassIcon />} title="Такой страницы нет" description="Возможно, ссылка устарела или в адресе опечатка.">
        <Button asChild variant="outline">
          <Link to="/">На главную</Link>
        </Button>
      </EmptyState>
    </div>
  )
}
