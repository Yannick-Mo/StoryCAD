import { useMemo, useCallback } from 'react'
import ReactFlow, { Background, type Node, type Edge, type NodeTypes } from 'reactflow'
import 'reactflow/dist/style.css'
import RhythmNode from './RhythmNode'
import type { RhythmPoint } from '../../types'
import { getBestHandle, nodeCenter } from '../shared/getBestHandle'

const nodeTypes: NodeTypes = { rhythm: RhythmNode }

interface RhythmCanvasProps { rhythms: RhythmPoint[] }

export default function RhythmCanvas({ rhythms }: RhythmCanvasProps) {
  const initialNodes: Node[] = useMemo(() =>
    rhythms.map((r, i) => ({
      id: `r${i}`,
      type: 'rhythm',
      position: { x: i * 160 + 60, y: 200 - r.intensity * 20 },
      data: { label: r.label, intensity: r.intensity, chapterIndex: r.chapterIndex },
    })), [rhythms])

  const edges: Edge[] = useMemo(() =>
    rhythms.slice(0, -1).map((_, i) => {
      const a = nodeCenter(initialNodes[i].position, 60, 60)
      const b = nodeCenter(initialNodes[i + 1].position, 60, 60)
      const { sourceHandle, targetHandle } = getBestHandle(a, b)
      return {
        id: `re${i}`,
        source: `r${i}`,
        target: `r${i + 1}`,
        sourceHandle,
        targetHandle,
        type: 'bezier',
        style: { stroke: '#666', strokeWidth: 1.5, strokeDasharray: '4 4' },
      }
    }), [rhythms, initialNodes])

  const onConnect = useCallback(() => {}, [])

  return (
    <ReactFlow
      nodes={initialNodes}
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
