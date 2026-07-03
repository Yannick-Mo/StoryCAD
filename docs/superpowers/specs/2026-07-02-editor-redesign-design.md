# Editor Redesign Design Spec

## Overview
Replace the current minimal ProjectPage editor with a rich canvas-based story structure editor
inspired by the reference "编辑页.html", adapted to dark theme.

## Architecture

### User Flow
1. Homepage → "新建项目" → prompt title → `createProject(title)` → navigate to `/projects/:id`
2. Editor loads with blank canvas + side panel open to 📝 素材 tab
3. User fills in story materials (idea, characters, world) → clicks "生成框架"
4. Backend generates framework → canvas renders chapter nodes + side panel populates
5. User refines: click nodes to edit, adjust act structure, use AI agent to assist

### New Files (under src/pages/editor/)
```
src/pages/editor/
├── index.tsx                 ← New ProjectPage (composes all editor components)
├── EditorNavbar.tsx          ← Top toolbar (logo, project name, undo/redo, zoom, save/export/validate)
├── ActBar.tsx                ← Act structure segments (colored, clickable to jump)
├── canvas/
│   ├── CanvasViewport.tsx    ← Infinite canvas (dot-grid, pan/zoom via CSS transforms)
│   ├── ChapterNode.tsx       ← Chapter node card (number dot, title, event, hook, word count)
│   ├── ConnectionLines.tsx   ← SVG layer (arrows between chapters + act dividers)
│   ├── ActGroupBackground.tsx← Colored semi-transparent act zone backgrounds
│   └── TurningPointMarker.tsx← Special markers (inciting/midpoint/darknight/climax)
├── panel/
│   ├── EditorPanel.tsx       ← Floating side panel container (tab switching)
│   ├── MaterialTab.tsx       ← Story material input form + "generate" button
│   ├── RelationsTab.tsx      ← Character relationship diagram
│   ├── HeatmapTab.tsx        ← Chapter intensity heatmap
│   └── ForeshadowTab.tsx     ← Foreshadowing tracker table
├── AgentButton.tsx           ← Floating AI chat button + dialog
└── types.ts                  ← Editor-specific types (ActConfig, Chapter, CanvasState)
```

### Modified Files
- `frontend/src/App.tsx` — update route import path
- `frontend/src/pages/ProjectPage.tsx` — replaced by editor/index.tsx
- `frontend/src/components/Layout.tsx` — may be simplified/removed
- `frontend/src/components/Navbar.tsx` — replaced by EditorNavbar
- `frontend/src/hooks/useProject.ts` — updated for new data shapes

### Deleted Files
- `frontend/src/pages/ProjectPage.tsx` (replaced)
- `frontend/src/components/Layout.tsx` (replaced by editor layout)
- `frontend/src/components/Navbar.tsx` (replaced by EditorNavbar)
- `frontend/src/components/DockLayout.tsx` (replaced)
- `frontend/src/components/panels/` (replaced by editor/panel/)
- `frontend/src/components/views/` (functionality moved into panel tabs)

### Dark Theme Adaptation
| Reference (light) | Dark equivalent |
|---|---|
| bg: #f2f3f7 | bg-gray-950 |
| surface: #ffffff | bg-gray-900 |
| canvas bg: #e9ecf2 | bg-gray-950 |
| dot-grid: #d5d9e2 | #374151 (gray-700) at 20px |
| card-bg: #ffffff | bg-gray-800 |
| border: #dde1e8 | border-gray-700 |
| text: #1e293b | text-gray-100 |
| accent: #4f6ef6 | #4f6ef6 (retained) |
| act1 color: #8b7cf6 | #8b7cf6 (retained) |
| act2a color: #5b9cf5 | #5b9cf5 (retained) |
| act2b color: #ec6b8c | #ec6b8c (retained) |
| act3 color: #f0b443 | #f0b443 (retained) |

## Components Detail

### EditorNavbar
- Sticky top, bg-gray-900/80 backdrop-blur
- Logo + project title (left)
- Undo/Redo buttons
- "适应画布" + zoom controls (- / zoom% / +)
- "💾 保存版本", "📤 导出", "✅ 全局校验" buttons

### ActBar
- 48px height bar below navbar
- Colored segments proportional to chapter count
- Each segment: act name + chapter count tooltip
- Click segment → fly to that act's area on canvas
- Segments separated by subtle dividers

### Canvas (CanvasViewport + sub-components)
- Full remaining viewport height
- Dot-grid background (CSS radial-gradient, 20px spacing)
- Pan: mouse drag (cursor: grab/grabbing)
- Zoom: scroll wheel (0.25x - 2.0x, step 0.1)
- Touch support: pinch zoom
- Act group backgrounds: colored semi-transparent rounded rectangles with labels
- Chapter nodes positioned absolutely in a grid layout per act
- SVG connections layer below nodes
- Keyboard shortcuts: +/- zoom, arrow keys pan, 0 fit, click node to fly

### Chapter Node Card
- 210px wide, bg-gray-800, rounded-xl
- Top: colored dot + "第N章" number
- Title (bold, 14px)
- Event description (gray-400, 11.5px)
- Hook/钩子 (amber accent, bordered)
- Word count (bottom right, gray-500)
- Turning point marker above node (if applicable)
- Click → flyToNode animation + highlight + panel opens detail form

### Right Panel (Floating)
- Fixed width ~340px, slides over canvas
- Peek tab strip visible when collapsed
- 4 tabs: 📝 素材, 👥 人物, 🔥 热图, 🔗 伏笔
- Tab switching with active indicator
- Material tab: form fields + "生成框架" button (disabled on new project until materials filled)
- Data refreshed after AI generation

### AI Agent
- Floating button (bottom-right, above panel)
- Click toggles dialog
- Input field + suggestion chips (@校验/@情节/@命题/@结构)
- Escape to close, click outside to close

## Data Flow

### State Management
- `ProjectContext` remains the top-level provider
- Editor-specific state in local `useEditorState` hook:
  - Canvas transform (scale, tx, ty)
  - Active act/chapter selection
  - Panel tab state & collapse
  - Edit mode (material input vs. viewing)

### API Integration
- `getProject(id)` → loads project metadata + skeleton
- Orchestrator API → generates framework from materials
- `exportJSON/Markdown` → export
- AI agent → direct chat endpoint (future)

## Implementation Order (Sub-projects)

### Phase 1: Editor Shell (UI skeleton)
1. Create editor directory and type definitions
2. EditorNavbar (toolbar with all buttons)
3. ActBar (segmented colored bar)
4. EditorPanel (floating container with tab shell)
5. AgentButton (floating button + dialog)
6. Compose in editor/index.tsx
7. Update App.tsx routing
8. Clean up old files (Layout, Navbar, DockLayout)

### Phase 2: Canvas
1. CanvasViewport (infinite pan/zoom, dot-grid)
2. ActGroupBackground + labels
3. ChapterNode component
4. Layout calculation (grid per act)
5. SVG ConnectionLines
6. TurningPointMarker
7. Fly-to-node animation + highlight
8. Keyboard shortcuts

### Phase 3: Panel Content
1. MaterialTab (form + generate button)
2. RelationsTab (character graph)
3. HeatmapTab (intensity bars)
4. ForeshadowTab (tracker table)
5. Chapter detail editing (node click → panel)

### Phase 4: Data Integration
1. Material submission → orchestrator API
2. Canvas rendering from generated framework
3. Save/load project state
4. Export functionality
5. AI Agent integration
6. Persistent act configuration

## Non-Goals
- Real-time collaboration
- Drag-to-reorder chapters on canvas
- Mobile-optimized canvas (touch works but not primary target)
- Complete rewrite of backend for editor API
