import { useMemo, useEffect } from 'react'
import ReactFlow, { Background, Controls, Handle, Position, type Node, type Edge, type NodeTypes, MarkerType, useNodesState } from 'reactflow'
import 'reactflow/dist/style.css'
import type { Faction, FactionRelation } from '../../types'

const RELATION_COLORS: Record<string, string> = {
  alliance: '#22c55e',
  conflict: '#ef4444',
  trade: '#3b82f6',
  vassal: '#a855f7',
  encroach: '#f97316',
}

const RELATION_LABELS: Record<string, string> = {
  alliance: '同盟',
  conflict: '敌对',
  trade: '贸易',
  vassal: '附庸',
  encroach: '蚕食',
}

function FactionNode({ data }: { data: { label: string } }) {
  return (
    <div className="bg-gray-800 border-2 border-gray-600 rounded-xl px-4 py-2 shadow-lg cursor-pointer hover:-translate-y-0.5 transition-all select-none">
      <Handle type="target" position={Position.Left} className="!bg-gray-500 !w-2 !h-2" />
      <span className="text-sm font-medium text-amber-100">{data.label}</span>
      <Handle type="source" position={Position.Right} className="!bg-gray-500 !w-2 !h-2" />
    </div>
  )
}

const nodeTypes: NodeTypes = { factionNode: FactionNode }

interface RelationshipGraphProps {
  factions: Faction[]
  relations: FactionRelation[]
}

export default function RelationshipGraph({ factions, relations }: RelationshipGraphProps) {
  const initialNodes: Node[] = useMemo(() =>
    factions.map((f, i) => ({
      id: f.id,
      type: 'factionNode',
      position: { x: 200 + (i % 3) * 280, y: 100 + Math.floor(i / 3) * 180 },
      data: { label: f.name },
    })), [factions])

  const edges: Edge[] = useMemo(() =>
    relations.map(r => ({
      id: r.id,
      source: r.sourceId,
      target: r.targetId,
      type: 'default',
      label: RELATION_LABELS[r.type],
      style: { stroke: RELATION_COLORS[r.type], strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: RELATION_COLORS[r.type] },
      labelStyle: { fontSize: 10, fill: '#9ca3af', background: '#1f2937', padding: '2px 6px', borderRadius: 4 },
    })), [relations])

  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState(initialNodes)
  const factionKey = factions.map(f => f.id).join(',')
  useEffect(() => { setFlowNodes(initialNodes) }, [factionKey, setFlowNodes])

  return (
    <div className="flex-1">
      <ReactFlow
        nodes={flowNodes}
        edges={edges}
        onNodesChange={onNodesChange}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={{ type: 'default' }}
        fitView minZoom={0.3} maxZoom={2}
        nodesDraggable
        nodesConnectable={false}
      >
        <Background color="#333" gap={20} />
        <Controls className="!bg-gray-800 !border-gray-700 !rounded-lg" />
      </ReactFlow>
      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-gray-900/90 border border-gray-700/50 rounded-xl px-3 py-2 flex gap-3 text-[10px]">
        {Object.entries(RELATION_LABELS).map(([key, label]) => (
          <div key={key} className="flex items-center gap-1">
            <div className="w-2.5 h-0.5 rounded" style={{ backgroundColor: RELATION_COLORS[key] }} />
            <span className="text-gray-400">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
