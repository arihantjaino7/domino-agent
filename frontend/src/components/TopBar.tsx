import { RotateCcw } from 'lucide-react'
import { useStore } from '../lib/store'
import { InjectMenu } from './InjectMenu'

export function TopBar() {
  const summary = useStore((s) => s.summary)
  const busy = useStore((s) => s.busy)
  const reset = useStore((s) => s.reset)
  const incidents = summary?.incidents ?? []
  return (
    <header className="flex h-12 items-center gap-4 border-b border-line bg-panel px-4">
      <div className="flex items-baseline gap-2">
        <span className="text-[15px] font-semibold tracking-[-0.01em]">DOMINO</span>
        <span className="text-[13px] text-dim">Kestrel Devices</span>
      </div>
      <div className="flex items-center gap-3 text-[12px] text-dim">
        <span className="num">Day 0</span>
        <span className="h-3 w-px bg-line" />
        <span className="num">{summary?.graph ?? '…'}</span>
        <span className="num">v{summary?.world_version ?? '–'}</span>
        {incidents.length > 0 && (
          <>
            <span className="h-3 w-px bg-line" />
            <span className="flex items-center gap-1.5 text-fg">
              <span className="size-1.5 rounded-full bg-disrupted" />
              {incidents.map((i) => i.id).join(', ')}
            </span>
          </>
        )}
      </div>
      <div className="ml-auto flex items-center gap-2">
        <InjectMenu />
        <button
          type="button"
          onClick={() => void reset()}
          disabled={busy}
          className="flex h-8 items-center gap-1.5 rounded-md border border-line px-3 text-[13px] text-dim transition-colors hover:bg-raised hover:text-fg focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-50"
        >
          <RotateCcw size={14} strokeWidth={1.75} />
          Reset world
        </button>
      </div>
    </header>
  )
}
