import { useEffect, useState } from 'react'
import { DetailPanel } from './components/DetailPanel'
import { GraphCanvas, Legend } from './components/GraphCanvas'
import { Hero } from './components/Hero'
import { Sidebar } from './components/Sidebar'
import { Topbar } from './components/Topbar'
import { Loader, Toasts, Wipe, spotHandlers } from './lib/motion'
import { useStore } from './lib/store'

/** The war room: app shell (journey sidebar + stage), adapted from the Rekora layout. */
export default function App() {
  const load = useStore((s) => s.load)
  const ready = useStore((s) => s.ready)
  const error = useStore((s) => s.error)
  const theme = useStore((s) => s.theme)
  const [shown, setShown] = useState(false)
  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])
  useEffect(() => {
    void load()
  }, [load])

  return (
    <>
      <Loader ready={ready} onOut={() => setShown(true)} />
      <Wipe />
      <Toasts />
      <div className="grid h-full grid-cols-[var(--side)_minmax(0,1fr)]">
        <Sidebar />
        <main className="flex min-h-0 min-w-0 flex-col overflow-hidden">
          <Topbar />
          {shown ? <Hero /> : <div className="h-[262px]" />}
          <div className={`grid min-h-0 flex-1 grid-cols-[minmax(0,1.55fr)_minmax(380px,1fr)] gap-4 px-8 pb-6 pt-4 ${shown ? 'reveal' : 'opacity-0'}`} style={{ ['--d' as string]: '350ms' }}>
            <section className="card spot flex min-h-0 flex-col overflow-hidden" {...spotHandlers()}>
              <header className="flex items-center justify-between gap-3 border-b border-line-2 px-5 py-3">
                <h2 className="text-[17px]">Supply network</h2>
                <span className="text-[12px] text-muted">tier 3 → customers · hover evidence to trace a path</span>
              </header>
              <div className="relative min-h-0 flex-1">
                <GraphCanvas />
                <div className="pointer-events-none absolute bottom-3 left-3 z-10 rounded-full bg-surface/85 p-1 backdrop-blur-sm">
                  <Legend />
                </div>
                {error && (
                  <div role="alert" className="card absolute left-4 top-4 max-w-md px-4 py-2.5 text-[12.5px] text-accent">
                    {error}
                  </div>
                )}
              </div>
            </section>
            <DetailPanel />
          </div>
        </main>
      </div>
    </>
  )
}
