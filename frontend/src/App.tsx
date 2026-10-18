import { useEffect, useState } from 'react'
import { AgentView } from './components/AgentView'
import { ChainView } from './components/ChainView'
import { FactoriesView } from './components/FactoriesView'
import { OverviewView } from './components/OverviewView'
import { ShipmentsView } from './components/ShipmentsView'
import { useModel } from './lib/model'
import { Toasts } from './lib/motion'
import { useStore, type Mode } from './lib/store'

const VIEWS = [
  ['overview', 'Overview'], ['chain', 'Supply chain'], ['factories', 'Factories'], ['shipments', 'Shipments'], ['agent', 'AI agent'],
] as const
export type ViewId = (typeof VIEWS)[number][0]

const ICON: Record<ViewId, React.ReactNode> = {
  overview: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M12 3 3 8l9 5 9-5-9-5Z" /><path d="m3 13 9 5 9-5" /><path d="m3 17.5 9 4.5 9-4.5" opacity=".5" /></svg>,
  chain: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="5" cy="6" r="2" /><circle cx="5" cy="18" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="19" cy="7" r="2" /><circle cx="19" cy="17" r="2" /><path d="M7 7l3.3 3.6M7 17l3.3-3.6M14 11.3 17 8M14 12.7l3 3.3" /></svg>,
  factories: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M3 20.5V11l5 3v-3l5 3v-3l5 3V4h3v16.5Z" /><path d="M7 17.5h2M12 17.5h2" opacity=".6" /></svg>,
  shipments: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><rect x="2.5" y="7" width="19" height="11" rx="1.5" /><path d="M6.5 7v11M10.5 7v11M14.5 7v11M18 9.5v6" /></svg>,
  agent: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><rect x="3" y="4" width="7" height="6" rx="1.5" /><rect x="14" y="14" width="7" height="6" rx="1.5" /><path d="M10 7h3a3 3 0 0 1 3 3v4" /><path d="M8 20h-1a4 4 0 0 1-4-4v-1" opacity=".5" /></svg>,
}

const viewFromHash = (): ViewId => {
  const h = location.hash.slice(1)
  return (VIEWS.some(([id]) => id === h) ? h : 'overview') as ViewId
}

/** The war room shell: icon rail, top bar with the views and the agent mode, and the five views. */
export default function App() {
  const load = useStore((s) => s.load)
  const error = useStore((s) => s.error)
  const [view, setView] = useState<ViewId>(viewFromHash)
  useEffect(() => {
    document.documentElement.dataset.theme = 'dark'
    void load()
    const on = () => setView(viewFromHash())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [load])
  const go = (v: ViewId) => {
    if (location.hash.slice(1) !== v) history.replaceState(null, '', `#${v}`)
    setView(v)
    window.scrollTo({ top: 0 })
  }
  return (
    <>
      <div className="app">
        <aside className="rail" aria-label="Views">
          <div className="logo" aria-hidden><span /><span /></div>
          <nav className="rail-nav">
            {VIEWS.map(([id, t]) => (
              <button key={id} type="button" className={view === id ? 'on' : ''} title={t} aria-label={t} aria-current={view === id ? 'page' : undefined} onClick={() => go(id)}>{ICON[id]}</button>
            ))}
          </nav>
          <div className="rail-foot"><div className="avatar" title="Approver: war room">WR</div></div>
        </aside>
        <div className="main">
          <TopBar view={view} go={go} />
          <section className="view on" key={view}>
            {error && <div className="banner" role="alert">{error}</div>}
            {view === 'overview' && <OverviewView go={go} />}
            {view === 'chain' && <ChainView />}
            {view === 'factories' && <FactoriesView />}
            {view === 'shipments' && <ShipmentsView />}
            {view === 'agent' && <AgentView />}
          </section>
          <footer className="concept-note">DOMINO: a supply-chain recovery agent on FalkorDB. Every number here comes from a graph engine result or the API.</footer>
        </div>
      </div>
      <nav className="bottom-nav" aria-label="Views">
        {VIEWS.map(([id, t]) => (
          <button key={id} type="button" className={view === id ? 'on' : ''} onClick={() => go(id)}>
            {ICON[id]}
            <span>{t}</span>
          </button>
        ))}
      </nav>
      <Toasts />
    </>
  )
}

function TopBar({ view, go }: { view: ViewId; go: (v: ViewId) => void }) {
  const m = useModel()
  const mode = useStore((s) => s.mode)
  const setMode = useStore((s) => s.setMode)
  const busy = useStore((s) => s.busy)
  const working = m.phase === 'running' || m.phase === 'approving' || busy
  const inc = m.d.declared?.incident_id
  const summaryIncidents = useStore((s) => s.summary?.incidents?.length ?? 0)
  const state =
    m.phase === 'idle' ? (summaryIncidents ? ['covered', 'Earlier disruption in this world'] : ['none', 'No disruption']) : m.phase === 'running' && mode === 'mcp' && m.steps.length === 0 ? ['covered', 'Waiting for Claude Code']
      : m.phase === 'running' ? ['covered', 'DOMINO is working'] : m.phase === 'awaiting' ? ['covered', 'Waiting for your OK']
      : m.phase === 'approving' ? ['covered', 'Placing the orders'] : m.phase === 'failed' ? ['disrupted', 'Run stopped'] : m.executed ? ['protected', 'Plan approved and checked'] : ['protected', 'Run complete']
  const MODES: [Mode, string, string][] = [['scripted', 'Demo', 'Free offline demo run'], ['replay', 'Replay', 'Watch a recorded run: free, and nothing in the graph changes'], ['mcp', 'Claude Code', 'Claude Code drives DOMINO over MCP; you watch here'], ['api', 'Claude API', 'Claude runs in the backend (paid)']]
  return (
    <header className="top">
      <div className="top-left">
        <span className="word">DOMINO</span>
        {inc && (
          <span className="inc-pill">
            <i className="dot st-disrupted pulse" />
            <b className="mono">{inc}</b>
            <span>{m.d.alert ?? ''}</span>
          </span>
        )}
      </div>
      <nav className="tabs" aria-label="Views">
        {VIEWS.map(([id, t]) => (
          <button key={id} type="button" className={view === id ? 'on' : ''} onClick={() => go(id)}>{t}</button>
        ))}
      </nav>
      <div className="top-right">
        <div className="seg" role="group" aria-label="Who runs the agent">
          {MODES.map(([v, t, title]) => (
            <button key={v} type="button" className={mode === v ? 'on' : ''} title={title} disabled={working} onClick={() => setMode(v)}>{t}</button>
          ))}
        </div>
        <span className="run-state">
          <i className={`dot st-${state[0]} ${m.phase === 'awaiting' || m.phase === 'running' ? 'pulse' : ''}`} />
          {mode === 'replay' && m.phase !== 'idle' ? `Replay · ${state[1]}` : state[1]}
        </span>
      </div>
    </header>
  )
}
