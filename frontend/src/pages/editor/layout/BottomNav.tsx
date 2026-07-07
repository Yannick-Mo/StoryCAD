import { useState } from 'react'
import { VIEWS } from '../types'

interface BottomNavProps {
  activeViewId: string
  onSwitchView: (viewId: string) => void
  onPreview: () => void
  onExport: () => void
  onGlobalSetting: () => void
}

export default function BottomNav({
  activeViewId, onSwitchView, onPreview, onExport, onGlobalSetting,
}: BottomNavProps) {
  const [mgmtOpen, setMgmtOpen] = useState(false)

  return (
    <nav className="h-14 bg-gray-900/95 backdrop-blur-xl border-t border-gray-800 flex items-center justify-center gap-2 px-4 relative">
      {VIEWS.map(v => (
        <button
          key={v.id}
          onClick={() => onSwitchView(v.id)}
          className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full transition-colors ${
            activeViewId === v.id
              ? 'bg-amber-500/15 text-amber-400'
              : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
          }`}
        >
          <span>{v.icon}</span>
          <span className="text-xs font-medium">{v.label}</span>
        </button>
      ))}

      <div className="w-px h-6 bg-gray-800" />

      {/* 内容管理 */}
      <div className="relative">
        <button onClick={() => setMgmtOpen(!mgmtOpen)}
          className="flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs text-gray-500 hover:text-gray-300 hover:bg-gray-800 transition-colors">📂 内容管理</button>
        {mgmtOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setMgmtOpen(false)} />
            <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 z-50 w-44 bg-gray-900/95 border border-gray-700 rounded-xl overflow-hidden shadow-xl backdrop-blur-sm">
              <button onClick={() => { setMgmtOpen(false); onPreview() }}
                className="w-full text-left px-4 py-2.5 text-sm text-gray-200 hover:bg-amber-600/20 hover:text-amber-400 transition-colors">📄 预览已完成内容</button>
              <button onClick={() => { setMgmtOpen(false); onExport() }}
                className="w-full text-left px-4 py-2.5 text-sm text-gray-200 hover:bg-amber-600/20 hover:text-amber-400 transition-colors">⬇️ 导出完整内容</button>
            </div>
          </>
        )}
      </div>

      <button onClick={onGlobalSetting}
        className="flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs text-gray-500 hover:text-gray-300 hover:bg-gray-800 transition-colors">📜 全局设定</button>
    </nav>
  )
}
