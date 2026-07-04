import { memo, useRef, useCallback, useState } from 'react'
import { type NodeProps } from 'reactflow'

interface ActGroupData {
  label: string
  color: string
  onResize: (id: string, w: number, h: number) => void
}

// Interaction contract for act groups:
// - The group background must stay pointer-events-none so edges and chapter nodes
//   inside the visual group remain clickable/selectable through it.
// - Do NOT add a full-area pointer-events-auto overlay or make the whole group a
//   React Flow drag handle; that blocks edge clicks because node DOM sits above
//   the edge SVG layer.
// - Blank-area dragging and bottom-right resizing are handled by PlotCanvas using
//   coordinate hit tests on the React Flow pane. This component only renders the
//   label and visual resize affordance.
function ActGroupNode({ id, data, selected }: NodeProps<ActGroupData>) {
  const divRef = useRef<HTMLDivElement>(null)
  const [hover, setHover] = useState(false)
  const [resizing, setResizing] = useState(false)

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    e.stopPropagation()
    if (!divRef.current) return
    const el = divRef.current
    setResizing(true)
    el.setPointerCapture(e.pointerId)
    const startX = e.clientX
    const startY = e.clientY
    const startW = el.offsetWidth
    const startH = el.offsetHeight

    const onMove = (ev: PointerEvent) => {
      data.onResize(id, Math.max(300, startW + ev.clientX - startX), Math.max(150, startH + ev.clientY - startY))
    }
    const onUp = () => {
      setResizing(false)
      el.releasePointerCapture(e.pointerId)
      el.removeEventListener('pointermove', onMove)
      el.removeEventListener('pointerup', onUp)
    }
    el.addEventListener('pointermove', onMove)
    el.addEventListener('pointerup', onUp)
  }, [id, data])

  return (
    <div
      ref={divRef}
      className={`relative w-full h-full rounded-xl border pointer-events-none transition-shadow ${selected ? 'shadow-[0_0_12px_2px_rgba(251,191,36,0.3)]' : ''}`}
      style={{
        backgroundColor: data.color + '0d',
        borderColor: selected ? '#fbbf24' : data.color + '25',
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <div
        className="act-drag-handle text-xs font-medium px-4 pt-2.5 pointer-events-auto cursor-grab active:cursor-grabbing"
        style={{ color: data.color }}
      >
        {data.label}
      </div>
      {/* Visual resize affordance only. Pointer events stay disabled here; PlotCanvas
          detects the bottom-right hit area by coordinates so this marker does not
          cover edges or chapter nodes. */}
      <div
        className={`nodrag absolute bottom-0 right-0 w-4 h-4 cursor-se-resize pointer-events-none transition-opacity ${hover || resizing ? 'opacity-100' : 'opacity-0'}`}
        onPointerDown={onPointerDown}
      >
        <svg viewBox="0 0 16 16" className="w-full h-full" style={{ color: data.color }}>
          <path d="M12 4v8H4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M8 8v4h4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    </div>
  )
}

export default memo(ActGroupNode)
