import { useSearchParams } from 'react-router'

/** Номер страницы списка в адресе (`?page=`): сохраняется при обновлении и переходе назад. */
export function usePage(key = 'page'): [number, (page: number) => void] {
  const [params, setParams] = useSearchParams()
  const page = Math.max(1, Number(params.get(key)) || 1)
  const setPage = (next: number) =>
    setParams(
      (prev) => {
        const p = new URLSearchParams(prev)
        if (next <= 1) p.delete(key)
        else p.set(key, String(next))
        return p
      },
      { replace: true },
    )
  return [page, setPage]
}
