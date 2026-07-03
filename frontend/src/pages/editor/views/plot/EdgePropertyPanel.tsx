import type { ChapterEdge, EdgeType, Chapter } from '../../types'

interface EdgePropertyPanelProps {
  edge: ChapterEdge | null
  chapters: Chapter[]
  onClose: () => void
  onChangeType: (edgeId: string, newType: EdgeType) => void
  onDelete: (edgeId: string) => void
}

const EDGE_TYPE_OPTIONS: { value: EdgeType; label: string }[] = [
  { value: 'timeline', label: '时序主线' },
  { value: 'causal', label: '因果关系' },
  { value: 'foreshadow', label: '伏笔照应' },
  { value: 'character', label: '人物关联' },
  { value: 'theme', label: '主题关联' },
]

export default function EdgePropertyPanel({ edge, chapters, onClose, onChangeType, onDelete }: EdgePropertyPanelProps) {
  if (!edge) return null

  return (
    <div className="absolute right-4 bottom-20 w-64 bg-gray-900/95 backdrop-blur-xl border border-gray-700/50 rounded-xl shadow-2xl z-30 p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-medium text-gray-300">连线属性</h4>
        <button onClick={onClose} className="text-gray-500 hover:text-white text-sm leading-none">✕</button>
      </div>

      <div className="space-y-3">
        <div>
          <label className="text-[10px] text-gray-500 block mb-1">类型</label>
          <select
            value={edge.type}
            onChange={e => onChangeType(edge.id, e.target.value as EdgeType)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-gray-300 outline-none focus:border-amber-600"
          >
            {EDGE_TYPE_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-[10px] text-gray-500 block mb-1">来源</label>
          <div className="text-xs text-gray-400 truncate">{edge.sourceId}</div>
        </div>

        <div>
          <label className="text-[10px] text-gray-500 block mb-1">目标</label>
          <div className="text-xs text-gray-400 truncate">{edge.targetId}</div>
        </div>

        <button
          onClick={() => onDelete(edge.id)}
          className="w-full px-3 py-1.5 rounded-lg text-xs text-red-400 hover:bg-red-600/20 transition-colors"
        >
          删除连线
        </button>
      </div>
    </div>
  )
}
