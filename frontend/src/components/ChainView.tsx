import { useState } from 'react'
import { COL, fmt, useModel, type Model } from '../lib/model'
import type { NodeStatus } from '../lib/types'
import { Head } from './Controls'

/* eslint-disable @typescript-eslint/no-explicit-any */

interface Col { title: string; ids: string[]; all: string[]; shown: string[]; split?: number }
interface Edge { s: string; t: string; kind: 'cut' | 'supply' | 'plan' | 'builds' | 'orders' }
interface Group { id: string; product: string; customers: number; orders: number; late: number; saved: number }

/** Only the companies on the disruption's path, in five columns, built from the trace evidence and the plan. */
function chainModel(m: Model, after: boolean) {
  const d = m.d, ev: any[] = d.trace?.evidence ?? []
  const sh = d.trace?.shared_upstream?.[0]
  const orderState = (o: any) => (after ? m.orderState(o) : o.status === 'projected_late' ? 'late' : 'covered')
  const upstream: string[] = [], tier1: string[] = [], plants: string[] = [], products: string[] = []
  const add = (arr: string[], id: string) => { if (!arr.includes(id)) arr.push(id) }
  const edges: Edge[] = []
  const edge = (e: Edge) => { if (!edges.some((x) => x.s === e.s && x.t === e.t && x.kind === e.kind)) edges.push(e) }
  for (const e of ev) {
    for (const id of e.path) {
      const n = m.N[id]
      if (!n) continue
      if (n.kind === 'plant') add(plants, id)
      else if (n.col === 'tier1') add(tier1, id)
      else add(upstream, id)
    }
    add(products, e.product)
    for (let i = 0; i + 1 < e.path.length; i++) {
      const a = m.N[e.path[i]], b = m.N[e.path[i + 1]]
      edge({ s: e.path[i], t: e.path[i + 1], kind: b?.kind === 'plant' || a?.col === 'tier1' ? 'supply' : 'cut' })
    }
    edge({ s: e.plant, t: e.product, kind: 'builds' })
  }
  if (sh) for (const dep of sh.dependents) { add(tier1, dep); edge({ s: sh.site, t: dep, kind: 'cut' }) }
  tier1.sort((a, b) => ev.filter((e) => e.tier1 === b).length - ev.filter((e) => e.tier1 === a).length)
  const rescue = m.suppliersInPlan.filter((id) => !tier1.includes(id))
  for (const po of m.plan?.pos ?? []) edge({ s: po.site_id, t: po.plant_id, kind: 'plan' })
  const groups: Group[] = products.map((pr) => {
    const os = m.orders.filter((o) => o.product === pr)
    return { id: `G:${pr}`, product: pr, customers: new Set(os.map((o) => o.customer)).size, orders: os.length,
      late: os.filter((o) => orderState(o) === 'late').length, saved: os.filter((o) => orderState(o) === 'protected').length }
  })
  for (const g of groups) edge({ s: g.product, t: g.id, kind: 'orders' })
  const shownCust = [...new Set(m.orders.map((o) => o.customer as string))]
  const of = (...c: string[]) => Object.values(m.N).filter((n) => c.includes(n.col)).map((n) => n.id)
  const cols: Col[] = [
    { title: 'Upstream makers', ids: upstream, all: of('tier2', 'tier3'), shown: upstream },
    { title: 'Direct suppliers', ids: [...tier1, ...rescue], all: of('tier1'), shown: [...tier1, ...rescue], split: rescue.length ? tier1.length : undefined },
    { title: 'Our factories', ids: plants, all: of('plant'), shown: plants },
    { title: 'Products', ids: products, all: of('product'), shown: products },
    { title: 'Customers', ids: groups.map((g) => g.id), all: of('customer'), shown: shownCust },
  ]
  return { cols, edges, groups, rescue, orderState }
}

function Chain({ m, lens, after }: { m: Model; lens: 'tier1' | 'domino'; after: boolean }) {
  const [hl, setHl] = useState<string[]>([])
  const cm = chainModel(m, after)
  const t1lens = lens === 'tier1'
  const st = after ? m.status : m.statusBefore
  const W = 1330, CW = 222, CH = 62, GAPX = (W - 40 - CW * 5) / 4, TOP = 118, ROW = 84
  const maxN = Math.max(1, ...cm.cols.map((c) => c.ids.length + (c.split != null ? 1 : 0)))
  const H = TOP + maxN * ROW + 40
  const pos: Record<string, [number, number]> = {}
  cm.cols.forEach((c, k) => {
    const n = c.ids.length + (c.split != null ? 1 : 0)
    const y0 = TOP + ((maxN - n) * ROW) / 2
    c.ids.forEach((id, i) => (pos[id] = [20 + k * (CW + GAPX), y0 + (i + (c.split != null && i >= c.split ? 1 : 0)) * ROW]))
  })
  const statusOf = (id: string): NodeStatus => {
    if (t1lens) return 'none'
    if (id.startsWith('G:')) { const g = cm.groups.find((x) => x.id === id)!; return g.late ? 'late' : g.saved ? 'protected' : 'covered' }
    if (cm.rescue.includes(id)) return 'protected'
    return st(id)
  }
  const custState = (cu: string): NodeStatus => {
    const os = m.orders.filter((o) => o.customer === cu).map(cm.orderState)
    return os.includes('late') ? 'late' : os.includes('covered') ? 'covered' : os.length ? 'protected' : 'none'
  }
  const reach = (id: string) => {
    const out = new Set([id]), up = new Set([id])
    for (let grew = true; grew;) { grew = false; for (const e of cm.edges) if (out.has(e.s) && !out.has(e.t)) { out.add(e.t); grew = true } }
    for (let grew = true; grew;) { grew = false; for (const e of cm.edges) if (up.has(e.t) && !up.has(e.s)) { up.add(e.s); grew = true } }
    return [...out, ...up]
  }
  const hls = new Set(hl)
  const rejected = (id: string) => m.d.alternatives.some((a: any) => (a.rejected ?? []).some((r: any) => r.site === id))
  return (
    <svg className={`chain-svg ${hl.length ? 'dim' : ''}`} viewBox={`0 0 ${W} ${H}`} role="img" aria-label="How the disruption travels from upstream makers to customers">
      {cm.cols.map((c, k) => {
        const x = 20 + k * (CW + GAPX)
        return (
          <g key={c.title}>
            <text x={x} y={22} fontSize={13} fontWeight={500} fill="#edebe6">{c.title}</text>
            <text x={x} y={40} fontSize={11.5} fill="#8f8d87">{c.shown.length} of {c.all.length} on the path{c.all.length > c.shown.length ? ', rest not affected' : ''}</text>
            {c.all.map((nid, i) => {
              const on = c.shown.includes(nid)
              const sv: NodeStatus = t1lens || !on ? 'none' : k === 4 ? custState(nid) : statusOf(nid)
              return <circle key={nid} className="mdot" cx={x + 4 + (i % 15) * 13} cy={58 + Math.floor(i / 15) * 13} r={on ? 4.2 : 3.4} style={{ fill: on && !t1lens ? COL[sv] : '#3a3834' }}><title>{`${m.name(nid)}${on ? ' (shown below)' : ', not affected'}`}</title></circle>
            })}
            {c.split != null && <text x={x} y={(pos[c.ids[c.split]]?.[1] ?? 0) - 18} fontSize={11.5} fill="#79b394">New suppliers in the plan</text>}
          </g>
        )
      })}
      {cm.edges.map((e, i) => {
        const a = pos[e.s], b = pos[e.t]
        if (!a || !b) return null
        const x1 = a[0] + CW, y1 = a[1] + CH / 2, x2 = b[0], y2 = b[1] + CH / 2, dx = (x2 - x1) / 2
        const col = t1lens ? '#3a3834' : e.kind === 'cut' ? COL.disrupted : e.kind === 'plan' ? COL.protected : e.kind === 'orders' ? COL[statusOf(e.t)] : COL.covered
        const moving = e.kind === 'cut' || (e.kind === 'plan' && !after)
        const k = cm.cols.findIndex((c) => c.ids.includes(e.s))
        return (
          <path key={i} className={`chain-edge ${moving ? 'flow' : 'draw'} ${hls.has(e.s) && hls.has(e.t) ? 'hl' : ''}`} {...(moving ? {} : { pathLength: 1 })}
            style={{ stroke: col, animationDelay: moving ? '0s' : `${k * 0.3}s` }} d={`M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`} fill="none" strokeWidth={e.kind === 'plan' ? 1.6 : 2} opacity={t1lens ? 0.6 : 0.9} />
        )
      })}
      {cm.cols.flatMap((c) => c.ids.map((id) => {
        const [x, y] = pos[id], sv = statusOf(id), hidden = t1lens && c === cm.cols[0]
        let title: string, sub: string, right = ''
        if (id.startsWith('G:')) {
          const g = cm.groups.find((z) => z.id === id)!
          title = `${g.customers} customers, ${g.orders} orders`
          sub = g.saved ? `${g.saved} protected (projected)${g.late ? `, ${g.late} late` : ''}` : g.late ? `${g.late} will be late` : 'stock covers them'
        } else if (m.N[id]?.kind === 'site') {
          title = m.short(id); sub = m.N[id].region ?? ''
          right = (m.d.declared?.site_ids ?? []).includes(id) ? 'stopped' : cm.rescue.includes(id) ? 'in the plan' : m.suppliersInPlan.includes(id) ? 'in plan too' : rejected(id) ? 'no clean supply' : ''
        } else if (m.N[id]?.kind === 'plant') {
          const p = m.plants.find((x) => x.plant === id)
          title = `${m.short(id)} factory`; sub = p?.stockout_day != null ? `${m.part[1]} run out day ${p.stockout_day}` : 'enough stock for now'
        } else { title = m.name(id); sub = 'product' }
        return (
          <g key={id} className={`chain-card ${hls.has(id) ? 'hl' : ''}`} tabIndex={0} onMouseEnter={() => setHl(reach(id))} onMouseLeave={() => setHl([])} onFocus={() => setHl(reach(id))} onBlur={() => setHl([])}>
            <rect x={x} y={y} width={CW} height={CH} rx={12} fill={sv === 'none' ? '#1c1b19' : '#211f1d'} style={{ stroke: sv === 'none' ? '#34322e' : COL[sv] }} strokeOpacity={sv === 'none' ? 1 : 0.55} strokeDasharray={hidden ? '4 4' : undefined} />
            <rect x={x} y={y + 12} width={3} height={CH - 24} rx={1.5} style={{ fill: COL[sv] }} />
            <text x={x + 16} y={y + 26} fontSize={13} fontWeight={500} fill={hidden ? '#5d5b56' : '#edebe6'}>{title.length > 24 ? `${title.slice(0, 23)}…` : title}</text>
            <text x={x + 16} y={y + 45} fontSize={11.5} fill="#8f8d87">{sub}</text>
            {right && !t1lens && <text x={x + CW - 12} y={y + 45} textAnchor="end" fontSize={11} style={{ fill: COL[sv] }}>{right}</text>}
            {hidden && <text x={x + CW / 2} y={y + CH + 20} textAnchor="middle" fontSize={11.5} fill="#8f8d87">A normal tool cannot see this</text>}
          </g>
        )
      }))}
    </svg>
  )
}

export function ChainView() {
  const m = useModel()
  const [lens, setLens] = useState<'tier1' | 'domino'>('domino')
  const [after, setAfter] = useState(true)
  const d = m.d, ev: any[] = d.trace?.evidence ?? []
  const sh = d.trace?.shared_upstream?.[0]
  const total = Object.keys(m.N).length
  if (!ev.length) {
    return (
      <>
        <Head title="How the disruption travels" text={`Your supply chain has ${fmt(total)} companies, from raw materials to customers.`} />
        <div className="card"><div className="empty">
          <h2>{m.noExposure ? 'Nothing on the path' : m.phase === 'idle' ? 'No disruption yet' : 'DOMINO is tracing the chain'}</h2>
          <p>{m.noExposure ? 'DOMINO found no company of yours behind this alert. Not being in the graph does not mean safe.' : m.phase === 'idle' ? 'Start a disruption on the Overview. This page then shows only the companies on its path, out of all of them.' : 'The path appears here as soon as the trace step finishes.'}</p>
          {m.phase === 'idle' && <button type="button" className="btn btn-ghost" onClick={() => (location.hash = 'overview')}>Go to the Overview</button>}
        </div></div>
      </>
    )
  }
  return (
    <>
      <Head title="How the disruption travels" text={`Your supply chain has ${fmt(total)} companies. Only the ones on its path are shown here, from upstream makers on the left to your customers on the right.`}
        right={
          <div className="head-toggles">
            <div className="chip-toggle" role="group" aria-label="Who is looking">
              <button type="button" className={lens === 'tier1' ? 'on' : ''} onClick={() => setLens('tier1')}>Normal tool</button>
              <button type="button" className={lens === 'domino' ? 'on' : ''} onClick={() => setLens('domino')}>DOMINO</button>
            </div>
            {m.executed && (
              <div className="chip-toggle" role="group" aria-label="Before or after the plan">
                <button type="button" className={!after ? 'on' : ''} onClick={() => setAfter(false)}>Before plan</button>
                <button type="button" className={after ? 'on' : ''} onClick={() => setAfter(true)}>After plan</button>
              </div>
            )}
          </div>
        } />
      <div className="net-grid stacked">
        <div className="card net-card">
          {lens === 'tier1' && <div className="net-note">A normal tool only knows the suppliers you buy from directly. Without the first column it finds {d.tier1View ?? 0} problems.</div>}
          <div className="net-scroll"><Chain m={m} lens={lens} after={after} /></div>
          <div className="sub" style={{ padding: '0 18px 10px' }}>Each small dot above a column is one company, {fmt(total)} in total. Coloured dots are on the path and are shown as cards. Hover a dot to see its name.</div>
          <div className="map-legend" style={{ margin: '0 18px 16px' }}><span><i className="dot st-disrupted" />Stopped</span><span><i className="dot st-late" />Will be late</span><span><i className="dot st-covered" />In danger</span><span><i className="dot st-protected" />{m.executed ? 'Protected (projected)' : 'Rescue in the plan'}</span><span><i className="dot" />Not affected</span></div>
        </div>
        <div className="side-stack">
          {sh && (
            <div className="card"><div className="card-b"><div className="side-h"><h3>The hidden weak point</h3></div>
              <p className="plain">{m.short(sh.site)} sells {m.partOf(sh.site)[1]} to {sh.fan_out} of your suppliers. They look like {sh.fan_out} separate companies, but one {m.kind} hits all of them.</p></div></div>
          )}
          <div className="card"><div className="card-b"><div className="side-h"><h3>Paths it takes</h3></div>
            {ev.map((e) => (
              <div className="ev" key={e.id}>
                <div className="path">{e.path.map((id: string, i: number) => <span key={id}>{i > 0 && <i>→ </i>}{m.N[id]?.kind === 'plant' ? `${m.short(id)} factory` : m.short(id)}</span>)}</div>
                <div className="sub" style={{ marginTop: 3 }}>{e.orders.length} orders, evidence {e.id}</div>
              </div>
            ))}</div></div>
          <div className="card"><div className="card-b"><div className="side-h"><h3>{m.part[1][0].toUpperCase() + m.part[1].slice(1)} we can still get</h3><span className="sub">per week</span></div>
            {d.capacity.map((c) => (
              <div className="cap-row" key={`${c.component}@${c.plant}`}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5 }}><span>{m.short(c.plant)} factory</span><span className="num"><b style={{ fontWeight: 500 }}>{fmt(c.trueWk)}</b> <span className="muted">of {fmt(c.naive)}</span></span></div>
                <div className="cap-bars"><i style={{ width: '100%', background: '#34322e' }} /><i style={{ width: `${c.naive ? (c.trueWk / c.naive) * 100 : 0}%`, background: c.trueWk === 0 ? 'var(--st-disrupted)' : 'var(--st-covered)' }} /></div>
              </div>
            ))}
            <div className="sub" style={{ marginTop: 4 }}>Grey is what the contracts promise. Colour is what can really arrive now (max-flow min cut).</div></div></div>
        </div>
      </div>
    </>
  )
}
