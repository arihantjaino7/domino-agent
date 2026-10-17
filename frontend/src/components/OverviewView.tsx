import { useEffect, useRef, useState } from 'react'
import type { ViewId } from '../App'
import { COL, COUNTRY, RANK, cap1, fmt, plural, usd, useModel, type Model } from '../lib/model'
import { useStore } from '../lib/store'
import type { NodeStatus } from '../lib/types'
import { GEO, PLANT_GEO } from '../lib/geo'
import { Progress, RunPanel } from './Controls'

/* eslint-disable @typescript-eslint/no-explicit-any */

/* ---------- the map: a tilted plane of the region, one block per city, height = number of supplier sites ---------- */
const LAND: [number, number][][] = [
  [[97, 41], [122, 41], [121.5, 39], [118.5, 38.5], [119, 37], [122.5, 37], [120, 35], [121.5, 32], [122, 29.5], [120, 26], [117, 23.5], [113.5, 22], [110, 21.2], [108.5, 21.6], [106, 20], [106.6, 17], [109, 15], [109.2, 11.6], [105, 8.6], [104.6, 10.5], [102.8, 12], [101, 12.6], [100, 13.4], [99.3, 10.5], [100.2, 8], [101.6, 6.6], [103.4, 4], [104.3, 1.4], [103.4, 1.2], [101, 2.9], [100.3, 5], [99, 7.6], [98.4, 9.6], [97.8, 13], [97, 16]],
  [[124.6, 40], [128.2, 41], [129.6, 37], [129.3, 35.2], [127.2, 34.5], [126.2, 34.6], [126.6, 37], [125.2, 37.8]],
  [[129.6, 33.5], [131, 34.1], [132.2, 34], [134, 34.5], [134, 33.5], [132, 32.8], [131.4, 31.3], [130.2, 31.2], [129.8, 32.7]],
  [[121.1, 25.3], [122, 25], [121.4, 22.4], [120.7, 21.9], [120.1, 23], [120.2, 24.3]],
  [[108.6, 19.2], [110.3, 20.1], [111, 19.6], [109.6, 18.2]],
  [[120.6, 18.5], [122.2, 18.5], [122, 16], [121.5, 14], [120.5, 14.4], [120, 16]],
  [[115.5, 5], [116.8, 7], [119, 5.2], [117.8, 4], [115.4, 4.3]],
  [[97, 5.2], [98, 4], [100.3, 2.2], [102, 0.8], [103, 0], [97, 0]],
]
const COUNTRY_LABELS: [string, number, number][] = [['Thailand', 101.6, 17.2], ['Malaysia', 102.6, 3.0], ['Vietnam', 105.6, 16.2], ['China', 112, 30.5], ['Taiwan', 122.4, 23.4], ['South Korea', 128.4, 39.4], ['Japan', 132.2, 32.4]]
const LON0 = 97, LAT0 = 41, GW = 37, GH = 41, SC = 18, TH = (12 * Math.PI) / 180, SQ = 0.68
const EX = [Math.cos(TH) * SC, Math.sin(TH) * SQ * SC], SY = [-Math.sin(TH) * SC, Math.cos(TH) * SQ * SC]
const grid = (lon: number, lat: number): [number, number] => [lon - LON0, LAT0 - lat]
const iso = (gx: number, gy: number, z = 0): [number, number] => [gx * EX[0] + gy * SY[0], gx * EX[1] + gy * SY[1] - z]
const P = (pts: number[][]) => pts.map((p) => p.map((v) => v.toFixed(1)).join(',')).join(' ')
const VB = { x: -150, y: 0, w: 860, h: 560 }

function Block({ gx, gy, w, h, status, plant }: { gx: number; gy: number; w: number; h: number; status: NodeStatus; plant: boolean }) {
  const a = iso(gx - w, gy - w, h), b = iso(gx + w, gy - w, h), c = iso(gx + w, gy + w, h), d = iso(gx - w, gy + w, h)
  const b0 = iso(gx + w, gy - w), c0 = iso(gx + w, gy + w), d0 = iso(gx - w, gy + w)
  const hot = status !== 'none', col = COL[status]
  const side = hot ? { style: { fill: col } } : { fill: '#2a2926' }
  return (
    <g>
      <polygon points={P([b0, c0, c, b])} {...side} opacity={hot ? 0.55 : 1} /><polygon points={P([b0, c0, c, b])} fill="#000" opacity={hot ? 0.35 : 0.15} />
      <polygon points={P([d0, c0, c, d])} {...side} opacity={hot ? 0.55 : 1} /><polygon points={P([d0, c0, c, d])} fill="#000" opacity={hot ? 0.5 : 0.3} />
      {plant ? (
        <>
          <polygon points={P([a, b, c, d])} fillOpacity={0.18} strokeWidth={1.2} style={{ fill: hot ? col : '#3a3834', stroke: hot ? col : '#8f8d87' }} />
          <polygon points={P([iso(gx - w * 0.45, gy - w * 0.45, h), iso(gx + w * 0.45, gy - w * 0.45, h), iso(gx + w * 0.45, gy + w * 0.45, h), iso(gx - w * 0.45, gy + w * 0.45, h)])} style={{ fill: hot ? col : '#8f8d87' }} opacity={0.9} />
        </>
      ) : (
        <polygon points={P([a, b, c, d])} {...(hot ? { style: { fill: col } } : { fill: '#3a3834' })} />
      )}
    </g>
  )
}
function Arc({ p, q, lift, color, flow, marker }: { p: number[]; q: number[]; lift: number; color: string; flow: boolean; marker: string }) {
  const mx = (p[0] + q[0]) / 2, my = (p[1] + q[1]) / 2 - lift
  return <path className={flow ? 'flow' : ''} markerEnd={`url(#${marker})`} d={`M${p[0].toFixed(1)},${p[1].toFixed(1)} Q${mx.toFixed(1)},${my.toFixed(1)} ${q[0].toFixed(1)},${q[1].toFixed(1)}`} fill="none" style={{ stroke: color }} strokeWidth={1.8} strokeLinecap="round" />
}

interface Pin { x: number; y: number; title: string; detail: string; status: NodeStatus; step: number }
const OFFSETS: [number, number][] = [[44, -18], [40, 24], [30, -70], [-34, -40], [-40, 52], [-30, -92], [60, 64], [-60, -64], [70, -34], [-70, 20]]
/** Place each label at the first offset that stays on the map and does not cover an earlier one. */
function placePins(pins: Pin[]) {
  const placed: { x: number; y: number; w: number; h: number }[] = []
  return pins.map((p) => {
    const w = Math.max(p.title.length * 6.6 + 10, p.detail.length * 6) + 34, h = 38
    let best: { dx: number; dy: number; rx: number } | null = null
    for (const [dx, dy] of OFFSETS) {
      const rx = dx < 0 ? p.x + dx - w : p.x + dx, ry = p.y + dy - 19
      const inside = rx > VB.x + 4 && rx + w < VB.x + VB.w - 4 && ry > VB.y + 4 && ry + h < VB.y + VB.h - 4
      const clear = placed.every((r) => rx + w + 6 < r.x || r.x + r.w + 6 < rx || ry + h + 6 < r.y || r.y + r.h + 6 < ry)
      if (inside && clear) { best = { dx, dy, rx }; break }
      best ??= { dx, dy, rx }
    }
    const b = best as { dx: number; dy: number; rx: number }
    placed.push({ x: b.rx, y: p.y + b.dy - 19, w, h })
    return { ...p, dx: b.dx, dy: b.dy, rx: b.rx, w }
  })
}

function Board({ m, lens, focus }: { m: Model; lens: 'tier1' | 'domino'; focus: string | null }) {
  const d = m.d
  const disrupted = new Set<string>(d.declared?.site_ids ?? [])
  const exposed = new Set<string>(d.exposedTier1.map((x) => x.site))
  const rescue = new Set(m.suppliersInPlan)
  const regions: Record<string, { sites: number; status: NodeStatus; step: number }> = {}
  for (const n of Object.values(m.N)) {
    if (n.kind !== 'site' || !n.region || !GEO[n.region]) continue
    if (lens === 'tier1' && n.col !== 'tier1') continue
    const r = (regions[n.region] ??= { sites: 0, status: 'none', step: 0 })
    r.sites++
    const s = lens === 'tier1' ? 'none' : m.status(n.id)
    if (RANK[s] > RANK[r.status]) r.status = s
    const step = disrupted.has(n.id) ? 1 : exposed.has(n.id) ? 2 : rescue.has(n.id) ? 4 : 0
    if (lens === 'domino' && step && (!r.step || step < r.step)) r.step = step
  }
  const items = Object.entries(regions).map(([rn, r]) => { const [gx, gy] = grid(...GEO[rn]); return { gx, gy, h: 6 + r.sites * 6.5, status: r.status, rn, plant: '', step: r.status === 'none' ? 0 : r.step } })
  for (const [pid, ll] of Object.entries(PLANT_GEO)) { if (!m.N[pid]) continue; const [gx, gy] = grid(...ll); items.push({ gx, gy, h: 30, status: lens === 'tier1' ? 'none' : m.status(pid), rn: '', plant: pid, step: 3 }) }
  items.sort((a, b) => iso(a.gx, a.gy)[1] - iso(b.gx, b.gy)[1])
  const topOf = (siteId: string) => { const rn = m.N[siteId]?.region; const it = items.find((i) => i.rn === rn); return it ? iso(it.gx, it.gy, it.h) : null }
  const ptop = (pid: string) => { const it = items.find((i) => i.plant === pid); return it ? iso(it.gx, it.gy, it.h) : null }

  const pins: Pin[] = []
  const arcs: { p: number[]; q: number[]; lift: number; color: string; flow: boolean; marker: string; step: number }[] = []
  if (lens === 'domino' && d.declared) {
    const seen = new Set<string>()
    const pct = Math.round((d.declared.capacity_factor ?? 0) * 100)
    for (const sid of disrupted) {
      const t = topOf(sid); const rn = m.N[sid]?.region ?? ''
      if (!t || seen.has(rn)) continue
      seen.add(rn)
      pins.push({ x: t[0], y: t[1], title: `${cap1(m.kind)} stops ${m.short(sid)}`, detail: `${pct}% working until day ${d.declared.end_day}`, status: 'disrupted', step: 1 })
    }
    for (const t1 of d.exposedTier1) {
      const t = topOf(t1.site)
      for (const v of t1.via ?? []) { const o = topOf(v); if (o && t) arcs.push({ p: o, q: t, lift: 46, color: COL.disrupted, flow: true, marker: 'arR', step: 2 }) }
      const rn = m.N[t1.site]?.region ?? ''
      if (!t || seen.has(rn)) continue
      seen.add(rn)
      pins.push({ x: t[0], y: t[1], title: `${m.short(t1.site)}, ${rn}`, detail: `buys ${m.input[1]} from ${m.short(t1.via?.[0] ?? '')}`, status: m.status(t1.site), step: 2 })
    }
    for (const p of m.plants) {
      if (!p.exposed) continue
      const t = ptop(p.plant)
      if (!t) continue
      pins.push({ x: t[0], y: t[1], title: `Our ${m.short(p.plant)} factory`, detail: p.projected_late ? `${p.projected_late} orders will be late` : p.stockout_day ? `${m.part[1]} run out on day ${p.stockout_day}` : 'stock covers its orders', status: m.status(p.plant), step: 3 })
    }
    for (const po of m.plan?.pos ?? []) {
      const s = topOf(po.site_id), q = ptop(po.plant_id)
      if (s && q) arcs.push({ p: s, q, lift: 70 + Math.abs(s[0] - q[0]) * 0.18, color: COL.protected, flow: !m.executed, marker: 'arG', step: 4 })
    }
    for (const sid of m.suppliersInPlan) {
      const t = topOf(sid); const rn = m.N[sid]?.region ?? ''
      if (!t || seen.has(rn)) continue
      seen.add(rn)
      pins.push({ x: t[0], y: t[1], title: `${m.short(sid)}, ${rn}`, detail: m.executed ? `new ${m.part[1]} ordered` : `can send new ${m.part[1]}`, status: 'protected', step: 4 })
    }
  }
  const placed = placePins(pins)
  const corners = [iso(0, 0), iso(GW, 0), iso(GW, GH), iso(0, GH)]
  const on = (step: number) => (focus ? (String(step) === focus ? 'on' : '') : '')
  return (
    <svg className={`board-svg ${focus ? 'focus' : ''}`} viewBox={`${VB.x} ${VB.y} ${VB.w} ${VB.h}`} preserveAspectRatio="xMidYMid meet" role="img" aria-label="Map: the stopped site, the suppliers that depend on it, our factories and the rescue suppliers">
      <defs>
        <pattern id="dots" width=".5" height=".5" patternUnits="userSpaceOnUse"><circle cx=".25" cy=".25" r=".09" fill="#55524d" /></pattern>
        <radialGradient id="glowR"><stop offset="0" stopColor="#d9566e" stopOpacity=".55" /><stop offset="1" stopColor="#d9566e" stopOpacity="0" /></radialGradient>
        <radialGradient id="glowA"><stop offset="0" stopColor="#d7a85a" stopOpacity=".3" /><stop offset="1" stopColor="#d7a85a" stopOpacity="0" /></radialGradient>
        <radialGradient id="glowG"><stop offset="0" stopColor="#79b394" stopOpacity=".3" /><stop offset="1" stopColor="#79b394" stopOpacity="0" /></radialGradient>
        <marker id="arR" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="#d9566e" /></marker>
        <marker id="arG" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="#79b394" /></marker>
      </defs>
      <polygon points={P(corners)} fill="#151514" stroke="#262522" />
      <g transform={`matrix(${EX[0]} ${EX[1]} ${SY[0]} ${SY[1]} 0 0)`}>
        {Array.from({ length: GW / 2 + 1 }, (_, i) => <line key={`v${i}`} x1={i * 2} y1={0} x2={i * 2} y2={GH} stroke="#1f1e1c" vectorEffect="non-scaling-stroke" />)}
        {Array.from({ length: Math.floor(GH / 2) + 1 }, (_, i) => <line key={`h${i}`} x1={0} y1={i * 2} x2={GW} y2={i * 2} stroke="#1f1e1c" vectorEffect="non-scaling-stroke" />)}
        {LAND.map((poly, i) => <polygon key={i} points={P(poly.map(([lo, la]) => grid(lo, la)))} fill="url(#dots)" stroke="#2c2b28" strokeWidth={0.6} vectorEffect="non-scaling-stroke" />)}
        {Object.entries(regions).filter(([, r]) => r.status !== 'none').map(([rn, r]) => {
          const [gx, gy] = grid(...GEO[rn])
          const g = r.status === 'disrupted' ? 'glowR' : r.status === 'protected' ? 'glowG' : 'glowA'
          return (
            <g key={rn} data-step={r.step} className={on(r.step)}>
              <circle cx={gx} cy={gy} r={r.status === 'disrupted' ? 4.2 : 2.6} fill={`url(#${g})`} />
              {r.status === 'disrupted' && (
                <circle cx={gx} cy={gy} r={1.2} fill="none" stroke="#d9566e" strokeWidth={1.2} vectorEffect="non-scaling-stroke">
                  <animate attributeName="r" values="1;4.5" dur="2.4s" repeatCount="indefinite" /><animate attributeName="opacity" values=".9;0" dur="2.4s" repeatCount="indefinite" />
                </circle>
              )}
            </g>
          )
        })}
      </g>
      {COUNTRY_LABELS.map(([cn, lo, la]) => { const [x, y] = iso(...grid(lo, la)); return <text key={cn} className="country" x={x.toFixed(1)} y={y.toFixed(1)} textAnchor="middle" fontSize={11} fill="#5d5b56" letterSpacing=".06em">{cn}</text> })}
      {items.map((it) => (
        <g key={it.rn || it.plant} data-step={it.step} className={on(it.step)}>
          <Block gx={it.gx} gy={it.gy} w={it.plant ? 0.6 : 0.48} h={it.h} status={it.status} plant={!!it.plant} />
        </g>
      ))}
      {arcs.map((a, i) => <g key={i} data-step={a.step} className={on(a.step)}><Arc {...a} /></g>)}
      {placed.map((p, i) => {
        const tx = p.x + p.dx, ty = p.y + p.dy
        return (
          <g key={i} className={`pin ${on(p.step)}`} data-step={p.step}>
            <line x1={p.x} y1={p.y} x2={tx} y2={ty} stroke="#5d5b56" strokeWidth={1} />
            <circle cx={p.x} cy={p.y} r={2.6} style={{ fill: COL[p.status] }} />
            <rect x={p.rx} y={ty - 19} width={p.w} height={38} rx={10} fill="rgba(26,26,24,.94)" stroke="#3a3834" />
            <circle cx={p.rx + 15} cy={ty - 5} r={8} style={{ fill: COL[p.status] }} />
            <text x={p.rx + 15} y={ty - 1.5} textAnchor="middle" fontSize={10} fontWeight={600} fill="#111110">{p.step}</text>
            <text x={p.rx + 29} y={ty - 1} fontSize={12.5} fill="#edebe6" fontWeight={500}>{p.title}</text>
            <text x={p.rx + 29} y={ty + 13} fontSize={11} fill="#8f8d87">{p.detail}</text>
          </g>
        )
      })}
    </svg>
  )
}

/* ---------- Overview ---------- */
export function OverviewView({ go }: { go: (v: ViewId) => void }) {
  const m = useModel()
  const st = useStore()
  const [lens, setLens] = useState<'tier1' | 'domino'>('domino')
  const [focus, setFocus] = useState<string | null>(null)
  const toured = useRef(false)
  const d = m.d
  const T = m.totals ?? st.summary?.totals
  const ready = !!m.totals && !!d.declared
  // a one-time walk through the four steps the first time a full story is on screen
  useEffect(() => {
    if (!ready || toured.current || matchMedia('(prefers-reduced-motion: reduce)').matches) return
    toured.current = true
    const ids = ['1', '2', '3', '4', null].map((n, i) => setTimeout(() => setFocus(n), 900 + i * 1700))
    return () => ids.forEach(clearTimeout)
  }, [ready])

  const site = m.site
  const rec = m.rec
  const t1 = d.tier1View ?? 0, mt = d.exposedTier1.length
  let h1: string, lede: string
  if (m.phase === 'idle' || !T) {
    h1 = 'Your supply chain is running normally.'
    lede = `${fmt(T?.orders)} customer orders, ${fmt(T?.projected_late ?? 0)} projected late. Pick a disruption below to watch DOMINO find the problem, plan a fix and ask for your OK.`
  } else if (m.noExposure) {
    h1 = d.report?.headline ?? 'Nothing in your supply chain is affected.'
    lede = 'DOMINO checked the graph and found no supplier of yours in the affected area. Not being in the graph does not mean safe, so the report says so.'
  } else if (!ready) {
    h1 = d.declared ? `A ${m.kind} stopped ${site ? m.short(site.id) : 'a supplier'}. DOMINO is tracing who is affected.` : 'DOMINO is reading the alert.'
    lede = d.alert ?? ''
  } else if (m.executed && rec) {
    h1 = `Plan approved. ${rec.protected_projected} of the ${T.projected_late} late orders are now protected (projected).`
    lede = `New ${m.part[1]} are ordered from ${plural(m.suppliersInPlan.length, 'other supplier')}. They have not arrived yet, so these orders are protected on paper until the parts land.`
  } else {
    h1 = `A ${m.kind} stopped ${site ? m.short(site.id) : 'a supplier'}. ${T.exposed === 1 ? '1 customer order is' : `${T.exposed} customer orders are`} in danger.`
    lede = `DOMINO followed the supply chain from the stopped site to your customers.${rec ? ` It found a plan that saves ${rec.protected_projected} of the ${T.projected_late} orders that would be late.` : ''}${m.phase === 'awaiting' ? ' You only need to say yes.' : ''}`
  }
  const late = m.executed && rec ? rec.late : T?.projected_late
  const fees = m.executed && rec ? rec.penalty_cents : T?.penalty_exposure_cents
  const deps = d.trace?.shared_upstream?.[0]
  const offMap = m.plants.filter((p) => p.exposed && !PLANT_GEO[p.plant])

  return (
    <>
      <section className="ov-hero">
        <div className="ov-story">
          <h1>{h1}</h1>
          <p className="lede">{lede}</p>
          {(m.phase === 'running' || m.phase === 'approving') && <div style={{ marginTop: 10 }}><Progress /></div>}
        </div>
        <div className="ov-nums">
          <div><b>{fmt(T?.exposed ?? 0)}</b><span>orders in danger</span></div>
          <div><b style={{ color: `var(--st-${m.executed ? 'protected' : late ? 'late' : 'none'})` }}>{fmt(late ?? 0)}</b><span>{m.executed ? 'still late with the plan' : 'will be late if nobody acts'}</span></div>
          <div><b>{usd(fees ?? 0)}</b><span>{m.executed ? 'late fees with the plan' : 'late fees if nobody acts'}</span></div>
        </div>
      </section>

      {(m.phase === 'idle' || m.phase === 'failed' || (m.phase === 'done' && !d.declared)) && (
        <div className="card" style={{ marginBottom: 16 }}><div className="card-b">
          <div className="side-h"><h2>{m.phase === 'idle' ? 'Start a disruption' : 'Run again'}</h2><span className="sub">{st.mode === 'scripted' ? 'Demo mode: free and offline' : st.mode === 'replay' ? 'Replay: a recorded run, nothing is changed' : st.mode === 'mcp' ? 'Claude Code drives DOMINO' : 'Claude runs in the backend'}</span></div>
          <RunPanel />
        </div></div>
      )}

      <section className="ov-main">
        <div className="card map-card">
          <div className="map-head">
            <div><h2>What is happening, step by step</h2><div className="sub">{lens === 'domino' ? (ready ? 'Hover a step below to see it on the map.' : 'Places with suppliers. Colours appear as DOMINO finds problems.') : 'This is all a tier-1 view can see.'}</div></div>
            <div className="chip-toggle" role="group" aria-label="Who is looking">
              <button type="button" className={lens === 'tier1' ? 'on' : ''} onClick={() => setLens('tier1')}>Tier-1 view</button>
              <button type="button" className={lens === 'domino' ? 'on' : ''} onClick={() => setLens('domino')}>DOMINO</button>
            </div>
          </div>
          <div className="board-stage">
            <Board m={m} lens={lens} focus={lens === 'domino' ? focus : null} />
            {lens === 'tier1' && d.trace && <div className="board-caption">A tier-1 view only checks the suppliers you buy from directly. It finds <b>{t1}</b> problems, because the stopped site is one step further back.</div>}
          </div>
          {lens === 'domino' && ready ? (
            <ol className="map-steps">
              {([
                [1, 'disrupted', 'The disruption', `${site ? m.short(site.id) : 'A supplier'} makes ${m.input[1]}${site?.region ? ` in ${site.region}` : ''}. A ${m.kind} stops it until day ${d.declared.end_day}.`],
                [2, 'covered', `Who needs those ${m.input[1]}`, `${mt === 1 ? '1 of your direct suppliers depends' : `${mt} of your direct suppliers depend`} on it. Red arrows show what no longer arrives.`],
                [3, m.executed ? 'protected' : 'late', 'Our factories', `${m.plants.filter((p) => p.projected_late).map((p) => m.short(p.plant)).join(' and ') || 'Our factories'} run short of ${m.part[1]}. ${m.executed && rec ? `${plural(rec.late, 'order')} still late.` : `${plural(T.projected_late, 'order')} would be late.`}`],
                [4, 'protected', 'The rescue', rec ? `Green arrows: ${m.part[1]} from ${plural(m.suppliersInPlan.length, 'other supplier')}. ${m.executed ? 'Ordered.' : 'Starts when you approve.'}` : 'DOMINO is still testing plans.'],
              ] as [number, NodeStatus, string, string][]).map(([n, sv, t, txt]) => (
                <li key={n} tabIndex={0} className={focus === String(n) ? 'on' : ''} onMouseEnter={() => setFocus(String(n))} onMouseLeave={() => setFocus(null)} onFocus={() => setFocus(String(n))} onBlur={() => setFocus(null)} onClick={() => setFocus(String(n))}>
                  <span className="n" style={{ background: COL[sv] }}>{n}</span>
                  <div><b>{t}</b><span>{txt}</span></div>
                </li>
              ))}
            </ol>
          ) : (
            <div className="map-legend" style={{ padding: '0 18px 16px' }}>
              <span><i className="dot st-disrupted" />Stopped</span><span><i className="dot st-late" />Will be late</span><span><i className="dot st-covered" />In danger</span><span><i className="dot st-protected" />Rescue</span><span><i className="dot" />Not affected</span>
            </div>
          )}
        </div>

        <div className="ov-side">
          <div className="card"><div className="card-b">
            <div className="side-h"><h2>What happened</h2>{d.declared && <span className="tag"><i className="dot st-disrupted pulse" />Day 0</span>}</div>
            <p className="plain">{d.alert ?? (m.phase === 'idle' ? 'No disruption yet. Pick one to start.' : 'Waiting for the alert.')}</p>
            {site && d.declared && (
              <dl className="facts">
                <div><dt>Site hit</dt><dd>{m.short(site.id)}, {site.region} ({COUNTRY[site.country ?? ''] ?? site.country})</dd></div>
                <div><dt>It makes</dt><dd>{m.input[1]}</dd></div>
                <div><dt>Working</dt><dd>{Math.round((d.declared.capacity_factor ?? 0) * 100)}% until day {d.declared.end_day}</dd></div>
              </dl>
            )}
          </div></div>
          <FixCard m={m} go={go} />
        </div>
      </section>

      {ready && (
        <section className="ov-details">
          <h2 className="sec-title">More details</h2>
          <div className="detail-grid">
            <div className="card"><div className="card-b"><div className="side-h"><h3>Our factories</h3><span className="sub">orders in danger</span></div>
              {m.plants.map((p) => {
                const lt = p.projected_late, exp = p.exposed - lt
                return (
                  <div className="plant-row" key={p.plant}><span>{m.short(p.plant)}</span>
                    <div className="stack" title={`${p.orders} orders, ${p.exposed} in danger, ${lt} will be late`}>
                      <i style={{ width: `${(lt / p.orders) * 100}%`, background: 'var(--st-late)' }} /><i style={{ width: `${(exp / p.orders) * 100}%`, background: 'var(--st-covered)', opacity: 0.75 }} />
                    </div>
                    <span className="num" style={{ textAlign: 'right' }}>{p.exposed} of {p.orders}</span></div>
                )
              })}
              <div className="sub" style={{ marginTop: 8, display: 'flex', gap: 12 }}><span><i className="dot st-late" /> will be late</span><span><i className="dot st-covered" /> stock still covers it</span></div>
            </div></div>
            <div className="card"><div className="card-b"><div className="side-h"><h3>When {m.part[1]} run out</h3><span className="sub">day 0 to {m.horizon}</span></div>
              <div className="clock"><div className="track" />
                {m.plants.filter((p) => p.stockout_day != null).map((p) => (
                  <span key={p.plant} className="mk" style={{ left: `${(p.stockout_day / m.horizon) * 100}%`, top: 0 }}>{m.short(p.plant)}, day {p.stockout_day}<i style={{ background: p.projected_late ? 'var(--st-late)' : 'var(--st-covered)' }} /></span>
                ))}
                <span className="mk" style={{ left: `${(d.declared.end_day / m.horizon) * 100}%`, top: 22 }}><i style={{ background: 'var(--ink-2)' }} />{site ? m.short(site.id) : 'Site'} works again, {d.declared.end_day}</span>
              </div><div className="clock-scale"><span>today</span><span>day {m.horizon}</span></div></div></div>
            {deps && (
              <div className="card"><div className="card-b"><div className="side-h"><h3>The hidden weak point</h3></div>
                <p className="plain">{m.short(deps.site)} sends {m.partOf(deps.site)[1]} to {deps.fan_out} of your suppliers. One {m.kind} hits all of them.</p>
                <div className="feed-list">{deps.dependents.map((x: string) => <div className="feed-item" key={x}><i className={`dot st-${m.status(x)}`} />{m.name(x)}</div>)}</div></div></div>
            )}
            <div className="card"><div className="card-b"><div className="side-h"><h3>What a tier-1 view misses</h3></div>
              <div className="lens-compare">
                <div><span className="sub">Tier-1 view</span><b>{t1}</b><span className="sub">suppliers in trouble</span></div>
                <div style={{ boxShadow: 'inset 0 0 0 1px var(--accent-soft)' }}><span className="sub">DOMINO</span><b>{mt}</b><span className="sub">suppliers in trouble</span></div>
              </div>
              <div className="sub" style={{ marginTop: 8 }}>If a site is not in your data, it is not automatically safe.</div></div></div>
            <div className="card"><div className="card-b"><div className="side-h"><h3>Money at risk</h3><span className="sub">if nobody acts</span></div>
              <dl className="facts"><div><dt>Sales at risk</dt><dd>{usd(T.revenue_at_risk_cents)}</dd></div><div><dt>Late fees</dt><dd>{usd(T.penalty_exposure_cents)}</dd></div>{rec && <div><dt>Late fees with plan</dt><dd>{usd(rec.penalty_cents)}</dd></div>}</dl></div></div>
            {offMap.length > 0 && (
              <div className="card"><div className="card-b"><div className="side-h"><h3>Not on the map</h3></div>
                {offMap.map((p) => <p className="plain" key={p.plant}>Our {m.short(p.plant)} factory has {p.exposed} orders in danger{p.projected_late ? `, ${p.projected_late} will be late` : ', and stock covers all of them'}.</p>)}</div></div>
            )}
          </div>
        </section>
      )}
      {m.phase === 'done' && d.declared && (
        <div className="card" style={{ marginTop: 16 }}><div className="card-b">
          <div className="side-h"><h2>Try another disruption</h2><span className="sub">a demo run starts from a fresh world</span></div>
          <RunPanel compact />
        </div></div>
      )}
    </>
  )
}

function FixCard({ m, go }: { m: Model; go: (v: ViewId) => void }) {
  const approve = useStore((s) => s.approve)
  const rec = m.rec
  if (!m.plan || !rec) {
    return (
      <div className="card fix-card"><div className="card-b">
        <div className="side-h"><h2>The fix</h2></div>
        <p className="plain">{m.noExposure ? 'DOMINO found no order of yours to protect. Not being in the graph does not mean safe, so check suppliers that are not in it.' : m.phase === 'idle' ? 'When a disruption hits, DOMINO tests five plans on copies of the graph and puts the one it recommends here for your OK.' : 'DOMINO is still testing plans.'}</p>
        {(m.phase === 'running') && <div style={{ marginTop: 10 }}><Progress /></div>}
      </div></div>
    )
  }
  return (
    <div className={`card fix-card ${m.executed ? 'done' : ''}`}><div className="card-b">
      <div className="side-h"><h2>{m.executed ? 'The plan is running' : 'The fix'}</h2><span className="tag"><i className={`dot st-${m.executed ? 'protected' : 'covered'}`} />{m.executed ? 'Approved' : m.phase === 'approving' ? 'Placing orders' : 'Needs your OK'}</span></div>
      <p className="plain">Buy {m.part[1]} from {plural(m.suppliersInPlan.length, 'other supplier')}: {m.suppliersInPlan.map((id) => m.short(id)).join(', ')}.</p>
      <dl className="facts">
        <div><dt>Cost</dt><dd>{usd(rec.spend_cents)} <span className="muted">of {usd(m.sim?.budget_cents)} budget</span></dd></div>
        <div><dt>Orders saved</dt><dd>{rec.protected_projected}, protected (projected)</dd></div>
        <div><dt>Still late</dt><dd>{rec.late} {rec.late === 1 ? 'order' : 'orders'}</dd></div>
      </dl>
      {m.executed ? (
        <button type="button" className="btn btn-ghost wide" onClick={() => go('shipments')}>Track the shipments</button>
      ) : (
        <div className="fix-actions">
          <button type="button" className="btn btn-accent" disabled={m.phase !== 'awaiting'} onClick={() => void approve()}>{m.phase === 'approving' ? 'Approving' : 'Approve plan'}</button>
          <button type="button" className="btn btn-ghost" onClick={() => go('agent')}>How DOMINO decided</button>
        </div>
      )}
    </div></div>
  )
}
