# Editor Refactor: React Flow Multi-View CAD

## Overview
Replace the current StoryCAD editor (`/projects/:id`) with a multi-view narrative CAD interface inspired by the provided HTML design. Uses React Flow for all canvas ("幕布") views.

## Layout Shell
```
+--------------------------------------------------------------------+
| [☰ 大纲]                             当前视图标签                    |
|                                        +--------------------------+|
|                                        |  📄 预览                  ||
|                                        |  ⬇️ 导出                  ||
|                                        +--------------------------+|
|                    +----------------------+     +------------------+|
|                    |                      |     |  📜 全局设定      ||
|                    |   Canvas             |     +------------------+|
|                    |   (React Flow)       |                         |
|  Drawer            |                      |                         |
|  +- 场景列表       |                      |                         |
|  +- 章节/场景      |                      |                         |
|  +- 点击跳转       |                      |                         |
|                    +----------------------+                         |
|  ◄──── 世界 │ 叙事 │ 体验 │ 创作 ────► (底部导航)                    |
+--------------------------------------------------------------------+
```

## Bottom Navigation
4 pillars, each with sub-views shown in a floating panel above the nav bar:
- **世界 (World)**: 地图与势力, 规则体系, 历史年表
- **叙事 (Narrative)**: 情节幕布, 人物幕布, 因果幕布, 节奏幕布, 主题幕布
- **体验 (Experience)**: 信息释放, POV策略
- **创作 (Creation)**: 灵感碎片, 进度看板, 版本日志

Click a pillar → show sub-panel. Click sub-view → switch canvas. Click active pillar → hide sub-panel.

## React Flow Canvas Views
All canvas views use React Flow with custom node types:

| View | Node Types | Edge Types | Layout |
|------|-----------|------------|--------|
| 情节幕布 | ChapterNode (card w/ goal, title, tags) | Directed arrows | dagre |
| 人物幕布 | CharacterNode (pill/badge) | Relationship lines (colored) | Force-directed |
| 因果幕布 | CauseNode, EffectNode | Causal arrows | Left-to-right |
| 节奏幕布 | RhythmNode (emotion markers) | Curve | Horizontal timeline |
| 主题幕布 | ThemeNode (tag cards) | Association lines | Freeform |

## Non-Canvas Views
Plain React components: MapView, RulesView, HistoryView, InfoControlView, PovControlView, InspirationView, KanbanView, ChangelogView.

## Modals
- **PreviewModal**: Chapter-by-chapter preview with pagination (prev/next), export to TXT
- **SceneEditor**: Overlay for editing individual scene content + AI generation button

## Left Drawer
Toggle via ☰ 大纲 button. Lists chapters/scenes. Click item → switch to plot canvas, highlight node.

## File Structure
```
pages/editor/
  index.tsx                     # Editor entry, mounts EditorShell
  layout/
    EditorShell.tsx             # Layout orchestrator
    BottomNav.tsx               # 4-pillar nav + sub-panel
    LeftDrawer.tsx              # Scene outline drawer
    ActionButtons.tsx           # Preview, Export, Global Setting
  views/
    plot/       PlotCanvas.tsx, ChapterNode.tsx
    character/  CharCanvas.tsx, CharacterNode.tsx
    causality/  CausalityCanvas.tsx, CauseNode.tsx, EffectNode.tsx
    rhythm/     RhythmCanvas.tsx, RhythmNode.tsx
    theme/      ThemeCanvas.tsx, ThemeNode.tsx
    info/       MapView.tsx, RulesView.tsx, HistoryView.tsx,
                InfoControlView.tsx, PovControlView.tsx,
                InspirationView.tsx, KanbanView.tsx, ChangelogView.tsx
  modals/
    PreviewModal.tsx
    SceneEditor.tsx
  data/
    mockData.ts                 # All mock data for every view
  hooks/
    useEditorViews.ts           # View switching logic
```

## Data Model (Mock)
```typescript
interface Chapter { id: string; title: string; goal: string; tags: string[]; content: string }
interface Character { id: string; name: string; relations: { targetId: string; type: string }[] }
interface Causality { id: string; cause: string; effect: string }
interface RhythmPoint { chapterIndex: number; intensity: number; label: string }
interface ThemeItem { name: string; color: string; connections: string[] }
interface MockData {
  chapters: Chapter[]
  characters: Character[]
  causalities: Causality[]
  rhythms: RhythmPoint[]
  themes: ThemeItem[]
  world: { name: string; regions: string[] }
  rules: string[]
  history: string[]
  infoControls: { topic: string; revealed: boolean }[]
  pov: { character: string; percentage: number }[]
  inspirations: string[]
  kanban: { stage: string; count: number }[]
  changelog: string[]
}
```

## Key Implementation Details
1. React Flow: `reactflow` package, custom `nodeTypes` per canvas view
2. Each canvas view manages its own React Flow instance (nodes + edges state)
3. Dark theme: Tailwind `gray-950/900/800` with warm accent (`amber-600/500`) matching design file's `#d4a373` / `#f4a261`
4. View switching: `useEditorViews` hook tracks `{ pillar: string, viewId: string }` and renders corresponding component
5. Data is all mock initially; API integration can be layered on later
6. Old editor files (CanvasViewport, ActBar, ConnectionLines, etc.) deleted after new editor is verified

## Non-Goals
- Backend API integration (mock data only)
- Persistence to server
- Real AI generation from scene editor
