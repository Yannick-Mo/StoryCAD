import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'

interface CausalNodeData {
  title: string
  actColor: string
  status: string
}

function CausalNode({ data }: NodeProps<CausalNodeData>) {
  const statusDot = data.status === 'final' ? 'bg-green-500'
    : data.status === 'revising' ? 'bg-yellow-500'
    : 'bg-gray-500'
  return (
    <div className="bg-gray-800/90 border border-gray-700 rounded-xl px-4 py-3 shadow-lg min-w-[140px]">
      <Handle type="source" position={Position.Right} id="s-r" className="!bg-amber-500 !w-2 !h-2" />
      <Handle type="target" position={Position.Left} id="t-l" className="!bg-amber-500 !w-2 !h-2" />
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full shrink-0 ${statusDot}`} />
        <span className="text-xs text-gray-400 truncate max-w-[100px]">{data.title}</span>
      </div>
    </div>
  )
}

export default memo(CausalNode)
