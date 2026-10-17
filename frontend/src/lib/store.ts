import { create } from 'zustand'
import { api } from './api'
import { useToasts } from './toasts'
import { subscribe } from './sse'
import type { NodeStatus, Places, RunEvent, RunStatus, Scenario, Summary, WorldGraph } from './types'

/* eslint-disable @typescript-eslint/no-explicit-any */

/* ---------- the agent's journey, as the sidebar shows it ---------- */
export type Mode = 'scripted' | 'mcp' | 'api'
export type StepId = 'detect' | 'trace' | 'impact' | 'options' | 'simulate' | 'approve' | 'verify'
export const STEPS: { id: StepId; num: string; title: string; tools: string[] }[] = [
  { id: 'detect', num: '01', title: 'Detect', tools: ['resolve_entities', 'declare_incident'] },
  { id: 'trace', num: '02', title: 'Trace', tools: ['trace_exposure', 'explain_shared_dependencies', 'get_entity_context', 'recall_history'] },
  { id: 'impact', num: '03', title: 'Impact', tools: ['project_shortages', 'flag_orders_at_risk'] },
  { id: 'options', num: '04', title: 'Options', tools: ['compute_true_capacity', 'find_alternatives'] },
  { id: 'simulate', num: '05', title: 'Simulate', tools: ['simulate_strategies'] },
  { id: 'approve', num: '06', title: 'Approve', tools: ['submit_plan_for_approval', 'get_decision_status'] },
  { id: 'verify', num: '07', title: 'Verify', tools: ['verify_execution', 'record_lessons', 'submit_incident_report'] },
]
export const STEP_OF: Record<string, StepId> = Object.fromEntries(STEPS.flatMap((s) => s.tools.map((t) => [t, s.id])))

export interface Step {
  step: number
  tool: string
  stepId: StepId
  args: Record<string, unknown>
  state: 'running' | 'ok' | 'error'
  ref?: string | null
  ms?: number
  summary?: string
  ui?: any
  queries?: QueryGroup[] | null
  t?: number // seconds since the run started
}

/** One named Cypher query a tool ran (grouped by run_query.group_records), for the Cypher drawer. */
export interface QueryGroup { name: string; cypher: string; params: Record<string, unknown>; ro: boolean; calls: number; rows: number; ms: number; graphs: string[] }

export interface Capacity { component: string; plant: string; naive: number; trueWk: number; healthy: number; bottleneck: any[] }

/** What every panel and the canvas show, derived ONLY from engine output carried by run events or the summary. */
export interface Derived {
  status: Record<string, NodeStatus>
  hop: Record<string, number>
  evidence: { id: string; path: string[]; component: string; product: string; plant: string; orders: number }[]
  hotEdges: Record<string, NodeStatus>
  tier1View: number | null
  exposedTier1: { site: string; via: string[] }[]
  shared: { site: string; operator: string; dependents: string[]; fan_out: number }[]
  origins: string[]
  components: string[]
  products: string[]
  plants: string[]
  exposedOrders: number | null
  lateOrders: number | null
  customersHit: number | null
  capacity: Capacity[]
  alternatives: any[]
  resolve: any | null
  declared: any | null
  shortage: any | null
  sim: any | null
  plan: any | null
  receipt: any | null
  verify: any | null
  report: any | null
  spendCents: number | null
  trace: any | null
  alert: string | null
  kind: string | null
  lessons: { text: string }[]
  memoryGraph: string | null
  executedSeq: number | null
}

interface State {
  graph: WorldGraph | null
  summary: Summary | null
  scenarios: Scenario[]
  places: Places | null
  scenario: string
  mode: Mode
  theme: 'light' | 'dark'
  runId: string | null
  runStatus: RunStatus
  events: RunEvent[]
  steps: Step[]
  pendingDecision: string | null
  selected: StepId | null
  hoverEvidence: string | null
  error: string | null
  busy: boolean
  ready: boolean
  derived: Derived
  load: () => Promise<void>
  refresh: () => Promise<void>
  setScenario: (s: string) => void
  setMode: (m: Mode) => void
  setTheme: (t: 'light' | 'dark') => void
  select: (s: StepId | null) => void
  setHoverEvidence: (id: string | null) => void
  run: () => Promise<void>
  approve: () => Promise<void>
  reject: (feedback: string) => Promise<void>
  reset: () => Promise<void>
  inject: (entityId: string, label: string) => Promise<void>
}

const EMPTY: Derived = {
  status: {}, hop: {}, evidence: [], hotEdges: {}, tier1View: null, exposedTier1: [], shared: [], origins: [],
  components: [], products: [], plants: [], exposedOrders: null, lateOrders: null, customersHit: null, capacity: [],
  alternatives: [], resolve: null, declared: null, shortage: null, sim: null, plan: null, receipt: null, verify: null,
  report: null, spendCents: null, trace: null, alert: null, kind: null, lessons: [], memoryGraph: null, executedSeq: null,
}

const RANK: Record<NodeStatus, number> = { none: 0, protected: 1, covered: 2, late: 3, disrupted: 4 }
function mark(map: Record<string, NodeStatus>, id: string, s: NodeStatus) {
  if (RANK[s] > RANK[map[id] ?? 'none']) map[id] = s
}
const lastUi = (steps: Step[], tool: string) => [...steps].reverse().find((s) => s.tool === tool && s.ui)?.ui ?? null

export function derive(graph: WorldGraph | null, summary: Summary | null, steps: Step[], events: RunEvent[]): Derived {
  const d: Derived = { ...EMPTY, status: {}, hop: {}, hotEdges: {}, evidence: [], capacity: [], alternatives: [] }
  if (!graph) return d
  for (const n of graph.nodes) if (n.kind === 'site' && n.data.status === 'disrupted') mark(d.status, n.id, 'disrupted')
  for (const inc of summary?.incidents ?? []) for (const s of inc.sites) mark(d.status, s, 'disrupted')

  d.resolve = lastUi(steps, 'resolve_entities')
  d.declared = lastUi(steps, 'declare_incident')
  const trace = lastUi(steps, 'trace_exposure')
  d.trace = trace
  d.alert = events.find((e) => e.type === 'run.started')?.data.alert ?? null
  d.kind = (steps.find((s) => s.tool === 'declare_incident')?.args.kind as string | undefined) ?? null
  const rl = [...steps].reverse().find((s) => s.tool === 'record_lessons' && s.state === 'ok')
  d.lessons = ((rl?.args.lessons as { text: string }[] | undefined) ?? []).filter((l) => l?.text)
  d.memoryGraph = rl?.ui?.graph ?? null
  if (trace) {
    d.tier1View = trace.tier1_view?.directly_affected_tier1 ?? null
    d.exposedTier1 = trace.multi_tier?.tier1_sites ?? []
    d.exposedOrders = trace.multi_tier?.exposed_orders ?? null
    d.shared = trace.shared_upstream ?? []
    d.hop = trace.hop_depth ?? {}
    const origins = new Set<string>(), comps = new Set<string>(), prods = new Set<string>(), plants = new Set<string>()
    for (const ev of trace.evidence ?? []) {
      d.evidence.push({ id: ev.id, path: ev.path, component: ev.component, product: ev.product, plant: ev.plant, orders: ev.orders.length })
      origins.add(ev.origin); comps.add(ev.component); prods.add(ev.product); plants.add(ev.plant)
      for (const id of ev.path) mark(d.status, id, 'covered')
      mark(d.status, ev.product, 'covered')
      for (let i = 0; i + 1 < ev.path.length; i++) {
        for (const e of graph.edges) if (e.source === ev.path[i] && e.target === ev.path[i + 1]) mark(d.hotEdges, e.id, 'covered')
      }
      for (const e of graph.edges) if (e.kind === 'builds' && e.source === ev.plant && e.target === ev.product) mark(d.hotEdges, e.id, 'covered')
    }
    d.origins = [...origins]; d.components = [...comps]; d.products = [...prods]; d.plants = [...plants]
  }

  const orderInfo = new Map<string, any>()
  d.shortage = lastUi(steps, 'project_shortages')
  if (d.shortage) {
    let late = 0
    const customers = new Set<string>()
    for (const o of d.shortage.orders ?? []) {
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
      if (e.kind !== 'demand') continue
      const states = ((e.data.order_ids as string[]) ?? []).map((id) => orderInfo.get(id)?.status)
      if (states.includes('projected_late')) mark(d.hotEdges, e.id, 'late')
      else if (states.includes('exposed_covered')) mark(d.hotEdges, e.id, 'covered')
    }
  }

  for (const s of steps) {
    if (s.tool === 'compute_true_capacity' && s.ui) {
      const key = `${s.ui.component}@${s.ui.plant}`
      d.capacity = d.capacity.filter((c) => `${c.component}@${c.plant}` !== key)
      d.capacity.push({ component: s.ui.component, plant: s.ui.plant, naive: s.ui.naive_wk, trueWk: s.ui.true_wk,
        healthy: s.ui.nominal_wk, bottleneck: s.ui.bottleneck ?? [] })
    }
    if (s.tool === 'find_alternatives' && s.ui) {
      d.alternatives = d.alternatives.filter((a) => !(a.component === s.ui.component && a.plant === s.ui.plant))
      d.alternatives.push(s.ui)
    }
  }
  d.sim = lastUi(steps, 'simulate_strategies')
  const proposed = [...events].reverse().find((e) => e.type === 'plan.proposed')
  if (proposed) {
    d.plan = { ...proposed.data, ...(lastUi(steps, 'submit_plan_for_approval')?.plan ?? {}) }
    d.spendCents = proposed.data.spend_cents
  }
  const executed = [...events].reverse().find((e) => e.type === 'action.executed')
  if (executed) {
    d.executedSeq = executed.seq
    d.receipt = executed.data.receipt
    for (const oid of d.receipt?.orders_protected ?? []) {
      const o = orderInfo.get(oid)
      if (o) d.status[o.customer] = 'protected'
    }
    const planEdges = (d.plan?.pos ?? []) as any[]
    for (const po of planEdges) {
      for (const e of graph.edges) {
        if (e.source === po.site_id && e.target === po.plant_id && e.kind === 'can_supply') d.hotEdges[e.id] = 'protected'
      }
      d.status[po.site_id] = d.status[po.site_id] === 'covered' || !d.status[po.site_id] ? 'protected' : d.status[po.site_id]
    }
  }
  d.verify = lastUi(steps, 'verify_execution')
  d.report = [...events].reverse().find((e) => e.type === 'run.completed')?.data.report ?? lastUi(steps, 'submit_incident_report')?.report ?? null
  return d
}

/** The step the agent is on right now. */
export function currentStep(st: Pick<State, 'steps' | 'runStatus' | 'events'>): StepId | null {
  if (st.runStatus === 'awaiting_approval' || st.runStatus === 'approving') return 'approve'
  const last = st.steps[st.steps.length - 1]
  if (!last) return st.events.some((e) => e.type === 'run.started') ? 'detect' : null
  return last.stepId
}
export function reachedSteps(steps: Step[], runStatus: RunStatus): Set<StepId> {
  const r = new Set<StepId>(steps.map((s) => s.stepId))
  if (runStatus === 'awaiting_approval' || runStatus === 'approving') r.add('approve')
  return r
}

function applyEvent(state: State, ev: RunEvent): Partial<State> {
  const events = [...state.events, ev]
  let steps = state.steps
  let { runStatus, pendingDecision } = state
  if (ev.type === 'tool.called') {
    steps = [...steps, { step: ev.data.step, tool: ev.data.tool, stepId: STEP_OF[ev.data.tool] ?? 'trace', args: ev.data.args ?? {}, state: 'running' }]
  } else if (ev.type === 'tool.result') {
    const i = steps.map((s) => s.tool === ev.data.tool && s.state === 'running').lastIndexOf(true)
    if (i >= 0) {
      steps = steps.slice()
      const t0 = state.events.find((e) => e.type === 'run.started')?.ts ?? ev.ts
      steps[i] = { ...steps[i], state: ev.data.is_error ? 'error' : 'ok', ref: ev.data.result_ref, ms: ev.data.duration_ms, summary: ev.data.summary, ui: ev.data.ui,
        queries: ev.data.queries ?? null, t: Math.max(0, ev.ts - t0) }
    }
  } else if (ev.type === 'approval.required') {
    runStatus = 'awaiting_approval'; pendingDecision = ev.data.decision_id
  } else if (ev.type === 'action.executed' || ev.type === 'plan.rejected' || ev.type === 'approval.failed') {
    runStatus = 'running'; pendingDecision = null
  } else if (ev.type === 'run.completed') {
    runStatus = 'completed'
  } else if (ev.type === 'run.error') {
    runStatus = 'failed'
  }
  return { events, steps, runStatus, pendingDecision, derived: derive(state.graph, state.summary, steps, events) }
}

/** Side effects with a job: a toast when something new happened. Every number comes from the event itself. */
function announce(ev: RunEvent) {
  const toast = useToasts.getState().push
  if (ev.type === 'tool.result' && !ev.data.is_error) {
    const ui = ev.data.ui
    if (ev.data.tool === 'declare_incident' && ui) toast(`${ui.incident_id} declared: ${ui.site_ids?.length} site(s) stopped`)
    if (ev.data.tool === 'trace_exposure' && ui) toast(`A normal tool sees ${ui.tier1_view?.directly_affected_tier1} problems. DOMINO found ${ui.multi_tier?.exposed_tier1} suppliers in trouble.`)
  }
  if (ev.type === 'approval.required') toast('A rescue plan is ready. It needs your OK.')
  if (ev.type === 'action.executed') toast(ev.data.receipt?.summary ?? 'Plan executed')
  if (ev.type === 'run.completed') toast('Run complete. The report was checked against the graph.')
  if (ev.type === 'run.error') toast(`Run stopped: ${String(ev.data.error).slice(0, 80)}`)
}

let unsubscribe: (() => void) | null = null
const REFRESH_ON = new Set(['declare_incident', 'flag_orders_at_risk', 'verify_execution'])

function initialTheme(): 'light' | 'dark' {
  try {
    const t = localStorage.getItem('domino-theme')
    if (t === 'light' || t === 'dark') return t
  } catch {
    /* storage unavailable */
  }
  return 'dark'
}

export const useStore = create<State>((set, get) => ({
  graph: null, summary: null, scenarios: [], places: null, scenario: 'monsoon', mode: 'scripted', theme: initialTheme(),
  runId: null, runStatus: 'idle', events: [], steps: [], pendingDecision: null, selected: null, hoverEvidence: null,
  error: null, busy: false, ready: false, derived: EMPTY,

  load: async () => {
    try {
      const [graph, summary, scenarios, places] = await Promise.all([api.graph(), api.summary(), api.scenarios(), api.places()])
      set({ graph, summary, scenarios, places, error: null, ready: true, derived: derive(graph, summary, get().steps, get().events) })
    } catch (e) {
      set({ ready: true, error: `Could not load the world. ${String((e as Error).message ?? e)}` })
    }
  },
  refresh: async () => {
    const [graph, summary] = await Promise.all([api.graph(), api.summary()])
    set({ graph, summary, derived: derive(graph, summary, get().steps, get().events) })
  },
  setScenario: (scenario) => set({ scenario }),
  setMode: (mode) => set({ mode }),
  setTheme: (theme) => {
    try { localStorage.setItem('domino-theme', theme) } catch { /* storage unavailable */ }
    document.documentElement.dataset.theme = theme
    set({ theme })
  },
  select: (selected) => set({ selected }),
  setHoverEvidence: (hoverEvidence) => set({ hoverEvidence }),

  run: async () => {
    unsubscribe?.()
    set({ busy: true, error: null, events: [], steps: [], pendingDecision: null, runStatus: 'running', selected: null })
    try {
      let run_id: string
      if (get().mode === 'mcp') {
        // Claude Code (or Desktop) is the agent; the war room only watches and approves.
        run_id = (await api.watchExternal()).run_id
        await get().refresh()
      } else {
        await api.reset()
        await get().refresh()
        run_id = (await api.startRun({ scenario: get().scenario, dry_run: get().mode === 'scripted' })).run_id
      }
      set({ runId: run_id, busy: false })
      unsubscribe = subscribe(run_id, (ev) => {
        set((s) => applyEvent(s, ev))
        announce(ev)
        if (ev.type === 'tool.result' && REFRESH_ON.has(ev.data.tool)) void get().refresh()
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
    try {
      await api.approve(runId, pendingDecision)
    } catch (e) {
      set({ error: String((e as Error).message ?? e), runStatus: 'awaiting_approval' })
    }
  },
  reject: async (feedback) => {
    const { runId } = get()
    if (!runId) return
    try { await api.reject(runId, feedback) } catch (e) { set({ error: String((e as Error).message ?? e) }) }
  },
  reset: async () => {
    unsubscribe?.()
    set({ busy: true, runId: null, runStatus: 'idle', events: [], steps: [], pendingDecision: null, selected: null })
    try {
      await api.reset()
      await get().refresh()
      useToasts.getState().push('World reset from pristine')
    } finally {
      set({ busy: false })
    }
  },
  inject: async (entityId, label) => {
    set({ busy: true, error: null })
    try {
      const r = await api.inject({ entity_ids: [entityId], kind: 'disruption', title: `Manual: ${label}`, capacity_factor: 0, duration_days: 21 })
      await get().refresh()
      useToasts.getState().push(`${r.incident_id} injected · ${r.site_ids.length} site(s) at 0% for 21 days`)
    } catch (e) {
      set({ error: String((e as Error).message ?? e) })
    } finally {
      set({ busy: false })
    }
  },
}))
