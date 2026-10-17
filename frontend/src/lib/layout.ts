import ELK from 'elkjs/lib/elk.bundled.js'
import type { Column, WorldGraph } from './types'

// Deterministic, tiered left-to-right layout: ELK layered with one partition per column.
export const COLUMNS: { id: Column; label: string }[] = [
  { id: 'tier3', label: 'Tier 3' },
  { id: 'tier2', label: 'Tier 2' },
  { id: 'tier1', label: 'Tier 1' },
  { id: 'plant', label: 'Plants' },
  { id: 'product', label: 'Products' },
  { id: 'customer', label: 'Customers' },
]
export const NODE_W = 196
export const NODE_H = 40

const elk = new ELK()
const cache = new Map<string, Record<string, { x: number; y: number }>>()

export async function layout(g: WorldGraph): Promise<Record<string, { x: number; y: number }>> {
  const key = `${g.graph}:${g.nodes.length}:${g.edges.length}`
  const hit = cache.get(key)
  if (hit) return hit
  const ids = new Set(g.nodes.map((n) => n.id))
  const res = await elk.layout({
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'RIGHT',
      'elk.partitioning.activate': 'true',
      'elk.layered.spacing.nodeNodeBetweenLayers': '120',
      'elk.spacing.nodeNode': '14',
      'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
      'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
    },
    children: g.nodes.map((n) => ({
      id: n.id,
      width: NODE_W,
      height: NODE_H,
      layoutOptions: { 'elk.partitioning.partition': String(COLUMNS.findIndex((c) => c.id === n.column)) },
    })),
    edges: g.edges
      .filter((e) => ids.has(e.source) && ids.has(e.target) && e.source !== e.target)
      .map((e) => ({ id: e.id, sources: [e.source], targets: [e.target] })),
  })
  const pos: Record<string, { x: number; y: number }> = {}
  for (const c of res.children ?? []) pos[c.id] = { x: c.x ?? 0, y: c.y ?? 0 }
  cache.set(key, pos)
  return pos
}
