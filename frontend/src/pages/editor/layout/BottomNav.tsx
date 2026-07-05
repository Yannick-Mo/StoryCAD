import type { Pillar } from '../types'

const PILLARS: { key: Pillar; icon: string; label: string }[] = [
  { key: 'world', icon: '🌍', label: '世界' },
  { key: 'narrative', icon: '📖', label: '叙事' },
]

interface SubOption {
  id: string
  label: string
}

interface BottomNavProps {
  activePillar: Pillar
  activeViewId: string
  subPanelOpen: boolean
  pillarViews: SubOption[]
  onSwitchPillar: (pillar: Pillar) => void
  onSwitchView: (viewId: string) => void
  onCloseSubPanel: () => void
}

export default function BottomNav({
  activePillar, activeViewId, subPanelOpen, pillarViews,
  onSwitchPillar, onSwitchView, onCloseSubPanel,
}: BottomNavProps) {
  return (
    <div className="relative">
      {subPanelOpen && (
        <>
          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-20">
            <div className="flex gap-1 bg-gray-800/95 backdrop-blur-xl border border-gray-700 rounded-2xl px-3 py-2 shadow-2xl">
              {pillarViews.map(v => (
                <button
                  key={v.id}
                  onClick={() => onSwitchView(v.id)}
                  className={`px-3 py-1.5 rounded-xl text-sm whitespace-nowrap transition-colors ${
                    activeViewId === v.id
                      ? 'bg-amber-600/20 text-amber-400'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700'
                  }`}
                >
                  {v.label}
                </button>
              ))}
            </div>
          </div>
          <div className="fixed inset-0 z-10" onClick={onCloseSubPanel} />
        </>
      )}
      <nav className="h-14 bg-gray-900/95 backdrop-blur-xl border-t border-gray-800 flex items-center justify-center gap-6 relative z-20">
        {PILLARS.map(p => (
          <button
            key={p.key}
            onClick={() => onSwitchPillar(p.key)}
            className={`flex flex-col items-center gap-0.5 px-4 py-1 rounded-full transition-colors ${
              activePillar === p.key
                ? 'text-amber-400 bg-amber-500/10'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            <span className="text-lg">{p.icon}</span>
            <span className="text-xs font-medium">{p.label}</span>
          </button>
        ))}
      </nav>
    </div>
  )
}
