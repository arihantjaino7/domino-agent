import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useModel } from '../lib/model'
import { STEPS, currentStep, useStore } from '../lib/store'

export function Head({ title, text, right }: { title: ReactNode; text: ReactNode; right?: ReactNode }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        <p className="lede">{text}</p>
      </div>
      {right}
    </div>
  )
}

/** Plain-words progress: which of the seven steps the agent is on. */
export function Progress() {
  const st = useStore()
  const cur = currentStep(st)
  const s = STEPS.find((x) => x.id === cur)
  if (st.runStatus !== 'running' && st.runStatus !== 'approving') return null
  return (
    <span className="progress"><i className="spin" />{st.runStatus === 'approving' ? 'Placing the orders and checking them' : s ? `Step ${s.num}: ${s.title}` : 'Starting'}</span>
  )
}

/** Pick a disruption and run DOMINO; reset the world; or inject a disruption by hand. */
export function RunPanel({ compact }: { compact?: boolean }) {
  const st = useStore()
  const m = useModel()
  const working = m.phase === 'running' || m.phase === 'approving' || st.busy
  const short: Record<string, string> = { monsoon: 'Flood', panel_fire: 'Factory fire', non_event: 'Port strike' }
  const runLabel = st.mode === 'mcp' ? 'Watch Claude Code' : st.mode === 'api' ? 'Run with Claude' : st.mode === 'replay' ? 'Play the recording' : 'Run the demo'
  if (st.mode === 'replay') return <ReplayPanel compact={compact} working={working} label={runLabel} />
  return (
    <div>
      {!compact && st.mode !== 'mcp' && (
        <div className="start">
          {st.scenarios.map((s) => (
            <button key={s.id} type="button" className={`scn ${st.scenario === s.id ? 'on' : ''}`} disabled={working} onClick={() => st.setScenario(s.id)}>
              <span className="sub">{short[s.id] ?? 'Scenario'}</span>
              <b>{s.title}</b>
              <span>{s.alert}</span>
            </button>
          ))}
        </div>
      )}
      {!compact && st.mode === 'mcp' && (
        <p className="plain" style={{ marginTop: 14 }}>Claude Code is the agent. Start watching here, then ask Claude Code to handle an alert. Every step it takes appears in this war room.</p>
      )}
      <div className="start-actions">
        {compact && st.mode !== 'mcp' && (
          <select className="pick" aria-label="Disruption to simulate" value={st.scenario} disabled={working} onChange={(e) => st.setScenario(e.target.value)}>
            {st.scenarios.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
          </select>
        )}
        <button type="button" className="btn btn-accent" disabled={working} onClick={() => void st.run()}>{working ? 'Running' : runLabel}</button>
        <InjectMenu disabled={working} />
        <button type="button" className="btn btn-ghost" disabled={working} onClick={() => void st.reset()} title="Undo every disruption and order: back to the starting world">Reset the world</button>
        <Progress />
      </div>
    </div>
  )
}

const when = (iso: string) => {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

/** Replay mode: pick a published recording and play it. Nothing is sent to the graph. */
function ReplayPanel({ compact, working, label }: { compact?: boolean; working: boolean; label: string }) {
  const st = useStore()
  const sel = st.replays.find((r) => r.id === st.replayId) ?? null
  const rec = st.recording
  if (st.replays.length === 0) return <p className="plain">No recordings are published yet.</p>
  return (
    <div>
      {!compact && (
        <div className="start">
          {st.replays.map((r) => (
            <button key={r.id} type="button" className={`scn ${st.replayId === r.id ? 'on' : ''}`} disabled={working} onClick={() => st.setReplay(r.id)}>
              <span className="sub">{r.real_model ? r.agent : `${r.agent}, not a model`}</span>
              <b>{r.title}</b>
              <span>Recorded {when(r.recorded_utc)}. {r.tool_calls} tool calls.{r.note ? ` ${r.note}` : ''}</span>
            </button>
          ))}
        </div>
      )}
      <div className="start-actions">
        {compact && (
          <select className="pick" aria-label="Recording to play" value={st.replayId ?? ''} disabled={working} onChange={(e) => st.setReplay(e.target.value)}>
            {st.replays.map((r) => <option key={r.id} value={r.id}>{r.title} ({r.real_model ? r.agent : 'scripted'})</option>)}
          </select>
        )}
        <button type="button" className="btn btn-accent" disabled={working || !sel} onClick={() => void st.run()}>{working ? 'Playing' : label}</button>
        {rec && !working && <button type="button" className="btn btn-ghost" onClick={() => void st.reset()}>Clear</button>}
        <Progress />
      </div>
      <p className="sub" style={{ marginTop: 10 }}>
        {rec ? `Playing a recording of ${rec.real_model ? `a real ${rec.agent} run` : 'the scripted stand-in'} from ${when(rec.recorded_utc)}. ` : 'A replay plays a recorded run back. '}
        Every number is what the engines returned at the time. Nothing in the graph is changed, and your Approve only continues the recording.
      </p>
    </div>
  )
}

function InjectMenu({ disabled }: { disabled: boolean }) {
  const places = useStore((s) => s.places)
  const inject = useStore((s) => s.inject)
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const close = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false)
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', esc)
    }
  }, [])
  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button type="button" className="btn btn-ghost" disabled={disabled || !places} aria-expanded={open} onClick={() => setOpen((o) => !o)}>Stop a region by hand</button>
      {open && places && (
        <div role="menu" className="menu">
          <p>Every site in the area stops for 21 days, right now. Claude Code (watch mode) sees it on its next run. A demo run starts again from a fresh world.</p>
          {places.zones.map((z) => (
            <button key={z.id} type="button" role="menuitem" onClick={() => { setOpen(false); void inject(z.id, z.name) }}>
              <span>{z.name} <span className="muted">{z.hazard}</span></span>
              <span className="muted num">{z.sites} sites</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
