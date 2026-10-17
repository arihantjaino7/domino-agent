export const usd = (cents: number | null | undefined) =>
  cents == null ? '—' : `$${Math.round(cents / 100).toLocaleString('en-US')}`
export const int = (n: number | null | undefined) => (n == null ? '—' : n.toLocaleString('en-US'))

/* eslint-disable @typescript-eslint/no-explicit-any */
/** One line per finished step, assembled only from the tool's own result payload. */
export function stepLine(tool: string, ui: any): string {
  if (!ui) return ''
  switch (tool) {
    case 'resolve_entities': {
      const r = ui.results ?? []
      const found = r.filter((x: any) => x.candidates.length).map((x: any) => `${x.term} → ${x.candidates[0].id}`)
      return found.length ? found.join(' · ') : 'No match in the graph (not modelled, which is not the same as safe)'
    }
    case 'declare_incident':
      return `${ui.incident_id} · ${ui.site_ids?.join(', ')} down until day ${ui.end_day}`
    case 'trace_exposure':
      return `Tier-1 view: ${ui.tier1_view?.directly_affected_tier1} affected · multi-tier: ${ui.multi_tier?.exposed_tier1} tier-1 via ${[...new Set((ui.evidence ?? []).map((e: any) => e.origin))].join(', ')}`
    case 'explain_shared_dependencies':
      return (ui.shared ?? []).map((s: any) => `${s.site} feeds ${s.fan_out} tier-1 sites`).join(' · ') || 'No shared upstream'
    case 'project_shortages':
      return `${ui.totals?.exposed} exposed · ${ui.totals?.projected_late} projected late of ${ui.totals?.orders} orders`
    case 'compute_true_capacity':
      return `${ui.component} → ${ui.plant}: naive ${ui.naive_wk}/wk, true ${ui.true_wk}/wk`
    case 'find_alternatives':
      return `${ui.component} → ${ui.plant}: ${ui.accepted?.length} accepted, ${ui.rejected?.length} rejected${(ui.rejected ?? []).length ? ` (${ui.rejected.map((r: any) => `${r.site}: ${r.reason}`).join('; ')})` : ''}`
    case 'simulate_strategies': {
      const rows = ui.strategies ?? []
      return rows.map((r: any) => `${r.strategy} ${r.on_time}/${r.orders}`).join(' · ')
    }
    case 'submit_plan_for_approval':
      return `${ui.plan?.decision_id} · ${ui.plan?.pos?.length} POs · awaiting a human`
    case 'verify_execution':
      return ui.ok ? 'All 9 invariants hold' : `Failed: ${(ui.failed ?? []).join(', ')}`
    case 'record_lessons':
      return `${ui.lesson_ids?.length ?? 0} lesson(s) written to memory`
    case 'submit_incident_report':
      return ui.report ? `${ui.report.outcome}: ${ui.report.headline}` : ''
    default:
      return ''
  }
}
