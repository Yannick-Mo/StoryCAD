import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import type { CharacterNodeData } from '../../types'

function CharacterNode({ data }: NodeProps<CharacterNodeData>) {
  return (
    <div className="bg-gray-800 border-2 border-gray-600 rounded-full px-5 py-2 shadow-lg flex items-center gap-2">
      <Handle type="target" position={Position.Left} id="t-l" className="!bg-gray-400 !w-2 !h-2" />
      <Handle type="target" position={Position.Top} id="t-t" className="!bg-gray-400 !w-2 !h-2" />
      <Handle type="target" position={Position.Right} id="t-r" className="!bg-gray-400 !w-2 !h-2" />
      <Handle type="target" position={Position.Bottom} id="t-b" className="!bg-gray-400 !w-2 !h-2" />
      <span className="font-bold text-amber-100 text-sm">{data.name}</span>
      <span className="text-xs text-gray-500">⚡</span>
      <Handle type="source" position={Position.Right} id="s-r" className="!bg-gray-400 !w-2 !h-2" />
      <Handle type="source" position={Position.Top} id="s-t" className="!bg-gray-400 !w-2 !h-2" />
      <Handle type="source" position={Position.Bottom} id="s-b" className="!bg-gray-400 !w-2 !h-2" />
      <Handle type="source" position={Position.Left} id="s-l" className="!bg-gray-400 !w-2 !h-2" />
    </div>
  )
}

export default memo(CharacterNode)
