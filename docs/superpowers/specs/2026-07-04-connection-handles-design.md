# Chapter Connection Handle Occupancy Design

Date: 2026-07-04
Project: StoryCAD frontend
Scope: `/home/yannick/StoryCAD/frontend/src/pages/editor` plot canvas chapter connections

## Goal

Chapter-node connections should use stable, unique physical connection points. A chapter has four physical connection points: top, right, bottom, and left. Each physical point may be occupied by at most one edge, regardless of whether that edge enters or exits the chapter.

This ensures:

- one visible connection point never has multiple lines attached;
- incoming and outgoing lines do not share the same physical point;
- cross-act connections remain stable after render, drag, reconnect, and data updates.

## Current context

The plot editor renders chapter and act nodes with React Flow.

Key files:

- `src/pages/editor/views/plot/PlotCanvas.tsx`
- `src/pages/editor/views/plot/ChapterNode.tsx`
- `src/pages/editor/data/editorStore.ts`
- `src/pages/editor/data/orderUtils.ts`
- `src/pages/editor/views/shared/getBestHandle.ts`
- `src/pages/editor/types.ts`

`ChapterNode` now exposes source and target handles on all four sides:

- source: `s-t`, `s-r`, `s-b`, `s-l`
- target: `t-t`, `t-r`, `t-b`, `t-l`

`getBestHandle()` currently chooses handles from chapter positions, but the edge data does not persist chosen handles. As a result, handle choices can be recalculated on render instead of remaining stable.

## Data model

Extend `ChapterEdge` with optional persisted handles:

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

Existing data remains valid because the new fields are optional. Newly created and reconnected edges should store both handles.

## Physical occupancy model

Physical side is derived from the handle suffix:

| Handle IDs | Physical side |
| --- | --- |
| `s-t`, `t-t` | `top` |
| `s-r`, `t-r` | `right` |
| `s-b`, `t-b` | `bottom` |
| `s-l`, `t-l` | `left` |

For a given chapter node, `s-r` and `t-r` both occupy the same physical `right` point. If any edge uses the right side of a node, no other edge may use that node's right side, whether incoming or outgoing.

Act group nodes are layout containers and do not participate in this rule.

## Handle allocation

When creating or reconnecting an edge, the editor should allocate handles as follows:

1. Remove or ignore edges that will be replaced by the operation.
2. Build an occupancy map from the remaining edges.
3. Generate candidate source/target side pairs from the relative positions of source and target chapters.
4. Select the first pair where both physical sides are free.
5. Persist the resulting `sourceHandle` and `targetHandle` on the edge.
6. If no pair is available, reject the operation and show a toast.

### Candidate order

The first candidate should match the geometric direction between the source and target chapters:

| Relative target position | First candidate |
| --- | --- |
| target mostly right | source right -> target left |
| target mostly left | source left -> target right |
| target mostly below | source bottom -> target top |
| target mostly above | source top -> target bottom |

Fallback candidates should try the remaining opposing side pairs in a deterministic order. For target mostly right, for example:

1. source right -> target left
2. source bottom -> target top
3. source top -> target bottom
4. source left -> target right

All candidates must satisfy the occupancy rule.

## Timeline semantics

This design does not change timeline semantics.

Timeline edges still follow the existing rules:

- no self-connections;
- no cycles;
- one outgoing timeline edge per chapter;
- one incoming timeline edge per chapter;
- creating a conflicting timeline replaces the existing conflicting timeline edge;
- timeline changes still affect topological chapter order, preview order, and export order.

When a timeline operation replaces existing timeline edges, those replaced edges must be excluded from occupancy before allocating handles for the new edge. This lets the new edge reuse a side that was only occupied by an edge being removed.

## Non-timeline edges

Non-timeline edges (`causal`, `foreshadow`, `character`, `theme`) do not affect chapter ordering. They do follow the same physical point occupancy rule.

Because each chapter has four physical points, a chapter can have at most four total attached edges across all edge types.

## Rendering

When rendering React Flow edges:

1. Use persisted `edge.sourceHandle` and `edge.targetHandle` when present.
2. For old edge data missing handles, compute a fallback handle pair for display.
3. Do not mutate data during render.
4. New create/reconnect operations should persist handles so newly touched edges remain stable.

## User feedback

Cycle rejection should keep the existing message:

```text
不能创建环路，操作已取消
```

Handle exhaustion or occupied-point rejection should use a clear toast, for example:

```text
节点连接点已满，无法创建连线
```

## Helper boundaries

Add a small, testable helper module for handle allocation. It should not depend on React Flow components.

Suggested responsibilities:

- parse handle IDs to physical sides;
- build node-side occupancy from edges;
- generate candidate side pairs from source/target positions;
- allocate the first free handle pair;
- report allocation failure.

This keeps `PlotCanvas` focused on React Flow event handling and rendering, and keeps `editorStore` focused on data mutations and timeline rules.

## Verification plan

Add or update regression checks covering:

1. every handle returned by routing exists in `ChapterNode`;
2. `s-r` and `t-r` count as the same physical `right` point for one chapter;
3. an occupied ideal side causes allocation to choose a fallback side;
4. a node with all four sides occupied rejects a new edge;
5. timeline replacement excludes removed edges from occupancy before allocating the new edge;
6. frontend TypeScript build succeeds.

## Out of scope

This design does not add:

- manual user selection persistence beyond the allocated handles;
- visual warning badges on occupied handles;
- drag-time preview of unavailable handles;
- backend persistence changes;
- changes to act group behavior;
- changes to timeline ordering semantics.
