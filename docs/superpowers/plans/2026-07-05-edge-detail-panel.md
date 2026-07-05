# Edge Detail Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show selected non-timeline plot edges in the same right-side detail panel area used by selected chapters and acts.

**Architecture:** Add a focused `EdgeDetail` component under the plot view, derive selected edge state in `EditorShell`, and remove the old local floating edge property panel from `PlotCanvas`. The feature remains read-focused and derives context from existing `ChapterEdge`, `Chapter`, `Act`, and `Scene` data without expanding the persisted edge model.

**Tech Stack:** React 18, TypeScript, React Flow, Tailwind CSS classes, existing editor store selection state.

---

## File Structure

- Create `frontend/src/pages/editor/views/plot/EdgeDetail.tsx`: right-side detail panel for non-timeline edges. Owns edge type labels, type-specific copy, chapter route cards, derived metrics, and panel actions.
- Modify `frontend/src/pages/editor/layout/EditorShell.tsx`: import `EdgeDetail`, derive selected edge from `store.selection`, render edge panel after act/chapter panels, and clear competing local detail state when an edge is selected.
- Modify `frontend/src/pages/editor/views/plot/PlotCanvas.tsx`: remove `EdgePropertyPanel` import/render/local state, keep edge selection in global store, and suppress right panel opening for timeline edges.
- Leave `frontend/src/pages/editor/views/plot/EdgePropertyPanel.tsx` in place unless no imports remain and the implementation pass chooses to delete it. Deletion is optional because unused files do not affect runtime, but removing it is cleaner if no future references remain.

## Task 1: Add EdgeDetail Component

**Files:**
- Create: `frontend/src/pages/editor/views/plot/EdgeDetail.tsx`

- [ ] **Step 1: Create the component skeleton and helpers**

Add `EdgeDetail.tsx` with these imports, props, labels, and helpers:

```tsx
import type { Act, Chapter, ChapterEdge, EdgeType } from '../../types'

interface EdgeDetailProps {
  edge: ChapterEdge
  chapters: Chapter[]
  acts: Act[]
  onClose: () => void
  onChangeType: (edgeId: string, newType: EdgeType) => void
  onDelete: (edgeId: string) => void
}

const EDGE_TYPE_OPTIONS: { value: EdgeType; label: string }[] = [
  { value: 'timeline', label: '时序主线' },
  { value: 'causal', label: '因果关系' },
  { value: 'foreshadow', label: '伏笔照应' },
  { value: 'character', label: '人物关联' },
  { value: 'theme', label: '主题关联' },
]

const EDGE_TITLES: Record<EdgeType, string> = {
  timeline: '时序主线',
  causal: '因果关系',
  foreshadow: '伏笔照应',
  character: '人物关联',
  theme: '主题关联',
}

const EMPTY_NOTES: Record<Exclude<EdgeType, 'timeline'>, string> = {
  causal: '说明这个事件如何推动后续结果。',
  foreshadow: '说明这里埋下了什么，以及后续如何回收。',
  character: '说明两章之间的人物关系如何变化。',
  theme: '说明两章共享、呼应或对照的主题命题。',
}

const STATUS_LABELS: Record<Chapter['status'], string> = {
  draft: '草稿',
  revising: '修改',
  final: '定稿',
}

function unique(values: string[]) {
  return Array.from(new Set(values.filter(Boolean)))
}

function getPovNames(chapter?: Chapter) {
  return unique(chapter?.scenes.map(scene => scene.povCharacter) ?? [])
}

function getAct(acts: Act[], chapter?: Chapter) {
  if (!chapter) return undefined
  return acts.find(act => act.id === chapter.actId)
}
```

- [ ] **Step 2: Implement reusable chapter cards**

Add this helper below the functions from Step 1:

```tsx
function ChapterCard({ label, chapter, act }: { label: string; chapter?: Chapter; act?: Act }) {
  if (!chapter) {
    return (
      <div className="bg-gray-950/50 border border-red-900/40 rounded-xl p-3">
        <div className="text-[10px] text-red-400 mb-1">{label}</div>
        <div className="text-sm text-gray-400">章节已不存在</div>
      </div>
    )
  }

  return (
    <div className="bg-gray-950/50 border border-gray-800 rounded-xl p-3" style={{ borderLeft: `3px solid ${act?.color ?? '#6b7280'}` }}>
      <div className="text-[10px] text-gray-500 mb-1">{label}</div>
      <div className="text-sm font-medium text-gray-200 truncate">{chapter.title}</div>
      <div className="text-xs text-gray-500 mt-1 line-clamp-2">{chapter.goal || '暂无章节目标'}</div>
      <div className="flex items-center gap-2 mt-2 text-[10px] text-gray-600">
        <span>{act?.name ?? '未分幕'}</span>
        <span>{chapter.scenes.length} 场</span>
        <span>{STATUS_LABELS[chapter.status]}</span>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Implement the type-specific body**

Add this helper below `ChapterCard`:

```tsx
function TypeSpecificContent({ edge, source, target }: { edge: ChapterEdge; source?: Chapter; target?: Chapter }) {
  if (edge.type === 'timeline') return null

  const sourcePovs = getPovNames(source)
  const targetPovs = getPovNames(target)
  const sharedPovs = sourcePovs.filter(name => targetPovs.includes(name))
  const allPovs = unique([...sharedPovs, ...sourcePovs, ...targetPovs])
  const sourceFirstSummary = source?.scenes[0]?.summary
  const targetFirstSummary = target?.scenes[0]?.summary
  const note = edge.label || EMPTY_NOTES[edge.type]

  if (edge.type === 'foreshadow') {
    return (
      <div className="space-y-3">
        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-1">埋设点</div>
          <p className="text-xs text-gray-400 leading-relaxed">{sourceFirstSummary || source?.goal || '暂无埋设说明'}</p>
        </section>
        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-1">回收点</div>
          <p className="text-xs text-gray-400 leading-relaxed">{targetFirstSummary || target?.goal || '暂无回收说明'}</p>
        </section>
        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-1">伏笔说明</div>
          <p className="text-xs text-gray-300 leading-relaxed">{note}</p>
        </section>
      </div>
    )
  }

  if (edge.type === 'character') {
    return (
      <div className="space-y-3">
        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-2">人物线索</div>
          <div className="flex flex-wrap gap-1.5">
            {allPovs.length > 0 ? allPovs.map(name => (
              <span key={name} className={`px-2 py-1 rounded-full text-[10px] ${sharedPovs.includes(name) ? 'bg-amber-600/20 text-amber-300' : 'bg-gray-700 text-gray-400'}`}>{name}</span>
            )) : <span className="text-xs text-gray-500">暂无 POV 人物信息</span>}
          </div>
        </section>
        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-1">关系变化</div>
          <p className="text-xs text-gray-300 leading-relaxed">{note}</p>
        </section>
      </div>
    )
  }

  if (edge.type === 'theme') {
    return (
      <div className="space-y-3">
        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-1">主题说明</div>
          <p className="text-xs text-gray-300 leading-relaxed">{note}</p>
        </section>
        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
          <div className="text-[10px] text-gray-500 mb-1">目标对照</div>
          <p className="text-xs text-gray-400 leading-relaxed">{source?.goal || '源章节暂无目标'} / {target?.goal || '目标章节暂无目标'}</p>
        </section>
      </div>
    )
  }

  return (
    <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3">
      <div className="text-[10px] text-gray-500 mb-1">因果内容</div>
      <p className="text-xs text-gray-300 leading-relaxed">{note}</p>
    </section>
  )
}
```

- [ ] **Step 4: Implement the exported panel**

Add the default export at the bottom of `EdgeDetail.tsx`:

```tsx
export default function EdgeDetail({ edge, chapters, acts, onClose, onChangeType, onDelete }: EdgeDetailProps) {
  const source = chapters.find(chapter => chapter.id === edge.sourceId)
  const target = chapters.find(chapter => chapter.id === edge.targetId)
  const sourceAct = getAct(acts, source)
  const targetAct = getAct(acts, target)
  const sourceIndex = source ? chapters.findIndex(chapter => chapter.id === source.id) : -1
  const targetIndex = target ? chapters.findIndex(chapter => chapter.id === target.id) : -1
  const distance = sourceIndex >= 0 && targetIndex >= 0 ? Math.abs(targetIndex - sourceIndex) : null
  const crossesActs = source && target ? source.actId !== target.actId : false

  return (
    <div className="absolute right-0 top-0 h-full w-96 bg-gray-900/95 backdrop-blur-xl border-l border-gray-800 z-20 flex flex-col shadow-2xl">
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-start justify-between gap-3 mb-2">
          <div>
            <div className="text-[10px] text-gray-500 mb-1">选中连线</div>
            <h3 className="font-medium text-amber-100">{EDGE_TITLES[edge.type]}</h3>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-lg leading-none">✕</button>
        </div>
        <div className="text-xs text-gray-500 line-clamp-2">
          {source?.title ?? edge.sourceId} → {target?.title ?? edge.targetId}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <div className="grid grid-cols-[1fr_auto_1fr] items-stretch gap-2">
          <ChapterCard label={edge.type === 'foreshadow' ? '埋设章节' : '来源章节'} chapter={source} act={sourceAct} />
          <div className="flex items-center text-amber-500 text-sm">→</div>
          <ChapterCard label={edge.type === 'foreshadow' ? '回收章节' : '目标章节'} chapter={target} act={targetAct} />
        </div>

        <div className="grid grid-cols-3 gap-2">
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-lg p-2 text-center">
            <div className="text-xs text-gray-300">{distance === null ? '-' : `跨 ${distance} 章`}</div>
            <div className="text-[10px] text-gray-600 mt-0.5">距离</div>
          </div>
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-lg p-2 text-center">
            <div className="text-xs text-gray-300">{crossesActs ? '跨幕' : '同幕'}</div>
            <div className="text-[10px] text-gray-600 mt-0.5">结构</div>
          </div>
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-lg p-2 text-center">
            <div className="text-xs text-gray-300">{source && target ? '完整' : '缺失'}</div>
            <div className="text-[10px] text-gray-600 mt-0.5">端点</div>
          </div>
        </div>

        <TypeSpecificContent edge={edge} source={source} target={target} />

        <section className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-3 space-y-3">
          <div>
            <label className="text-[10px] text-gray-500 block mb-1">类型</label>
            <select
              value={edge.type}
              onChange={event => onChangeType(edge.id, event.target.value as EdgeType)}
              className="w-full bg-gray-950 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-gray-300 outline-none focus:border-amber-600"
            >
              {EDGE_TYPE_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>

          <button
            onClick={() => onDelete(edge.id)}
            className="w-full px-3 py-1.5 rounded-lg text-xs text-red-400 hover:bg-red-600/20 transition-colors"
          >
            删除连线
          </button>
        </section>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Verify TypeScript for the isolated component**

Run: `docker compose exec -T frontend npx tsc --noEmit`

Expected: TypeScript may still fail because `EdgeDetail` is not imported yet only if linting unused files is configured. In this repo, `tsc --noEmit` should typecheck project files and should pass once the file is syntactically correct.

- [ ] **Step 6: Commit Task 1**

```bash
git add frontend/src/pages/editor/views/plot/EdgeDetail.tsx
git commit -m "feat: add plot edge detail panel"
```

## Task 2: Wire EdgeDetail Into EditorShell

**Files:**
- Modify: `frontend/src/pages/editor/layout/EditorShell.tsx`

- [ ] **Step 1: Import `EdgeDetail`**

Add the import beside the existing plot detail imports:

```tsx
import EdgeDetail from '../views/plot/EdgeDetail'
```

- [ ] **Step 2: Derive selected edge state**

After `const data = store.data`, add:

```tsx
  const selectedEdge = store.selection.type === 'edge'
    ? data.edges.find(edge => edge.id === store.selection.id) ?? null
    : null
```

- [ ] **Step 3: Clear node details when selecting an edge from PlotCanvas**

In the `PlotCanvas` props inside `renderCanvas`, replace:

```tsx
            onSelectEdge={store.selectEdge}
```

with:

```tsx
            onSelectEdge={(edgeId) => {
              setSelectedActId(null)
              setSelectedChapter(null)
              store.selectEdge(edgeId)
            }}
```

- [ ] **Step 4: Keep chapter selection clearing act state and edge selection**

Confirm `handleChapterClick` still calls `store.selectNode('chapter', chapterId)` and sets `selectedActId(null)`. No extra code is needed because `selectNode` replaces edge selection in the store.

- [ ] **Step 5: Render EdgeDetail in the existing right-side detail area**

Replace the right-side panel conditional at lines around the `Chapter/Act detail panel` block with this structure:

```tsx
        {/* Chapter/Act/Edge detail panel */}
        {views.activeViewId === 'narrative-plot' && (
          selectedActId ? (
            <ActDetail
              act={data.acts.find(a => a.id === selectedActId)!}
              chapters={data.chapters.filter(c => c.actId === selectedActId)}
              onClose={() => setSelectedActId(null)}
              onSelectChapter={(chId) => {
                setSelectedActId(null)
                setSelectedChapter(data.chapters.find(c => c.id === chId) ?? null)
              }}
              onSceneSave={handleSceneSave}
              onOpenSceneEditor={(scene) => setEditingScene(scene)}
            />
          ) : selectedChapter ? (
            <ChapterDetail
              chapter={selectedChapter}
              onClose={() => setSelectedChapter(null)}
              onSceneSave={handleSceneSave}
              onChapterSave={handleChapterGoalSave}
              onOpenSceneEditor={(scene) => setEditingScene(scene)}
            />
          ) : selectedEdge && selectedEdge.type !== 'timeline' ? (
            <EdgeDetail
              edge={selectedEdge}
              chapters={data.chapters}
              acts={data.acts}
              onClose={store.clearSelection}
              onChangeType={(edgeId, newType) => {
                const changed = store.changeEdgeType(edgeId, newType)
                if (changed && newType === 'timeline') store.clearSelection()
              }}
              onDelete={(edgeId) => {
                store.deleteEdge(edgeId)
                store.clearSelection()
              }}
            />
          ) : null
        )}
```

This preserves the existing act/chapter JSX and adds edge handling only after them.

- [ ] **Step 6: Verify TypeScript**

Run: `docker compose exec -T frontend npx tsc --noEmit`

Expected: PASS.

- [ ] **Step 7: Commit Task 2**

```bash
git add frontend/src/pages/editor/layout/EditorShell.tsx
git commit -m "feat: show selected edges in side panel"
```

## Task 3: Remove Floating Edge Panel From PlotCanvas

**Files:**
- Modify: `frontend/src/pages/editor/views/plot/PlotCanvas.tsx`
- Optional delete: `frontend/src/pages/editor/views/plot/EdgePropertyPanel.tsx`

- [ ] **Step 1: Remove old panel import**

Delete this import from `PlotCanvas.tsx`:

```tsx
import EdgePropertyPanel from './EdgePropertyPanel'
```

- [ ] **Step 2: Remove local selected edge state**

Delete this state line:

```tsx
  const [selectedRfEdge, setSelectedRfEdge] = useState<string | null>(null)
```

- [ ] **Step 3: Update edge click behavior**

Replace `handleEdgeClick` with:

```tsx
  const handleEdgeClick = useCallback((_event: React.MouseEvent, edge: Edge) => {
    const domainEdge = edges.find(item => item.id === edge.id)
    if (!domainEdge || domainEdge.type === 'timeline') {
      onClearSelection()
      return
    }
    onSelectEdge(edge.id)
  }, [edges, onClearSelection, onSelectEdge])
```

- [ ] **Step 4: Update pane click behavior**

In `handlePaneClick`, delete this line:

```tsx
    setSelectedRfEdge(null)
```

Keep the rest of the function. It already calls `onClearSelection()` when no act group is hit.

- [ ] **Step 5: Remove old floating panel render**

Delete this JSX block from inside `ReactFlow`:

```tsx
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
```

- [ ] **Step 6: Delete unused `EdgePropertyPanel.tsx` if no imports remain**

Run: `rg "EdgePropertyPanel" frontend/src/pages/editor`

If the only match was removed from `PlotCanvas.tsx`, delete `frontend/src/pages/editor/views/plot/EdgePropertyPanel.tsx`.

Expected after deletion: `rg "EdgePropertyPanel" frontend/src/pages/editor` returns no matches.

- [ ] **Step 7: Verify TypeScript**

Run: `docker compose exec -T frontend npx tsc --noEmit`

Expected: PASS.

- [ ] **Step 8: Commit Task 3**

```bash
git add frontend/src/pages/editor/views/plot/PlotCanvas.tsx frontend/src/pages/editor/views/plot/EdgePropertyPanel.tsx
git commit -m "refactor: move edge properties out of floating panel"
```

If `EdgePropertyPanel.tsx` was not deleted, omit it from `git add`.

## Task 4: Manual Verification

**Files:**
- No code files expected unless bugs are found.

- [ ] **Step 1: Compile**

Run: `docker compose exec -T frontend npx tsc --noEmit`

Expected: PASS with no TypeScript errors.

- [ ] **Step 2: Open the app**

Use existing frontend server at `http://localhost:5173`.

Expected: editor loads and the narrative plot canvas is reachable through the bottom navigation.

- [ ] **Step 3: Verify existing chapter and act panels**

Manual checks:

- Click a chapter node. Expected: `ChapterDetail` opens on the right.
- Click blank space inside an act container. Expected: `ActDetail` opens on the right.
- Click blank canvas outside act containers. Expected: right-side panel closes.

- [ ] **Step 4: Verify non-timeline edge panel**

Manual checks:

- Switch connection mode to `因果关系`, or use the existing mock causal edge if visible.
- Click a causal edge. Expected: `EdgeDetail` opens on the right with source/target chapter titles and `因果内容`.
- Create/select a foreshadow edge. Expected: `EdgeDetail` opens with setup/payoff sections.
- Create/select a character edge. Expected: `EdgeDetail` opens with POV character hints.
- Create/select a theme edge. Expected: `EdgeDetail` opens with theme note and chapter goal context.

- [ ] **Step 5: Verify timeline behavior**

Manual check:

- Click a timeline edge. Expected: no right-side edge detail panel opens. Any previously open panel should close.

- [ ] **Step 6: Verify panel actions**

Manual checks:

- Change a non-timeline edge type in `EdgeDetail`. Expected: edge type and label style update on canvas.
- Change a selected edge to `时序主线` only when store constraints allow it. Expected: panel closes after a successful timeline conversion.
- Delete selected edge. Expected: edge disappears and panel closes.

- [ ] **Step 7: Commit fixes if verification found issues**

If any fixes were needed:

```bash
git add frontend/src/pages/editor/views/plot/EdgeDetail.tsx frontend/src/pages/editor/layout/EditorShell.tsx frontend/src/pages/editor/views/plot/PlotCanvas.tsx
git commit -m "fix: polish edge detail panel behavior"
```

If no fixes were needed, do not create an empty commit.

## Self-Review

- Spec coverage: non-timeline right panel is covered by Tasks 1-3; timeline no-panel behavior is covered by Task 3; type-specific content is covered by Task 1; old floating panel removal is covered by Task 3; manual checks are covered by Task 4.
- Placeholder scan: no `TBD`, `TODO`, or unspecified implementation steps remain.
- Type consistency: all component props use existing `Act`, `Chapter`, `ChapterEdge`, and `EdgeType` names from `frontend/src/pages/editor/types.ts`.
