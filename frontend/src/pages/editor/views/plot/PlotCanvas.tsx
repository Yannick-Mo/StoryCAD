import { useMemo, useCallback, useEffect, useState } from 'react'
import ReactFlow, {
  Background, Controls, MiniMap,
  type Node, type Edge, type NodeTypes,
  useNodesState, useEdgesState, MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'
import ChapterNode from './ChapterNode'
import ActGroupNode from './ActGroupNode'
import type { Chapter, Act, ChapterEdge, EdgeType, EdgeResult, SelectionState } from '../../types'
import { getBestHandle } from '../shared/getBestHandle'
import { topologicalSort, getCompletedChain } from '../../data/orderUtils'
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

interface PlotCanvasProps {
  chapters: Chapter[]; acts: Act[]; edges: ChapterEdge[]
  onChapterClick?: (chapterId: string) => void
  onActClick?: (actId: string) => void
  onAddEdge?: (sourceId: string, targetId: string, type?: EdgeType) => EdgeResult
  onDeleteEdge?: (edgeId: string) => void
  onChangeEdgeType?: (edgeId: string, newType: EdgeType) => boolean
  onReconnectEdge?: (edgeId: string, newSource?: string, newTarget?: string) => void
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
        style: { width: w, height: ACT_H, pointerEvents: 'none' },
        selectable: false,
      })
      chs.forEach((ch, i) => {
        result.push({
          id: ch.id,
          type: 'chapter',
          parentId: actNodeId,
          extent: 'parent',
          position: { x: i * 240 + 40, y: 60 },
          style: { pointerEvents: 'auto' },
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
    return edges.map(e => {
      const srcNode = initialNodes.find(n => n.id === e.sourceId)
      const tgtNode = initialNodes.find(n => n.id === e.targetId)
      if (!srcNode || !tgtNode) return null
      const a = getAbsPos(srcNode, initialNodes)
      const b = getAbsPos(tgtNode, initialNodes)
      const { sourceHandle, targetHandle } = getBestHandle(a, b)
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
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; items: { label: string; icon?: string; disabled?: boolean; onClick: () => void }[][] } | null>(null)

  // Sync nodes from data without resetting drag positions
  useEffect(() => {
    setNodes(prev => {
      const prevMap = new Map(prev.map(n => [n.id, n]))
      return initialNodes.map(n => ({
        ...n,
        position: prevMap.get(n.id)?.position ?? n.position,
        style: { ...n.style, pointerEvents: n.type === 'actGroup' ? 'none' : 'auto' },
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
    const result = onAddEdge?.(conn.source, conn.target, 'timeline')
    if (result?.cycle) addToast('不能创建环路，操作已取消', 'error')
  }, [onAddEdge, addToast])

  const onEdgeUpdate = useCallback((oldEdge: Edge, newConn: import('reactflow').Connection) => {
    if (!newConn.source || !newConn.target) return
    onReconnectEdge?.(oldEdge.id, newConn.source, newConn.target)
  }, [onReconnectEdge])

  const handleNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    if (node.type === 'chapter') onSelectNode('chapter', node.id)
    if (node.type === 'actGroup') onSelectNode('act', node.id.replace('act-', ''))
  }, [onSelectNode])

  const handleEdgeClick = useCallback((_event: React.MouseEvent, edge: Edge) => {
    setSelectedRfEdge(edge.id)
    onSelectEdge(edge.id)
  }, [onSelectEdge])

  const handlePaneClick = useCallback(() => {
    setSelectedRfEdge(null)
    onClearSelection()
  }, [onClearSelection])

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
    onClearSelection()
    setCtxMenu({
      x: event.clientX, y: event.clientY,
      items: [
        [{ label: '新建幕', icon: '+', onClick: () => onAddAct?.() }],
      ],
    })
  }, [onClearSelection, onAddAct])

  return (
    <>
      <ReactFlow
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
        deleteKeyCode="Delete"
        fitView
        minZoom={0.3}
        maxZoom={2}
      >
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
    </>
  )
}
