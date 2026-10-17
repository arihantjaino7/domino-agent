/* DOMINO war room concept: five views in one shell. Static data from data.js (a captured scripted run). */
(() => {
  const D = window.DOMINO
  const N = Object.fromEntries(D.nodes.map((n) => [n.id, n]))
  const name = (id) => N[id]?.label ?? id
  const usd = (cents) => '$' + Math.round(cents / 100).toLocaleString('en-US')
  const usdW = (dollars) => '$' + Math.round(dollars).toLocaleString('en-US')
  const fmt = (n) => Number(n).toLocaleString('en-US')
  const $ = (s, r = document) => r.querySelector(s)
  const $$ = (s, r = document) => [...r.querySelectorAll(s)]
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c])

  const state = { view: 'overview', approved: false, lens: 'domino', po: 0, node: null, factory: 'PL-PEN', focusCell: null, agentSeen: false, netSeen: false }
  const COL = { disrupted: 'var(--st-disrupted)', late: 'var(--st-late)', covered: 'var(--st-covered)', protected: 'var(--st-protected)', none: 'var(--st-none)' }
  const RANK = { none: 0, protected: 1, covered: 2, late: 3, disrupted: 4 }
  const st = (id) => (state.approved ? D.statusAfter : D.status)[id] || 'none'
  const hotOf = (eid) => (state.approved ? D.hotAfter : D.hot)[eid] || null
  const S4 = D.strategies.find((s) => s.strategy === D.recommended)
  const S0 = D.strategies.find((s) => s.strategy === 'S0')
  const protectedSet = new Set(D.receipt.orders_protected)
  const PLANT_SHORT = { 'PL-PEN': 'Penang', 'PL-BAC': 'Bac Ninh', 'PL-GDL': 'Guadalajara' }
  const COUNTRY = { TH: 'Thailand', MY: 'Malaysia', VN: 'Vietnam', KR: 'South Korea', JP: 'Japan', MX: 'Mexico' }
  const H = D.trace.horizon
  const SITE = D.declared.site_ids[0]
  const plant = (id) => D.plants.find((p) => p.plant === id)
  const orderOf = (id) => D.orders.find((o) => o.order_id === id)
  const orderState = (o) => (state.approved && protectedSet.has(o.order_id) ? 'protected' : o.status === 'projected_late' ? 'late' : 'covered')
  const suppliersInPlan = [...new Set(D.plan.pos.map((p) => p.site_id))]
  // the kind of disruption comes from the run (flood, fire, quake, strike...); visuals stay generic
  const KIND = D.steps.find((x) => x.tool === 'declare_incident')?.args.kind ?? 'disruption'
  const KINDC = KIND[0].toUpperCase() + KIND.slice(1)

  const ICON = {
    overview: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 3 3 8l9 5 9-5-9-5Z"/><path d="m3 13 9 5 9-5"/><path d="m3 17.5 9 4.5 9-4.5" opacity=".5"/></svg>',
    network: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="5" cy="6" r="2"/><circle cx="5" cy="18" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="7" r="2"/><circle cx="19" cy="17" r="2"/><path d="M7 7l3.3 3.6M7 17l3.3-3.6M14 11.3 17 8M14 12.7l3 3.3"/></svg>',
    incident: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 20.5V11l5 3v-3l5 3v-3l5 3V4h3v16.5Z"/><path d="M7 17.5h2M12 17.5h2" opacity=".6"/></svg>',
    logistics: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="2.5" y="7" width="19" height="11" rx="1.5"/><path d="M6.5 7v11M10.5 7v11M14.5 7v11M18 9.5v6"/></svg>',
    agent: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="4" width="7" height="6" rx="1.5"/><rect x="14" y="14" width="7" height="6" rx="1.5"/><path d="M10 7h3a3 3 0 0 1 3 3v4"/><path d="M8 20h-1a4 4 0 0 1-4-4v-1" opacity=".5"/></svg>',
  }
  const VIEWS = [['overview', 'Overview'], ['network', 'Supply chain'], ['incident', 'Factories'], ['logistics', 'Shipments'], ['agent', 'AI agent']]

  /* ---------------- shell ---------------- */
  function shell() {
    $('#railNav').innerHTML = VIEWS.map(([id, t]) => `<button data-go="${id}" title="${t}" aria-label="${t}">${ICON[id]}</button>`).join('')
    $('#bottomNav').innerHTML = VIEWS.map(([id, t]) => `<button data-go="${id}">${ICON[id]}<span>${t}</span></button>`).join('')
    $('#topTabs').innerHTML = VIEWS.map(([id, t]) => `<button data-go="${id}">${t}</button>`).join('')
    $('#runId').textContent = D.source.run_id
    const q = new URLSearchParams(location.search) // ?approved=1&node=trace&factory=S-VOLT-AYU: jump to a state when reviewing
    if (q.get('shot')) document.documentElement.classList.add('shot')
    if (q.get('approved') === '1') state.approved = true
    if (q.get('node')) state.node = q.get('node')
    if (q.get('factory')) state.factory = q.get('factory')
    if (q.get('still') === '1') { state.agentSeen = true; state.netSeen = true }
    document.addEventListener('click', (e) => {
      const go = e.target.closest('[data-go]')
      if (go) { go.blur?.(); setView(go.dataset.go) }
    })
    window.addEventListener('hashchange', () => setView(location.hash.slice(1) || 'overview', false))
    setView(location.hash.slice(1) || 'overview', false)
  }
  function setView(v, push = true) {
    if (!VIEWS.some(([id]) => id === v)) v = 'overview'
    state.view = v
    if (push && location.hash.slice(1) !== v) history.replaceState(null, '', '#' + v)
    $$('[data-go]').forEach((b) => b.classList.toggle('on', b.dataset.go === v))
    $$('.view').forEach((s) => s.classList.toggle('on', s.id === 'view-' + v))
    render()
    window.scrollTo({ top: 0 })
  }
  function render() {
    $('#runState').innerHTML = state.approved
      ? '<i class="dot st-protected"></i>Plan approved and checked'
      : '<i class="dot st-covered pulse"></i>Waiting for your OK'
    ;({ overview, network, incident, logistics, agent })[state.view]()
  }
  function approve() { state.approved = true; render() }
  function unapprove() { state.approved = false; render() }
  const head = (title, text, right = '') => `<div class="page-head"><div><h1>${title}</h1><p class="lede">${text}</p></div>${right}</div>`

  /* ================= OVERVIEW ================= */
  // schematic lon/lat (nudged so neighbouring cities do not overlap)
  const GEO = {
    Ayutthaya: [100.6, 14.6], Chonburi: [101.4, 12.9], Penang: [100.2, 5.6], 'Johor Bahru': [103.8, 1.6],
    'Hai Phong': [106.9, 20.6], Shenzhen: [114.5, 22.3], Dongguan: [113.2, 23.3], Wuhan: [114.3, 30.6],
    Shanghai: [121.8, 30.9], Suzhou: [120.3, 31.7], Taichung: [120.3, 24.1], Hsinchu: [121.3, 25.2], Tainan: [120.1, 22.8],
    Suwon: [126.7, 37.5], Cheongju: [127.6, 36.5], Gumi: [128.8, 35.7], Kumamoto: [130.8, 32.6],
  }
  const PLANT_GEO = { 'PL-PEN': [101.3, 4.5], 'PL-BAC': [105.6, 21.9] }
  const OFFBOARD = ['Monterrey', 'Houston', 'Brno']
  const LAND = [
    [[97, 41], [122, 41], [121.5, 39], [118.5, 38.5], [119, 37], [122.5, 37], [120, 35], [121.5, 32], [122, 29.5], [120, 26], [117, 23.5], [113.5, 22], [110, 21.2], [108.5, 21.6], [106, 20], [106.6, 17], [109, 15], [109.2, 11.6], [105, 8.6], [104.6, 10.5], [102.8, 12], [101, 12.6], [100, 13.4], [99.3, 10.5], [100.2, 8], [101.6, 6.6], [103.4, 4], [104.3, 1.4], [103.4, 1.2], [101, 2.9], [100.3, 5], [99, 7.6], [98.4, 9.6], [97.8, 13], [97, 16]],
    [[124.6, 40], [128.2, 41], [129.6, 37], [129.3, 35.2], [127.2, 34.5], [126.2, 34.6], [126.6, 37], [125.2, 37.8]],
    [[129.6, 33.5], [131, 34.1], [132.2, 34], [134, 34.5], [134, 33.5], [132, 32.8], [131.4, 31.3], [130.2, 31.2], [129.8, 32.7]],
    [[121.1, 25.3], [122, 25], [121.4, 22.4], [120.7, 21.9], [120.1, 23], [120.2, 24.3]],
    [[108.6, 19.2], [110.3, 20.1], [111, 19.6], [109.6, 18.2]],
    [[120.6, 18.5], [122.2, 18.5], [122, 16], [121.5, 14], [120.5, 14.4], [120, 16]],
    [[115.5, 5], [116.8, 7], [119, 5.2], [117.8, 4], [115.4, 4.3]],
    [[97, 5.2], [98, 4], [100.3, 2.2], [102, 0.8], [103, 0], [97, 0]],
  ]
  const LON0 = 97, LAT0 = 41, GW = 37, GH = 41, SC = 18, TH = (12 * Math.PI) / 180, SQ = 0.68
  const EX = [Math.cos(TH) * SC, Math.sin(TH) * SQ * SC], SY = [-Math.sin(TH) * SC, Math.cos(TH) * SQ * SC]
  const grid = (lon, lat) => [lon - LON0, LAT0 - lat]
  const iso = (gx, gy, z = 0) => [gx * EX[0] + gy * SY[0], gx * EX[1] + gy * SY[1] - z]
  const P = (pts) => pts.map((p) => p.map((v) => v.toFixed(1)).join(',')).join(' ')

  function regionStats(lens) {
    const out = {}
    for (const n of D.nodes) {
      if (n.kind !== 'site' || !GEO[n.region]) continue
      if (lens === 'tier1' && n.col !== 'tier1') continue
      const r = (out[n.region] ??= { sites: 0, status: 'none' })
      r.sites++
      const s = lens === 'tier1' ? 'none' : st(n.id)
      if (RANK[s] > RANK[r.status]) r.status = s
    }
    return out
  }
  function block(gx, gy, w, h, status, isPlant) {
    const a = iso(gx - w, gy - w, h), b = iso(gx + w, gy - w, h), c = iso(gx + w, gy + w, h), d = iso(gx - w, gy + w, h)
    const b0 = iso(gx + w, gy - w), c0 = iso(gx + w, gy + w), d0 = iso(gx - w, gy + w)
    const hot = status !== 'none', col = COL[status]
    const side = hot ? `style="fill:${col}"` : 'fill="#2a2926"'
    return `<g>
      <polygon points="${P([b0, c0, c, b])}" ${side} opacity="${hot ? 0.55 : 1}"/><polygon points="${P([b0, c0, c, b])}" fill="#000" opacity="${hot ? 0.35 : 0.15}"/>
      <polygon points="${P([d0, c0, c, d])}" ${side} opacity="${hot ? 0.55 : 1}"/><polygon points="${P([d0, c0, c, d])}" fill="#000" opacity="${hot ? 0.5 : 0.3}"/>
      ${isPlant
        ? `<polygon points="${P([a, b, c, d])}" fill-opacity=".18" stroke-width="1.2" style="fill:${hot ? col : '#3a3834'};stroke:${hot ? col : '#8f8d87'}"/>
           <polygon points="${P([iso(gx - w * 0.45, gy - w * 0.45, h), iso(gx + w * 0.45, gy - w * 0.45, h), iso(gx + w * 0.45, gy + w * 0.45, h), iso(gx - w * 0.45, gy + w * 0.45, h)])}" style="fill:${hot ? col : '#8f8d87'}" opacity=".9"/>`
        : `<polygon points="${P([a, b, c, d])}" ${hot ? `style="fill:${col}"` : 'fill="#3a3834"'}/>`}
    </g>`
  }
  function arc(p, q, lift, color, cls = '', marker = '') {
    const mx = (p[0] + q[0]) / 2, my = (p[1] + q[1]) / 2 - lift
    return `<path class="${cls}" ${marker ? `marker-end="url(#${marker})"` : ''} d="M${p[0].toFixed(1)},${p[1].toFixed(1)} Q${mx.toFixed(1)},${my.toFixed(1)} ${q[0].toFixed(1)},${q[1].toFixed(1)}" fill="none" style="stroke:${color}" stroke-width="1.8" stroke-linecap="round"/>`
  }
  function label(x, y, dx, dy, title, detail, status, step) {
    const tx = x + dx, ty = y + dy
    const w = Math.max(title.length * 6.6 + 10, detail.length * 6) + 34
    const rx = dx < 0 ? tx - w : tx
    return `<g class="pin" data-step="${step}">
      <line x1="${x}" y1="${y}" x2="${tx}" y2="${ty}" stroke="#5d5b56" stroke-width="1"/>
      <circle cx="${x}" cy="${y}" r="2.6" style="fill:${COL[status]}"/>
      <rect x="${rx}" y="${ty - 19}" width="${w}" height="38" rx="10" fill="rgba(26,26,24,.94)" stroke="#3a3834"/>
      <circle cx="${rx + 15}" cy="${ty - 5}" r="8" style="fill:${COL[status]}"/>
      <text x="${rx + 15}" y="${ty - 1.5}" text-anchor="middle" font-size="10" font-weight="600" fill="#111110">${step}</text>
      <text x="${rx + 29}" y="${ty - 1}" font-size="12.5" fill="#edebe6" font-weight="500">${esc(title)}</text>
      <text x="${rx + 29}" y="${ty + 13}" font-size="11" fill="#8f8d87">${esc(detail)}</text>
    </g>`
  }
  // which story step each place belongs to (1 disruption, 2 suppliers that buy its cells, 3 our factories, 4 rescue)
  const REGION_STEP = { Ayutthaya: 1, Penang: 2, 'Hai Phong': 2, 'Johor Bahru': 2, Suwon: 4, Kumamoto: 4 }
  const COUNTRY_LABELS = [['Thailand', 101.6, 17.2], ['Malaysia', 102.6, 3.0], ['Vietnam', 105.6, 16.2], ['China', 112, 30.5], ['Taiwan', 122.4, 23.4], ['South Korea', 128.4, 39.4], ['Japan', 132.2, 32.4]]
  function boardSvg() {
    const lens = state.lens
    const regions = regionStats(lens)
    const corners = [iso(0, 0), iso(GW, 0), iso(GW, GH), iso(0, GH)]
    const M = `matrix(${EX[0]} ${EX[1]} ${SY[0]} ${SY[1]} 0 0)`
    let s = `<svg class="board-svg" viewBox="-150 0 860 560" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Map: the stopped factory, the suppliers that depend on it, our factories and the rescue suppliers">
      <defs>
        <pattern id="dots" width=".5" height=".5" patternUnits="userSpaceOnUse"><circle cx=".25" cy=".25" r=".09" fill="#55524d"/></pattern>
        <radialGradient id="glowR"><stop offset="0" stop-color="#d9566e" stop-opacity=".55"/><stop offset="1" stop-color="#d9566e" stop-opacity="0"/></radialGradient>
        <radialGradient id="glowA"><stop offset="0" stop-color="#d7a85a" stop-opacity=".3"/><stop offset="1" stop-color="#d7a85a" stop-opacity="0"/></radialGradient>
        <radialGradient id="glowG"><stop offset="0" stop-color="#79b394" stop-opacity=".3"/><stop offset="1" stop-color="#79b394" stop-opacity="0"/></radialGradient>
        <marker id="arR" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="#d9566e"/></marker>
        <marker id="arG" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="#79b394"/></marker>
      </defs>
      <polygon points="${P(corners)}" fill="#151514" stroke="#262522"/>
      <g transform="${M}">
        ${Array.from({ length: GW / 2 + 1 }, (_, i) => `<line x1="${i * 2}" y1="0" x2="${i * 2}" y2="${GH}" stroke="#1f1e1c" vector-effect="non-scaling-stroke"/>`).join('')}
        ${Array.from({ length: Math.floor(GH / 2) + 1 }, (_, i) => `<line x1="0" y1="${i * 2}" x2="${GW}" y2="${i * 2}" stroke="#1f1e1c" vector-effect="non-scaling-stroke"/>`).join('')}
        ${LAND.map((poly) => `<polygon points="${P(poly.map(([lo, la]) => grid(lo, la)))}" fill="url(#dots)" stroke="#2c2b28" stroke-width=".6" vector-effect="non-scaling-stroke"/>`).join('')}`
    for (const [rn, r] of Object.entries(regions)) {
      if (r.status === 'none') continue
      const [gx, gy] = grid(...GEO[rn])
      const g = r.status === 'disrupted' ? 'glowR' : r.status === 'protected' ? 'glowG' : 'glowA'
      s += `<g data-step="${REGION_STEP[rn] ?? 0}"><circle cx="${gx}" cy="${gy}" r="${r.status === 'disrupted' ? 4.2 : 2.6}" fill="url(#${g})"/>`
      if (r.status === 'disrupted') s += `<circle cx="${gx}" cy="${gy}" r="1.2" fill="none" stroke="#d9566e" stroke-width="1.2" vector-effect="non-scaling-stroke"><animate attributeName="r" values="1;4.5" dur="2.4s" repeatCount="indefinite"/><animate attributeName="opacity" values=".9;0" dur="2.4s" repeatCount="indefinite"/></circle>`
      s += '</g>'
    }
    s += '</g>'
    for (const [cn, lo, la] of COUNTRY_LABELS) { const [x, y] = iso(...grid(lo, la)); s += `<text class="country" x="${x.toFixed(1)}" y="${y.toFixed(1)}" text-anchor="middle" font-size="11" fill="#5d5b56" letter-spacing=".06em">${cn}</text>` }
    const items = Object.entries(regions).map(([rn, r]) => { const [gx, gy] = grid(...GEO[rn]); return { gx, gy, h: 6 + r.sites * 6.5, status: r.status, rn, step: r.status === 'none' ? 0 : REGION_STEP[rn] ?? 0 } })
    for (const [pid, ll] of Object.entries(PLANT_GEO)) { const [gx, gy] = grid(...ll); items.push({ gx, gy, h: 30, status: lens === 'tier1' ? 'none' : st(pid), plant: pid, step: 3 }) }
    items.sort((a, b) => iso(a.gx, a.gy)[1] - iso(b.gx, b.gy)[1])
    for (const it of items) s += `<g data-step="${it.step}">${block(it.gx, it.gy, it.plant ? 0.6 : 0.48, it.h, it.status, !!it.plant)}</g>`
    const top = (rn) => { const it = items.find((i) => i.rn === rn); return iso(it.gx, it.gy, it.h) }
    const ptop = (pid) => { const it = items.find((i) => i.plant === pid); return iso(it.gx, it.gy, it.h) }
    if (lens === 'domino') {
      s += '<g data-step="2">'
      for (const dep of D.trace.shared_upstream[0].dependents) s += arc(top('Ayutthaya'), top(N[dep].region), 46, COL.disrupted, 'flow', 'arR')
      s += '</g><g data-step="4">'
      for (const po of D.plan.pos) s += arc(top(N[po.site_id].region), ptop(po.plant_id), 70 + Math.abs(top(N[po.site_id].region)[0] - ptop(po.plant_id)[0]) * 0.18, COL.protected, state.approved ? '' : 'flow', 'arG')
      s += '</g>'
      s += label(...top('Ayutthaya'), 44, -18, `${KINDC} stops ${N[SITE].operator}`, `0% working until day ${D.declared.end_day}`, 'disrupted', 1)
      s += label(...top('Hai Phong'), 30, -70, 'PowerCell, Hai Phong', 'buys cells from VoltCell', st('S-PWRC-HPG'), 2)
      s += label(...top('Penang'), 40, 24, 'BatteryMax + our Penang factory', `${plant('PL-PEN').projected_late} orders will be late`, st('PL-PEN'), 3)
      s += label(...ptop('PL-BAC'), -30, -92, 'Our Bac Ninh factory', `batteries run out on day ${plant('PL-BAC').stockout_day}`, st('PL-BAC'), 3)
      s += label(...top('Suwon'), -34, -40, 'ElectroHub, Suwon', state.approved ? 'new batteries ordered' : 'can send new batteries', 'protected', 4)
      s += label(...top('Kumamoto'), -40, 52, 'Kanto Energy, Kumamoto', state.approved ? 'new batteries ordered' : 'can send new batteries', 'protected', 4)
    }
    return s + '</svg>'
  }
  function overview() {
    const T = D.totals
    const t1 = D.trace.tier1_view.directly_affected_tier1, mt = D.trace.multi_tier.exposed_tier1
    const site = N[SITE]
    const late = state.approved ? S4.late : T.projected_late
    const fees = state.approved ? usd(S4.penalty_cents) : usdW(T.penalty_exposure_usd)
    const deps = D.trace.shared_upstream[0]
    const plantRows = ['PL-PEN', 'PL-BAC', 'PL-GDL'].map((id) => {
      const p = plant(id), lt = p.projected_late, exp = p.exposed - lt
      return `<div class="plant-row"><span>${PLANT_SHORT[id]}</span>
        <div class="stack" title="${p.orders} orders, ${p.exposed} in danger, ${lt} will be late">
          <i style="width:${(lt / p.orders) * 100}%;background:var(--st-late)"></i><i style="width:${(exp / p.orders) * 100}%;background:var(--st-covered);opacity:.75"></i></div>
        <span class="num" style="text-align:right">${p.exposed} of ${p.orders}</span></div>`
    }).join('')
    const pen = plant('PL-PEN'), bac = plant('PL-BAC')
    const mk = (day, txt, color, below) => below
      ? `<span class="mk" style="left:${(day / H) * 100}%;top:22px"><i style="background:${color}"></i>${txt}</span>`
      : `<span class="mk" style="left:${(day / H) * 100}%;top:0">${txt}<i style="background:${color}"></i></span>`

    $('#view-overview').innerHTML = `
      <section class="ov-hero">
        <div class="ov-story">
          <h1>${state.approved
            ? `Plan approved. ${S4.protected_projected} of the ${T.projected_late} late orders are now protected (projected).`
            : `A ${KIND} stopped one battery factory. ${T.exposed} customer orders are in danger.`}</h1>
          <p class="lede">${state.approved
            ? `New batteries are ordered from ${suppliersInPlan.length} other suppliers. They have not arrived yet, so the orders are protected on paper until the parts land.`
            : `DOMINO followed the supply chain from the stopped factory to your customers. It found a plan that saves ${S4.protected_projected} of the ${T.projected_late} orders that would be late. You only need to say yes.`}</p>
        </div>
        <div class="ov-nums">
          <div><b>${T.exposed}</b><span>orders in danger</span></div>
          <div><b style="color:var(--st-${state.approved ? 'protected' : 'late'})">${late}</b><span>${state.approved ? 'still late with the plan' : 'will be late if nobody acts'}</span></div>
          <div><b>${fees}</b><span>${state.approved ? 'late fees with the plan' : 'late fees if nobody acts'}</span></div>
        </div>
      </section>

      <section class="ov-main">
        <div class="card map-card">
          <div class="map-head">
            <div><h2>What is happening, step by step</h2><div class="sub">${state.lens === 'domino' ? 'Hover a step below to see it on the map.' : 'This is all a normal tool can see.'}</div></div>
            <div class="chip-toggle" role="group" aria-label="Who is looking">
              <button data-lens="tier1" class="${state.lens === 'tier1' ? 'on' : ''}">Normal tool</button>
              <button data-lens="domino" class="${state.lens === 'domino' ? 'on' : ''}">DOMINO</button>
            </div>
          </div>
          <div class="board-stage">${boardSvg()}
            ${state.lens === 'tier1' ? `<div class="board-caption">A normal tool only checks the suppliers you buy from directly. It finds <b>${t1}</b> problems, because the stopped factory is one step further back.</div>` : ''}
          </div>
          ${state.lens === 'domino' ? `<ol class="map-steps">
            ${[
              [1, 'disrupted', 'The disruption', `${esc(site.operator)} makes battery cells in ${esc(site.region)}. A ${KIND} stops it until day ${D.declared.end_day}.`],
              [2, 'covered', 'Who needs those cells', `${deps.fan_out} battery makers buy its cells. Red arrows show the cells that no longer come.`],
              [3, state.approved ? 'protected' : 'late', 'Our factories', `Penang and Bac Ninh run short of batteries. ${state.approved ? `${S4.late} order is still late.` : `${T.projected_late} orders would be late.`}`],
              [4, 'protected', 'The rescue', `Green arrows: batteries from ${suppliersInPlan.length} other suppliers. ${state.approved ? 'Ordered.' : 'Starts when you approve.'}`],
            ].map(([n, sv, t, d]) => `<li data-step="${n}" tabindex="0"><span class="n" style="background:var(--st-${sv})">${n}</span><div><b>${t}</b><span>${d}</span></div></li>`).join('')}
          </ol>` : '<div class="map-legend"><span><i class="dot"></i>Grey blocks: places with suppliers. A normal tool shows them all as fine.</span></div>'}
        </div>

        <div class="ov-side">
          <div class="card"><div class="card-b">
            <div class="side-h"><h2>What happened</h2><span class="tag"><i class="dot st-disrupted pulse"></i>Day 0</span></div>
            <p class="plain">${esc(D.alert)}</p>
            <dl class="facts">
              <div><dt>Factory hit</dt><dd>${esc(site.operator)}, ${esc(site.region)} (${COUNTRY[site.country] ?? site.country})</dd></div>
              <div><dt>It makes</dt><dd>battery ${esc(site.unit)}</dd></div>
              <div><dt>Working</dt><dd>${Math.round(D.declared.capacity_factor * 100)}% until day ${D.declared.end_day}</dd></div>
            </dl>
          </div></div>
          <div class="card fix-card ${state.approved ? 'done' : ''}"><div class="card-b">
            <div class="side-h"><h2>${state.approved ? 'The plan is running' : 'The fix'}</h2><span class="tag"><i class="dot st-${state.approved ? 'protected' : 'covered'}"></i>${state.approved ? 'Approved' : 'Needs your OK'}</span></div>
            <p class="plain">Buy batteries from ${suppliersInPlan.length} other suppliers: ${suppliersInPlan.map((id) => esc(N[id].operator)).join(', ')}.</p>
            <dl class="facts">
              <div><dt>Cost</dt><dd>${usd(S4.spend_cents)} <span class="muted">of ${usd(D.budget_cents)} budget</span></dd></div>
              <div><dt>Orders saved</dt><dd>${S4.protected_projected}, protected (projected)</dd></div>
              <div><dt>Still late</dt><dd>${S4.late} order</dd></div>
            </dl>
            ${state.approved
              ? '<button class="btn btn-ghost wide" data-go="logistics">Track the shipments</button>'
              : '<div class="fix-actions"><button class="btn btn-accent" id="ovApprove">Approve plan</button><button class="btn btn-ghost" data-go="agent">How DOMINO decided</button></div>'}
          </div></div>
        </div>
      </section>


      <section class="ov-details" id="ov-details">
        <h2 class="sec-title">More details</h2>
        <div class="detail-grid">
          <div class="card"><div class="card-b"><div class="side-h"><h3>Our factories</h3><span class="sub">orders in danger</span></div>${plantRows}
            <div class="sub" style="margin-top:8px;display:flex;gap:12px"><span><i class="dot st-late"></i> will be late</span><span><i class="dot st-covered"></i> stock still covers it</span></div></div></div>
          <div class="card"><div class="card-b"><div class="side-h"><h3>When batteries run out</h3><span class="sub">day 0 to ${H}</span></div>
            <div class="clock"><div class="track"></div>
              ${mk(pen.stockout_day, `Penang, day ${pen.stockout_day}`, 'var(--st-late)')}
              ${mk(bac.stockout_day, `Bac Ninh, day ${bac.stockout_day}`, 'var(--st-covered)')}
              ${mk(D.declared.end_day, `VoltCell works again, ${D.declared.end_day}`, 'var(--ink-2)', true)}
            </div><div class="clock-scale"><span>today</span><span>day ${H}</span></div></div></div>
          <div class="card"><div class="card-b"><div class="side-h"><h3>The hidden weak point</h3></div>
            <p class="plain">${esc(deps.operator)} sends battery cells to ${deps.fan_out} of your suppliers. One ${KIND} hits all of them.</p>
            <div class="feed-list">${deps.dependents.map((d) => `<div class="feed-item"><i class="dot st-${st(d)}"></i>${esc(name(d))}</div>`).join('')}</div></div></div>
          <div class="card"><div class="card-b"><div class="side-h"><h3>What a normal tool misses</h3></div>
            <div class="lens-compare">
              <div><span class="sub">Normal tool</span><b>${t1}</b><span class="sub">suppliers in trouble</span></div>
              <div style="box-shadow:inset 0 0 0 1px var(--accent-soft)"><span class="sub">DOMINO</span><b>${mt}</b><span class="sub">suppliers in trouble</span></div>
            </div>
            <div class="sub" style="margin-top:8px">If a factory is not in your data, it is not automatically safe.</div></div></div>
          <div class="card"><div class="card-b"><div class="side-h"><h3>Money at risk</h3><span class="sub">if nobody acts</span></div>
            <dl class="facts"><div><dt>Sales at risk</dt><dd>${usdW(T.revenue_at_risk_usd)}</dd></div><div><dt>Late fees</dt><dd>${usdW(T.penalty_exposure_usd)}</dd></div><div><dt>Late fees with plan</dt><dd>${usd(S4.penalty_cents)}</dd></div></dl></div></div>
          <div class="card"><div class="card-b"><div class="side-h"><h3>Not on the map</h3></div>
            <p class="plain">Our Guadalajara factory in Mexico has ${plant('PL-GDL').exposed} orders in danger, but enough stock to finish them on time. ${D.nodes.filter((n) => OFFBOARD.includes(n.region)).length} more suppliers in Mexico, the US and Europe are not affected.</p></div></div>
        </div>
      </section>`
    $$('[data-lens]').forEach((b) => (b.onclick = () => { state.lens = b.dataset.lens; overview() }))
    const board = $('.board-svg')
    const focus = (n) => { board.classList.toggle('focus', !!n); $$('[data-step]', board).forEach((g) => g.classList.toggle('on', g.dataset.step === n)); $$('.map-steps li').forEach((li) => li.classList.toggle('on', li.dataset.step === n)) }
    let touring = false
    $$('.map-steps li').forEach((li) => { li.onmouseenter = li.onfocus = () => { touring = false; focus(li.dataset.step) }; li.onmouseleave = li.onblur = () => focus(null); li.onclick = () => focus(li.dataset.step) })
    if (!state.tourDone && $('.map-steps') && !matchMedia('(prefers-reduced-motion: reduce)').matches && !document.documentElement.classList.contains('shot')) {
      state.tourDone = touring = true
      ;['1', '2', '3', '4', null].forEach((n, i) => setTimeout(() => { if (touring && state.view === 'overview') focus(n) }, 900 + i * 1700))
    }
    $('#ovApprove')?.addEventListener('click', approve)
  }

  /* ================= SUPPLY CHAIN: only the path the disruption travels, as cards ================= */
  function chainModel() {
    const sh = D.trace.shared_upstream[0], ev = D.trace.evidence
    const deps = [...sh.dependents].sort((a, b) => ev.filter((e) => e.tier1 === b).length - ev.filter((e) => e.tier1 === a).length)
    const rescue = suppliersInPlan.filter((id) => !deps.includes(id))
    const plants = [...new Set(ev.map((e) => e.plant))]
    const products = [...new Set(ev.map((e) => e.product))]
    const groups = products.map((pr) => {
      const os = D.orders.filter((o) => o.product === pr)
      return { id: 'G:' + pr, product: pr, customers: new Set(os.map((o) => o.customer)).size, orders: os.length,
        late: os.filter((o) => orderState(o) === 'late').length, saved: os.filter((o) => orderState(o) === 'protected').length }
    })
    const shownCust = new Set(D.orders.map((o) => o.customer))
    const count = (col) => D.nodes.filter((n) => n.col === col).length
    const of = (...c) => D.nodes.filter((n) => c.includes(n.col)).map((n) => n.id)
    const cols = [
      { title: 'Parts makers', ids: [SITE], all: of('tier2', 'tier3'), shown: [SITE] },
      { title: 'Direct suppliers', ids: [...deps, ...rescue], all: of('tier1'), shown: [...deps, ...rescue], split: deps.length },
      { title: 'Our factories', ids: plants, all: of('plant'), shown: plants },
      { title: 'Products', ids: products, all: of('product'), shown: products },
      { title: 'Customers', ids: groups.map((g) => g.id), all: of('customer'), shown: [...shownCust] },
    ]
    const edges = []
    for (const d of deps) edges.push({ s: SITE, t: d, kind: 'cells' })
    for (const e of ev) if (!edges.some((x) => x.s === e.tier1 && x.t === e.plant)) edges.push({ s: e.tier1, t: e.plant, kind: 'packs' })
    for (const po of D.plan.pos) if (!edges.some((x) => x.s === po.site_id && x.t === po.plant_id && x.kind === 'plan')) edges.push({ s: po.site_id, t: po.plant_id, kind: 'plan' })
    for (const e of ev) if (!edges.some((x) => x.s === e.plant && x.t === e.product)) edges.push({ s: e.plant, t: e.product, kind: 'builds' })
    for (const g of groups) edges.push({ s: g.product, t: g.id, kind: 'orders' })
    return { cols, edges, groups, deps, rescue }
  }
  function chainSvg() {
    const m = chainModel(), t1lens = state.lens === 'tier1'
    const W = 1330, CW = 222, CH = 62, GAPX = (W - 40 - CW * 5) / 4, TOP = 118, ROW = 84
    const H = TOP + Math.max(...m.cols.map((c) => c.ids.length)) * ROW + 40
    const pos = {}
    m.cols.forEach((c, k) => {
      const n = c.ids.length, extra = c.split ? 26 : 0
      const y0 = TOP + ((Math.max(...m.cols.map((x) => x.ids.length)) - n) * ROW - extra) / 2
      c.ids.forEach((id, i) => (pos[id] = [20 + k * (CW + GAPX), y0 + i * ROW + (c.split && i >= c.split ? 26 + extra : 0)]))
    })
    const intro = !state.netSeen
    const statusOf = (id) => {
      if (t1lens) return 'none'
      if (id.startsWith('G:')) { const g = m.groups.find((x) => x.id === id); return g.late ? 'late' : g.saved ? 'protected' : 'covered' }
      if (m.rescue.includes(id)) return 'protected'
      return st(id)
    }
    const custState = (cu) => { const os = D.orders.filter((o) => o.customer === cu).map(orderState); return os.includes('late') ? 'late' : os.includes('covered') ? 'covered' : os.length ? 'protected' : 'none' }
    let s = `<svg class="chain-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="How the disruption travels from one parts maker to customers">`
    m.cols.forEach((c, k) => {
      const x = 20 + k * (CW + GAPX)
      s += `<text x="${x}" y="22" font-size="13" font-weight="500" fill="#edebe6">${c.title}</text>
        <text x="${x}" y="40" font-size="11.5" fill="#8f8d87">${c.shown.length} of ${c.all.length} on the path${c.all.length > c.shown.length ? ', rest not affected' : ''}</text>`
      c.all.forEach((nid, i) => {
        const on = c.shown.includes(nid)
        const sv = t1lens ? 'none' : !on ? 'none' : k === 4 ? custState(nid) : statusOf(nid)
        s += `<circle class="mdot" cx="${x + 4 + (i % 15) * 13}" cy="${58 + Math.floor(i / 15) * 13}" r="${on ? 4.2 : 3.4}" style="fill:${on && !t1lens ? COL[sv] : '#3a3834'}"><title>${esc(name(nid))}${on ? ' (shown below)' : ', not affected'}</title></circle>`
      })
      if (c.split) { const y = pos[c.ids[c.split]][1] - 18; s += `<text x="${x}" y="${y}" font-size="11.5" fill="#79b394">New suppliers in the plan</text>` }
    })
    // connectors first, cards on top
    m.edges.forEach((e, i) => {
      const a = pos[e.s], b = pos[e.t]; if (!a || !b) return
      const x1 = a[0] + CW, y1 = a[1] + CH / 2, x2 = b[0], y2 = b[1] + CH / 2, dx = (x2 - x1) / 2
      const col = t1lens ? '#3a3834' : e.kind === 'cells' ? COL.disrupted : e.kind === 'plan' ? COL.protected : e.kind === 'orders' ? COL[statusOf(e.t)] : COL.covered
      const dashed = e.kind === 'plan' && !state.approved
      const k = m.cols.findIndex((c) => c.ids.includes(e.s))
      const moving = dashed || e.kind === 'cells'
      s += `<path class="chain-edge ${moving ? 'flow' : intro ? 'draw' : ''}" data-s="${e.s}" data-t="${e.t}" ${moving ? '' : 'pathLength="1"'} style="stroke:${col};animation-delay:${moving ? 0 : k * 0.3}s" d="M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}" fill="none" stroke-width="${e.kind === 'plan' ? 1.6 : 2}" opacity="${t1lens ? 0.6 : 0.9}"/>`
    })
    for (const c of m.cols) for (const id of c.ids) {
      const [x, y] = pos[id], sv = statusOf(id), hidden = t1lens && id === SITE
      let title, sub, right = ''
      if (id.startsWith('G:')) {
        const g = m.groups.find((z) => z.id === id)
        title = `${g.customers} customers, ${g.orders} orders`
        sub = g.saved ? `${g.saved} protected (projected)${g.late ? `, ${g.late} late` : ''}` : g.late ? `${g.late} will be late` : 'stock covers them'
      } else if (N[id].kind === 'site') {
        title = N[id].operator; sub = N[id].region
        right = id === SITE ? 'stopped' : m.rescue.includes(id) ? 'in the plan' : suppliersInPlan.includes(id) ? 'in plan too' : D.alternatives.some((a) => a.rejected.some((r) => r.site === id)) ? 'no cells left' : ''
      } else if (N[id].kind === 'plant') {
        const p = plant(id); title = `${PLANT_SHORT[id]} factory`; sub = p.projected_late ? `batteries run out day ${p.stockout_day}` : 'enough stock for now'
      } else { title = N[id].label; sub = 'laptop' }
      s += `<g class="chain-card ${hidden ? 'hidden' : ''}" data-id="${id}" tabindex="0">
        <rect x="${x}" y="${y}" width="${CW}" height="${CH}" rx="12" fill="${sv === 'none' ? '#1c1b19' : '#211f1d'}" style="stroke:${sv === 'none' ? '#34322e' : COL[sv]}" stroke-opacity="${sv === 'none' ? 1 : 0.55}" ${hidden ? 'stroke-dasharray="4 4"' : ''}/>
        <rect x="${x}" y="${y + 12}" width="3" height="${CH - 24}" rx="1.5" style="fill:${COL[sv]}"/>
        <text x="${x + 16}" y="${y + 26}" font-size="13" font-weight="500" fill="${hidden ? '#5d5b56' : '#edebe6'}">${esc(title.length > 24 ? title.slice(0, 23) + '…' : title)}</text>
        <text x="${x + 16}" y="${y + 45}" font-size="11.5" fill="#8f8d87">${esc(sub)}</text>
        ${right && !t1lens ? `<text x="${x + CW - 12}" y="${y + 45}" text-anchor="end" font-size="11" style="fill:${COL[sv]}">${right}</text>` : ''}
      </g>`
      if (hidden) s += `<text x="${x + CW / 2}" y="${y + CH + 20}" text-anchor="middle" font-size="11.5" fill="#8f8d87">A normal tool cannot see this</text>`
    }
    return s + '</svg>'
  }
  function network() {
    const ev = D.trace.evidence, sh = D.trace.shared_upstream[0]
    $('#view-network').innerHTML = `
      ${head('How the disruption travels', `Your supply chain has ${D.nodes.length} companies. Only the ones on its path are shown here, from the parts maker on the left to your customers on the right.`,
        `<div class="head-toggles">
          <div class="chip-toggle"><button data-lens="tier1" class="${state.lens === 'tier1' ? 'on' : ''}">Normal tool</button><button data-lens="domino" class="${state.lens === 'domino' ? 'on' : ''}">DOMINO</button></div>
          <div class="chip-toggle"><button data-ba="0" class="${!state.approved ? 'on' : ''}">Before plan</button><button data-ba="1" class="${state.approved ? 'on' : ''}">After plan</button></div>
        </div>`)}
      <div class="net-grid stacked">
        <div class="card net-card">
          ${state.lens === 'tier1' ? `<div class="net-note">A normal tool only knows the suppliers you buy from directly. Without the first column, it finds ${D.trace.tier1_view.directly_affected_tier1} problems.</div>` : ''}
          <div class="net-scroll">${chainSvg()}</div>
          <div class="sub" style="padding:0 18px 10px">Each small dot above a column is one company, ${D.nodes.length} in total. Coloured dots are on the path and are shown as cards. Hover a dot to see its name.</div>
          <div class="map-legend" style="margin:0 18px 16px"><span><i class="dot st-disrupted"></i>Stopped</span><span><i class="dot st-late"></i>Will be late</span><span><i class="dot st-covered"></i>In danger</span><span><i class="dot st-protected"></i>${state.approved ? 'Protected (projected)' : 'Rescue in the plan'}</span><span><i class="dot"></i>Not affected</span></div>
        </div>
        <div class="side-stack">
          <div class="card"><div class="card-b"><div class="side-h"><h3>The hidden weak point</h3></div>
            <p class="plain">${esc(sh.operator)} sells battery cells to ${sh.fan_out} of your suppliers. They look like ${sh.fan_out} separate companies, but one ${KIND} hits all of them.</p></div></div>
          <div class="card"><div class="card-b"><div class="side-h"><h3>Paths it takes</h3></div>
            ${ev.map((e) => `<button class="ev" data-ev="${e.id}"><div class="path">${e.path.map((id) => `<span>${esc(N[id].kind === 'plant' ? PLANT_SHORT[id] + ' factory' : N[id].operator)}</span>`).join('<i>→</i>')}</div>
              <div class="sub" style="margin-top:3px">${e.orders.length} orders</div></button>`).join('')}</div></div>
          <div class="card"><div class="card-b"><div class="side-h"><h3>Batteries we can still get</h3><span class="sub">per week</span></div>
            ${D.capacity.map((c) => `<div class="cap-row">
              <div style="display:flex;justify-content:space-between;font-size:12.5px"><span>${PLANT_SHORT[c.plant]} factory</span><span class="num"><b style="font-weight:500">${fmt(c.true_wk)}</b> <span class="muted">of ${fmt(c.naive_wk)}</span></span></div>
              <div class="cap-bars"><i style="width:100%;background:#34322e"></i><i style="width:${(c.true_wk / c.naive_wk) * 100}%;background:${c.true_wk === 0 ? 'var(--st-disrupted)' : 'var(--st-covered)'}"></i></div></div>`).join('')}
            <div class="sub" style="margin-top:4px">Grey is what the contracts promise. Colour is what can really arrive now.</div></div></div>
        </div>
      </div>`
    state.netSeen = true
    $$('[data-lens]').forEach((b) => (b.onclick = () => { state.lens = b.dataset.lens; network() }))
    $$('[data-ba]').forEach((b) => (b.onclick = () => (b.dataset.ba === '1' ? approve() : unapprove())))
    const svg = $('.chain-svg')
    const hl = (ids) => {
      const set = new Set(ids)
      svg.classList.toggle('dim', ids.length > 0)
      $$('.chain-card', svg).forEach((g) => g.classList.toggle('hl', set.has(g.dataset.id)))
      $$('.chain-edge', svg).forEach((p) => p.classList.toggle('hl', set.has(p.dataset.s) && set.has(p.dataset.t)))
    }
    const reach = (id) => { // everything upstream and downstream of a card
      const E = $$('.chain-edge', svg).map((p) => [p.dataset.s, p.dataset.t])
      const out = new Set([id]); let grew = true
      while (grew) { grew = false; for (const [a, b] of E) { if (out.has(a) && !out.has(b) && b !== SITE) { out.add(b); grew = true } } }
      const up = new Set([id]); grew = true
      while (grew) { grew = false; for (const [a, b] of E) { if (up.has(b) && !up.has(a)) { up.add(a); grew = true } } }
      return [...out, ...up]
    }
    $$('.chain-card', svg).forEach((g) => { g.onmouseenter = g.onfocus = () => hl(reach(g.dataset.id)); g.onmouseleave = g.onblur = () => hl([]) })
    $$('[data-ev]').forEach((b) => {
      const e = ev.find((x) => x.id === b.dataset.ev)
      const ids = [...e.path, e.product, 'G:' + e.product]
      b.onmouseenter = b.onfocus = () => { b.classList.add('on'); hl(ids) }
      b.onmouseleave = b.onblur = () => { b.classList.remove('on'); hl([]) }
    })
  }

  /* ================= FACTORIES: one large building, orders on a glass panel (truck reference) ================= */
  function factoryModel(id) {
    if (id === SITE) {
      const deps = D.trace.shared_upstream[0].dependents
      return {
        stopped: true, sign: name(id),
        cells: deps.map((d) => {
          const to = [...new Set(D.trace.evidence.filter((e) => e.tier1 === d).map((e) => PLANT_SHORT[e.plant]))]
          return { id: d, top: N[d].operator, mid: N[d].region, bottom: to.length ? `sends batteries to ${to.join(', ')}` : 'no orders through it', status: st(d) }
        }),
        rest: null,
        metrics: [['Working', `${Math.round(D.declared.capacity_factor * 100)}%`, 'disrupted'], ['Works again', `day ${D.declared.end_day}`, null], ['Buyers of its cells', deps.length, 'covered'], ['Orders it reaches', D.totals.exposed, 'late']],
        power: { on: false, tone: 'disrupted', title: 'Power off', detail: `${KINDC}: production stopped until day ${D.declared.end_day}` },
        note: `${N[id].operator} makes battery cells. A ${KIND} stopped it. The panel shows the ${deps.length} battery makers that buy its cells.`,
      }
    }
    const p = plant(id)
    const mine = D.orders.filter((o) => o.plant === id).sort((a, b) => RANK[orderState(b)] - RANK[orderState(a)] || a.need_day - b.need_day)
    const ev = D.trace.evidence.find((e) => e.plant === id)
    const cap = D.capacity.find((c) => c.plant === id)
    const arrivals = D.plan.pos.filter((po) => po.plant_id === id).map((po) => po.first_arrival_day)
    const lateNow = mine.filter((o) => orderState(o) === 'late').length
    return {
      sign: name(id),
      cells: mine.map((o) => ({ id: o.order_id, top: o.order_id, mid: name(o.customer), bottom: `due day ${o.need_day}`, status: orderState(o) })),
      rest: p.orders - mine.length,
      metrics: [['Orders', p.orders, null], ['In danger', p.exposed, 'covered'], ['Will be late', lateNow, lateNow ? 'late' : 'protected'],
        state.approved && arrivals.length ? ['New batteries', `day ${Math.min(...arrivals)}`, 'protected'] : ['Batteries run out', p.stockout_day ? `day ${p.stockout_day}` : `not in ${H} days`, p.stockout_day ? 'late' : null]],
      power: state.approved && arrivals.length
        ? { on: true, tone: 'protected', title: 'Running, rescue on the way', detail: `New batteries from day ${Math.min(...arrivals)}` }
        : cap.true_wk === 0
          ? { on: true, tone: 'covered', title: 'Running on stock', detail: `Battery supply cut: 0 of ${fmt(cap.naive_wk)} a week` }
          : { on: true, tone: p.projected_late ? 'late' : 'covered', title: 'Running, low on batteries', detail: `Battery supply ${fmt(cap.true_wk)} of ${fmt(cap.naive_wk)} a week` },
      note: cap.true_wk === 0
        ? `Batteries came from ${name(ev.tier1)}, whose cells all came from the stopped factory. Stock covers these orders for now.`
        : `Batteries come from ${name(ev.tier1)}: now ${fmt(cap.true_wk)} a week instead of ${fmt(cap.naive_wk)}.`,
    }
  }
  // A flat 2D elevation of a modern "gigafactory": long white hall, ribbon glazing, rooftop solar, dock wing.
  // Decorative only: the orders live on the HTML glass panel placed over the glass wall.
  // Main power switch on the wall: lever up = running, down = stopped; the lamp shows the problem's colour.
  function switchBox(power) {
    if (!power) return ''
    const on = power.on, lamp = COL[power.tone]
    return `<g class="switch">
      <line x1="235" y1="171" x2="235" y2="262" stroke="#a9a49b" stroke-width="3"/>
      <rect x="198" y="262" width="74" height="96" rx="4" fill="#bfbab1" stroke="#8f8b84"/>
      <rect x="204" y="268" width="62" height="84" rx="2" fill="#d6d2ca"/>
      <text x="235" y="281" text-anchor="middle" font-size="9" fill="#5d5b56">Main power</text>
      <circle class="${on && power.tone === 'protected' ? '' : 'lamp-glow'}" cx="235" cy="295" r="11" style="fill:${lamp}" opacity=".3"/>
      <circle cx="235" cy="295" r="5.5" style="fill:${lamp}"/>
      <text x="250" y="${on ? 316 : 349}" font-size="8.5" fill="#2a2926" font-weight="600">${on ? 'on' : 'off'}</text>
      <circle cx="232" cy="330" r="9" fill="#3a3936"/>
      <rect x="228" y="${on ? 306 : 330}" width="8" height="24" rx="3" fill="#2a2926"/>
      <circle cx="232" cy="${on ? 306 : 354}" r="5.5" style="fill:${on ? '#2a2926' : '#d9566e'}" stroke="#1a1a18"/>
    </g>`
  }
  function buildingSvg(stopped, mini, power) {
    const id = mini ? 'm' : 'b'
    // stopped: same building in a dimmer palette (no filters, so nothing but the building changes)
    const [wall, wall2, seam, trim, frame] = stopped ? ['#8f8b84', '#827e78', '#7b7771', '#9b9790', '#6f6b65'] : ['#ebe8e2', '#dedad3', '#d6d2ca', '#f6f4f0', '#bdb8af']
    const glass = '#1a1e23', mull = '#2a3038'
    let s = `<svg class="${mini ? 'fac-mini' : 'building'}" viewBox="0 70 1200 380" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <defs><pattern id="${id}caution" width="16" height="16" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="16" fill="#d7a85a"/><rect x="8" width="8" height="16" fill="#1a1a18"/></pattern></defs>
      <polygon points="20,430 1180,430 1196,442 4,442" fill="#0b0b0a"/>

      <!-- rooftop solar, seen slightly from above, and plant on the roof -->
      <polygon points="176,162 1084,162 1068,140 192,140" fill="#243040"/>
      ${Array.from({ length: 32 }, (_, i) => `<line x1="${196 + i * 28}" y1="141" x2="${190 + i * 28}" y2="161" stroke="#34465c"/>`).join('')}
      <line x1="186" y1="151" x2="1076" y2="151" stroke="#34465c"/>
      <rect x="282" y="122" width="46" height="18" fill="${wall2}"/><rect x="282" y="122" width="46" height="4" fill="${trim}"/>
      <rect x="660" y="126" width="64" height="14" fill="${wall2}"/><rect x="660" y="126" width="64" height="3" fill="${trim}"/>
      <!-- dock wing -->
      <rect x="30" y="290" width="140" height="140" fill="${wall2}"/><rect x="26" y="284" width="148" height="8" fill="${trim}"/>
      ${[48, 108].map((x) => `<rect x="${x}" y="340" width="46" height="90" fill="#2c2f34"/>${Array.from({ length: 9 }, (_, i) => `<line x1="${x}" y1="${348 + i * 9}" x2="${x + 46}" y2="${348 + i * 9}" stroke="#3b3f45"/>`).join('')}<rect x="${x - 4}" y="332" width="54" height="5" fill="${trim}"/><rect x="${x - 2}" y="420" width="6" height="10" fill="#1a1a18"/><rect x="${x + 42}" y="420" width="6" height="10" fill="#1a1a18"/>`).join('')}
      <!-- main hall -->
      <rect x="170" y="168" width="920" height="262" fill="${wall}"/>
      <rect x="166" y="162" width="928" height="9" fill="${trim}"/>
      ${[262, 322, 382].map((y) => `<line x1="170" y1="${y}" x2="1090" y2="${y}" stroke="${seam}" stroke-width="1.5"/>`).join('')}
      ${Array.from({ length: 20 }, (_, i) => `<rect x="${192 + i * 46}" y="222" width="2" height="198" fill="${seam}"/>`).join('')}
      <rect x="170" y="182" width="920" height="28" fill="${glass}"/>
      ${Array.from({ length: 23 }, (_, i) => `<line x1="${170 + i * 40}" y1="182" x2="${170 + i * 40}" y2="210" stroke="${mull}" stroke-width="2"/>`).join('')}
      ${stopped ? '' : [3, 4, 9, 10, 11, 15, 16, 19].map((i) => `<rect x="${172 + i * 40}" y="184" width="36" height="24" fill="#cdbf98" opacity=".28"/>`).join('')}
      <polygon points="420,182 462,182 438,210 396,210" fill="#262c34" opacity=".9"/><polygon points="770,182 800,182 776,210 746,210" fill="#262c34" opacity=".9"/>
      <rect x="170" y="214" width="920" height="4" fill="${stopped ? '#5a2a33' : '#8a2f3d'}"/>
      <!-- glass wall: the order panel sits here -->
      <rect x="300" y="232" width="580" height="170" fill="${glass}" stroke="${frame}" stroke-width="3"/>
      ${Array.from({ length: 6 }, (_, i) => `<line x1="${300 + (i + 1) * 580 / 7}" y1="234" x2="${300 + (i + 1) * 580 / 7}" y2="400" stroke="#20252b"/>`).join('')}
      ${switchBox(power)}
      <!-- entrance -->
      <rect x="900" y="300" width="110" height="130" fill="${glass}" stroke="${frame}" stroke-width="3"/><line x1="955" y1="300" x2="955" y2="430" stroke="${frame}" stroke-width="2"/>
      <rect x="890" y="292" width="130" height="7" fill="${trim}"/>
      ${stopped ? '' : '<rect x="902" y="302" width="106" height="4" fill="#cdbf98" opacity=".35"/>'}
      <rect x="176" y="172" width="4" height="248" fill="${seam}"/><rect x="1080" y="172" width="4" height="248" fill="${seam}"/>
      <!-- office tower -->
      <rect x="1090" y="206" width="80" height="224" fill="${wall2}"/><rect x="1086" y="200" width="88" height="7" fill="${trim}"/>
      ${[1104, 1124, 1144].map((x) => `<rect x="${x}" y="226" width="10" height="184" fill="${glass}"/>`).join('')}
      <rect x="170" y="420" width="1000" height="10" fill="${stopped ? '#6f6b65' : '#cfcbc3'}"/>`
    if (stopped) s += `<rect x="170" y="414" width="920" height="8" fill="url(#${id}caution)" opacity=".8"/>
`
    return s + '</svg>'
  }
  function incident() {
    const ids = [SITE, 'PL-PEN', 'PL-BAC', 'PL-GDL']
    if (!ids.includes(state.factory)) state.factory = 'PL-PEN'
    const f = factoryModel(state.factory)
    const stopped = state.factory === SITE
    const sel = state.focusCell && f.cells.some((c) => c.id === state.focusCell) ? state.focusCell : null
    const cells = f.cells.map((c, i) => `<button class="cell ${sel === c.id ? 'on' : ''}" data-o="${c.id}" style="animation-delay:${i * 40}ms">
        <span class="cell-top"><i class="dot st-${c.status}"></i><span class="${stopped ? '' : 'mono'}">${esc(c.top)}</span></span>
        <span class="cell-mid">${esc(c.mid)}</span><span class="cell-bot">${esc(c.bottom)}</span></button>`).join('')
      + (f.rest ? `<div class="cell rest"><b>${f.rest}</b><span>more orders, safe</span></div>` : '')
    const list = stopped
      ? f.cells.map((c) => `<div class="row" data-o="${c.id}"><i class="dot st-${c.status}"></i><div><div>${esc(name(c.id))}</div><div class="sub">${esc(c.bottom)}</div></div></div>`).join('')
      : D.orders.filter((o) => o.plant === state.factory).sort((a, b) => a.need_day - b.need_day).map((o) => {
          const sv = orderState(o)
          const words = sv === 'protected' ? 'protected (projected)' : sv === 'late' ? (o.ready_day == null ? `not ready within ${H} days` : `late by ${o.late_days} days`) : 'stock covers it'
          return `<div class="row" data-o="${o.order_id}"><i class="dot st-${sv}"></i><div><div><span class="mono">${o.order_id}</span> ${esc(name(o.customer))}</div><div class="sub">due day ${o.need_day}, ${words}</div></div></div>`
        }).join('')
    const tiles = ids.map((id) => {
      const fl = id === SITE, p = fl ? null : plant(id)
      const lateNow = fl ? 0 : D.orders.filter((o) => o.plant === id && orderState(o) === 'late').length
      const sv = fl ? 'disrupted' : lateNow ? 'late' : state.approved && p.projected_late ? 'protected' : 'covered'
      return `<button class="fac ${state.factory === id ? 'on' : ''}" data-fac="${id}">
        <div><span class="sub">${fl ? 'Where it started' : 'Our factory'}</span><b>${fl ? esc(N[SITE].operator) : PLANT_SHORT[id]}</b>
          <span class="tag" style="margin-top:6px"><i class="dot st-${sv}"></i>${fl ? 'stopped' : lateNow ? `${lateNow} late` : `${p.exposed} in danger, on time`}</span></div>
        ${buildingSvg(fl, true)}</button>`
    }).join('')
    $('#view-incident').innerHTML = `
      ${head('Inside your factories', 'Each tile on the glass panel is one customer order at this factory, coloured by what will happen to it.')}
      <div class="card fac-stage-card">
        <div class="fac-top">
          <div><span class="sub">${stopped ? 'Where it started' : 'Our factory'}</span><h2 class="fac-name">${esc(f.sign)}</h2></div>
          <div class="fac-metrics">${f.metrics.map(([k, v, sv]) => `<div><span class="sub">${sv ? `<i class="dot st-${sv}"></i> ` : ''}${k}</span><b>${v}</b></div>`).join('')}</div>
        </div>
        <div class="fac-scene">
          <div class="fac-canvas">
            ${buildingSvg(stopped, false, f.power)}
            <div class="power-pin tone-${f.power.tone}"><i class="dot st-${f.power.tone} ${f.power.tone === 'protected' ? '' : 'pulse'}"></i><div><b>${f.power.title}</b><span>${esc(f.power.detail)}</span></div></div>
            <div class="fac-panel ${stopped ? 'few' : ''}" id="facPanel">${cells}</div>
          </div>
          <aside class="fac-list">
            <div class="side-h"><h3>${stopped ? 'Who buys its cells' : 'Orders in danger'}</h3><span class="sub">${stopped ? '' : `${f.cells.length} of ${f.cells.length + f.rest}`}</span></div>
            <div class="order-list">${list}</div>
          </aside>
        </div>
        <p class="plain fac-note">${f.note}</p>
      </div>
      <div class="fac-strip">${tiles}</div>
      <div class="card compare">
        <div><span class="sub">If nobody acts</span><p><b>${S0.late}</b> orders late, <b>${usd(S0.penalty_cents)}</b> in late fees</p></div>
        <div class="arrow-r" aria-hidden="true"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 12h15m-5-5 5 5-5 5"/></svg></div>
        <div><span class="sub">With DOMINO's plan</span><p><b style="color:var(--st-protected)">${S4.late}</b> order late, <b>${usd(S4.penalty_cents)}</b> in late fees, plan costs <b>${usd(S4.spend_cents)}</b></p></div>
        ${state.approved ? '<span class="tag"><i class="dot st-protected"></i>Approved</span>' : '<button class="btn btn-accent" id="facApprove">Approve plan</button>'}
      </div>`
    $$('[data-fac]').forEach((b) => (b.onclick = () => { state.factory = b.dataset.fac; state.focusCell = null; incident() }))
    $('#facApprove')?.addEventListener('click', approve)
    const panel = $('#facPanel')
    const hl = (id) => { panel.classList.toggle('holding', !!id); $$('.cell[data-o]', panel).forEach((g) => g.classList.toggle('hl', g.dataset.o === id)); $$('.row').forEach((r) => r.classList.toggle('on', r.dataset.o === id)) }
    $$('.row[data-o]').forEach((r) => { r.onmouseenter = () => hl(r.dataset.o); r.onmouseleave = () => hl(null) })
    $$('.cell[data-o]', panel).forEach((g) => { g.onmouseenter = g.onfocus = () => hl(g.dataset.o); g.onmouseleave = g.onblur = () => hl(null) })
  }

  /* ================= SHIPMENTS ================= */
  const siteLL = (id) => (id.startsWith('PL-') ? PLANT_GEO[id] : GEO[N[id].region])
  function miniRoute(po, i) {
    const a = siteLL(po.site_id), b = siteLL(po.plant_id)
    const pad = 3, minLo = Math.min(a[0], b[0]) - pad, maxLo = Math.max(a[0], b[0]) + pad, minLa = Math.min(a[1], b[1]) - pad, maxLa = Math.max(a[1], b[1]) + pad
    const sc = Math.min(90 / (maxLo - minLo), 50 / (maxLa - minLa))
    const pt = ([lo, la]) => [3 + (lo - minLo) * sc, 3 + (maxLa - la) * sc]
    const p = pt(a), q = pt(b)
    let dots = ''
    for (let x = 4; x < 96; x += 6) for (let y = 4; y < 56; y += 6) dots += `<circle cx="${x}" cy="${y}" r=".7" fill="#302f2b"/>`
    const d = `M${p[0]},${p[1]} Q${(p[0] + q[0]) / 2},${Math.min(p[1], q[1]) - 14} ${q[0]},${q[1]}`
    return `<svg class="mini-route" viewBox="0 0 96 56" aria-hidden="true">${dots}
      <path id="rt${i}" d="${d}" fill="none" stroke="#79b394" stroke-width="1.4" stroke-dasharray="3 3"/>
      <circle cx="${p[0]}" cy="${p[1]}" r="3" fill="#bdbab3"/><circle cx="${q[0]}" cy="${q[1]}" r="3.4" fill="none" stroke="#edebe6" stroke-width="1.4"/>
      <circle r="3" fill="#79b394"><animateMotion dur="${2.2 + i * 0.4}s" repeatCount="indefinite" path="${d}"/></circle></svg>`
  }
  function altFor(po) {
    for (const a of D.alternatives) if (a.component === po.component_id && a.plant === po.plant_id) { const x = a.accepted.find((c) => c.site === po.site_id); if (x) return x }
    return null
  }
  function slots(allocs, n) {
    const total = allocs.reduce((a, x) => a + x.qty, 0)
    const raw = allocs.map((x) => (x.qty / total) * n)
    const base = raw.map((r) => Math.max(1, Math.floor(r)))
    let left = n - base.reduce((a, b) => a + b, 0)
    const order = raw.map((r, i) => [r - Math.floor(r), i]).sort((a, b) => b[0] - a[0])
    for (let i = 0; left > 0; i = (i + 1) % order.length, left--) base[order[i][1]]++
    return base
  }
  function holdSvg(po) {
    const air = po.mode === 'air'
    const cols = 14, rows = 3, n = cols * rows
    const counts = slots(po.allocations, n)
    const x0 = air ? 120 : 70, x1 = 660, y0 = 52, y1 = 186
    const sw = (x1 - x0) / cols, sh = (y1 - y0) / rows
    let s = `<svg class="hold-svg" viewBox="0 0 760 240" role="img" aria-label="${po.qty} batteries, split across ${po.allocations.length} orders"><ellipse cx="380" cy="224" rx="330" ry="8" fill="#000" opacity=".45"/>`
    s += air
      ? `<polygon points="60,30 716,30 716,210 130,210 60,140" fill="#1f1e1c" stroke="#3a3834" stroke-width="1.5"/>${Array.from({ length: 22 }, (_, i) => `<line x1="${80 + i * 30}" y1="34" x2="${80 + i * 30 - 40}" y2="206" stroke="#262522"/>`).join('')}<text x="78" y="56" font-size="11" fill="#5d5b56">air cargo box</text>`
      : `<rect x="40" y="30" width="676" height="180" rx="4" fill="#1f1e1c" stroke="#3a3834" stroke-width="1.5"/>${Array.from({ length: 46 }, (_, i) => `<line x1="${52 + i * 14}" y1="34" x2="${52 + i * 14}" y2="206" stroke="#262522" stroke-width="2"/>`).join('')}
        <rect x="676" y="34" width="36" height="172" fill="#232220" stroke="#3a3834"/><line x1="688" y1="40" x2="688" y2="200" stroke="#5d5b56" stroke-width="2"/><line x1="700" y1="40" x2="700" y2="200" stroke="#5d5b56" stroke-width="2"/>
        ${[[40, 30], [704, 30], [40, 198], [704, 198]].map(([x, y]) => `<rect x="${x}" y="${y}" width="12" height="12" fill="#3a3834"/>`).join('')}<text x="58" y="50" font-size="11" fill="#5d5b56">sea container</text>`
    let k = 0
    po.allocations.forEach((a, ai) => {
      for (let j = 0; j < counts[ai]; j++, k++) {
        const c = Math.floor(k / rows), r = k % rows
        const x = x0 + c * sw + 3, y = y0 + r * sh + 3
        s += `<rect class="slot" data-o="${a.order_id}" style="animation-delay:${k * 25}ms;fill:var(--st-${state.approved ? 'protected' : 'covered'})" x="${x}" y="${y}" width="${sw - 6}" height="${sh - 6}" rx="4" fill-opacity="${0.18 + (ai % 3) * 0.12}" stroke="#4a4844"/>`
        if (j === 0) s += `<g class="slot-t" style="animation-delay:${k * 25 + 420}ms" pointer-events="none"><text x="${x + 6}" y="${y + 16}" font-size="10" fill="#edebe6" font-family="JetBrains Mono">${a.order_id.replace('SO-', '')}</text><text x="${x + 6}" y="${y + 29}" font-size="9.5" fill="#bdbab3">${a.qty}</text></g>`
      }
    })
    return s + '</svg>'
  }
  function ganttSvg() {
    const W = 1000, x0 = 230, x1 = W - 16, RH = 46
    const X = (d) => x0 + (d / H) * (x1 - x0)
    const h = 40 + D.plan.pos.length * RH + 20
    let s = `<svg class="gantt-svg" viewBox="0 0 ${W} ${h}" role="img" aria-label="When the new batteries arrive">`
    for (let d = 0; d <= H; d += 7) s += `<line x1="${X(d)}" y1="26" x2="${X(d)}" y2="${h - 14}" stroke="#262522"/><text x="${X(d)}" y="18" text-anchor="middle" font-size="10.5" fill="#5d5b56">${d ? `day ${d}` : 'today'}</text>`
    const marks = [[plant('PL-PEN').stockout_day, 'Penang runs out', 'var(--st-late)'], [plant('PL-BAC').stockout_day, 'Bac Ninh runs out', 'var(--st-covered)'], [D.declared.end_day, 'VoltCell works again', '#8f8d87']]
    marks.forEach(([d, t, c], i) => (s += `<line x1="${X(d)}" y1="26" x2="${X(d)}" y2="${h - 14}" style="stroke:${c}" stroke-dasharray="3 3"/><text x="${X(d) + (i === 2 ? 6 : -6)}" y="${h - 4}" text-anchor="${i === 2 ? 'start' : 'end'}" font-size="10" style="fill:${c}">${t}</text>`))
    D.plan.pos.forEach((po, i) => {
      const y = 34 + i * RH, lead = altFor(po)?.lead_days ?? 0
      s += `<g data-po="${i}" style="cursor:pointer">
        <rect x="0" y="${y - 4}" width="${W}" height="${RH - 4}" rx="8" fill="${i === state.po ? '#1f1e1c' : 'transparent'}"/>
        <text x="10" y="${y + 13}" font-size="12" fill="#edebe6">${esc(N[po.site_id].operator)} to ${PLANT_SHORT[po.plant_id]}</text>
        <text x="10" y="${y + 29}" font-size="10.5" fill="#8f8d87">${fmt(po.qty)} batteries by ${po.mode}</text>
        <rect class="grow" style="animation-delay:${i * 120}ms" x="${X(0)}" y="${y + 6}" width="${X(lead) - X(0)}" height="16" rx="5" fill="#34322e"/>
        ${X(lead) - X(0) > 70 ? `<text x="${X(0) + 6}" y="${y + 18}" font-size="10" fill="#bdbab3">making ${lead}d</text>` : ''}
        <rect class="grow" style="animation-delay:${i * 120 + 300}ms;fill:var(--st-protected)" x="${X(lead)}" y="${y + 6}" width="${X(po.first_arrival_day) - X(lead)}" height="16" rx="5" fill-opacity="${state.approved ? 0.55 : 0.25}"/>
        ${X(po.first_arrival_day) - X(lead) > 70 ? `<text x="${X(lead) + 6}" y="${y + 18}" font-size="10" fill="#edebe6">shipping</text>` : ''}
        <text x="${X(po.first_arrival_day) + 8}" y="${y + 18}" font-size="10.5" fill="#edebe6">arrives day ${po.first_arrival_day}</text>
        ${po.allocations.map((a) => { const o = orderOf(a.order_id); return o ? `<path d="M${X(o.need_day)},${y + 26} l4,5 -4,5 -4,-5Z" style="fill:var(--st-late)" opacity=".85"><title>${a.order_id} is due on day ${o.need_day}</title></path>` : '' }).join('')}
      </g>`
    })
    return s + '</svg>'
  }
  function logistics() {
    const pos = D.plan.pos, po = pos[state.po], alt = altFor(po)
    const ship = po.mode === 'air' ? alt?.air_transit_days : alt?.transit_days
    $('#view-logistics').innerHTML = `
      ${head(state.approved ? 'Shipments on the way' : 'Shipments in the plan', `The plan buys batteries from new suppliers. Each card is one order to a supplier. ${state.approved ? 'They are ordered, not delivered yet.' : 'Nothing is ordered until you approve.'}`)}
      <div class="ship-strip">${pos.map((p, i) => `<button class="ship ${i === state.po ? 'on' : ''}" data-po="${i}">
        <div><b>${esc(N[p.site_id].operator)}</b><div class="sub">to our ${PLANT_SHORT[p.plant_id]} factory</div>
          <div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:6px"><span class="tag">${p.mode === 'air' ? 'by air' : 'by sea'}</span><span class="tag">arrives day ${p.first_arrival_day}</span></div></div>
        ${miniRoute(p, i)}</button>`).join('')}</div>
      <div class="log-grid">
        <div class="card">
          <div class="hold-head">
            <p class="plain" style="margin:0;max-width:62ch"><b>${fmt(po.qty)} batteries</b> from ${esc(name(po.site_id))} to our ${PLANT_SHORT[po.plant_id]} factory, by ${po.mode}. ${alt ? `${alt.lead_days} days to make, ${ship} days to ship.` : ''} First batteries arrive on <b>day ${po.first_arrival_day}</b>.</p>
            <span class="tag"><i class="dot st-${state.approved ? 'protected' : 'covered'}"></i>${state.approved ? 'Ordered, not delivered yet' : 'Waiting for your OK'}</span>
          </div>
          <div id="hold">${holdSvg(po)}</div>
          <div class="sub" style="padding:0 18px 16px">Each block is a share of this shipment, marked with the customer order it is for.${alt?.exposure_warning ? ' Watch out: this supplier also gets some cells from the stopped factory, so DOMINO only counts its clean supply.' : ''}</div>
        </div>
        <div class="card"><div class="card-b">
          <div class="side-h"><h3>Who gets these batteries</h3></div>
          <div style="overflow-x:auto"><table><thead><tr><th>Order</th><th>Customer</th><th class="r">Batteries</th><th class="r">Arrive</th><th class="r">Due</th></tr></thead><tbody>
          ${po.allocations.map((a) => { const o = orderOf(a.order_id); return `<tr data-o="${a.order_id}"><td class="mono">${a.order_id}</td><td>${esc(name(o?.customer ?? ''))}</td><td class="r">${a.qty}</td><td class="r">day ${a.arrival_day}</td><td class="r">day ${o?.need_day ?? ''}</td></tr>` }).join('')}
          </tbody></table></div></div></div>
      </div>
      <div class="card" style="margin-top:16px"><div class="card-h"><h2>When the new batteries arrive</h2><span class="sub">grey is making, green is shipping, pink marks are the days customers need their orders</span></div>
        <div class="card-b" style="overflow-x:auto">${ganttSvg()}</div></div>`
    $$('[data-po]').forEach((b) => (b.onclick = () => { state.po = +b.dataset.po; logistics() }))
    $$('tr[data-o]').forEach((tr) => {
      tr.onmouseenter = () => { $('#hold').classList.add('holding'); $$('.slot').forEach((r) => r.classList.toggle('hl', r.dataset.o === tr.dataset.o)) }
      tr.onmouseleave = () => $('#hold').classList.remove('holding')
    })
  }

  /* ================= AI AGENT ================= */
  const STEPS = [
    ['detect', 'Detect', 'Read the news alert', ['resolve_entities', 'declare_incident']],
    ['trace', 'Trace', 'Follow the supply chain', ['trace_exposure', 'explain_shared_dependencies', 'get_entity_context', 'recall_history']],
    ['impact', 'Impact', 'Find orders that will be late', ['project_shortages', 'flag_orders_at_risk']],
    ['options', 'Options', 'Look for other suppliers', ['compute_true_capacity', 'find_alternatives']],
    ['simulate', 'Simulate', 'Test 5 plans', ['simulate_strategies']],
    ['approve', 'Approve', 'Ask you', ['submit_plan_for_approval', 'get_decision_status']],
    ['verify', 'Verify', 'Check it worked', ['verify_execution', 'record_lessons', 'submit_incident_report']],
  ]
  const CYPHER = {
    trace_exposure: [
      ['exposure/exposure.cypher', `// Q-EXPOSURE: multi-tier exposure of unknown depth, with the evidence path for every hit.
MATCH (inc:Incident {id: $incident_id})-[a:AFFECTS]->(d:Site)
MATCH chain = (d)-[:FEEDS*0..4]->(t1:Site)
MATCH (t1)-[sup:SUPPLIES]->(pl:Plant)-[b:BUILDS]->(prod:Product)-[req:REQUIRES]->(k:Component)
WHERE k.id = sup.component_id
MATCH (o:Order)-[fp:FOR_PRODUCT]->(prod)
MATCH (o)-[fa:FULFILLED_AT]->(pl)
WHERE o.status = 'open' AND o.need_day <= $horizon
RETURN d.id AS origin, [n IN nodes(chain) | n.id] AS supply_path, length(chain) AS upstream_hops,
       t1.id AS tier1, k.id AS component, prod.id AS product, pl.id AS plant,
       collect(o.id) AS orders, sum(o.value_cents) AS value_cents
ORDER BY origin, tier1, plant, component, product, upstream_hops`, { incident_id: 'INC-0001', horizon: 42 }],
      ['exposure/tier1_view.cypher', `// Q-TIER1-VIEW: what a tier-1-only system sees. Affected sites that themselves supply a plant.
MATCH (inc:Incident {id: $incident_id})-[a:AFFECTS]->(s:Site)-[sup:SUPPLIES]->(pl:Plant)
RETURN count(DISTINCT s) AS directly_affected_tier1, collect(DISTINCT s.id) AS sites`, { incident_id: 'INC-0001' }],
    ],
  }
  const hiCypher = (q) => esc(q).split('\n').map((l) => (l.startsWith('//') ? `<span class="cm">${l}</span>` : l.replace(/\b(MATCH|WHERE|RETURN|ORDER BY|AS|AND|IN|collect|count|sum|length|nodes|DISTINCT)\b/g, '<span class="kw">$1</span>'))).join('\n')
  function stepState(id) {
    if (id === 'approve') return state.approved ? 'done' : 'wait'
    if (id === 'verify') return state.approved ? 'done' : 'todo'
    return 'done'
  }
  function agent() {
    const calls = D.steps
    const intro = !state.agentSeen
    const nodeHtml = STEPS.map(([id, title, plain, tools], i) => {
      const mine = calls.filter((c) => tools.includes(c.tool)), ss = stepState(id)
      return `<button class="node ${ss === 'wait' ? 'wait' : ''} ${ss === 'todo' ? 'todo' : ''} ${state.node === id ? 'sel' : ''} ${intro ? 'intro' : ''}" style="animation-delay:${i * 180}ms" data-node="${id}">
        <div class="node-h"><b>${title}</b><span class="node-n">${String(i + 1).padStart(2, '0')}</span></div>
        <div class="node-plain">${plain}</div>
        <div class="sub" style="margin:2px 0 6px;display:flex;align-items:center;gap:6px"><i class="dot st-${ss === 'done' ? 'protected' : ss === 'wait' ? 'covered' : 'none'}"></i>${ss === 'done' ? 'done' : ss === 'wait' ? 'waiting for you' : 'after you approve'}</div>
        ${(ss === 'todo' ? [] : mine).map((c) => `<div class="tool"><span>${c.tool}</span><span class="mono">${c.ms} ms</span></div>`).join('')}
      </button>`
    }).join('')
    const strat = D.strategies, maxLate = Math.max(...strat.map((s) => s.late)), pl = D.plan
    const checksOk = D.verify.filter((c) => c.ok).length
    $('#view-agent').innerHTML = `
      ${head('How the AI agent worked', 'DOMINO ran 7 steps on its own. It used only fixed, safe tools on the graph and never wrote anything without you. Click a step to see exactly what it ran.')}
      <div class="agent-grid">
        <div class="canvas ${intro ? 'intro' : ''}" id="canvas">
          <svg class="canvas-svg" id="wires"></svg>
          ${nodeHtml}
          <div class="drawer" id="drawer"></div>
          <div class="canvas-bar"><button id="replay">Replay the run</button><button data-node-open="trace">Show the database query</button></div>
        </div>
        <div class="side-stack">
          <div class="card approval ${state.approved ? 'done' : ''}"><div class="card-b" style="padding-top:16px">
            ${state.approved ? `
              <div class="side-h"><h2>Plan done</h2><span class="tag"><i class="dot st-protected"></i>all checks passed</span></div>
              <p class="plain">${D.receipt.pos_created} orders were sent to suppliers. ${D.receipt.orders_protected.length} customer orders are protected (projected) until the batteries arrive.</p>
              <details class="checks-box"><summary>${checksOk} of ${D.verify.length} safety checks passed</summary>
                <div class="checks">${D.verify.map((c) => `<div class="check"><b><i class="dot st-${c.ok ? 'protected' : 'disrupted'}"></i>${c.id}</b>${esc(c.name)}</div>`).join('')}</div></details>
              <button class="btn btn-ghost wide" id="undo" style="margin-top:12px">Back to the approval (concept only)</button>` : `
              <div class="side-h"><h2>Approve the rescue plan</h2><span class="tag"><i class="dot st-covered pulse"></i>needs you</span></div>
              <p class="plain">Buy batteries from ${suppliersInPlan.length} other suppliers so ${S4.protected_projected} late orders can still ship.</p>
              <div class="appr-v">
                <div><span class="sub">Cost</span><b>${usd(pl.spend_cents)}</b><div class="budget"><i style="width:${(pl.spend_cents / D.budget_cents) * 100}%"></i></div><span class="sub">of ${usd(D.budget_cents)} budget</span></div>
                <div><span class="sub">Supplier orders</span><b>${pl.pos.length}</b></div>
                <div><span class="sub">Orders saved</span><b>${S4.protected_projected}</b><span class="sub">protected (projected)</span></div>
                <div><span class="sub">Still late</span><b>${S4.late}</b></div>
              </div>
              <div class="sub">Your OK is tied to this exact plan (<span class="mono">${pl.plan_hash}</span>). If anything changes, DOMINO asks again.</div>
              <div class="fix-actions" style="margin-top:12px"><button class="btn btn-accent" id="approve">Approve plan</button><button class="btn btn-ghost">Reject</button></div>`}
          </div></div>
          <div class="card"><div class="card-b"><div class="side-h"><h3>The 5 plans it tested</h3><span class="sub">late orders, cost</span></div>
            ${strat.map((s) => `<div class="strat ${s.strategy === D.recommended ? 'rec' : ''}"><span class="mono">${s.strategy}</span>
              <div><div style="display:flex;justify-content:space-between"><span>${esc(s.name)}</span><span class="num">${s.late} late</span></div><div class="bar"><i style="width:${(s.late / maxLate) * 100}%"></i></div></div>
              <span class="num" style="text-align:right">${usd(s.spend_cents)}</span><span style="text-align:right">${s.strategy === D.recommended ? '<span class="tag"><i class="dot st-protected"></i>best</span>' : ''}</span></div>`).join('')}</div></div>
          ${state.approved ? `<div class="card"><div class="card-b"><div class="side-h"><h3>What it learned</h3></div><p class="plain">${esc(D.lesson[0].text)}</p></div></div>` : ''}
        </div>
      </div>`
    state.agentSeen = true
    $('#approve')?.addEventListener('click', approve)
    $('#undo')?.addEventListener('click', unapprove)
    $$('[data-node]').forEach((b) => (b.onclick = () => openDrawer(b.dataset.node)))
    $('[data-node-open]').onclick = () => openDrawer('trace')
    $('#replay').onclick = replay
    if (state.node) openDrawer(state.node, true)
    layoutNodes()
  }
  const phone = () => matchMedia('(max-width: 760px)').matches
  function layoutNodes() {
    const c = $('#canvas'); if (!c) return
    if (phone()) { c.style.height = ''; $('#drawer').style.top = ''; $$('.node').forEach((n) => { n.style.left = n.style.top = n.style.width = '' }); return }
    const pad = 20, gap = 18, W = c.clientWidth, w = (W - 2 * pad - 3 * gap) / 4
    const at = (id, col, top) => { const n = $(`[data-node="${id}"]`); n.style.width = w + 'px'; n.style.left = pad + col * (w + gap) + 'px'; n.style.top = top + 'px'; return n }
    const row1 = ['detect', 'trace', 'impact', 'options'].map((id, i) => at(id, i, 22))
    const top2 = 22 + Math.max(...row1.map((n) => n.offsetHeight)) + 64
    const row2 = [['verify', 1], ['approve', 2], ['simulate', 3]].map(([id, i]) => at(id, i, top2))
    const bottom = top2 + Math.max(...row2.map((n) => n.offsetHeight))
    const open = $('#drawer').classList.contains('open')
    $('#drawer').style.top = bottom + 26 + 'px'
    c.style.height = bottom + (open ? Math.min(380, $('#drawer').scrollHeight) + 110 : 90) + 'px'
    requestAnimationFrame(wires)
  }
  function openDrawer(id, keep) {
    if (!keep && state.node === id && $('#drawer').classList.contains('open')) { state.node = null; $('#drawer').classList.remove('open'); $$('.node').forEach((n) => n.classList.remove('sel')); layoutNodes(); return }
    state.node = id
    $$('.node').forEach((n) => n.classList.toggle('sel', n.dataset.node === id))
    const [, title, plain, tools] = STEPS.find((s) => s[0] === id)
    const calls = D.steps.filter((c) => tools.includes(c.tool) && stepState(id) !== 'todo')
    const cy = calls.flatMap((c) => CYPHER[c.tool] ?? [])
    $('#drawer').innerHTML = `<div class="drawer-h"><h3>${title}: ${plain.toLowerCase()}</h3><button class="link" id="closeDrawer">Close</button></div>
      ${calls.length ? calls.map((c) => `<pre><span class="cm">// tool ${c.tool}, ${c.ms} ms, inputs:</span>\n${esc(JSON.stringify(c.args, null, 2))}</pre>`).join('') : '<pre>This step runs after you approve the plan.</pre>'}
      ${cy.map(([file, q, params]) => `<pre><span class="cm">// database query queries/${file}, values ${esc(JSON.stringify(params))}</span>\n${hiCypher(q)}</pre>`).join('')}`
    $('#drawer').classList.add('open')
    $('#closeDrawer').onclick = () => openDrawer(id)
    layoutNodes()
  }
  function wires() {
    const c = $('#canvas'); if (!c) return
    const svg = $('#wires'), r = c.getBoundingClientRect()
    const box = (id) => { const b = $(`[data-node="${id}"]`).getBoundingClientRect(); return { l: b.left - r.left, t: b.top - r.top, r: b.right - r.left, b: b.bottom - r.top, cx: (b.left + b.right) / 2 - r.left, cy: (b.top + b.bottom) / 2 - r.top } }
    const ids = STEPS.map((x) => x[0])
    let s = ''
    for (let i = 0; i + 1 < ids.length; i++) {
      const a = box(ids[i]), b = box(ids[i + 1]), ss = stepState(ids[i + 1])
      const col = ss === 'todo' ? '#3a3834' : ss === 'wait' ? '#d7a85a' : '#5d5b56'
      const d = Math.abs(a.t - b.t) < 20
        ? (a.r < b.l ? `M${a.r},${a.cy} C${a.r + 24},${a.cy} ${b.l - 24},${b.cy} ${b.l},${b.cy}` : `M${a.l},${a.cy} C${a.l - 24},${a.cy} ${b.r + 24},${b.cy} ${b.r},${b.cy}`)
        : `M${a.cx},${a.b} C${a.cx},${a.b + 40} ${b.cx},${b.t - 40} ${b.cx},${b.t}`
      const end = d.split(' ').pop().split(',')
      s += `<path class="${ss === 'wait' ? 'flow' : 'draw'}" style="animation-delay:${i * 180 + 120}ms" pathLength="1" d="${d}" fill="none" stroke="${col}" stroke-width="1.5"/><circle cx="${end[0]}" cy="${end[1]}" r="3" fill="${col}"/>`
    }
    svg.innerHTML = s
  }
  function replay() {
    const c = $('#canvas')
    c.classList.remove('intro'); $$('.node', c).forEach((n) => n.classList.remove('intro'))
    void c.offsetWidth
    c.classList.add('intro'); $$('.node', c).forEach((n) => n.classList.add('intro'))
    wires()
  }
  window.addEventListener('resize', () => state.view === 'agent' && layoutNodes())

  shell()
})()
