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
