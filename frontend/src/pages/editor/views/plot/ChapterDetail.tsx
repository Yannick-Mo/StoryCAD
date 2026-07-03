import { useState } from 'react'
import type { Chapter, Scene } from '../../types'

interface ChapterDetailProps {
  chapter: Chapter | null
  onClose: () => void
  onSceneSave: (chapterId: string, sceneId: string, content: string) => void
  onChapterSave: (chapterId: string, goal: string) => void
  onOpenSceneEditor?: (scene: Scene) => void
}

const STATUS_OPTIONS = [
  { value: 'draft' as const, label: '草稿' },
  { value: 'revising' as const, label: '修改' },
  { value: 'final' as const, label: '定稿' },
]

export default function ChapterDetail({ chapter, onClose, onSceneSave, onChapterSave, onOpenSceneEditor }: ChapterDetailProps) {
  const [editSceneId, setEditSceneId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')
  const [editGoal, setEditGoal] = useState('')

  if (!chapter) return null

  const totalWords = chapter.scenes.reduce((s, sc) => s + sc.wordCount, 0)

  const startEdit = (scene: Scene) => {
    setEditSceneId(scene.id)
    setEditContent(scene.content)
  }

  const saveScene = () => {
    if (editSceneId) {
      onSceneSave(chapter.id, editSceneId, editContent)
      setEditSceneId(null)
    }
  }

  return (
    <div className="absolute right-0 top-0 h-full w-96 bg-gray-900/95 backdrop-blur-xl border-l border-gray-800 z-20 flex flex-col shadow-2xl">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-medium text-amber-100">{chapter.title}</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-lg leading-none">✕</button>
        </div>
        <input
          value={editGoal || chapter.goal}
          onChange={e => setEditGoal(e.target.value)}
          onBlur={() => { if (editGoal !== chapter.goal) onChapterSave(chapter.id, editGoal || chapter.goal) }}
          placeholder="本章目标..."
          className="w-full bg-transparent text-xs text-gray-400 placeholder-gray-600 outline-none border-b border-transparent focus:border-amber-600/50 pb-0.5"
        />
        <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
          <span>{chapter.scenes.length} 场</span>
          <span>{totalWords > 0 ? `${totalWords} 字` : '未开始'}</span>
          <span className={`px-1.5 py-0.5 rounded text-[10px] ${
            chapter.status === 'final' ? 'bg-green-900/30 text-green-400' :
            chapter.status === 'revising' ? 'bg-amber-900/30 text-amber-400' :
            'bg-gray-800 text-gray-400'
          }`}>
            {STATUS_OPTIONS.find(s => s.value === chapter.status)?.label}
          </span>
        </div>
      </div>

      {/* Scene list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {chapter.scenes.map(scene => (
          <div key={scene.id} className="bg-gray-800/60 border border-gray-700/50 rounded-xl overflow-hidden">
            <div className="p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gray-200">{scene.title}</span>
                <span className="text-[10px] text-gray-500">{scene.wordCount > 0 ? `${scene.wordCount} 字` : '空'}</span>
              </div>
              <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-gray-500 mb-2">
                <span>🎭 {scene.povCharacter}</span>
                <span>📍 {scene.setting}</span>
                <span>⏰ {scene.time}</span>
              </div>
              <div className="text-[11px] text-gray-400 italic mb-2 line-clamp-2">{scene.summary}</div>
              {editSceneId === scene.id ? (
                <div className="space-y-2">
                  <textarea
                    value={editContent}
                    onChange={e => setEditContent(e.target.value)}
                    className="w-full h-32 bg-gray-950 border border-gray-700 rounded-lg p-2 text-xs text-gray-300 resize-none focus:outline-none focus:border-amber-600 font-mono leading-relaxed"
                    placeholder="在这里写小说正文..."
                  />
                  <div className="flex gap-2">
                    <button onClick={saveScene} className="px-3 py-1 rounded-lg bg-amber-600 text-xs font-medium text-black hover:bg-amber-500 transition-colors">保存</button>
                    <button onClick={() => setEditSceneId(null)} className="px-3 py-1 rounded-lg bg-gray-700 text-xs text-gray-300 hover:bg-gray-600 transition-colors">取消</button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => startEdit(scene)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
                    scene.content
                      ? 'bg-gray-950/50 text-gray-400 hover:bg-gray-800 border border-gray-800'
                      : 'bg-gray-800/30 text-gray-600 hover:bg-gray-700 border border-dashed border-gray-700'
                  }`}
                >
                  {scene.content
                    ? <span className="line-clamp-3 font-mono leading-relaxed">{scene.content}</span>
                    : '✏️ 点击开始写作...'}
                </button>
              )}
              {editSceneId !== scene.id && (
                <button
                  onClick={(e) => { e.stopPropagation(); onOpenSceneEditor?.(scene) }}
                  className="w-full mt-1 px-2 py-1 rounded text-[10px] text-gray-600 hover:text-gray-400 hover:bg-gray-700/50 transition-colors text-center"
                >
                  全屏编辑 ↗
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
