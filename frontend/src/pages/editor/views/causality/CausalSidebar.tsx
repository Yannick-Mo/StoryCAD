import type { Causality } from '../../types'

interface CausalSidebarProps {
  causalities: Causality[]
}

export default function CausalSidebar({ causalities }: CausalSidebarProps) {
  if (causalities.length === 0) return null
  return (
    <div className="w-60 border-l border-gray-800 bg-gray-900/50 p-3 overflow-y-auto shrink-0">
      <h3 className="text-xs text-gray-500 font-medium mb-3 uppercase tracking-wider">因果链</h3>
      <div className="space-y-2">
        {causalities.map(c => (
          <div key={c.id} className="bg-gray-800/60 border border-gray-700/50 rounded-lg p-3">
            <div className="text-xs text-gray-400">
              <span className="text-amber-500">因</span> {c.cause}
            </div>
            <div className="text-xs text-gray-500 mt-1">↓</div>
            <div className="text-xs text-gray-400">
              <span className="text-orange-500">果</span> {c.effect}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
