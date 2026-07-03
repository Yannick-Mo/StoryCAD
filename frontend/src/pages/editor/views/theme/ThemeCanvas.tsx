import { useMemo, useCallback } from 'react'
import ReactFlow, { Background, type Node, type Edge, type NodeTypes } from 'reactflow'
import 'reactflow/dist/style.css'
import ThemeNode from './ThemeNode'
import type { ThemeItem } from '../../types'
import { getBestHandle, nodeCenter } from '../shared/getBestHandle'

const nodeTypes: NodeTypes = { theme: ThemeNode }
const RADIUS = 140

interface ThemeCanvasProps { themes: ThemeItem[] }

export default function ThemeCanvas({ themes }: ThemeCanvasProps) {
  const initialNodes: Node[] = useMemo(() =>
    themes.map((t, i) => {
      const angle = (2 * Math.PI * i) / themes.length - Math.PI / 2
      return {
        id: `t${i}`,
        type: 'theme',
        position: { x: 250 + RADIUS * Math.cos(angle), y: 160 + RADIUS * Math.sin(angle) },
        data: { name: t.name, color: t.color, connections: t.connections },
      }
    }), [themes])

  const edges: Edge[] = useMemo(() =>
    themes.flatMap((t, i) =>
      t.connections.map(targetName => {
        const j = themes.findIndex(th => th.name === targetName)
        if (j === -1) return []
        const src = initialNodes[i]
        const tgt = initialNodes[j]
        if (!src || !tgt) return []
        const a = nodeCenter(src.position, 120, 40)
        const b = nodeCenter(tgt.position, 120, 40)
        const { sourceHandle, targetHandle } = getBestHandle(a, b)
        return [{
          id: `te${i}-${j}`,
          source: `t${i}`,
          target: `t${j}`,
          sourceHandle,
          targetHandle,
          type: 'bezier',
          style: { stroke: '#666', strokeWidth: 1 },
        }]
      }).flat()
    ), [themes, initialNodes])

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
