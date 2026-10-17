import { Moon, RotateCcw, Sun, Zap } from 'lucide-react'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { stepSub } from '../lib/headline'
import { STEPS, currentStep, reachedSteps, useStore, type StepId } from '../lib/store'

/** The agent's journey: seven steps, a sliding highlight, and a line that fills as the run progresses. */
export function Sidebar() {
  const st = useStore()
  const cur = currentStep(st)
  const reached = reachedSteps(st.steps, st.runStatus)
  const view: StepId | null = st.selected ?? cur
  const curIdx = STEPS.findIndex((s) => s.id === cur)
  const listRef = useRef<HTMLUListElement>(null)
  const indRef = useRef<HTMLLIElement>(null)

  const moveInd = () => {
    const ind = indRef.current
    const b = listRef.current?.querySelector<HTMLButtonElement>('.step.active')
    if (!ind) return
    if (!b) {
      ind.style.opacity = '0'
      return
    }
    ind.style.opacity = '1'
    ind.style.width = `${b.offsetWidth}px`
    ind.style.height = `${b.offsetHeight}px`
    ind.style.transform = `translate(${b.offsetLeft}px, ${b.offsetTop}px)`
  }
  useLayoutEffect(moveInd)
  useEffect(() => {
    void document.fonts?.ready.then(moveInd)
  }, [])

  const working = st.runStatus === 'running' || st.runStatus === 'approving'
  const incident = st.derived.declared?.incident_id ?? st.summary?.incidents?.[0]?.id

  return (
    <aside className="side">
      <div className="brand">
        <div className="mark" aria-hidden>
          D
        </div>
        <div className="leading-tight">
          <b className="display text-[15px] font-semibold tracking-[-0.02em]">DOMINO</b>
          <div className="text-[12px] text-muted">Kestrel Devices · recovery agent</div>
        </div>
      </div>

      <div className="journey-label">{incident ? `${incident} · ${st.scenarios.find((s) => s.id === st.scenario)?.title ?? ''}` : 'No open incident'}</div>

      <ul ref={listRef} className="steps">
        <li ref={indRef} className="step-ind" aria-hidden />
        {STEPS.map((s, i) => {
          const isReached = reached.has(s.id)
          const passed = curIdx >= 0 && i < curIdx && isReached
          const done = isReached && (i < curIdx || st.runStatus === 'completed')
          const sub = stepSub(s.id, st.derived, st.runStatus)
          const cls = [
            'step',
            view === s.id ? 'active' : '',
            done ? 'done' : '',
            passed ? 'passed' : '',
            !isReached ? 'locked' : '',
            cur === s.id && working ? 'working' : '',
          ].join(' ')
          return (
            <li key={s.id}>
              <button
                type="button"
                className={cls}
                disabled={!isReached}
                aria-current={view === s.id ? 'step' : undefined}
                onClick={() => st.select(cur === s.id ? null : s.id)}
              >
                <span className="sdot">{done && view !== s.id ? '✓' : s.num}</span>
                <span className="min-w-0 text-left">
                  <span className="t">{s.title}</span>
                  <span className="s truncate">{sub ?? (isReached ? 'Working…' : 'Opens as the agent gets here')}</span>
                </span>
              </button>
            </li>
          )
        })}
      </ul>

      <div className="mt-auto grid gap-2.5 pt-4">
        <div className="flex items-center gap-2 px-1.5 text-[12px] text-muted">
          <i className={`live ${working ? '' : st.runStatus === 'awaiting_approval' ? 'warn' : 'idle'}`} />
          <span className="mono">{st.summary?.graph ?? 'world:live'}</span>
          <span className="num">v{st.summary?.world_version ?? '–'}</span>
        </div>
        <div className="flex items-center gap-2">
          <InjectMenu />
          <button type="button" className="icon-btn" title="Reset world from pristine" aria-label="Reset world" disabled={st.busy || working} onClick={() => void st.reset()}>
            <RotateCcw size={14} strokeWidth={1.75} />
          </button>
          <button
            type="button"
            className="icon-btn"
            aria-label={st.theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
            onClick={() => st.setTheme(st.theme === 'dark' ? 'light' : 'dark')}
          >
            {st.theme === 'dark' ? <Sun size={14} strokeWidth={1.75} /> : <Moon size={14} strokeWidth={1.75} />}
          </button>
        </div>
      </div>
    </aside>
  )
}

function InjectMenu() {
  const places = useStore((s) => s.places)
  const inject = useStore((s) => s.inject)
  const busy = useStore((s) => s.busy)
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
    <div ref={ref} className="relative flex-1">
      <button type="button" className="btn btn-ghost w-full" disabled={busy || !places} aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        <Zap size={14} strokeWidth={1.75} />
        Inject disruption
      </button>
      {open && places && (
        <div role="menu" className="card reveal absolute bottom-11 left-0 z-50 w-72 overflow-hidden p-0">
          <p className="border-b border-line-2 px-3.5 py-2.5 text-[12px] leading-[1.45] text-muted">
            Every site in the zone drops to 0% for 21 days. The agent is not involved.
          </p>
          <ul className="max-h-72 overflow-y-auto py-1">
            {places.zones.map((z) => (
              <li key={z.id}>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setOpen(false)
                    void inject(z.id, z.name)
                  }}
                  className="flex w-full items-center justify-between gap-3 px-3.5 py-2 text-left text-[13px] hover:bg-bg"
                >
                  <span className="truncate">
                    {z.name} <span className="text-muted">{z.hazard}</span>
                  </span>
                  <span className="num shrink-0 text-[12px] text-muted">{z.sites} sites</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
