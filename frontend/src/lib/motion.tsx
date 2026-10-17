/* Small motion helpers. One easing everywhere; motion only where it shows a change. */
import type { ReactNode } from 'react'
import { create } from 'zustand'

interface Toast { id: number; html: ReactNode; out?: boolean }

export const useToasts = create<{ list: Toast[]; push: (html: ReactNode) => void }>((set, get) => ({
  list: [],
  push: (html) => {
    const id = Date.now() + Math.random()
    set({ list: [...get().list.slice(-2), { id, html }] })
    setTimeout(() => set({ list: get().list.map((t) => (t.id === id ? { ...t, out: true } : t)) }), 5200)
    setTimeout(() => set({ list: get().list.filter((t) => t.id !== id) }), 5700)
  },
}))

export function Toasts() {
  const list = useToasts((s) => s.list)
  return (
    <div className="toasts" aria-live="polite">
      {list.map((t) => (
        <div key={t.id} className={`toast ${t.out ? 'out' : ''}`}>
          {t.html}
        </div>
      ))}
    </div>
  )
}
