# Chapter Connection Handle Occupancy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce one line per physical chapter connection point while keeping incoming and outgoing lines off the same point.

**Architecture:** Add a small pure helper for handle occupancy and allocation, persist allocated handles on `ChapterEdge`, and integrate allocation into React Flow connect/reconnect/render paths. Timeline ordering and replacement semantics stay in `editorStore`; `PlotCanvas` supplies node positions and user feedback.

**Tech Stack:** React 18, TypeScript, Vite, React Flow, Node 20 via Docker, existing shell verification scripts.

## Global Constraints

- Project root: `/home/yannick/StoryCAD`; frontend root: `/home/yannick/StoryCAD/frontend`.
- Do not change backend APIs or database schema.
- Do not change timeline semantics: no self-connections, no cycles, one incoming timeline and one outgoing timeline per chapter, conflicting timeline edges are replaced.
- A physical chapter side is one of `top`, `right`, `bottom`, or `left`; `s-r` and `t-r` both occupy `right` for the same chapter.
- Each physical side can be occupied by at most one edge total, regardless of incoming/outgoing direction.
- New and reconnected edges must persist `sourceHandle` and `targetHandle`.
- Rendering must prefer persisted handles and must not mutate editor data during render.
- Do not run `git commit` unless the user explicitly authorizes commits in the execution session.

---

## File Structure

- Create `frontend/src/pages/editor/data/handleAllocation.ts`
  - Pure helper module for parsing handle IDs, building node-side occupancy, generating side candidates, and allocating handles.
  - No React or React Flow imports.

- Create `frontend/scripts/verify-handle-allocation.mjs`
  - Node script that transpiles and imports `handleAllocation.ts`, then checks the connection-point rules directly.

- Create `frontend/scripts/verify-editor-store-handles.mjs`
  - Node script that checks `ChapterEdge` and `editorStore` persist handle fields.

- Create `frontend/scripts/verify-plotcanvas-handle-integration.mjs`
  - Node script that checks `PlotCanvas` uses allocation for render, connect, and reconnect flows.

- Modify `frontend/src/pages/editor/types.ts`
  - Add optional `sourceHandle` and `targetHandle` to `ChapterEdge`.

- Modify `frontend/src/pages/editor/data/editorStore.ts`
  - Accept and persist handles in `addEdge` and `reconnectEdge`.
  - Keep existing timeline replacement and topological sorting behavior.

- Modify `frontend/src/pages/editor/views/plot/PlotCanvas.tsx`
  - Import allocation helpers.
  - Use persisted/fallback handles while rendering edges.
  - Allocate handles before creating and reconnecting edges.
  - Show a toast when no physical point is available.

- Existing file `frontend/src/pages/editor/views/plot/ChapterNode.tsx`
  - Must keep all eight handles: `s-t`, `s-r`, `s-b`, `s-l`, `t-t`, `t-r`, `t-b`, `t-l`.

---

### Task 1: Add Pure Handle Allocation Helper

**Files:**
- Create: `frontend/src/pages/editor/data/handleAllocation.ts`
- Create: `frontend/scripts/verify-handle-allocation.mjs`

**Interfaces:**
- Consumes: Existing `ChapterEdge`-like edge shape: `{ id?, sourceId, targetId, type?, sourceHandle?, targetHandle? }`.
- Produces:
  - `type PhysicalSide = 'top' | 'right' | 'bottom' | 'left'`
  - `interface Point { x: number; y: number }`
  - `interface SidePair { sourceSide: PhysicalSide; targetSide: PhysicalSide }`
  - `interface HandlePair { sourceHandle: string; targetHandle: string }`
  - `interface EdgeForHandleAllocation { id?: string; sourceId: string; targetId: string; type?: string; sourceHandle?: string; targetHandle?: string }`
  - `function sideFromHandle(handleId?: string | null): PhysicalSide | null`
  - `function sourceHandleForSide(side: PhysicalSide): string`
  - `function targetHandleForSide(side: PhysicalSide): string`
  - `function candidateSidePairs(sourcePosition: Point, targetPosition: Point): SidePair[]`
  - `function buildHandleOccupancy(edges: EdgeForHandleAllocation[], ignoreEdgeIds?: Iterable<string>): Map<string, Set<PhysicalSide>>`
  - `function isSideOccupied(occupancy: Map<string, Set<PhysicalSide>>, nodeId: string, side: PhysicalSide): boolean`
  - `function getTimelineReplacementEdgeIds(edges: EdgeForHandleAllocation[], sourceId: string, targetId: string, replacingEdgeId?: string): string[]`
  - `function allocateHandles(args: AllocateHandlesArgs): HandlePair | null`

- [ ] **Step 1: Write the failing verification script**

Create `frontend/scripts/verify-handle-allocation.mjs` with this exact content:

```js
import assert from 'node:assert/strict'
import { readFileSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import ts from 'typescript'

const helperSource = readFileSync(
  new URL('../src/pages/editor/data/handleAllocation.ts', import.meta.url),
  'utf8'
)

const output = ts.transpileModule(helperSource, {
  compilerOptions: {
    module: ts.ModuleKind.ES2022,
    target: ts.ScriptTarget.ES2022,
    strict: true,
  },
}).outputText

const tempDir = mkdtempSync(join(tmpdir(), 'storycad-handle-allocation-'))
const modulePath = join(tempDir, 'handleAllocation.mjs')
writeFileSync(modulePath, output)

const {
  allocateHandles,
  buildHandleOccupancy,
  candidateSidePairs,
  getTimelineReplacementEdgeIds,
  isSideOccupied,
  sideFromHandle,
  sourceHandleForSide,
  targetHandleForSide,
} = await import(pathToFileURL(modulePath).href)

assert.equal(sideFromHandle('s-r'), 'right')
assert.equal(sideFromHandle('t-r'), 'right')
assert.equal(sideFromHandle('s-t'), 'top')
assert.equal(sideFromHandle('t-b'), 'bottom')
assert.equal(sideFromHandle('bad-handle'), null)
assert.equal(sourceHandleForSide('left'), 's-l')
assert.equal(targetHandleForSide('left'), 't-l')

assert.deepEqual(
  candidateSidePairs({ x: 0, y: 0 }, { x: 300, y: 20 })[0],
  { sourceSide: 'right', targetSide: 'left' }
)
assert.deepEqual(
  candidateSidePairs({ x: 300, y: 0 }, { x: 0, y: 20 })[0],
  { sourceSide: 'left', targetSide: 'right' }
)
assert.deepEqual(
  candidateSidePairs({ x: 0, y: 0 }, { x: 20, y: 300 })[0],
  { sourceSide: 'bottom', targetSide: 'top' }
)
assert.deepEqual(
  candidateSidePairs({ x: 0, y: 300 }, { x: 20, y: 0 })[0],
  { sourceSide: 'top', targetSide: 'bottom' }
)

const incomingRight = [
  { id: 'incoming', sourceId: 'other', targetId: 'chapter', sourceHandle: 's-l', targetHandle: 't-r' },
]
const occupancy = buildHandleOccupancy(incomingRight)
assert.equal(isSideOccupied(occupancy, 'chapter', 'right'), true)
assert.equal(isSideOccupied(occupancy, 'chapter', 'left'), false)

assert.deepEqual(
  allocateHandles({
    sourceId: 'chapter',
    targetId: 'next',
    sourcePosition: { x: 0, y: 0 },
    targetPosition: { x: 300, y: 0 },
    edges: incomingRight,
  }),
  { sourceHandle: 's-b', targetHandle: 't-t' }
)

const occupiedIdeal = [
  { id: 'existing', sourceId: 'source', targetId: 'old', sourceHandle: 's-r', targetHandle: 't-l' },
]
assert.deepEqual(
  allocateHandles({
    sourceId: 'source',
    targetId: 'target',
    sourcePosition: { x: 0, y: 0 },
    targetPosition: { x: 300, y: 0 },
    edges: occupiedIdeal,
  }),
  { sourceHandle: 's-b', targetHandle: 't-t' }
)

const fullNode = [
  { id: 'top', sourceId: 'a', targetId: 'full', sourceHandle: 's-r', targetHandle: 't-t' },
  { id: 'right', sourceId: 'b', targetId: 'full', sourceHandle: 's-r', targetHandle: 't-r' },
  { id: 'bottom', sourceId: 'c', targetId: 'full', sourceHandle: 's-r', targetHandle: 't-b' },
  { id: 'left', sourceId: 'd', targetId: 'full', sourceHandle: 's-r', targetHandle: 't-l' },
]
assert.equal(
  allocateHandles({
    sourceId: 'new',
    targetId: 'full',
    sourcePosition: { x: 0, y: 0 },
    targetPosition: { x: 300, y: 0 },
    edges: fullNode,
  }),
  null
)

const replacementEdges = [
  { id: 'old', type: 'timeline', sourceId: 'source', targetId: 'old-target', sourceHandle: 's-r', targetHandle: 't-l' },
  { id: 'other', type: 'causal', sourceId: 'other', targetId: 'source', sourceHandle: 's-b', targetHandle: 't-b' },
]
assert.deepEqual(
  getTimelineReplacementEdgeIds(replacementEdges, 'source', 'new-target'),
  ['old']
)
assert.deepEqual(
  allocateHandles({
    sourceId: 'source',
    targetId: 'new-target',
    sourcePosition: { x: 0, y: 0 },
    targetPosition: { x: 300, y: 0 },
    edges: replacementEdges,
    ignoreEdgeIds: ['old'],
  }),
  { sourceHandle: 's-r', targetHandle: 't-l' }
)

console.log('handle allocation checks passed')
```

- [ ] **Step 2: Run the script to verify it fails**

Run:

```bash
cd /home/yannick/StoryCAD/frontend
docker run --rm -v /home/yannick/StoryCAD/frontend:/app -w /app node:20-alpine node scripts/verify-handle-allocation.mjs
```

Expected: FAIL with `ENOENT` for `src/pages/editor/data/handleAllocation.ts`, because the helper does not exist yet.

- [ ] **Step 3: Create the helper implementation**

Create `frontend/src/pages/editor/data/handleAllocation.ts` with this exact content:

```ts
export type PhysicalSide = 'top' | 'right' | 'bottom' | 'left'

export interface Point {
  x: number
  y: number
}

export interface SidePair {
  sourceSide: PhysicalSide
  targetSide: PhysicalSide
}

export interface HandlePair {
  sourceHandle: string
  targetHandle: string
}

export interface EdgeForHandleAllocation {
  id?: string
  sourceId: string
  targetId: string
  type?: string
  sourceHandle?: string
  targetHandle?: string
}

export interface AllocateHandlesArgs {
  sourceId: string
  targetId: string
  sourcePosition: Point
  targetPosition: Point
  edges: EdgeForHandleAllocation[]
  ignoreEdgeIds?: Iterable<string>
}

const SIDE_TO_SUFFIX: Record<PhysicalSide, string> = {
  top: 't',
  right: 'r',
  bottom: 'b',
  left: 'l',
}

const SUFFIX_TO_SIDE: Record<string, PhysicalSide> = {
  t: 'top',
  r: 'right',
  b: 'bottom',
  l: 'left',
}

const OPPOSING_SIDE_PAIRS: SidePair[] = [
  { sourceSide: 'right', targetSide: 'left' },
  { sourceSide: 'bottom', targetSide: 'top' },
  { sourceSide: 'top', targetSide: 'bottom' },
  { sourceSide: 'left', targetSide: 'right' },
]

export function sideFromHandle(handleId?: string | null): PhysicalSide | null {
  if (!handleId) return null
  const suffix = handleId.split('-')[1]
  return suffix ? SUFFIX_TO_SIDE[suffix] ?? null : null
}

export function sourceHandleForSide(side: PhysicalSide): string {
  return `s-${SIDE_TO_SUFFIX[side]}`
}

export function targetHandleForSide(side: PhysicalSide): string {
  return `t-${SIDE_TO_SUFFIX[side]}`
}

function dedupeSidePairs(pairs: SidePair[]): SidePair[] {
  const seen = new Set<string>()
  const result: SidePair[] = []
  for (const pair of pairs) {
    const key = `${pair.sourceSide}:${pair.targetSide}`
    if (seen.has(key)) continue
    seen.add(key)
    result.push(pair)
  }
  return result
}

export function candidateSidePairs(sourcePosition: Point, targetPosition: Point): SidePair[] {
  const dx = targetPosition.x - sourcePosition.x
  const dy = targetPosition.y - sourcePosition.y
  const absDx = Math.abs(dx)
  const absDy = Math.abs(dy)

  let preferred: SidePair
  if (absDx >= absDy && dx > 0) {
    preferred = { sourceSide: 'right', targetSide: 'left' }
  } else if (absDx >= absDy && dx <= 0) {
    preferred = { sourceSide: 'left', targetSide: 'right' }
  } else if (dy > 0) {
    preferred = { sourceSide: 'bottom', targetSide: 'top' }
  } else {
    preferred = { sourceSide: 'top', targetSide: 'bottom' }
  }

  return dedupeSidePairs([preferred, ...OPPOSING_SIDE_PAIRS])
}

function addSide(
  occupancy: Map<string, Set<PhysicalSide>>,
  nodeId: string,
  handleId?: string
) {
  const side = sideFromHandle(handleId)
  if (!side) return
  const sides = occupancy.get(nodeId) ?? new Set<PhysicalSide>()
  sides.add(side)
  occupancy.set(nodeId, sides)
}

export function buildHandleOccupancy(
  edges: EdgeForHandleAllocation[],
  ignoreEdgeIds: Iterable<string> = []
): Map<string, Set<PhysicalSide>> {
  const ignored = new Set(ignoreEdgeIds)
  const occupancy = new Map<string, Set<PhysicalSide>>()

  for (const edge of edges) {
    if (edge.id && ignored.has(edge.id)) continue
    addSide(occupancy, edge.sourceId, edge.sourceHandle)
    addSide(occupancy, edge.targetId, edge.targetHandle)
  }

  return occupancy
}

export function isSideOccupied(
  occupancy: Map<string, Set<PhysicalSide>>,
  nodeId: string,
  side: PhysicalSide
): boolean {
  return occupancy.get(nodeId)?.has(side) ?? false
}

export function getTimelineReplacementEdgeIds(
  edges: EdgeForHandleAllocation[],
  sourceId: string,
  targetId: string,
  replacingEdgeId?: string
): string[] {
  return edges
    .filter(edge =>
      edge.id &&
      edge.id !== replacingEdgeId &&
      edge.type === 'timeline' &&
      (edge.sourceId === sourceId || edge.targetId === targetId)
    )
    .map(edge => edge.id!)
}

export function allocateHandles({
  sourceId,
  targetId,
  sourcePosition,
  targetPosition,
  edges,
  ignoreEdgeIds = [],
}: AllocateHandlesArgs): HandlePair | null {
  const occupancy = buildHandleOccupancy(edges, ignoreEdgeIds)

  for (const pair of candidateSidePairs(sourcePosition, targetPosition)) {
    if (isSideOccupied(occupancy, sourceId, pair.sourceSide)) continue
    if (isSideOccupied(occupancy, targetId, pair.targetSide)) continue
    return {
      sourceHandle: sourceHandleForSide(pair.sourceSide),
      targetHandle: targetHandleForSide(pair.targetSide),
    }
  }

  return null
}
```

- [ ] **Step 4: Run the script to verify it passes**

Run:

```bash
cd /home/yannick/StoryCAD/frontend
docker run --rm -v /home/yannick/StoryCAD/frontend:/app -w /app node:20-alpine node scripts/verify-handle-allocation.mjs
```

Expected output:

```text
handle allocation checks passed
```

- [ ] **Step 5: Commit this task if commits are authorized**

If the user has authorized commits in the execution session, run:

```bash
cd /home/yannick/StoryCAD
git add frontend/src/pages/editor/data/handleAllocation.ts frontend/scripts/verify-handle-allocation.mjs
git commit -m "feat: add chapter handle allocation helper"
```

If commits are not authorized, leave the files uncommitted and note this in the task summary.

---

### Task 2: Persist Handles in Types and Editor Store

**Files:**
- Modify: `frontend/src/pages/editor/types.ts`
- Modify: `frontend/src/pages/editor/data/editorStore.ts`
- Create: `frontend/scripts/verify-editor-store-handles.mjs`

**Interfaces:**
- Consumes from Task 1: `sourceHandle` and `targetHandle` strings allocated by `allocateHandles()`.
- Produces:
  - `ChapterEdge.sourceHandle?: string`
  - `ChapterEdge.targetHandle?: string`
  - `addEdge(sourceId: string, targetId: string, type?: EdgeType, sourceHandle?: string, targetHandle?: string): EdgeResult`
  - `reconnectEdge(edgeId: string, newSource?: string, newTarget?: string, sourceHandle?: string, targetHandle?: string): void`

- [ ] **Step 1: Write the failing verification script**

Create `frontend/scripts/verify-editor-store-handles.mjs` with this exact content:

```js
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const typesSource = readFileSync(new URL('../src/pages/editor/types.ts', import.meta.url), 'utf8')
const storeSource = readFileSync(new URL('../src/pages/editor/data/editorStore.ts', import.meta.url), 'utf8')

assert.match(typesSource, /sourceHandle\?: string/)
assert.match(typesSource, /targetHandle\?: string/)

assert.match(
  storeSource,
  /const addEdge = useCallback\(\(sourceId: string, targetId: string, type: EdgeType = 'timeline', sourceHandle\?: string, targetHandle\?: string\): EdgeResult =>/
)
assert.match(
  storeSource,
  /const newEdge: ChapterEdge = \{ id: uid\(\), sourceId, targetId, type, sourceHandle, targetHandle \}/
)
assert.match(
  storeSource,
  /const reconnectEdge = useCallback\(\(edgeId: string, newSource\?: string, newTarget\?: string, sourceHandle\?: string, targetHandle\?: string\) =>/
)
assert.match(storeSource, /sourceHandle: sourceHandle \?\? e\.sourceHandle/)
assert.match(storeSource, /targetHandle: targetHandle \?\? e\.targetHandle/)

console.log('editor store handle persistence checks passed')
```

- [ ] **Step 2: Run the script to verify it fails**

Run:

```bash
cd /home/yannick/StoryCAD/frontend
docker run --rm -v /home/yannick/StoryCAD/frontend:/app -w /app node:20-alpine node scripts/verify-editor-store-handles.mjs
```

Expected: FAIL with an assertion mentioning `sourceHandle?: string`, because `ChapterEdge` does not persist handles yet.

- [ ] **Step 3: Extend `ChapterEdge`**

In `frontend/src/pages/editor/types.ts`, replace the `ChapterEdge` interface with this exact block:

```ts
export interface ChapterEdge {
  id: string
  sourceId: string
  targetId: string
  type: EdgeType
  label?: string
  sourceHandle?: string
  targetHandle?: string
}
```

- [ ] **Step 4: Update `addEdge` in `editorStore.ts`**

In `frontend/src/pages/editor/data/editorStore.ts`, replace the entire `addEdge` callback with this exact block:

```ts
  const addEdge = useCallback((sourceId: string, targetId: string, type: EdgeType = 'timeline', sourceHandle?: string, targetHandle?: string): EdgeResult => {
    let result: EdgeResult = { edge: null }
    setData(d => {
      if (type === 'timeline') {
        if (wouldCreateCycle(d.edges, sourceId, targetId)) {
          result = { edge: null, cycle: true }
          return d
        }
        // Remove existing outgoing from source and incoming to target
        const filtered = d.edges.filter(e =>
          !(e.type === 'timeline' && (e.sourceId === sourceId || e.targetId === targetId))
        )
        const newEdge: ChapterEdge = { id: uid(), sourceId, targetId, type, sourceHandle, targetHandle }
        result = { edge: newEdge }
        return { ...d, edges: [...filtered, newEdge], chapters: reSort(d.chapters, [...filtered, newEdge]) }
      }
      const newEdge: ChapterEdge = { id: uid(), sourceId, targetId, type, sourceHandle, targetHandle }
      result = { edge: newEdge }
      return { ...d, edges: [...d.edges, newEdge] }
    })
    return result
  }, [reSort])
```

- [ ] **Step 5: Update `reconnectEdge` in `editorStore.ts`**

In `frontend/src/pages/editor/data/editorStore.ts`, replace the entire `reconnectEdge` callback with this exact block:

```ts
  const reconnectEdge = useCallback((edgeId: string, newSource?: string, newTarget?: string, sourceHandle?: string, targetHandle?: string) => {
    setData(d => {
      const edge = d.edges.find(e => e.id === edgeId)
      if (!edge) return d
      const source = newSource ?? edge.sourceId
      const target = newTarget ?? edge.targetId
      if (edge.type === 'timeline') {
        if (wouldCreateCycle(d.edges.filter(e => e.id !== edgeId), source, target)) return d
        // Replace outgoing from new source and incoming to new target
        const filtered = d.edges.filter(e =>
          e.id === edgeId ||
          !(e.type === 'timeline' && (e.sourceId === source || e.targetId === target))
        )
        const newEdges = filtered.map(e => e.id === edgeId ? {
          ...e,
          sourceId: source,
          targetId: target,
          sourceHandle: sourceHandle ?? e.sourceHandle,
          targetHandle: targetHandle ?? e.targetHandle,
        } : e)
        return { ...d, edges: newEdges, chapters: reSort(d.chapters, newEdges) }
      }
      return {
        ...d,
        edges: d.edges.map(e => e.id === edgeId ? {
          ...e,
          sourceId: source,
          targetId: target,
          sourceHandle: sourceHandle ?? e.sourceHandle,
          targetHandle: targetHandle ?? e.targetHandle,
        } : e),
      }
    })
  }, [reSort])
```

- [ ] **Step 6: Run the script to verify it passes**

Run:

```bash
cd /home/yannick/StoryCAD/frontend
docker run --rm -v /home/yannick/StoryCAD/frontend:/app -w /app node:20-alpine node scripts/verify-editor-store-handles.mjs
```

Expected output:

```text
editor store handle persistence checks passed
```

- [ ] **Step 7: Run TypeScript build for this task**

Run:

```bash
cd /home/yannick/StoryCAD
docker compose exec -T frontend npm run build
```

Expected output includes:

```text
✓ built
```

- [ ] **Step 8: Commit this task if commits are authorized**

If the user has authorized commits in the execution session, run:

```bash
cd /home/yannick/StoryCAD
git add frontend/src/pages/editor/types.ts frontend/src/pages/editor/data/editorStore.ts frontend/scripts/verify-editor-store-handles.mjs
git commit -m "feat: persist chapter edge handles"
```

If commits are not authorized, leave the files uncommitted and note this in the task summary.

---

### Task 3: Integrate Allocation into PlotCanvas Rendering and Connections

**Files:**
- Modify: `frontend/src/pages/editor/views/plot/PlotCanvas.tsx`
- Create: `frontend/scripts/verify-plotcanvas-handle-integration.mjs`

**Interfaces:**
- Consumes from Task 1:
  - `allocateHandles(args): HandlePair | null`
  - `getTimelineReplacementEdgeIds(edges, sourceId, targetId, replacingEdgeId?): string[]`
- Consumes from Task 2:
  - `onAddEdge(sourceId, targetId, type, sourceHandle, targetHandle)`
  - `onReconnectEdge(edgeId, sourceId, targetId, sourceHandle, targetHandle)`
  - `ChapterEdge.sourceHandle` and `ChapterEdge.targetHandle`
- Produces:
  - New edges use allocated, persisted handles.
  - Reconnected edges use allocated, persisted handles.
  - Rendered old edges use persisted handles when present and fallback handles when absent.

- [ ] **Step 1: Write the failing verification script**

Create `frontend/scripts/verify-plotcanvas-handle-integration.mjs` with this exact content:

```js
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('../src/pages/editor/views/plot/PlotCanvas.tsx', import.meta.url), 'utf8')

assert.match(source, /import \{ allocateHandles, getTimelineReplacementEdgeIds \} from '\.\.\/\.\.\/data\/handleAllocation'/)
assert.match(source, /onAddEdge\?: \(sourceId: string, targetId: string, type\?: EdgeType, sourceHandle\?: string, targetHandle\?: string\) => EdgeResult/)
assert.match(source, /onReconnectEdge\?: \(edgeId: string, newSource\?: string, newTarget\?: string, sourceHandle\?: string, targetHandle\?: string\) => void/)
assert.match(source, /const displayEdges: ChapterEdge\[] = \[]/)
assert.match(source, /let sourceHandle = e\.sourceHandle/)
assert.match(source, /let targetHandle = e\.targetHandle/)
assert.match(source, /allocateHandles\(\{[\s\S]*sourceId: e\.sourceId,[\s\S]*targetId: e\.targetId,[\s\S]*edges: displayEdges,[\s\S]*\}\)/)
assert.match(source, /sourceHandle,[\s\S]*targetHandle,[\s\S]*type: 'bezier'/)
assert.match(source, /const ignoreEdgeIds = getTimelineReplacementEdgeIds\(edges, conn\.source, conn\.target\)/)
assert.match(source, /节点连接点已满，无法创建连线/)
assert.match(source, /conn\.source, conn\.target, 'timeline', allocation\.sourceHandle, allocation\.targetHandle/)
assert.match(source, /oldEdge\.id, newConn\.source, newConn\.target, allocation\.sourceHandle, allocation\.targetHandle/)

console.log('plot canvas handle integration checks passed')
```

- [ ] **Step 2: Run the script to verify it fails**

Run:

```bash
cd /home/yannick/StoryCAD/frontend
docker run --rm -v /home/yannick/StoryCAD/frontend:/app -w /app node:20-alpine node scripts/verify-plotcanvas-handle-integration.mjs
```

Expected: FAIL because `PlotCanvas.tsx` does not import or use `allocateHandles` yet.

- [ ] **Step 3: Add allocation imports**

In `frontend/src/pages/editor/views/plot/PlotCanvas.tsx`, add this import below the existing `getBestHandle` import:

```ts
import { allocateHandles, getTimelineReplacementEdgeIds } from '../../data/handleAllocation'
```

- [ ] **Step 4: Update `PlotCanvasProps` callback signatures**

In `frontend/src/pages/editor/views/plot/PlotCanvas.tsx`, replace these prop lines:

```ts
  onAddEdge?: (sourceId: string, targetId: string, type?: EdgeType) => EdgeResult
  onReconnectEdge?: (edgeId: string, newSource?: string, newTarget?: string) => void
```

with:

```ts
  onAddEdge?: (sourceId: string, targetId: string, type?: EdgeType, sourceHandle?: string, targetHandle?: string) => EdgeResult
  onReconnectEdge?: (edgeId: string, newSource?: string, newTarget?: string, sourceHandle?: string, targetHandle?: string) => void
```

- [ ] **Step 5: Replace rendered edge handle resolution**

In `frontend/src/pages/editor/views/plot/PlotCanvas.tsx`, replace the entire `const rfEdges: Edge[] = useMemo(() => { ... }, [edges, initialNodes, selection])` block with this exact block:

```ts
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
```

- [ ] **Step 6: Replace `onConnect`**

In `frontend/src/pages/editor/views/plot/PlotCanvas.tsx`, replace the existing `onConnect` callback with this exact block:

```ts
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
```

- [ ] **Step 7: Replace `onEdgeUpdate`**

In `frontend/src/pages/editor/views/plot/PlotCanvas.tsx`, replace the existing `onEdgeUpdate` callback with this exact block:

```ts
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
```

- [ ] **Step 8: Run the script to verify it passes**

Run:

```bash
cd /home/yannick/StoryCAD/frontend
docker run --rm -v /home/yannick/StoryCAD/frontend:/app -w /app node:20-alpine node scripts/verify-plotcanvas-handle-integration.mjs
```

Expected output:

```text
plot canvas handle integration checks passed
```

- [ ] **Step 9: Run TypeScript build for this task**

Run:

```bash
cd /home/yannick/StoryCAD
docker compose exec -T frontend npm run build
```

Expected output includes:

```text
✓ built
```

- [ ] **Step 10: Commit this task if commits are authorized**

If the user has authorized commits in the execution session, run:

```bash
cd /home/yannick/StoryCAD
git add frontend/src/pages/editor/views/plot/PlotCanvas.tsx frontend/scripts/verify-plotcanvas-handle-integration.mjs
git commit -m "feat: allocate unique chapter connection handles"
```

If commits are not authorized, leave the files uncommitted and note this in the task summary.

---

### Task 4: Final Regression and Runtime Verification

**Files:**
- Verify: `frontend/scripts/verify-chapter-handles.mjs`
- Verify: `frontend/scripts/verify-handle-allocation.mjs`
- Verify: `frontend/scripts/verify-editor-store-handles.mjs`
- Verify: `frontend/scripts/verify-plotcanvas-handle-integration.mjs`
- Verify: `frontend/src/pages/editor/views/plot/ChapterNode.tsx`
- Verify: `frontend/src/pages/editor/views/plot/PlotCanvas.tsx`
- Verify: `frontend/src/pages/editor/data/editorStore.ts`
- Verify: `frontend/src/pages/editor/data/handleAllocation.ts`

**Interfaces:**
- Consumes all interfaces from Tasks 1-3.
- Produces verified feature state: scripts pass, TypeScript build passes, Docker-served editor route returns HTTP 200.

- [ ] **Step 1: Run all handle verification scripts**

Run:

```bash
cd /home/yannick/StoryCAD/frontend
docker run --rm -v /home/yannick/StoryCAD/frontend:/app -w /app node:20-alpine sh -c "node scripts/verify-chapter-handles.mjs && node scripts/verify-handle-allocation.mjs && node scripts/verify-editor-store-handles.mjs && node scripts/verify-plotcanvas-handle-integration.mjs"
```

Expected output includes:

```text
handle allocation checks passed
editor store handle persistence checks passed
plot canvas handle integration checks passed
```

`verify-chapter-handles.mjs` has no success output; it passes by exiting with code 0.

- [ ] **Step 2: Run the frontend build**

Run:

```bash
cd /home/yannick/StoryCAD
docker compose exec -T frontend npm run build
```

Expected output includes:

```text
✓ built
```

- [ ] **Step 3: Confirm Docker services are running**

Run:

```bash
cd /home/yannick/StoryCAD
docker compose ps
```

Expected output includes running services for:

```text
storycad-frontend-1
storycad-backend-1
storycad-db-1
storycad-redis-1
storycad-neo4j-1
```

- [ ] **Step 4: Confirm the editor route is served**

Run:

```bash
curl -sS -I http://localhost:5173/projects/b488108a-86fc-40de-894f-c475367c564e
```

Expected output begins with:

```text
HTTP/1.1 200 OK
```

- [ ] **Step 5: Inspect the working tree for intended files**

Run:

```bash
cd /home/yannick/StoryCAD
git status --short frontend/src/pages/editor/views/plot/ChapterNode.tsx frontend/src/pages/editor/views/plot/PlotCanvas.tsx frontend/src/pages/editor/data/editorStore.ts frontend/src/pages/editor/data/handleAllocation.ts frontend/src/pages/editor/types.ts frontend/scripts/verify-chapter-handles.mjs frontend/scripts/verify-handle-allocation.mjs frontend/scripts/verify-editor-store-handles.mjs frontend/scripts/verify-plotcanvas-handle-integration.mjs docs/superpowers/specs/2026-07-04-connection-handles-design.md docs/superpowers/plans/2026-07-04-connection-handles.md
```

Expected: only these planned files appear for this feature and the earlier handle-completion fix/spec/plan.

- [ ] **Step 6: Commit final verification state if commits are authorized**

If the user has authorized commits and earlier task commits were not made, run one final commit:

```bash
cd /home/yannick/StoryCAD
git add frontend/src/pages/editor/views/plot/ChapterNode.tsx frontend/src/pages/editor/views/plot/PlotCanvas.tsx frontend/src/pages/editor/data/editorStore.ts frontend/src/pages/editor/data/handleAllocation.ts frontend/src/pages/editor/types.ts frontend/scripts/verify-chapter-handles.mjs frontend/scripts/verify-handle-allocation.mjs frontend/scripts/verify-editor-store-handles.mjs frontend/scripts/verify-plotcanvas-handle-integration.mjs docs/superpowers/specs/2026-07-04-connection-handles-design.md docs/superpowers/plans/2026-07-04-connection-handles.md
git commit -m "feat: enforce unique chapter connection handles"
```

If commits are not authorized, do not commit; report the verified uncommitted changes.

---

## Self-Review

### Spec coverage

- Stable unique physical connection points: Task 1 helper, Task 3 render/connect/reconnect integration.
- `ChapterEdge.sourceHandle` and `ChapterEdge.targetHandle`: Task 2.
- `s-r` and `t-r` share one physical side: Task 1 verification and helper implementation.
- Ideal and fallback allocation: Task 1 `candidateSidePairs()` and `allocateHandles()`.
- Full-node rejection and toast: Task 1 full-node verification, Task 3 warning toast.
- Timeline semantics unchanged: Task 2 keeps existing timeline filtering, cycle check, and `reSort`; Task 3 ignores replaced timeline edges before allocation.
- Non-timeline edges follow occupancy: Task 1 helper applies to all edges, Task 3 uses helper for reconnect; new manual connections still default to timeline as before.
- Rendering prefers persisted handles and does not mutate data: Task 3 `rfEdges` uses `e.sourceHandle`/`e.targetHandle`, with display-only fallback.
- Verification: Task 4 runs all scripts, build, service status, and route smoke check.

### Placeholder scan

No `TBD`, `TODO`, incomplete sections, or unspecified code steps are present.

### Type consistency

The plan consistently uses `sourceHandle?: string`, `targetHandle?: string`, `PhysicalSide`, `HandlePair`, `EdgeForHandleAllocation`, `allocateHandles()`, and `getTimelineReplacementEdgeIds()` across helper, store, and canvas tasks.
