import { useState } from 'react'
import type { Continent, Region, Faction, FactionRelation } from '../../types'
import RegionDetail from './RegionDetail'
import FactionDetail from './FactionDetail'
import RelationshipGraph from './RelationshipGraph'

interface WorldBuilderProps {
  continents: Continent[]
  regions: Region[]
  factions: Faction[]
  factionRelations: FactionRelation[]
  characters: { id: string; name: string }[]
  onSaveRegion: (region: Region) => void
  onSaveFaction: (faction: Faction) => void
  onAddFactionRelation: (sourceId: string, targetId: string, type: string) => void
  onDeleteFactionRelation: (id: string) => void
}

type Tab = 'regions' | 'factions' | 'relations'

export default function WorldBuilder({
  continents, regions, factions, factionRelations, characters,
  onSaveRegion, onSaveFaction, onAddFactionRelation, onDeleteFactionRelation,
}: WorldBuilderProps) {
  const [tab, setTab] = useState<Tab>('regions')
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null)
  const [selectedFaction, setSelectedFaction] = useState<Faction | null>(null)

  const tabs: { key: Tab; label: string }[] = [
    { key: 'regions', label: '区域' },
    { key: 'factions', label: '势力' },
    { key: 'relations', label: '关系' },
  ]

  return (
    <div className="h-full w-full flex flex-col">
      {/* Tab bar */}
      <div className="flex gap-1 px-4 pt-3 pb-2 border-b border-gray-800">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-colors ${tab === t.key ? 'bg-amber-600/20 text-amber-400' : 'text-gray-500 hover:text-gray-300'}`}
          >{t.label}</button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Region tab */}
        {tab === 'regions' && (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {continents.map(cont => {
              const contRegions = regions.filter(r => r.continentId === cont.id)
              return (
                <div key={cont.id}>
                  <div className="text-sm font-medium text-amber-100 mb-2">{cont.name}</div>
                  <div className="text-xs text-gray-500 mb-3">{cont.description}</div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {contRegions.map(reg => {
                      const regionChars = characters.filter(c => reg.characterIds.includes(c.id))
                      return (
                        <div
                          key={reg.id}
                          onClick={() => setSelectedRegion(reg)}
                          className="bg-gray-800/60 border border-gray-700/50 rounded-xl p-4 cursor-pointer hover:border-gray-600 transition-colors"
                        >
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-sm font-medium text-gray-200">{reg.name}</span>
                            <span className="text-[10px] text-gray-600">{reg.climate}</span>
                          </div>
                          <div className="text-xs text-gray-500 line-clamp-2 mb-2">{reg.description}</div>
                          <div className="flex flex-wrap gap-1.5 text-[10px]">
                            {reg.resources.map(r => (
                              <span key={r} className="px-1.5 py-0.5 rounded bg-gray-700/50 text-gray-400">{r}</span>
                            ))}
                            {regionChars.map(c => (
                              <span key={c.id} className="px-1.5 py-0.5 rounded bg-amber-600/20 text-amber-400">@{c.name}</span>
                            ))}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Faction tab */}
        {tab === 'factions' && (
          <div className="flex-1 overflow-y-auto p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {factions.map(fac => {
                const allyNames = fac.allies.map(id => factions.find(f => f.id === id)?.name ?? id)
                const enemyNames = fac.enemies.map(id => factions.find(f => f.id === id)?.name ?? id)
                const territoryNames = fac.territory.map(id => regions.find(r => r.id === id)?.name ?? id)
                return (
                  <div
                    key={fac.id}
                    onClick={() => setSelectedFaction(fac)}
                    className="bg-gray-800/60 border border-gray-700/50 rounded-xl p-4 cursor-pointer hover:border-gray-600 transition-colors"
                  >
                    <div className="text-sm font-medium text-gray-200 mb-1">{fac.name}</div>
                    <div className="text-xs text-gray-500 mb-2">{fac.goal}</div>
                    <div className="flex flex-wrap gap-2 text-[10px]">
                      <span className="text-gray-600">领地: {territoryNames.join('、')}</span>
                      <span className="text-gray-600">领袖: {fac.leader}</span>
                    </div>
                    <div className="flex gap-2 mt-2 text-[10px]">
                      {allyNames.length > 0 && <span className="px-1.5 py-0.5 rounded bg-green-900/30 text-green-400">盟友: {allyNames.join('、')}</span>}
                      {enemyNames.length > 0 && <span className="px-1.5 py-0.5 rounded bg-red-900/30 text-red-400">敌对: {enemyNames.join('、')}</span>}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Relations tab */}
        {tab === 'relations' && (
          <RelationshipGraph
            factions={factions}
            relations={factionRelations}
            onAddRelation={onAddFactionRelation}
            onDeleteRelation={onDeleteFactionRelation}
          />
        )}
      </div>

      {/* Detail panels */}
      {selectedRegion && (
        <RegionDetail
          region={selectedRegion}
          characters={characters}
          onClose={() => setSelectedRegion(null)}
          onSave={region => { onSaveRegion(region); setSelectedRegion(null) }}
        />
      )}
      {selectedFaction && (
        <FactionDetail
          faction={selectedFaction}
          regions={regions}
          factions={factions}
          onClose={() => setSelectedFaction(null)}
          onSave={faction => { onSaveFaction(faction); setSelectedFaction(null) }}
        />
      )}
    </div>
  )
}
