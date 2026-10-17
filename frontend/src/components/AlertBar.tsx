import { AlertTriangle, Play } from 'lucide-react'
import { useStore } from '../lib/store'

/** Bottom ticker: the incoming alert, which scenario, which model, and the button that starts the agent. */
export function AlertBar() {
  const scenarios = useStore((s) => s.scenarios)
  const scenario = useStore((s) => s.scenario)
  const setScenario = useStore((s) => s.setScenario)
  const dryRun = useStore((s) => s.dryRun)
  const setDryRun = useStore((s) => s.setDryRun)
  const run = useStore((s) => s.run)
  const status = useStore((s) => s.runStatus)
  const busy = useStore((s) => s.busy)
  const alert = scenarios.find((s) => s.id === scenario)
  const working = status === 'running' || status === 'approving' || busy

  return (
    <footer className="flex h-14 items-center gap-4 border-t border-line bg-panel px-4">
      <AlertTriangle size={16} strokeWidth={1.75} className="shrink-0 text-covered" aria-hidden />
      <p className="min-w-0 flex-1 truncate text-[13px]">
        <span className="text-dim">Alert (synthetic): </span>
        {alert?.alert ?? '…'}
      </p>
      <label className="flex shrink-0 items-center gap-2 text-[12.5px] text-dim">
        Scenario
        <select
          value={scenario}
          onChange={(e) => setScenario(e.target.value)}
          disabled={working}
          className="h-8 max-w-56 rounded-md border border-line bg-raised px-2 text-[13px] text-fg focus-visible:outline-2 focus-visible:outline-accent"
        >
          {scenarios.map((s) => (
            <option key={s.id} value={s.id}>
              {s.title}
            </option>
          ))}
        </select>
      </label>
      <div role="radiogroup" aria-label="Model" className="flex h-8 shrink-0 rounded-md border border-line p-0.5 text-[12.5px]">
        {[
          [true, 'Scripted, free'],
          [false, 'Claude, live'],
        ].map(([value, label]) => (
          <button
            key={String(value)}
            type="button"
            role="radio"
            aria-checked={dryRun === value}
            disabled={working}
            onClick={() => setDryRun(value as boolean)}
            className={`rounded px-2.5 transition-colors ${dryRun === value ? 'bg-raised text-fg' : 'text-dim hover:text-fg'}`}
          >
            {label as string}
          </button>
        ))}
      </div>
      <button
        type="button"
        onClick={() => void run()}
        disabled={working}
        className="flex h-8 shrink-0 items-center gap-1.5 rounded-md bg-accent px-3.5 text-[13px] font-medium text-accent-ink transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-60"
      >
        <Play size={13} strokeWidth={2} />
        {working ? 'Running…' : 'Run DOMINO'}
      </button>
    </footer>
  )
}
