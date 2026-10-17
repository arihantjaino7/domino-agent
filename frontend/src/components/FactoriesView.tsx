import { useState } from 'react'
import { COL, cap1, fmt, usd, useModel, type Model } from '../lib/model'
import { useStore } from '../lib/store'
import type { NodeStatus } from '../lib/types'
import { Head } from './Controls'

/* eslint-disable @typescript-eslint/no-explicit-any */

interface Power { on: boolean; tone: NodeStatus; title: string; detail: string }
interface Cell { id: string; top: string; mid: string; bottom: string; status: NodeStatus }

/** Main power switch on the wall: lever up = running, down = stopped; the lamp shows the problem's colour. */
function SwitchBox({ power }: { power: Power }) {
  const on = power.on, lamp = COL[power.tone]
  return (
    <g>
      <line x1={235} y1={171} x2={235} y2={262} stroke="#a9a49b" strokeWidth={3} />
      <rect x={198} y={262} width={74} height={96} rx={4} fill="#bfbab1" stroke="#8f8b84" />
      <rect x={204} y={268} width={62} height={84} rx={2} fill="#d6d2ca" />
      <text x={235} y={281} textAnchor="middle" fontSize={9} fill="#5d5b56">Main power</text>
      <circle className={power.tone === 'protected' ? '' : 'lamp-glow'} cx={235} cy={295} r={11} style={{ fill: lamp }} opacity={0.3} />
      <circle cx={235} cy={295} r={5.5} style={{ fill: lamp }} />
      <text x={250} y={on ? 316 : 349} fontSize={8.5} fill="#2a2926" fontWeight={600}>{on ? 'on' : 'off'}</text>
      <circle cx={232} cy={330} r={9} fill="#3a3936" />
      <rect x={228} y={on ? 306 : 330} width={8} height={24} rx={3} fill="#2a2926" />
      <circle cx={232} cy={on ? 306 : 354} r={5.5} style={{ fill: on ? '#2a2926' : '#d9566e' }} stroke="#1a1a18" />
    </g>
  )
}

/** A flat 2D elevation of a modern "gigafactory". Decorative: the orders live on the HTML panel over the glass wall. */
export function Building({ stopped, mini, power }: { stopped: boolean; mini?: boolean; power?: Power }) {
  const id = mini ? 'm' : 'b'
  const [wall, wall2, seam, trim, frame] = stopped ? ['#8f8b84', '#827e78', '#7b7771', '#9b9790', '#6f6b65'] : ['#ebe8e2', '#dedad3', '#d6d2ca', '#f6f4f0', '#bdb8af']
  const glass = '#1a1e23', mull = '#2a3038'
  return (
    <svg className={mini ? 'fac-mini' : 'building'} viewBox="0 70 1200 380" preserveAspectRatio="xMidYMid meet" aria-hidden>
      <defs><pattern id={`${id}caution`} width="16" height="16" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="16" fill="#d7a85a" /><rect x="8" width="8" height="16" fill="#1a1a18" /></pattern></defs>
      <polygon points="20,430 1180,430 1196,442 4,442" fill="#0b0b0a" />
      <polygon points="176,162 1084,162 1068,140 192,140" fill="#243040" />
      {Array.from({ length: 32 }, (_, i) => <line key={i} x1={196 + i * 28} y1={141} x2={190 + i * 28} y2={161} stroke="#34465c" />)}
      <line x1={186} y1={151} x2={1076} y2={151} stroke="#34465c" />
      <rect x={282} y={122} width={46} height={18} fill={wall2} /><rect x={282} y={122} width={46} height={4} fill={trim} />
      <rect x={660} y={126} width={64} height={14} fill={wall2} /><rect x={660} y={126} width={64} height={3} fill={trim} />
      <rect x={30} y={290} width={140} height={140} fill={wall2} /><rect x={26} y={284} width={148} height={8} fill={trim} />
      {[48, 108].map((x) => (
        <g key={x}>
          <rect x={x} y={340} width={46} height={90} fill="#2c2f34" />
          {Array.from({ length: 9 }, (_, i) => <line key={i} x1={x} y1={348 + i * 9} x2={x + 46} y2={348 + i * 9} stroke="#3b3f45" />)}
          <rect x={x - 4} y={332} width={54} height={5} fill={trim} /><rect x={x - 2} y={420} width={6} height={10} fill="#1a1a18" /><rect x={x + 42} y={420} width={6} height={10} fill="#1a1a18" />
        </g>
      ))}
      <rect x={170} y={168} width={920} height={262} fill={wall} />
      <rect x={166} y={162} width={928} height={9} fill={trim} />
      {[262, 322, 382].map((y) => <line key={y} x1={170} y1={y} x2={1090} y2={y} stroke={seam} strokeWidth={1.5} />)}
      {Array.from({ length: 20 }, (_, i) => <rect key={i} x={192 + i * 46} y={222} width={2} height={198} fill={seam} />)}
      <rect x={170} y={182} width={920} height={28} fill={glass} />
      {Array.from({ length: 23 }, (_, i) => <line key={i} x1={170 + i * 40} y1={182} x2={170 + i * 40} y2={210} stroke={mull} strokeWidth={2} />)}
      {!stopped && [3, 4, 9, 10, 11, 15, 16, 19].map((i) => <rect key={i} x={172 + i * 40} y={184} width={36} height={24} fill="#cdbf98" opacity={0.28} />)}
      <polygon points="420,182 462,182 438,210 396,210" fill="#262c34" opacity={0.9} /><polygon points="770,182 800,182 776,210 746,210" fill="#262c34" opacity={0.9} />
      <rect x={170} y={214} width={920} height={4} fill={stopped ? '#5a2a33' : '#8a2f3d'} />
      <rect x={300} y={232} width={580} height={170} fill={glass} stroke={frame} strokeWidth={3} />
      {Array.from({ length: 6 }, (_, i) => <line key={i} x1={300 + ((i + 1) * 580) / 7} y1={234} x2={300 + ((i + 1) * 580) / 7} y2={400} stroke="#20252b" />)}
      {power && <SwitchBox power={power} />}
      <rect x={900} y={300} width={110} height={130} fill={glass} stroke={frame} strokeWidth={3} /><line x1={955} y1={300} x2={955} y2={430} stroke={frame} strokeWidth={2} />
      <rect x={890} y={292} width={130} height={7} fill={trim} />
      {!stopped && <rect x={902} y={302} width={106} height={4} fill="#cdbf98" opacity={0.35} />}
      <rect x={176} y={172} width={4} height={248} fill={seam} /><rect x={1080} y={172} width={4} height={248} fill={seam} />
      <rect x={1090} y={206} width={80} height={224} fill={wall2} /><rect x={1086} y={200} width={88} height={7} fill={trim} />
      {[1104, 1124, 1144].map((x) => <rect key={x} x={x} y={226} width={10} height={184} fill={glass} />)}
      <rect x={170} y={420} width={1000} height={10} fill={stopped ? '#6f6b65' : '#cfcbc3'} />
      {stopped && <rect x={170} y={414} width={920} height={8} fill={`url(#${id}caution)`} opacity={0.8} />}
    </svg>
  )
}

function factoryModel(m: Model, id: string) {
  const d = m.d
  const siteId = d.declared?.site_ids?.[0]
  if (id === siteId) {
    const deps: string[] = d.trace?.shared_upstream?.find((s: any) => s.site === id)?.dependents ?? [...new Set<string>(d.exposedTier1.map((x) => x.site))]
    const pct = Math.round((d.declared.capacity_factor ?? 0) * 100)
    return {
      stopped: true, sign: m.name(id),
      cells: deps.map((x): Cell => {
        const to = [...new Set((d.trace?.evidence ?? []).filter((e: any) => e.tier1 === x).map((e: any) => m.short(e.plant)))]
        return { id: x, top: m.short(x), mid: m.N[x]?.region ?? '', bottom: to.length ? `sends ${m.partOf(x)[1]} to ${to.join(', ')}` : 'no orders through it', status: m.status(x) }
      }),
      rest: 0,
      metrics: [['Working', `${pct}%`, 'disrupted'], ['Works again', `day ${d.declared.end_day}`, null], [`Buyers of its ${m.input[1]}`, deps.length, 'covered'], ['Orders it reaches', m.totals?.exposed ?? '—', 'late']] as [string, string | number, NodeStatus | null][],
      power: { on: false, tone: 'disrupted', title: pct ? `Running at ${pct}%` : 'Power off', detail: `${cap1(m.kind)}: ${pct ? 'production cut' : 'production stopped'} until day ${d.declared.end_day}` } as Power,
      note: `${m.short(id)} makes ${m.input[1]}. A ${m.kind} stopped it. The panel shows the ${deps.length} suppliers that buy from it.`,
    }
  }
  const p = m.plants.find((x) => x.plant === id) ?? { orders: 0, exposed: 0, projected_late: 0, stockout_day: null }
  const mine = m.orders.filter((o) => o.plant === id).sort((a, b) => (m.orderState(a) === 'late' ? 0 : 1) - (m.orderState(b) === 'late' ? 0 : 1) || a.need_day - b.need_day)
  const ev = d.trace?.evidence?.find((e: any) => e.plant === id)
  const cap = m.capFor(id)
  const arrivals = (m.plan?.pos ?? []).filter((po: any) => po.plant_id === id).map((po: any) => po.first_arrival_day)
  const lateNow = mine.filter((o) => m.orderState(o) === 'late').length
  const power: Power = !m.hasIncident || !p.exposed
    ? { on: true, tone: 'protected', title: 'Running normally', detail: m.hasIncident ? 'No orders here depend on the stopped site' : 'No disruption reported' }
    : m.executed && arrivals.length
      ? { on: true, tone: 'protected', title: 'Running, rescue on the way', detail: `New ${m.part[1]} from day ${Math.min(...arrivals)}` }
      : cap && cap.trueWk === 0
        ? { on: true, tone: 'covered', title: 'Running on stock', detail: `${cap1(m.part[1])} supply cut: 0 of ${fmt(cap.naive)} a week` }
        : { on: true, tone: p.projected_late ? 'late' : 'covered', title: `Running, low on ${m.part[1]}`, detail: cap ? `${cap1(m.part[1])} supply ${fmt(cap.trueWk)} of ${fmt(cap.naive)} a week` : 'Supply reduced' }
  return {
    stopped: false, sign: m.name(id),
    cells: mine.map((o): Cell => ({ id: o.order_id, top: o.order_id, mid: m.name(o.customer), bottom: `due day ${o.need_day}`, status: m.orderState(o) })),
    rest: Math.max(0, p.orders - mine.length),
    metrics: [['Orders', p.orders, null], ['In danger', p.exposed, 'covered'], ['Will be late', lateNow, lateNow ? 'late' : 'protected'],
      m.executed && arrivals.length ? [`New ${m.part[1]}`, `day ${Math.min(...arrivals)}`, 'protected'] : [`${cap1(m.part[1])} run out`, p.stockout_day != null ? `day ${p.stockout_day}` : `not in ${m.horizon} days`, p.stockout_day != null ? 'late' : null]] as [string, string | number, NodeStatus | null][],
    power,
    note: !ev ? 'No orders at this factory depend on the stopped site.' : cap && cap.trueWk === 0
      ? `${cap1(m.part[1])} came from ${m.name(ev.tier1)}, which relied on the stopped site. Stock covers these orders for now.`
      : cap ? `${cap1(m.part[1])} come from ${m.name(ev.tier1)}: now ${fmt(cap.trueWk)} a week instead of ${fmt(cap.naive)}.` : '',
  }
}

export function FactoriesView() {
  const m = useModel()
  const approve = useStore((s) => s.approve)
  const siteId: string | undefined = m.d.declared?.site_ids?.[0]
  const ids = [...(siteId ? [siteId] : []), ...m.plants.map((p) => p.plant)]
  const [pick, setPick] = useState<string | null>(null)
  const [hl, setHl] = useState<string | null>(null)
  const worst = [...m.plants].sort((a, b) => b.projected_late - a.projected_late || b.exposed - a.exposed)[0]
  const sel = pick && ids.includes(pick) ? pick : worst?.exposed ? worst.plant : ids[0]
  if (!sel) return <Head title="Inside your factories" text="Loading the world…" />
  const f = factoryModel(m, sel)
  const few = f.stopped
  const list = f.stopped
    ? f.cells.map((c) => (
      <div key={c.id} className={`row ${hl === c.id ? 'on' : ''}`} onMouseEnter={() => setHl(c.id)} onMouseLeave={() => setHl(null)}><i className={`dot st-${c.status}`} /><div><div>{m.name(c.id)}</div><div className="sub">{c.bottom}</div></div></div>
    ))
    : m.orders.filter((o) => o.plant === sel).sort((a, b) => a.need_day - b.need_day).map((o) => {
      const sv = m.orderState(o)
      const words = sv === 'protected' ? 'protected (projected)' : sv === 'late' ? (o.ready_day == null ? `not ready within ${m.horizon} days` : `late by ${o.late_days} days`) : 'stock covers it'
      return <div key={o.order_id} className={`row ${hl === o.order_id ? 'on' : ''}`} onMouseEnter={() => setHl(o.order_id)} onMouseLeave={() => setHl(null)}><i className={`dot st-${sv}`} /><div><div><span className="mono">{o.order_id}</span> {m.name(o.customer)}</div><div className="sub">due day {o.need_day}, {words}</div></div></div>
    })
  const rec = m.rec, base = m.base
  return (
    <>
      <Head title="Inside your factories" text="Each tile on the glass wall is one customer order at this factory, coloured by what will happen to it." />
      <div className="card fac-stage-card">
        <div className="fac-top">
          <div><span className="sub">{f.stopped ? 'Where it started' : 'Our factory'}</span><h2 className="fac-name">{f.sign}</h2></div>
          <div className="fac-metrics">{f.metrics.map(([k, v, sv]) => <div key={k}><span className="sub">{sv && <i className={`dot st-${sv}`} />} {k}</span><b>{v}</b></div>)}</div>
        </div>
        <div className="fac-scene">
          <div className="fac-canvas">
            <Building stopped={f.stopped} power={f.power} />
            <div className={`power-pin tone-${f.power.tone}`}><i className={`dot st-${f.power.tone} ${f.power.tone === 'protected' ? '' : 'pulse'}`} /><div><b>{f.power.title}</b><span>{f.power.detail}</span></div></div>
            <div className={`fac-panel ${few ? 'few' : ''} ${hl ? 'holding' : ''}`}>
              {f.cells.map((c, i) => (
                <button key={c.id} type="button" className={`cell ${hl === c.id ? 'hl' : ''}`} style={{ animationDelay: `${i * 40}ms` }} onMouseEnter={() => setHl(c.id)} onMouseLeave={() => setHl(null)} onFocus={() => setHl(c.id)} onBlur={() => setHl(null)}>
                  <span className="cell-top"><i className={`dot st-${c.status}`} /><span className={few ? '' : 'mono'}>{c.top}</span></span>
                  <span className="cell-mid">{c.mid}</span><span className="cell-bot">{c.bottom}</span>
                </button>
              ))}
              {f.rest > 0 && <div className="cell rest"><b>{f.rest}</b><span>{f.cells.length ? 'more orders, safe' : 'orders, all safe'}</span></div>}
            </div>
          </div>
          <aside className="fac-list">
            <div className="side-h"><h3>{f.stopped ? 'Who buys from it' : 'Orders in danger'}</h3><span className="sub">{f.stopped ? '' : `${f.cells.length} of ${f.cells.length + f.rest}`}</span></div>
            <div className="order-list">{list.length ? list : <div className="sub" style={{ padding: '8px 6px' }}>No orders in danger here.</div>}</div>
          </aside>
        </div>
        <p className="plain fac-note">{f.note}</p>
      </div>
      <div className="fac-strip">
        {ids.map((id) => {
          const fl = id === siteId
          const p = fl ? null : m.plants.find((x) => x.plant === id)
          const lateNow = fl ? 0 : m.orders.filter((o) => o.plant === id && m.orderState(o) === 'late').length
          const sv: NodeStatus = fl ? 'disrupted' : lateNow ? 'late' : m.executed && p?.projected_late ? 'protected' : p?.exposed ? 'covered' : 'protected'
          return (
            <button key={id} type="button" className={`fac ${sel === id ? 'on' : ''}`} onClick={() => { setPick(id); setHl(null) }}>
              <div><span className="sub">{fl ? 'Where it started' : 'Our factory'}</span><b>{m.short(id)}</b>
                <span className="tag" style={{ marginTop: 6 }}><i className={`dot st-${sv}`} />{fl ? 'stopped' : lateNow ? `${lateNow} late` : p?.exposed ? `${p.exposed} in danger, on time` : 'running normally'}</span></div>
              <Building stopped={fl} mini />
            </button>
          )
        })}
      </div>
      {rec && base && (
        <div className="card compare">
          <div><span className="sub">If nobody acts</span><p><b>{base.late}</b> orders late, <b>{usd(base.penalty_cents)}</b> in late fees</p></div>
          <div className="arrow-r" aria-hidden><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M4 12h15m-5-5 5 5-5 5" /></svg></div>
          <div><span className="sub">With DOMINO's plan</span><p><b style={{ color: 'var(--st-protected)' }}>{rec.late}</b> {rec.late === 1 ? 'order' : 'orders'} late, <b>{usd(rec.penalty_cents)}</b> in late fees, plan costs <b>{usd(rec.spend_cents)}</b></p></div>
          {m.executed ? <span className="tag"><i className="dot st-protected" />Approved</span> : <button type="button" className="btn btn-accent" disabled={m.phase !== 'awaiting'} onClick={() => void approve()}>Approve plan</button>}
        </div>
      )}
    </>
  )
}
