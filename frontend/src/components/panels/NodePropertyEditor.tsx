import type { GraphNode } from "../../types/skeleton"

interface NodePropertyEditorProps {
  node: GraphNode
  onUpdate: (field: string, value: string | number) => void
}

export default function NodePropertyEditor({ node, onUpdate }: NodePropertyEditorProps) {
  return (
    <div className="p-4 space-y-4 bg-gray-800">
      <div>
        <label className="block text-xs text-gray-400 mb-1">描述</label>
        <textarea
          value={node.description}
          onChange={(e) => onUpdate("description", e.target.value)}
          className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-100 resize-none"
          rows={3}
        />
      </div>
      <div>
        <label className="block text-xs text-gray-400 mb-1">
          情感值: {node.emotion_value}
        </label>
        <input
          type="range"
          min={0}
          max={100}
          value={node.emotion_value}
          onChange={(e) => onUpdate("emotion_value", Number(e.target.value))}
          className="w-full accent-blue-500"
        />
        <div className="flex justify-between text-xs text-gray-500">
          <span>0</span>
          <span>100</span>
        </div>
      </div>
    </div>
  )
}
