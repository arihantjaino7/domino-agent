/* eslint-disable @typescript-eslint/no-explicit-any */
import { Check, Loader2, X } from 'lucide-react'
import { useState } from 'react'
import { Btn, Seg, spotHandlers } from '../lib/motion'
import { STEPS, currentStep, useStore, type StepId } from '../lib/store'
import { STATUS_VAR } from './GraphCanvas'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('en-US'))
const usd = (c: number | null | undefined) => (c == null ? '—' : `$${Math.round(c / 100).toLocaleString('en-US')}`)

/** Right-hand card: the detail of whichever step is in view, or the raw agent log. */
export function DetailPanel() {
  const st = useStore()
  const [tab, setTab] = useState<'step' | 'log'>('step')
  const step = st.selected ?? currentStep(st)
  const title = STEPS.find((s) => s.id === step)?.title ?? 'Overview'
  const simulating = st.steps.some((s) => s.tool === 'simulate_strategies' && s.state === 'running')
  return (
    <section className="card spot flex min-h-0 flex-col overflow-hidden" {...spotHandlers()}>
      <header className="flex items-center justify-between gap-3 border-b border-line-2 px-5 py-3">
        <h2 className="text-[17px]">{tab === 'log' ? 'Agent log' : title}</h2>
        <Seg label="Panel" value={tab} onChange={setTab} options={[{ value: 'step', label: 'Step' }, { value: 'log', label: `Log · ${st.steps.length}` }]} />
      </header>
      <div className={`min-h-0 flex-1 overflow-y-auto ${simulating && tab === 'step' && step === 'simulate' ? 'scanning' : ''}`} data-scan="Running every plan in its own sandbox…">
        <div key={`${tab}-${step}`} className="reveal px-5 py-4">
          {tab === 'log' ? <Log /> : <StepBody step={step} />}
        </div>
      </div>
    </section>
  )
}

function StepBody({ step }: { step: StepId | null }) {
  switch (step) {
    case 'detect': return <Detect />
    case 'trace': return <Trace />
    case 'impact': return <Impact />
    case 'options': return <Options />
    case 'simulate': return <Simulate />
    case 'approve': return <Approve />
    case 'verify': return <Verify />
    default: return <Idle />
  }
}

function Idle() {
  return (
    <div className="grid gap-4">
      <p className="text-[13.5px] leading-[1.6] text-ink-2">
        Press <b className="font-medium text-ink">Run DOMINO</b>. One Claude agent picks tools; deterministic engines compute every number; nothing is bought until you approve.
      </p>
      <ol className="stagger grid">
        {STEPS.map((s, i) => (
          <li key={s.id} className="row" style={{ ['--s' as string]: i }}>
            <span className="num w-6 text-[12px] text-accent">{s.num}</span>
            <span className="text-[13.5px] font-medium">{s.title}</span>
            <span className="ml-auto text-[12.5px] text-muted">{IDLE_HINT[s.id]}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}
const IDLE_HINT: Record<StepId, string> = {
  detect: 'alert → graph entities',
  trace: 'tier-1 view vs multi-tier',
  impact: 'exposed vs projected late',
  options: 'max-flow capacity, alternatives',
  simulate: 'plans in GRAPH.COPY sandboxes',
  approve: 'a human signs off',
  verify: 'nine invariants on the graph',
}

function Detect() {
  const d = useStore((s) => s.derived)
  return (
    <div className="grid gap-5">
      {d.resolve && (
        <div>
          <div className="label mb-2">Places in the alert</div>
          <ul className="stagger grid">
            {d.resolve.results.map((r: any, i: number) => (
              <li key={r.term} className="row" style={{ ['--s' as string]: i }}>
                <span className="text-[13.5px]">{r.term}</span>
                <span className="ml-auto flex flex-wrap justify-end gap-1.5">
                  {r.candidates.length ? r.candidates.slice(0, 3).map((c: any) => <span key={c.id} className="tag mono" style={{ ['--c' as string]: 'var(--accent)' }}>{c.id}</span>) : <span className="text-[12.5px] text-muted">not in the graph</span>}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {d.declared && (
        <div>
          <div className="label mb-2">Declared incident</div>
          <div className="kv"><span>Incident</span><b className="mono">{d.declared.incident_id}</b></div>
          <div className="kv"><span>Sites at 0%</span><b className="mono">{d.declared.site_ids?.join(', ')}</b></div>
          <div className="kv"><span>Disrupted until</span><b>day {d.declared.end_day}</b></div>
          <div className="kv"><span>World version</span><b>v{d.declared.world_version}</b></div>
        </div>
      )}
    </div>
  )
}

function Trace() {
  const d = useStore((s) => s.derived)
  const setHover = useStore((s) => s.setHoverEvidence)
  return (
    <div className="grid gap-5">
      <div className="grid grid-cols-2 gap-3">
        <div className="card p-4 shadow-none">
          <div className="label">Tier-1 view</div>
          <div className="display num mt-1 text-[40px] leading-none tracking-[-0.04em]">{n(d.tier1View)}</div>
          <p className="mt-1.5 text-[12px] text-muted">affected suppliers it can see</p>
        </div>
        <div className="card beam p-4 shadow-none">
          <div className="label">Multi-tier graph</div>
          <div className="display num mt-1 text-[40px] leading-none tracking-[-0.04em]" style={{ color: 'var(--accent)' }}>{n(d.exposedTier1.length)}</div>
          <p className="mt-1.5 text-[12px] text-muted">via {d.origins.join(', ')}</p>
        </div>
      </div>
      <div>
        <div className="label mb-2">Evidence paths · hover to see them on the map</div>
        <ul className="stagger grid">
          {d.evidence.map((ev, i) => (
            <li key={ev.id} className="row cursor-default" style={{ ['--s' as string]: i }} onMouseEnter={() => setHover(ev.id)} onMouseLeave={() => setHover(null)}>
              <span className="mono w-7 text-[12px] text-accent">{ev.id}</span>
              <span className="mono min-w-0 flex-1 truncate text-[12px]">{ev.path.join(' → ')}</span>
              <span className="shrink-0 text-[12px] text-muted">{ev.component} · {n(ev.orders)} orders</span>
            </li>
          ))}
        </ul>
      </div>
      {d.shared.map((s) => (
        <p key={s.site} className="text-[13px] leading-[1.55] text-ink-2">
          <span className="mono text-accent">{s.site}</span> ({s.operator}) feeds <b className="font-medium">{s.fan_out}</b> tier-1 suppliers, active or alternate:{' '}
          <span className="mono">{s.dependents.join(', ')}</span>. Backups that share it are not independent.
        </p>
      ))}
    </div>
  )
}

function Impact() {
  const d = useStore((s) => s.derived)
  const sh = d.shortage
  if (!sh) return <Waiting what="the shortage projection" />
  const late = (sh.orders ?? []).filter((o: any) => o.status === 'projected_late')
  return (
    <div className="grid gap-5">
      <div>
        <div className="label mb-2">Plants</div>
        <ul className="stagger grid">
          {sh.plants.filter((p: any) => p.exposed).map((p: any, i: number) => {
            const tone = p.projected_late ? 'late' : 'covered'
            return (
              <li key={p.plant} className="row" style={{ ['--s' as string]: i }}>
                <span className="dot" style={{ background: STATUS_VAR[tone] }} />
                <span className="mono text-[12.5px]">{p.plant}</span>
                <span className="text-[12.5px] text-muted">{n(p.exposed)} exposed · {n(p.projected_late)} late</span>
                <span className="ml-auto text-[12.5px]">{p.projected_late ? <>stockout day <b className="num font-medium">{p.stockout_day}</b></> : 'covered by stock + pipeline'}</span>
              </li>
            )
          })}
        </ul>
      </div>
      <div>
        <div className="label mb-2">Projected-late orders · {late.length}</div>
        <ul className="grid">
          {late.slice(0, 14).map((o: any) => (
            <li key={o.order_id} className="kv">
              <span className="mono">{o.order_id} · {o.plant} · {o.product}</span>
              <b>
                {o.tier === 'strategic' && <span className="tag mr-2" style={{ ['--c' as string]: 'var(--accent)' }}>strategic</span>}
                need day {o.need_day} · {o.beyond_horizon ? `≥${o.late_days}` : o.late_days}d late
              </b>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function Options() {
  const d = useStore((s) => s.derived)
  if (!d.capacity.length && !d.alternatives.length) return <Waiting what="capacity and alternatives" />
  const max = Math.max(1, ...d.capacity.map((c) => c.naive))
  return (
    <div className="grid gap-5">
      <div>
        <div className="label mb-2">Capacity per week · naive (tier-1 sum) vs true (max-flow)</div>
        <ul className="grid gap-3">
          {d.capacity.map((c, i) => (
            <li key={`${c.component}@${c.plant}`}>
              <div className="flex items-baseline justify-between text-[12.5px]">
                <span className="mono">{c.component} → {c.plant}</span>
                <span className="num text-muted">{n(c.naive)} → <b className="font-medium text-ink">{n(c.trueWk)}</b></span>
              </div>
              <div className="relative mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-2">
                <div className="bar-grow absolute inset-y-0 left-0 rounded-full bg-line" style={{ width: `${(c.naive / max) * 100}%`, ['--d' as string]: `${i * 120}ms` }} />
                <div className="bar-grow absolute inset-y-0 left-0 rounded-full bg-accent" style={{ width: `${(c.trueWk / max) * 100}%`, ['--d' as string]: `${i * 120 + 300}ms` }} />
              </div>
              {c.bottleneck.length > 0 && <p className="mt-1 text-[11.5px] text-muted">Bottleneck: {c.bottleneck.map((b: any) => `${b.what} (${n(b.cap)})`).join(' · ')}</p>}
            </li>
          ))}
        </ul>
      </div>
      {d.alternatives.map((a: any) => (
        <div key={`${a.component}@${a.plant}`}>
          <div className="label mb-2">Alternatives · {a.component} → {a.plant}</div>
          {!a.accepted.length && !a.rejected.length && <p className="text-[12.5px] text-muted">No approved alternate sources in the graph.</p>}
          <ul className="stagger grid">
            {a.accepted.map((x: any, i: number) => (
              <li key={x.site} className="row" style={{ ['--s' as string]: i }}>
                <Check size={14} className="shrink-0" style={{ color: 'var(--pos)' }} />
                <span className="mono text-[12.5px]">{x.site}</span>
                <span className="text-[12px] text-muted">{usd(x.price_cents)} · {n(x.usable_wk)}/wk</span>
                {x.exposure_warning && <span className="tag ml-auto" style={{ ['--c' as string]: 'var(--warn)' }}>exposed, usable</span>}
              </li>
            ))}
            {a.rejected.map((x: any, i: number) => (
              <li key={x.site} className="row" style={{ ['--s' as string]: a.accepted.length + i }}>
                <X size={14} className="shrink-0 text-accent" />
                <span className="mono text-[12.5px]">{x.site}</span>
                <span className="min-w-0 truncate text-[12px] text-muted">{x.reason.replaceAll('_', ' ')}{x.tainted_paths?.[0] ? ` · ${x.tainted_paths[0].join(' → ')}` : ''}</span>
                <span className="num ml-auto shrink-0 text-[12px] text-muted">{usd(x.price_cents)}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}

function Simulate() {
  const sim = useStore((s) => s.derived.sim)
  if (!sim) return <Waiting what="the sandbox comparison" />
  const rows: any[] = sim.strategies
  const best = rows.find((r) => r.strategy === sim.recommended)
  const cells: [string, (r: any) => string][] = [
    ['On time', (r) => `${n(r.on_time)}/${n(r.orders)}`],
    ['Penalty', (r) => usd(r.penalty_cents)],
    ['Spend', (r) => usd(r.spend_cents)],
    ['Days late', (r) => n(r.days_late)],
  ]
  return (
    <div className="grid gap-4">
      <ul className="stagger grid gap-2">
        {rows.map((r, i) => {
          const missing = r.protected_but_late.length > 0
          const star = r.strategy === sim.recommended
          return (
            <li key={r.strategy} className={`card px-3.5 py-2.5 shadow-none ${missing ? 'missing' : ''} ${star ? 'beam' : ''}`} style={{ ['--s' as string]: i }}>
              <div className="flex items-baseline gap-2">
                <span className="num text-[11.5px] text-accent">{r.strategy}{star ? ' ★' : ''}</span>
                <span className="text-[13.5px] font-medium">{r.name}</span>
                <span className={`ml-auto text-[11.5px] ${r.verification.ok ? 'text-muted' : 'text-accent'}`}>
                  {r.verification.ok ? 'invariants pass' : `fails ${r.verification.failed.join(', ')}`}
                </span>
              </div>
              <dl className="mt-1.5 grid grid-cols-4 gap-2">
                {cells.map(([label, f]) => (
                  <div key={label} className="min-w-0">
                    <dt className="truncate text-[10.5px] text-muted">{label}</dt>
                    <dd className="num truncate text-[13px]">{f(r)}</dd>
                  </div>
                ))}
              </dl>
              {missing && (
                <p className="mt-1.5 text-[11.5px] text-accent">
                  Promised {n(r.protected_projected)} orders, {n(r.protected_but_late.length)} still late · planned {n(r.planned_rate_wk)}/wk, realized {n(r.realized_rate_wk)}/wk
                </p>
              )}
            </li>
          )
        })}
      </ul>
      {best && (
        <p className="text-[13px] leading-[1.6] text-ink-2">
          <b className="font-medium text-ink">Net benefit ({best.strategy}):</b> spend {usd(best.spend_cents)} to avoid {usd(best.avoided_penalty_cents)} in late penalties
          and protect {usd(best.revenue_protected_cents)} of revenue, net <b className="num font-medium text-ink">{usd(best.net_benefit_cents)}</b>.
        </p>
      )}
      {rows.find((r) => r.strategy === 'S1' && r.protected_but_late.length) && (
        <p className="text-[12.5px] leading-[1.55] text-muted">
          The hatched column promised orders its suppliers cannot deliver once upstream cells are shared. The naive tool never sees that its cheapest source runs on the flooded fab.
        </p>
      )}
    </div>
  )
}

function Approve() {
  const st = useStore()
  const [feedback, setFeedback] = useState('')
  const plan = st.derived.plan
  if (!plan) return <Waiting what="a plan to approve" />
  const simRow = st.derived.sim?.strategies?.find((r: any) => r.strategy === plan.strategy)
  const waiting = st.runStatus === 'awaiting_approval' || st.runStatus === 'approving'
  return (
    <div className="grid gap-4">
      <div>
        <div className="kv"><span>Decision</span><b className="mono">{plan.decision_id}</b></div>
        <div className="kv"><span>Plan hash · world</span><b className="mono">{plan.plan_hash} · v{plan.world_version ?? '–'}</b></div>
        <div className="kv"><span>Spend</span><b>{usd(plan.spend_cents)}</b></div>
        <div className="kv"><span>Orders protected (projected)</span><b>{n(plan.protected_orders?.length)}</b></div>
        <div className="kv"><span>Sandbox invariants</span><b className={simRow && !simRow.verification.ok ? 'bad' : ''}>{simRow ? (simRow.verification.ok ? 'all 9 pass' : simRow.verification.failed.join(', ')) : '—'}</b></div>
      </div>
      <div>
        <div className="label mb-2">Purchase orders</div>
        <ul className="stagger grid">
          {(plan.pos ?? []).map((p: any, i: number) => (
            <li key={p.id} className="row" style={{ ['--s' as string]: i }}>
              <span className="mono min-w-0 flex-1 truncate text-[12px]">{p.site_id} · {p.component_id} → {p.plant_id}</span>
              <span className="num shrink-0 text-[12px] text-muted">{n(p.rate_wk)}/wk × {n(p.qty)} · {p.mode} · day {p.first_arrival_day}</span>
            </li>
          ))}
        </ul>
      </div>
      {waiting ? (
        <div className="grid gap-2.5">
          <div className="flex gap-2">
            <Btn variant="accent" shine arrow className="flex-1" disabled={st.runStatus === 'approving'} onClick={() => void st.approve()}>
              {st.runStatus === 'approving' ? 'Executing' : 'Approve plan'}
            </Btn>
            <Btn variant="ghost" disabled={st.runStatus === 'approving'} onClick={() => void st.reject(feedback || 'Rejected from the war room')}>
              Reject
            </Btn>
          </div>
          <input
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Feedback for the agent if you reject (optional)"
            className="h-9 rounded-full border border-line bg-bg px-4 text-[13px] placeholder:text-muted focus-visible:outline-2 focus-visible:outline-accent"
          />
        </div>
      ) : st.derived.receipt ? (
        <p className="text-[13px] text-ink-2">
          <Check size={14} className="mr-1 inline" style={{ color: 'var(--pos)' }} />
          Approved and executed: <span className="mono">{st.derived.receipt.summary}</span>
        </p>
      ) : null}
    </div>
  )
}

function Verify() {
  const d = useStore((s) => s.derived)
  const t = useStore((s) => s.summary?.totals)
  if (!d.verify) return <Waiting what="verification" />
  return (
    <div className="grid gap-5">
      <ul className="stagger grid">
        {d.verify.checks.map((c: any, i: number) => (
          <li key={c.id} className="row" style={{ ['--s' as string]: i }}>
            <span className="pop grid size-5 shrink-0 place-items-center rounded-full" style={{ background: c.ok ? 'var(--pos)' : 'var(--accent)', animationDelay: `${i * 70 + 200}ms` }}>
              {c.ok ? <Check size={12} color="#fff" /> : <X size={12} color="#fff" />}
            </span>
            <span className="mono w-7 text-[12px] text-muted">{c.id}</span>
            <span className="text-[13px]">{c.name}</span>
          </li>
        ))}
      </ul>
      <div>
        <div className="kv"><span>Graph receipt</span><b className="mono">{d.receipt?.summary ?? '—'}</b></div>
        <div className="kv"><span>After execution</span><b>{t ? `${n(t.orders - t.projected_late)}/${n(t.orders)} on time` : '—'}</b></div>
      </div>
      {d.report && (
        <div className="card p-4 shadow-none">
          <div className="num text-[11px] text-accent">{d.report.outcome}</div>
          <p className="mt-1 text-[14px] leading-[1.5]">{d.report.headline}</p>
          <ul className="mt-2 grid gap-1">
            {d.report.claims?.map((c: any, i: number) => (
              <li key={i} className="text-[12.5px] leading-[1.5] text-muted">
                <span className="text-ink-2">{c.text}</span> {c.evidence_ids?.length ? <span className="mono text-accent">[{c.evidence_ids.join(', ')}]</span> : null}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function Log() {
  const steps = useStore((s) => s.steps)
  if (!steps.length) return <p className="text-[13px] text-muted">Every tool call appears here as it happens.</p>
  return (
    <ol className="grid">
      {steps.map((s) => (
        <li key={`${s.step}-${s.tool}`} className="row">
          {s.state === 'running' ? <Loader2 size={13} className="shrink-0 animate-spin text-accent" /> : s.state === 'ok' ? <Check size={13} className="shrink-0" style={{ color: 'var(--pos)' }} /> : <X size={13} className="shrink-0 text-accent" />}
          <span className="mono text-[12px]">{s.tool}</span>
          {s.ref && <span className="mono text-[11px] text-accent">{s.ref}</span>}
          <span className="num ml-auto text-[11.5px] text-muted">{s.ms != null ? `${s.ms} ms` : ''}</span>
        </li>
      ))}
    </ol>
  )
}

function Waiting({ what }: { what: string }) {
  return <p className="shimmer text-[13.5px]">Waiting for {what}…</p>
}
