import { Link } from 'react-router'

const YEAR = new Date().getFullYear()

const LINKS = [
  { to: '/', label: 'Главная' },
  { to: '/calendar', label: 'Календарь' },
  { to: '/courses/archive', label: 'Архив курсов' },
  { to: '/profile', label: 'Профиль' },
]

/** Подвал, как внизу страниц Google: название и короткие ссылки. */
export function Footer() {
  return (
    <footer className="mt-auto border-t px-4 py-4 text-xs leading-4 text-muted-foreground sm:px-8">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <span>© {YEAR} Labka · учебная платформа</span>
        <nav aria-label="Ссылки в подвале">
          <ul className="flex flex-wrap gap-x-5 gap-y-1">
            {LINKS.map((l) => (
              <li key={l.to}>
                <Link to={l.to} className="rounded-sm hover:text-foreground hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none">
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </footer>
  )
}
