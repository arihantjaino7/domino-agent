/* The war room's view model: everything the five views read, built ONLY from the store (engine events + API).
   Words that depend on the incident (its kind, what the stopped site makes) come from the run too. */
import { useMemo } from 'react'
import { derive, useStore, type Derived, type Step } from './store'
import type { NodeStatus, RunStatus, WorldGraph } from './types'

/* eslint-disable @typescript-eslint/no-explicit-any */

export interface Site { id: string; label: string; col: string; kind: string; region: string | null; country: string | null; operator: string | null; unit: string | null; siteKind: string | null }
export type OrderState = 'late' | 'covered' | 'protected'

export const COL: Record<NodeStatus, string> = {
  disrupted: 'var(--st-disrupted)', late: 'var(--st-late)', covered: 'var(--st-covered)', protected: 'var(--st-protected)', none: 'var(--st-none)',
}
export const RANK: Record<NodeStatus, number> = { none: 0, protected: 1, covered: 2, late: 3, disrupted: 4 }
export const COUNTRY: Record<string, string> = { TH: 'Thailand', MY: 'Malaysia', VN: 'Vietnam', KR: 'South Korea', JP: 'Japan', MX: 'Mexico', CN: 'China', TW: 'Taiwan', US: 'United States', CZ: 'Czechia' }
// What a site of each kind makes, in plain words (labels only, never numbers).
const MAKES: Record<string, [string, string]> = {
  cell_fab: ['battery cell', 'battery cells'], pack_line: ['battery pack', 'battery packs'], panel_fab: ['display panel', 'display panels'],
  glass_fab: ['glass sheet', 'glass'], smt_line: ['circuit board', 'circuit boards'], module_line: ['module', 'modules'], wafer_fab: ['chip', 'chips'],
  osat: ['chip package', 'chip packages'], laminate: ['laminate sheet', 'laminate'], mill: ['metal sheet', 'metal'], chemical_plant: ['chemical', 'chemicals'],
  machining: ['machined part', 'machined parts'],
}
export const usd = (cents: number | null | undefined) => (cents == null ? '—' : `$${Math.round(cents / 100).toLocaleString('en-US')}`)
export const fmt = (n: number | null | undefined) => (n == null ? '—' : Number(n).toLocaleString('en-US'))
export const cap1 = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s)
/** "1 supplier", "3 suppliers" */
export const plural = (n: number | null | undefined, one: string, many = `${one}s`) => `${fmt(n)} ${n === 1 ? one : many}`

export interface Model {
  ready: boolean
  graph: WorldGraph | null
  N: Record<string, Site>
  name: (id: string) => string
  short: (id: string) => string // "Penang" for a plant, the operator for a site
  status: (id: string) => NodeStatus
  statusBefore: (id: string) => NodeStatus
  d: Derived
  runStatus: RunStatus
  phase: 'idle' | 'running' | 'awaiting' | 'approving' | 'done' | 'failed'
  executed: boolean
  pendingDecision: string | null
  steps: Step[]
  kind: string // "flood", "fire", or "disruption" when the run has not declared one
  site: Site | null // the first stopped site
  input: [string, string] // what the stopped site makes
  part: [string, string] // what our factories are short of
  partOf: (id: string) => [string, string]
  horizon: number
  totals: any | null
  plants: any[]
  orders: any[]
  orderState: (o: any) => OrderState
  protectedSet: Set<string>
  sim: any | null
  rec: any | null // the recommended strategy row
  base: any | null // do-nothing row
  plan: any | null
  suppliersInPlan: string[]
  capFor: (plantId: string) => any | null
  altFor: (po: any) => any | null
  hasIncident: boolean
  noExposure: boolean // ran, but nothing in the graph is affected
}

export function useModel(): Model {
  const st = useStore()
  return useMemo(() => build(st.graph, st.summary, st.derived, st.steps, st.events, st.runStatus, st.pendingDecision, st.ready),
    [st.graph, st.summary, st.derived, st.steps, st.events, st.runStatus, st.pendingDecision, st.ready])
}

function build(graph: WorldGraph | null, summary: any, d: Derived, steps: Step[], events: any[], runStatus: RunStatus, pendingDecision: string | null, ready: boolean): Model {
  const N: Record<string, Site> = {}
  for (const n of graph?.nodes ?? []) {
    const x = n.data as any
    N[n.id] = { id: n.id, label: n.label, col: n.column, kind: n.kind, region: x.region_name ?? null, country: x.country ?? null, operator: x.operator ?? null, unit: x.unit ?? null, siteKind: x.kind ?? null }
  }
  const name = (id: string) => N[id]?.label ?? id
  const short = (id: string) => {
    const n = N[id]
    if (!n) return id
    if (n.kind === 'plant') return n.label.split(' ').slice(1).join(' ') || n.label
    return n.operator ?? n.label
  }
  // statuses before the plan executed, for the before/after toggle
  const before = d.executedSeq != null ? derive(graph, summary, steps, events.filter((e) => e.seq < (d.executedSeq as number))) : d
  const status = (id: string): NodeStatus => d.status[id] ?? 'none'
  const statusBefore = (id: string): NodeStatus => before.status[id] ?? 'none'
  const partOf = (id: string): [string, string] => MAKES[N[id]?.siteKind ?? ''] ?? ['part', 'parts']
  const siteId = d.declared?.site_ids?.[0] ?? null
  const ev0 = d.trace?.evidence?.[0]
  const sh = d.shortage
  const orders = (sh?.orders ?? []).filter((o: any) => o.exposed || o.status !== 'on_time')
  const protectedSet = new Set<string>(d.receipt?.orders_protected ?? [])
  const executed = d.receipt != null
  const orderState = (o: any): OrderState => (executed && protectedSet.has(o.order_id) ? 'protected' : o.status === 'projected_late' ? 'late' : 'covered')
  const sim = d.sim
  const rec = sim?.strategies?.find((s: any) => s.strategy === sim.recommended) ?? null
  const base = sim?.strategies?.find((s: any) => s.strategy === 'S0') ?? null
  const plan = d.plan
  const suppliersInPlan: string[] = [...new Set<string>((plan?.pos ?? []).map((p: any) => p.site_id))]
  const phase: Model['phase'] =
    runStatus === 'idle' ? 'idle' : runStatus === 'awaiting_approval' ? 'awaiting' : runStatus === 'approving' ? 'approving'
      : runStatus === 'completed' ? 'done' : runStatus === 'failed' ? 'failed' : 'running'
  const plantsFromSummary = (summary?.plants ?? []).map((p: any) => ({ ...p }))
  return {
    ready, graph, N, name, short, status, statusBefore, d, runStatus, phase, executed, pendingDecision, steps,
    kind: d.kind ?? 'disruption',
    site: siteId ? N[siteId] ?? null : null,
    input: siteId ? partOf(siteId) : ['part', 'parts'],
    part: ev0 ? partOf(ev0.tier1) : ['part', 'parts'],
    partOf,
    horizon: d.trace?.horizon ?? sh?.horizon ?? 42,
    totals: sh?.totals ?? null,
    plants: sh?.plants ?? plantsFromSummary,
    orders, orderState, protectedSet, sim, rec, base, plan, suppliersInPlan,
    capFor: (plantId: string) => {
      const e = d.trace?.evidence?.find((x: any) => x.plant === plantId)
      return d.capacity.find((c) => c.plant === plantId && (!e || c.component === e.component)) ?? null
    },
    altFor: (po: any) => {
      for (const a of d.alternatives) if (a.component === po.component_id && a.plant === po.plant_id) { const x = a.accepted?.find((c: any) => c.site === po.site_id); if (x) return x }
      return null
    },
    hasIncident: !!d.declared,
    noExposure: runStatus === 'completed' && !(d.trace?.evidence?.length),
  }
}
