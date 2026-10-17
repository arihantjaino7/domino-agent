import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useModel } from '../lib/model'
import { STEPS, currentStep, useStore } from '../lib/store'
import { useToasts } from '../lib/toasts'

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
  if (st.mode === 'mcp' && st.steps.length === 0) return <span className="progress"><i className="spin" />Waiting for Claude Code</span>
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
      {!compact && st.mode === 'mcp' && <McpGuide />}
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

/** The prompt a person pastes into Claude Code for the chosen scenario. */
function mcpPrompt(alert: string) {
  return `New alert: ${alert} Handle it as DOMINO.`
}

/**
 * Claude Code mode: the war room cannot type into Claude Code, so it shows the exact steps and the
 * alert to paste, with a copy button. The alert text comes from /api/scenarios.
 */
export function McpGuide() {
  const st = useStore()
  const sc = st.scenarios.find((s) => s.id === st.scenario) ?? st.scenarios[0]
  const prompt = sc ? mcpPrompt(sc.alert) : ''
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(prompt)
      useToasts.getState().push('Alert copied. Paste it into Claude Code.')
    } catch {
      useToasts.getState().push('Could not copy. Select the text and copy it by hand.')
    }
  }
  return (
    <div className="mcp-guide">
      <p className="plain">Claude Code is the agent: it reads the alert and chooses DOMINO's tools. This war room shows each step live and asks you before anything is bought. It is free with a Claude subscription; no API key is needed.</p>
      <ol>
        <li>Once: run <code>make agent-workspace</code>. It creates a <code>domino-agent</code> folder next to the repo with the agent's instructions and the MCP connection.</li>
        <li>Open a terminal in that folder and run <code>claude</code>. Allow the <code>domino</code> MCP server when asked.</li>
        <li>Press <b>Watch Claude Code</b> below. The world resets and this page starts watching.</li>
        <li>Pick an alert, copy it and paste it into Claude Code:</li>
      </ol>
      <div className="mcp-pick" role="group" aria-label="Alert to paste">
        {st.scenarios.map((s) => (
          <button key={s.id} type="button" className={st.scenario === s.id ? 'on' : ''} onClick={() => st.setScenario(s.id)}>{s.title}</button>
        ))}
      </div>
      <div className="mcp-prompt">
        <code>{prompt}</code>
        <button type="button" className="btn btn-ghost" onClick={() => void copy()}>Copy</button>
      </div>
      <ol start={5}>
        <li>When Claude Code says the plan is waiting, approve or reject it here, then tell Claude Code you decided.</li>
      </ol>
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
          <p>Every site in the area stops for 21 days, right now, and the views show what follows. Starting a run (Run the demo or Watch Claude Code) resets the world first, so this stop does not carry into a run.</p>
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
