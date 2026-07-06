// frontend/src/pages/editor/modals/AiAssistModal.tsx
import { useState } from 'react'
import type { Chapter } from '../types'
import { generateAI } from '../../../api/ai'
import type { GoalResult, OutlineResult, WritingResult, SceneOutlineItem } from '../../../api/ai'

const MODE_LABELS: Record<string, string> = {
  goal: '生成章节目标',
  outline: '生成场景大纲',
  writing: '辅助写作',
}

const MODE_PLACEHOLDERS: Record<string, string> = {
  goal: '可选：补充对章节的额外说明...',
  outline: '可选：补充你的规划偏好...',
  writing: '描述你的写作需求，AI 将根据上下文生成内容...',
}

interface Props {
  mode: 'goal' | 'outline' | 'writing'
  projectId: string
  chapter: Chapter
  onClose: () => void
  onApplyGoal?: (goal: string) => void
  onApplyOutlines?: (outlines: SceneOutlineItem[]) => void
}

export default function AiAssistModal({ mode, projectId, chapter, onClose, onApplyGoal, onApplyOutlines }: Props) {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<GoalResult | OutlineResult | WritingResult | null>(null)
  const [applied, setApplied] = useState(false)

  const handleGenerate = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await generateAI(projectId, {
        chapter_id: chapter.id,
        mode,
        prompt: prompt.trim(),
      })
      setResult(data)
    } catch (e: any) {
      setError(e.message || '生成失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  const renderResult = () => {
    if (!result) return null

    if (mode === 'goal') {
      const r = result as GoalResult
      return (
        <div className="space-y-3">
          <div>
            <div className="text-[10px] text-amber-500/80 mb-1">分析</div>
            <p className="text-xs text-gray-300 leading-relaxed">{r.reasoning}</p>
          </div>
          <div>
            <div className="text-[10px] text-amber-500/80 mb-1">目标</div>
            <p className="text-sm text-amber-100 leading-relaxed bg-gray-800/60 rounded-lg p-3">{r.goal}</p>
          </div>
          {onApplyGoal && (
            <button
              onClick={() => { onApplyGoal(r.goal); setApplied(true) }}
              disabled={applied}
              className={`w-full px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                applied
                  ? 'bg-green-900/40 text-green-400'
                  : 'bg-amber-600 text-black hover:bg-amber-500'
              }`}
            >
              {applied ? '已应用' : '应用到章节'}
            </button>
          )}
        </div>
      )
    }

    if (mode === 'outline') {
      const r = result as OutlineResult
      return (
        <div className="space-y-3">
          <div>
            <div className="text-[10px] text-amber-500/80 mb-1">规划思路</div>
            <p className="text-xs text-gray-300 leading-relaxed">{r.planning}</p>
          </div>
          <div>
            <div className="text-[10px] text-amber-500/80 mb-1">
              场景列表 ({r.scenes.length})
            </div>
            <div className="space-y-2">
              {r.scenes.map((sc, i) => (
                <div key={i} className="bg-gray-800/60 rounded-lg p-2.5 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-500 w-4">{i + 1}</span>
                    <span className="text-xs font-medium text-gray-200">{sc.title}</span>
                  </div>
                  <div className="flex gap-3 text-[10px] text-gray-500 ml-6">
                    <span> {sc.pov_character}</span>
                    <span> {sc.setting}</span>
                    <span> {sc.scene_time}</span>
                  </div>
                  <p className="text-[11px] text-gray-400 ml-6">{sc.summary}</p>
                </div>
              ))}
            </div>
          </div>
          {onApplyOutlines && (
            <button
              onClick={() => { onApplyOutlines(r.scenes); setApplied(true) }}
              disabled={applied}
              className={`w-full px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                applied
                  ? 'bg-green-900/40 text-green-400'
                  : 'bg-amber-600 text-black hover:bg-amber-500'
              }`}
            >
              {applied ? '已添加' : '添加场景到章节'}
            </button>
          )}
        </div>
      )
    }

    if (mode === 'writing') {
      const r = result as WritingResult
      return (
        <div className="space-y-3">
          {r.note && (
            <div className="text-[10px] text-amber-500/80 mb-1">AI 备注</div>
          )}
          {r.note && <p className="text-[11px] text-gray-400 italic">{r.note}</p>}
          <div>
            <div className="text-[10px] text-amber-500/80 mb-1">生成内容</div>
            <div className="bg-gray-800/60 rounded-lg p-3 text-xs text-gray-300 leading-relaxed max-h-64 overflow-y-auto whitespace-pre-wrap font-mono">
              {r.content}
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => navigator.clipboard.writeText(r.content)}
              className="flex-1 px-3 py-1.5 rounded-lg bg-gray-700 text-xs text-gray-300 hover:bg-gray-600 transition-colors"
            >
              复制到剪贴板
            </button>
          </div>
        </div>
      )
    }
  }

  return (
    <div className="absolute inset-0 bg-gray-950/80 backdrop-blur-sm z-50 flex items-end">
      <div className="w-full max-h-[85%] overflow-y-auto bg-gray-900 border-t border-gray-800 rounded-t-2xl p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium text-amber-100">
            {MODE_LABELS[mode]}
          </h4>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-lg">✕</button>
        </div>

        <details className="text-xs text-gray-500">
          <summary className="cursor-pointer hover:text-gray-400 select-none">
            上下文预览 · {chapter.title} · {chapter.status} · {chapter.scenes.length}场 · {chapter.scenes.reduce((s, sc) => s + sc.wordCount, 0)}字
          </summary>
          <div className="mt-2 space-y-1 text-gray-500">
            <div>目标：{chapter.goal || '未设定'}</div>
            <div>场景：{chapter.scenes.map(s => s.title).join('、') || '无'}</div>
          </div>
        </details>

        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder={MODE_PLACEHOLDERS[mode]}
          disabled={loading}
          className="w-full h-20 bg-gray-950 border border-gray-700 rounded-xl p-3 text-xs text-gray-300 resize-none focus:outline-none focus:border-amber-600 leading-relaxed disabled:opacity-50"
        />

        <div className="flex gap-2">
          <button
            onClick={handleGenerate}
            disabled={loading}
            className={`flex-1 px-4 py-2 rounded-xl text-xs font-medium text-black transition-colors ${
              loading ? 'bg-amber-800 animate-pulse' : 'bg-amber-600 hover:bg-amber-500'
            }`}
          >
            {loading ? '生成中...' : '生成'}
          </button>
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 rounded-xl bg-gray-800 text-xs text-gray-400 hover:bg-gray-700 transition-colors disabled:opacity-50"
          >
            取消
          </button>
        </div>

        {error && (
          <div className="bg-red-900/20 border border-red-800/30 rounded-lg p-3">
            <p className="text-xs text-red-400">{error}</p>
          </div>
        )}

        {result && !error && (
          <div className="border-t border-gray-800 pt-3">
            {renderResult()}
          </div>
        )}
      </div>
    </div>
  )
}
