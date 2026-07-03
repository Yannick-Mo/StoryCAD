interface ActionButtonsProps {
  onPreview: () => void
  onExport: () => void
  onGlobalSetting: () => void
}

export default function ActionButtons({ onPreview, onExport, onGlobalSetting }: ActionButtonsProps) {
  return (
    <div className="absolute right-4 bottom-20 z-10 flex flex-col gap-2">
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
