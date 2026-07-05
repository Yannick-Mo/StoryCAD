import { useCallback } from 'react'
import type { ThemeItem, Chapter } from '../../types'

interface ThemeCanvasProps {
  themes: ThemeItem[]
  chapters: Chapter[]
  selected: { themeIndex: number; chapterIndex: number } | null
  onSelect: (themeIndex: number, chapterIndex: number) => void
}

export default function ThemeCanvas({ themes, chapters, selected, onSelect }: ThemeCanvasProps) {
  const handleClick = useCallback((themeIdx: number) => {
    onSelect(themeIdx, -1)
  }, [onSelect])

  return (
    <div className="h-full w-full overflow-auto p-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl">
        {themes.map((t, tIdx) => {
          const chaptersForTheme = t.chapterIndices.map(i => chapters[i]).filter(Boolean)
          const isSelected = selected?.themeIndex === tIdx
          return (
            <div
              key={t.name}
              onClick={() => handleClick(tIdx)}
              className={`bg-gray-900/80 border rounded-2xl p-5 cursor-pointer transition-all hover:-translate-y-1 ${
                isSelected ? 'ring-2 ring-blue-500 shadow-[0_0_20px_rgba(59,130,246,0.15)]' : 'border-gray-800 hover:border-gray-700'
              }`}
              style={{ borderLeft: `4px solid ${t.color}` }}
            >
              {/* Header */}
              <h3 className="text-lg font-bold mb-1" style={{ color: t.color }}>{t.name}</h3>
              <p className="text-xs text-gray-400 leading-relaxed line-clamp-2 mb-4">{t.proposition}</p>

              {/* Chapter tags */}
              <div className="mb-3">
                <div className="text-[10px] text-gray-600 mb-1.5 uppercase tracking-wider">出现章节</div>
                <div className="flex flex-wrap gap-1.5">
                  {chaptersForTheme.length > 0 ? chaptersForTheme.map(ch => (
                    <span
                      key={ch.id}
                      onClick={(e) => { e.stopPropagation(); onSelect(tIdx, t.chapterIndices[chaptersForTheme.indexOf(ch)]) }}
                      className="px-2 py-0.5 rounded-full text-[10px] bg-gray-800 text-gray-300 hover:bg-gray-700 cursor-pointer transition-colors"
                    >{ch.title}</span>
                  )) : <span className="text-[10px] text-gray-600">暂无</span>}
                </div>
              </div>

              {/* Connection tags */}
              {t.connections.length > 0 && (
                <div>
                  <div className="text-[10px] text-gray-600 mb-1.5 uppercase tracking-wider">关联主题</div>
                  <div className="flex flex-wrap gap-1.5">
                    {t.connections.map(name => (
                      <span key={name} className="px-2 py-0.5 rounded-full text-[10px] bg-gray-800/50 text-gray-500">#{name}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
