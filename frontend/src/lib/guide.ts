import type { ViewId } from '../App'

/** Guided path: the step at which each view opens. It stays open after that. */
export const OPENS_AT: Record<ViewId, number> = { overview: 0, chain: 2, factories: 5, shipments: 5, agent: 6, xray: 8 }
export const VIEW_NAMES: Record<ViewId, string> = { overview: 'Overview', chain: 'Supply chain', factories: 'Factories', shipments: 'Shipments', agent: 'AI agent', xray: 'Risk X-ray' }
export const LAST_STEP = 9

/** Which views a visitor may open: everything in the full version; in the guide, what the path has reached. */
export function viewOpen(view: ViewId, experience: string | null, guideMax: number) {
  return experience !== 'guided' || guideMax >= OPENS_AT[view]
}

/** A view that has just opened in the guide gets a short glow in the navigation. */
export function viewFresh(view: ViewId, experience: string | null, guideStep: number) {
  return experience === 'guided' && OPENS_AT[view] > 0 && OPENS_AT[view] === guideStep
}
