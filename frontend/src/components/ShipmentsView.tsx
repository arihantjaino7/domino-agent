import { useState } from 'react'
import { fmt, lateWords, usd, useModel, type Model } from '../lib/model'
import { Head } from './Controls'
import { FastForward, LearnedList } from './Delivery'
import { GEO, PLANT_GEO } from '../lib/geo'

/* eslint-disable @typescript-eslint/no-explicit-any */

function MiniRoute({ m, po, i }: { m: Model; po: any; i: number }) {
  const a = GEO[m.N[po.site_id]?.region ?? ''], b = PLANT_GEO[po.plant_id]
  if (!a || !b) return null
  const pad = 3, minLo = Math.min(a[0], b[0]) - pad, maxLo = Math.max(a[0], b[0]) + pad, minLa = Math.min(a[1], b[1]) - pad, maxLa = Math.max(a[1], b[1]) + pad
  const sc = Math.min(90 / (maxLo - minLo), 50 / (maxLa - minLa))
  const pt = ([lo, la]: [number, number]) => [3 + (lo - minLo) * sc, 3 + (maxLa - la) * sc]
  const p = pt(a), q = pt(b)
  const d = `M${p[0]},${p[1]} Q${(p[0] + q[0]) / 2},${Math.min(p[1], q[1]) - 14} ${q[0]},${q[1]}`
  const dots = []
  for (let x = 4; x < 96; x += 6) for (let y = 4; y < 56; y += 6) dots.push(<circle key={`${x}-${y}`} cx={x} cy={y} r={0.7} fill="#302f2b" />)
  return (
    <svg className="mini-route" viewBox="0 0 96 56" aria-hidden>
      {dots}
      <path d={d} fill="none" stroke="#79b394" strokeWidth={1.4} strokeDasharray="3 3" />
      <circle cx={p[0]} cy={p[1]} r={3} fill="#bdbab3" /><circle cx={q[0]} cy={q[1]} r={3.4} fill="none" stroke="#edebe6" strokeWidth={1.4} />
      <circle r={3} fill="#79b394"><animateMotion dur={`${2.2 + i * 0.4}s`} repeatCount="indefinite" path={d} /></circle>
    </svg>
  )
}

/** Largest-remainder split of n blocks across the allocations, at least one block each. */
function slots(allocs: any[], n: number) {
  const total = allocs.reduce((a, x) => a + x.qty, 0) || 1
  const raw = allocs.map((x) => (x.qty / total) * n)
  const base = raw.map((r) => Math.max(1, Math.floor(r)))
  let left = n - base.reduce((a, b) => a + b, 0)
  const order = raw.map((r, i) => [r - Math.floor(r), i]).sort((a, b) => b[0] - a[0])
  for (let i = 0; left > 0 && order.length; i = (i + 1) % order.length, left--) base[order[i][1]]++
  return base
}

function Hold({ m, po, hl }: { m: Model; po: any; hl: string | null }) {
  const air = po.mode === 'air'
  const cols = 14, rows = 3, counts = slots(po.allocations, cols * rows)
  const x0 = air ? 120 : 70, x1 = 660, y0 = 52, y1 = 186, sw = (x1 - x0) / cols, sh = (y1 - y0) / rows
  const out: React.ReactNode[] = []
  let k = 0
  po.allocations.forEach((a: any, ai: number) => {
    for (let j = 0; j < counts[ai]; j++, k++) {
      const c = Math.floor(k / rows), r = k % rows, x = x0 + c * sw + 3, y = y0 + r * sh + 3
      out.push(<rect key={`s${k}`} className={`slot ${hl === a.order_id ? 'hl' : ''}`} style={{ animationDelay: `${k * 25}ms`, fill: `var(--st-${m.executed ? 'protected' : 'covered'})` }} x={x} y={y} width={sw - 6} height={sh - 6} rx={4} fillOpacity={0.18 + (ai % 3) * 0.12} stroke="#4a4844" />)
      if (j === 0) out.push(
        <g key={`t${k}`} className="slot-t" style={{ animationDelay: `${k * 25 + 420}ms` }} pointerEvents="none">
          <text x={x + 6} y={y + 16} fontSize={10} fill="#edebe6" fontFamily="JetBrains Mono">{String(a.order_id).replace('SO-', '')}</text>
          <text x={x + 6} y={y + 29} fontSize={9.5} fill="#bdbab3">{a.qty}</text>
        </g>,
      )
    }
  })
  return (
    <svg key={po.id} className={`hold-svg ${hl ? 'holding' : ''}`} viewBox="0 0 760 240" role="img" aria-label={`${po.qty} units split across ${po.allocations.length} orders`}>
      <ellipse cx={380} cy={224} rx={330} ry={8} fill="#000" opacity={0.45} />
      {air ? (
        <>
          <polygon points="60,30 716,30 716,210 130,210 60,140" fill="#1f1e1c" stroke="#3a3834" strokeWidth={1.5} />
          {Array.from({ length: 22 }, (_, i) => <line key={i} x1={80 + i * 30} y1={34} x2={80 + i * 30 - 40} y2={206} stroke="#262522" />)}
          <text x={78} y={56} fontSize={11} fill="#5d5b56">air cargo box</text>
        </>
      ) : (
        <>
          <rect x={40} y={30} width={676} height={180} rx={4} fill="#1f1e1c" stroke="#3a3834" strokeWidth={1.5} />
          {Array.from({ length: 46 }, (_, i) => <line key={i} x1={52 + i * 14} y1={34} x2={52 + i * 14} y2={206} stroke="#262522" strokeWidth={2} />)}
          <rect x={676} y={34} width={36} height={172} fill="#232220" stroke="#3a3834" /><line x1={688} y1={40} x2={688} y2={200} stroke="#5d5b56" strokeWidth={2} /><line x1={700} y1={40} x2={700} y2={200} stroke="#5d5b56" strokeWidth={2} />
          {[[40, 30], [704, 30], [40, 198], [704, 198]].map(([x, y]) => <rect key={`${x}${y}`} x={x} y={y} width={12} height={12} fill="#3a3834" />)}
          <text x={58} y={50} fontSize={11} fill="#5d5b56">sea container</text>
        </>
      )}
      {out}
    </svg>
  )
}

function Gantt({ m, pick, setPick }: { m: Model; pick: number; setPick: (i: number) => void }) {
  const H = m.horizon, W = 1000, x0 = 230, x1 = W - 16, RH = 46
  const X = (d: number) => x0 + (d / H) * (x1 - x0)
  const pos: any[] = m.plan?.pos ?? []
  const h = 40 + pos.length * RH + 20
  const orderOf = (id: string) => m.orders.find((o) => o.order_id === id)
  const marks: [number, string, string][] = [
    ...m.plants.filter((p) => p.stockout_day != null).map((p): [number, string, string] => [p.stockout_day, `${m.short(p.plant)} runs out`, p.projected_late ? 'var(--st-late)' : 'var(--st-covered)']),
    ...(m.d.declared ? [[m.d.declared.end_day, `${m.site ? m.short(m.site.id) : 'Site'} works again`, '#8f8d87'] as [number, string, string]] : []),
  ]
  return (
    <svg className="gantt-svg" viewBox={`0 0 ${W} ${h}`} role="img" aria-label="When the new parts arrive">
      {Array.from({ length: Math.floor(H / 7) + 1 }, (_, i) => i * 7).map((d) => (
        <g key={d}><line x1={X(d)} y1={26} x2={X(d)} y2={h - 14} stroke="#262522" /><text x={X(d)} y={18} textAnchor="middle" fontSize={10.5} fill="#5d5b56">{d ? `day ${d}` : 'today'}</text></g>
      ))}
      {marks.map(([d, t, c], i) => (
        <g key={t}><line x1={X(d)} y1={26} x2={X(d)} y2={h - 14} style={{ stroke: c }} strokeDasharray="3 3" /><text x={X(d) + (i === marks.length - 1 ? 6 : -6)} y={h - 4} textAnchor={i === marks.length - 1 ? 'start' : 'end'} fontSize={10} style={{ fill: c }}>{t}</text></g>
      ))}
      {pos.map((po, i) => {
        const y = 34 + i * RH, lead = m.altFor(po)?.lead_days ?? 0
        return (
          <g key={po.id} style={{ cursor: 'pointer' }} onClick={() => setPick(i)}>
            <rect x={0} y={y - 4} width={W} height={RH - 4} rx={8} fill={i === pick ? '#1f1e1c' : 'transparent'} />
            <text x={10} y={y + 13} fontSize={12} fill="#edebe6">{m.short(po.site_id)} to {m.short(po.plant_id)}</text>
            <text x={10} y={y + 29} fontSize={10.5} fill="#8f8d87">{fmt(po.qty)} {m.partOf(po.site_id)[1]} by {po.mode}</text>
            <rect className="grow" style={{ animationDelay: `${i * 120}ms` }} x={X(0)} y={y + 6} width={X(lead) - X(0)} height={16} rx={5} fill="#34322e" />
            {X(lead) - X(0) > 70 && <text x={X(0) + 6} y={y + 18} fontSize={10} fill="#bdbab3">making {lead}d</text>}
            <rect className="grow" style={{ animationDelay: `${i * 120 + 300}ms`, fill: 'var(--st-protected)' }} x={X(lead)} y={y + 6} width={Math.max(0, X(po.first_arrival_day) - X(lead))} height={16} rx={5} fillOpacity={m.executed ? 0.55 : 0.25} />
            {X(po.first_arrival_day) - X(lead) > 70 && <text x={X(lead) + 6} y={y + 18} fontSize={10} fill="#edebe6">shipping</text>}
            {(() => {
              const out = m.poOutcome(po.id)
              if (!out) return <text x={X(po.first_arrival_day) + 8} y={y + 18} fontSize={10.5} fill="#edebe6">arrives day {po.first_arrival_day}</text>
              const at = Math.min(H, out.arrived_day)
              return (
                <>
                  {out.days_late > 0 && <rect className="grow" style={{ fill: 'var(--st-late)' }} x={X(po.first_arrival_day)} y={y + 6} width={Math.max(0, X(at) - X(po.first_arrival_day))} height={16} rx={5} fillOpacity={0.55}><title>{`${lateWords(out.days_late)}: planned day ${po.first_arrival_day}, arrived day ${out.arrived_day}`}</title></rect>}
                  <text x={X(at) + 8} y={y + 18} fontSize={10.5} fill="#edebe6">{out.days_late > 0 ? `arrived day ${out.arrived_day}, ${lateWords(out.days_late)}` : `arrived day ${out.arrived_day}, on time`}</text>
                </>
              )
            })()}
            {po.allocations.map((a: any) => { const o = orderOf(a.order_id); return o ? <path key={a.order_id} d={`M${X(o.need_day)},${y + 26} l4,5 -4,5 -4,-5Z`} style={{ fill: 'var(--st-late)' }} opacity={0.85}><title>{`${a.order_id} is due on day ${o.need_day}`}</title></path> : null })}
          </g>
        )
      })}
    </svg>
  )
}

/** What happened to one customer order once the parts arrived. "Fulfilled" only after delivery. */
function OrderOutcome({ o }: { o: any }) {
  if (!o) return <span className="sub">—</span>
  if (o.status === 'fulfilled') return <span className="outcome" title={`fulfilled on day ${o.delivered_day}`}><i className="dot st-protected" />on time</span>
  if (o.status === 'fulfilled_late') return <span className="outcome" title={`fulfilled on day ${o.delivered_day}`}><i className="dot st-late" />{lateWords(o.late_days)}</span>
  return <span className="outcome"><i className="dot st-disrupted" />still waiting</span>
}

export function ShipmentsView() {
  const m = useModel()
  const [pick, setPick] = useState(0)
  const [hl, setHl] = useState<string | null>(null)
  const pos: any[] = m.plan?.pos ?? []
  if (!pos.length) {
    return (
      <>
        <Head title="Shipments" text="When DOMINO has a rescue plan, every order it would place with a supplier shows up here." />
        <div className="card"><div className="empty">
          <h2>{m.noExposure ? 'No shipments needed' : 'No plan yet'}</h2>
          <p>{m.noExposure ? 'Nothing in the graph is affected, so nothing needs to be bought.' : m.phase === 'idle' ? 'Start a disruption on the Overview. The plan and its shipments appear here.' : 'DOMINO is still testing plans.'}</p>
        </div></div>
      </>
    )
  }
  const i = Math.min(pick, pos.length - 1), po = pos[i], alt = m.altFor(po)
  const ship = po.mode === 'air' ? alt?.air_transit_days : alt?.transit_days
  const what = m.partOf(po.site_id)[1]
  const out = m.poOutcome(po.id)
  const learned: any[] = m.delivery?.learned_reliability ?? []
  return (
    <>
      <Head title={m.delivery ? 'Shipments delivered' : m.executed ? 'Shipments on the way' : 'Shipments in the plan'} text={`The plan buys ${m.part[1]} from new suppliers. Each card is one order to a supplier. ${m.delivery ? `The clock was fast-forwarded to day ${m.delivery.day}: this is how each one really arrived.` : m.executed ? 'They are ordered, not delivered yet.' : 'Nothing is ordered until you approve.'}`} />
      {m.executed && !m.delivery && <div className="card ff-card"><div className="card-b"><FastForward /></div></div>}
      <div className="ship-strip">
        {pos.map((p, j) => (
          <button key={p.id} type="button" className={`ship ${j === i ? 'on' : ''}`} onClick={() => { setPick(j); setHl(null) }}>
            <div><b>{m.short(p.site_id)}</b><div className="sub">to our {m.short(p.plant_id)} factory</div>
              <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}><span className="tag">{p.mode === 'air' ? 'by air' : 'by sea'}</span>{(() => {
                const out = m.poOutcome(p.id)
                return out ? <span className="tag"><i className={`dot st-${out.days_late > 0 ? 'late' : 'protected'}`} />{out.days_late > 0 ? lateWords(out.days_late) : 'on time'}</span>
                  : <span className="tag">arrives day {p.first_arrival_day}</span>
              })()}</div></div>
            <MiniRoute m={m} po={p} i={j} />
          </button>
        ))}
      </div>
      <div className="log-grid">
        <div className="card">
          <div className="hold-head">
            <p className="plain" style={{ margin: 0, maxWidth: '62ch' }}><b>{fmt(po.qty)} {what}</b> from {m.name(po.site_id)} to our {m.short(po.plant_id)} factory, by {po.mode}. {alt ? `${alt.lead_days} days to make, ${ship} days to ship. ` : ''}{out ? <>Planned for day {po.first_arrival_day}; the first ones <b>arrived on day {out.arrived_day}</b>, {lateWords(out.days_late)}, and the last on day {out.received_day ?? '—'}. </> : <>First ones arrive on <b>day {po.first_arrival_day}</b>, </>}at {usd(po.unit_price_cents)} each.</p>
            <span className="tag"><i className={`dot st-${out ? (out.days_late > 0 ? 'late' : 'protected') : m.executed ? 'protected' : 'covered'}`} />{out ? (out.days_late > 0 ? `Delivered ${lateWords(out.days_late)}` : 'Delivered on time') : m.executed ? 'Ordered, not delivered yet' : 'Waiting for your OK'}</span>
          </div>
          <Hold m={m} po={po} hl={hl} />
          <div className="sub" style={{ padding: '0 18px 16px' }}>Each block is a share of this shipment, marked with the customer order it is for.{alt?.exposure_warning ? ' Watch out: this supplier also depends partly on the stopped site, so DOMINO only counts its clean supply.' : ''}</div>
        </div>
        <div className="card"><div className="card-b">
          <div className="side-h"><h3>Who gets these {what}</h3></div>
          <div style={{ overflowX: 'auto' }}><table><thead><tr><th>Order</th><th>Customer</th><th className="r">Units</th>{!m.delivery && <th className="r">Arrive</th>}<th className="r">Due</th>{m.delivery && <th>Delivered</th>}</tr></thead><tbody>
            {po.allocations.map((a: any) => {
              const o = m.orders.find((x) => x.order_id === a.order_id)
              return <tr key={a.order_id} onMouseEnter={() => setHl(a.order_id)} onMouseLeave={() => setHl(null)}><td className="mono">{a.order_id}</td><td>{o ? m.name(o.customer) : ''}</td><td className="r">{a.qty}</td>{!m.delivery && <td className="r">day {a.arrival_day}</td>}<td className="r">{o ? `day ${o.need_day}` : ''}</td>{m.delivery && <td><OrderOutcome o={m.orderOutcome(a.order_id)} /></td>}</tr>
            })}
          </tbody></table></div>
        </div></div>
      </div>
      <div className="card" style={{ marginTop: 16 }}><div className="card-h"><h2>When the new {m.part[1]} arrive</h2><span className="sub">grey is making, green is shipping, pink marks are the days customers need their orders</span></div>
        <div className="card-b" style={{ overflowX: 'auto' }}><Gantt m={m} pick={i} setPick={(j) => { setPick(j); setHl(null) }} /></div></div>
      {m.delivery && (
        <div className="log-grid" style={{ marginTop: 16 }}>
          <div className="card"><div className="card-b">
            <FastForward />
            <div style={{ overflowX: 'auto', marginTop: 10 }}><table><thead><tr><th>Order</th><th>Customer</th><th className="r">Due</th><th className="r">Ready</th><th>Outcome</th></tr></thead><tbody>
              {(m.delivery.orders ?? []).map((o: any) => (
                <tr key={o.id}><td className="mono">{o.id}</td><td>{m.name(o.customer)}{o.tier === 'strategic' ? <span className="sub"> · strategic</span> : null}</td><td className="r">day {o.need_day}</td><td className="r">{o.delivered_day != null ? `day ${o.delivered_day}` : '—'}</td><td><OrderOutcome o={o} /></td></tr>
              ))}
            </tbody></table></div>
          </div></div>
          <div className="card"><div className="card-b">
            <div className="side-h"><h3>What DOMINO learned</h3><span className="mono muted">{m.delivery.memory_graph}</span></div>
            <p className="sub">Reliability per supplier, seeded → learned from these deliveries. It survives a world reset; the next plan ranks suppliers by it.</p>
            <LearnedList rows={learned} names={m.name} />
          </div></div>
        </div>
      )}
    </>
  )
}
