import type { WorldInfo } from '../../types'

export function MapView({ data }: { data: WorldInfo }) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="bg-gray-800/80 rounded-2xl px-8 py-6 text-center">
        <div className="text-3xl mb-2">🗺️</div>
        <div className="text-lg font-medium text-amber-100">{data.name}</div>
        <div className="flex gap-2 mt-3 justify-center">
          {data.regions.map(r => (
            <span key={r} className="px-3 py-1 rounded-full text-xs bg-gray-700 text-gray-300">{r}</span>
          ))}
        </div>
      </div>
    </div>
  )
}

export function RulesView({ data }: { data: string[] }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <span className="text-lg">⚛️ 修炼体系</span>
      <div className="space-y-2">
        {data.map(r => <div key={r} className="bg-gray-800 px-4 py-2 rounded-lg text-sm text-gray-300">{r}</div>)}
      </div>
    </div>
  )
}

export function HistoryView({ data }: { data: string[] }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <span className="text-lg">📜 历史年表</span>
      <div className="space-y-2">
        {data.map(h => <div key={h} className="bg-gray-800 px-4 py-2 rounded-lg text-sm text-gray-300">{h}</div>)}
      </div>
    </div>
  )
}
