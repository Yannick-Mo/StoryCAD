import { useState, useMemo, useCallback, useEffect, useRef } from 'react'
import ReactFlow, { Background, type Node, type Edge, type NodeTypes, MarkerType } from 'reactflow'
import 'reactflow/dist/style.css'
import CausalNode from './CausalNode'
import CausalSidebar from './CausalSidebar'
import type { Chapter, Act, ChapterEdge, Causality } from '../../types'

const nodeTypes: NodeTypes = { causalNode: CausalNode }

// Simple force simulation (no external dependency)
function runForceSimulation(
  nodes: { id: string; x: number; y: number }[],
  links: { source: number; target: number; strength: number }[],
  width: number,
  height: number,
) {
  if (nodes.length === 0) return
  const reps: { x: number; y: number }[] = nodes.map(() => ({ x: 0, y: 0 }))
  const attrs: { x: number; y: number }[] = nodes.map(() => ({ x: 0, y: 0 }))
  const vel: { x: number; y: number }[] = nodes.map(() => ({ x: 0, y: 0 }))
  let alpha = 1
  const alphaMin = 0.001
  const decay = 0.99

  for (let iter = 0; iter < 200 && alpha > alphaMin; iter++) {
    // Repulsion (all pairs)
    for (let i = 0; i < nodes.length; i++) {
      reps[i].x = 0; reps[i].y = 0
      for (let j = 0; j < nodes.length; j++) {
        if (i === j) continue
        const dx = nodes[i].x - nodes[j].x
        const dy = nodes[i].y - nodes[j].y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const force = 6000 / (dist * dist)
        reps[i].x += (dx / dist) * force
        reps[i].y += (dy / dist) * force
      }
    }

    // Attraction along links
    for (let i = 0; i < nodes.length; i++) {
      attrs[i].x = 0; attrs[i].y = 0
    }
    for (const link of links) {
      const s = nodes[link.source]
      const t = nodes[link.target]
      const dx = t.x - s.x
      const dy = t.y - s.y
      const dist = Math.sqrt(dx * dx + dy * dy) || 1
      const force = (dist - 200) * link.strength
      attrs[link.source].x += (dx / dist) * force
      attrs[link.source].y += (dy / dist) * force
      attrs[link.target].x -= (dx / dist) * force
      attrs[link.target].y -= (dy / dist) * force
    }

    // Apply forces
    for (let i = 0; i < nodes.length; i++) {
      vel[i].x = (vel[i].x + (reps[i].x + attrs[i].x) * alpha) * 0.5
      vel[i].y = (vel[i].y + (reps[i].y + attrs[i].y) * alpha) * 0.5
      nodes[i].x += vel[i].x
      nodes[i].y += vel[i].y
    }

    // Center gravity
    const cx = nodes.reduce((s, n) => s + n.x, 0) / nodes.length
    const cy = nodes.reduce((s, n) => s + n.y, 0) / nodes.length
    for (const n of nodes) {
      n.x += (width / 2 - cx) * 0.01
      n.y += (height / 2 - cy) * 0.01
    }

    alpha *= decay
  }
}

interface CausalityCanvasProps {
  chapters: Chapter[]
  acts: Act[]
  edges: ChapterEdge[]
  causalities: Causality[]
  onChapterClick?: (chapterId: string) => void
}

export default function CausalityCanvas({
  chapters, acts, edges, causalities, onChapterClick,
}: CausalityCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dim, setDim] = useState({ w: 800, h: 600 })

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    let raf: number | null = null
    const ro = new ResizeObserver(entries => {
      if (raf) cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const { width, height } = entries[0].contentRect
        setDim({ w: Math.max(width - 240, 400), h: Math.max(height, 400) })
      })
    })
    ro.observe(el)
    return () => {
      ro.disconnect()
      if (raf) cancelAnimationFrame(raf)
    }
  }, [])

  const actMap = useMemo(() => new Map(acts.map(a => [a.id, a])), [acts])

  const causalEdges = useMemo(() => edges.filter(e => e.type === 'causal'), [edges])
  const timelineEdges = useMemo(() => edges.filter(e => e.type === 'timeline'), [edges])

  // Compute positions via force simulation
  const layoutPositions = useMemo(() => {
    const simNodes = chapters.map((ch, i) => ({
      id: ch.id,
      x: 100 + (i % 3) * 250,
      y: 100 + Math.floor(i / 3) * 180,
    }))

    // Build link indices: map chapterId → index
    const idToIdx = new Map(chapters.map((ch, i) => [ch.id, i]))
    const links: { source: number; target: number; strength: number }[] = []

    for (const ce of causalEdges) {
      const si = idToIdx.get(ce.sourceId)
      const ti = idToIdx.get(ce.targetId)
      if (si !== undefined && ti !== undefined) {
        links.push({ source: si, target: ti, strength: 0.02 })
      }
    }
    for (const te of timelineEdges) {
      const si = idToIdx.get(te.sourceId)
      const ti = idToIdx.get(te.targetId)
      if (si !== undefined && ti !== undefined) {
        links.push({ source: si, target: ti, strength: 0.005 })
      }
    }

    runForceSimulation(simNodes, links, dim.w, dim.h)
    return new Map(simNodes.map(n => [n.id, { x: n.x, y: n.y }]))
  }, [chapters, causalEdges, timelineEdges, dim])

  const rfNodes: Node[] = useMemo(() =>
    chapters.map(ch => {
      const pos = layoutPositions.get(ch.id) ?? { x: 100, y: 100 }
      const act = actMap.get(ch.actId)
      return {
        id: ch.id,
        type: 'causalNode',
        position: pos,
        data: { title: ch.title, actColor: act?.color ?? '#666', status: ch.status },
      }
    }), [chapters, layoutPositions, actMap])

  const rfEdges: Edge[] = useMemo(() => {
    const result: Edge[] = []
    for (const ce of causalEdges) {
      result.push({
        id: ce.id,
        source: ce.sourceId,
        target: ce.targetId,
        type: 'bezier',
        style: { stroke: '#d4a373', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#d4a373' },
        label: ce.label,
      })
    }
    for (const te of timelineEdges) {
      result.push({
        id: `timeline-${te.id}`,
        source: te.sourceId,
        target: te.targetId,
        type: 'bezier',
        style: { stroke: '#555', strokeWidth: 1, strokeDasharray: '4 4', opacity: 0.3 },
        animated: false,
        interactionWidth: 0,
      })
    }
    return result
  }, [causalEdges, timelineEdges])

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    onChapterClick?.(node.id)
  }, [onChapterClick])

  return (
    <div ref={containerRef} className="h-full w-full flex">
      <div className="flex-1">
        <ReactFlow
          nodes={rfNodes}
          edges={rfEdges}
          nodeTypes={nodeTypes}
          onNodeClick={onNodeClick}
          fitView
          minZoom={0.3}
          maxZoom={2}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
        >
          <Background color="#333" gap={20} />
        </ReactFlow>
      </div>
      <CausalSidebar causalities={causalities} />
    </div>
  )
}
