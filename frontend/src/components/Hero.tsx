import { headline } from '../lib/headline'
import { CountUp, SplitHeadline } from '../lib/motion'
import { STEPS, currentStep, useStore } from '../lib/store'

const usd = (c: number) => `$${Math.round(c / 100).toLocaleString('en-US')}`
const int = (v: number) => v.toLocaleString('en-US')

/** Giant outlined step number, a two-tone headline built from engine output, and the count-up figures. */
export function Hero() {
  const st = useStore()
  const step = st.selected ?? currentStep(st)
  const title = st.scenarios.find((s) => s.id === st.scenario)?.title ?? ''
  const h = headline(step, st.derived, st.summary, st.runStatus, title)
  const num = STEPS.find((s) => s.id === step)?.num ?? '00'
  const t = st.summary?.totals
  const cap = st.derived.capacity[0]

  return (
    <section className="relative px-8 pt-7">
      <div className="bignum" aria-hidden key={num}>
        <span className="reveal inline-block">{num}</span>
      </div>
      <div className="relative z-[1]">
        <div className="eyebrow reveal" key={`e-${h.eyebrow}`}>
          <span>({num})</span>
          {h.eyebrow}
        </div>
        <SplitHeadline lead={h.lead} soft={h.soft} />
        {h.lede && (
          <p className="lede reveal" key={`l-${h.lede}`} style={{ ['--d' as string]: '220ms' }}>
            {h.lede}
          </p>
        )}
        <dl className="mt-6 grid grid-cols-5 border-y border-line">
          <Figure label="Exposed orders" tone={t?.exposed ? 'var(--st-covered)' : undefined} note={t ? `of ${int(t.orders)} due in 42 days` : ''}>
            <CountUp value={t?.exposed} format={int} />
          </Figure>
          <Figure label="Projected late" tone={t?.projected_late ? 'var(--st-late)' : undefined} note={t?.late_beyond_horizon ? `${t.late_beyond_horizon} still late at day 42` : ''}>
            <CountUp value={t?.projected_late} format={int} />
          </Figure>
          <Figure label="Revenue at risk" note="value of projected-late orders">
            <CountUp value={t?.revenue_at_risk_cents} format={usd} />
          </Figure>
          <Figure label="True capacity, per week" note={cap ? `${cap.component} at ${cap.plant} · naive ${int(cap.naive)}` : 'max-flow, measured in a run'}>
            <CountUp value={cap?.trueWk} format={int} />
          </Figure>
          <Figure label="Recovery spend" note={st.derived.receipt ? 'committed, parts not yet received' : st.derived.spendCents ? 'awaiting approval' : 'nothing committed'}>
            <CountUp value={st.derived.spendCents} format={usd} />
          </Figure>
        </dl>
      </div>
    </section>
  )
}

function Figure({ label, note, tone, children }: { label: string; note?: string; tone?: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0 border-r border-line px-4 py-3.5 first:pl-0 last:border-r-0">
      <dt className="label truncate">{label}</dt>
      <dd className="display num mt-1 truncate text-[28px] leading-8 tracking-[-0.03em]" style={tone ? { color: tone } : undefined}>
        {children}
      </dd>
      <dd className="mt-0.5 h-4 truncate text-[12px] text-muted">{note}</dd>
    </div>
  )
}
