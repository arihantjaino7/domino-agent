import { Zap } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useStore } from '../lib/store'

/** Manual injection: take a hazard zone offline without the agent (PLAN §10, POST /api/incidents). */
export function InjectMenu() {
  const places = useStore((s) => s.places)
  const inject = useStore((s) => s.inject)
  const busy = useStore((s) => s.busy)
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const esc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', esc)
    }
  }, [])

  const pick = (id: string, label: string) => {
    setOpen(false)
    void inject(id, label)
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="menu"
        disabled={busy || !places}
        onClick={() => setOpen((o) => !o)}
        className="flex h-8 items-center gap-1.5 rounded-md border border-line px-3 text-[13px] text-dim transition-colors hover:bg-raised hover:text-fg focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-50"
      >
        <Zap size={14} strokeWidth={1.75} />
        Inject disruption
      </button>
      {open && places && (
        <div
          role="menu"
          className="absolute right-0 top-10 z-50 w-80 overflow-hidden rounded-lg border border-line bg-panel shadow-[0_12px_32px_-8px_rgb(0_0_0/0.6)]"
        >
          <p className="border-b border-line-soft px-3 py-2 text-[12px] leading-[1.45] text-dim">
            Takes every site in the zone to 0% capacity for 21 days. The agent is not involved.
          </p>
          <ul className="max-h-80 overflow-y-auto py-1">
            {places.zones.map((z) => (
              <li key={z.id}>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => pick(z.id, z.name)}
                  className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-[13px] hover:bg-raised focus-visible:bg-raised focus-visible:outline-none"
                >
                  <span className="truncate">
                    {z.name}
                    <span className="ml-2 text-dim">{z.hazard}</span>
                  </span>
                  <span className="num shrink-0 text-[12px] text-dim">
                    {z.sites} {z.sites === 1 ? 'site' : 'sites'}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
