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
