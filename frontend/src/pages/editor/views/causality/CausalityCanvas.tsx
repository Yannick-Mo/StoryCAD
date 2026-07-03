import { useMemo, useCallback } from 'react'
import ReactFlow, { Background, type Node, type Edge, type NodeTypes, MarkerType } from 'reactflow'
import 'reactflow/dist/style.css'
import CauseNode from './CauseNode'
import EffectNode from './EffectNode'
import type { Causality } from '../../types'
import { getBestHandle, nodeCenter } from '../shared/getBestHandle'

const nodeTypes: NodeTypes = { cause: CauseNode, effect: EffectNode }

interface CausalityCanvasProps { causalities: Causality[] }

export default function CausalityCanvas({ causalities }: CausalityCanvasProps) {
  const nodes: Node[] = useMemo(() =>
    causalities.flatMap((c, i) => [
      { id: `cause-${c.id}`, type: 'cause' as const, position: { x: 40, y: i * 120 + 40 }, data: { label: c.cause } },
      { id: `effect-${c.id}`, type: 'effect' as const, position: { x: 320, y: i * 120 + 40 }, data: { label: c.effect } },
    ]), [causalities])

  const edges: Edge[] = useMemo(() =>
    causalities.map(c => {
      const src = nodes.find(n => n.id === `cause-${c.id}`)!
      const tgt = nodes.find(n => n.id === `effect-${c.id}`)!
      const a = nodeCenter(src.position, 120, 70)
      const b = nodeCenter(tgt.position, 120, 70)
      const { sourceHandle, targetHandle } = getBestHandle(a, b)
      return {
        id: `e-${c.id}`,
        source: `cause-${c.id}`,
        target: `effect-${c.id}`,
        sourceHandle,
        targetHandle,
        type: 'bezier',
        style: { stroke: '#d4a373', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#d4a373' },
      }
    }), [causalities, nodes])

  const onConnect = useCallback(() => {}, [])

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onConnect={onConnect}
      defaultEdgeOptions={{ type: 'bezier' }}
      fitView minZoom={0.3} maxZoom={2}
    >
      <Background color="#333" gap={20} />
    </ReactFlow>
  )
}
