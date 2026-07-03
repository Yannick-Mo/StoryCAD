import type { WorldInfo, InfoControl, PovInfo, KanbanItem } from '../../types'

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

export function InfoControlView({ data }: { data: InfoControl[] }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <span className="text-lg">👁️ 信息释放</span>
      <div className="space-y-2">
        {data.map(ic => (
          <div key={ic.topic} className="flex items-center gap-3 bg-gray-800 px-4 py-2 rounded-lg text-sm">
            <span className={`w-2 h-2 rounded-full ${ic.revealed ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-gray-300">{ic.topic}</span>
            <span className="text-xs text-gray-500">{ic.revealed ? '已揭示' : '未揭示'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function PovView({ data }: { data: PovInfo[] }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <span className="text-lg">🎯 POV分配</span>
      <div className="space-y-3">
        {data.map(p => (
          <div key={p.character} className="flex items-center gap-3 bg-gray-800 px-4 py-2 rounded-lg text-sm w-64">
            <span className="text-gray-300 w-16">{p.character}</span>
            <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
              <div className="h-full bg-amber-600 rounded-full" style={{ width: `${p.percentage}%` }} />
            </div>
            <span className="text-xs text-gray-400 w-8 text-right">{p.percentage}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function InspirationView({ data }: { data: string[] }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <span className="text-lg">💡 灵感碎片</span>
      <div className="space-y-2">
        {data.map(insp => (
          <div key={insp} className="bg-gray-800/50 border border-dashed border-gray-700 px-4 py-2 rounded-lg text-sm text-gray-400 italic">
            「{insp}」
          </div>
        ))}
      </div>
    </div>
  )
}

export function KanbanView({ data }: { data: KanbanItem[] }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <span className="text-lg">📋 进度看板</span>
      <div className="flex gap-4">
        {data.map(k => (
          <div key={k.stage} className="bg-gray-800 px-5 py-3 rounded-xl text-center min-w-[80px]">
            <div className="text-2xl font-bold text-amber-400">{k.count}</div>
            <div className="text-xs text-gray-400 mt-1">{k.stage}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function ChangelogView({ data }: { data: string[] }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <span className="text-lg">📓 版本日志</span>
      <div className="space-y-2">
        {data.map(entry => (
          <div key={entry} className="bg-gray-800/50 px-4 py-2 rounded-lg text-sm text-gray-400 border-l-2 border-gray-700">
            {entry}
          </div>
        ))}
      </div>
    </div>
  )
}
