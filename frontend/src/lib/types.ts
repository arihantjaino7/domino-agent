// Shapes returned by the DOMINO API. Every number shown in the UI comes from one of these.

export type Column = 'tier3' | 'tier2' | 'tier1' | 'plant' | 'product' | 'customer'
export type NodeKind = 'site' | 'plant' | 'product' | 'customer'
export type EdgeKind = 'feeds' | 'supplies' | 'can_supply' | 'builds' | 'demand'

export interface WorldNode {
  id: string
  kind: NodeKind
  column: Column
  label: string
  data: Record<string, unknown>
}
export interface WorldEdge {
  id: string
  source: string
  target: string
  kind: EdgeKind
  data: Record<string, unknown>
}
export interface WorldGraph {
  graph: string
  nodes: WorldNode[]
  edges: WorldEdge[]
}

export interface Totals {
  orders: number
  exposed: number
  exposed_covered: number
  projected_late: number
  late_beyond_horizon: number
  revenue_at_risk_cents: number
  penalty_exposure_cents: number
}
export interface Summary {
  graph: string
  world_version: number
  incidents: { id: string; title: string; kind: string; sites: string[]; expected_end_day: number }[]
  totals: Totals
  plants: { plant: string; orders: number; exposed: number; projected_late: number; stockout_day: number | null }[]
}

export interface Scenario {
  id: string
  title: string
  alert: string
}

export interface RunEvent {
  seq: number
  ts: number
  run_id: string
  type: string
  data: Record<string, any> // eslint-disable-line @typescript-eslint/no-explicit-any
}

export type RunStatus = 'idle' | 'running' | 'awaiting_approval' | 'approving' | 'completed' | 'failed'

/** Status painted on canvas nodes. Priority: disrupted > late > covered (exposed) > protected > none. */
export type NodeStatus = 'disrupted' | 'late' | 'covered' | 'protected' | 'none'

export interface Places {
  zones: { id: string; name: string; hazard: string; regions: string[]; sites: number }[]
  regions: { id: string; name: string; country: string; sites: number }[]
}

export interface MemoryEntity {
  id: string
  name: string
  kind: string | null
  /** false: no node with this id in the current world. That is not the same as safe. */
  in_world: boolean
}

export interface Memory {
  source: 'real' | 'demo'
  graph: string
  incidents: { id: string; incident_id?: string; title: string; learned_on: string; outcome: string; entities: MemoryEntity[] }[]
  lessons: { id: string; text: string; learned_on: string; incident_id: string; evidence: string[]; entities: MemoryEntity[] }[]
  counts: { incidents: number; lessons: number }
  /** supplier reliability learned from how past purchase orders were delivered */
  reliability: LearnedReliability[]
}

export interface LearnedReliability {
  site: string
  name: string
  seeded: number
  learned: number
  deliveries: number
  on_time: number
  learned_on: string
  evidence: { po_id: string; days_late: number; learned_on: string; run_id: string }[]
  text: string
}

export interface ReplayMeta {
  id: string
  title: string
  scenario: string
  agent: string
  /** true when a real model chose the tools (Claude Code over MCP, or the Claude API) */
  real_model: boolean
  recorded_utc: string
  note?: string | null
  tool_calls: number
  events: number
}

/** A recorded run: its events, plus the world view (graph and summary) at the moments the live war room refreshed. */
export interface Recording extends Omit<ReplayMeta, 'events'> {
  frames: { after_seq: number; graph: WorldGraph; summary: Summary }[]
  events: RunEvent[]
}

export interface LiveAlertPlace { id: string; name: string; kind: 'Site' | 'Plant' | 'Port' | 'Region'; tier: number | null; distance_km: number }
export interface LiveAlert {
  id: string
  event_type: string
  type_label: string
  title: string
  country: string
  alert_level: string
  lat: number
  lng: number
  starts_at: string | null
  ends_at: string | null
  updated_at: string | null
  radius_km: number
  places: LiveAlertPlace[]
  sites: LiveAlertPlace[]
  site_ids: string[]
  in_graph: boolean
  alert_text: string
}
export interface LiveAlertsResponse { events: LiveAlert[]; source: 'gdacs'; updated_at: string | null; error?: string }
