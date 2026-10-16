import { Link } from 'react-router'

import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from '@/shared/ui/breadcrumb'
import { Skeleton } from '@/shared/ui/skeleton'

/** «Курс › текущая страница» над заголовком экранов внутри курса; пока курс грузится — скелет той же высоты. */
export function CourseBreadcrumbs({ course, current }: { course?: { id: string; name: string }; current: string }) {
  if (!course) return <Skeleton className="h-4 w-56" />
  return (
    <Breadcrumb>
      <BreadcrumbList>
        <BreadcrumbItem>
          <BreadcrumbLink asChild>
            <Link to={`/courses/${course.id}`} className="max-w-80 truncate">{course.name}</Link>
          </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator />
        <BreadcrumbItem>
          <BreadcrumbPage className="max-w-80 truncate">{current}</BreadcrumbPage>
        </BreadcrumbItem>
      </BreadcrumbList>
    </Breadcrumb>
  )
}
