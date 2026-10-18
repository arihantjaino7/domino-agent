import type { Memory, Places, Recording, ReplayMeta, Scenario, Summary, WorldGraph } from './types'

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'content-type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body)
    } catch {
      /* keep statusText */
    }
    throw new Error(`${res.status}: ${detail}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  graph: () => req<WorldGraph>('/api/graph'),
  summary: () => req<Summary>('/api/world/summary'),
  scenarios: () => req<{ scenarios: Scenario[]; claude_api?: boolean }>('/api/scenarios'),
  places: () => req<Places>('/api/world/places'),
  replays: () => req<{ replays: ReplayMeta[] }>('/api/replays').then((r) => r.replays),
  replay: (id: string) => req<Recording>(`/api/replays/${encodeURIComponent(id)}`),
  memory: (source: 'real' | 'demo') => req<Memory>(`/api/memory?source=${source}`),
  reset: () => req<{ graph: string }>('/api/world/reset', { method: 'POST' }),
  inject: (body: { entity_ids: string[]; kind: string; title: string; capacity_factor: number; duration_days: number }) =>
    req<{ incident_id: string; site_ids: string[] }>('/api/incidents', { method: 'POST', body: JSON.stringify(body) }),
  watchExternal: () => req<{ run_id: string }>('/api/external/watch', { method: 'POST' }),
  startRun: (body: { scenario: string; dry_run: boolean }) =>
    req<{ run_id: string }>('/api/runs', { method: 'POST', body: JSON.stringify(body) }),
  approve: (runId: string, decisionId: string) =>
    req(`/api/runs/${runId}/approve`, { method: 'POST', body: JSON.stringify({ approver: 'war-room', decision_id: decisionId }) }),
  reject: (runId: string, feedback: string, decisionId?: string | null) =>
    req(`/api/runs/${runId}/reject`, { method: 'POST', body: JSON.stringify({ feedback, decision_id: decisionId ?? undefined }) }),
}
