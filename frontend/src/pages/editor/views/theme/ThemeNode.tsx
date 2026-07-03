import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import type { ThemeNodeData } from '../../types'

function ThemeNode({ data }: NodeProps<ThemeNodeData>) {
  return (
    <div className="relative">
      <Handle type="target" position={Position.Left} id="t-l" className="!bg-gray-500 !w-2 !h-2" />
      <Handle type="target" position={Position.Top} id="t-t" className="!bg-gray-500 !w-2 !h-2" />
      <Handle type="target" position={Position.Right} id="t-r" className="!bg-gray-500 !w-2 !h-2" />
      <Handle type="target" position={Position.Bottom} id="t-b" className="!bg-gray-500 !w-2 !h-2" />
      <div
        className="px-4 py-2 rounded-full text-sm font-medium shadow-lg"
        style={{ backgroundColor: data.color + '20', border: `2px solid ${data.color}`, color: data.color }}
      >
        #{data.name}
      </div>
      <Handle type="source" position={Position.Right} id="s-r" className="!bg-gray-500 !w-2 !h-2" />
      <Handle type="source" position={Position.Top} id="s-t" className="!bg-gray-500 !w-2 !h-2" />
      <Handle type="source" position={Position.Bottom} id="s-b" className="!bg-gray-500 !w-2 !h-2" />
      <Handle type="source" position={Position.Left} id="s-l" className="!bg-gray-500 !w-2 !h-2" />
    </div>
  )
}

export default memo(ThemeNode)
