import type { RunEvent } from './types'

// sse-starlette sends `event: <type>`, so each type needs its own listener.
const TYPES = [
  'run.started', 'agent.note', 'tool.called', 'tool.result', 'plan.proposed', 'approval.required',
  'approval.failed', 'plan.rejected', 'action.executed', 'run.completed', 'run.error',
]

/** Subscribe to a run's events. EventSource resends Last-Event-ID on reconnect, so nothing is lost. */
export function subscribe(runId: string, onEvent: (ev: RunEvent) => void): () => void {
  const es = new EventSource(`/api/runs/${runId}/events`)
  const seen = new Set<number>()
  const handler = (msg: MessageEvent) => {
    const ev = JSON.parse(msg.data) as RunEvent
    if (seen.has(ev.seq)) return
    seen.add(ev.seq)
    onEvent(ev)
    if (ev.type === 'run.completed' || ev.type === 'run.error') es.close()
  }
  for (const t of TYPES) es.addEventListener(t, handler as EventListener)
  return () => es.close()
}
