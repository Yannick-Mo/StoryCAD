import { useMemo, useCallback } from 'react'
import ReactFlow, { Background, type Node, type Edge, type NodeTypes, MarkerType } from 'reactflow'
import 'reactflow/dist/style.css'
import CharacterNode from './CharacterNode'
import type { Character } from '../../types'
import { getBestHandle, nodeCenter } from '../shared/getBestHandle'

const nodeTypes: NodeTypes = { character: CharacterNode }

const POSITIONS: Record<number, { x: number; y: number }> = {
  0: { x: 150, y: 200 },
  1: { x: 450, y: 200 },
  2: { x: 300, y: 80 },
}

interface CharCanvasProps { characters: Character[] }

export default function CharCanvas({ characters }: CharCanvasProps) {
  const nodes: Node[] = useMemo(() =>
    characters.map((ch, i) => ({
      id: ch.id,
      type: 'character',
      position: POSITIONS[i] ?? { x: i * 200, y: 150 },
      data: { name: ch.name, role: ch.role, relations: ch.relations },
    })), [characters])

  const edges: Edge[] = useMemo(() =>
    characters.flatMap(ch =>
      ch.relations.map((rel, i) => {
        const src = nodes.find(n => n.id === ch.id)
        const tgt = nodes.find(n => n.id === rel.targetId)
        if (!src || !tgt) return []
        const a = nodeCenter(src.position, 120, 40)
        const b = nodeCenter(tgt.position, 120, 40)
        const { sourceHandle, targetHandle } = getBestHandle(a, b)
        return [{
          id: `e-${ch.id}-${rel.targetId}-${i}`,
          source: ch.id,
          target: rel.targetId,
          sourceHandle,
          targetHandle,
          type: 'bezier',
          label: rel.type,
          style: { stroke: '#8a8a8a' },
          markerEnd: { type: MarkerType.ArrowClosed, color: '#8a8a8a' },
        }]
      }).flat()
    ), [characters, nodes])

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
