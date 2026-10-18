import { create } from 'zustand'
import { api } from './api'
import { useToasts } from './toasts'
import { subscribe } from './sse'
import type { LiveAlert, NodeStatus, Places, Recording, ReplayMeta, RunEvent, RunStatus, Scenario, Summary, WorldGraph } from './types'

/* eslint-disable @typescript-eslint/no-explicit-any */

/* ---------- the agent's journey, as the sidebar shows it ---------- */
export type Mode = 'scripted' | 'replay' | 'mcp' | 'api'
export type Experience = 'guided' | 'free' | null

// The visitor's choice survives a reload; private windows or blocked storage simply ask again.
const saved = (k: string): string | null => { try { return localStorage.getItem(k) } catch { return null } }
const save = (k: string, v: string | null) => { try { if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v) } catch { /* storage unavailable */ } }
export type StepId = 'detect' | 'trace' | 'impact' | 'options' | 'simulate' | 'approve' | 'verify'
export const STEPS: { id: StepId; num: string; title: string; tools: string[] }[] = [
  { id: 'detect', num: '01', title: 'Detect', tools: ['resolve_entities', 'declare_incident'] },
  { id: 'trace', num: '02', title: 'Trace', tools: ['trace_exposure', 'explain_shared_dependencies', 'get_entity_context', 'recall_history', 'scan_single_points_of_failure'] },
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
  execFailed: any | null  // the executor's receipt when an approved plan was not committed
  verify: any | null
  report: any | null
  spendCents: number | null
  trace: any | null
  alert: string | null
  kind: string | null
  lessons: { text: string }[]
  memoryGraph: string | null
  executedSeq: number | null
  delivery: any | null // fast-forward result: how each PO arrived and which orders were fulfilled
}

interface State {
  graph: WorldGraph | null
  summary: Summary | null
  scenarios: Scenario[]
  /** false when the server has no ANTHROPIC_API_KEY, so Claude API mode cannot run */
  claudeApi: boolean
  /** how the visitor chose to use the war room: a guided path, everything open, or not chosen yet */
  experience: Experience
  /** guided path: the step on screen, and the furthest step reached (what is unlocked) */
  guideStep: number
  guideMax: number
  setExperience: (e: Experience) => void
  setGuideStep: (step: number) => void
  /** true when /mcp needs MCP_API_KEY, so the Claude Code guide shows where the key goes */
  mcpKey: boolean
  places: Places | null
  scenario: string
  mode: Mode
  replays: ReplayMeta[]
  replayId: string | null
  /** the recording being played (replay mode only) */
  recording: Recording | null
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
  stopWatching: () => void
  setTheme: (t: 'light' | 'dark') => void
  select: (s: StepId | null) => void
  setHoverEvidence: (id: string | null) => void
  run: () => Promise<void>
  setReplay: (id: string) => void
  approve: () => Promise<void>
  reject: (feedback: string) => Promise<void>
  deliver: () => Promise<void>
  reset: () => Promise<void>
  inject: (entityId: string, label: string) => Promise<void>
  stopLiveSites: (event: LiveAlert) => Promise<void>
}

const EMPTY: Derived = {
  status: {}, hop: {}, evidence: [], hotEdges: {}, tier1View: null, exposedTier1: [], shared: [], origins: [],
  components: [], products: [], plants: [], exposedOrders: null, lateOrders: null, customersHit: null, capacity: [],
  alternatives: [], resolve: null, declared: null, shortage: null, sim: null, plan: null, receipt: null, execFailed: null, verify: null,
  report: null, spendCents: null, trace: null, alert: null, kind: null, lessons: [], memoryGraph: null, executedSeq: null,
  delivery: null,
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
  const last = [...events].reverse().find((e) => e.type === 'action.executed')
  // An approval the executor's checks stopped (e.g. preflight) bought nothing: never show it as done.
  const executed = last?.data.receipt?.outcome === 'executed' ? last : undefined
  if (last && !executed) d.execFailed = last.data.receipt
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
  d.delivery = [...events].reverse().find((e) => e.type === 'delivery.completed')?.data ?? null
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
  if (state.events.some((e) => e.seq === ev.seq)) return {} // the deliver call returns its event and the stream may send it too
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
    if (ev.data.tool === 'trace_exposure' && ui) toast(`A tier-1 view sees ${ui.tier1_view?.directly_affected_tier1} problems. DOMINO found ${ui.multi_tier?.exposed_tier1} suppliers in trouble.`)
  }
  if (ev.type === 'approval.required') toast('A rescue plan is ready. It needs your OK.')
  if (ev.type === 'action.executed') {
    const r = ev.data.receipt
    toast(r?.outcome === 'executed' ? r.summary : `The executor stopped the plan (${r?.outcome ?? 'unknown'}). Nothing was bought.`)
  }
  if (ev.type === 'run.completed') toast('Run complete. The report was checked against the graph.')
  if (ev.type === 'delivery.completed') {
    const c = ev.data.counts ?? {}
    toast(`Day ${ev.data.day}: ${c.fulfilled ?? 0} orders fulfilled on time, ${c.fulfilled_late ?? 0} late. DOMINO remembered how each supplier did.`)
  }
  if (ev.type === 'run.error') toast(`Run stopped: ${String(ev.data.error).slice(0, 80)}`)
}

let unsubscribe: (() => void) | null = null

/* ---------- replay: play a recorded run through the same applyEvent as live events ---------- */

let replayTimer: ReturnType<typeof setTimeout> | null = null
let replayNext: (() => void) | null = null // resumes playback after the recorded approval
function stopReplay() {
  if (replayTimer) clearTimeout(replayTimer)
  replayTimer = null
  replayNext = null
}
/** Real gaps between events (the model thinking, a person deciding), capped so a viewer is not kept waiting. */
const gapMs = (a: RunEvent, b: RunEvent) => Math.min(1400, Math.max(90, (b.ts - a.ts) * 1000))
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
  graph: null, summary: null, scenarios: [], claudeApi: true, mcpKey: true, places: null, scenario: 'monsoon', mode: 'scripted', theme: initialTheme(),
  experience: saved('domino-experience') as Experience,
  guideStep: Number(saved('domino-guide-step') ?? 0) || 0,
  guideMax: Number(saved('domino-guide-max') ?? 0) || 0,
  setExperience: (experience) => {
    save('domino-experience', experience)
    set({ experience })
  },

  setGuideStep: (guideStep) => {
    const guideMax = Math.max(get().guideMax, guideStep)
    save('domino-guide-step', String(guideStep))
    save('domino-guide-max', String(guideMax))
    set({ guideStep, guideMax })
  },
  replays: [], replayId: null, recording: null,
  runId: null, runStatus: 'idle', events: [], steps: [], pendingDecision: null, selected: null, hoverEvidence: null,
  error: null, busy: false, ready: false, derived: EMPTY,

  load: async () => {
    try {
      // The backend may still be starting (make dev starts both at once): retry a few times before giving up.
      const fetchAll = () => Promise.all([api.graph(), api.summary(), api.scenarios(), api.places()])
      let all: Awaited<ReturnType<typeof fetchAll>> | null = null
      for (let attempt = 1; !all; attempt++) {
        try { all = await fetchAll() } catch (e) {
          if (attempt >= 8) throw e
          await new Promise((r) => setTimeout(r, 1500))
        }
      }
      const [graph, summary, { scenarios, claude_api, mcp_key }, places] = all
      set({ graph, summary, scenarios, claudeApi: claude_api ?? true, mcpKey: mcp_key ?? true, places, error: null, ready: true, derived: derive(graph, summary, get().steps, get().events) })
      api.replays().then((replays) => set((s) => ({ replays, replayId: s.replayId ?? replays[0]?.id ?? null })), () => { /* replays are optional */ })
    } catch (e) {
      set({ ready: true, error: `Could not load the world. ${String((e as Error).message ?? e)}` })
    }
  },
  refresh: async () => {
    const [graph, summary] = await Promise.all([api.graph(), api.summary()])
    set({ graph, summary, derived: derive(graph, summary, get().steps, get().events) })
  },
  setScenario: (scenario) => set({ scenario }),
  setMode: (mode) => {
    const was = get().mode
    if (mode === was) return
    if (was === 'replay' || mode === 'replay' || (was === 'mcp' && get().runStatus !== 'idle')) {
      // Entering or leaving a recording, or leaving a Claude Code run that this page only watches:
      // clear the screen and show the live world again.
      stopReplay(); unsubscribe?.(); unsubscribe = null
      set({ mode, recording: null, runId: null, runStatus: 'idle', events: [], steps: [], pendingDecision: null, selected: null })
      void get().refresh()
      return
    }
    set({ mode })
  },
  stopWatching: () => {
    // The page stops following the Claude Code run; the run itself (outside this page) is not touched.
    unsubscribe?.(); unsubscribe = null
    set({ runId: null, runStatus: 'idle', events: [], steps: [], pendingDecision: null, selected: null })
    void get().refresh()
  },
  setReplay: (replayId) => set({ replayId }),
  setTheme: (theme) => {
    try { localStorage.setItem('domino-theme', theme) } catch { /* storage unavailable */ }
    document.documentElement.dataset.theme = theme
    set({ theme })
  },
  select: (selected) => set({ selected }),
  setHoverEvidence: (hoverEvidence) => set({ hoverEvidence }),

  run: async () => {
    // Without a key the backend refuses a Claude API run; check first, so the shared world is not reset for nothing.
    if (get().mode === 'api' && !get().claudeApi) {
      useToasts.getState().push('This copy has no Claude API key. Use Replay, Demo or Claude Code instead.')
      return
    }
    unsubscribe?.()
    stopReplay()
    set({ busy: true, error: null, events: [], steps: [], pendingDecision: null, runStatus: 'running', selected: null })
    if (get().mode === 'replay') {
      // Only the recording is read from the backend: no reset, no run, no approval reaches the graph.
      try {
        const id = get().replayId
        if (!id) throw new Error('No recording is published yet')
        const rec = await api.replay(id)
        const frames = [...rec.frames].sort((a, b) => a.after_seq - b.after_seq)
        const first = frames[0]
        const graph = first?.graph ?? get().graph, summary = first?.summary ?? get().summary
        set({ recording: rec, busy: false, graph, summary, derived: derive(graph, summary, [], []) })
        const play = (i: number) => {
          const ev = rec.events[i]
          if (!ev) return
          const frame = frames.find((f) => f.after_seq === ev.seq)
          set((s) => ({ ...applyEvent(frame ? { ...s, graph: frame.graph, summary: frame.summary } : s, ev),
            ...(frame ? { graph: frame.graph, summary: frame.summary } : {}) }))
          announce(ev)
          const next = rec.events[i + 1]
          if (!next) return
          if (ev.type === 'approval.required') {
            useToasts.getState().push('In the recording a person approved this plan here. Press Approve to continue.')
            replayNext = () => { replayNext = null; replayTimer = setTimeout(() => play(i + 1), 400) }
            return
          }
          replayTimer = setTimeout(() => play(i + 1), gapMs(ev, next))
        }
        play(0)
      } catch (e) {
        set({ busy: false, runStatus: 'failed', error: String((e as Error).message ?? e) })
      }
      return
    }
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
      // No run was started (refused, rate-limited or unreachable): back to idle, not stuck on "reading the alert".
      set({ busy: false, runStatus: 'idle', error: String((e as Error).message ?? e) })
    }
  },
  approve: async () => {
    if (get().mode === 'replay') {
      if (replayNext && get().runStatus === 'awaiting_approval') { set({ runStatus: 'approving' }); replayNext() }
      return
    }
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
    if (get().mode === 'replay') {
      useToasts.getState().push('This recording was approved, so it cannot be rejected here. Switch to Demo to try a rejection.')
      return
    }
    const { runId, pendingDecision } = get()
    if (!runId) return
    // The refused plan can no longer be approved: lock Approve now, not when the stream catches up.
    set({ runStatus: 'running', pendingDecision: null })
    try { await api.reject(runId, feedback, pendingDecision) } catch (e) {
      set({ error: String((e as Error).message ?? e), runStatus: 'awaiting_approval', pendingDecision })
    }
  },
  deliver: async () => {
    const { runId, mode } = get()
    if (!runId || mode === 'replay') return
    set({ busy: true, error: null })
    try {
      const { event } = await api.deliver(runId)
      set((s) => applyEvent(s, event))
      announce(event)
      await get().refresh()
    } catch (e) {
      set({ error: String((e as Error).message ?? e) })
    } finally {
      set({ busy: false })
    }
  },
  reset: async () => {
    unsubscribe?.()
    stopReplay()
    if (get().mode === 'replay') {
      // A replay never touches the live world; this only clears the screen.
      set({ recording: null, runId: null, runStatus: 'idle', events: [], steps: [], pendingDecision: null, selected: null })
      await get().refresh()
      return
    }
    set({ busy: true, runId: null, runStatus: 'idle', events: [], steps: [], pendingDecision: null, selected: null })
    try {
      await api.reset()
      await get().refresh()
      useToasts.getState().push('World reset from pristine')
    } finally {
      set({ busy: false })
    }
  },
  stopLiveSites: async (event) => {
    if (get().busy || ['running', 'approving', 'awaiting_approval'].includes(get().runStatus) || !event.site_ids.length) return
    set({ busy: true, error: null })
    const stopped = new Set<string>()
    try {
      // The manual-incident API accepts up to twenty entities per request.
      for (let i = 0; i < event.site_ids.length; i += 20) {
        const result = await api.inject({ entity_ids: event.site_ids.slice(i, i + 20), kind: event.type_label.toLowerCase(),
          title: `GDACS: ${event.title}`.slice(0, 200), capacity_factor: 0, duration_days: 21 })
        result.site_ids.forEach((id) => stopped.add(id))
      }
      useToasts.getState().push(`${stopped.size} site(s) stopped in this world from the GDACS alert.`)
    } catch (e) {
      set({ error: `${stopped.size ? `${stopped.size} site(s) were stopped before the request failed. ` : ''}${String((e as Error).message ?? e)}` })
    } finally {
      try { await get().refresh() } catch {
        set({ error: 'Could not refresh the world after the manual stop. Reload to check its current state.' })
      }
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
