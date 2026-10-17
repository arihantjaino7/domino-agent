import { int, usd } from '../lib/format'
import { useStore } from '../lib/store'

function Cell({ label, value, tone, note }: { label: string; value: string; tone?: string; note?: string }) {
  return (
    <div className="flex min-w-0 flex-col justify-center gap-0.5 border-r border-line-soft px-4 last:border-r-0">
      <span className="truncate text-[11.5px] text-dim">{label}</span>
      <span className={`num truncate text-[19px] leading-6 ${tone ?? 'text-fg'}`}>{value}</span>
      <span className="num h-[15px] truncate text-[11px] text-faint">{note ?? ''}</span>
    </div>
  )
}

/** KPIs straight from the projection on the live graph and from this run's tool results. */
export function KpiStrip() {
  const t = useStore((s) => s.summary?.totals)
  const cap = useStore((s) => s.derived.capacity)
  const spend = useStore((s) => s.derived.spendCents)
  const executed = useStore((s) => s.events.some((e) => e.type === 'action.executed'))
  const capLine = cap.length
    ? cap.map((c) => `${c.naive.toLocaleString('en-US')} → ${c.trueWk.toLocaleString('en-US')}`).join(' · ')
    : '—'
  return (
    <section
      aria-label="Key figures"
      className="grid h-[72px] grid-cols-[1fr_1fr_1fr_1fr_1.7fr_1fr] border-b border-line bg-panel"
    >
      <Cell
        label="Exposed orders"
        value={int(t?.exposed)}
        tone={t?.exposed ? 'text-covered' : undefined}
        note={t ? `of ${int(t.orders)} due within 42 days` : undefined}
      />
      <Cell
        label="Projected late"
        value={int(t?.projected_late)}
        tone={t?.projected_late ? 'text-late' : undefined}
        note={t?.late_beyond_horizon ? `${t.late_beyond_horizon} still late at day 42` : undefined}
      />
      <Cell label="Revenue at risk" value={usd(t?.revenue_at_risk_cents)} />
      <Cell label="Late penalties (at least)" value={usd(t?.penalty_exposure_cents)} />
      {cap.length > 1 ? (
        <div className="flex min-w-0 flex-col justify-center gap-0.5 border-r border-line-soft px-4">
          <span className="truncate text-[11.5px] text-dim">Capacity per week, naive → true (max-flow)</span>
          <ul className="grid grid-cols-2 gap-x-4 gap-y-px">
            {cap.slice(0, 4).map((c) => (
              <li key={`${c.component}@${c.plant}`} className="num flex min-w-0 items-baseline gap-1.5 text-[12.5px]">
                <span className="truncate text-faint">
                  {c.component} {c.plant.replace('PL-', '')}
                </span>
                <span className="shrink-0 text-fg">
                  {c.naive.toLocaleString('en-US')} → {c.trueWk.toLocaleString('en-US')}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <Cell
          label="Capacity per week, naive → true"
          value={capLine}
          note={
            cap.length
              ? cap.map((c) => `${c.component} at ${c.plant.replace('PL-', '')}`).join(' · ')
              : 'measured with max-flow during a run'
          }
        />
      )}
      <Cell label="Recovery spend" value={usd(spend)} note={spend ? (executed ? 'committed: POs placed, parts not yet received' : 'submitted for approval') : undefined} />
    </section>
  )
}
