# Editor Refactor: React Flow Multi-View CAD

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the StoryCAD editor with a multi-view narrative CAD using React Flow for all canvas views.

**Architecture:** Layout shell with bottom 4-pillar navigation → per-pillar sub-views. Canvas views (幕布) use React Flow with custom node types. Non-canvas views use plain React. All data mocked. Old editor files deleted after replacement.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS, `reactflow` v11, lucide-react

---

## File Inventory

### New Files
```
pages/editor/
  index.tsx                        # EditorPage entry
  types.ts                         # Updated editor types
  layout/
    EditorShell.tsx                # Layout orchestrator
    BottomNav.tsx                  # 4-pillar nav + sub-panel
    LeftDrawer.tsx                 # Scene outline drawer
    ActionButtons.tsx              # Preview/Export/Global Setting
  views/
    plot/
      PlotCanvas.tsx               # React Flow plot canvas
      ChapterNode.tsx              # Custom chapter card node
    character/
      CharCanvas.tsx               # React Flow character canvas
      CharacterNode.tsx            # Custom character pill node
    causality/
      CausalityCanvas.tsx          # React Flow causality canvas
      CauseNode.tsx                # Cause card node
      EffectNode.tsx               # Effect card node
    rhythm/
      RhythmCanvas.tsx             # React Flow rhythm canvas
      RhythmNode.tsx               # Rhythm marker node
    theme/
      ThemeCanvas.tsx              # React Flow theme canvas
      ThemeNode.tsx                # Theme tag node
    info/
      InfoViews.tsx                # All non-canvas view components
  modals/
    PreviewModal.tsx               # Chapter preview with pagination
    SceneEditor.tsx                # Scene editing overlay
  data/
    mockData.ts                    # All mock data for every view
  hooks/
    useEditorViews.ts              # View switching logic
```

### Files to Delete
```
AgentButton.tsx
EditorNavbar.tsx
types.ts (old)
canvas/CanvasViewport.tsx
canvas/ChapterNode.tsx
canvas/ConnectionLines.tsx
canvas/TurningPointMarker.tsx
panel/ChapterEditForm.tsx
panel/EditorPanel.tsx
panel/ForeshadowTab.tsx
panel/HeatmapTab.tsx
panel/MaterialTab.tsx
panel/RelationsTab.tsx
hooks/useCanvas.ts
hooks/useEditorState.ts
hooks/useLayout.ts
data/mockChapters.ts
data/mockCharacters.ts
```

### Files to Modify
```
App.tsx (if routing changes needed — unlikely, same /projects/:id route)
package.json (add reactflow dependency)
```

---

### Task 1: Install React Flow + Define New Types

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/pages/editor/types.ts`

- [ ] **Step 1: Install reactflow**

```bash
cd /home/yannick/StoryCAD/frontend
npm install reactflow
```

- [ ] **Step 2: Write new editor types**

```typescript
// frontend/src/pages/editor/types.ts

// View system
export type Pillar = 'world' | 'narrative' | 'experience' | 'creation'

export interface ViewDef {
  id: string
  label: string
  pillar: Pillar
  type: 'canvas' | 'info'
}

export const VIEWS: ViewDef[] = [
  // World
  { id: 'world-map', label: '🗺️ 地图与势力', pillar: 'world', type: 'info' },
  { id: 'world-rules', label: '⚛️ 规则体系', pillar: 'world', type: 'info' },
  { id: 'world-history', label: '📜 历史年表', pillar: 'world', type: 'info' },
  // Narrative
  { id: 'narrative-plot', label: '🎬 情节幕布', pillar: 'narrative', type: 'canvas' },
  { id: 'narrative-char', label: '👥 人物幕布', pillar: 'narrative', type: 'canvas' },
  { id: 'narrative-causality', label: '🔗 因果幕布', pillar: 'narrative', type: 'canvas' },
  { id: 'narrative-rhythm', label: '📈 节奏幕布', pillar: 'narrative', type: 'canvas' },
  { id: 'narrative-theme', label: '🎭 主题幕布', pillar: 'narrative', type: 'canvas' },
  // Experience
  { id: 'experience-info', label: '👁️ 信息释放', pillar: 'experience', type: 'info' },
  { id: 'experience-pov', label: '🎯 POV策略', pillar: 'experience', type: 'info' },
  // Creation
  { id: 'creation-inspo', label: '💡 灵感碎片', pillar: 'creation', type: 'info' },
  { id: 'creation-kanban', label: '📋 进度看板', pillar: 'creation', type: 'info' },
  { id: 'creation-log', label: '📓 版本日志', pillar: 'creation', type: 'info' },
]

export const PILLAR_VIEWS: Record<Pillar, ViewDef[]> = {
  world: VIEWS.filter(v => v.pillar === 'world'),
  narrative: VIEWS.filter(v => v.pillar === 'narrative'),
  experience: VIEWS.filter(v => v.pillar === 'experience'),
  creation: VIEWS.filter(v => v.pillar === 'creation'),
}

// React Flow node data types
export interface ChapterNodeData {
  goal: string
  title: string
  tags: string[]
  content: string
  intensity: number
}

export interface CharacterNodeData {
  name: string
  role: string
  relations: { targetId: string; type: string }[]
}

export interface CauseNodeData {
  label: string
}

export interface EffectNodeData {
  label: string
}

export interface RhythmNodeData {
  label: string
  intensity: number
  chapterIndex: number
}

export interface ThemeNodeData {
  name: string
  color: string
}

// Mock data types
export interface Chapter {
  id: string
  title: string
  goal: string
  tags: string[]
  content: string
  intensity: number
}

export interface Character {
  id: string
  name: string
  role: string
  relations: { targetId: string; type: string }[]
}

export interface Causality {
  id: string
  cause: string
  effect: string
}

export interface RhythmPoint {
  chapterIndex: number
  intensity: number
  label: string
}

export interface ThemeItem {
  name: string
  color: string
  connections: string[]
}

export interface WorldInfo {
  name: string
  regions: string[]
}

export interface InfoControl {
  topic: string
  revealed: boolean
}

export interface PovInfo {
  character: string
  percentage: number
}

export interface KanbanItem {
  stage: string
  count: number
}

export interface EditorMockData {
  projectTitle: string
  chapters: Chapter[]
  characters: Character[]
  causalities: Causality[]
  rhythms: RhythmPoint[]
  themes: ThemeItem[]
  world: WorldInfo
  rules: string[]
  history: string[]
  infoControls: InfoControl[]
  pov: PovInfo[]
  inspirations: string[]
  kanban: KanbanItem[]
  changelog: string[]
}
```

---

### Task 2: Create Mock Data

**Files:**
- Create: `frontend/src/pages/editor/data/mockData.ts`

- [ ] **Step 1: Write mock data file**

```typescript
// frontend/src/pages/editor/data/mockData.ts
import type { EditorMockData } from '../types'

export const MOCK_DATA: EditorMockData = {
  projectTitle: '迷雾之城',
  chapters: [
    { id: 'ch1', title: '雨夜来客', goal: '引入主角，建立悬念', tags: ['开局', '悬念'], content: '雨幕如织...', intensity: 3 },
    { id: 'ch2', title: '玉牌疑云', goal: '揭示线索，推进调查', tags: ['推理', '线索'], content: '黑衣人被安置在榻上...', intensity: 4 },
    { id: 'ch3', title: '密室发现', goal: '寻找证据', tags: ['冲突', '揭示'], content: '密室中的发现...', intensity: 5 },
    { id: 'ch4', title: '湖心对峙', goal: '质问盟友', tags: ['人际冲突'], content: '湖心亭中...', intensity: 6 },
    { id: 'ch5', title: '信使到来', goal: '接收情报', tags: ['转折'], content: '信使带来消息...', intensity: 4 },
    { id: 'ch6', title: '背叛的誓言', goal: '揭露内鬼', tags: ['背叛', '高潮'], content: '最信任的人...', intensity: 8 },
  ],
  characters: [
    { id: 'c1', name: '林渊', role: 'protagonist', relations: [{ targetId: 'c2', type: '信任裂痕' }, { targetId: 'c3', type: '敌对' }] },
    { id: 'c2', name: '苏绛', role: 'ally', relations: [{ targetId: 'c1', type: '信任裂痕' }, { targetId: 'c3', type: '暗中保护' }] },
    { id: 'c3', name: '沈寒舟', role: 'antagonist', relations: [{ targetId: 'c1', type: '敌对' }, { targetId: 'c2', type: '暗中保护' }] },
  ],
  causalities: [
    { id: 'ca1', cause: '密信被截', effect: '盟友猜忌' },
    { id: 'ca2', cause: '玉牌现世', effect: '灭门案重查' },
    { id: 'ca3', cause: '内鬼泄密', effect: '行动失败' },
  ],
  rhythms: [
    { chapterIndex: 0, intensity: 3, label: '开场' },
    { chapterIndex: 1, intensity: 4, label: '推进' },
    { chapterIndex: 2, intensity: 5, label: '上升' },
    { chapterIndex: 3, intensity: 6, label: '小高潮' },
    { chapterIndex: 4, intensity: 4, label: '缓冲' },
    { chapterIndex: 5, intensity: 8, label: '高潮' },
  ],
  themes: [
    { name: '自由', color: '#d4a373', connections: ['牺牲'] },
    { name: '牺牲', color: '#e76f51', connections: ['自由', '背叛'] },
    { name: '背叛', color: '#9b5de5', connections: ['牺牲'] },
    { name: '救赎', color: '#00b4d8', connections: ['自由'] },
  ],
  world: { name: '苍玄大陆', regions: ['人界', '魔渊', '妖森', '神遗之地'] },
  rules: ['灵基 → 凝脉 → 神游', '万物皆可修炼', '煞气入体则堕魔'],
  history: ['三千年前·神魔之约', '千年前·苏家灭门', '三月前·玉牌重现'],
  infoControls: [
    { topic: '主角身世', revealed: true },
    { topic: '反派动机', revealed: false },
    { topic: '灭门真相', revealed: false },
  ],
  pov: [
    { character: '林渊', percentage: 60 },
    { character: '苏绛', percentage: 25 },
    { character: '沈寒舟', percentage: 15 },
  ],
  inspirations: [
    '雨夜，一把无鞘的剑',
    '破碎的玉牌暗藏地图',
    '湖心亭的棋局暗语',
  ],
  kanban: [
    { stage: '草稿', count: 12 },
    { stage: '修改', count: 5 },
    { stage: '定稿', count: 3 },
  ],
  changelog: [
    '3天前删除感情线分支',
    '1周前新增支线：魔渊密道',
    '2周前调整章节顺序',
  ],
}
```

---

### Task 3: Build View Switching Hook

**Files:**
- Create: `frontend/src/pages/editor/hooks/useEditorViews.ts`

- [ ] **Step 1: Write the hook**

```typescript
// frontend/src/pages/editor/hooks/useEditorViews.ts
import { useState, useCallback } from 'react'
import { VIEWS, type ViewDef, type Pillar } from '../types'

export function useEditorViews() {
  const [activePillar, setActivePillar] = useState<Pillar>('narrative')
  const [activeViewId, setActiveViewId] = useState('narrative-plot')
  const [subPanelOpen, setSubPanelOpen] = useState(false)

  const activeView = VIEWS.find(v => v.id === activeViewId) ?? VIEWS[0]
  const pillarViews = VIEWS.filter(v => v.pillar === activePillar)

  const switchPillar = useCallback((pillar: Pillar) => {
    if (activePillar === pillar && subPanelOpen) {
      setSubPanelOpen(false)
      return
    }
    setActivePillar(pillar)
    setSubPanelOpen(true)
  }, [activePillar, subPanelOpen])

  const switchView = useCallback((viewId: string) => {
    setActiveViewId(viewId)
    setSubPanelOpen(false)
  }, [])

  const closeSubPanel = useCallback(() => {
    setSubPanelOpen(false)
  }, [])

  return {
    activePillar,
    activeView,
    activeViewId,
    subPanelOpen,
    pillarViews,
    switchPillar,
    switchView,
    closeSubPanel,
  }
}
```

---

### Task 4: Build Bottom Navigation

**Files:**
- Create: `frontend/src/pages/editor/layout/BottomNav.tsx`

- [ ] **Step 1: Write BottomNav component**

```typescript
// frontend/src/pages/editor/layout/BottomNav.tsx
import type { Pillar } from '../types'

const PILLARS: { key: Pillar; icon: string; label: string }[] = [
  { key: 'world', icon: '🌍', label: '世界' },
  { key: 'narrative', icon: '📖', label: '叙事' },
  { key: 'experience', icon: '❤️', label: '体验' },
  { key: 'creation', icon: '⚙️', label: '创作' },
]

interface SubOption {
  id: string
  label: string
}

interface BottomNavProps {
  activePillar: Pillar
  activeViewId: string
  subPanelOpen: boolean
  pillarViews: SubOption[]
  onSwitchPillar: (pillar: Pillar) => void
  onSwitchView: (viewId: string) => void
  onCloseSubPanel: () => void
}

export default function BottomNav({
  activePillar, activeViewId, subPanelOpen, pillarViews,
  onSwitchPillar, onSwitchView, onCloseSubPanel,
}: BottomNavProps) {
  return (
    <div className="relative">
      {subPanelOpen && (
        <>
          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2">
            <div className="flex gap-1 bg-gray-800/95 backdrop-blur-xl border border-gray-700 rounded-2xl px-3 py-2 shadow-2xl">
              {pillarViews.map(v => (
                <button
                  key={v.id}
                  onClick={() => onSwitchView(v.id)}
                  className={`px-3 py-1.5 rounded-xl text-sm whitespace-nowrap transition-colors ${
                    activeViewId === v.id
                      ? 'bg-amber-600/20 text-amber-400'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700'
                  }`}
                >
                  {v.label}
                </button>
              ))}
            </div>
          </div>
          <div className="fixed inset-0 z-10" onClick={onCloseSubPanel} />
        </>
      )}
      <nav className="h-14 bg-gray-900/95 backdrop-blur-xl border-t border-gray-800 flex items-center justify-center gap-6 relative z-20">
        {PILLARS.map(p => (
          <button
            key={p.key}
            onClick={() => onSwitchPillar(p.key)}
            className={`flex flex-col items-center gap-0.5 px-4 py-1 rounded-full transition-colors ${
              activePillar === p.key
                ? 'text-amber-400 bg-amber-500/10'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            <span className="text-lg">{p.icon}</span>
            <span className="text-xs font-medium">{p.label}</span>
          </button>
        ))}
      </nav>
    </div>
  )
}
```

---

### Task 5: Build Left Drawer

**Files:**
- Create: `frontend/src/pages/editor/layout/LeftDrawer.tsx`

- [ ] **Step 1: Write LeftDrawer component**

```typescript
// frontend/src/pages/editor/layout/LeftDrawer.tsx
interface LeftDrawerProps {
  open: boolean
  chapters: { id: string; title: string; goal: string }[]
  onClose: () => void
  onSelectChapter: (id: string) => void
}

export default function LeftDrawer({ open, chapters, onClose, onSelectChapter }: LeftDrawerProps) {
  return (
    <>
      {open && <div className="fixed inset-0 z-20" onClick={onClose} />}
      <div
        className={`fixed left-0 top-0 h-full w-64 bg-gray-900/95 backdrop-blur-xl border-r border-gray-800 z-30 transition-transform duration-200 shadow-2xl ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="p-4">
          <h3 className="text-amber-600/80 text-xs uppercase tracking-wider mb-3">📋 当前章节场景</h3>
          <div className="space-y-1">
            {chapters.map(ch => (
              <div
                key={ch.id}
                onClick={() => { onSelectChapter(ch.id); onClose() }}
                className="px-3 py-2 rounded-lg text-sm bg-gray-800/50 border-l-2 border-amber-700/50 hover:bg-gray-700/50 hover:border-amber-500 cursor-pointer transition-colors"
              >
                <div className="text-gray-200">{ch.title}</div>
                <div className="text-gray-500 text-xs mt-0.5">{ch.goal}</div>
              </div>
            ))}
          </div>
          <div className="mt-auto pt-4 text-gray-600 text-xs">点击跳转场景</div>
        </div>
      </div>
    </>
  )
}
```

---

### Task 6: Build Action Buttons

**Files:**
- Create: `frontend/src/pages/editor/layout/ActionButtons.tsx`

- [ ] **Step 1: Write ActionButtons component**

```typescript
// frontend/src/pages/editor/layout/ActionButtons.tsx
interface ActionButtonsProps {
  onPreview: () => void
  onExport: () => void
  onGlobalSetting: () => void
}

export default function ActionButtons({ onPreview, onExport, onGlobalSetting }: ActionButtonsProps) {
  return (
    <div className="absolute right-4 bottom-20 z-10 flex flex-col gap-2">
      <button onClick={onPreview} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs bg-gray-800/80 border border-gray-700 text-gray-300 hover:border-amber-600 hover:text-amber-400 transition-colors backdrop-blur-sm">
        📄 预览已完成内容
      </button>
      <button onClick={onExport} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs bg-gray-800/80 border border-gray-700 text-gray-300 hover:border-amber-600 hover:text-amber-400 transition-colors backdrop-blur-sm">
        ⬇️ 导出完整内容
      </button>
      <button onClick={onGlobalSetting} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs bg-gray-800/80 border border-amber-800/50 text-amber-600 hover:bg-amber-900/20 hover:border-amber-600 transition-colors backdrop-blur-sm">
        📜 全局设定
      </button>
    </div>
  )
}
```

---

### Task 7: Build ChapterNode + PlotCanvas

**Files:**
- Create: `frontend/src/pages/editor/views/plot/ChapterNode.tsx`
- Create: `frontend/src/pages/editor/views/plot/PlotCanvas.tsx`

- [ ] **Step 1: Write ChapterNode custom component**

```typescript
// frontend/src/pages/editor/views/plot/ChapterNode.tsx
import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import type { ChapterNodeData } from '../../types'

function ChapterNode({ data }: NodeProps<ChapterNodeData>) {
  return (
    <div className="bg-gray-800 border-l-4 border-amber-600 rounded-xl px-4 py-3 shadow-lg w-44 cursor-pointer hover:bg-gray-750 hover:-translate-y-0.5 transition-all">
      <Handle type="target" position={Position.Top} className="!bg-amber-500" />
      <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">{data.goal}</div>
      <div className="font-semibold text-amber-100 text-sm">{data.title}</div>
      <div className="flex gap-1.5 mt-2">
        {data.tags.map(t => (
          <span key={t} className="text-[10px] text-gray-500 bg-gray-700/50 px-1.5 py-0.5 rounded">{t}</span>
        ))}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-amber-500" />
    </div>
  )
}

export default memo(ChapterNode)
```

- [ ] **Step 2: Write PlotCanvas React Flow wrapper**

```typescript
// frontend/src/pages/editor/views/plot/PlotCanvas.tsx
import { useMemo, useCallback } from 'react'
import ReactFlow, {
  Background, Controls, MiniMap,
  type Node, type Edge, type NodeTypes,
  useNodesState, useEdgesState, MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'
import ChapterNode from './ChapterNode'
import type { Chapter } from '../../types'

const nodeTypes: NodeTypes = { chapter: ChapterNode }

interface PlotCanvasProps {
  chapters: Chapter[]
}

export default function PlotCanvas({ chapters }: PlotCanvasProps) {
  const initialNodes: Node[] = useMemo(() =>
    chapters.map((ch, i) => ({
      id: ch.id,
      type: 'chapter',
      position: { x: i * 240 + 40, y: 80 },
      data: { goal: ch.goal, title: ch.title, tags: ch.tags, content: ch.content, intensity: ch.intensity },
    })), [chapters])

  const initialEdges: Edge[] = useMemo(() =>
    chapters.slice(0, -1).map((ch, i) => ({
      id: `e-${ch.id}-${chapters[i + 1].id}`,
      source: ch.id,
      target: chapters[i + 1].id,
      animated: true,
      style: { stroke: '#d4a373', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#d4a373' },
    })), [chapters])

  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [edges, , onEdgesChange] = useEdgesState(initialEdges)

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      fitView
      minZoom={0.3}
      maxZoom={2}
    >
      <Background color="#333" gap={20} />
      <Controls className="!bg-gray-800 !border-gray-700 !rounded-lg" />
      <MiniMap
        nodeColor="#d4a373"
        maskColor="rgba(0,0,0,0.7)"
        className="!bg-gray-900 !border-gray-700"
      />
    </ReactFlow>
  )
}
```

---

### Task 8: Build CharacterNode + CharCanvas

**Files:**
- Create: `frontend/src/pages/editor/views/character/CharacterNode.tsx`
- Create: `frontend/src/pages/editor/views/character/CharCanvas.tsx`

- [ ] **Step 1: Write CharacterNode**

```typescript
// frontend/src/pages/editor/views/character/CharacterNode.tsx
import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import type { CharacterNodeData } from '../../types'

function CharacterNode({ data }: NodeProps<CharacterNodeData>) {
  return (
    <div className="bg-gray-800 border-2 border-gray-600 rounded-full px-5 py-2 shadow-lg flex items-center gap-2">
      <Handle type="target" position={Position.Left} className="!bg-gray-400" />
      <span className="font-bold text-amber-100 text-sm">{data.name}</span>
      <span className="text-xs text-gray-500">⚡</span>
      <Handle type="source" position={Position.Right} className="!bg-gray-400" />
    </div>
  )
}

export default memo(CharacterNode)
```

- [ ] **Step 2: Write CharCanvas**

```typescript
// frontend/src/pages/editor/views/character/CharCanvas.tsx
import { useMemo } from 'react'
import ReactFlow, { Background, type Node, type Edge, type NodeTypes, MarkerType } from 'reactflow'
import 'reactflow/dist/style.css'
import CharacterNode from './CharacterNode'
import type { Character } from '../../types'

const nodeTypes: NodeTypes = { character: CharacterNode }

const POSITIONS: Record<number, { x: number; y: number }> = {
  0: { x: 150, y: 200 },
  1: { x: 450, y: 200 },
  2: { x: 300, y: 80 },
}

interface CharCanvasProps {
  characters: Character[]
}

export default function CharCanvas({ characters }: CharCanvasProps) {
  const nodes: Node[] = useMemo(() =>
    characters.map((ch, i) => ({
      id: ch.id,
      type: 'character',
      position: POSITIONS[i] ?? { x: i * 200, y: 150 },
      data: { name: ch.name, role: ch.role, relations: ch.relations },
    })), [characters])

  const edges: Edge[] = useMemo(() =>
    characters.flatMap(ch =>
      ch.relations.map((rel, i) => ({
        id: `e-${ch.id}-${rel.targetId}-${i}`,
        source: ch.id,
        target: rel.targetId,
        label: rel.type,
        style: { stroke: '#8a8a8a' },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#8a8a8a' },
      }))
    ), [characters])

  return (
    <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView minZoom={0.3} maxZoom={2}>
      <Background color="#333" gap={20} />
    </ReactFlow>
  )
}
```

---

### Task 9: Build CauseNode / EffectNode + CausalityCanvas

**Files:**
- Create: `frontend/src/pages/editor/views/causality/CauseNode.tsx`
- Create: `frontend/src/pages/editor/views/causality/EffectNode.tsx`
- Create: `frontend/src/pages/editor/views/causality/CausalityCanvas.tsx`

- [ ] **Step 1: Write CauseNode**

```typescript
// frontend/src/pages/editor/views/causality/CauseNode.tsx
import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import type { CauseNodeData } from '../../types'

function CauseNode({ data }: NodeProps<CauseNodeData>) {
  return (
    <div className="bg-gray-800 border border-amber-700/50 rounded-xl px-4 py-3 shadow-lg">
      <Handle type="source" position={Position.Right} className="!bg-amber-500" />
      <div className="text-xs text-amber-500 mb-1">🔗 因</div>
      <div className="text-sm text-gray-200">{data.label}</div>
    </div>
  )
}

export default memo(CauseNode)
```

- [ ] **Step 2: Write EffectNode**

```typescript
// frontend/src/pages/editor/views/causality/EffectNode.tsx
import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import type { EffectNodeData } from '../../types'

function EffectNode({ data }: NodeProps<EffectNodeData>) {
  return (
    <div className="bg-gray-800 border border-orange-700/50 rounded-xl px-4 py-3 shadow-lg">
      <Handle type="target" position={Position.Left} className="!bg-orange-500" />
      <div className="text-xs text-orange-500 mb-1">⚡ 果</div>
      <div className="text-sm text-gray-200">{data.label}</div>
    </div>
  )
}

export default memo(EffectNode)
```

- [ ] **Step 3: Write CausalityCanvas**

```typescript
// frontend/src/pages/editor/views/causality/CausalityCanvas.tsx
import { useMemo } from 'react'
import ReactFlow, { Background, type Node, type Edge, type NodeTypes, MarkerType } from 'reactflow'
import 'reactflow/dist/style.css'
import CauseNode from './CauseNode'
import EffectNode from './EffectNode'
import type { Causality } from '../../types'

const nodeTypes: NodeTypes = { cause: CauseNode, effect: EffectNode }

interface CausalityCanvasProps {
  causalities: Causality[]
}

export default function CausalityCanvas({ causalities }: CausalityCanvasProps) {
  const nodes: Node[] = useMemo(() =>
    causalities.flatMap((c, i) => [
      { id: `cause-${c.id}`, type: 'cause' as const, position: { x: 40, y: i * 120 + 40 }, data: { label: c.cause } },
      { id: `effect-${c.id}`, type: 'effect' as const, position: { x: 320, y: i * 120 + 40 }, data: { label: c.effect } },
    ]), [causalities])

  const edges: Edge[] = useMemo(() =>
    causalities.map(c => ({
      id: `e-${c.id}`,
      source: `cause-${c.id}`,
      target: `effect-${c.id}`,
      style: { stroke: '#d4a373', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#d4a373' },
    })), [causalities])

  return (
    <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView minZoom={0.3} maxZoom={2}>
      <Background color="#333" gap={20} />
    </ReactFlow>
  )
}
```

---

### Task 10: Build RhythmNode + RhythmCanvas

**Files:**
- Create: `frontend/src/pages/editor/views/rhythm/RhythmNode.tsx`
- Create: `frontend/src/pages/editor/views/rhythm/RhythmCanvas.tsx`

- [ ] **Step 1: Write RhythmNode**

```typescript
// frontend/src/pages/editor/views/rhythm/RhythmNode.tsx
import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import type { RhythmNodeData } from '../../types'

function RhythmNode({ data }: NodeProps<RhythmNodeData>) {
  const color = data.intensity > 6 ? '#e76f51' : data.intensity > 4 ? '#d4a373' : '#00b4d8'
  return (
    <div className="flex flex-col items-center">
      <Handle type="source" position={Position.Bottom} className="!opacity-0" />
      <div className="w-3 h-3 rounded-full shadow-lg" style={{ backgroundColor: color }} />
      <div className="text-[10px] text-gray-400 mt-1 whitespace-nowrap">{data.label}</div>
      <Handle type="target" position={Position.Top} className="!opacity-0" />
    </div>
  )
}

export default memo(RhythmNode)
```

- [ ] **Step 2: Write RhythmCanvas**

```typescript
// frontend/src/pages/editor/views/rhythm/RhythmCanvas.tsx
import { useMemo } from 'react'
import ReactFlow, { Background, type Node, type Edge, type NodeTypes } from 'reactflow'
import 'reactflow/dist/style.css'
import RhythmNode from './RhythmNode'
import type { RhythmPoint } from '../../types'

const nodeTypes: NodeTypes = { rhythm: RhythmNode }

interface RhythmCanvasProps {
  rhythms: RhythmPoint[]
}

export default function RhythmCanvas({ rhythms }: RhythmCanvasProps) {
  const nodes: Node[] = useMemo(() =>
    rhythms.map((r, i) => ({
      id: `r${i}`,
      type: 'rhythm',
      position: { x: i * 160 + 60, y: 200 - r.intensity * 20 },
      data: { label: r.label, intensity: r.intensity, chapterIndex: r.chapterIndex },
    })), [rhythms])

  const edges: Edge[] = useMemo(() =>
    rhythms.slice(0, -1).map((_, i) => ({
      id: `re${i}`,
      source: `r${i}`,
      target: `r${i + 1}`,
      style: { stroke: '#666', strokeWidth: 1.5, strokeDasharray: '4 4' },
      animated: false,
    })), [rhythms])

  return (
    <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView minZoom={0.3} maxZoom={2}>
      <Background color="#333" gap={20} />
    </ReactFlow>
  )
}
```

---

### Task 11: Build ThemeNode + ThemeCanvas

**Files:**
- Create: `frontend/src/pages/editor/views/theme/ThemeNode.tsx`
- Create: `frontend/src/pages/editor/views/theme/ThemeCanvas.tsx`

- [ ] **Step 1: Write ThemeNode**

```typescript
// frontend/src/pages/editor/views/theme/ThemeNode.tsx
import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import type { ThemeNodeData } from '../../types'

function ThemeNode({ data }: NodeProps<ThemeNodeData>) {
  return (
    <div className="relative">
      <Handle type="target" position={Position.Left} className="!bg-gray-500" />
      <div
        className="px-4 py-2 rounded-full text-sm font-medium shadow-lg"
        style={{ backgroundColor: data.color + '20', border: `2px solid ${data.color}`, color: data.color }}
      >
        #{data.name}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-gray-500" />
    </div>
  )
}

export default memo(ThemeNode)
```

- [ ] **Step 2: Write ThemeCanvas**

```typescript
// frontend/src/pages/editor/views/theme/ThemeCanvas.tsx
import { useMemo } from 'react'
import ReactFlow, { Background, type Node, type Edge, type NodeTypes } from 'reactflow'
import 'reactflow/dist/style.css'
import ThemeNode from './ThemeNode'
import type { ThemeItem } from '../../types'

const nodeTypes: NodeTypes = { theme: ThemeNode }

const RADIUS = 140

interface ThemeCanvasProps {
  themes: ThemeItem[]
}

export default function ThemeCanvas({ themes }: ThemeCanvasProps) {
  const nodes: Node[] = useMemo(() =>
    themes.map((t, i) => {
      const angle = (2 * Math.PI * i) / themes.length - Math.PI / 2
      return {
        id: `t${i}`,
        type: 'theme',
        position: { x: 250 + RADIUS * Math.cos(angle), y: 160 + RADIUS * Math.sin(angle) },
        data: { name: t.name, color: t.color, connections: t.connections },
      }
    }), [themes])

  const edges: Edge[] = useMemo(() =>
    themes.flatMap((t, i) =>
      t.connections.map(targetName => {
        const j = themes.findIndex(th => th.name === targetName)
        if (j === -1) return []
        return {
          id: `te${i}-${j}`,
          source: `t${i}`,
          target: `t${j}`,
          style: { stroke: '#666', strokeWidth: 1 },
          animated: false,
        }
      }).flat()
    ), [themes])

  return (
    <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView minZoom={0.3} maxZoom={2}>
      <Background color="#333" gap={20} />
    </ReactFlow>
  )
}
```

---

### Task 12: Build Info Views

**Files:**
- Create: `frontend/src/pages/editor/views/info/InfoViews.tsx`

- [ ] **Step 1: Write all non-canvas view components**

```typescript
// frontend/src/pages/editor/views/info/InfoViews.tsx
import type { WorldInfo, InfoControl, PovInfo, KanbanItem } from '../../types'

export function MapView({ data }: { data: WorldInfo }) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="bg-gray-800/80 rounded-2xl px-8 py-6 text-center">
        <div className="text-3xl mb-2">🗺️</div>
        <div className="text-lg font-medium text-amber-100">{data.name}</div>
        <div className="flex gap-2 mt-3 justify-center">
          {data.regions.map(r => (
            <span key={r} className="px-3 py-1 rounded-full text-xs bg-gray-700 text-gray-300">{r}</span>
          ))}
        </div>
      </div>
    </div>
  )
}

export function RulesView({ data }: { data: string[] }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <span className="text-lg">⚛️ 修炼体系</span>
      <div className="space-y-2">
        {data.map(r => <div key={r} className="bg-gray-800 px-4 py-2 rounded-lg text-sm text-gray-300">{r}</div>)}
      </div>
    </div>
  )
}

export function HistoryView({ data }: { data: string[] }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <span className="text-lg">📜 历史年表</span>
      <div className="space-y-2">
        {data.map(h => <div key={h} className="bg-gray-800 px-4 py-2 rounded-lg text-sm text-gray-300">{h}</div>)}
      </div>
    </div>
  )
}

export function InfoControlView({ data }: { data: InfoControl[] }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <span className="text-lg">👁️ 信息释放</span>
      <div className="space-y-2">
        {data.map(ic => (
          <div key={ic.topic} className="flex items-center gap-3 bg-gray-800 px-4 py-2 rounded-lg text-sm">
            <span className={`w-2 h-2 rounded-full ${ic.revealed ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-gray-300">{ic.topic}</span>
            <span className="text-xs text-gray-500">{ic.revealed ? '已揭示' : '未揭示'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function PovView({ data }: { data: PovInfo[] }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <span className="text-lg">🎯 POV分配</span>
      <div className="space-y-3">
        {data.map(p => (
          <div key={p.character} className="flex items-center gap-3 bg-gray-800 px-4 py-2 rounded-lg text-sm w-64">
            <span className="text-gray-300 w-16">{p.character}</span>
            <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
              <div className="h-full bg-amber-600 rounded-full" style={{ width: `${p.percentage}%` }} />
            </div>
            <span className="text-xs text-gray-400 w-8 text-right">{p.percentage}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function InspirationView({ data }: { data: string[] }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <span className="text-lg">💡 灵感碎片</span>
      <div className="space-y-2">
        {data.map(insp => (
          <div key={insp} className="bg-gray-800/50 border border-dashed border-gray-700 px-4 py-2 rounded-lg text-sm text-gray-400 italic">
            「{insp}」
          </div>
        ))}
      </div>
    </div>
  )
}

export function KanbanView({ data }: { data: KanbanItem[] }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <span className="text-lg">📋 进度看板</span>
      <div className="flex gap-4">
        {data.map(k => (
          <div key={k.stage} className="bg-gray-800 px-5 py-3 rounded-xl text-center min-w-[80px]">
            <div className="text-2xl font-bold text-amber-400">{k.count}</div>
            <div className="text-xs text-gray-400 mt-1">{k.stage}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function ChangelogView({ data }: { data: string[] }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <span className="text-lg">📓 版本日志</span>
      <div className="space-y-2">
        {data.map(entry => (
          <div key={entry} className="bg-gray-800/50 px-4 py-2 rounded-lg text-sm text-gray-400 border-l-2 border-gray-700">
            {entry}
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

### Task 13: Build PreviewModal

**Files:**
- Create: `frontend/src/pages/editor/modals/PreviewModal.tsx`

- [ ] **Step 1: Write PreviewModal**

```typescript
// frontend/src/pages/editor/modals/PreviewModal.tsx
import { useState, useMemo } from 'react'
import type { Chapter } from '../types'

interface PreviewModalProps {
  open: boolean
  chapters: Chapter[]
  onClose: () => void
}

export default function PreviewModal({ open, chapters, onClose }: PreviewModalProps) {
  const [index, setIndex] = useState(0)
  const chapter = chapters[index]

  const prev = () => setIndex(i => Math.max(0, i - 1))
  const next = () => setIndex(i => Math.min(chapters.length - 1, i + 1))

  if (!open || !chapter) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl w-[500px] max-w-[90vw] max-h-[80vh] flex flex-col p-6 backdrop-blur-xl" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-amber-600 font-medium">{chapter.title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-lg">✕</button>
        </div>
        <div className="flex-1 bg-gray-950 rounded-xl p-4 text-sm text-gray-300 leading-relaxed whitespace-pre-wrap border border-gray-800 min-h-[200px] mb-4 overflow-y-auto">
          {chapter.content || '（内容待创作）'}
        </div>
        <div className="flex items-center justify-center gap-4">
          <button onClick={prev} disabled={index === 0} className="px-3 py-1 rounded-full text-sm bg-gray-800 text-amber-600 disabled:opacity-30 disabled:cursor-default hover:bg-gray-700 transition-colors">◀ 上一章</button>
          <span className="text-xs text-gray-500">{index + 1} / {chapters.length}</span>
          <button onClick={next} disabled={index >= chapters.length - 1} className="px-3 py-1 rounded-full text-sm bg-gray-800 text-amber-600 disabled:opacity-30 disabled:cursor-default hover:bg-gray-700 transition-colors">下一章 ▶</button>
        </div>
      </div>
    </div>
  )
}
```

---

### Task 14: Build SceneEditor

**Files:**
- Create: `frontend/src/pages/editor/modals/SceneEditor.tsx`

- [ ] **Step 1: Write SceneEditor**

```typescript
// frontend/src/pages/editor/modals/SceneEditor.tsx
import { useState, useEffect } from 'react'
import type { Chapter } from '../types'

interface SceneEditorProps {
  chapter: Chapter | null
  onClose: () => void
  onSave: (id: string, content: string) => void
}

export default function SceneEditor({ chapter, onClose, onSave }: SceneEditorProps) {
  const [content, setContent] = useState('')

  useEffect(() => {
    if (chapter) setContent(chapter.content)
  }, [chapter])

  if (!chapter) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-gray-900 border border-amber-700/50 rounded-2xl shadow-2xl w-[400px] p-6 backdrop-blur-xl" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-3">
          <h4 className="text-amber-600 font-medium">✎ {chapter.title}</h4>
          <button onClick={onClose} className="text-gray-400 hover:text-white">✕</button>
        </div>
        <div className="text-xs text-gray-500 mb-2">目标-障碍-结果</div>
        <textarea
          value={content}
          onChange={e => setContent(e.target.value)}
          className="w-full h-24 bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm text-gray-200 resize-none focus:outline-none focus:border-amber-600"
        />
        <div className="flex gap-2 mt-3">
          <button onClick={() => onSave(chapter.id, content)} className="flex-1 py-2 rounded-lg bg-amber-600 text-sm font-medium text-black hover:bg-amber-500 transition-colors">保存</button>
          <button className="flex-1 py-2 rounded-lg bg-gray-800 text-sm text-gray-300 border border-gray-700 hover:bg-gray-700 transition-colors">AI 生成正文草案</button>
        </div>
      </div>
    </div>
  )
}
```

---

### Task 15: Build EditorShell + Wire Up index.tsx

**Files:**
- Create: `frontend/src/pages/editor/layout/EditorShell.tsx`
- Create: `frontend/src/pages/editor/index.tsx` (replace existing)

- [ ] **Step 1: Write EditorShell**

```typescript
// frontend/src/pages/editor/layout/EditorShell.tsx
import { useState } from 'react'
import BottomNav from './BottomNav'
import LeftDrawer from './LeftDrawer'
import ActionButtons from './ActionButtons'
import PlotCanvas from '../views/plot/PlotCanvas'
import CharCanvas from '../views/character/CharCanvas'
import CausalityCanvas from '../views/causality/CausalityCanvas'
import RhythmCanvas from '../views/rhythm/RhythmCanvas'
import ThemeCanvas from '../views/theme/ThemeCanvas'
import { MapView, RulesView, HistoryView, InfoControlView, PovView, InspirationView, KanbanView, ChangelogView } from '../views/info/InfoViews'
import PreviewModal from '../modals/PreviewModal'
import SceneEditor from '../modals/SceneEditor'
import { useEditorViews } from '../hooks/useEditorViews'
import { MOCK_DATA } from '../data/mockData'
import type { Chapter } from '../types'

export default function EditorShell() {
  const views = useEditorViews()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [editingChapter, setEditingChapter] = useState<Chapter | null>(null)

  const data = MOCK_DATA

  const renderCanvas = () => {
    switch (views.activeViewId) {
      case 'narrative-plot':
        return <PlotCanvas chapters={data.chapters} />
      case 'narrative-char':
        return <CharCanvas characters={data.characters} />
      case 'narrative-causality':
        return <CausalityCanvas causalities={data.causalities} />
      case 'narrative-rhythm':
        return <RhythmCanvas rhythms={data.rhythms} />
      case 'narrative-theme':
        return <ThemeCanvas themes={data.themes} />
      default:
        return renderInfoView()
    }
  }

  const renderInfoView = () => {
    switch (views.activeViewId) {
      case 'world-map': return <MapView data={data.world} />
      case 'world-rules': return <RulesView data={data.rules} />
      case 'world-history': return <HistoryView data={data.history} />
      case 'experience-info': return <InfoControlView data={data.infoControls} />
      case 'experience-pov': return <PovView data={data.pov} />
      case 'creation-inspo': return <InspirationView data={data.inspirations} />
      case 'creation-kanban': return <KanbanView data={data.kanban} />
      case 'creation-log': return <ChangelogView data={data.changelog} />
      default: return <div className="flex items-center justify-center h-full text-gray-500">选择视图</div>
    }
  }

  const handleExport = () => {
    const text = data.chapters.map(ch => `${ch.title}\n\n${ch.content}\n\n${'-'.repeat(16)}\n\n`).join('')
    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '小说已完成内容.txt'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="h-screen flex flex-col bg-gray-950 text-gray-100 overflow-hidden select-none">
      {/* Top bar */}
      <div className="h-12 flex items-center justify-between px-4 border-b border-gray-800 bg-gray-900/50">
        <button
          onClick={() => setDrawerOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs text-gray-400 hover:text-gray-200 bg-gray-800/50 hover:bg-gray-700 transition-colors"
        >
          ☰ 大纲
        </button>
        <div className="text-xs text-gray-500 bg-gray-800/50 px-3 py-1 rounded-full">
          {views.activeView.label}
        </div>
      </div>

      {/* Canvas area */}
      <div className="flex-1 relative">
        {renderCanvas()}
        <ActionButtons
          onPreview={() => setPreviewOpen(true)}
          onExport={handleExport}
          onGlobalSetting={() => alert('📜 全局设定 (宪法)\n\n世界基石：人·魔·妖·神共存\n普适规则：万物皆可修炼\n核心冲突：资源与理念之争')}
        />
      </div>

      {/* Drawer */}
      <LeftDrawer
        open={drawerOpen}
        chapters={data.chapters}
        onClose={() => setDrawerOpen(false)}
        onSelectChapter={(id) => {
          setEditingChapter(data.chapters.find(c => c.id === id) ?? null)
        }}
      />

      {/* Modals */}
      <PreviewModal open={previewOpen} chapters={data.chapters} onClose={() => setPreviewOpen(false)} />
      <SceneEditor
        chapter={editingChapter}
        onClose={() => setEditingChapter(null)}
        onSave={(id, content) => {
          const idx = data.chapters.findIndex(c => c.id === id)
          if (idx >= 0) data.chapters[idx].content = content
          setEditingChapter(null)
        }}
      />

      {/* Bottom nav */}
      <BottomNav
        activePillar={views.activePillar}
        activeViewId={views.activeViewId}
        subPanelOpen={views.subPanelOpen}
        pillarViews={views.pillarViews}
        onSwitchPillar={views.switchPillar}
        onSwitchView={views.switchView}
        onCloseSubPanel={views.closeSubPanel}
      />
    </div>
  )
}
```

- [ ] **Step 2: Replace index.tsx**

```typescript
// frontend/src/pages/editor/index.tsx
import EditorShell from './layout/EditorShell'

export default function ProjectPage() {
  return <EditorShell />
}
```

---

### Task 16: Remove Old Editor Files

**Files:**
- Delete: all files under canvas/, panel/, hooks/, data/ (except mockData.ts which is new)
- Delete: AgentButton.tsx, EditorNavbar.tsx, types.ts (old)

- [ ] **Step 1: Remove old files**

```bash
cd /home/yannick/StoryCAD/frontend/src/pages/editor
rm -f AgentButton.tsx EditorNavbar.tsx types.ts
rm -rf canvas/ panel/ hooks/
rm -f data/mockChapters.ts data/mockCharacters.ts
```

---

### Task 17: Verify No TypeScript Errors

**Files:**
- Modify: `frontend/` (entire project)

- [ ] **Step 1: Run TypeScript compiler**

```bash
cd /home/yannick/StoryCAD/frontend
npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 2: Run vite build to verify bundling**

```bash
cd /home/yannick/StoryCAD/frontend
npx vite build
```

Expected: Build succeeds with no errors.
