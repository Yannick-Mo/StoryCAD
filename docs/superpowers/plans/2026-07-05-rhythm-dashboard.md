# Rhythm Dashboard Implementation Plan

> **Goal:** Replace dot-based rhythm canvas with SVG multi-dimensional chart + analysis table + right detail panel.

### Task 1: Expand data model and mock data

**Files:** `types.ts`, `mockData.ts`

- Add `action`, `suspense`, `emotion`, `humor` fields to `RhythmPoint`
- Update all 6 mock rhythm points with per-dimension values
- Verify `tsc --noEmit`

### Task 2: Rewrite RhythmCanvas

**Files:** `RhythmCanvas.tsx` (rewrite)

- Remove ReactFlow dependency; use pure SVG
- Accept `rhythms`, `chapters`, `acts`, `onSelectChapter` props
- Render grouped bar chart (4 colored segments per chapter)
- Overlay intensity line
- Act separator dashed lines
- Below chart: HTML table with chapter name | word count | intensity | pace analysis
- Click bar → call `onSelectChapter(chapterIndex)`
- Verify `tsc --noEmit`

### Task 3: Create RhythmDetail panel

**Files:** `RhythmDetail.tsx` (new)

- Right-aligned panel matching ChapterDetail style
- Show chapter name, act, word count
- Four-dimension breakdown (action/suspense/emotion/humor with values)
- Pace analysis text
- Chapter goal
- Verify `tsc --noEmit`

### Task 4: Wire EditorShell and clean up

**Files:** `EditorShell.tsx`, `RhythmNode.tsx` (delete)

- Add `selectedRhythmIndex` state
- Pass chapters/acts to RhythmCanvas
- Render RhythmDetail when rhythm view active
- Delete unused RhythmNode.tsx
- Verify `tsc --noEmit`
