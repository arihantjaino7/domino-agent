// Risk X-ray: shapes returned by GET /api/xray. Every number shown comes from the scan engine.

export interface XrayPath { path: string[]; tier1: string; plant: string; component: string; active: boolean }
export interface XrayCapacity { component: string; plant: string; healthy_wk: number; during_outage_wk: number; drop_wk: number; bottleneck: string[] }
export interface XraySite {
  rank: number
  site: string
  name: string
  tier: number
  kind: string
  status: string
  operator: string | null
  region_name: string | null
  country: string | null
  direct_contract: boolean
  hidden: boolean
  operator_has_contract: boolean
  single_point_of_failure: boolean
  orders_exposed: number
  orders_late: number
  late_order_ids: string[]
  strategic_late: number
  penalty_cents: number
  revenue_at_risk_cents: number
  tier1_hit: string[]
  plants_hit: string[]
  parts_hit: { plant: string; component: string; stockout_day: number | null; unmet_units_at_horizon: number }[]
  first_stockout_day: number | null
  dependents: { tier1_active: string[]; tier1_backup: string[]; plants: string[] }
  paths: XrayPath[]
  confirmed: { method: string; matches_fast_pass: boolean; capacity: XrayCapacity[]; ms: number } | null
}
export interface Xray {
  graph: string
  world_version: number
  duration_days: number
  horizon: number
  scope: string
  baseline: { orders: number; exposed: number; projected_late: number; penalty_exposure_cents: number }
  scanned: number
  projected: number
  single_points_of_failure: number
  hidden_single_points_of_failure: number
  confirmed: string[]
  sites: XraySite[]
  timing_ms: { total: number }
  cached: boolean
}

export async function fetchXray(): Promise<Xray> {
  const res = await fetch('/api/xray')
  if (!res.ok) throw new Error(`${res.status}: ${res.statusText}`)
  return res.json() as Promise<Xray>
}
