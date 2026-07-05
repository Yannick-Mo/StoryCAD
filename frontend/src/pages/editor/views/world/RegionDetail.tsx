import type { Region } from '../../types'

interface RegionDetailProps {
  region: Region
  characters: { id: string; name: string }[]
  onClose: () => void
  onSave: (region: Region) => void
}

const CLIMATES = ['极寒', '寒带', '温带', '亚热带', '热带', '荒漠', '海洋性', '荒芜', '多变']

export default function RegionDetail({ region, characters, onClose, onSave }: RegionDetailProps) {
  const handleChange = (field: keyof Region, value: string) => {
    onSave({ ...region, [field]: value })
  }

  const toggleResource = (resource: string) => {
    const current = region.resources.includes(resource)
      ? region.resources.filter((r: string) => r !== resource)
      : [...region.resources, resource]
    onSave({ ...region, resources: current })
  }

  const toggleCharacter = (charId: string) => {
    const current = region.characterIds.includes(charId)
      ? region.characterIds.filter((id: string) => id !== charId)
      : [...region.characterIds, charId]
    onSave({ ...region, characterIds: current })
  }

  return (
    <div className="absolute right-0 top-0 h-full w-96 bg-gray-900/95 backdrop-blur-xl border-l border-gray-800 z-20 flex flex-col shadow-2xl">
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center justify-between mb-3">
          <input
            value={region.name}
            onChange={e => handleChange('name', e.target.value)}
            className="bg-transparent text-lg font-medium text-amber-100 outline-none border-b border-transparent focus:border-amber-600/50 w-full max-w-[240px]"
          />
          <button onClick={onClose} className="text-gray-500 hover:text-white text-lg leading-none">✕</button>
        </div>
        <div className="flex gap-2">
          <select
            value={region.climate}
            onChange={e => handleChange('climate', e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-xs text-gray-300 outline-none"
          >
            {CLIMATES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <input
            value={region.ruler}
            onChange={e => handleChange('ruler', e.target.value)}
            placeholder="统治者"
            className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-xs text-gray-300 outline-none flex-1"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-1">描述</div>
          <textarea
            value={region.description}
            onChange={e => handleChange('description', e.target.value)}
            className="w-full h-24 bg-gray-950 border border-gray-700 rounded-lg p-2 text-xs text-gray-300 resize-none focus:outline-none focus:border-amber-600 leading-relaxed"
          />
        </section>

        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-2">资源</div>
          <div className="flex flex-wrap gap-1.5">
            {['灵石', '玄铁', '灵药', '灵兽', '珍珠', '龙骨', '寒铁', '冰晶', '煞晶', '魔铁', '远古遗物', '神纹碎片'].map(r => (
              <button
                key={r}
                onClick={() => toggleResource(r)}
                className={`px-2 py-1 rounded-full text-[10px] transition-colors ${region.resources.includes(r) ? 'bg-amber-600/30 text-amber-300' : 'bg-gray-800 text-gray-600 hover:bg-gray-700'}`}
              >{r}</button>
            ))}
          </div>
        </section>

        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-2">关联角色</div>
          <div className="flex flex-wrap gap-1.5">
            {characters.map(c => (
              <button
                key={c.id}
                onClick={() => toggleCharacter(c.id)}
                className={`px-2 py-1 rounded-full text-[10px] transition-colors ${region.characterIds.includes(c.id) ? 'bg-blue-600/30 text-blue-300' : 'bg-gray-800 text-gray-600 hover:bg-gray-700'}`}
              >@{c.name}</button>
            ))}
          </div>
        </section>

        <div className="grid grid-cols-2 gap-2">
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-lg p-2">
            <div className="text-[10px] text-gray-500">都城</div>
            <input
              value={region.capital}
              onChange={e => handleChange('capital', e.target.value)}
              className="bg-transparent text-xs text-gray-300 outline-none w-full mt-0.5"
            />
          </div>
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-lg p-2">
            <div className="text-[10px] text-gray-500">气候</div>
            <div className="text-xs text-gray-300 mt-0.5">{region.climate}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
