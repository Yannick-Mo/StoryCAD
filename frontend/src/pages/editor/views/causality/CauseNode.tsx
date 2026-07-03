import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import type { CauseNodeData } from '../../types'

function CauseNode({ data }: NodeProps<CauseNodeData>) {
  return (
    <div className="bg-gray-800 border border-amber-700/50 rounded-xl px-4 py-3 shadow-lg">
      <Handle type="source" position={Position.Right} id="s-r" className="!bg-amber-500 !w-2 !h-2" />
      <Handle type="source" position={Position.Top} id="s-t" className="!bg-amber-500 !w-2 !h-2" />
      <Handle type="source" position={Position.Bottom} id="s-b" className="!bg-amber-500 !w-2 !h-2" />
      <Handle type="source" position={Position.Left} id="s-l" className="!bg-amber-500 !w-2 !h-2" />
      <div className="text-xs text-amber-500 mb-1">🔗 因</div>
      <div className="text-sm text-gray-200">{data.label}</div>
    </div>
  )
}

export default memo(CauseNode)
