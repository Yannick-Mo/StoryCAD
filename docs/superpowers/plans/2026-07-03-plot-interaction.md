# Plot Interaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add full node/edge editing to the plot canvas — create/delete acts and chapters, create/reconnect/delete edges (timeline + relationship types), and auto-order chapters by timeline edges.

**Architecture:** Add `EdgeType` and `ChapterEdge` to types; create `useEditorStore` hook wrapping `MOCK_DATA` with mutation operations; add React Flow handles to `ChapterNode` for edge creation; add toolbar and context menu for actions; compute chapter order via topological sort on timeline edges.

**Tech Stack:** React, TypeScript, React Flow v11, Tailwind CSS

---

### Task 1: Edge types + data layer + topological sort

**Files:**
- Modify: `frontend/src/pages/editor/types.ts`
- Create: `frontend/src/pages/editor/data/editorStore.ts`
- Create: `frontend/src/pages/editor/data/orderUtils.ts`

- [ ] **Step 1: Add edge types to types.ts**

Add before `EditorMockData`:
```typescript
export type EdgeType = 'timeline' | 'causal' | 'foreshadow' | 'character' | 'theme'

export interface ChapterEdge {
  id: string
  sourceId: string
  targetId: string
  type: EdgeType
  label?: string
}
```

Add `orderBadge` to `ChapterNodeData`:
```typescript
export interface ChapterNodeData {
  actId: string
  actColor: string
  title: string
  goal: string
  wordCount: number
  status: 'draft' | 'revising' | 'final'
  sceneCount: number
  orderBadge?: string | number  // ← add this
}
```

Add `edges` to `EditorMockData`:
```typescript
export interface EditorMockData {
  projectTitle: string
  acts: Act[]
  chapters: Chapter[]
  edges: ChapterEdge[]
  characters: Character[]
  // ... rest unchanged
}
```

- [ ] **Step 2: Create orderUtils.ts**

```typescript
import type { ChapterEdge } from '../types'

/** Topological sort of chapter IDs based on timeline edges */
export function topologicalSort(chapters: { id: string }[], edges: ChapterEdge[]): string[] {
  const timelineEdges = edges.filter(e => e.type === 'timeline')
  const adj = new Map<string, string[]>()
  const inDeg = new Map<string, number>()
  const allIds = new Set(chapters.map(c => c.id))

  for (const id of allIds) {
    adj.set(id, [])
    inDeg.set(id, 0)
  }

  for (const e of timelineEdges) {
    if (!allIds.has(e.sourceId) || !allIds.has(e.targetId)) continue
    adj.get(e.sourceId)!.push(e.targetId)
    inDeg.set(e.targetId, (inDeg.get(e.targetId) ?? 0) + 1)
  }

  const queue: string[] = []
  for (const [id, deg] of inDeg) {
    if (deg === 0) queue.push(id)
  }

  const result: string[] = []
  while (queue.length > 0) {
    const id = queue.shift()!
    result.push(id)
    for (const next of adj.get(id) ?? []) {
      const nd = (inDeg.get(next) ?? 1) - 1
      inDeg.set(next, nd)
      if (nd === 0) queue.push(next)
    }
  }

  // Check for cycles — if result doesn't include all nodes, append missing
  for (const id of allIds) {
    if (!result.includes(id)) result.push(id)
  }

  return result
}

/** Check if adding an edge would create a cycle */
export function wouldCreateCycle(edges: ChapterEdge[], sourceId: string, targetId: string): boolean {
  if (sourceId === targetId) return true
  // Simulate adding the edge and check if target reaches source
  const adj = new Map<string, string[]>()
  const allIds = new Set<string>()
  for (const e of edges) {
    if (!adj.has(e.sourceId)) adj.set(e.sourceId, [])
    adj.get(e.sourceId)!.push(e.targetId)
    allIds.add(e.sourceId)
    allIds.add(e.targetId)
  }
  allIds.add(sourceId)
  allIds.add(targetId)
  if (!adj.has(sourceId)) adj.set(sourceId, [])
  adj.get(sourceId)!.push(targetId)

  // DFS from targetId to sourceId
  const visited = new Set<string>()
  const stack = [targetId]
  while (stack.length > 0) {
    const id = stack.pop()!
    if (id === sourceId) return true
    if (visited.has(id)) continue
    visited.add(id)
    for (const next of adj.get(id) ?? []) {
      stack.push(next)
    }
  }
  return false
}
```

- [ ] **Step 3: Create editorStore.ts**

```typescript
import { useState, useCallback } from 'react'
import type { Act, Chapter, Scene, ChapterEdge, EdgeType } from '../types'
import { MOCK_DATA } from './mockData'
import { topologicalSort, wouldCreateCycle } from './orderUtils'

let _nextId = 100
function uid() { return `mock-${_nextId++}` }

export interface EdgeResult {
  edge: ChapterEdge | null
  cycle?: boolean
}

export function useEditorStore(initialData = MOCK_DATA) {
  const [data, setData] = useState(initialData)

  const reSort = useCallback((chapters: Chapter[], edges: ChapterEdge[]) => {
    const ordered = topologicalSort(chapters, edges)
    const map = new Map(chapters.map(c => [c.id, c]))
    return ordered.map(id => map.get(id)!).filter(Boolean)
  }, [])

  const addAct = useCallback((name?: string) => {
    const newAct: Act = {
      id: uid(),
      name: name ?? `第 ${data.acts.length + 1} 幕`,
      order: data.acts.length + 1,
      color: ['#f97316', '#8b5cf6', '#06b6d4', '#ec4899', '#10b981', '#eab308'][data.acts.length % 6],
    }
    setData(d => ({ ...d, acts: [...d.acts, newAct] }))
    return newAct
  }, [data.acts.length])

  const addChapter = useCallback((actId: string) => {
    const actChs = data.chapters.filter(c => c.actId === actId)
    const newCh: Chapter = {
      id: uid(),
      actId,
      title: `第 ${actChs.length + 1} 章`,
      goal: '',
      wordCount: 0,
      status: 'draft',
      scenes: [],
    }
    setData(d => ({ ...d, chapters: [...d.chapters, newCh] }))
    return newCh
  }, [data.chapters])

  const deleteAct = useCallback((actId: string) => {
    const actChapterIds = new Set(data.chapters.filter(c => c.actId === actId).map(c => c.id))
    setData(d => ({
      ...d,
      acts: d.acts.filter(a => a.id !== actId),
      chapters: d.chapters.filter(c => c.actId !== actId),
      edges: d.edges.filter(e => !actChapterIds.has(e.sourceId) && !actChapterIds.has(e.targetId)),
    }))
  }, [data.chapters, data.edges])

  const deleteChapter = useCallback((chapterId: string) => {
    setData(d => ({
      ...d,
      chapters: d.chapters.filter(c => c.id !== chapterId),
      edges: d.edges.filter(e => e.sourceId !== chapterId && e.targetId !== chapterId),
    }))
  }, [])

  const addEdge = useCallback((sourceId: string, targetId: string, type: EdgeType = 'timeline'): EdgeResult => {
    if (type === 'timeline') {
      if (wouldCreateCycle(data.edges, sourceId, targetId)) {
        return { edge: null, cycle: true }
      }
      // Replace existing incoming timeline edge to target
      const filtered = data.edges.filter(e => !(e.type === 'timeline' && e.targetId === targetId))
      const newEdge: ChapterEdge = { id: uid(), sourceId, targetId, type }
      const newEdges = [...filtered, newEdge]
      const newChapters = reSort(data.chapters, newEdges)
      setData(d => ({ ...d, edges: newEdges, chapters: newChapters }))
      return { edge: newEdge }
    }
    const newEdge: ChapterEdge = { id: uid(), sourceId, targetId, type }
    setData(d => ({ ...d, edges: [...d.edges, newEdge] }))
    return { edge: newEdge }
  }, [data.edges, data.chapters, reSort])

  const deleteEdge = useCallback((edgeId: string) => {
    const edge = data.edges.find(e => e.id === edgeId)
    if (!edge) return
    const newEdges = data.edges.filter(e => e.id !== edgeId)
    if (edge.type === 'timeline') {
      const newChapters = reSort(data.chapters, newEdges)
      setData(d => ({ ...d, edges: newEdges, chapters: newChapters }))
    } else {
      setData(d => ({ ...d, edges: newEdges }))
    }
  }, [data.edges, data.chapters, reSort])

  const changeEdgeType = useCallback((edgeId: string, newType: EdgeType) => {
    setData(d => ({
      ...d,
      edges: d.edges.map(e => e.id === edgeId ? { ...e, type: newType } : e),
    }))
  }, [])

  const reconnectEdge = useCallback((edgeId: string, newSource?: string, newTarget?: string) => {
    const edge = data.edges.find(e => e.id === edgeId)
    if (!edge) return
    const source = newSource ?? edge.sourceId
    const target = newTarget ?? edge.targetId
    if (edge.type === 'timeline' && wouldCreateCycle(data.edges.filter(e => e.id !== edgeId), source, target)) {
      return // cycle detected — caller shows error
    }
    const newEdges = data.edges.map(e => e.id === edgeId ? { ...e, sourceId: source, targetId: target } : e)
    if (edge.type === 'timeline') {
      const newChapters = reSort(data.chapters, newEdges)
      setData(d => ({ ...d, edges: newEdges, chapters: newChapters }))
    } else {
      setData(d => ({ ...d, edges: newEdges }))
    }
  }, [data.edges, data.chapters, reSort])

  return {
    data,
    setData,
    addAct,
    addChapter,
    deleteAct,
    deleteChapter,
    addEdge,
    deleteEdge,
    changeEdgeType,
    reconnectEdge,
  }
}
```

---

### Task 2: Add edge data to mock data + wire EditorShell with store

**Files:**
- Modify: `frontend/src/pages/editor/data/mockData.ts`
- Modify: `frontend/src/pages/editor/layout/EditorShell.tsx`

- [ ] **Step 1: Add edges to mockData.ts**

Add `edges` array to `MOCK_DATA`:
```typescript
edges: [
  { id: 'e1', sourceId: 'ch1', targetId: 'ch2', type: 'timeline' },
  { id: 'e2', sourceId: 'ch2', targetId: 'ch3', type: 'timeline' },
  { id: 'e3', sourceId: 'ch4', targetId: 'ch5', type: 'timeline' },
  { id: 'e4', sourceId: 'ch5', targetId: 'ch6', type: 'timeline' },
  { id: 'e5', sourceId: 'ch2', targetId: 'ch4', type: 'causal', label: '因果' },
],
```

Add to `MOCK_DATA` object in the `EditorMockData` shape.

- [ ] **Step 2: Wire EditorShell with useEditorStore**

Replace `const data = MOCK_DATA` with:
```typescript
const store = useEditorStore()
const data = store.data
```

Replace mutation callbacks to use store methods where applicable. Keep `handleSceneSave` and `handleChapterGoalSave` as-is since they will later be integrated with the API.

Pass store methods to `PlotCanvas`:
```tsx
<PlotCanvas
  chapters={data.chapters}
  acts={data.acts}
  edges={data.edges}
  onChapterClick={handleChapterClick}
  onActClick={handleActClick}
  onAddEdge={store.addEdge}
  onDeleteEdge={store.deleteEdge}
  onChangeEdgeType={store.changeEdgeType}
  onReconnectEdge={store.reconnectEdge}
  onAddChapter={store.addChapter}
  onDeleteChapter={store.deleteChapter}
  onAddAct={store.addAct}
  onDeleteAct={store.deleteAct}
/>
```

---

### Task 3: Update PlotCanvas with full interaction support

**Files:**
- Modify: `frontend/src/pages/editor/views/plot/PlotCanvas.tsx`
- Modify: `frontend/src/pages/editor/views/plot/ChapterNode.tsx`
- Modify: `frontend/src/pages/editor/views/plot/ActGroupNode.tsx`

- [ ] **Step 1: Update ChapterNode with source/target handles**

```typescript
import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import type { ChapterNodeData } from '../../types'

function ChapterNode({ data }: NodeProps<ChapterNodeData>) {
  return (
    <div className="px-3 py-2.5 rounded-xl bg-gray-800 border border-gray-600/60 shadow-lg w-44 cursor-pointer hover:border-amber-500/50 transition-colors group">
      {/* Top handle — target for incoming edges */}
      <Handle type="target" position={Position.Top} className="!bg-amber-400 !w-2.5 !h-2.5 !border-2 !border-gray-900 opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="text-xs font-medium text-gray-200 truncate">{data.title}</div>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-[10px] text-gray-500">{data.sceneCount} 场</span>
        <span className={`px-1 rounded text-[9px] ${
          data.status === 'final' ? 'bg-green-900/30 text-green-400' :
          data.status === 'revising' ? 'bg-amber-900/30 text-amber-400' :
          'bg-gray-700 text-gray-400'
        }`}>{data.status === 'final' ? '完' : data.status === 'revising' ? '改' : '稿'}</span>
        <span className="text-[10px] text-gray-600 ml-auto">{data.wordCount > 0 ? `${data.wordCount}w` : ''}</span>
      </div>
      {/* Bottom handle — source for outgoing edges */}
      <Handle type="source" position={Position.Bottom} className="!bg-amber-400 !w-2.5 !h-2.5 !border-2 !border-gray-900 opacity-0 group-hover:opacity-100 transition-opacity" />
    </div>
  )
}

export default memo(ChapterNode)
```

- [ ] **Step 2: Update PlotCanvas props interface and connection handling**

```typescript
interface PlotCanvasProps {
  chapters: Chapter[]
  acts: Act[]
  edges: ChapterEdge[]
  onChapterClick?: (chapterId: string) => void
  onActClick?: (actId: string) => void
  onAddEdge?: (sourceId: string, targetId: string, type?: EdgeType) => EdgeResult
  onDeleteEdge?: (edgeId: string) => void
  onChangeEdgeType?: (edgeId: string, newType: EdgeType) => void
  onReconnectEdge?: (edgeId: string, newSource?: string, newTarget?: string) => void
  onAddChapter?: (actId: string) => Chapter
  onDeleteChapter?: (chapterId: string) => void
  onAddAct?: (name?: string) => Act
  onDeleteAct?: (actId: string) => void
}
```

- [ ] **Step 3: Build React Flow edges from ChapterEdge**

```typescript
const rfEdges: Edge[] = useMemo(() => {
  return edges.map(e => {
    const srcNode = initialNodes.find(n => n.id === e.sourceId)
    const tgtNode = initialNodes.find(n => n.id === e.targetId)
    if (!srcNode || !tgtNode) return null
    const a = getAbsPos(srcNode, initialNodes)
    const b = getAbsPos(tgtNode, initialNodes)
    const { sourceHandle, targetHandle } = getBestHandle(a, b)
    const isTimeline = e.type === 'timeline'
    return {
      id: e.id,
      source: e.sourceId,
      target: e.targetId,
      sourceHandle,
      targetHandle,
      type: 'bezier',
      animated: isTimeline,
      style: {
        stroke: isTimeline ? '#d4a373' : '#6b7280',
        strokeWidth: isTimeline ? 3 : 1.5,
        strokeDasharray: isTimeline ? 'none' : '6 3',
      },
      markerEnd: { type: MarkerType.ArrowClosed, color: isTimeline ? '#d4a373' : '#6b7280' },
      label: e.type !== 'timeline' ? e.label || e.type : undefined,
      labelStyle: { fontSize: 10, fill: '#9ca3af', background: '#1f2937', padding: '2px 6px', borderRadius: 4 },
    }
  }).filter(Boolean) as Edge[]
}, [edges, initialNodes])
```

- [ ] **Step 4: Add connection handler**

```typescript
const onConnect = useCallback((conn: Connection) => {
  if (!conn.source || !conn.target || conn.source === conn.target) return
  const result = onAddEdge?.(conn.source, conn.target, 'timeline')
  if (result?.cycle) {
    alert('⚠️ 时序边不能形成环路，操作已取消')
  }
}, [onAddEdge])
```

- [ ] **Step 5: Add delete key handler and edge update**

```typescript
const onEdgeUpdate = useCallback((oldEdge: Edge, newConn: Connection) => {
  if (!newConn.source || !newConn.target) return
  onReconnectEdge?.(oldEdge.id, newConn.source, newConn.target)
}, [onReconnectEdge])

// Inside ReactFlow component, add:
deleteKeyCode="Delete"
onEdgeUpdate={onEdgeUpdate}
```

- [ ] **Step 6: Enable edge selection**

```typescript
// Remove selectable: false from edges, add onEdgeClick handler
const handleEdgeClick = useCallback((_event: React.MouseEvent, edge: Edge) => {
  // Edge is selected by React Flow — type change / delete available via keyboard
}, [])
```

- [ ] **Step 7: Update initialNodes to include order badge**

In the chapter node data, pass `orderIndex`:
```typescript
// After topological sort or using chapter index:
const orderedIds = topologicalSort(chapters, edges)
const orderMap = new Map(orderedIds.map((id, i) => [id, i + 1]))
// In data: orderBadge: orderMap.get(ch.id) ?? '-'
```

Add to ChapterNode display:
```typescript
<span className="absolute -top-2 -left-2 w-5 h-5 rounded-full bg-amber-600 text-[10px] font-bold text-black flex items-center justify-center">
  {data.orderBadge}
</span>
```

---

### Task 4: Toolbar component

**Files:**
- Create: `frontend/src/pages/editor/views/plot/PlotToolbar.tsx`
- Modify: `frontend/src/pages/editor/layout/EditorShell.tsx`

- [ ] **Step 1: Create PlotToolbar.tsx**

```typescript
import type { Act, EdgeType } from '../../types'

interface PlotToolbarProps {
  selectedActId: string | null
  selectedNodeType: 'act' | 'chapter' | 'edge' | null
  edgeFilter: 'all' | 'timeline' | 'relation'
  onAddAct: () => void
  onAddChapter: () => void
  onDeleteSelected: () => void
  onEdgeFilterChange: (filter: 'all' | 'timeline' | 'relation') => void
  onLayout: () => void
  onExport: () => void
}

export default function PlotToolbar({
  selectedActId, selectedNodeType,
  edgeFilter, onAddAct, onAddChapter,
  onDeleteSelected, onEdgeFilterChange, onLayout, onExport,
}: PlotToolbarProps) {
  return (
    <div className="absolute top-3 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1.5 bg-gray-900/90 backdrop-blur-lg border border-gray-700/50 rounded-xl px-3 py-1.5 shadow-xl">
      <button onClick={onAddAct} className="px-2.5 py-1 rounded-lg text-xs text-gray-300 hover:bg-amber-600/20 hover:text-amber-400 transition-colors" title="添加幕">＋幕</button>
      <button onClick={onAddChapter} disabled={!selectedActId} className={`px-2.5 py-1 rounded-lg text-xs transition-colors ${selectedActId ? 'text-gray-300 hover:bg-amber-600/20 hover:text-amber-400' : 'text-gray-600 cursor-not-allowed'}`} title="添加章节">＋章</button>
      <div className="w-px h-5 bg-gray-700/50 mx-1" />
      <button onClick={onDeleteSelected} disabled={!selectedNodeType} className={`px-2.5 py-1 rounded-lg text-xs transition-colors ${selectedNodeType ? 'text-red-400 hover:bg-red-600/20' : 'text-gray-600 cursor-not-allowed'}`} title="删除选中">✕</button>
      <div className="w-px h-5 bg-gray-700/50 mx-1" />
      <select value={edgeFilter} onChange={e => onEdgeFilterChange(e.target.value as any)} className="bg-transparent text-xs text-gray-400 border border-gray-700 rounded px-1.5 py-1 outline-none cursor-pointer">
        <option value="all">全部连线</option>
        <option value="timeline">仅时序</option>
        <option value="relation">仅关系</option>
      </select>
      <button onClick={onLayout} className="px-2.5 py-1 rounded-lg text-xs text-gray-300 hover:bg-gray-700 transition-colors" title="自动布局">◉ 布局</button>
      <div className="w-px h-5 bg-gray-700/50 mx-1" />
      <button onClick={onExport} className="px-2.5 py-1 rounded-lg text-xs text-gray-300 hover:bg-gray-700 transition-colors">☰ 导出</button>
    </div>
  )
}
```

- [ ] **Step 2: Integrate toolbar into EditorShell**

In EditorShell, add state and render toolbar conditionally in the plot view:
```tsx
// State
const [edgeFilter, setEdgeFilter] = useState<'all' | 'timeline' | 'relation'>('all')

// Inside renderCanvas, before the canvas:
{views.activeViewId === 'narrative-plot' && (
  <PlotToolbar
    selectedActId={selectedActId}
    selectedNodeType={/* derive from selection state */}
    edgeFilter={edgeFilter}
    onAddAct={() => store.addAct()}
    onAddChapter={() => selectedActId && store.addChapter(selectedActId)}
    onDeleteSelected={handleDeleteSelected}
    onEdgeFilterChange={setEdgeFilter}
    onLayout={() => {}}  // Dagre layout — can be added later
    onExport={handleExport}
  />
)}
```

---

### Task 5: Context menu + edge property panel

**Files:**
- Create: `frontend/src/pages/editor/views/plot/EdgePropertyPanel.tsx`

- [ ] **Step 1: Edge property panel**

When an edge is selected, show a small panel near it or in the right panel:
```typescript
interface EdgePropertyPanelProps {
  edge: ChapterEdge | null
  onChangeType: (edgeId: string, newType: EdgeType) => void
  onDelete: (edgeId: string) => void
  onClose: () => void
}
```

- Render when an edge is selected in the plot canvas
- Dropdown to change type
- Label input (for relation edges)
- Delete button

- [ ] **Step 2: Add context menu via React Flow's onNodeContextMenu + onEdgeContextMenu**

```typescript
const onNodeContextMenu = useCallback((event: React.MouseEvent, node: Node) => {
  event.preventDefault()
  // Show custom context menu at cursor position
  setContextMenu({ x: event.clientX, y: event.clientY, nodeId: node.id, nodeType: node.type })
}, [])

const onEdgeContextMenu = useCallback((event: React.MouseEvent, edge: Edge) => {
  event.preventDefault()
  setContextMenu({ x: event.clientX, y: event.clientY, edgeId: edge.id })
}, [])

const onPaneContextMenu = useCallback((event: React.MouseEvent) => {
  event.preventDefault()
  setContextMenu({ x: event.clientX, y: event.clientY, pane: true })
}, [])

// Close menu
const closeContextMenu = useCallback(() => setContextMenu(null), [])
```

- [ ] **Step 3: Context menu component**

```typescript
function ContextMenu({ menu, onClose, onAddAct, onAddChapter, onDeleteAct, onDeleteChapter, onDeleteEdge, onChangeEdgeType }: Props) {
  if (!menu) return null
  return (
    <div
      className="fixed z-50 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl py-1 min-w-[140px]"
      style={{ left: menu.x, top: menu.y }}
      onClick={onClose}
    >
      {menu.pane && <MenuItem label="添加幕" onClick={onAddAct} />}
      {menu.nodeType === 'actGroup' && <>
        <MenuItem label="添加章节" onClick={() => onAddChapter(menu.nodeId!.replace('act-', ''))} />
        <MenuItem label="删除幕" onClick={() => onDeleteAct(menu.nodeId!.replace('act-', ''))} danger />
      </>}
      {menu.nodeType === 'chapter' && <>
        <MenuItem label="删除章节" onClick={() => onDeleteChapter(menu.nodeId!)} danger />
      </>}
      {menu.edgeId && <>
        <div className="px-3 py-1.5 text-[10px] text-gray-500 border-b border-gray-700">修改类型</div>
        {(['causal', 'foreshadow', 'character', 'theme'] as EdgeType[]).map(t => (
          <MenuItem key={t} label={typeLabel(t)} onClick={() => onChangeEdgeType(menu.edgeId!, t)} />
        ))}
        <MenuItem label="删除连线" onClick={() => onDeleteEdge(menu.edgeId!)} danger />
      </>}
    </div>
  )
}

function MenuItem({ label, onClick, danger }: { label: string; onClick: () => void; danger?: boolean }) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-1.5 text-xs transition-colors ${danger ? 'text-red-400 hover:bg-red-600/20' : 'text-gray-300 hover:bg-gray-700'}`}
    >
      {label}
    </button>
  )
}

function typeLabel(t: EdgeType): string {
  switch (t) {
    case 'causal': return '🔗 因果关系'
    case 'foreshadow': return '🔮 伏笔照应'
    case 'character': return '👤 人物关联'
    case 'theme': return '🎭 主题关联'
    default: return t
  }
}
```

- [ ] **Step 4: Pass context menu events to ReactFlow**

Add to ReactFlow component:
```tsx
onNodeContextMenu={onNodeContextMenu}
onEdgeContextMenu={onEdgeContextMenu}
onPaneContextMenu={onPaneContextMenu}
```

---

### Task 6: Verify build

- [ ] **Step 1: Run tsc**

Run: `wsl docker exec storycad-frontend-1 sh -c 'cd /app && npx tsc --noEmit'`
Expected: exit code 0, no errors

- [ ] **Step 2: Verify page loads**

Run: `curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/`
Expected: 200
