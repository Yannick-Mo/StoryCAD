import { useMemo, useCallback, useEffect, useState, useRef } from 'react'
import ReactFlow, {
  Background, Controls, MiniMap,
  type Node, type Edge, type NodeTypes, type ReactFlowInstance,
  useNodesState, useEdgesState, MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'
import ChapterNode from './ChapterNode'
import ActGroupNode from './ActGroupNode'
import type { Chapter, Act, ChapterEdge, EdgeType, EdgeResult, SelectionState } from '../../types'
import { getBestHandle } from '../shared/getBestHandle'
import { allocateHandles, getTimelineReplacementEdgeIds } from '../../data/handleAllocation'
import { topologicalSort } from '../../data/orderUtils'
import EdgePropertyPanel from './EdgePropertyPanel'
import ContextMenu from './ContextMenu'
import { useToast } from '../../components/Toast'

const nodeTypes: NodeTypes = { chapter: ChapterNode, actGroup: ActGroupNode }
const NODE_W = 176
const NODE_H = 90
const ACT_H = 220
const ACT_GAP = 32
const CH_PER_ROW = 6

function nodeCenter(pos: { x: number; y: number }, w: number, h: number) {
  return { x: pos.x + w / 2, y: pos.y + h / 2 }
}

function getAbsPos(node: Node, all: Node[]): { x: number; y: number } {
  if (node.parentId) {
    const p = all.find(n => n.id === node.parentId)
    if (p) return { x: node.position.x + p.position.x + NODE_W / 2, y: node.position.y + p.position.y + NODE_H / 2 }
  }
  return nodeCenter(node.position, NODE_W, NODE_H)
}

// Act group interaction layering:
// React Flow renders edge SVGs below node DOM. If an act group DOM element covers
// the whole group area with pointer events enabled, edge clicks inside the group
// are swallowed by the group node. Therefore act group node styles keep
// pointerEvents: 'none' and blank-area group dragging/resizing is implemented by
// coordinate hit-testing on the pane capture handlers below. Keep edge/node/handle
// targets excluded in isInteractiveFlowTarget().
function getActGroupAtPosition(nodes: Node[], position: { x: number; y: number }) {
  return [...nodes].reverse().find(n => {
    if (n.type !== 'actGroup') return false
    const w = (n.style?.width as number) || 300
    const h = (n.style?.height as number) || 200
    return position.x >= n.position.x && position.x <= n.position.x + w &&
           position.y >= n.position.y && position.y <= n.position.y + h
  })
}

// Bottom-right resize zone is intentionally coordinate-based instead of DOM-based.
// A pointer-enabled resize DOM handle would sit in the node layer and can block
// edge selection near the group corner.
function isActGroupResizePosition(node: Node, position: { x: number; y: number }) {
  const w = (node.style?.width as number) || 300
  const h = (node.style?.height as number) || 200
  return position.x >= node.position.x + w - 18 && position.y >= node.position.y + h - 18
}

interface PlotCanvasProps {
  chapters: Chapter[]; acts: Act[]; edges: ChapterEdge[]
  onChapterClick?: (chapterId: string) => void
  onActClick?: (actId: string) => void
  onAddEdge?: (sourceId: string, targetId: string, type?: EdgeType, sourceHandle?: string, targetHandle?: string) => EdgeResult
  onDeleteEdge?: (edgeId: string) => void
  onChangeEdgeType?: (edgeId: string, newType: EdgeType) => boolean
  onReconnectEdge?: (edgeId: string, newSource?: string, newTarget?: string, sourceHandle?: string, targetHandle?: string) => void
  onAddChapter?: (actId: string) => Chapter
  onDeleteChapter?: (chapterId: string) => void
  onAddAct?: (name?: string) => Act
  onDeleteAct?: (actId: string) => void
  selection: SelectionState
  onSelectNode: (type: 'act' | 'chapter', id: string) => void
  onSelectEdge: (edgeId: string) => void
  onClearSelection: () => void
}

export default function PlotCanvas({
  chapters, acts, edges,
  onChapterClick, onActClick,
  onAddEdge, onDeleteEdge, onChangeEdgeType, onReconnectEdge,
  onAddChapter, onDeleteChapter, onAddAct, onDeleteAct,
  selection, onSelectNode, onSelectEdge, onClearSelection,
}: PlotCanvasProps) {
  const { addToast } = useToast()
  const sortedActs = useMemo(() => [...acts].sort((a, b) => a.order - b.order), [acts])

  const orderMap = useMemo(() => {
    const ordered = topologicalSort(chapters, edges)
    return new Map(ordered.map((id, i) => [id, i + 1]))
  }, [chapters, edges])

  const initialNodes: Node[] = useMemo(() => {
    const result: Node[] = []
    let y = 20
    sortedActs.forEach(act => {
      const chs = chapters.filter(c => c.actId === act.id)
      const count = chs.length
      const w = Math.max(count * 240 + 80, 300)
      const actNodeId = `act-${act.id}`
      result.push({
        id: actNodeId,
        type: 'actGroup',
        position: { x: 20, y },
        data: { label: act.name, color: act.color },
        // Keep the group node transparent to pointer events. Do not remove this:
        // edge/node clicks inside the visual group depend on events reaching the
        // React Flow edge/node layers. Group blank-area drag/resize is handled
        // by pane coordinate hit tests below.
        style: { width: w, height: ACT_H, pointerEvents: 'none' },
        dragHandle: '.act-drag-handle',
        selectable: false,
      })
      chs.forEach((ch, i) => {
        result.push({
          id: ch.id,
          type: 'chapter',
          parentId: actNodeId,
          extent: 'parent',
          position: { x: i * 240 + 40, y: 60 },
          data: {
            actId: ch.actId,
            actColor: act.color,
            title: ch.title,
            goal: ch.goal,
            wordCount: ch.wordCount,
            status: ch.status,
            sceneCount: ch.scenes.length,
            orderBadge: orderMap.get(ch.id),
          },
        })
      })
      y += ACT_H + ACT_GAP
    })
    return result
  }, [chapters, sortedActs, orderMap])

  const rfEdges: Edge[] = useMemo(() => {
    const displayEdges: ChapterEdge[] = []

    return edges.map(e => {
      const srcNode = initialNodes.find(n => n.id === e.sourceId)
      const tgtNode = initialNodes.find(n => n.id === e.targetId)
      if (!srcNode || !tgtNode) return null
      const a = getAbsPos(srcNode, initialNodes)
      const b = getAbsPos(tgtNode, initialNodes)

      let sourceHandle = e.sourceHandle
      let targetHandle = e.targetHandle
      if (!sourceHandle || !targetHandle) {
        const allocation = allocateHandles({
          sourceId: e.sourceId,
          targetId: e.targetId,
          sourcePosition: a,
          targetPosition: b,
          edges: displayEdges,
        })
        const fallback = getBestHandle(a, b)
        sourceHandle = allocation?.sourceHandle ?? fallback.sourceHandle
        targetHandle = allocation?.targetHandle ?? fallback.targetHandle
      }

      displayEdges.push({ ...e, sourceHandle, targetHandle })

      const isTimeline = e.type === 'timeline'
      const isSelected = selection.type === 'edge' && selection.id === e.id
      return {
        id: e.id,
        source: e.sourceId,
        target: e.targetId,
        sourceHandle,
        targetHandle,
        type: 'bezier',
        animated: isTimeline,
        selected: isSelected,
        style: {
          stroke: isSelected ? (isTimeline ? '#fbbf24' : '#60a5fa') : (isTimeline ? '#d4a373' : '#6b7280'),
          strokeWidth: isTimeline ? 3 : 1.5,
          strokeDasharray: isTimeline ? 'none' : '6 3',
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isSelected ? (isTimeline ? '#fbbf24' : '#60a5fa') : (isTimeline ? '#d4a373' : '#6b7280'),
        },
        label: e.type !== 'timeline' ? (e.label || e.type) : undefined,
        labelStyle: { fontSize: 10, fill: '#9ca3af', background: '#1f2937', padding: '2px 6px', borderRadius: 4 },
      }
    }).filter(Boolean) as Edge[]
  }, [edges, initialNodes, selection])

  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [rfEdgesState, setRfEdges, onEdgesChange] = useEdgesState([])
  const [selectedRfEdge, setSelectedRfEdge] = useState<string | null>(null)
  const [paneCursor, setPaneCursor] = useState<'default' | 'se-resize'>('default')
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; items: { label: string; icon?: string; disabled?: boolean; onClick: () => void }[][] } | null>(null)
  const rfRef = useRef<ReactFlowInstance | null>(null)

  // Sync nodes from data without resetting drag positions
  useEffect(() => {
    setNodes(prev => {
      const prevMap = new Map(prev.map(n => [n.id, n]))
      return initialNodes.map(n => ({
        ...n,
        position: prevMap.get(n.id)?.position ?? n.position,
      }))
    })
  }, [initialNodes, setNodes])
  // Sync data edges
  useEffect(() => { setRfEdges(rfEdges) }, [rfEdges, setRfEdges])

  // Sync selection state on nodes without resetting positions
  useEffect(() => {
    setNodes(prev => prev.map(n => {
      if (n.type === 'chapter') return { ...n, selected: selection.type === 'chapter' && selection.id === n.id }
      if (n.type === 'actGroup') return { ...n, selected: selection.type === 'act' && selection.id === n.id.replace('act-', '') }
      return n
    }))
  }, [selection, setNodes])

  const handleResize = useCallback((id: string, w: number, h: number) => {
    setNodes(nds => nds.map(n => n.id === id ? { ...n, style: { ...n.style, width: w, height: h } } : n))
  }, [setNodes])

  useEffect(() => {
    setNodes(nds => nds.map(n =>
      n.type === 'actGroup' ? { ...n, data: { ...n.data, onResize: handleResize } } : n
    ))
  }, [handleResize, setNodes])

  const onConnect = useCallback((conn: import('reactflow').Connection) => {
    if (!conn.source || !conn.target || conn.source === conn.target) return

    const rf = rfRef.current
    if (!rf) return
    const currentNodes = rf.getNodes()
    const sourceNode = currentNodes.find(n => n.id === conn.source)
    const targetNode = currentNodes.find(n => n.id === conn.target)
    if (!sourceNode || !targetNode) return

    const ignoreEdgeIds = getTimelineReplacementEdgeIds(edges, conn.source, conn.target)
    const allocation = allocateHandles({
      sourceId: conn.source,
      targetId: conn.target,
      sourcePosition: getAbsPos(sourceNode, currentNodes),
      targetPosition: getAbsPos(targetNode, currentNodes),
      edges,
      ignoreEdgeIds,
    })

    if (!allocation) {
      addToast('节点连接点已满，无法创建连线', 'warning')
      return
    }

    const result = onAddEdge?.(conn.source, conn.target, 'timeline', allocation.sourceHandle, allocation.targetHandle)
    if (result?.cycle) addToast('不能创建环路，操作已取消', 'error')
  }, [edges, onAddEdge, addToast])

  const onEdgeUpdate = useCallback((oldEdge: Edge, newConn: import('reactflow').Connection) => {
    if (!newConn.source || !newConn.target) return

    const rf = rfRef.current
    if (!rf) return
    const currentNodes = rf.getNodes()
    const sourceNode = currentNodes.find(n => n.id === newConn.source)
    const targetNode = currentNodes.find(n => n.id === newConn.target)
    if (!sourceNode || !targetNode) return

    const domainEdge = edges.find(e => e.id === oldEdge.id)
    const ignoreEdgeIds = [oldEdge.id]
    if (domainEdge?.type === 'timeline') {
      ignoreEdgeIds.push(...getTimelineReplacementEdgeIds(edges, newConn.source, newConn.target, oldEdge.id))
    }

    const allocation = allocateHandles({
      sourceId: newConn.source,
      targetId: newConn.target,
      sourcePosition: getAbsPos(sourceNode, currentNodes),
      targetPosition: getAbsPos(targetNode, currentNodes),
      edges,
      ignoreEdgeIds,
    })

    if (!allocation) {
      addToast('节点连接点已满，无法创建连线', 'warning')
      return
    }

    onReconnectEdge?.(oldEdge.id, newConn.source, newConn.target, allocation.sourceHandle, allocation.targetHandle)
  }, [edges, onReconnectEdge, addToast])

  const handleNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    if (node.type === 'chapter') {
      onSelectNode('chapter', node.id)
      onChapterClick?.(node.id)
    }
    if (node.type === 'actGroup') {
      const actId = node.id.replace('act-', '')
      onSelectNode('act', actId)
      onActClick?.(actId)
    }
  }, [onSelectNode, onChapterClick, onActClick])

  const handleEdgeClick = useCallback((_event: React.MouseEvent, edge: Edge) => {
    setSelectedRfEdge(edge.id)
    onSelectEdge(edge.id)
  }, [onSelectEdge])

  const isInteractiveFlowTarget = useCallback((target: EventTarget | null) => {
    if (!(target instanceof Element)) return false
    return Boolean(
      target.closest('.react-flow__edge') ||
      target.closest('.react-flow__node') ||
      target.closest('.react-flow__handle') ||
      target.closest('.react-flow__edgeupdater') ||
      target.closest('.nodrag') ||
      target.closest('[data-interactive="true"]') ||
      target.closest('button, input, textarea, select, a')
    )
  }, [])

  // Capture before React Flow pane panning. Only blank space inside an act group
  // is intercepted; edges, chapters, handles, resize-disabled DOM, and controls
  // are explicitly allowed through so their native React Flow handlers still run.
  const handleActGroupPanePointerDown = useCallback((event: React.PointerEvent) => {
    if (event.button !== 0 || isInteractiveFlowTarget(event.target)) return

    const rf = rfRef.current
    if (!rf) return

    const startFlowPos = rf.screenToFlowPosition({ x: event.clientX, y: event.clientY })
    const currentNodes = rf.getNodes()
    const actNode = getActGroupAtPosition(currentNodes, startFlowPos)
    if (!actNode) return

    event.preventDefault()
    event.stopPropagation()
    event.nativeEvent.stopImmediatePropagation()

    const actId = actNode.id.replace('act-', '')
    onSelectNode('act', actId)
    onActClick?.(actId)

    const pointerId = event.pointerId
    const startPosition = { ...actNode.position }
    const startWidth = (actNode.style?.width as number) || 300
    const startHeight = (actNode.style?.height as number) || 200
    const isResize = isActGroupResizePosition(actNode, startFlowPos)

    const onMove = (ev: PointerEvent) => {
      if (ev.pointerId !== pointerId) return
      const nextFlowPos = rf.screenToFlowPosition({ x: ev.clientX, y: ev.clientY })

      if (isResize) {
        setNodes(nds => nds.map(n => n.id === actNode.id ? {
          ...n,
          style: {
            ...n.style,
            width: Math.max(300, startWidth + nextFlowPos.x - startFlowPos.x),
            height: Math.max(150, startHeight + nextFlowPos.y - startFlowPos.y),
          },
        } : n))
        return
      }

      setNodes(nds => nds.map(n => n.id === actNode.id ? {
        ...n,
        position: {
          x: startPosition.x + nextFlowPos.x - startFlowPos.x,
          y: startPosition.y + nextFlowPos.y - startFlowPos.y,
        },
      } : n))
    }

    const cleanup = (ev: PointerEvent) => {
      if (ev.pointerId !== pointerId) return
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', cleanup)
      window.removeEventListener('pointercancel', cleanup)
    }

    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', cleanup)
    window.addEventListener('pointercancel', cleanup)
  }, [isInteractiveFlowTarget, onActClick, onSelectNode, setNodes])

  const handleActGroupPanePointerMove = useCallback((event: React.PointerEvent) => {
    if (isInteractiveFlowTarget(event.target)) {
      setPaneCursor('default')
      return
    }

    const rf = rfRef.current
    if (!rf) {
      setPaneCursor('default')
      return
    }

    const flowPos = rf.screenToFlowPosition({ x: event.clientX, y: event.clientY })
    const actNode = getActGroupAtPosition(rf.getNodes(), flowPos)
    setPaneCursor(actNode && isActGroupResizePosition(actNode, flowPos) ? 'se-resize' : 'default')
  }, [isInteractiveFlowTarget])

  const handlePaneClick = useCallback((event: React.MouseEvent) => {
    setSelectedRfEdge(null)
    const rf = rfRef.current
    if (!rf) return
    const flowPos = rf.screenToFlowPosition({ x: event.clientX, y: event.clientY })
    const currentNodes = rf.getNodes()
    const actNode = currentNodes.find(n => {
      if (n.type !== 'actGroup') return false
      const w = (n.style?.width as number) || 300
      const h = (n.style?.height as number) || 200
      return flowPos.x >= n.position.x && flowPos.x <= n.position.x + w &&
             flowPos.y >= n.position.y && flowPos.y <= n.position.y + h
    })
    if (actNode) {
      const actId = actNode.id.replace('act-', '')
      onSelectNode('act', actId)
      onActClick?.(actId)
    } else {
      onClearSelection()
    }
  }, [onClearSelection, onSelectNode, onActClick])

  // Context menus
  const onNodeContextMenu = useCallback((event: React.MouseEvent, node: Node) => {
    event.preventDefault()
    const id = node.type === 'actGroup' ? node.id.replace('act-', '') : node.id
    if (node.type === 'actGroup') {
      onSelectNode('act', id)
      setCtxMenu({
        x: event.clientX, y: event.clientY,
        items: [
          [{ label: '新建章', icon: '+', onClick: () => onAddChapter?.(id) }],
          [{ label: '删除幕', icon: '✕', onClick: () => onDeleteAct?.(id) }],
        ],
      })
    } else if (node.type === 'chapter') {
      onSelectNode('chapter', id)
      setCtxMenu({
        x: event.clientX, y: event.clientY,
        items: [
          [{ label: '编辑目标', icon: '✎', onClick: () => onChapterClick?.(id) }],
          [{ label: '删除章', icon: '✕', onClick: () => onDeleteChapter?.(id) }],
          [{ label: '断开时序线', icon: '⊘', onClick: () => {
            const chEdges = edges.filter(e => e.targetId === id && e.type === 'timeline')
            chEdges.forEach(e => onDeleteEdge?.(e.id))
          }}],
        ],
      })
    }
  }, [onSelectNode, onAddChapter, onDeleteAct, onChapterClick, onDeleteChapter, onDeleteEdge, chapters, edges])

  const onEdgeContextMenu = useCallback((event: React.MouseEvent, edge: Edge) => {
    event.preventDefault()
    onSelectEdge(edge.id)
    setCtxMenu({
      x: event.clientX, y: event.clientY,
      items: [
        [{ label: '删除连线', icon: '✕', onClick: () => onDeleteEdge?.(edge.id) }],
        [
          { label: '改为时序', icon: '→', onClick: () => onChangeEdgeType?.(edge.id, 'timeline') },
          { label: '改为因果', icon: '⚡', onClick: () => onChangeEdgeType?.(edge.id, 'causal') },
        ],
      ],
    })
  }, [onSelectEdge, onDeleteEdge, onChangeEdgeType])

  const onPaneContextMenu = useCallback((event: React.MouseEvent) => {
    event.preventDefault()
    const rf = rfRef.current
    if (!rf) return
    const flowPos = rf.screenToFlowPosition({ x: event.clientX, y: event.clientY })
    const currentNodes = rf.getNodes()
    const actNode = currentNodes.find(n => {
      if (n.type !== 'actGroup') return false
      const w = (n.style?.width as number) || 300
      const h = (n.style?.height as number) || 200
      return flowPos.x >= n.position.x && flowPos.x <= n.position.x + w &&
             flowPos.y >= n.position.y && flowPos.y <= n.position.y + h
    })
    if (actNode) {
      const actId = actNode.id.replace('act-', '')
      onSelectNode('act', actId)
      setCtxMenu({
        x: event.clientX, y: event.clientY,
        items: [
          [{ label: '新建章', icon: '+', onClick: () => onAddChapter?.(actId) }],
          [{ label: '删除幕', icon: '✕', onClick: () => onDeleteAct?.(actId) }],
        ],
      })
    } else {
      onClearSelection()
      setCtxMenu({
        x: event.clientX, y: event.clientY,
        items: [
          [{ label: '新建幕', icon: '+', onClick: () => onAddAct?.() }],
        ],
      })
    }
  }, [onClearSelection, onAddAct, onSelectNode, onAddChapter, onDeleteAct])

  return (
    <div
      className="h-full w-full"
      style={{ cursor: paneCursor }}
      onPointerDownCapture={handleActGroupPanePointerDown}
      onPointerMove={handleActGroupPanePointerMove}
      onPointerLeave={() => setPaneCursor('default')}
    >
      <ReactFlow
        className={paneCursor === 'se-resize' ? 'resize-cursor' : undefined}
        nodes={nodes}
        edges={rfEdgesState}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        onPaneClick={handlePaneClick}
        onEdgeUpdate={onEdgeUpdate}
        onNodeContextMenu={onNodeContextMenu}
        onEdgeContextMenu={onEdgeContextMenu}
        onPaneContextMenu={onPaneContextMenu}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={{ type: 'bezier' }}
        onInit={(instance) => { rfRef.current = instance }}
        deleteKeyCode="Delete"
        fitView
        minZoom={0.3}
        maxZoom={2}
      >
        <style>{`
          /* React Flow's pane/viewport set their own cursor, so the wrapper cursor
             is not enough. This class is toggled from the same coordinate hit
             test used for act group resizing. */
          .resize-cursor .react-flow__pane,
          .resize-cursor .react-flow__renderer,
          .resize-cursor .react-flow__viewport {
            cursor: se-resize !important;
          }
        `}</style>
        <Background color="#333" gap={20} />
        <Controls className="!bg-gray-800 !border-gray-700 !rounded-lg" />
        <MiniMap
          nodeColor={(n) => n.type === 'actGroup' ? 'transparent' : (n.data as any)?.actColor ?? '#d4a373'}
          maskColor="rgba(0,0,0,0.7)"
          className="!bg-gray-900 !border-gray-700"
        />

        {selectedRfEdge && (
          <EdgePropertyPanel
            edge={edges.find(e => e.id === selectedRfEdge) ?? null}
            chapters={chapters}
            onClose={() => setSelectedRfEdge(null)}
            onChangeType={(edgeId, newType) => {
              onChangeEdgeType?.(edgeId, newType)
              setSelectedRfEdge(null)
            }}
            onDelete={(edgeId) => {
              onDeleteEdge?.(edgeId)
              setSelectedRfEdge(null)
            }}
          />
        )}
      </ReactFlow>
      {ctxMenu && <ContextMenu {...ctxMenu} onClose={() => setCtxMenu(null)} />}
    </div>
  )
}
