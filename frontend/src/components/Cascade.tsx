import { ChevronRight } from 'lucide-react'
import { useStore } from '../lib/store'

const NONE: never[] = []

/** The cascade sentence, built only from trace_exposure and project_shortages results. */
export function Cascade() {
  const d = useStore((s) => s.derived)
  const incidents = useStore((s) => s.summary?.incidents ?? NONE)
  if (!d.origins.length && incidents.length) {
    return (
      <p className="text-[13px] text-dim">
        <span className="num text-disrupted">{incidents.map((i) => i.id).join(', ')}</span> is open. Run DOMINO to
        trace its cascade, or reset the world.
      </p>
    )
  }
  if (!d.origins.length) {
    return (
      <p className="text-[13px] text-dim">
        No disruption traced yet. Run DOMINO on the alert below, or inject a disruption.
      </p>
    )
  }
  const orders =
    d.exposedOrders != null
      ? `${d.exposedOrders} orders${d.customersHit != null ? ` / ${d.customersHit} customers` : ''}`
      : null
  const parts = [
    d.origins.join(', '),
    `${d.exposedTier1.length} tier-1`,
    `${d.components.length} components`,
    `${d.products.length} products`,
    `${d.plants.length} plants`,
    orders,
  ].filter((p): p is string => Boolean(p))
  return (
    <p className="flex flex-wrap items-center gap-x-1 gap-y-0.5 text-[13px]">
      <span className="mr-1 text-dim">Cascade</span>
      {parts.map((p, i) => (
        <span key={`${i}-${p}`} className="flex items-center gap-1">
          {i > 0 && <ChevronRight size={13} className="text-faint" aria-hidden />}
          <span className={i === 0 ? 'num text-disrupted' : 'text-fg'}>{p}</span>
        </span>
      ))}
      {d.tier1View != null && (
        <span className="ml-4 text-dim">
          A tier-1-only view sees <span className="num text-fg">{d.tier1View}</span> affected suppliers
        </span>
      )}
    </p>
  )
}
