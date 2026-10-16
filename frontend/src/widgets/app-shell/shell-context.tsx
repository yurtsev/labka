import { createContext, useContext, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

export type PanelKey = 'app' | 'calendar'

type Shell = {
  /** Развёрнута ли левая панель: навигация приложения или панель календаря. */
  panel: Record<PanelKey, boolean>
  togglePanel: (key: PanelKey) => void
  /** Узел в шапке, куда страница может вынести свои элементы управления. */
  slot: HTMLElement | null
  setSlot: (el: HTMLElement | null) => void
}

const ShellContext = createContext<Shell | null>(null)

const read = (key: PanelKey) => {
  try {
    return localStorage.getItem(`labka:panel:${key}`) !== 'closed'
  } catch {
    return true
  }
}

export function ShellProvider({ children }: { children: ReactNode }) {
  const [panel, setPanel] = useState(() => ({ app: read('app'), calendar: read('calendar') }))
  const [slot, setSlot] = useState<HTMLElement | null>(null)
  const togglePanel = (key: PanelKey) =>
    setPanel((prev) => {
      try {
        localStorage.setItem(`labka:panel:${key}`, prev[key] ? 'closed' : 'open')
      } catch {
        /* хранилище недоступно — состояние живёт до перезагрузки */
      }
      return { ...prev, [key]: !prev[key] }
    })
  return <ShellContext value={{ panel, togglePanel, slot, setSlot }}>{children}</ShellContext>
}

export function useShell() {
  const ctx = useContext(ShellContext)
  if (!ctx) throw new Error('useShell вне ShellProvider')
  return ctx
}

/** Выносит элементы управления страницы в шапку, как у Google Календаря. */
export function HeaderPortal({ children }: { children: ReactNode }) {
  const { slot } = useShell()
  return slot ? createPortal(children, slot) : null
}
