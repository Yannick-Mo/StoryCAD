import { useState, useEffect, useRef } from 'react'

interface GlobalSettingsModalProps {
  open: boolean
  initialText: string
  onSave: (text: string) => void
  onClose: () => void
}

export default function GlobalSettingsModal({ open, initialText, onSave, onClose }: GlobalSettingsModalProps) {
  const [text, setText] = useState(initialText)
  const textRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (open) setText(initialText)
  }, [open, initialText])

  useEffect(() => {
    if (open) textRef.current?.focus()
  }, [open])

  const handleSave = () => {
    onSave(text)
    onClose()
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl w-[700px] max-w-[90vw] max-h-[85vh] flex flex-col p-6 backdrop-blur-xl" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <div>
            <h3 className="text-amber-600 font-medium text-base">🌐 全局设定</h3>
            <p className="text-xs text-gray-500 mt-0.5">记录世界观、地理、势力、年表等任何参考信息</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-lg">✕</button>
        </div>
        <textarea
          ref={textRef}
          value={text}
          onChange={e => setText(e.target.value)}
          className="flex-1 bg-gray-950 border border-gray-700 rounded-xl p-4 text-sm text-gray-300 leading-relaxed resize-none focus:outline-none focus:border-amber-600/50 font-mono min-h-[300px]"
          placeholder={`在此记录你的世界设定...

例如：
■ 世界观：这是一个剑与魔法的世界，三大种族共存
■ 主要大陆：艾泽拉斯（中部）、卡利姆多（西部）...
■ 势力格局：联盟 vs 部落...
■ 重要年表：第1年 - 黑暗之门开启...
■ 魔法体系：分为奥术、自然、神圣、暗影四系...`}
        />
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-1.5 rounded-lg text-xs text-gray-400 hover:text-gray-200 bg-gray-800 hover:bg-gray-700 transition-colors">
            取消
          </button>
          <button onClick={handleSave} className="px-4 py-1.5 rounded-lg text-xs font-medium bg-amber-600 text-black hover:bg-amber-500 transition-colors">
            保存
          </button>
        </div>
      </div>
    </div>
  )
}
