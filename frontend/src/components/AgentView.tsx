import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { fmt, plural, usd, useModel, type Model } from '../lib/model'
import { api } from '../lib/api'
import { STEPS, useStore, type StepId } from '../lib/store'
import type { Memory } from '../lib/types'
import { Head, RunPanel } from './Controls'

/* eslint-disable @typescript-eslint/no-explicit-any */

const PLAIN: Record<StepId, string> = {
  detect: 'Read the news alert', trace: 'Follow the supply chain', impact: 'Find orders that will be late', options: 'Look for other suppliers',
  simulate: 'Test the plans', approve: 'Ask you', verify: 'Check it worked',
}
const KW = /\b(MATCH|OPTIONAL MATCH|WHERE|RETURN|ORDER BY|WITH|UNWIND|CREATE|MERGE|SET|AS|AND|OR|NOT|IN|collect|count|sum|min|max|length|nodes|DISTINCT|LIMIT)\b/g
function Cypher({ text }: { text: string }) {
  return (
    <>
      {text.split('\n').map((l, i) => {
        if (l.trimStart().startsWith('//')) return <span key={i} className="cm">{l}{'\n'}</span>
        const parts = l.split(KW)
        return <span key={i}>{parts.map((p, j) => (j % 2 ? <span key={j} className="kw">{p}</span> : p))}{'\n'}</span>
      })}
    </>
  )
}

function stepState(m: Model, id: StepId): 'done' | 'wait' | 'todo' | 'active' {
  const mine = m.steps.filter((s) => STEPS.find((x) => x.id === id)!.tools.includes(s.tool))
  if (id === 'approve' && (m.phase === 'awaiting' || m.phase === 'approving')) return 'wait'
  if (mine.some((s) => s.state === 'running')) return 'active'
  if (mine.length) return 'done'
  return 'todo'
}

const WHEN = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
const learned = (d: string) => (d ? WHEN.format(new Date(`${d}T00:00:00`)) : 'date not recorded')

/** Past incidents and lessons from the memory graph (GET /api/memory). Demo runs keep their own memory. */
function MemoryPanel({ refresh }: { refresh: string }) {
  const st = useStore()
  // follows the run mode (demo runs read memory:dryrun) until the viewer picks one
  const [picked, setSource] = useState<'real' | 'demo' | null>(null)
  const source = picked ?? (st.mode === 'scripted' ? 'demo' : 'real')
  const [mem, setMem] = useState<Memory | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    let live = true
    api.memory(source).then((r) => { if (live) { setMem(r); setErr(null) } }, (e: Error) => { if (live) setErr(e.message) })
    return () => { live = false }
  }, [source, refresh])
  const names = (es: Memory['lessons'][number]['entities']) => es.map((e) => (
    <span className={`mem-ent ${e.in_world ? '' : 'gone'}`} key={e.id} title={e.in_world ? e.id : `${e.id}: not in the current world (that does not mean it is safe)`}>{e.name}</span>
  ))
  return (
    <div className="card"><div className="card-b">
      <div className="side-h"><h3>What DOMINO remembers</h3>
        <div className="chip-toggle" role="group" aria-label="Which memory">
          <button type="button" className={source === 'real' ? 'on' : ''} onClick={() => setSource('real')}>Real runs</button>
          <button type="button" className={source === 'demo' ? 'on' : ''} onClick={() => setSource('demo')}>Demo runs</button>
        </div>
      </div>
      {err && <p className="plain">Could not read memory: {err}</p>}
      {mem && !err && (mem.counts.lessons === 0 && mem.counts.incidents === 0 ? (
        <p className="plain muted">Nothing remembered yet. {source === 'demo' ? 'Finish a demo run and its lessons appear here.' : 'Lessons from real agent runs appear here once a run finishes.'}</p>
      ) : (
        <>
          <p className="sub">{plural(mem.counts.incidents, 'past incident')}, {plural(mem.counts.lessons, 'lesson')}. Kept in <span className="mono">{mem.graph}</span>, which survives a world reset. The agent can look these up with its recall_history tool.</p>
          {mem.incidents.map((inc) => {
            const ls = mem.lessons.filter((l) => l.incident_id === inc.id)
            return (
              <div className="mem-inc" key={inc.id}>
                <div className="mem-h">
                  <span className="mono" title={inc.id !== inc.incident_id ? `memory record ${inc.id}` : undefined}>{inc.incident_id ?? inc.id}</span>
                  <span className="sub">learned {learned(inc.learned_on)}</span>
                </div>
                {inc.title && inc.title !== inc.id && <p className="plain">{inc.title}</p>}
                {ls.map((l) => (
                  <div className="mem-lesson" key={l.id}>
                    <p className="plain">{l.text}</p>
                    <div className="mem-ents">{names(l.entities)}{l.evidence.length > 0 && <span className="mono muted">evidence {l.evidence.join(', ')}</span>}</div>
                  </div>
                ))}
              </div>
            )
          })}
          {mem.lessons.filter((l) => !mem.incidents.some((i) => i.id === l.incident_id)).map((l) => (
            <div className="mem-lesson" key={l.id}><p className="plain">{l.text}</p><div className="mem-ents">{names(l.entities)}<span className="sub">learned {learned(l.learned_on)}</span></div></div>
          ))}
        </>
      ))}
    </div></div>
  )
}

export function AgentView() {
  const m = useModel()
  const st = useStore()
  const [node, setNode] = useState<StepId | null>(null)
  const [intro, setIntro] = useState(1)
  const [rejecting, setRejecting] = useState(false)
  const [feedback, setFeedback] = useState('')
  const canvas = useRef<HTMLDivElement>(null)
  const drawer = useRef<HTMLDivElement>(null)
  const [wires, setWires] = useState<{ d: string; col: string; flow: boolean; end: [number, number] }[]>([])
  const [height, setHeight] = useState<number | undefined>(undefined)

  // lay out the seven steps in two rows (snake) and draw the wires; on phones the CSS stacks them instead
  useLayoutEffect(() => {
    const c = canvas.current
    if (!c) return
    const layout = () => {
      const nodes = [...c.querySelectorAll<HTMLElement>('.node')]
      if (matchMedia('(max-width: 760px)').matches) {
        nodes.forEach((n) => { n.style.left = n.style.top = n.style.width = '' })
        setWires([]); setHeight(undefined); return
      }
      const pad = 20, gap = 18, w = (c.clientWidth - 2 * pad - 3 * gap) / 4
      const at = (id: string, col: number, top: number) => { const n = c.querySelector<HTMLElement>(`[data-node="${id}"]`)!; n.style.width = `${w}px`; n.style.left = `${pad + col * (w + gap)}px`; n.style.top = `${top}px`; return n }
      const row1 = ['detect', 'trace', 'impact', 'options'].map((id, i) => at(id, i, 22))
      const top2 = 22 + Math.max(...row1.map((n) => n.offsetHeight)) + 64
      const row2 = [['verify', 1], ['approve', 2], ['simulate', 3]].map(([id, i]) => at(id as string, i as number, top2))
      const bottom = top2 + Math.max(...row2.map((n) => n.offsetHeight))
      const dr = drawer.current
      if (dr) dr.style.top = `${bottom + 26}px`
      setHeight(bottom + (node && dr ? Math.min(380, dr.scrollHeight) + 110 : 90))
      const box = (id: string) => { const n = c.querySelector<HTMLElement>(`[data-node="${id}"]`)!; return { l: n.offsetLeft, t: n.offsetTop, r: n.offsetLeft + n.offsetWidth, b: n.offsetTop + n.offsetHeight, cx: n.offsetLeft + n.offsetWidth / 2, cy: n.offsetTop + n.offsetHeight / 2 } }
      const ids = STEPS.map((s) => s.id)
      const out: typeof wires = []
      for (let i = 0; i + 1 < ids.length; i++) {
        const a = box(ids[i]), b = box(ids[i + 1]), ss = stepState(m, ids[i + 1])
        const col = ss === 'todo' ? '#3a3834' : ss === 'wait' ? '#d7a85a' : '#5d5b56'
        let d: string, end: [number, number]
        if (Math.abs(a.t - b.t) < 20) {
          if (a.r < b.l) { d = `M${a.r},${a.cy} C${a.r + 24},${a.cy} ${b.l - 24},${b.cy} ${b.l},${b.cy}`; end = [b.l, b.cy] }
          else { d = `M${a.l},${a.cy} C${a.l - 24},${a.cy} ${b.r + 24},${b.cy} ${b.r},${b.cy}`; end = [b.r, b.cy] }
        } else { d = `M${a.cx},${a.b} C${a.cx},${a.b + 40} ${b.cx},${b.t - 40} ${b.cx},${b.t}`; end = [b.cx, b.t] }
        out.push({ d, col, flow: ss === 'wait', end })
      }
      setWires(out)
    }
    layout()
    window.addEventListener('resize', layout)
    return () => window.removeEventListener('resize', layout)
  }, [m, node])

  const strat: any[] = m.sim?.strategies ?? []
  const maxLate = Math.max(1, ...strat.map((s) => s.late))
  const pl = m.plan, rec = m.rec
  const sel = node ? STEPS.find((s) => s.id === node)! : null
  const selCalls = sel ? m.steps.filter((s) => sel.tools.includes(s.tool)) : []
  return (
    <>
      <Head title="How the AI agent worked" text="DOMINO works in seven steps. It only uses fixed, safe tools on the graph, and it never places a purchase order without your OK. Click a step to see exactly what it ran, including the database queries." />
      <div className="agent-grid">
        <div className={`canvas ${intro ? 'intro' : ''}`} ref={canvas} style={{ height }} key={intro}>
          <svg className="canvas-svg">
            {wires.map((w, i) => (
              <g key={i}>
                <path className={w.flow ? 'flow' : 'draw'} {...(w.flow ? {} : { pathLength: 1 })} style={{ animationDelay: `${i * 180 + 120}ms` }} d={w.d} fill="none" stroke={w.col} strokeWidth={1.5} />
                <circle cx={w.end[0]} cy={w.end[1]} r={3} fill={w.col} />
              </g>
            ))}
          </svg>
          {STEPS.map((s, i) => {
            const ss = stepState(m, s.id)
            const mine = m.steps.filter((x) => s.tools.includes(x.tool))
            return (
              <button key={s.id} type="button" data-node={s.id} className={`node ${ss === 'wait' ? 'wait' : ''} ${ss === 'todo' ? 'todo' : ''} ${node === s.id ? 'sel' : ''} ${intro ? 'intro' : ''}`} style={{ animationDelay: `${i * 180}ms` }} onClick={() => setNode(node === s.id ? null : s.id)}>
                <div className="node-h"><b>{s.title}</b><span className="node-n">{s.num}</span></div>
                <div className="node-plain">{PLAIN[s.id]}</div>
                <div className="sub" style={{ margin: '2px 0 6px', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <i className={`dot st-${ss === 'done' ? 'protected' : ss === 'wait' || ss === 'active' ? 'covered' : 'none'} ${ss === 'active' ? 'pulse' : ''}`} />
                  {ss === 'done' ? 'done' : ss === 'wait' ? 'waiting for you' : ss === 'active' ? 'working' : m.phase === 'idle' ? 'not started' : 'not reached yet'}
                </div>
                {mine.map((c, j) => <div className="tool" key={j}><span>{c.tool}</span><span className="mono">{c.state === 'running' ? '…' : c.state === 'error' ? 'error' : `${c.ms} ms`}</span></div>)}
              </button>
            )
          })}
          <div className={`drawer ${node ? 'open' : ''}`} ref={drawer}>
            {sel && (
              <>
                <div className="drawer-h"><h3>{sel.title}: {PLAIN[sel.id].toLowerCase()}</h3><button type="button" className="link" onClick={() => setNode(null)}>Close</button></div>
                {!selCalls.length && <pre>This step has not run yet.</pre>}
                {selCalls.map((c, j) => (
                  <div key={j}>
                    <pre><span className="cm">{`// tool ${c.tool}${c.ref ? `, result ${c.ref}` : ''}${c.ms != null ? `, ${c.ms} ms` : ''}, inputs:`}</span>{'\n'}{JSON.stringify(c.args, null, 2)}</pre>
                    {(c.queries ?? []).map((q) => (
                      <pre key={q.name}><span className="cm">{`// database query queries/${q.name}.cypher, ran ${q.calls}x on ${q.graphs.join(', ')}, ${q.rows} rows, ${q.ms} ms\n// values ${JSON.stringify(q.params)}`}</span>{'\n'}<Cypher text={q.cypher} /></pre>
                    ))}
                  </div>
                ))}
              </>
            )}
          </div>
          <div className="canvas-bar">
            <button type="button" onClick={() => setIntro((n) => n + 1)}>Replay the animation</button>
            <button type="button" disabled={!m.steps.some((s) => s.tool === 'trace_exposure')} onClick={() => setNode('trace')}>Show a database query</button>
          </div>
        </div>

        <div className="side-stack">
          {pl && rec ? (
            <div className={`card approval ${m.executed ? 'done' : ''}`}><div className="card-b" style={{ paddingTop: 16 }}>
              {m.executed ? (
                <>
                  <div className="side-h"><h2>Plan done</h2><span className="tag"><i className={`dot st-${m.d.receipt?.receipt_matches_plan ? 'protected' : 'disrupted'}`} />{m.d.receipt?.receipt_matches_plan ? 'matches the plan' : 'receipt mismatch'}</span></div>
                  <p className="plain">{m.d.receipt?.pos_created} orders were sent to suppliers. {m.d.receipt?.orders_protected?.length} customer orders are protected (projected) until the parts arrive.</p>
                  {m.d.verify?.checks ? (
                    <details className="checks-box"><summary>{m.d.verify.checks.filter((c: any) => c.ok).length} of {m.d.verify.checks.length} safety checks passed</summary>
                      <div className="checks">{m.d.verify.checks.map((c: any) => <div className="check" key={c.id}><b><i className={`dot st-${c.ok ? 'protected' : 'disrupted'}`} />{c.id}</b>{c.name}</div>)}</div></details>
                  ) : <p className="sub" style={{ marginTop: 8 }}>Running the safety checks…</p>}
                </>
              ) : (
                <>
                  <div className="side-h"><h2>Approve the rescue plan</h2><span className="tag"><i className="dot st-covered pulse" />{m.phase === 'approving' ? 'placing orders' : 'needs you'}</span></div>
                  <p className="plain">Buy {m.part[1]} from {plural(m.suppliersInPlan.length, 'other supplier')} so {plural(rec.protected_projected, 'late order')} can still ship.</p>
                  <div className="appr-v">
                    <div><span className="sub">Cost</span><b>{usd(pl.spend_cents)}</b><div className="budget"><i style={{ width: `${m.sim?.budget_cents ? (pl.spend_cents / m.sim.budget_cents) * 100 : 0}%` }} /></div><span className="sub">of {usd(m.sim?.budget_cents)} budget</span></div>
                    <div><span className="sub">Supplier orders</span><b>{fmt(pl.pos?.length)}</b></div>
                    <div><span className="sub">Orders saved</span><b>{rec.protected_projected}</b><span className="sub">protected (projected)</span></div>
                    <div><span className="sub">Still late</span><b>{rec.late}</b></div>
                  </div>
                  <div className="sub">Your OK is tied to this exact plan (<span className="mono">{pl.plan_hash}</span>) on world version {m.d.declared?.world_version ?? '—'}. If anything changes, DOMINO asks again.</div>
                  <div className="fix-actions" style={{ marginTop: 12 }}>
                    <button type="button" className="btn btn-accent" disabled={m.phase !== 'awaiting'} onClick={() => void st.approve()}>{m.phase === 'approving' ? 'Approving' : 'Approve plan'}</button>
                    <button type="button" className="btn btn-ghost" disabled={m.phase !== 'awaiting'} onClick={() => setRejecting((r) => !r)}>Reject</button>
                  </div>
                  {rejecting && (
                    <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
                      <textarea className="pick" style={{ borderRadius: 12, height: 70, padding: 10, backgroundImage: 'none' }} placeholder="Tell DOMINO what to change, for example: keep spend under $100,000" value={feedback} onChange={(e) => setFeedback(e.target.value)} />
                      <button type="button" className="btn btn-ghost" disabled={!feedback.trim()} onClick={() => { void st.reject(feedback.trim()); setRejecting(false); setFeedback('') }}>Send feedback and re-plan</button>
                    </div>
                  )}
                </>
              )}
            </div></div>
          ) : (
            <div className="card"><div className="card-b">
              <div className="side-h"><h2>{m.phase === 'idle' ? 'Start the agent' : 'Controls'}</h2></div>
              <RunPanel compact />
            </div></div>
          )}
          {strat.length > 0 && (
            <div className="card"><div className="card-b"><div className="side-h"><h3>The plans it tested</h3><span className="sub">late orders, cost</span></div>
              {strat.map((s) => (
                <div className={`strat ${s.strategy === m.sim.recommended ? 'rec' : ''}`} key={s.strategy}><span className="mono">{s.strategy}</span>
                  <div><div style={{ display: 'flex', justifyContent: 'space-between' }}><span>{s.name}</span><span className="num">{s.late} late</span></div><div className="bar"><i style={{ width: `${(s.late / maxLate) * 100}%` }} /></div></div>
                  <span className="num" style={{ textAlign: 'right' }}>{usd(s.spend_cents)}</span><span style={{ textAlign: 'right' }}>{s.strategy === m.sim.recommended && <span className="tag"><i className="dot st-protected" />recommended</span>}</span></div>
              ))}</div></div>
          )}
          {m.steps.length > 0 && (
            <div className="card"><div className="card-b"><div className="side-h"><h3>Activity</h3><span className="sub">{m.steps.length} tool calls</span></div>
              <div className="activity">{m.steps.map((s, i) => <div className="act" key={i}><span className="mono">{s.t != null ? `+${s.t.toFixed(2)}s` : '…'}</span><span>{s.tool}</span><span className="mono">{s.ref ?? (s.state === 'error' ? 'error' : '')}</span></div>)}</div></div></div>
          )}
          {m.d.lessons.length > 0 && (
            <div className="card"><div className="card-b"><div className="side-h"><h3>What it learned</h3><span className="mono muted">{m.d.memoryGraph}</span></div>
              {m.d.lessons.map((l, i) => <p className="plain" key={i}>{l.text}</p>)}</div></div>
          )}
          <MemoryPanel refresh={m.phase} />
          {(pl || m.phase === 'done' || m.phase === 'failed') && <div className="card"><div className="card-b"><div className="side-h"><h3>Run again</h3></div><RunPanel compact /></div></div>}
        </div>
      </div>
    </>
  )
}
