import { useState } from 'react'
import type { Chapter } from '../types'

interface PreviewModalProps {
  open: boolean
  chapters: Chapter[]
  onClose: () => void
}

export default function PreviewModal({ open, chapters, onClose }: PreviewModalProps) {
  const [index, setIndex] = useState(0)
  const chapter = chapters[index]

  const prev = () => setIndex(i => Math.max(0, i - 1))
  const next = () => setIndex(i => Math.min(chapters.length - 1, i + 1))

  if (!open || !chapter) return null

  const fullContent = chapter.scenes
    .filter(s => s.content)
    .map(s => s.content)
    .join('\n\n')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl w-[600px] max-w-[90vw] max-h-[85vh] flex flex-col p-6 backdrop-blur-xl" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <div>
            <h3 className="text-amber-600 font-medium">{chapter.title}</h3>
            <div className="text-xs text-gray-500 mt-0.5">{chapter.goal} · {chapter.scenes.length} 场 · {chapter.wordCount} 字</div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-lg">✕</button>
        </div>
        <div className="flex-1 bg-gray-950 rounded-xl p-4 text-sm text-gray-300 leading-relaxed whitespace-pre-wrap border border-gray-800 min-h-[300px] mb-4 overflow-y-auto">
          {fullContent || '（内容待创作）'}
        </div>
        <div className="flex items-center justify-center gap-4">
          <button onClick={prev} disabled={index === 0} className="px-4 py-1.5 rounded-full text-sm bg-gray-800 text-amber-600 disabled:opacity-30 disabled:cursor-default hover:bg-gray-700 transition-colors">◀ 上一章</button>
          <span className="text-xs text-gray-500">{index + 1} / {chapters.length}</span>
          <button onClick={next} disabled={index >= chapters.length - 1} className="px-4 py-1.5 rounded-full text-sm bg-gray-800 text-amber-600 disabled:opacity-30 disabled:cursor-default hover:bg-gray-700 transition-colors">下一章 ▶</button>
        </div>
      </div>
    </div>
  )
}
