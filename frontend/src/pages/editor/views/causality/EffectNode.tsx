import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import type { EffectNodeData } from '../../types'

function EffectNode({ data }: NodeProps<EffectNodeData>) {
  return (
    <div className="bg-gray-800 border border-orange-700/50 rounded-xl px-4 py-3 shadow-lg">
      <Handle type="target" position={Position.Left} id="t-l" className="!bg-orange-500 !w-2 !h-2" />
      <Handle type="target" position={Position.Top} id="t-t" className="!bg-orange-500 !w-2 !h-2" />
      <Handle type="target" position={Position.Right} id="t-r" className="!bg-orange-500 !w-2 !h-2" />
      <Handle type="target" position={Position.Bottom} id="t-b" className="!bg-orange-500 !w-2 !h-2" />
      <div className="text-xs text-orange-500 mb-1">⚡ 果</div>
      <div className="text-sm text-gray-200">{data.label}</div>
    </div>
  )
}

export default memo(EffectNode)
