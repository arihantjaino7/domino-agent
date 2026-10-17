import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { memo, useEffect, useMemo, useState } from 'react'
import { COLUMNS, NODE_H, NODE_W, layout } from '../lib/layout'
import { useStore } from '../lib/store'
import type { NodeStatus, WorldNode } from '../lib/types'

const STATUS_STYLE: Record<NodeStatus, { dot: string; ring: string; label: string }> = {
  disrupted: { dot: 'bg-disrupted', ring: 'border-disrupted/80', label: 'disrupted' },
  late: { dot: 'bg-late', ring: 'border-late/70', label: 'projected late' },
  covered: { dot: 'bg-covered', ring: 'border-covered/60', label: 'exposed, covered' },
  protected: { dot: 'bg-protected', ring: 'border-protected/70', label: 'protected (projected)' },
  none: { dot: 'bg-line', ring: 'border-line-soft', label: '' },
}
const EDGE_COLOR: Record<NodeStatus, string> = {
  disrupted: 'var(--color-disrupted)',
  late: 'var(--color-late)',
  covered: 'var(--color-covered)',
  protected: 'var(--color-protected)',
  none: 'var(--color-line)',
}

type EntityData = { node: WorldNode; status: NodeStatus; dim: boolean; sub: string }

function subline(n: WorldNode): string {
  const d = n.data as Record<string, unknown>
  if (n.kind === 'site') return [n.id, d.region_name].filter(Boolean).join(' · ')
  if (n.kind === 'customer') return `${d.orders} orders${d.tier === 'strategic' ? ' · strategic' : ''}`
  return n.id
}

const EntityNode = memo(function EntityNode({ data }: NodeProps<Node<EntityData>>) {
  const s = STATUS_STYLE[data.status]
  return (
    <div
      style={{ width: NODE_W, height: NODE_H }}
      className={`flex items-center gap-2 rounded-md border bg-raised px-2.5 transition-[opacity,border-color] duration-200 ${s.ring} ${data.dim ? 'opacity-35' : 'opacity-100'}`}
      title={s.label ? `${data.node.label}: ${s.label}` : data.node.label}
    >
      <Handle type="target" position={Position.Left} className="!size-1 !border-0 !bg-transparent" />
      <span className={`size-2 shrink-0 rounded-full ${s.dot}`} aria-hidden />
      <div className="min-w-0 leading-tight">
        <div className="truncate text-[12.5px] text-fg">{data.node.label}</div>
        <div className="num truncate text-[10.5px] text-faint">{data.sub}</div>
      </div>
      <Handle type="source" position={Position.Right} className="!size-1 !border-0 !bg-transparent" />
    </div>
  )
})

function ColumnLabel({ data }: NodeProps<Node<{ label: string }>>) {
  return <div className="w-[196px] text-[11.5px] font-medium tracking-[0.02em] text-dim">{data.label}</div>
}

const nodeTypes = { entity: EntityNode, column: ColumnLabel }

/** When a cascade is traced, frame the involved nodes; otherwise show the whole network. */
function AutoFrame({ ids, ready }: { ids: string[]; ready: boolean }) {
  const rf = useReactFlow()
  const key = ids.join(',')
  useEffect(() => {
    if (!ready) return
    const t = setTimeout(() => {
      void rf.fitView({ nodes: ids.length ? ids.map((id) => ({ id })) : undefined, padding: ids.length ? 0.18 : 0.06, duration: 450 })
    }, 60)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, ready])
  return null
}

export function GraphCanvas() {
  return (
    <ReactFlowProvider>
      <Canvas />
    </ReactFlowProvider>
  )
}

function Canvas() {
  const graph = useStore((s) => s.graph)
  const derived = useStore((s) => s.derived)
  const [pos, setPos] = useState<Record<string, { x: number; y: number }> | null>(null)

  useEffect(() => {
    if (!graph) return
    let alive = true
    void layout(graph).then((p) => alive && setPos(p))
    return () => {
      alive = false
    }
  }, [graph])

  const focus = Object.keys(derived.status).length > 0 && derived.origins.length > 0

  const nodes = useMemo<Node[]>(() => {
    if (!graph || !pos) return []
    const out: Node[] = graph.nodes.map((n) => {
      const status = derived.status[n.id] ?? 'none'
      return {
        id: n.id,
        type: 'entity',
        position: pos[n.id] ?? { x: 0, y: 0 },
        data: { node: n, status, dim: focus && status === 'none', sub: subline(n) },
        draggable: false,
        selectable: false,
      }
    })
    const top = Math.min(...Object.values(pos).map((p) => p.y))
    for (const c of COLUMNS) {
      const xs = graph.nodes.filter((n) => n.column === c.id).map((n) => pos[n.id]?.x ?? 0)
      if (!xs.length) continue
      out.push({
        id: `col:${c.id}`,
        type: 'column',
        position: { x: Math.min(...xs), y: top - 34 },
        data: { label: c.label },
        draggable: false,
        selectable: false,
      })
    }
    return out
  }, [graph, pos, derived.status, focus])

  const edges = useMemo<Edge[]>(() => {
    if (!graph) return []
    return graph.edges.map((e) => {
      const hot = derived.hotEdges[e.id]
      const color = hot ? EDGE_COLOR[hot] : 'var(--color-line)'
      return {
        id: e.id,
        source: e.source,
        target: e.target,
        type: 'default',
        animated: false,
        style: {
          stroke: color,
          strokeWidth: hot ? 1.75 : 1,
          strokeDasharray: e.kind === 'can_supply' ? '4 4' : undefined,
          opacity: hot ? 0.95 : focus ? 0.18 : 0.45,
        },
        markerEnd: hot ? { type: MarkerType.ArrowClosed, color, width: 14, height: 14 } : undefined,
        zIndex: hot ? 1 : 0,
      }
    })
  }, [graph, derived.hotEdges, focus])

  const frameIds = useMemo(
    () => (focus ? Object.keys(derived.status).filter((id) => graph?.nodes.some((n) => n.id === id)) : []),
    [focus, derived.status, graph],
  )

  if (!graph || !pos) {
    return (
      <div className="grid h-full place-items-center text-[13px] text-dim">
        {graph ? 'Laying out the supply network…' : 'Loading the world graph…'}
      </div>
    )
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.06 }}
      minZoom={0.2}
      maxZoom={1.6}
      nodesConnectable={false}
      proOptions={{ hideAttribution: true }}
      colorMode="dark"
    >
      <AutoFrame ids={frameIds} ready={nodes.length > 0} />
      <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="var(--color-line-soft)" />
      <Controls showInteractive={false} position="bottom-right" />
    </ReactFlow>
  )
}

export function Legend() {
  const items: [NodeStatus, string][] = [
    ['disrupted', 'Disrupted'],
    ['covered', 'Exposed, covered'],
    ['late', 'Projected late'],
    ['protected', 'Protected (projected)'],
  ]
  return (
    <ul className="flex items-center gap-4 text-[12px] text-dim">
      {items.map(([k, label]) => (
        <li key={k} className="flex items-center gap-1.5">
          <span className={`size-2 rounded-full ${STATUS_STYLE[k].dot}`} aria-hidden />
          {label}
        </li>
      ))}
      <li className="flex items-center gap-1.5">
        <svg width="18" height="6" aria-hidden>
          <line x1="0" y1="3" x2="18" y2="3" stroke="var(--color-dim)" strokeDasharray="4 3" />
        </svg>
        Approved alternate
      </li>
    </ul>
  )
}
