import { useState } from 'react'

interface RhythmEditPanelProps {
  chapterTitle: string
  initialValues: { action: number; suspense: number; emotion: number; humor: number; intensity: number }
  onSave: (values: { action: number; suspense: number; emotion: number; humor: number; intensity: number }) => void
  onClose: () => void
}

export function RhythmEditPanel({ chapterTitle, initialValues, onSave, onClose }: RhythmEditPanelProps) {
  const [action, setAction] = useState(initialValues.action)
  const [suspense, setSuspense] = useState(initialValues.suspense)
  const [emotion, setEmotion] = useState(initialValues.emotion)
  const [humor, setHumor] = useState(initialValues.humor)
  const intensity = Math.round((action + suspense + emotion + humor) / 4)

  const handleSave = () => {
    onSave({ action, suspense, emotion, humor, intensity })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-80" onClick={e => e.stopPropagation()}>
        <h3 className="text-white font-semibold mb-1">{chapterTitle}</h3>
        <p className="text-gray-400 text-sm mb-4">节奏维度编辑</p>
        <div className="space-y-3">
          <div>
            <label className="flex justify-between text-sm"><span style={{color:'#f97316'}}>动作</span><span>{action}</span></label>
            <input type="range" min="0" max="10" value={action} onChange={e => setAction(Number(e.target.value))} className="w-full accent-orange-500" />
          </div>
          <div>
            <label className="flex justify-between text-sm"><span style={{color:'#3b82f6'}}>悬疑</span><span>{suspense}</span></label>
            <input type="range" min="0" max="10" value={suspense} onChange={e => setSuspense(Number(e.target.value))} className="w-full accent-blue-500" />
          </div>
          <div>
            <label className="flex justify-between text-sm"><span style={{color:'#ec4899'}}>情感</span><span>{emotion}</span></label>
            <input type="range" min="0" max="10" value={emotion} onChange={e => setEmotion(Number(e.target.value))} className="w-full accent-pink-500" />
          </div>
          <div>
            <label className="flex justify-between text-sm"><span style={{color:'#22c55e'}}>幽默</span><span>{humor}</span></label>
            <input type="range" min="0" max="10" value={humor} onChange={e => setHumor(Number(e.target.value))} className="w-full accent-green-500" />
          </div>
        </div>
        <div className="mt-4 pt-3 border-t border-gray-700">
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">强度指数</span>
            <span className="text-white font-bold">{intensity}/10</span>
          </div>
          <div className="h-2 bg-gray-700 rounded mt-1 overflow-hidden">
            <div className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded transition-all" style={{ width: `${intensity * 10}%` }} />
          </div>
        </div>
        <div className="flex gap-2 mt-4">
          <button onClick={onClose} className="flex-1 px-3 py-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600">取消</button>
          <button onClick={handleSave} className="flex-1 px-3 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-500">保存</button>
        </div>
      </div>
    </div>
  )
}
