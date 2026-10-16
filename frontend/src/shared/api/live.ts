import { refreshSession } from './client'

import type { Notification } from './types'

export type LiveMessage =
  | { type: 'ready'; unread_count: number }
  | { type: 'notification'; notification: Notification; unread_count: number }
  | { type: 'resync' }
  | { type: 'ping' }

/**
 * Поток уведомлений `/api/ws`. При обрыве переподключается с паузой, при истёкшем токене
 * (код 4401) сначала обновляет сессию; после переподключения список нужно перечитать (`resync`).
 */
export function subscribeLive(onMessage: (msg: LiveMessage) => void): () => void {
  let socket: WebSocket | null = null
  let stopped = false
  let retry: ReturnType<typeof setTimeout>
  let delay = 1000

  const connect = () => {
    const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/ws`
    socket = new WebSocket(url)
    socket.onopen = () => (delay = 1000)
    socket.onmessage = (e) => {
      try {
        onMessage(JSON.parse(e.data) as LiveMessage)
      } catch {
        // Неизвестный формат пропускаем.
      }
    }
    socket.onclose = (e) => {
      if (stopped || e.code === 4403) return
      // Истёк access-токен: обновляем сессию и переподключаемся; не вышло — сессии нет.
      if (e.code === 4401) {
        const closedAt = Date.now()
        refreshSession(closedAt).then((ok) => {
          if (ok && !stopped) {
            onMessage({ type: 'resync' })
            connect()
          }
        })
        return
      }
      retry = setTimeout(() => {
        onMessage({ type: 'resync' })
        connect()
      }, delay)
      delay = Math.min(delay * 2, 30_000)
    }
  }
  connect()

  return () => {
    stopped = true
    clearTimeout(retry)
    socket?.close()
  }
}
