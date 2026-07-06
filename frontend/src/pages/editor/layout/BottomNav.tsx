import { VIEWS, type ViewDef } from '../types'

interface BottomNavProps {
  activeViewId: string
  onSwitchView: (viewId: string) => void
}

export default function BottomNav({ activeViewId, onSwitchView }: BottomNavProps) {
  return (
    <nav className="h-14 bg-gray-900/95 backdrop-blur-xl border-t border-gray-800 flex items-center justify-center gap-2 px-4">
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
    </nav>
  )
}
