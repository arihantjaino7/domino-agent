import { create } from 'zustand'
import { api } from './api'
import { subscribe } from './sse'
import type { NodeStatus, Places, RunEvent, RunStatus, Scenario, Summary, WorldGraph } from './types'

/* eslint-disable @typescript-eslint/no-explicit-any */

export type Phase = 'DETECT' | 'INVESTIGATE' | 'RECOVER' | 'SIMULATE' | 'ACT' | 'VERIFY'

export const PHASE_OF: Record<string, Phase> = {
  resolve_entities: 'DETECT', declare_incident: 'DETECT',
  get_entity_context: 'INVESTIGATE', recall_history: 'INVESTIGATE', trace_exposure: 'INVESTIGATE',
  explain_shared_dependencies: 'INVESTIGATE', project_shortages: 'INVESTIGATE', compute_true_capacity: 'INVESTIGATE',
  find_alternatives: 'RECOVER', simulate_strategies: 'SIMULATE',
  flag_orders_at_risk: 'ACT', submit_plan_for_approval: 'ACT',
  verify_execution: 'VERIFY', record_lessons: 'VERIFY', submit_incident_report: 'VERIFY',
}

export interface Step {
  step: number
  tool: string
  phase: Phase
  args: Record<string, unknown>
  state: 'running' | 'ok' | 'error'
  ref?: string | null
  ms?: number
  summary?: string
  ui?: any
}

export interface Capacity { component: string; plant: string; naive: number; trueWk: number }

/** Everything the canvas paints is derived from engine output carried by run events or the summary. */
export interface Derived {
  status: Record<string, NodeStatus>
  hop: Record<string, number>
  evidence: Record<string, string[]>
  hotEdges: Record<string, NodeStatus>
  tier1View: number | null
  exposedTier1: string[]
  origins: string[]
  components: string[]
  products: string[]
  plants: string[]
  exposedOrders: number | null
  lateOrders: number | null
  customersHit: number | null
  capacity: Capacity[]
  spendCents: number | null
}

interface State {
  graph: WorldGraph | null
  summary: Summary | null
  scenarios: Scenario[]
  places: Places | null
  scenario: string
  dryRun: boolean
  runId: string | null
  runStatus: RunStatus
  events: RunEvent[]
  steps: Step[]
  notes: string[]
  pendingDecision: string | null
  error: string | null
  busy: boolean
  derived: Derived
  load: () => Promise<void>
  refresh: () => Promise<void>
  setScenario: (s: string) => void
  setDryRun: (b: boolean) => void
  run: () => Promise<void>
  approve: () => Promise<void>
  reject: (feedback: string) => Promise<void>
  reset: () => Promise<void>
  inject: (entityId: string, label: string) => Promise<void>
}

const EMPTY: Derived = {
  status: {}, hop: {}, evidence: {}, hotEdges: {}, tier1View: null, exposedTier1: [], origins: [], components: [],
  products: [], plants: [], exposedOrders: null, lateOrders: null, customersHit: null, capacity: [], spendCents: null,
}

const RANK: Record<NodeStatus, number> = { none: 0, protected: 1, covered: 2, late: 3, disrupted: 4 }
function mark(map: Record<string, NodeStatus>, id: string, s: NodeStatus) {
  if (RANK[s] > RANK[map[id] ?? 'none']) map[id] = s
}

export function derive(graph: WorldGraph | null, summary: Summary | null, steps: Step[], events: RunEvent[]): Derived {
  const d: Derived = { ...EMPTY, status: {}, hop: {}, evidence: {}, hotEdges: {}, capacity: [] }
  if (!graph) return d
  for (const n of graph.nodes) if (n.kind === 'site' && n.data.status === 'disrupted') mark(d.status, n.id, 'disrupted')
  for (const inc of summary?.incidents ?? []) for (const s of inc.sites) mark(d.status, s, 'disrupted')

  const orderInfo = new Map<string, { customer: string; product: string; plant: string; status: string }>()
  const trace = [...steps].reverse().find((s) => s.tool === 'trace_exposure' && s.ui)?.ui
  if (trace) {
    d.tier1View = trace.tier1_view?.directly_affected_tier1 ?? null
    d.exposedTier1 = (trace.multi_tier?.tier1_sites ?? []).map((t: any) => t.site)
    d.exposedOrders = trace.multi_tier?.exposed_orders ?? null
    d.hop = trace.hop_depth ?? {}
    const origins = new Set<string>(), comps = new Set<string>(), prods = new Set<string>(), plants = new Set<string>()
    for (const ev of trace.evidence ?? []) {
      d.evidence[ev.id] = ev.path
      origins.add(ev.origin); comps.add(ev.component); prods.add(ev.product); plants.add(ev.plant)
      for (const id of ev.path) if (d.status[id] !== 'disrupted') mark(d.status, id, 'covered')
      mark(d.status, ev.product, 'covered')
      for (let i = 0; i + 1 < ev.path.length; i++) {
        const [a, b] = [ev.path[i], ev.path[i + 1]]
        for (const e of graph.edges) {
          if (e.source === a && e.target === b) mark(d.hotEdges, e.id, 'covered')
        }
      }
      for (const e of graph.edges) if (e.kind === 'builds' && e.source === ev.plant && e.target === ev.product) mark(d.hotEdges, e.id, 'covered')
    }
    d.origins = [...origins]; d.components = [...comps]; d.products = [...prods]; d.plants = [...plants]
  }

  const short = [...steps].reverse().find((s) => s.tool === 'project_shortages' && s.ui)?.ui
  if (short) {
    let late = 0
    const customers = new Set<string>()
    for (const o of short.orders ?? []) {
      orderInfo.set(o.order_id, o)
      if (o.status === 'projected_late') {
        late++
        customers.add(o.customer)
        mark(d.status, o.plant, 'late'); mark(d.status, o.product, 'late'); mark(d.status, o.customer, 'late')
      } else if (o.exposed) {
        customers.add(o.customer)
        mark(d.status, o.customer, 'covered')
      }
    }
    d.lateOrders = late
    d.customersHit = customers.size
    for (const e of graph.edges) {
      if (e.kind === 'demand') {
        const ids = (e.data.order_ids as string[]) ?? []
        const states = ids.map((id) => orderInfo.get(id)?.status)
        if (states.includes('projected_late')) mark(d.hotEdges, e.id, 'late')
        else if (states.includes('exposed_covered')) mark(d.hotEdges, e.id, 'covered')
      }
    }
  }

  for (const s of steps) {
    if (s.tool === 'compute_true_capacity' && s.ui) {
      const key = `${s.ui.component}@${s.ui.plant}`
      d.capacity = d.capacity.filter((c) => `${c.component}@${c.plant}` !== key)
      d.capacity.push({ component: s.ui.component, plant: s.ui.plant, naive: s.ui.naive_wk, trueWk: s.ui.true_wk })
    }
  }
  const proposed = [...events].reverse().find((e) => e.type === 'plan.proposed')
  if (proposed) d.spendCents = proposed.data.spend_cents
  const executed = events.find((e) => e.type === 'action.executed')
  if (executed) {
    for (const oid of executed.data.receipt?.orders_protected ?? []) {
      const o = orderInfo.get(oid)
      if (o) { d.status[o.customer] = d.status[o.customer] === 'late' ? 'protected' : d.status[o.customer] }
    }
  }
  return d
}

function applyEvent(state: State, ev: RunEvent): Partial<State> {
  const events = [...state.events, ev]
  let steps = state.steps
  let { runStatus, pendingDecision, notes } = state
  if (ev.type === 'tool.called') {
    steps = [...steps, { step: ev.data.step, tool: ev.data.tool, phase: PHASE_OF[ev.data.tool] ?? 'INVESTIGATE',
      args: ev.data.args ?? {}, state: 'running' }]
  } else if (ev.type === 'tool.result') {
    const i = steps.map((s) => s.tool === ev.data.tool && s.state === 'running').lastIndexOf(true)
    if (i >= 0) {
      steps = steps.slice()
      steps[i] = { ...steps[i], state: ev.data.is_error ? 'error' : 'ok', ref: ev.data.result_ref, ms: ev.data.duration_ms,
        summary: ev.data.summary, ui: ev.data.ui }
    }
  } else if (ev.type === 'approval.required') {
    runStatus = 'awaiting_approval'; pendingDecision = ev.data.decision_id
  } else if (ev.type === 'action.executed' || ev.type === 'plan.rejected') {
    runStatus = 'running'; pendingDecision = null
  } else if (ev.type === 'run.completed') {
    runStatus = 'completed'
  } else if (ev.type === 'run.error') {
    runStatus = 'failed'
  } else if (ev.type === 'agent.note') {
    notes = [...notes, ev.data.text]
  }
  return { events, steps, runStatus, pendingDecision, notes, derived: derive(state.graph, state.summary, steps, events) }
}

let unsubscribe: (() => void) | null = null
const REFRESH_ON = new Set(['declare_incident', 'flag_orders_at_risk'])

export const useStore = create<State>((set, get) => ({
  graph: null, summary: null, scenarios: [], places: null, scenario: 'monsoon', dryRun: true,
  runId: null, runStatus: 'idle', events: [], steps: [], notes: [], pendingDecision: null, error: null, busy: false,
  derived: EMPTY,

  load: async () => {
    try {
      const [graph, summary, scenarios, places] = await Promise.all([api.graph(), api.summary(), api.scenarios(), api.places()])
      set({ graph, summary, scenarios, places, error: null, derived: derive(graph, summary, get().steps, get().events) })
    } catch (e) {
      set({ error: `Could not load the world. ${String((e as Error).message ?? e)}` })
    }
  },
  refresh: async () => {
    const [graph, summary] = await Promise.all([api.graph(), api.summary()])
    set({ graph, summary, derived: derive(graph, summary, get().steps, get().events) })
  },
  setScenario: (scenario) => set({ scenario }),
  setDryRun: (dryRun) => set({ dryRun }),

  run: async () => {
    unsubscribe?.()
    set({ busy: true, error: null, events: [], steps: [], notes: [], pendingDecision: null, runStatus: 'running' })
    try {
      await api.reset()
      await get().refresh()
      const { run_id } = await api.startRun({ scenario: get().scenario, dry_run: get().dryRun })
      set({ runId: run_id, busy: false })
      unsubscribe = subscribe(run_id, (ev) => {
        set((s) => applyEvent(s, ev))
        if (ev.type === 'tool.result' && (REFRESH_ON.has(ev.data.tool) || ev.data.tool === 'verify_execution')) void get().refresh()
        if (ev.type === 'action.executed' || ev.type === 'run.completed') void get().refresh()
      })
    } catch (e) {
      set({ busy: false, runStatus: 'failed', error: String((e as Error).message ?? e) })
    }
  },
  approve: async () => {
    const { runId, pendingDecision } = get()
    if (!runId || !pendingDecision) return
    set({ runStatus: 'approving' })
    try { await api.approve(runId, pendingDecision) } catch (e) { set({ error: String((e as Error).message ?? e), runStatus: 'awaiting_approval' }) }
  },
  reject: async (feedback) => {
    const { runId } = get()
    if (!runId) return
    try { await api.reject(runId, feedback) } catch (e) { set({ error: String((e as Error).message ?? e) }) }
  },
  reset: async () => {
    unsubscribe?.()
    set({ busy: true, runId: null, runStatus: 'idle', events: [], steps: [], notes: [], pendingDecision: null })
    try { await api.reset(); await get().refresh() } finally { set({ busy: false }) }
  },
  inject: async (entityId, label) => {
    set({ busy: true, error: null })
    try {
      await api.inject({ entity_ids: [entityId], kind: 'disruption', title: `Manual: ${label}`, capacity_factor: 0, duration_days: 21 })
      await get().refresh()
    } catch (e) {
      set({ error: String((e as Error).message ?? e) })
    } finally { set({ busy: false }) }
  },
}))
