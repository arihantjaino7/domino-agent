import { Check, Loader2, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { stepLine } from '../lib/format'
import { useStore } from '../lib/store'

/** The agent's run, step by step, as it streams in over SSE. */
export function Timeline() {
  const steps = useStore((s) => s.steps)
  const status = useStore((s) => s.runStatus)
  const notes = useStore((s) => s.notes)
  const pending = useStore((s) => s.pendingDecision)
  const approve = useStore((s) => s.approve)
  const reject = useStore((s) => s.reject)
  const events = useStore((s) => s.events)
  const [feedback, setFeedback] = useState('')
  const end = useRef<HTMLDivElement>(null)

  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end', behavior: 'smooth' })
  }, [steps.length, status])

  const report = [...events].reverse().find((e) => e.type === 'run.completed')?.data.report
  const failure = events.find((e) => e.type === 'run.error')?.data.error

  return (
    <aside className="flex min-h-0 flex-col border-l border-line bg-panel">
      <div className="flex h-10 items-center justify-between border-b border-line-soft px-4">
        <span className="text-[13px] font-medium">Agent run</span>
        <RunBadge />
      </div>
      <ol className="min-h-0 flex-1 overflow-y-auto px-2 py-2" aria-live="polite">
        {steps.length === 0 && (
          <li className="px-2 py-6 text-[13px] leading-[1.5] text-dim">
            Every tool call the agent makes appears here as it happens: which tool, what it found, and how long it took.
          </li>
        )}
        {steps.map((s, i) => {
          const prev = steps[i - 1]
          return (
            <li key={`${s.step}-${s.tool}`}>
              {(!prev || prev.phase !== s.phase) && (
                <div className="px-2 pb-1 pt-3 text-[10.5px] font-medium tracking-[0.06em] text-faint">{s.phase}</div>
              )}
              <div className="rounded-md px-2 py-1.5 hover:bg-raised">
                <div className="flex items-center gap-2">
                  {s.state === 'running' && <Loader2 size={13} className="shrink-0 animate-spin text-accent" />}
                  {s.state === 'ok' && <Check size={13} className="shrink-0 text-protected" />}
                  {s.state === 'error' && <X size={13} className="shrink-0 text-late" />}
                  <span className="num truncate text-[12.5px] text-fg">{s.tool}</span>
                  {s.ref && <span className="num text-[11px] text-accent">{s.ref}</span>}
                  {s.ms != null && <span className="num ml-auto shrink-0 text-[11px] text-faint">{s.ms} ms</span>}
                </div>
                {s.state !== 'running' && (
                  <p className="mt-0.5 pl-[21px] text-[12px] leading-[1.45] text-dim">
                    {s.state === 'error' ? (s.summary ?? '').slice(0, 220) : stepLine(s.tool, s.ui)}
                  </p>
                )}
              </div>
            </li>
          )
        })}
        {notes.length > 0 && status === 'completed' && (
          <li className="px-2 pt-3 text-[12px] leading-[1.5] text-dim">{notes[notes.length - 1]}</li>
        )}
        {report && (
          <li className="mx-2 mt-3 rounded-md border border-line-soft px-3 py-2.5">
            <div className="num text-[11px] text-accent">{report.outcome}</div>
            <p className="mt-1 text-[13px] leading-[1.45]">{report.headline}</p>
          </li>
        )}
        {failure && <li className="mx-2 mt-3 text-[12.5px] text-late">Run stopped: {failure}</li>}
        <div ref={end} />
      </ol>
      {(status === 'awaiting_approval' || status === 'approving') && pending && (
        <div className="border-t border-line p-3">
          <p className="text-[12.5px] leading-[1.45] text-dim">
            Purchase commitments need a human. Decision <span className="num text-fg">{pending}</span> waits for you.
          </p>
          <div className="mt-2.5 flex gap-2">
            <button
              type="button"
              onClick={() => void approve()}
              disabled={status === 'approving'}
              className="h-8 flex-1 rounded-md bg-accent text-[13px] font-medium text-accent-ink transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-60"
            >
              {status === 'approving' ? 'Executing…' : 'Approve plan'}
            </button>
            <button
              type="button"
              onClick={() => void reject(feedback || 'Rejected from the war room')}
              disabled={status === 'approving'}
              className="h-8 rounded-md border border-line px-3 text-[13px] text-dim hover:bg-raised hover:text-fg focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-60"
            >
              Reject
            </button>
          </div>
          <input
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Feedback for the agent if you reject (optional)"
            className="mt-2 h-8 w-full rounded-md border border-line bg-raised px-2.5 text-[12.5px] text-fg placeholder:text-faint focus-visible:outline-2 focus-visible:outline-accent"
          />
        </div>
      )}
    </aside>
  )
}

function RunBadge() {
  const status = useStore((s) => s.runStatus)
  const map: Record<string, [string, string]> = {
    idle: ['Idle', 'text-faint'],
    running: ['Working', 'text-accent'],
    awaiting_approval: ['Awaiting approval', 'text-covered'],
    approving: ['Executing', 'text-accent'],
    completed: ['Completed', 'text-protected'],
    failed: ['Failed', 'text-late'],
  }
  const [label, tone] = map[status] ?? map.idle
  return <span className={`text-[12px] ${tone}`}>{label}</span>
}
