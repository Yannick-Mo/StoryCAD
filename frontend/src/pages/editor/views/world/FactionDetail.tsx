import type { Faction, Region } from '../../types'

interface FactionDetailProps {
  faction: Faction
  regions: Region[]
  factions: Faction[]
  onClose: () => void
  onSave: (faction: Faction) => void
}

export default function FactionDetail({ faction, regions, factions, onClose, onSave }: FactionDetailProps) {
  const handleChange = (field: keyof Faction, value: string) => {
    onSave({ ...faction, [field]: value })
  }

  const toggleTerritory = (regId: string) => {
    const current = faction.territory.includes(regId)
      ? faction.territory.filter((id: string) => id !== regId)
      : [...faction.territory, regId]
    onSave({ ...faction, territory: current })
  }

  const toggleFaction = (field: 'allies' | 'enemies', facId: string) => {
    const current = faction[field].includes(facId)
      ? faction[field].filter((id: string) => id !== facId)
      : [...faction[field], facId]
    onSave({ ...faction, [field]: current })
  }

  return (
    <div className="absolute right-0 top-0 h-full w-96 bg-gray-900/95 backdrop-blur-xl border-l border-gray-800 z-20 flex flex-col shadow-2xl">
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center justify-between mb-2">
          <input
            value={faction.name}
            onChange={e => handleChange('name', e.target.value)}
            className="bg-transparent text-lg font-medium text-amber-100 outline-none border-b border-transparent focus:border-amber-600/50 w-full max-w-[200px]"
          />
          <button onClick={onClose} className="text-gray-500 hover:text-white text-lg leading-none">✕</button>
        </div>
        <input
          value={faction.leader}
          onChange={e => handleChange('leader', e.target.value)}
          placeholder="领袖"
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-xs text-gray-300 outline-none mb-2"
        />
        <textarea
          value={faction.goal}
          onChange={e => handleChange('goal', e.target.value)}
          placeholder="势力目标..."
          className="w-full h-16 bg-gray-800 border border-gray-700 rounded-lg p-2 text-xs text-gray-300 resize-none outline-none focus:border-amber-600"
        />
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-2">领地</div>
          <div className="flex flex-wrap gap-1.5">
            {regions.map(r => (
              <button
                key={r.id}
                onClick={() => toggleTerritory(r.id)}
                className={`px-2 py-1 rounded-full text-[10px] transition-colors ${faction.territory.includes(r.id) ? 'bg-amber-600/30 text-amber-300' : 'bg-gray-800 text-gray-600 hover:bg-gray-700'}`}
              >{r.name}</button>
            ))}
          </div>
        </section>

        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-2">盟友</div>
          <div className="flex flex-wrap gap-1.5">
            {factions.filter(f => f.id !== faction.id).map(f => (
              <button
                key={f.id}
                onClick={() => toggleFaction('allies', f.id)}
                className={`px-2 py-1 rounded-full text-[10px] transition-colors ${faction.allies.includes(f.id) ? 'bg-green-900/40 text-green-400' : 'bg-gray-800 text-gray-600 hover:bg-gray-700'}`}
              >{f.name}</button>
            ))}
          </div>
        </section>

        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-2">敌对</div>
          <div className="flex flex-wrap gap-1.5">
            {factions.filter(f => f.id !== faction.id).map(f => (
              <button
                key={f.id}
                onClick={() => toggleFaction('enemies', f.id)}
                className={`px-2 py-1 rounded-full text-[10px] transition-colors ${faction.enemies.includes(f.id) ? 'bg-red-900/40 text-red-400' : 'bg-gray-800 text-gray-600 hover:bg-gray-700'}`}
              >{f.name}</button>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
