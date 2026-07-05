# Edge Detail Panel Design

## Goal

When a non-timeline edge is selected in the plot canvas, the editor should show a right-side detail panel just like it does for selected chapters and acts. The panel should explain what the relationship means in story terms, not only expose technical edge properties.

Timeline edges remain structural ordering links. Selecting a timeline edge should not open the right-side detail panel.

## Current State

- `EditorShell` owns the right-side detail panels for selected acts and chapters.
- `PlotCanvas` owns a local `selectedRfEdge` state and renders `EdgePropertyPanel` as a small floating panel near the bottom right.
- `SelectionState` already supports `type: 'edge'`, but `EditorShell` does not map that selection to a right-side panel.
- `ChapterEdge` currently stores only `id`, `sourceId`, `targetId`, `type`, optional `label`, and handle ids.

## Recommended Approach

Use a single right-side `EdgeDetail` panel for every selected non-timeline edge. This makes edges feel like first-class story objects, matching the existing chapter and act selection model.

The old floating `EdgePropertyPanel` should no longer be the primary details UI. Its useful controls should move into `EdgeDetail`:

- Change relationship type.
- Delete the selected edge.
- Show source and target chapters by title instead of raw ids.

## Selection Behavior

- Clicking a chapter opens `ChapterDetail` and clears act/edge detail state.
- Clicking an act container opens `ActDetail` and clears chapter/edge detail state.
- Clicking a non-timeline edge opens `EdgeDetail` and clears chapter/act detail state.
- Clicking a timeline edge selects the edge visually if useful, but does not open `EdgeDetail`.
- Clicking blank canvas clears all right-side detail panels.
- Right-clicking an edge keeps context menu behavior, but the selected edge should still be reflected in the global selection state.

## Edge Types And Panel Content

### Timeline

No right-side panel.

Reason: timeline edges define chapter order. They are frequent, mechanical, and already influence export/topological order. Opening a detail panel for every timeline edge would add noise.

### Causal

Purpose: explain why one chapter produces pressure, consequence, or motivation for another.

Panel sections:

- Header: `因果关系`, source chapter title -> target chapter title.
- Route: source and target chapter cards with goals and act color accents.
- Cause summary: use `edge.label` if present, otherwise show a generated placeholder like `说明这个事件如何推动后续结果。`
- Structure checks: chapter distance, whether the relationship crosses acts, and whether both chapters still exist.
- Actions: change type, delete edge.

### Foreshadow

Purpose: track setup and payoff.

Panel sections:

- Header: `伏笔照应`, source chapter as setup, target chapter as payoff.
- Setup card: source chapter title, goal, first scene summary when available.
- Payoff card: target chapter title, goal, first scene summary when available.
- Tracking checks: chapter distance, cross-act status, payoff status based on target chapter status.
- Actions: change type, delete edge.

### Character

Purpose: show how a relationship or character thread carries between two chapters.

Panel sections:

- Header: `人物关联`, source chapter -> target chapter.
- Route cards: source and target chapters.
- Character hints: derive visible names from scene `povCharacter` values in both chapters. Show shared POV characters first, then unique POVs.
- Relationship note: use `edge.label` if present, otherwise show a placeholder explaining that this link should describe the character relationship shift.
- Actions: change type, delete edge.

### Theme

Purpose: show thematic echo, contrast, or development between two chapters.

Panel sections:

- Header: `主题关联`, source chapter -> target chapter.
- Route cards: source and target chapters.
- Theme note: use `edge.label` if present, otherwise show a placeholder explaining that this link should describe the shared theme or contrast.
- Context hints: show both chapter goals and status.
- Actions: change type, delete edge.

## Data Strategy

For this iteration, do not expand `ChapterEdge` with new persisted fields. The current domain model only has `label`, so the panel should be read-focused and derive useful context from existing chapters, acts, scenes, and edge type.

This keeps the implementation small and avoids designing persistence for relationship-specific metadata before the app has editing workflows for those fields.

Later, if relationship authoring becomes important, `ChapterEdge` can gain optional fields such as `summary`, `status`, `tags`, `characters`, or type-specific metadata. That is out of scope for this change.

## Component Design

Add a new plot component:

- `frontend/src/pages/editor/views/plot/EdgeDetail.tsx`

Props:

- `edge: ChapterEdge`
- `chapters: Chapter[]`
- `acts: Act[]`
- `onClose: () => void`
- `onChangeType: (edgeId: string, newType: EdgeType) => void`
- `onDelete: (edgeId: string) => void`

The component should be visually consistent with `ChapterDetail` and `ActDetail`: right-aligned, `w-96`, full-height, dark translucent background, left border, close button, scrollable body.

## EditorShell Integration

`EditorShell` should derive the selected edge from `store.selection`:

- `const selectedEdge = store.selection.type === 'edge' ? data.edges.find(...) : null`

Panel priority should be explicit:

- selected act -> `ActDetail`
- selected chapter -> `ChapterDetail`
- selected non-timeline edge -> `EdgeDetail`
- otherwise no panel

When `EdgeDetail` closes, call `store.clearSelection()`.

When a node or act is selected, existing handlers should clear the competing local detail states as they already do for act/chapter. Edge selection should clear `selectedActId` and `selectedChapter`.

## PlotCanvas Integration

`PlotCanvas` should no longer render `EdgePropertyPanel` as the main edge UI. Edge click behavior should be:

- Find the domain edge by React Flow edge id.
- If the domain edge is timeline, select it visually or clear panel state, but do not open details.
- If the domain edge is non-timeline, call `onSelectEdge(edge.id)`.

Because React Flow timeline edges use normal ids in `PlotCanvas`, this can be done directly from `edges.find(e => e.id === edge.id)`.

## Causality Canvas

The causality canvas is read-only and already has a right sidebar for text `Causality[]`. This change is scoped to the plot canvas first.

In a later pass, clicking a causal edge in the causality canvas could open the same `EdgeDetail` panel or reuse its content model. That should not be included in this implementation because the causality canvas currently lays out its own sidebar and uses `elementsSelectable={false}`.

## Error And Empty States

- If either endpoint chapter no longer exists, show a compact missing endpoint state and keep delete available.
- If an edge type has no `label`, show a type-specific placeholder rather than empty space.
- If changing type to timeline is blocked by timeline constraints, preserve existing store behavior and do not close the panel unless the change succeeds.

## Testing

Manual verification:

- Click chapter: chapter right panel opens.
- Click act blank area: act right panel opens.
- Click causal/foreshadow/character/theme edge: edge right panel opens.
- Click timeline edge: no edge detail panel opens.
- Click blank canvas: right panel closes.
- Change selected edge type in the panel.
- Delete selected edge from the panel.
- TypeScript compile passes.
