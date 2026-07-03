import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import type { RhythmNodeData } from '../../types'

function RhythmNode({ data }: NodeProps<RhythmNodeData>) {
  const color = data.intensity > 6 ? '#e76f51' : data.intensity > 4 ? '#d4a373' : '#00b4d8'
  return (
    <div className="flex flex-col items-center" style={{ width: 60, height: 60 }}>
      <Handle type="target" position={Position.Top} id="t-t" className="!opacity-0" />
      <Handle type="target" position={Position.Left} id="t-l" className="!opacity-0" />
      <Handle type="target" position={Position.Bottom} id="t-b" className="!opacity-0" />
      <Handle type="target" position={Position.Right} id="t-r" className="!opacity-0" />
      <div className="w-3 h-3 rounded-full shadow-lg" style={{ backgroundColor: color }} />
      <div className="text-[10px] text-gray-400 mt-1 whitespace-nowrap">{data.label}</div>
      <Handle type="source" position={Position.Bottom} id="s-b" className="!opacity-0" />
      <Handle type="source" position={Position.Right} id="s-r" className="!opacity-0" />
      <Handle type="source" position={Position.Top} id="s-t" className="!opacity-0" />
      <Handle type="source" position={Position.Left} id="s-l" className="!opacity-0" />
    </div>
  )
}

export default memo(RhythmNode)
