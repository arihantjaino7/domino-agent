import { Play } from 'lucide-react'
import { Btn, Seg } from '../lib/motion'
import { useStore } from '../lib/store'

/** The incoming alert, which scenario and which model, and the one primary action. */
export function Topbar() {
  const scenarios = useStore((s) => s.scenarios)
  const scenario = useStore((s) => s.scenario)
  const setScenario = useStore((s) => s.setScenario)
  const dryRun = useStore((s) => s.dryRun)
  const setDryRun = useStore((s) => s.setDryRun)
  const run = useStore((s) => s.run)
  const status = useStore((s) => s.runStatus)
  const busy = useStore((s) => s.busy)
  const working = status === 'running' || status === 'approving' || busy
  const alert = scenarios.find((s) => s.id === scenario)
  const short: Record<string, string> = { monsoon: 'Monsoon', panel_fire: 'Panel fire', non_event: 'Non-event' }

  return (
    <header className="flex flex-wrap items-center gap-3 border-b border-line px-8 py-3.5">
      <div className="flex min-w-0 flex-1 items-center gap-2.5">
        <span className="tag shrink-0" style={{ ['--c' as string]: 'var(--warn)' }}>
          Alert, synthetic
        </span>
        <p className="truncate text-[13px] text-ink-2" title={alert?.alert}>
          {alert?.alert ?? '…'}
        </p>
      </div>
      <Seg
        label="Scenario"
        value={scenario}
        disabled={working}
        onChange={setScenario}
        options={scenarios.map((s) => ({ value: s.id, label: short[s.id] ?? s.title }))}
      />
      <Seg
        label="Model"
        value={dryRun}
        disabled={working}
        onChange={setDryRun}
        options={[
          { value: true, label: 'Scripted · free' },
          { value: false, label: 'Claude · live' },
        ]}
      />
      <Btn variant="primary" shine arrow icon={<Play size={13} strokeWidth={2} />} disabled={working} onClick={() => void run()}>
        {working ? 'Running' : 'Run DOMINO'}
      </Btn>
    </header>
  )
}
