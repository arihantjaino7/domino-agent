import { fmt, lateWords, plural, useModel } from '../lib/model'
import { useStore } from '../lib/store'
import type { LearnedReliability } from '../lib/types'

/* eslint-disable @typescript-eslint/no-explicit-any */

const WHEN = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
const learnedOn = (d: string) => (d ? WHEN.format(new Date(`${d}T00:00:00`)) : 'date not recorded')
const arrow = (t: string) => t.replace(/ -> /g, ' → ')

/** "Fast-forward to delivery" once the plan is executed and checked; afterwards, what arrived. */
export function FastForward() {
  const m = useModel()
  const st = useStore()
  if (!m.executed) return null
  const dl = m.delivery
  if (dl) {
    const late = (dl.pos ?? []).filter((p: any) => p.days_late > 0).length
    return (
      <div className="ff done">
        <div className="side-h"><h3>Delivered by day {dl.day}</h3><span className="tag"><i className={`dot st-${dl.counts?.fulfilled_late || dl.counts?.unfulfilled ? 'late' : 'protected'}`} />{fmt(dl.counts?.fulfilled)} of {plural(dl.orders?.length, 'order')} on time</span></div>
        <p className="plain">{plural((dl.pos?.length ?? 0) - late, 'supplier order')} arrived on time and {fmt(late)} late. {dl.counts?.fulfilled_late ? `${plural(dl.counts.fulfilled_late, 'customer order')} shipped late; ` : ''}{dl.counts?.unfulfilled ? `${plural(dl.counts.unfulfilled, 'order')} still waits for parts; ` : ''}DOMINO wrote how each supplier did to <span className="mono">{dl.memory_graph}</span>, and the next plan ranks suppliers by it.</p>
      </div>
    )
  }
  const replay = st.mode === 'replay'
  const ready = !!m.d.verify && !replay
  return (
    <div className="ff">
      <div>
        <p className="plain">The orders are placed, not delivered. Fast-forward the clock until the parts arrive: each supplier is on time or late, set by its reliability and how hard this plan pushes it.</p>
        {!ready && <p className="sub" style={{ marginTop: 6 }}>{replay ? 'A recording ends at its report. Switch to Demo to fast-forward a run.' : 'Available once the safety checks have run.'}</p>}
      </div>
      <button type="button" className="btn btn-accent wide" disabled={!ready || st.busy} onClick={() => void st.deliver()}>{st.busy ? 'Delivering' : 'Fast-forward to delivery'}</button>
    </div>
  )
}

/** Reliability learned from deliveries: seeded value, learned value, and the purchase orders it came from. */
export function LearnedList({ rows, names }: { rows: LearnedReliability[]; names?: (id: string) => string }) {
  return (
    <div className="learned">
      {rows.map((r) => (
        <div className="mem-lesson" key={r.site}>
          <div className="mem-h">
            <span>{names ? names(r.site) : r.name ?? r.site}</span>
            <span className="rel num"><span className="muted">{r.seeded.toFixed(2)}</span> → <b className={r.learned < r.seeded ? 'down' : r.learned > r.seeded ? 'up' : ''}>{r.learned.toFixed(2)}</b></span>
          </div>
          <div className="mem-ents">
            <span className="sub">learned {learnedOn(r.learned_on)} from {plural(r.deliveries, 'delivery', 'deliveries')}, {fmt(r.on_time)} on time</span>
            {r.evidence.slice(-3).reverse().map((e, i) => <span className="mem-ent mono" key={`${e.po_id}-${e.run_id}-${i}`} title={`run ${e.run_id}`}>{e.po_id} {lateWords(e.days_late)}</span>)}
          </div>
        </div>
      ))}
    </div>
  )
}

/** Why the plan differs from a memory-less one: the learned values it used and the rankings they changed. */
export function PlanMemory({ plan }: { plan: any }) {
  const rows: any[] = plan?.learned_reliability ?? []
  if (!rows.length) return null
  const changes: any[] = plan?.ranking_changes ?? []
  return (
    <details className="checks-box" open>
      <summary>{changes.length ? 'Memory changed this plan' : 'What memory knows about these suppliers'}</summary>
      {changes.map((c) => <p className="plain" key={`${c.component}-${c.plant}`}>{arrow(c.text)}.</p>)}
      {rows.map((r) => <p className="plain" key={r.site}>{arrow(r.text)}{r.in_plan ? '' : '. Not used in this plan'}.</p>)}
    </details>
  )
}
