import { useState, useEffect } from 'react'
import type { Scene } from '../types'

interface SceneEditorProps {
  scene: Scene | null
  chapterTitle: string
  onClose: () => void
  onSave: (sceneId: string, content: string) => void
}

export default function SceneEditor({ scene, chapterTitle, onClose, onSave }: SceneEditorProps) {
  const [content, setContent] = useState('')

  useEffect(() => {
    if (scene) setContent(scene.content)
  }, [scene])

  if (!scene) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-gray-900 border border-amber-700/50 rounded-2xl shadow-2xl w-[600px] max-w-[90vw] max-h-[85vh] flex flex-col p-6 backdrop-blur-xl" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-start mb-3">
          <div>
            <div className="text-xs text-gray-500 mb-0.5">{chapterTitle}</div>
            <h4 className="text-amber-600 font-medium">✎ {scene.title}</h4>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-lg">✕</button>
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 mb-3 pb-3 border-b border-gray-800">
          <span>🎭 {scene.povCharacter}</span>
          <span>📍 {scene.setting}</span>
          <span>⏰ {scene.time}</span>
          <span className="italic text-gray-600">—— {scene.summary}</span>
        </div>
        <textarea
          value={content}
          onChange={e => setContent(e.target.value)}
          className="flex-1 min-h-[300px] bg-gray-950 border border-gray-700 rounded-xl p-4 text-sm text-gray-200 font-mono leading-relaxed resize-none focus:outline-none focus:border-amber-600"
          placeholder="在这里写小说正文..."
        />
        <div className="flex gap-2 mt-3 justify-end">
          <button onClick={() => onSave(scene.id, content)} className="px-5 py-2 rounded-lg bg-amber-600 text-sm font-medium text-black hover:bg-amber-500 transition-colors">保存</button>
          <button onClick={onClose} className="px-5 py-2 rounded-lg bg-gray-800 text-sm text-gray-300 border border-gray-700 hover:bg-gray-700 transition-colors">取消</button>
        </div>
      </div>
    </div>
  )
}
