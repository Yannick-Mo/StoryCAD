import { useMemo, useCallback, useState } from 'react'
import type { RhythmPoint, Chapter, Act } from '../../types'
import { RhythmEditPanel } from './RhythmEditPanel'

interface RhythmCanvasProps {
  rhythms: RhythmPoint[]
  chapters: Chapter[]
  acts: Act[]
  selectedIndex: number | null
  onSelectChapter: (index: number) => void
  onSaveRhythm: (chapterId: string, values: { action: number; suspense: number; emotion: number; humor: number; intensity: number }) => void
}

const BAR_W = 40
const GAP = 60
const CHART_H = 220
const PAD_L = 50
const PAD_R = 30
const PAD_T = 20
const PAD_B = 30

const DIM_COLORS = ['#f97316', '#3b82f6', '#ec4899', '#22c55e']
const DIM_LABELS = ['动作', '悬疑', '感情', '幽默']

function paceNote(words: number, intensity: number): string {
  if (words > 2000 && intensity < 5) return '偏慢 — 字数偏多但节奏偏弱'
  if (words < 800 && intensity > 7) return '偏快 — 信息量大但展开不足'
  return '适中'
}

export default function RhythmCanvas({ rhythms, chapters, acts, selectedIndex, onSelectChapter, onSaveRhythm }: RhythmCanvasProps) {
  const [editChapter, setEditChapter] = useState<{ id: string; title: string; values: any } | null>(null)
  const totalW = Math.max(rhythms.length * (BAR_W + GAP) + PAD_L + PAD_R, 400)

  const actBoundaries = useMemo(() => {
    const result: number[] = []
    let prevActId = ''
    for (let i = 0; i < rhythms.length; i++) {
      const ch = chapters[rhythms[i].chapterIndex]
      const actId = ch?.actId ?? ''
      if (i > 0 && actId !== prevActId) result.push(i)
      prevActId = actId
    }
    return result
  }, [rhythms, chapters])

  const intensityPath = useMemo(() => {
    if (rhythms.length < 2) return ''
    return rhythms.map((r, i) => {
      const x = PAD_L + i * (BAR_W + GAP) + BAR_W / 2
      const y = PAD_T + CHART_H - (r.intensity / 10) * CHART_H
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`
    }).join(' ')
  }, [rhythms])

  const handleBarClick = useCallback((index: number) => {
    const r = rhythms[index]
    const ch = chapters[r.chapterIndex]
    setEditChapter({
      id: r.chapterId,
      title: ch?.title || r.label,
      values: { action: r.action, suspense: r.suspense, emotion: r.emotion, humor: r.humor, intensity: r.intensity },
    })
    onSelectChapter(index)
  }, [rhythms, chapters, onSelectChapter])

  return (
    <div className="h-full w-full flex flex-col overflow-auto p-4">
      {/* Chart */}
      <div className="flex-1 min-h-0 overflow-x-auto">
        <svg width={totalW} height={PAD_T + CHART_H + PAD_B} className="shrink-0">
          {/* Y axis grid lines */}
          {[0, 2, 4, 6, 8, 10].map(v => (
            <g key={v}>
              <line x1={PAD_L} y1={PAD_T + CHART_H - (v / 10) * CHART_H} x2={totalW - PAD_R} y2={PAD_T + CHART_H - (v / 10) * CHART_H} stroke="#1f2937" strokeDasharray="3 3" />
              <text x={PAD_L - 8} y={PAD_T + CHART_H - (v / 10) * CHART_H + 4} fill="#6b7280" fontSize="10" textAnchor="end">{v}</text>
            </g>
          ))}

          {/* Act separators */}
          {actBoundaries.map(bi => {
            const x = PAD_L + bi * (BAR_W + GAP)
            return (
              <g key={bi}>
                <line x1={x} y1={PAD_T} x2={x} y2={PAD_T + CHART_H} stroke="#f59e0b" strokeDasharray="6 4" strokeWidth={1} opacity={0.5} />
                <text x={x} y={PAD_T + CHART_H + 14} fill="#f59e0b" fontSize="9" textAnchor="middle" opacity={0.5}>幕</text>
              </g>
            )
          })}

          {/* Bars */}
          {rhythms.map((r, i) => {
            const barX = PAD_L + i * (BAR_W + GAP)
            const isSelected = selectedIndex === i
            const segH = CHART_H / 4
            return (
              <g key={i} onClick={() => handleBarClick(i)} className="cursor-pointer">
                {DIM_COLORS.map((color, di) => {
                  const vals = [r.action, r.suspense, r.emotion, r.humor]
                  const val = vals[di]
                  const h = (val / 10) * CHART_H
                  return (
                    <rect
                      key={di}
                      x={barX + di * (BAR_W / 4)}
                      y={PAD_T + CHART_H - h}
                      width={BAR_W / 4 - 1}
                      height={h}
                      fill={color}
                      opacity={isSelected ? 1 : 0.7}
                      rx={0}
                    />
                  )
                })}
                {/* Intensity dot + line overlay */}
                <circle cx={barX + BAR_W / 2} cy={PAD_T + CHART_H - (r.intensity / 10) * CHART_H} r={4} fill="#fbbf24" stroke="#111" strokeWidth={1.5} />
                {/* Chapter label */}
                <text x={barX + BAR_W / 2} y={PAD_T + CHART_H + 14} fill={isSelected ? '#fbbf24' : '#9ca3af'} fontSize="10" textAnchor="middle">{r.label}</text>
              </g>
            )
          })}

          {/* Intensity connecting line */}
          {rhythms.length > 1 && (
            <path d={intensityPath} fill="none" stroke="#fbbf24" strokeWidth={2} strokeDasharray="5 3" opacity={0.5} />
          )}
        </svg>

        {/* Legend */}
        <div className="flex items-center gap-3 mt-1 ml-14">
          {DIM_COLORS.map((c, i) => (
            <div key={c} className="flex items-center gap-1 text-[10px] text-gray-500">
              <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: c }} />
              {DIM_LABELS[i]}
            </div>
          ))}
          <div className="flex items-center gap-1 text-[10px] text-gray-500">
            <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            综合强度
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="shrink-0 mt-4 border-t border-gray-800 pt-3">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 border-b border-gray-800">
              <th className="text-left py-1.5 px-2 font-medium">章节</th>
              <th className="text-right py-1.5 px-2 font-medium">字数</th>
              <th className="text-center py-1.5 px-2 font-medium">强度</th>
              <th className="text-left py-1.5 px-2 font-medium">节奏分析</th>
            </tr>
          </thead>
          <tbody>
            {rhythms.map((r, i) => {
              const ch = chapters[r.chapterIndex]
              const words = ch?.wordCount ?? 0
              const isSelected = selectedIndex === i
              return (
                <tr
                  key={i}
                  onClick={() => handleBarClick(i)}
                  className={`cursor-pointer border-b border-gray-800/50 transition-colors ${isSelected ? 'bg-amber-600/10 text-amber-300' : 'text-gray-400 hover:bg-gray-800/30'}`}
                >
                  <td className="py-1.5 px-2">{r.label}</td>
                  <td className="text-right py-1.5 px-2">{words > 0 ? `${words}` : '未开始'}</td>
                  <td className="text-center py-1.5 px-2">
                    <span className="px-1.5 py-0.5 rounded-full bg-amber-600/20 text-amber-400 text-[10px]">{r.intensity}</span>
                  </td>
                  <td className="py-1.5 px-2 text-[11px]">{paceNote(words, r.intensity)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {editChapter && (
        <RhythmEditPanel
          chapterTitle={editChapter.title}
          initialValues={editChapter.values}
          onSave={(values) => {
            onSaveRhythm(editChapter.id, values)
            setEditChapter(null)
          }}
          onClose={() => setEditChapter(null)}
        />
      )}
    </div>
  )
}
