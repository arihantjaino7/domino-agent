import { useEffect, useMemo, useState } from 'react'
import type { ViewId } from '../App'
import { api } from '../lib/api'
import { COUNTRY_LABELS, EX, GEO, GH, GW, LAND, P, PLANT_GEO, SY, VB, grid, iso } from '../lib/geo'
import { COL, COUNTRY, fmt, plural, usd, useModel, type Model } from '../lib/model'
import { useStore } from '../lib/store'
import { useToasts } from '../lib/toasts'
import type { NodeStatus } from '../lib/types'
import { fetchXray, type Xray, type XraySite } from '../lib/xray'
import { Arc, Block } from './OverviewView'

// The last scan and the world summary it was made for, kept across view switches. world_version restarts after a
// reset, so the key is the summary's content; the backend also caches by the content it scanned.
let lastScan: Xray | null = null
let lastKey = ''

/** Map colour for one site's outage: hidden single point of failure > single point of failure > only exposes orders. */
const tone = (s: XraySite): NodeStatus => (s.orders_late > 0 ? (s.hidden ? 'disrupted' : 'late') : s.orders_exposed > 0 ? 'covered' : 'none')

function XrayBoard({ m, scan, sel, pick }: { m: Model; scan: Xray; sel: XraySite | null; pick: (id: string) => void }) {
  const regions: Record<string, { sites: XraySite[]; status: NodeStatus; late: number }> = {}
  for (const s of scan.sites) {
    if (!s.region_name || !GEO[s.region_name]) continue
    const r = (regions[s.region_name] ??= { sites: [], status: 'none', late: 0 })
    r.sites.push(s)
    const t = tone(s)
    const order: NodeStatus[] = ['none', 'covered', 'late', 'disrupted']
    if (order.indexOf(t) > order.indexOf(r.status)) r.status = t
    r.late = Math.max(r.late, s.orders_late)
  }
  const items = Object.entries(regions).map(([rn, r]) => { const [gx, gy] = grid(...GEO[rn]); return { gx, gy, h: 6 + Math.min(r.late, 14) * 5, status: r.status, rn, plant: '' } })
  for (const [pid, ll] of Object.entries(PLANT_GEO)) { if (!m.N[pid]) continue; const [gx, gy] = grid(...ll); items.push({ gx, gy, h: 30, status: sel?.plants_hit.includes(pid) ? 'late' : 'none', rn: '', plant: pid }) }
  items.sort((a, b) => iso(a.gx, a.gy)[1] - iso(b.gx, b.gy)[1])
  const top = (rn: string | null | undefined) => { const it = items.find((i) => i.rn === rn); return it ? iso(it.gx, it.gy, it.h) : null }
  const ptop = (pid: string) => { const it = items.find((i) => i.plant === pid); return it ? iso(it.gx, it.gy, it.h) : null }
  const arcs: { p: number[]; q: number[]; lift: number }[] = []
  const from = sel ? top(sel.region_name) : null
  if (sel && from) {
    const seen = new Set<string>()
    for (const t1 of sel.tier1_hit) {
      const rn = m.N[t1]?.region ?? ''
      const q = rn && rn !== sel.region_name ? top(rn) : null
      if (q && !seen.has(rn)) { seen.add(rn); arcs.push({ p: from, q, lift: 46 }) }
      for (const pid of sel.plants_hit) {
        const pq = ptop(pid), pp = q ?? from
        if (pq && !seen.has(`${rn}>${pid}`)) { seen.add(`${rn}>${pid}`); arcs.push({ p: pp, q: pq, lift: 60 + Math.abs(pp[0] - pq[0]) * 0.15 }) }
      }
    }
  }
  const corners = [iso(0, 0), iso(GW, 0), iso(GW, GH), iso(0, GH)]
  const label = sel && from ? { x: from[0], y: from[1], title: m.short(sel.site), detail: sel.orders_late ? `${plural(sel.orders_late, 'order')} late if it stops` : sel.orders_exposed ? `${plural(sel.orders_exposed, 'order')} in danger, none late` : 'no order affected' } : null
  const lw = label ? Math.max(label.title.length * 6.6, label.detail.length * 6) + 24 : 0
  const lx = label ? Math.min(label.x + 30, VB.x + VB.w - lw - 6) : 0
  return (
    <svg className="board-svg" viewBox={`${VB.x} ${VB.y} ${VB.w} ${VB.h}`} preserveAspectRatio="xMidYMid meet" role="img" aria-label="Map: each place's colour and height show how much damage the worst site there would do if it stopped">
      <defs>
        <pattern id="xdots" width=".5" height=".5" patternUnits="userSpaceOnUse"><circle cx=".25" cy=".25" r=".09" fill="#55524d" /></pattern>
        <radialGradient id="xglowR"><stop offset="0" stopColor="#d9566e" stopOpacity=".5" /><stop offset="1" stopColor="#d9566e" stopOpacity="0" /></radialGradient>
        <radialGradient id="xglowP"><stop offset="0" stopColor="#e88aa0" stopOpacity=".18" /><stop offset="1" stopColor="#e88aa0" stopOpacity="0" /></radialGradient>
        <marker id="xarR" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="#d9566e" /></marker>
      </defs>
      <polygon points={P(corners)} fill="#151514" stroke="#262522" />
      <g transform={`matrix(${EX[0]} ${EX[1]} ${SY[0]} ${SY[1]} 0 0)`}>
        {LAND.map((poly, i) => <polygon key={i} points={P(poly.map(([lo, la]) => grid(lo, la)))} fill="url(#xdots)" stroke="#2c2b28" strokeWidth={0.6} vectorEffect="non-scaling-stroke" />)}
        {Object.entries(regions).filter(([, r]) => r.status === 'disrupted' || r.status === 'late').map(([rn, r]) => {
          const [gx, gy] = grid(...GEO[rn])
          return <circle key={rn} cx={gx} cy={gy} r={r.status === 'disrupted' ? 2.2 + Math.min(r.late, 14) * 0.12 : 1.4} fill={`url(#${r.status === 'disrupted' ? 'xglowR' : 'xglowP'})`} />
        })}
        {sel?.region_name && GEO[sel.region_name] && (() => {
          const [gx, gy] = grid(...GEO[sel.region_name])
          return (
            <circle cx={gx} cy={gy} r={1.2} fill="none" stroke="#edebe6" strokeWidth={1.2} vectorEffect="non-scaling-stroke">
              <animate attributeName="r" values="1;4" dur="2.4s" repeatCount="indefinite" /><animate attributeName="opacity" values=".8;0" dur="2.4s" repeatCount="indefinite" />
            </circle>
          )
        })()}
      </g>
      {COUNTRY_LABELS.map(([cn, lo, la]) => { const [x, y] = iso(...grid(lo, la)); return <text key={cn} className="country" x={x.toFixed(1)} y={y.toFixed(1)} textAnchor="middle" fontSize={11} fill="#5d5b56" letterSpacing=".06em">{cn}</text> })}
      {items.map((it) => (
        <g key={it.rn || it.plant} className={it.rn ? 'xr-block' : ''} onClick={it.rn ? () => pick(regions[it.rn].sites[0].site) : undefined}>
          <Block gx={it.gx} gy={it.gy} w={it.plant ? 0.6 : 0.48} h={it.h} status={it.status} plant={!!it.plant} />
        </g>
      ))}
      {arcs.map((a, i) => <Arc key={i} {...a} color={COL.disrupted} flow marker="xarR" />)}
      {label && (
        <g className="pin">
          <line x1={label.x} y1={label.y} x2={lx} y2={label.y - 18} stroke="#5d5b56" strokeWidth={1} />
          <rect x={lx} y={label.y - 37} width={lw} height={38} rx={10} fill="rgba(26,26,24,.94)" stroke="#3a3834" />
          <text x={lx + 12} y={label.y - 19} fontSize={12.5} fill="#edebe6" fontWeight={500}>{label.title}</text>
          <text x={lx + 12} y={label.y - 5} fontSize={11} fill="#8f8d87">{label.detail}</text>
        </g>
      )}
    </svg>
  )
}

function placeOf(s: XraySite) {
  return [s.region_name, COUNTRY[s.country ?? ''] ?? s.country].filter(Boolean).join(', ')
}

function SiteDetail({ m, scan, s, go }: { m: Model; scan: Xray; s: XraySite; go: (v: ViewId) => void }) {
  const busy = useStore((st) => st.busy)
  const working = busy || m.phase === 'running' || m.phase === 'approving'
  const active = s.paths.filter((p) => p.active)
  const backups = s.dependents.tier1_backup.filter((t) => !s.dependents.tier1_active.includes(t))
  const rehearse = async () => {
    useStore.setState({ busy: true, error: null })
    try {
      const r = await api.inject({ entity_ids: [s.site], kind: 'disruption', title: `Rehearsal: ${m.short(s.site)} stops`, capacity_factor: 0, duration_days: scan.duration_days })
      await useStore.getState().refresh()
      useToasts.getState().push(`${r.incident_id}: ${m.short(s.site)} stopped for ${scan.duration_days} days in the live world. Reset the world to undo.`)
      go('overview')
    } catch (e) {
      useStore.setState({ error: String((e as Error).message ?? e) })
    } finally {
      useStore.setState({ busy: false })
    }
  }
  const cap = s.confirmed?.capacity[0]
  return (
    <div className="card xr-detail"><div className="card-b">
      <div className="side-h"><h2>{s.name}</h2><span className="tag"><i className={`dot st-${tone(s)}`} />#{s.rank}</span></div>
      <div className="sub">Tier {s.tier} · makes {m.partOf(s.site)[1]} · {placeOf(s)}</div>
      <p className="plain">
        {s.hidden ? <>Kestrel has <b>no direct contract</b> with this site{s.operator_has_contract ? ` (its operator, ${s.operator}, has other sites that do)` : ''}, so a tier-1 view never sees it. </> : 'Kestrel buys from this site directly. '}
        {s.orders_late ? `If it stops for ${scan.duration_days} days, ${plural(s.orders_late, 'order')} will be late.` : s.orders_exposed ? `If it stops for ${scan.duration_days} days, ${plural(s.orders_exposed, 'order')} are in danger, but stock covers them.` : `If it stops for ${scan.duration_days} days, no order of yours is affected.`}
      </p>
      <dl className="facts">
        <div><dt>Orders late</dt><dd>{fmt(s.orders_late)}{s.strategic_late ? <span className="muted"> ({s.strategic_late} strategic)</span> : null}</dd></div>
        <div><dt>Late fees</dt><dd>{usd(s.penalty_cents)}</dd></div>
        <div><dt>Orders in danger</dt><dd>{fmt(s.orders_exposed)}</dd></div>
        <div><dt>First part runs out</dt><dd>{s.first_stockout_day == null ? '—' : `day ${s.first_stockout_day}`}</dd></div>
      </dl>
      {active.length > 0 && (
        <>
          <h3 className="xr-h3">Who depends on it</h3>
          {active.slice(0, 6).map((p, i) => (
            <div className="ev" key={i}>
              <div className="path">{p.path.map((id, j) => <span key={id + j}>{j > 0 && <i>→ </i>}{m.N[id]?.kind === 'plant' ? `${m.short(id)} factory` : m.short(id)}</span>)}</div>
              <div className="sub" style={{ marginTop: 3 }}>{p.component}{s.tier1_hit.includes(p.tier1) ? ' · this supplier is hit' : ''}</div>
            </div>
          ))}
          {active.length > 6 && <div className="sub" style={{ marginTop: 6 }}>and {active.length - 6} more paths</div>}
        </>
      )}
      {backups.length > 0 && <p className="plain">Backup lines built on it too: {backups.map((t) => m.short(t)).join(', ')}. They are not independent of this site.</p>}
      {s.confirmed && (
        <p className="plain xr-check">
          <i className="dot st-protected" /> Checked again on a sandbox copy of the graph{s.confirmed.matches_fast_pass ? ': same result' : ': the sandbox result is shown'}.
          {cap && ` Max-flow: ${cap.component} into ${m.short(cap.plant)} drops from ${fmt(cap.healthy_wk)} to ${fmt(cap.during_outage_wk)} a week.`}
        </p>
      )}
      <button type="button" className="btn btn-accent wide" disabled={working} onClick={() => void rehearse()}>{busy ? 'Stopping the site' : 'Rehearse this disruption'}</button>
      <div className="sub" style={{ marginTop: 8 }}>Stops this site at 0% for {scan.duration_days} days in the live world, like a manual stop, so the other views show what follows. Starting a run resets the world first.</div>
    </div></div>
  )
}

/* ---------- Risk X-ray ---------- */
export function XrayView({ go }: { go: (v: ViewId) => void }) {
  const m = useModel()
  const summary = useStore((s) => s.summary)
  const key = summary ? JSON.stringify([summary.world_version, summary.incidents, summary.totals]) : ''
  const [scan, setScan] = useState<Xray | null>(lastScan)
  const [error, setError] = useState<string | null>(null)
  const [sel, setSel] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'hidden'>('all')
  const [all, setAll] = useState(false)
  useEffect(() => {
    if (!key || (lastScan && lastKey === key)) return
    let live = true
    fetchXray().then((x) => { lastScan = x; lastKey = key; if (live) { setScan(x); setError(null) } }).catch((e) => live && setError(String(e.message ?? e)))
    return () => { live = false }
  }, [key])
  const rows = useMemo(() => (scan?.sites ?? []).filter((s) => filter === 'all' || (s.hidden && s.orders_late > 0)), [scan, filter])
  const topHidden = scan?.sites.find((s) => s.hidden && s.orders_late > 0)
  const chosen = scan?.sites.find((s) => s.site === sel) ?? topHidden ?? rows[0] ?? null
  const max = Math.max(1, ...(scan?.sites ?? []).map((s) => s.penalty_cents))
  const shown = all ? rows : rows.slice(0, 12)
  const offMap = (scan?.sites ?? []).filter((s) => s.orders_late > 0 && !(s.region_name && GEO[s.region_name])).length

  return (
    <>
      {error && <div className="banner" role="alert">Risk X-ray could not run: {error}</div>}
      {!scan && !error && (
        <section className="ov-hero"><div className="ov-story">
          <div className="xr-eyebrow">Risk X-ray</div>
          <h1>Where would one stopped site hurt most?</h1>
          <p className="lede"><span className="progress"><i className="spin" />DOMINO is stopping each supplier site in turn on a model of today's world. This takes a few seconds the first time.</span></p>
        </div></section>
      )}
      {scan && (
        <>
          <section className="ov-hero">
            <div className="ov-story">
              <div className="xr-eyebrow">Risk X-ray · each site stopped alone for {scan.duration_days} days</div>
              <h1>{topHidden ? `${m.short(topHidden.site)} is your biggest hidden weak point.` : scan.single_points_of_failure ? 'Your weak points are all suppliers you buy from directly.' : 'No single site can make an order late.'}</h1>
              <p className="lede">
                {topHidden
                  ? `Kestrel has no contract with ${topHidden.name}, but ${plural(topHidden.tier1_hit.length, 'of your suppliers', 'of your suppliers')} need it. If it stops, ${plural(topHidden.orders_late, 'order')} will be late. `
                  : ''}
                {`DOMINO stopped each of the ${scan.scanned} sites that feed a supplier or sell to a factory (tier 1 included), one at a time, on a model of today's world. Nothing in the graph is changed. `}
                {scan.baseline.projected_late ? `The world already has ${plural(scan.baseline.projected_late, 'late order')}; the numbers are what each stop would add. ` : ''}
                A site that is not in the graph is not scanned, which is not the same as safe.
              </p>
            </div>
            <div className="ov-nums">
              <div><b style={{ color: 'var(--st-late)' }}>{fmt(scan.single_points_of_failure)}</b><span>sites that alone make orders late</span></div>
              <div><b style={{ color: 'var(--st-disrupted)' }}>{fmt(scan.hidden_single_points_of_failure)}</b><span>of them hidden: no direct contract</span></div>
              <div><b>{fmt(scan.scanned)}</b><span>sites scanned</span></div>
            </div>
          </section>

          <section className="ov-main">
            <div className="card map-card">
              <div className="map-head">
                <div><h2>Where one stop hurts most</h2><div className="sub">Colour and height show the worst site in each place. Click a place or a row to see who depends on it.</div></div>
              </div>
              <div className="board-stage"><XrayBoard m={m} scan={scan} sel={chosen} pick={setSel} /></div>
              <div className="map-legend" style={{ padding: '0 18px 16px' }}>
                <span><i className="dot st-disrupted" />Hidden, makes orders late</span><span><i className="dot st-late" />Makes orders late</span><span><i className="dot st-covered" />Only puts orders in danger</span><span><i className="dot" />No effect</span>
                {offMap > 0 && <span className="muted">{plural(offMap, 'weak point')} outside the map, listed below</span>}
              </div>
            </div>
            <div className="ov-side">{chosen && <SiteDetail m={m} scan={scan} s={chosen} go={go} />}</div>
          </section>

          <section className="ov-details">
            <div className="card"><div className="card-b">
              <div className="side-h xr-list-h">
                <div><h2>Every site, ranked</h2><div className="sub">By orders made late, then late fees, then orders in danger. Each stop is tested alone at 0%.</div></div>
                <div className="chip-toggle" role="group" aria-label="Which sites">
                  <button type="button" className={filter === 'all' ? 'on' : ''} onClick={() => setFilter('all')}>All sites</button>
                  <button type="button" className={filter === 'hidden' ? 'on' : ''} onClick={() => setFilter('hidden')}>Hidden weak points</button>
                </div>
              </div>
              <div className="xr-list" role="list">
                {shown.map((s) => (
                  <button type="button" role="listitem" key={s.site} className={`xr-row ${chosen?.site === s.site ? 'on' : ''}`} onClick={() => { setSel(s.site); window.scrollTo({ top: 0, behavior: 'smooth' }) }}>
                    <span className="xr-rank num">{s.rank}</span>
                    <span className="xr-name">
                      <b>{s.name}</b>
                      <span className="sub">Tier {s.tier} · {m.partOf(s.site)[1]} · {placeOf(s)}</span>
                      {s.hidden ? <span className="tag xr-tag"><i className="dot st-disrupted" />No direct contract</span> : null}
                    </span>
                    <span className="xr-metrics">
                      <span><b className="num" style={{ color: s.orders_late ? 'var(--st-late)' : undefined }}>{fmt(s.orders_late)}</b><span className="sub">late</span></span>
                      <span><b className="num">{fmt(s.orders_exposed)}</b><span className="sub">in danger</span></span>
                      <span className="xr-fee"><b className="num">{usd(s.penalty_cents)}</b><span className="sub">late fees</span><i className="xr-bar"><i style={{ width: `${(s.penalty_cents / max) * 100}%`, background: COL[tone(s)] }} /></i></span>
                    </span>
                  </button>
                ))}
                {rows.length === 0 && <p className="plain">No hidden site can make an order late on its own.</p>}
              </div>
              {rows.length > 12 && <button type="button" className="btn btn-ghost wide" onClick={() => setAll((a) => !a)}>{all ? 'Show the top 12' : `Show all ${rows.length}`}</button>}
              <div className="sub" style={{ marginTop: 10 }}>
                The top {plural(scan.confirmed.length, 'site')} were checked again on a GRAPH.COPY sandbox with the real incident and projection code, plus max-flow. Scan of world version {scan.world_version}{scan.cached ? ', cached' : ''}, {fmt(scan.timing_ms.total)} ms.
              </div>
            </div></div>
          </section>
        </>
      )}
    </>
  )
}
