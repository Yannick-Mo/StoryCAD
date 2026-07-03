import { useState } from 'react'
import type { Act, Chapter, Scene } from '../../types'

interface ActDetailProps {
  act: Act
  chapters: Chapter[]
  onClose: () => void
  onSelectChapter: (chapterId: string) => void
  onSceneSave: (chapterId: string, sceneId: string, content: string) => void
  onOpenSceneEditor?: (scene: Scene) => void
}

const STATUS_OPTIONS = [
  { value: 'draft' as const, label: '草稿' },
  { value: 'revising' as const, label: '修改' },
  { value: 'final' as const, label: '定稿' },
]

export default function ActDetail({ act, chapters, onClose, onSelectChapter, onSceneSave, onOpenSceneEditor }: ActDetailProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [editSceneId, setEditSceneId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')

  const totalWords = chapters.reduce((s, c) => s + c.wordCount, 0)
  const totalScenes = chapters.reduce((s, c) => s + c.scenes.length, 0)

  const toggleExpand = (chId: string) => {
    setExpandedId(expandedId === chId ? null : chId)
    setEditSceneId(null)
  }

  const startEdit = (scene: Scene) => {
    setEditSceneId(scene.id)
    setEditContent(scene.content)
  }

  const saveScene = (chapterId: string) => {
    if (editSceneId) {
      onSceneSave(chapterId, editSceneId, editContent)
      setEditSceneId(null)
    }
  }

  return (
    <div className="absolute right-0 top-0 h-full w-96 bg-gray-900/95 backdrop-blur-xl border-l border-gray-800 z-20 flex flex-col shadow-2xl">
      <div className="p-4 border-b border-gray-800" style={{ borderLeft: `3px solid ${act.color}` }}>
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-medium text-amber-100">{act.name}</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-lg leading-none">✕</button>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>{chapters.length} 章</span>
          <span>{totalScenes} 场</span>
          <span>{totalWords > 0 ? `${totalWords} 字` : '未开始'}</span>
          <span className="text-gray-600">
            {chapters.filter(c => c.status === 'final').length}/{chapters.length} 完成
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
        {chapters.map(ch => {
          const isExpanded = expandedId === ch.id
          return (
            <div key={ch.id} className="bg-gray-800/40 border border-gray-700/40 rounded-xl overflow-hidden">
              <button
                onClick={() => toggleExpand(ch.id)}
                className="w-full flex items-center gap-2 px-3 py-2.5 hover:bg-gray-700/30 transition-colors text-left"
              >
                <span className="text-xs text-gray-500 w-4 shrink-0">{isExpanded ? '▾' : '▸'}</span>
                <span className="text-sm font-medium text-gray-200 flex-1 truncate">{ch.title}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                  ch.status === 'final' ? 'bg-green-900/30 text-green-400' :
                  ch.status === 'revising' ? 'bg-amber-900/30 text-amber-400' :
                  'bg-gray-800 text-gray-500'
                }`}>{STATUS_OPTIONS.find(s => s.value === ch.status)?.label}</span>
                <span className="text-[10px] text-gray-600 w-10 text-right">{ch.wordCount > 0 ? `${ch.wordCount}w` : '-'}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); onSelectChapter(ch.id) }}
                  className="text-[10px] text-gray-600 hover:text-amber-400 transition-colors px-1"
                  title="聚焦到本章"
                >🔍</button>
              </button>

              {isExpanded && (
                <div className="px-3 pb-3 space-y-2 border-t border-gray-700/30 pt-2">
                  {ch.scenes.map(scene => (
                    <div key={scene.id} className="bg-gray-800/60 border border-gray-700/40 rounded-lg p-2.5">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-gray-300">{scene.title}</span>
                        <span className="text-[10px] text-gray-600">{scene.wordCount > 0 ? `${scene.wordCount}字` : '空'}</span>
                      </div>
                      <div className="flex flex-wrap gap-x-2 gap-y-0.5 text-[10px] text-gray-600 mb-1.5">
                        <span>🎭 {scene.povCharacter}</span>
                        <span>📍 {scene.setting}</span>
                        <span>⏰ {scene.time}</span>
                      </div>
                      {editSceneId === scene.id ? (
                        <div className="space-y-1.5">
                          <textarea
                            value={editContent}
                            onChange={e => setEditContent(e.target.value)}
                            className="w-full h-28 bg-gray-950 border border-gray-700 rounded-lg p-2 text-xs text-gray-300 resize-none focus:outline-none focus:border-amber-600 font-mono leading-relaxed"
                            placeholder="写小说正文..."
                          />
                          <div className="flex gap-2">
                            <button onClick={() => saveScene(ch.id)} className="px-3 py-1 rounded-lg bg-amber-600 text-xs font-medium text-black hover:bg-amber-500 transition-colors">保存</button>
                            <button onClick={() => setEditSceneId(null)} className="px-3 py-1 rounded-lg bg-gray-700 text-xs text-gray-300 hover:bg-gray-600 transition-colors">取消</button>
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => startEdit(scene)}
                          className={`w-full text-left px-2.5 py-2 rounded-lg text-xs transition-colors ${
                            scene.content
                              ? 'bg-gray-950/50 text-gray-400 hover:bg-gray-800 border border-gray-800'
                              : 'bg-gray-800/30 text-gray-600 hover:bg-gray-700 border border-dashed border-gray-700'
                          }`}
                        >
                          {scene.content
                            ? <span className="line-clamp-2 font-mono leading-relaxed">{scene.content}</span>
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
                  ))}
                </div>
              )}
            </div>
          )
        })}
        {chapters.length === 0 && (
          <div className="text-center text-gray-600 text-sm py-8">该幕暂无章节</div>
        )}
      </div>
    </div>
  )
}
