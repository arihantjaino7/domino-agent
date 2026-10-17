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

export const STATUS_VAR: Record<NodeStatus, string> = {
  disrupted: 'var(--st-disrupted)',
  late: 'var(--st-late)',
  covered: 'var(--st-covered)',
  protected: 'var(--st-protected)',
  none: 'var(--line)',
}
const STATUS_LABEL: Record<NodeStatus, string> = {
  disrupted: 'disrupted',
  late: 'projected late',
  covered: 'exposed, covered',
  protected: 'protected (projected)',
  none: '',
}
const HOP_MS = 220

type EntityData = { node: WorldNode; status: NodeStatus; dim: boolean; focus: boolean; sub: string }

function subline(n: WorldNode): string {
  const d = n.data as Record<string, unknown>
  if (n.kind === 'site') return [n.id, d.region_name].filter(Boolean).join(' · ')
  if (n.kind === 'customer') return `${d.orders} orders${d.tier === 'strategic' ? ' · strategic' : ''}`
  return n.id
}

const EntityNode = memo(function EntityNode({ data }: NodeProps<Node<EntityData>>) {
  const color = STATUS_VAR[data.status]
  const on = data.status !== 'none'
  return (
    <div
      style={{
        width: NODE_W,
        height: NODE_H,
        borderColor: on ? `color-mix(in srgb, ${color} 55%, transparent)` : undefined,
        boxShadow: data.focus ? `0 0 0 3px color-mix(in srgb, var(--accent) 18%, transparent)` : undefined,
      }}
      className={`flow-node flex items-center gap-2 rounded-[10px] border border-line-2 bg-surface px-2.5 ${data.dim ? 'opacity-30' : ''} ${on ? 'lit' : ''}`}
      title={on ? `${data.node.label}: ${STATUS_LABEL[data.status]}` : data.node.label}
    >
      <Handle type="target" position={Position.Left} className="!size-1 !border-0 !bg-transparent" />
      <span className="dot" style={{ background: on ? color : 'var(--line)' }} aria-hidden />
      <div className="min-w-0 leading-tight">
        <div className="truncate text-[12.5px] font-medium text-ink">{data.node.label}</div>
        <div className="mono truncate text-[10px] text-muted">{data.sub}</div>
      </div>
      <Handle type="source" position={Position.Right} className="!size-1 !border-0 !bg-transparent" />
    </div>
  )
})

function ColumnLabel({ data }: NodeProps<Node<{ label: string }>>) {
  return <div className="label w-[196px]">{data.label}</div>
}
const nodeTypes = { entity: EntityNode, column: ColumnLabel }

function AutoFrame({ ids, ready }: { ids: string[]; ready: boolean }) {
  const rf = useReactFlow()
  const key = ids.join(',')
  useEffect(() => {
    if (!ready) return
    const t = setTimeout(() => {
      void rf.fitView({ nodes: ids.length ? ids.map((id) => ({ id })) : undefined, padding: ids.length ? 0.16 : 0.05, duration: 800 })
    }, 80)
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
  const hover = useStore((s) => s.hoverEvidence)
  const theme = useStore((s) => s.theme)
  const [pos, setPos] = useState<Record<string, { x: number; y: number }> | null>(null)

  useEffect(() => {
    if (!graph) return
    let alive = true
    void layout(graph).then((p) => alive && setPos(p))
    return () => {
      alive = false
    }
  }, [graph])

  // Domino propagation: reveal the traced cascade one hop at a time.
  const maxHop = useMemo(() => Math.max(-1, ...Object.values(derived.hop)), [derived.hop])
  const hopKey = Object.keys(derived.hop).join(',')
  const [revealHop, setRevealHop] = useState(99)
  useEffect(() => {
    if (!hopKey) {
      setRevealHop(99)
      return
    }
    setRevealHop(0)
    let h = 0
    const id = setInterval(() => {
      h += 1
      setRevealHop(h)
      if (h > maxHop + 2) clearInterval(id)
    }, HOP_MS)
    return () => clearInterval(id)
  }, [hopKey, maxHop])

  const shown = (id: string): NodeStatus => {
    const s = derived.status[id] ?? 'none'
    if (s === 'none' || s === 'disrupted' || s === 'protected') return s
    const hop = derived.hop[id]
    if (hop != null) return hop <= revealHop ? s : 'none'
    return revealHop > maxHop ? s : 'none'
  }

  const hoverPath = useMemo(() => derived.evidence.find((e) => e.id === hover)?.path ?? null, [hover, derived.evidence])
  const traced = derived.origins.length > 0

  const nodes = useMemo<Node[]>(() => {
    if (!graph || !pos) return []
    const out: Node[] = graph.nodes.map((n) => {
      const status = shown(n.id)
      const onPath = hoverPath ? hoverPath.includes(n.id) : false
      return {
        id: n.id,
        type: 'entity',
        position: pos[n.id] ?? { x: 0, y: 0 },
        data: { node: n, status, sub: subline(n), focus: onPath, dim: hoverPath ? !onPath : traced && status === 'none' },
        draggable: false,
        selectable: false,
      }
    })
    const top = Math.min(...Object.values(pos).map((p) => p.y))
    for (const c of COLUMNS) {
      const xs = graph.nodes.filter((n) => n.column === c.id).map((n) => pos[n.id]?.x ?? 0)
      if (xs.length) out.push({ id: `col:${c.id}`, type: 'column', position: { x: Math.min(...xs), y: top - 30 }, data: { label: c.label }, draggable: false, selectable: false })
    }
    return out
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph, pos, derived.status, derived.hop, revealHop, hoverPath, traced])

  const edges = useMemo<Edge[]>(() => {
    if (!graph) return []
    return graph.edges.map((e) => {
      const hotRaw = derived.hotEdges[e.id]
      const hot = hotRaw && shown(e.source) !== 'none' && shown(e.target) !== 'none' ? hotRaw : undefined
      const onPath = hoverPath ? hoverPath.includes(e.source) && hoverPath.includes(e.target) && hoverPath.indexOf(e.target) === hoverPath.indexOf(e.source) + 1 : false
      const color = onPath ? 'var(--accent)' : hot ? STATUS_VAR[hot] : 'var(--line)'
      return {
        id: e.id,
        source: e.source,
        target: e.target,
        type: 'default',
        animated: hot === 'protected',
        style: {
          stroke: color,
          strokeWidth: onPath ? 2.5 : hot ? 1.6 : 1,
          strokeDasharray: e.kind === 'can_supply' && hot !== 'protected' ? '4 4' : undefined,
          opacity: hoverPath ? (onPath ? 1 : 0.08) : hot ? 0.9 : traced ? 0.22 : 0.6,
        },
        markerEnd: hot || onPath ? { type: MarkerType.ArrowClosed, color, width: 13, height: 13 } : undefined,
        zIndex: onPath ? 2 : hot ? 1 : 0,
      }
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph, derived.hotEdges, revealHop, hoverPath, traced])

  const frameIds = useMemo(
    () => (traced ? Object.keys(derived.status).filter((id) => graph?.nodes.some((n) => n.id === id)) : []),
    [traced, derived.status, graph],
  )

  if (!graph || !pos) {
    return <div className="grid h-full place-items-center text-[13px] text-muted">{graph ? 'Laying out the supply network…' : 'Loading the world graph…'}</div>
  }
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.05 }}
      minZoom={0.15}
      maxZoom={1.8}
      nodesConnectable={false}
      proOptions={{ hideAttribution: true }}
      colorMode={theme}
      style={{ background: 'transparent' }}
    >
      <AutoFrame ids={frameIds} ready={nodes.length > 0} />
      <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="var(--line)" />
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
    <ul className="flex flex-wrap items-center gap-2">
      {items.map(([k, label]) => (
        <li key={k} className="tag" style={{ ['--c' as string]: STATUS_VAR[k] }}>
          {label}
        </li>
      ))}
    </ul>
  )
}
