import { useCallback } from 'react'
import type { ThemeItem, Chapter } from '../../types'

interface ThemeCanvasProps {
  themes: ThemeItem[]
  chapters: Chapter[]
  selected: { themeIndex: number; chapterIndex: number } | null
  onSelect: (themeIndex: number, chapterIndex: number) => void
}

export default function ThemeCanvas({ themes, chapters, selected, onSelect }: ThemeCanvasProps) {
  const handleCellClick = useCallback((themeIdx: number, chIdx: number) => {
    onSelect(themeIdx, chIdx)
  }, [onSelect])

  return (
    <div className="h-full w-full overflow-auto p-4">
      {/* Legend */}
      <div className="flex items-center gap-4 mb-6 flex-wrap">
        {themes.map((t, i) => (
          <div key={t.name} className="flex items-center gap-1.5 text-xs">
            <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: t.color }} />
            <span style={{ color: t.color }}>#{t.name}</span>
            <span className="text-gray-600">— {t.proposition.slice(0, 20)}...</span>
          </div>
        ))}
      </div>

      {/* Matrix */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="text-left py-2 px-3 text-xs text-gray-500 font-medium border-b border-gray-800 sticky left-0 bg-gray-950 z-10">章节</th>
              {themes.map(t => (
                <th key={t.name} className="text-center py-2 px-4 text-xs font-medium border-b border-gray-800" style={{ color: t.color }}>
                  #{t.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {chapters.map((ch, chIdx) => (
              <tr key={ch.id} className="border-b border-gray-800/50 hover:bg-gray-800/20 transition-colors">
                <td className="py-2.5 px-3 sticky left-0 bg-gray-950/90">
                  <div className="text-sm text-gray-200 truncate max-w-[140px]">{ch.title}</div>
                  <div className="text-[10px] text-gray-600">{ch.wordCount > 0 ? `${ch.wordCount} 字` : '未开始'}</div>
                </td>
                {themes.map((t, tIdx) => {
                  const isChecked = t.chapterIndices.includes(chIdx)
                  const isSel = selected?.themeIndex === tIdx && selected?.chapterIndex === chIdx
                  return (
                    <td
                      key={t.name}
                      onClick={() => handleCellClick(tIdx, chIdx)}
                      className={`text-center py-2.5 px-4 cursor-pointer transition-colors ${isSel ? 'bg-blue-600/10' : ''}`}
                    >
                      <div
                        className={`w-5 h-5 rounded mx-auto transition-all ${isChecked ? 'scale-100 opacity-100' : 'scale-75 opacity-20'}`}
                        style={{ backgroundColor: isChecked ? t.color : '#374151' }}
                      />
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
