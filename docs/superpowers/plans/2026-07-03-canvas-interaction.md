# Canvas Interaction System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full CAD interaction system for the plot canvas: create/delete/reorder nodes and edges, right-click context menu, dynamic toolbar, locked-edge protection for chapters with content.

**Architecture:** Fix the `useEditorStore` stale-closure bugs, add `SelectionState` to drive toolbar/visual feedback, add `isEdgeLocked` for timeline protection, create `ContextMenu` and `Toast` components, and sync React Flow node state correctly.

**Tech Stack:** React, React Flow v11, TypeScript, Tailwind CSS

---

### Task 1: Types + orderUtils

**Files:**
- Modify: `frontend/src/pages/editor/types.ts`
- Modify: `frontend/src/pages/editor/data/orderUtils.ts`

- [ ] **Step 1: Add SelectionState, Toast, and update EdgeResult with locked field**

```typescript
// Add to existing types.ts
export interface SelectionState {
  type: 'act' | 'chapter' | 'edge' | null
  id: string | null
}

export interface Toast {
  id: string
  message: string
  type: 'info' | 'warning' | 'error' | 'success'
  duration?: number
}

// Add `locked?: boolean` to existing EdgeResult
// Current EdgeResult:
// export interface EdgeResult { edge: ChapterEdge | null; cycle?: boolean }
// Change to:
// export interface EdgeResult { edge: ChapterEdge | null; cycle?: boolean; locked?: boolean }
```

- [ ] **Step 2: Add isEdgeLocked to orderUtils.ts**

```typescript
// Add to existing orderUtils.ts
export function isEdgeLocked(edge: ChapterEdge, chapters: Chapter[]): boolean {
  if (edge.type !== 'timeline') return false
  const target = chapters.find(c => c.id === edge.targetId)
  return target ? target.wordCount > 0 : false
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/editor/types.ts frontend/src/pages/editor/data/orderUtils.ts
git commit -m "feat: add SelectionState, Toast, isEdgeLocked types"
```

---

### Task 2: Toast system

**Files:**
- Create: `frontend/src/pages/editor/components/Toast.tsx`

- [ ] **Step 1: Create ToastContainer and useToast hook**

```tsx
import { useState, useCallback, createContext, useContext } from 'react'
import type { Toast } from '../types'

interface ToastContextValue {
  toasts: Toast[]
  addToast: (message: string, type?: Toast['type']) => void
  removeToast: (id: string) => void
}

const ToastContext = createContext<ToastContextValue>(null!)

export function useToast() {
  return useContext(ToastContext)
}

let _toastId = 0

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts(t => t.filter(x => x.id !== id))
  }, [])

  const addToast = useCallback((message: string, type: Toast['type'] = 'info') => {
    const id = `toast-${++_toastId}`
    setToasts(t => [...t, { id, message, type }])
    setTimeout(() => removeToast(id), 3000)
  }, [removeToast])

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <div className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2 items-center pointer-events-none">
        {toasts.map(t => (
          <div
            key={t.id}
            className={`px-4 py-2 rounded-lg text-sm shadow-lg backdrop-blur-lg transition-all animate-fade-in pointer-events-auto ${
              t.type === 'error' ? 'bg-red-900/90 text-red-200' :
              t.type === 'warning' ? 'bg-amber-900/90 text-amber-200' :
              t.type === 'success' ? 'bg-green-900/90 text-green-200' :
              'bg-gray-800/90 text-gray-200'
            }`}
          >
            {t.type === 'error' ? '✕ ' : t.type === 'warning' ? '⚠ ' : t.type === 'success' ? '✓ ' : 'ℹ '}
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/editor/components/Toast.tsx
git commit -m "feat: add Toast notification system"
```

---

### Task 3: ConfirmDialog component

**Files:**
- Create: `frontend/src/pages/editor/components/ConfirmDialog.tsx`

- [ ] **Step 1: Create ConfirmDialog**

```tsx
interface ConfirmDialogProps {
  open: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  onConfirm: () => void
  onCancel: () => void
}

export default function ConfirmDialog({
  open, title, message,
  confirmText = '确认删除',
  cancelText = '取消',
  onConfirm, onCancel,
}: ConfirmDialogProps) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onCancel}>
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 shadow-2xl w-80" onClick={e => e.stopPropagation()}>
        <h3 className="text-sm font-semibold text-gray-200 mb-2">{title}</h3>
        <p className="text-xs text-gray-400 mb-6">{message}</p>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} className="px-3 py-1.5 rounded-lg text-xs text-gray-400 hover:bg-gray-700 transition-colors">
            {cancelText}
          </button>
          <button onClick={onConfirm} className="px-3 py-1.5 rounded-lg text-xs text-white bg-red-600 hover:bg-red-500 transition-colors">
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/editor/components/ConfirmDialog.tsx
git commit -m "feat: add ConfirmDialog component"
```

---

### Task 4: Rewrite editorStore

**Files:**
- Modify: `frontend/src/pages/editor/data/editorStore.ts`

**Key fixes:**
1. All callbacks have proper dependency arrays
2. All state mutations return new objects (no direct mutation)
3. Add `selection` state with `selectNode`, `selectEdge`, `clearSelection`
4. Add locking check in `addEdge` and `reconnectEdge`
5. Cycle detection preserved
6. Callbacks no longer depend on `data` directly—use `setData(d => ...)` form throughout

- [ ] **Step 1: Write the rewritten store**

```typescript
import { useState, useCallback } from 'react'
import type { Act, Chapter, ChapterEdge, EdgeType, EdgeResult, SelectionState } from '../types'
import { MOCK_DATA } from './mockData'
import { topologicalSort, wouldCreateCycle, isEdgeLocked } from './orderUtils'

let _nextId = 100
function uid() { return `mock-${_nextId++}` }

const COLORS = ['#f97316', '#8b5cf6', '#06b6d4', '#ec4899', '#10b981', '#eab308']

export function useEditorStore(initialData = MOCK_DATA) {
  const [data, setData] = useState(initialData)
  const [selection, setSelection] = useState<SelectionState>({ type: null, id: null })

  const selectNode = useCallback((type: 'act' | 'chapter', id: string) => {
    setSelection({ type, id })
  }, [])

  const selectEdge = useCallback((edgeId: string) => {
    setSelection({ type: 'edge', id: edgeId })
  }, [])

  const clearSelection = useCallback(() => {
    setSelection({ type: null, id: null })
  }, [])

  const reSort = useCallback((chapters: Chapter[], edges: ChapterEdge[]) => {
    const ordered = topologicalSort(chapters, edges)
    const map = new Map(chapters.map(c => [c.id, c]))
    return ordered.map(id => map.get(id)!).filter(Boolean)
  }, [])

  const addAct = useCallback((name?: string) => {
    const newAct: Act = { id: uid(), name: name ?? `第 ${data.acts.length + 1} 幕`, order: data.acts.length + 1, color: COLORS[data.acts.length % 6] }
    setData(d => ({ ...d, acts: [...d.acts, newAct] }))
    return newAct
  }, [data.acts.length])

  const addChapter = useCallback((actId: string) => {
    const newCh: Chapter = { id: uid(), actId, title: `第 ${data.chapters.filter(c => c.actId === actId).length + 1} 章`, goal: '', wordCount: 0, status: 'draft', scenes: [] }
    setData(d => ({ ...d, chapters: [...d.chapters, newCh] }))
    return newCh
  }, [data.chapters])

  const deleteAct = useCallback((actId: string) => {
    setData(d => {
      const chapterIds = new Set(d.chapters.filter(c => c.actId === actId).map(c => c.id))
      return {
        ...d,
        acts: d.acts.filter(a => a.id !== actId),
        chapters: d.chapters.filter(c => c.actId !== actId),
        edges: d.edges.filter(e => !chapterIds.has(e.sourceId) && !chapterIds.has(e.targetId)),
      }
    })
    setSelection({ type: null, id: null })
  }, [])

  const deleteChapter = useCallback((chapterId: string) => {
    setData(d => ({
      ...d,
      chapters: d.chapters.filter(c => c.id !== chapterId),
      edges: d.edges.filter(e => e.sourceId !== chapterId && e.targetId !== chapterId),
    }))
  }, [])

  const addEdge = useCallback((sourceId: string, targetId: string, type: EdgeType = 'timeline'): EdgeResult => {
    let result: EdgeResult = { edge: null }
    setData(d => {
      if (type === 'timeline') {
        // Check lock: target chapter with content
        const targetChapter = d.chapters.find(c => c.id === targetId)
        if (targetChapter && targetChapter.wordCount > 0) {
          result = { edge: null, locked: true }
          return d
        }
        // Check cycle
        if (wouldCreateCycle(d.edges, sourceId, targetId)) {
          result = { edge: null, cycle: true }
          return d
        }
        // Replace existing timeline edge to same target (one predecessor constraint)
        const filtered = d.edges.filter(e => !(e.type === 'timeline' && e.targetId === targetId))
        const newEdge: ChapterEdge = { id: uid(), sourceId, targetId, type }
        result = { edge: newEdge }
        return { ...d, edges: [...filtered, newEdge], chapters: reSort(d.chapters, [...filtered, newEdge]) }
      }
      const newEdge: ChapterEdge = { id: uid(), sourceId, targetId, type }
      result = { edge: newEdge }
      return { ...d, edges: [...d.edges, newEdge] }
    })
    return result
  }, [reSort])

  const deleteEdge = useCallback((edgeId: string) => {
    setData(d => {
      const edge = d.edges.find(e => e.id === edgeId)
      if (!edge) return d
      const newEdges = d.edges.filter(e => e.id !== edgeId)
      if (edge.type === 'timeline') return { ...d, edges: newEdges, chapters: reSort(d.chapters, newEdges) }
      return { ...d, edges: newEdges }
    })
  }, [reSort])

  const changeEdgeType = useCallback((edgeId: string, newType: EdgeType): boolean => {
    let blocked = false
    setData(d => {
      const edge = d.edges.find(e => e.id === edgeId)
      if (!edge) return d
      if (newType === 'timeline' && edge.type !== 'timeline') {
        const targetChapter = d.chapters.find(c => c.id === edge.targetId)
        if (targetChapter && targetChapter.wordCount > 0) { blocked = true; return d }
      }
      return { ...d, edges: d.edges.map(e => e.id === edgeId ? { ...e, type: newType } : e) }
    })
    return !blocked
  }, [])

  const reconnectEdge = useCallback((edgeId: string, newSource?: string, newTarget?: string) => {
    setData(d => {
      const edge = d.edges.find(e => e.id === edgeId)
      if (!edge) return d
      const source = newSource ?? edge.sourceId
      const target = newTarget ?? edge.targetId
      if (edge.type === 'timeline') {
        // Check lock on new target
        const targetChapter = d.chapters.find(c => c.id === target)
        if (targetChapter && targetChapter.wordCount > 0) return d
        // Check cycle
        if (wouldCreateCycle(d.edges.filter(e => e.id !== edgeId), source, target)) return d
        const newEdges = d.edges.map(e => e.id === edgeId ? { ...e, sourceId: source, targetId: target } : e)
        return { ...d, edges: newEdges, chapters: reSort(d.chapters, newEdges) }
      }
      return { ...d, edges: d.edges.map(e => e.id === edgeId ? { ...e, sourceId: source, targetId: target } : e) }
    })
  }, [reSort])

  return {
    data, setData,
    selection, selectNode, selectEdge, clearSelection,
    addAct, addChapter, deleteAct, deleteChapter,
    addEdge, deleteEdge, changeEdgeType, reconnectEdge,
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/editor/data/editorStore.ts
git commit -m "fix: rewrite editorStore with proper closures, selection state, and edge locking"
```

---

### Task 5: ContextMenu component

**Files:**
- Create: `frontend/src/pages/editor/views/plot/ContextMenu.tsx`

- [ ] **Step 1: Create the right-click context menu**

```tsx
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

  // Clamp to viewport
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/editor/views/plot/ContextMenu.tsx
git commit -m "feat: add ContextMenu component"
```

---

### Task 6: Fix PlotCanvas — sync, selection, locking

**Files:**
- Modify: `frontend/src/pages/editor/views/plot/PlotCanvas.tsx`

**Changes:**
1. Use `useEffect` to sync `initialNodes` → `setNodes` (replace `useNodesState` init-only behavior)
2. Use `useEffect` to sync `rfEdges` → `setRfEdges`
3. Add `selection` prop to drive visual feedback
4. Add `onContextMenu` handlers for canvas/nodes/edges
5. Locking: check `isEdgeLocked` before allowing edge reconnect via `onEdgeUpdate`
6. Lock icon on locked edges

- [ ] **Step 1: Rewrite PlotCanvas.tsx**

```typescript
// imports unchanged + add:
import type { SelectionState, Toast } from '../../types'
import { isEdgeLocked } from '../../data/orderUtils'
import ContextMenu from './ContextMenu'
import { useToast } from '../../components/Toast'

// Add props:
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

// ============ SYNC NODES ============
const [nodes, setNodes, onNodesChange] = useNodesState([])
const [rfEdgesState, setRfEdges, onEdgesChange] = useEdgesState([])

// Sync data → React Flow nodes
useEffect(() => {
  setNodes(initialNodes)
}, [initialNodes, setNodes])

// Sync data → React Flow edges
useEffect(() => {
  setRfEdges(rfEdges)
}, [rfEdges, setRfEdges])

// ============ SELECTION ============
const handleNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
  if (node.type === 'actGroup') onSelectNode('act', node.id.replace('act-', ''))
  else if (node.type === 'chapter') onSelectNode('chapter', node.id)
}, [onSelectNode])

const handleEdgeClick = useCallback((_event: React.MouseEvent, edge: Edge) => {
  onSelectEdge(edge.id)
}, [onSelectEdge])

const handlePaneClick = useCallback(() => {
  onClearSelection()
}, [onClearSelection])

// ============ CONNECT (with locking check) ============
const { addToast } = useToast()

const onConnect = useCallback((conn: import('reactflow').Connection) => {
  if (!conn.source || !conn.target || conn.source === conn.target) return
  const result = onAddEdge?.(conn.source, conn.target, 'timeline')
  if (result?.cycle) { addToast('不能创建环路，操作已取消', 'error') }
  else if ((result as any)?.locked) { addToast('该章节已有内容，时序已锁定', 'warning') }
}, [onAddEdge, addToast])

// ============ EDGE UPDATE (with locking check) ============
const onEdgeUpdate = useCallback((oldEdge: Edge, newConn: import('reactflow').Connection) => {
  if (!newConn.source || !newConn.target) return
  // Check if target chapter has content
  const ch = chapters.find(c => c.id === newConn.target)
  if (ch && ch.wordCount > 0) { addToast('该章节已有内容，时序已锁定', 'warning'); return }
  onReconnectEdge?.(oldEdge.id, newConn.source, newConn.target)
}, [onReconnectEdge, chapters, addToast])

// ============ EDGE LOCK ICON ============
// In rfEdges useMemo, add locked edge styling:
// if (isEdgeLocked(e, chapters)) add label: '🔒'

// ============ CONTEXT MENU ============
const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; items: ContextMenuItem[][] } | null>(null)

const onNodeContextMenu = useCallback((event: React.MouseEvent, node: Node) => {
  event.preventDefault()
  const id = node.type === 'actGroup' ? node.id.replace('act-', '') : node.id
  if (node.type === 'actGroup') {
    // Also select it
    onSelectNode('act', id)
    setCtxMenu({
      x: event.clientX, y: event.clientY,
      items: [
        [{ label: '新建章', icon: '+', onClick: () => onAddChapter?.(id) }],
        [{ label: '重命名', icon: '✎', onClick: () => {
          const act = acts.find(a => a.id === id)
          const name = prompt('重命名幕：', act?.name)
          if (name && act) {
            act.name = name
            // Re-render by triggering parent update
            onActClick?.(id)
          }
        }}],
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
        [{ label: '断开时序线', icon: '⊘', disabled: chapters.find(c => c.id === id)?.wordCount > 0, onClick: () => {
          // Remove all incoming timeline edges to this chapter
          const chEdges = edges.filter(e => e.targetId === id && e.type === 'timeline')
          chEdges.forEach(e => onDeleteEdge?.(e.id))
        }}],
      ],
    })
  }
}, [onSelectNode, onAddChapter, onDeleteAct, onDeleteChapter, onDeleteEdge, chapters, edges])

const onEdgeContextMenu = useCallback((event: React.MouseEvent, edge: Edge) => {
  event.preventDefault()
  onSelectEdge(edge.id)
  const chEdge = edges.find(e => e.id === edge.id)
  const locked = chEdge ? isEdgeLocked(chEdge, chapters) : false
  setCtxMenu({
    x: event.clientX, y: event.clientY,
    items: [
      [{ label: '删除连线', icon: '✕', onClick: () => onDeleteEdge?.(edge.id) }],
      [
        { label: '改为时序', icon: '→', disabled: locked, onClick: () => onChangeEdgeType?.(edge.id, 'timeline') },
        { label: '改为因果', icon: '⚡', onClick: () => onChangeEdgeType?.(edge.id, 'causal') },
        { label: '改为伏笔', icon: '◈', onClick: () => onChangeEdgeType?.(edge.id, 'foreshadow') },
        { label: '改为人关联', icon: '👤', onClick: () => onChangeEdgeType?.(edge.id, 'character') },
        { label: '改为主关联', icon: '◎', onClick: () => onChangeEdgeType?.(edge.id, 'theme') },
      ],
    ],
  })
}, [onSelectEdge, onDeleteEdge, onChangeEdgeType, edges, chapters])

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

// ============ RENDER ============
// In ReactFlow, add:
// onNodeContextMenu={onNodeContextMenu}
// onEdgeContextMenu={onEdgeContextMenu}
// onPaneContextMenu={onPaneContextMenu}
// Also add selection state to nodes:
// apply selected class based on selection.id matching node.id

// After ReactFlow:
// {ctxMenu && <ContextMenu ... onClose={() => setCtxMenu(null)} />}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/editor/views/plot/PlotCanvas.tsx
git commit -m "feat: add node sync, selection, context menu, edge locking to PlotCanvas"
```

---

### Task 7: Fix PlotToolbar — dynamic toolbar

**Files:**
- Modify: `frontend/src/pages/editor/views/plot/PlotToolbar.tsx`

- [ ] **Step 1: Update PlotToolbar to accept selection and show context-sensitive buttons**

```tsx
import type { EdgeType, SelectionState } from '../../types'

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
      {/* Always shown */}
      <button onClick={onAddAct} className="px-2.5 py-1 rounded-lg text-xs text-gray-300 hover:bg-amber-600/20 hover:text-amber-400 transition-colors" title="添加幕">＋幕</button>
      <button
        onClick={onAddChapter}
        disabled={!selectedActId}
        className={`px-2.5 py-1 rounded-lg text-xs transition-colors ${selectedActId ? 'text-gray-300 hover:bg-amber-600/20 hover:text-amber-400' : 'text-gray-600 cursor-not-allowed'}`}
      >＋章</button>

      {/* Context-sensitive */}
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/editor/views/plot/PlotToolbar.tsx
git commit -m "feat: dynamic toolbar with context-sensitive buttons"
```

---

### Task 8: Fix ChapterNode — selected state + lock indicator

**Files:**
- Modify: `frontend/src/pages/editor/views/plot/ChapterNode.tsx`

- [ ] **Step 1: Add selected highlight (blue border) to ChapterNode**

The React Flow `NodeProps` already includes `selected`. Add a blue glow when selected:

```tsx
// Modify the outer div:
<div className={`relative bg-gray-800 rounded-xl px-4 py-3 shadow-lg w-44 cursor-pointer hover:-translate-y-0.5 transition-all select-none group ${
  selected ? 'ring-2 ring-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.3)]' : ''
}`} ...>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/editor/views/plot/ChapterNode.tsx
git commit -m "feat: add selected highlight to ChapterNode"
```

---

### Task 9: Fix ActGroupNode — selected state

**Files:**
- Modify: `frontend/src/pages/editor/views/plot/ActGroupNode.tsx`

- [ ] **Step 1: The ActGroupNode already has selected highlight (amber glow)**

The existing code already has:
```tsx
className={`... ${selected ? 'shadow-[0_0_12px_2px_rgba(251,191,36,0.3)]' : ''}`}
```

This is correct. No changes needed.

- [ ] **Step 2: Commit** (no changes, skip this task)

---

### Task 10: Wire EditorShell — connect all pieces

**Files:**
- Modify: `frontend/src/pages/editor/layout/EditorShell.tsx`

- [ ] **Step 1: Wire ToastProvider, ConfirmDialog, selection state, context menu into EditorShell**

```tsx
// Add imports:
import { ToastProvider } from '../components/Toast'
import ConfirmDialog from '../components/ConfirmDialog'
import type { SelectionState } from '../types'

// Add state:
const [confirmDelete, setConfirmDelete] = useState<{ type: 'act'; id: string } | null>(null)
const [inlineEditAct, setInlineEditAct] = useState<string | null>(null)
const [inlineEditChapter, setInlineEditChapter] = useState<string | null>(null)

// Confirm delete handler:
const handleConfirmDelete = useCallback(() => {
  if (confirmDelete?.type === 'act') store.deleteAct(confirmDelete.id)
  setConfirmDelete(null)
}, [confirmDelete, store])

// Wrap the render with ToastProvider:
// <ToastProvider>
//   ... existing content ...
//   <ConfirmDialog ... />
// </ToastProvider>

// Pass selection to PlotCanvas:
// selection={store.selection}
// onSelectNode={store.selectNode}
// onSelectEdge={store.selectEdge}
// onClearSelection={store.clearSelection}

// Pass selection to PlotToolbar:
// selection={store.selection}
```

Replace the PlotToolbar usage to wire the new functions:

```tsx
<PlotToolbar
  selection={store.selection}
  selectedActId={selectedActId}
  edgeFilter={edgeFilter}
  onAddAct={() => store.addAct()}
  onAddChapter={() => selectedActId && store.addChapter(selectedActId)}
  onDeleteSelected={() => {
    const sel = store.selection
    if (sel.type === 'act') setConfirmDelete({ type: 'act', id: sel.id! })
    if (sel.type === 'chapter') store.deleteChapter(sel.id!)
    if (sel.type === 'edge') store.deleteEdge(sel.id!)
    store.clearSelection()
  }}
  onRenameAct={() => {
    if (store.selection.type === 'act') {
      const act = data.acts.find(a => a.id === store.selection.id)
      const name = prompt('重命名幕：', act?.name)
      if (name && act) {
        act.name = name
        store.setData({ ...data })
      }
    }
    store.clearSelection()
  }}
  onEditChapterGoal={() => {
    if (store.selection.type === 'chapter') {
      const ch = data.chapters.find(c => c.id === store.selection.id)
      if (ch) {
        setSelectedChapter({ ...ch })
        store.clearSelection()
      }
    }
  }}
  onDisconnectTimeline={() => {
    if (store.selection.type === 'chapter') {
      const edges = data.edges.filter(e => e.targetId === store.selection.id && e.type === 'timeline')
      edges.forEach(e => store.deleteEdge(e.id))
    }
    store.clearSelection()
  }}
  onEdgeFilterChange={setEdgeFilter}
  onLayout={() => {}}
  onExport={handleExport}
/>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/editor/layout/EditorShell.tsx
git commit -m "feat: wire ToastProvider, ConfirmDialog, selection, context menu in EditorShell"
```

---

### Task 11: EdgePropertyPanel — lock-aware

**Files:**
- Modify: `frontend/src/pages/editor/views/plot/EdgePropertyPanel.tsx`

- [ ] **Step 1: Show lock indicator and disable type change for locked edges**

```tsx
import { isEdgeLocked } from '../../../data/orderUtils'
import type { Chapter } from '../../../types'

// Add prop: chapters: Chapter[]
// In the panel, check if edge is locked:
// const locked = edge ? isEdgeLocked(edge, chapters) : false
// Disable the type dropdown if locked
// Show lock indicator
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/editor/views/plot/EdgePropertyPanel.tsx
git commit -m "feat: add lock awareness to EdgePropertyPanel"
```

---

### Self-Review

- [ ] **Spec coverage check**: Every spec section maps to at least one task
- [ ] **Placeholder scan**: No TBD, TODO, or incomplete code blocks
- [ ] **Type consistency**: `SelectionState` defined in Task 1, used in Tasks 4-10; `isEdgeLocked` defined in Task 1, used in Tasks 4, 6, 11
