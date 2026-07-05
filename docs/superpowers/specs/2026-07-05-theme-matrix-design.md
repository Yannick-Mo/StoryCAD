# Theme Matrix Dashboard Design

## Goal

Replace the circular theme circle graph with a chapter×theme matrix table that lets writers verify which themes actually appear in each chapter.

## Data Model

Expand `ThemeItem`:
```ts
export interface ThemeItem {
  name: string
  color: string
  proposition: string        // theme as a philosophical question
  chapterIndices: number[]   // which chapters this theme appears in
}
```

## Layout

```
┌──────────────────────────────────────┐
│ Legend: #自由 #牺牲 #背叛 #救赎      │
├──────────────────────────────────────┤
│ Matrix                    自由 牺牲 背叛 救赎 │
│ 雨夜来客 (2100 字)         ■   □   □   ■  │
│ 密室发现 (1800 字)         ■   ■   □   □  │
│ ...                                    │
├──────────────────────────────────────┤
│ Click a cell → right-side ThemeDetail │
│ Shows: theme proposition, how theme   │
│ appears in this specific chapter      │
└──────────────────────────────────────┘
```

## Right Panel (ThemeDetail)

When a cell is clicked:
- Theme name + color
- Theme proposition
- Chapter name + word count
- Editable note: "该主题在此章中如何体现"

## Component Design

- Rewrite `ThemeCanvas.tsx` → pure HTML table (no ReactFlow)
- Create `ThemeDetail.tsx` → right panel
- Delete `ThemeNode.tsx`
- Keep store data editable via `setData` for the note

## Scope

- No external dependencies
- Table rendering with colored indicators
- Click interaction for opening detail panel
- Read with editable note
