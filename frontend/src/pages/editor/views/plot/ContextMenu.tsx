import { useEffect, useRef } from 'react'

interface ContextMenuItem {
  label: string
  icon?: string
  disabled?: boolean
  onClick: () => void
}

interface ContextMenuProps {
  x: number
  y: number
  items: ContextMenuItem[][]
  onClose: () => void
}

export default function ContextMenu({ x, y, items, onClose }: ContextMenuProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [onClose])

  const mx = Math.min(x, window.innerWidth - 180)
  const my = Math.min(y, window.innerHeight - items.length * 40)

  return (
    <div
      ref={ref}
      className="fixed z-50 bg-gray-900/95 backdrop-blur-lg border border-gray-700/50 rounded-xl py-1 shadow-2xl min-w-[160px]"
      style={{ left: mx, top: my }}
    >
      {items.map((group, gi) => (
        <div key={gi}>
          {gi > 0 && <div className="mx-2 my-1 border-t border-gray-700/50" />}
          {group.map(item => (
            <button
              key={item.label}
              disabled={item.disabled}
              onClick={() => { if (!item.disabled) { item.onClick(); onClose() } }}
              className={`w-full text-left px-3 py-1.5 text-xs flex items-center gap-2 transition-colors ${
                item.disabled
                  ? 'text-gray-600 cursor-not-allowed'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-gray-100'
              }`}
            >
              {item.icon && <span className="w-4 text-center">{item.icon}</span>}
              {item.label}
            </button>
          ))}
        </div>
      ))}
    </div>
  )
}
