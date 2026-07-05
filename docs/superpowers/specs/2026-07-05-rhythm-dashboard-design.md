# Multi-Dimensional Rhythm Dashboard Design

## Goal

Replace the minimal dot-based rhythm canvas with a multi-dimensional interactive chart that helps writers analyze story pacing across four dimensions: action, suspense, emotion, and humor — plus overall intensity. Each chapter gets a grouped bar, and a data table reveals pacing issues like "high word count + low intensity = dragging."

## Current State

- `RhythmPoint` has only `chapterIndex`, `intensity`, `label`
- `RhythmCanvas` renders colored dots on a line using ReactFlow
- No right-side panel or interaction
- Mock data has 6 points with generic labels

## Recommended Approach

Abandon ReactFlow for the rhythm view. Build a pure SVG chart + HTML table layout that shows per-chapter multi-dimensional intensity. This is a data visualization, not a node/edge canvas.

Add a right-side `RhythmDetail` panel that opens when a chapter bar is clicked, showing a textual breakdown of that chapter's rhythm profile.

## Data Model

Expand `RhythmPoint` with four sub-dimensions:

```ts
export interface RhythmPoint {
  chapterIndex: number
  label: string
  intensity: number    // 1-10 overall
  action: number       // 1-10
  suspense: number     // 1-10
  emotion: number      // 1-10
  humor: number        // 1-10
}
```

## Visualization

### Chart Area (left 2/3)

Custom SVG chart. No external charting library.

- X axis: chapters in order, labeled with short names
- Y axis: 0-10 intensity scale
- Each chapter: stacked/grouped bar of 4 colored segments (orange=action, blue=suspense, pink=emotion, green=humor)
- An overall intensity line overlay connecting the intensity values
- Act separator vertical dashed lines between acts
- Click a bar to select that chapter and open `RhythmDetail`

### Table Area (below chart)

HTML table showing per-chapter metrics:

| Chapter | Words | Intensity | Pace Note |
|---------|-------|-----------|-----------|
| 雨夜来客 | 2100 | 5 | 适中 |
| 密室发现 | 1800 | 4 | 偏慢 — 字数偏多但节奏偏弱 |
| ... | | | |

Pace note logic:
- `words > 2000 && intensity < 5` → "偏慢 — 字数偏多但节奏偏弱"
- `words < 800 && intensity > 7` → "偏快 — 信息量大但展开不足"
- otherwise → "适中"

### Right Panel (RhythmDetail)

When a chapter bar is clicked:
- Chapter name and act
- Radar-style text breakdown of the 4 dimensions
- Word count and pace analysis
- The chapter's goal from `Chapter` model

## Component Design

### Files

- Modify: `frontend/src/pages/editor/types.ts` — expand RhythmPoint
- Modify: `frontend/src/pages/editor/data/mockData.ts` — multi-dimension mock data
- Rewrite: `frontend/src/pages/editor/views/rhythm/RhythmCanvas.tsx` — SVG chart + table
- Create: `frontend/src/pages/editor/views/rhythm/RhythmDetail.tsx` — right panel
- Modify: `frontend/src/pages/editor/layout/EditorShell.tsx` — wire panels
- Delete: `frontend/src/pages/editor/views/rhythm/RhythmNode.tsx` — no longer needed

### Props

`RhythmCanvas`: `{ rhythms: RhythmPoint[], chapters: Chapter[], acts: Act[], onSelectChapter: (index: number) => void }`

`RhythmDetail`: `{ point: RhythmPoint, chapter?: Chapter, act?: Act, wordCount: number, onClose: () => void }`

## Scope

- No external charting library
- No drag interaction on the chart (read-only analysis)
- Click interaction only for selecting a chapter to view details
- Rhythm data is static mock data; no persistence editing in this iteration

## Testing

- TypeScript compile passes
- Chart renders all chapters with colored bars
- Table shows word counts and pace analysis
- Click a bar → right panel opens with rhythm breakdown
- Act separators appear between acts
