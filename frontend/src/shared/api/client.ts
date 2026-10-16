import createClient from 'openapi-fetch'

import type { paths } from './schema'

/** Ошибка API в формате backend: `{"error": {"code", "message", "details"}}`. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: unknown

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
  }
}

// Эти запросы сами работают с токенами: на их 401 обновлять сессию нельзя.
const AUTH_PATHS = ['/api/auth/login', '/api/auth/register', '/api/auth/refresh', '/api/auth/logout']
const REFRESHED_AT = 'labka:refreshed-at'

let inFlight: Promise<boolean> | null = null

/**
 * Обновляет access-токен по refresh-cookie. Возвращает `true`, если сессия жива.
 *
 * Refresh-токен одноразовый: два одновременных обновления бэкенд считает кражей и отзывает
 * сессию. Поэтому внутри вкладки обновление одно на всех, а между вкладками — по очереди
 * (Web Locks). Вкладка, дождавшаяся очереди, сначала смотрит, не обновила ли токены соседняя
 * после того, как её запрос получил 401, и тогда просто повторяет запрос.
 */
export function refreshSession(failedAt = Date.now()): Promise<boolean> {
  inFlight ??= (async () => {
    const run = async () => {
      if (Number(localStorage.getItem(REFRESHED_AT) ?? 0) >= failedAt) return true
      const res = await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' })
      if (res.ok) localStorage.setItem(REFRESHED_AT, String(Date.now()))
      return res.ok
    }
    try {
      return navigator.locks ? await navigator.locks.request('labka:refresh', run) : await run()
    } catch {
      return false
    } finally {
      inFlight = null
    }
  })()
  return inFlight
}

/** Запрос к API: на 401 обновляет токены и повторяет запрос один раз. */
async function fetchWithRefresh(request: Request): Promise<Response> {
  const retry = request.clone()
  const sentAt = Date.now()
  const response = await fetch(request)
  if (response.status !== 401 || AUTH_PATHS.includes(new URL(request.url).pathname)) return response
  return (await refreshSession(sentAt)) ? fetch(retry) : response
}

export const client = createClient<paths>({
  baseUrl: '',
  credentials: 'include',
  fetch: fetchWithRefresh,
})

type Result<T> = { data?: T; error?: unknown; response: Response }

/** Достаёт данные из ответа openapi-fetch или бросает `ApiError`. */
export async function unwrap<T>(promise: Promise<Result<T>>): Promise<T> {
  let result: Result<T>
  try {
    result = await promise
  } catch {
    throw new ApiError(0, 'network', 'Нет связи с сервером. Проверьте подключение и попробуйте ещё раз')
  }
  const { data, error, response } = result
  if (response.ok) return data as T
  const body = (error ?? {}) as { error?: { code?: string; message?: string; details?: unknown } }
  throw new ApiError(
    response.status,
    body.error?.code ?? `http.${response.status}`,
    body.error?.message ?? 'Что-то пошло не так. Попробуйте ещё раз',
    body.error?.details,
  )
}

/**
 * Загрузка файлов: presigned-форма от backend → файл напрямую в S3 → ключи для записи.
 */
export async function uploadFiles(
  files: File[],
  start: (body: { content_type: string; file_size: number }) => Promise<{ key: string; url: string; fields: Record<string, string> }>,
): Promise<{ key: string; file_name: string }[]> {
  return Promise.all(
    files.map(async (file) => {
      const form = await start({ content_type: file.type || 'application/octet-stream', file_size: file.size })
      const body = new FormData()
      Object.entries(form.fields).forEach(([k, v]) => body.append(k, v))
      body.append('file', file)
      const res = await fetch(form.url, { method: 'POST', body })
      if (!res.ok) throw new ApiError(res.status, 's3.upload_failed', `Не удалось загрузить «${file.name}»`)
      return { key: form.key, file_name: file.name }
    }),
  )
}
