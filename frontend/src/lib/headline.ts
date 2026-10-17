/* Two-tone headlines and sidebar sub-lines per step. Every number comes from engine output (CLAUDE.md rule 8). */
import type { Derived, StepId } from './store'
import type { RunStatus, Summary } from './types'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('en-US'))
const usd = (c: number | null | undefined) => (c == null ? '—' : `$${Math.round(c / 100).toLocaleString('en-US')}`)
const plural = (k: number, one: string, many: string) => `${n(k)} ${k === 1 ? one : many}`

export interface Head { eyebrow: string; lead: string; soft: string; lede: string }

export function headline(step: StepId | null, d: Derived, summary: Summary | null, status: RunStatus, scenarioTitle: string): Head {
  const notInGraph = d.report?.outcome === 'not_in_graph'
  if (notInGraph) {
    const term = d.resolve?.results?.[0]?.term ?? 'That place'
    return {
      eyebrow: 'Outcome',
      lead: `${term} is not in the graph.`,
      soft: 'That is not the same as safe.',
      lede: 'Nothing in the modelled supply network connects to this alert. It may simply not be modelled, so DOMINO says so instead of reporting "no impact".',
    }
  }
  switch (step) {
    case 'detect': {
      const sites = d.declared?.site_ids ?? []
      return d.declared
        ? { eyebrow: 'Detect', lead: `${plural(sites.length, 'site is', 'sites are')} down.`, soft: `Declared as ${d.declared.incident_id}, until day ${d.declared.end_day}.`,
            lede: `Footprint: ${sites.join(', ')}. Recording an observed fact is a safe action, so the agent does it on its own.` }
        : { eyebrow: 'Detect', lead: 'Reading the alert.', soft: 'Matching its places to the graph.', lede: 'Full-text search, exact and fuzzy, over every region, hazard zone, site, port and plant.' }
    }
    case 'trace':
      return {
        eyebrow: 'Trace',
        lead: `A tier-1 view sees ${n(d.tier1View)} affected suppliers.`,
        soft: `The graph finds ${n(d.exposedTier1.length)}, through ${d.origins.join(', ') || '…'}.`,
        lede: `Variable-depth FEEDS paths from the disrupted site to tier-1 suppliers, plants, products and ${n(d.exposedOrders)} open orders. Hover an evidence path to see it on the map.`,
      }
    case 'impact':
      return {
        eyebrow: 'Impact',
        lead: `${n(d.shortage?.totals?.exposed)} orders are exposed.`,
        soft: `${n(d.shortage?.totals?.projected_late)} will actually be late.`,
        lede: 'Exposure is not shortage. A day-by-day projection with stock, goods already on the water and complementary inputs decides which orders really slip.',
      }
    case 'options': {
      const c = d.capacity[0]
      return c
        ? { eyebrow: 'Options', lead: `Naive capacity says ${n(c.naive)} a week.`, soft: `The network can deliver ${n(c.trueWk)}.`,
            lede: `${c.component} into ${c.plant}, from algo.maxFlow over the whole upstream network. A source is rejected only when its remaining clean capacity is zero.` }
        : { eyebrow: 'Options', lead: 'Measuring what can really be delivered.', soft: 'Max-flow, not tier-1 sums.', lede: '' }
    }
    case 'simulate': {
      const rows = d.sim?.strategies ?? []
      const best = rows.find((r: any) => r.strategy === d.sim?.recommended)
      const naive = rows.find((r: any) => r.strategy === 'S1')
      return best
        ? { eyebrow: 'Simulate', lead: `DOMINO keeps ${n(best.on_time)} of ${n(best.orders)} orders on time.`, soft: `The naive plan, ${n(naive?.on_time)}.`,
            lede: 'Every plan was executed in its own GRAPH.COPY sandbox with the real executor, and upstream capacity was rationed jointly across all of them.' }
        : { eyebrow: 'Simulate', lead: 'Testing every plan in a sandbox.', soft: 'One graph copy per strategy.', lede: '' }
    }
    case 'approve':
      return d.plan
        ? { eyebrow: 'Approve', lead: `${plural(d.plan.pos?.length ?? 0, 'purchase order', 'purchase orders')}, ${usd(d.plan.spend_cents)}.`,
            soft: status === 'awaiting_approval' ? 'Waiting for your approval.' : 'Approved by a human.',
            lede: 'Purchase commitments always need a human. Approval is bound to this plan hash and this world version; the LLM never executes anything.' }
        : { eyebrow: 'Approve', lead: 'No plan yet.', soft: '', lede: '' }
    case 'verify': {
      const checks = d.verify?.checks ?? []
      const ok = checks.filter((c: any) => c.ok).length
      return checks.length
        ? { eyebrow: 'Verify', lead: ok === checks.length ? `All ${checks.length} invariants hold.` : `${checks.length - ok} invariants failed.`,
            soft: 'Protected (projected): parts not yet received.',
            lede: d.receipt?.summary ? `Graph receipt: ${d.receipt.summary}.` : '' }
        : { eyebrow: 'Verify', lead: 'Checking the graph after execution.', soft: 'Nine invariants.', lede: '' }
    }
    default: {
      const inc = summary?.incidents?.[0]
      return inc
        ? { eyebrow: 'Open incident', lead: `${inc.id} is open.`, soft: 'Run DOMINO to trace its cascade.', lede: inc.title }
        : { eyebrow: 'Kestrel Devices', lead: 'A quiet day in the supply chain.', soft: 'Pick an alert and run DOMINO.',
            lede: `${scenarioTitle ? `Next alert: ${scenarioTitle}. ` : ''}DOMINO traces the multi-tier impact on a FalkorDB graph, tests recovery plans in sandboxes, and asks you before it commits a cent.` }
    }
  }
}

export function stepSub(step: StepId, d: Derived, status: RunStatus): string | null {
  switch (step) {
    case 'detect': return d.declared ? `${d.declared.incident_id} · ${d.declared.site_ids?.join(', ')}` : d.resolve ? 'Places resolved' : null
    case 'trace': return d.tier1View != null ? `Tier-1 view ${n(d.tier1View)} · graph ${n(d.exposedTier1.length)}` : null
    case 'impact': return d.shortage ? `${n(d.shortage.totals?.exposed)} exposed · ${n(d.shortage.totals?.projected_late)} late` : null
    case 'options': return d.capacity.length ? `${d.capacity.length} networks · ${d.alternatives.reduce((k, a) => k + (a.rejected?.length ?? 0), 0)} rejected` : null
    case 'simulate': {
      const best = d.sim?.strategies?.find((r: any) => r.strategy === d.sim?.recommended)
      return best ? `${best.strategy} ${n(best.on_time)}/${n(best.orders)} on time` : null
    }
    case 'approve': return d.receipt ? 'Approved · executed' : status === 'awaiting_approval' ? 'Waiting for you' : d.plan ? 'Submitted' : null
    case 'verify': {
      const checks = d.verify?.checks ?? []
      return checks.length ? `${checks.filter((c: any) => c.ok).length}/${checks.length} invariants` : null
    }
  }
}
