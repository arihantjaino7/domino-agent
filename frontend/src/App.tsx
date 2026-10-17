import { useEffect } from 'react'
import { AlertBar } from './components/AlertBar'
import { Cascade } from './components/Cascade'
import { GraphCanvas, Legend } from './components/GraphCanvas'
import { KpiStrip } from './components/KpiStrip'
import { Timeline } from './components/Timeline'
import { TopBar } from './components/TopBar'
import { useStore } from './lib/store'

/** The war room: one screen (PLAN §11.1). */
export default function App() {
  const load = useStore((s) => s.load)
  const error = useStore((s) => s.error)
  useEffect(() => {
    void load()
  }, [load])

  return (
    <div className="grid h-full grid-cols-[minmax(0,1fr)] grid-rows-[auto_auto_minmax(0,1fr)_auto]">
      <TopBar />
      <KpiStrip />
      <main className="grid min-h-0 grid-cols-[minmax(0,1fr)_400px]">
        <section className="flex min-h-0 min-w-0 flex-col">
          <div className="flex min-h-11 items-center border-b border-line-soft px-4 py-2">
            <Cascade />
          </div>
          <div className="relative min-h-0 flex-1">
            <GraphCanvas />
            {error && (
              <div role="alert" className="absolute left-4 top-4 max-w-md rounded-md border border-late/50 bg-panel px-3 py-2 text-[12.5px] text-late">
                {error}
              </div>
            )}
          </div>
          <div className="flex h-10 items-center border-t border-line-soft px-4">
            <Legend />
          </div>
        </section>
        <Timeline />
      </main>
      <AlertBar />
    </div>
  )
}
