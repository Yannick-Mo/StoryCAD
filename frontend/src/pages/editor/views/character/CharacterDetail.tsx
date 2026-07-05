import type { Character } from '../../types'

interface CharacterDetailProps {
  character: Character
  onClose: () => void
}

const ROLE_LABELS: Record<string, string> = {
  protagonist: '主角',
  ally: '盟友',
  antagonist: '对手',
}

export default function CharacterDetail({ character, onClose }: CharacterDetailProps) {
  return (
    <div className="absolute right-0 top-0 h-full w-96 bg-gray-900/95 backdrop-blur-xl border-l border-gray-800 z-20 flex flex-col shadow-2xl">
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-start justify-between gap-3 mb-1">
          <h3 className="font-medium text-amber-100 text-lg">{character.name}</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-lg leading-none">✕</button>
        </div>
        <span className="px-2 py-0.5 rounded-full text-[10px] bg-amber-600/20 text-amber-400">
          {ROLE_LABELS[character.role] ?? character.role}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-1">性格特征</div>
          <p className="text-xs text-gray-300 leading-relaxed">{character.personality || '暂无'}</p>
        </section>

        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-1">外貌描述</div>
          <p className="text-xs text-gray-300 leading-relaxed">{character.appearance || '暂无'}</p>
        </section>

        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-1">身世背景</div>
          <p className="text-xs text-gray-300 leading-relaxed">{character.background || '暂无'}</p>
        </section>

        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-1">核心动机</div>
          <p className="text-xs text-gray-300 leading-relaxed">{character.motivation || '暂无'}</p>
        </section>

        {character.relations.length > 0 && (
          <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
            <div className="text-[10px] text-gray-500 mb-2">关系网络</div>
            <div className="space-y-1.5">
              {character.relations.map(rel => (
                <div key={rel.id} className="bg-gray-950/50 border border-gray-700/50 rounded-lg px-3 py-2">
                  <div className="text-xs text-gray-300">{rel.type}</div>
                  <div className="text-[10px] text-gray-500 mt-0.5 line-clamp-2">{rel.description}</div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
