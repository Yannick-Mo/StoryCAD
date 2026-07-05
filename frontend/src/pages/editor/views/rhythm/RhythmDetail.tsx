import type { RhythmPoint, Chapter, Act } from '../../types'

interface RhythmDetailProps {
  point: RhythmPoint
  chapter?: Chapter
  act?: Act
  wordCount: number
  onClose: () => void
}

const DIMENSIONS = [
  { key: 'action' as const, label: '动作/冲突', color: '#f97316' },
  { key: 'suspense' as const, label: '悬疑/谜题', color: '#3b82f6' },
  { key: 'emotion' as const, label: '感情/关系', color: '#ec4899' },
  { key: 'humor' as const, label: '轻松/幽默', color: '#22c55e' },
]

function barWidth(value: number, max: number) {
  return `${Math.max((value / max) * 100, 4)}%`
}

function paceNote(words: number, intensity: number): string {
  if (words > 2000 && intensity < 5) return '偏慢 — 字数偏多但节奏偏弱，建议精简或提升冲突密度'
  if (words < 800 && intensity > 7) return '偏快 — 信息量大但展开不足，建议适当扩充场景'
  return '节奏适中，字数和强度匹配良好'
}

function paceColor(words: number, intensity: number): string {
  if (words > 2000 && intensity < 5) return 'text-amber-400'
  if (words < 800 && intensity > 7) return 'text-blue-400'
  return 'text-green-400'
}

export default function RhythmDetail({ point, chapter, act, wordCount, onClose }: RhythmDetailProps) {
  const maxVal = Math.max(point.action, point.suspense, point.emotion, point.humor, 1)

  return (
    <div className="absolute right-0 top-0 h-full w-96 bg-gray-900/95 backdrop-blur-xl border-l border-gray-800 z-20 flex flex-col shadow-2xl">
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-start justify-between gap-3 mb-2">
          <div>
            <div className="text-[10px] text-gray-500 mb-1">节奏详情</div>
            <h3 className="font-medium text-amber-100 text-lg">{point.label}</h3>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-lg leading-none">✕</button>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          {act && <span style={{ color: act.color }}>{act.name}</span>}
          {chapter && <span>· {chapter.goal || '暂无目标'}</span>}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Summary */}
        <section className="grid grid-cols-3 gap-2">
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-lg p-2 text-center">
            <div className="text-sm text-gray-200">{wordCount > 0 ? `${wordCount}` : '未开始'}</div>
            <div className="text-[10px] text-gray-600 mt-0.5">字数</div>
          </div>
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-lg p-2 text-center">
            <div className="text-sm text-amber-400">{point.intensity}/10</div>
            <div className="text-[10px] text-gray-600 mt-0.5">综合强度</div>
          </div>
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-lg p-2 text-center">
            <div className={`text-xs ${paceColor(wordCount, point.intensity)}`}>{wordCount > 0 ? paceNote(wordCount, point.intensity) : '未开始写作'}</div>
            <div className="text-[10px] text-gray-600 mt-0.5">节奏</div>
          </div>
        </section>

        {/* Four dimensions */}
        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-3">四维强度分布</div>
          <div className="space-y-2.5">
            {DIMENSIONS.map(d => (
              <div key={d.key} className="flex items-center gap-2">
                <div className="w-14 text-[10px] text-gray-400 text-right shrink-0">{d.label}</div>
                <div className="flex-1 h-3 bg-gray-950 rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all" style={{ width: barWidth(point[d.key], maxVal), backgroundColor: d.color }} />
                </div>
                <div className="w-5 text-[10px] text-gray-500 text-right">{point[d.key]}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Overall */}
        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-1">综合强度曲线位置</div>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 bg-gray-950 rounded-full overflow-hidden">
              <div className="h-full rounded-full bg-amber-400 transition-all" style={{ width: `${(point.intensity / 10) * 100}%` }} />
            </div>
            <span className="text-xs text-amber-400 font-medium">{point.intensity}/10</span>
          </div>
        </section>
      </div>
    </div>
  )
}
