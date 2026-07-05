import type { Character, CharacterRelation } from '../../types'

interface CharacterEdgeDetailProps {
  source: Character
  target: Character
  relation: CharacterRelation
  onClose: () => void
  onDelete: () => void
}

const ROLE_LABELS: Record<string, string> = {
  protagonist: '主角',
  ally: '盟友',
  antagonist: '对手',
}

export default function CharacterEdgeDetail({ source, target, relation, onClose, onDelete }: CharacterEdgeDetailProps) {
  return (
    <div className="absolute right-0 top-0 h-full w-96 bg-gray-900/95 backdrop-blur-xl border-l border-gray-800 z-20 flex flex-col shadow-2xl">
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-start justify-between gap-3 mb-2">
          <div>
            <div className="text-[10px] text-gray-500 mb-1">选中关系连线</div>
            <h3 className="font-medium text-amber-100">{relation.type}</h3>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-lg leading-none">✕</button>
        </div>
        <div className="text-xs text-gray-500">
          {source.name} → {target.name}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <div className="grid grid-cols-[1fr_auto_1fr] items-stretch gap-2">
          <div className="bg-gray-950/50 border border-gray-800 rounded-xl p-3">
            <div className="text-[10px] text-gray-500 mb-1">源角色</div>
            <div className="text-sm font-medium text-gray-200 truncate">{source.name}</div>
            <div className="text-[10px] text-gray-600 mt-0.5">{ROLE_LABELS[source.role] ?? source.role}</div>
          </div>
          <div className="flex items-center text-amber-500 text-sm">→</div>
          <div className="bg-gray-950/50 border border-gray-800 rounded-xl p-3">
            <div className="text-[10px] text-gray-500 mb-1">目标角色</div>
            <div className="text-sm font-medium text-gray-200 truncate">{target.name}</div>
            <div className="text-[10px] text-gray-600 mt-0.5">{ROLE_LABELS[target.role] ?? target.role}</div>
          </div>
        </div>

        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-1">关系详情</div>
          <p className="text-xs text-gray-300 leading-relaxed">{relation.description || '暂未填写关系描述。'}</p>
        </section>

        <button
          onClick={onDelete}
          className="w-full px-3 py-1.5 rounded-lg text-xs text-red-400 hover:bg-red-600/20 transition-colors"
        >
          删除连线
        </button>
      </div>
    </div>
  )
}
