import type { SelectionState } from '../../types'

interface PlotToolbarProps {
  selection: SelectionState
  selectedActId: string | null
  edgeFilter: 'all' | 'timeline' | 'relation'
  onAddAct: () => void
  onAddChapter: () => void
  onDeleteSelected: () => void
  onRenameAct: () => void
  onEditChapterGoal: () => void
  onDisconnectTimeline: () => void
  onEdgeFilterChange: (filter: 'all' | 'timeline' | 'relation') => void
  onLayout: () => void
  onExport: () => void
}

export default function PlotToolbar({
  selection, selectedActId, edgeFilter,
  onAddAct, onAddChapter, onDeleteSelected,
  onRenameAct, onEditChapterGoal, onDisconnectTimeline,
  onEdgeFilterChange, onLayout, onExport,
}: PlotToolbarProps) {
  const show = selection.type

  return (
    <div className="absolute top-3 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1.5 bg-gray-900/90 backdrop-blur-lg border border-gray-700/50 rounded-xl px-3 py-1.5 shadow-xl">
      <button onClick={onAddAct} className="px-2.5 py-1 rounded-lg text-xs text-gray-300 hover:bg-amber-600/20 hover:text-amber-400 transition-colors" title="添加幕">＋幕</button>
      <button
        onClick={onAddChapter}
        disabled={!selectedActId}
        className={`px-2.5 py-1 rounded-lg text-xs transition-colors ${selectedActId ? 'text-gray-300 hover:bg-amber-600/20 hover:text-amber-400' : 'text-gray-600 cursor-not-allowed'}`}
      >＋章</button>

      {show === 'act' && (<>
        <div className="w-px h-5 bg-gray-700/50 mx-1" />
        <button onClick={onRenameAct} className="px-2.5 py-1 rounded-lg text-xs text-gray-300 hover:bg-blue-600/20 hover:text-blue-400 transition-colors">✎ 重命名</button>
        <button onClick={onDeleteSelected} className="px-2.5 py-1 rounded-lg text-xs text-red-400 hover:bg-red-600/20 transition-colors">✕ 删除幕</button>
      </>)}

      {show === 'chapter' && (<>
        <div className="w-px h-5 bg-gray-700/50 mx-1" />
        <button onClick={onEditChapterGoal} className="px-2.5 py-1 rounded-lg text-xs text-gray-300 hover:bg-blue-600/20 hover:text-blue-400 transition-colors">✎ 编辑目标</button>
        <button onClick={onDeleteSelected} className="px-2.5 py-1 rounded-lg text-xs text-red-400 hover:bg-red-600/20 transition-colors">✕ 删除章</button>
        <button onClick={onDisconnectTimeline} className="px-2.5 py-1 rounded-lg text-xs text-amber-400 hover:bg-amber-600/20 transition-colors">⊘ 断开时序</button>
      </>)}

      {show === 'edge' && (<>
        <div className="w-px h-5 bg-gray-700/50 mx-1" />
        <button onClick={onDeleteSelected} className="px-2.5 py-1 rounded-lg text-xs text-red-400 hover:bg-red-600/20 transition-colors">✕ 删除连线</button>
      </>)}

      <div className="w-px h-5 bg-gray-700/50 mx-1" />
      <select value={edgeFilter} onChange={e => onEdgeFilterChange(e.target.value as any)}
        className="bg-transparent text-xs text-gray-400 border border-gray-700 rounded px-1.5 py-1 outline-none cursor-pointer"
      >
        <option value="all">全部连线</option>
        <option value="timeline">仅时序</option>
        <option value="relation">仅关系</option>
      </select>
      <button onClick={onLayout} className="px-2.5 py-1 rounded-lg text-xs text-gray-300 hover:bg-gray-700 transition-colors">◉ 布局</button>
      <div className="w-px h-5 bg-gray-700/50 mx-1" />
      <button onClick={onExport} className="px-2.5 py-1 rounded-lg text-xs text-gray-300 hover:bg-gray-700 transition-colors">☰ 导出</button>
    </div>
  )
}
