import { useState } from 'react'

interface ActionButtonsProps {
  onPreview: () => void
  onExport: () => void
  onGlobalSetting: () => void
  onAIChat: () => void
  onInspiration: () => void
  onRhythmAnalysis: () => void
  onConsistencyCheck: () => void
}

export default function ActionButtons({
  onPreview, onExport, onGlobalSetting,
  onAIChat, onInspiration, onRhythmAnalysis, onConsistencyCheck
}: ActionButtonsProps) {
  const [aiMenuOpen, setAiMenuOpen] = useState(false)

  const aiItems = [
    { label: '💬 AI 对话', action: onAIChat },
    { label: '✨ 灵感生成', action: onInspiration },
    { label: '📊 节奏分析', action: onRhythmAnalysis },
    { label: '✅ 一致性检查', action: onConsistencyCheck },
  ]

  return (
    <div className="absolute right-4 bottom-[188px] z-10 flex flex-col items-end gap-2">
      {/* AI main button (larger, above others) */}
      <div className="relative">
        <button
          onClick={() => setAiMenuOpen(!aiMenuOpen)}
          className="flex items-center gap-1.5 px-4 py-2 rounded-full text-sm bg-gradient-to-r from-amber-700/80 to-amber-600/80 border border-amber-500/50 text-white hover:from-amber-600 hover:to-amber-500 transition-all backdrop-blur-sm shadow-lg shadow-amber-900/20"
        >
          🤖 AI
        </button>
        {aiMenuOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setAiMenuOpen(false)} />
            <div className="absolute bottom-full mb-2 right-0 z-50 w-44 bg-gray-900/95 border border-gray-700 rounded-xl overflow-hidden shadow-xl backdrop-blur-sm">
              {aiItems.map((item) => (
                <button
                  key={item.label}
                  onClick={() => { setAiMenuOpen(false); item.action() }}
                  className="w-full text-left px-4 py-2.5 text-sm text-gray-200 hover:bg-amber-600/20 hover:text-amber-400 transition-colors"
                >
                  {item.label}
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Existing buttons */}
      <button onClick={onPreview} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs bg-gray-800/80 border border-gray-700 text-gray-300 hover:border-amber-600 hover:text-amber-400 transition-colors backdrop-blur-sm">
        📄 预览已完成内容
      </button>
      <button onClick={onExport} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs bg-gray-800/80 border border-gray-700 text-gray-300 hover:border-amber-600 hover:text-amber-400 transition-colors backdrop-blur-sm">
        ⬇️ 导出完整内容
      </button>
      <button onClick={onGlobalSetting} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs bg-gray-800/80 border border-amber-800/50 text-amber-600 hover:bg-amber-900/20 hover:border-amber-600 transition-colors backdrop-blur-sm">
        📜 全局设定
      </button>
    </div>
  )
}
