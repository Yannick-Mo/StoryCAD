# Editor Redesign — Full Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current minimal ProjectPage editor with a canvas-based story structure editor inspired by 编辑页.html, dark theme.

**Architecture:** Custom CSS-transform canvas + React components + SVG connections + floating side panel. 4 phases sequentially.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, lucide-react

---

## Files

### Modified
- `frontend/src/App.tsx` — update import
- `frontend/src/hooks/useProject.ts` — update to work with new types
- `frontend/src/api/client.ts` — add orchestrator/agent endpoints

### Created (41 files)
```
src/pages/editor/
├── index.tsx
├── types.ts
├── EditorNavbar.tsx
├── ActBar.tsx
├── AgentButton.tsx
├── canvas/
│   ├── CanvasViewport.tsx
│   ├── ChapterNode.tsx
│   ├── ConnectionLines.tsx
│   ├── ActGroupBackground.tsx
│   └── TurningPointMarker.tsx
├── panel/
│   ├── EditorPanel.tsx
│   ├── MaterialTab.tsx
│   ├── RelationsTab.tsx
│   ├── HeatmapTab.tsx
│   ├── ForeshadowTab.tsx
│   └── ChapterEditForm.tsx
├── hooks/
│   ├── useCanvas.ts
│   ├── useEditorState.ts
│   └── useLayout.ts
└── data/
    ├── mockChapters.ts
    └── mockCharacters.ts
```

### Deleted
- `frontend/src/pages/ProjectPage.tsx`
- `frontend/src/components/Navbar.tsx`
- `frontend/src/components/Layout.tsx`
- `frontend/src/components/DockLayout.tsx`
- `frontend/src/components/panels/`
- `frontend/src/components/views/`

---

## Phase 1: Editor Shell

### Task 1: Editor types

**Create:** `frontend/src/pages/editor/types.ts`

```typescript
export interface ActConfig {
  id: string
  name: string
  color: string // Tailwind color class
  bgColor: string // act group bg class
  labelColor: string // label bg class
  chapterCount: number
}

export interface Chapter {
  num: number
  actId: string
  title: string
  event: string
  hook: string
  words: string
  intensity: number // 0-1 for heatmap
  turningPoint?: "inciting" | "midpoint" | "darknight" | "climax"
}

export interface StoryMaterial {
  idea: string
  protagonist: string
  world: string
  constraints: string
}

export interface CanvasState {
  scale: number
  tx: number
  ty: number
}

export interface Character {
  id: string
  name: string
  role: "protagonist" | "antagonist" | "ally"
  arc: string[]
  x: number
  y: number
}

export interface ForeshadowItem {
  id: string
  content: string
  plantedAt: string
  resolvedAt: string
  status: "planned" | "pending"
}

export const DEFAULT_ACTS: ActConfig[] = [
  { id: "act1", name: "第一幕 · 建置", color: "text-purple-400", bgColor: "act1-bg", labelColor: "bg-purple-500", chapterCount: 0 },
  { id: "act2a", name: "第二幕上 · 冲突升级", color: "text-blue-400", bgColor: "act2a-bg", labelColor: "bg-blue-500", chapterCount: 0 },
  { id: "act2b", name: "第二幕下 · 绝地重塑", color: "text-pink-400", bgColor: "act2b-bg", labelColor: "bg-pink-500", chapterCount: 0 },
  { id: "act3", name: "第三幕 · 高潮结局", color: "text-yellow-400", bgColor: "act3-bg", labelColor: "bg-yellow-500", chapterCount: 0 },
]
```

### Task 2: EditorNavbar

**Create:** `frontend/src/pages/editor/EditorNavbar.tsx`

```tsx
import { Undo2, Redo2, ZoomIn, ZoomOut, Maximize2, Save, Download, CheckCircle } from "lucide-react"

interface EditorNavbarProps {
  title: string
  zoom: number
  onZoomIn: () => void
  onZoomOut: () => void
  onFit: () => void
  onSave: () => void
  onExport: () => void
  onValidate: () => void
}

export default function EditorNavbar({ title, zoom, onZoomIn, onZoomOut, onFit, onSave, onExport, onValidate }: EditorNavbarProps) {
  return (
    <header className="h-13 flex items-center gap-3 px-5 bg-gray-900/90 backdrop-blur-xl border-b border-gray-800 shrink-0 z-30">
      <a href="/" className="flex items-center gap-2 text-blue-400 font-bold text-sm no-underline shrink-0">
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
          <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5zm0 2.18l7 3.5v6.72c0 4.17-2.69 8.08-7 9.08-4.31-1-7-4.91-7-9.08V7.68l7-3.5z"/>
        </svg>
        StoryCAD
      </a>
      <span className="text-xs text-gray-400 pl-3 border-l border-gray-700 truncate">《{title}》</span>
      <div className="flex-1" />
      <div className="flex items-center gap-1">
        <button className="btn-icon" title="撤销"><Undo2 className="w-4 h-4" /></button>
        <button className="btn-icon" title="重做"><Redo2 className="w-4 h-4" /></button>
        <span className="w-px h-5 bg-gray-700 mx-1" />
        <button className="btn-icon" onClick={onFit} title="适应画布"><Maximize2 className="w-4 h-4" /></button>
        <button className="btn-icon" onClick={onZoomOut} title="缩小"><ZoomOut className="w-4 h-4" /></button>
        <span className="zoom-badge">{Math.round(zoom * 100)}%</span>
        <button className="btn-icon" onClick={onZoomIn} title="放大"><ZoomIn className="w-4 h-4" /></button>
        <span className="w-px h-5 bg-gray-700 mx-1" />
        <button className="btn-primary" onClick={onSave}><Save className="w-3.5 h-3.5" /> 保存版本</button>
        <button className="btn" onClick={onExport}><Download className="w-3.5 h-3.5" /> 导出</button>
        <button className="btn-icon" onClick={onValidate} title="全局校验"><CheckCircle className="w-4 h-4" /></button>
      </div>
    </header>
  )
}
```

Add CSS for editor buttons in the editor/index.tsx or a separate CSS file:

```css
.btn-icon {
  @apply w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-colors cursor-pointer border-none font-inherit;
}
.btn {
  @apply flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-700 bg-gray-800 text-gray-200 text-xs font-medium hover:bg-gray-700 transition-colors cursor-pointer font-inherit;
}
.btn-primary {
  @apply flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 transition-colors cursor-pointer border-none font-inherit;
}
.zoom-badge {
  @apply text-xs text-gray-400 bg-gray-800 px-2 py-1 rounded-md min-w-[3rem] text-center font-mono border border-gray-700;
}
```

### Task 3: ActBar

**Create:** `frontend/src/pages/editor/ActBar.tsx`

```tsx
import { actColors } from "./types"

interface ActBarProps {
  acts: { id: string; name: string; chapterCount: number }[]
  activeAct: string | null
  onActClick: (actId: string) => void
}

const ACT_STYLES: Record<string, { bg: string; text: string }> = {
  act1: { bg: "bg-purple-500/80", text: "text-white" },
  act2a: { bg: "bg-blue-500/80", text: "text-white" },
  act2b: { bg: "bg-pink-500/80", text: "text-white" },
  act3: { bg: "bg-yellow-500/80", text: "text-yellow-900" },
}

export default function ActBar({ acts, activeAct, onActClick }: ActBarProps) {
  const totalChapters = acts.reduce((s, a) => s + a.chapterCount, 0) || 1
  return (
    <div className="h-11 flex items-center gap-0 px-4 bg-gray-900 border-b border-gray-800 shrink-0 z-20">
      {acts.map((act, i) => {
        const pct = (act.chapterCount / totalChapters) * 100
        const style = ACT_STYLES[act.id] || ACT_STYLES.act1
        return (
          <div key={act.id} className="flex items-center flex-1">
            <div
              onClick={() => onActClick(act.id)}
              className={`h-7 flex items-center justify-center cursor-pointer text-[10px] font-semibold tracking-wider transition-all hover:brightness-110 hover:-translate-y-0.5 ${style.bg} ${style.text} ${activeAct === act.id ? "ring-2 ring-white/30" : ""}`}
              style={{ width: `${Math.max(pct, 10)}%`, borderRadius: i === 0 ? "6px 0 0 6px" : i === acts.length - 1 ? "0 6px 6px 0" : "0" }}
            >
              {act.name}
              <span className="ml-1 opacity-70 text-[9px]">{act.chapterCount}章</span>
            </div>
            {i < acts.length - 1 && <div className="w-1 h-7 shrink-0 cursor-col-resize flex items-center justify-center"><div className="w-0.5 h-4 bg-gray-600 rounded" /></div>}
          </div>
        )
      })}
    </div>
  )
}
```

### Task 4: EditorPanel

**Create:** `frontend/src/pages/editor/panel/EditorPanel.tsx`

```tsx
import { useState } from "react"
import { PanelRightClose, PanelRightOpen } from "lucide-react"
import MaterialTab from "./MaterialTab"
import RelationsTab from "./RelationsTab"
import HeatmapTab from "./HeatmapTab"
import ForeshadowTab from "./ForeshadowTab"

const TABS = [
  { id: "material", label: "📝 素材", icon: "📝" },
  { id: "relations", label: "👥 人物", icon: "👥" },
  { id: "heatmap", label: "🔥 热图", icon: "🔥" },
  { id: "foreshadow", label: "🔗 伏笔", icon: "🔗" },
]

export default function EditorPanel() {
  const [activeTab, setActiveTab] = useState("material")
  const [collapsed, setCollapsed] = useState(false)

  if (collapsed) {
    return (
      <div className="fixed right-0 top-24 z-40 flex flex-col gap-1 bg-gray-900/80 backdrop-blur border-l border-gray-800 rounded-l-xl p-1.5">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => { setActiveTab(t.id); setCollapsed(false) }} className="w-9 h-9 flex items-center justify-center text-sm hover:bg-gray-800 rounded-lg transition-colors cursor-pointer border-none font-inherit" title={t.label}>
            {t.icon}
          </button>
        ))}
      </div>
    )
  }

  return (
    <div className="fixed right-0 top-24 bottom-4 w-[340px] z-40 flex flex-col bg-gray-900/95 backdrop-blur-xl border border-gray-800 rounded-l-2xl shadow-2xl overflow-hidden">
      <div className="flex border-b border-gray-800 shrink-0">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} className={`flex-1 py-3 text-xs font-medium transition-colors cursor-pointer border-none font-inherit ${activeTab === t.id ? "text-blue-400 border-b-2 border-blue-400 bg-gray-800/50" : "text-gray-500 hover:text-gray-300"}`}>
            {t.label}
          </button>
        ))}
        <button onClick={() => setCollapsed(true)} className="px-2 text-gray-500 hover:text-gray-300 transition-colors cursor-pointer border-none font-inherit bg-transparent"><PanelRightClose className="w-4 h-4" /></button>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === "material" && <MaterialTab />}
        {activeTab === "relations" && <RelationsTab />}
        {activeTab === "heatmap" && <HeatmapTab />}
        {activeTab === "foreshadow" && <ForeshadowTab />}
      </div>
    </div>
  )
}
```

### Task 5: MaterialTab

**Create:** `frontend/src/pages/editor/panel/MaterialTab.tsx`

```tsx
import { useState } from "react"
import { Wand2, Loader2 } from "lucide-react"

export default function MaterialTab() {
  const [idea, setIdea] = useState("")
  const [protagonist, setProtagonist] = useState("")
  const [world, setWorld] = useState("")
  const [constraints, setConstraints] = useState("")
  const [generating, setGenerating] = useState(false)

  async function handleGenerate() {
    if (!idea.trim()) return
    setGenerating(true)
    // TODO: call orchestrator API
    await new Promise((r) => setTimeout(r, 1500))
    setGenerating(false)
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs text-gray-400 font-medium mb-1.5 block">故事创意 *</label>
        <textarea value={idea} onChange={(e) => setIdea(e.target.value)} placeholder="把你的故事灵感写下来，越详细越好..." className="w-full h-24 bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs text-gray-100 placeholder-gray-500 outline-none resize-none focus:border-blue-500/50 font-inherit" />
      </div>
      <div>
        <label className="text-xs text-gray-400 font-medium mb-1.5 block">主角设定</label>
        <textarea value={protagonist} onChange={(e) => setProtagonist(e.target.value)} placeholder="主角的身份、性格、目标..." className="w-full h-16 bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs text-gray-100 placeholder-gray-500 outline-none resize-none focus:border-blue-500/50 font-inherit" />
      </div>
      <div>
        <label className="text-xs text-gray-400 font-medium mb-1.5 block">世界观</label>
        <textarea value={world} onChange={(e) => setWorld(e.target.value)} placeholder="故事发生的世界设定、时代背景..." className="w-full h-16 bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs text-gray-100 placeholder-gray-500 outline-none resize-none focus:border-blue-500/50 font-inherit" />
      </div>
      <div>
        <label className="text-xs text-gray-400 font-medium mb-1.5 block">补充约束</label>
        <textarea value={constraints} onChange={(e) => setConstraints(e.target.value)} placeholder="字数要求、风格偏好、禁忌内容等..." className="w-full h-12 bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs text-gray-100 placeholder-gray-500 outline-none resize-none focus:border-blue-500/50 font-inherit" />
      </div>
      <button onClick={handleGenerate} disabled={!idea.trim() || generating} className="w-full flex items-center justify-center gap-2 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white text-xs font-semibold rounded-lg transition-all cursor-pointer border-none font-inherit">
        {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
        {generating ? "生成中..." : "✨ 生成故事框架"}
      </button>
    </div>
  )
}
```

### Task 6: RelationsTab

**Create:** `frontend/src/pages/editor/panel/RelationsTab.tsx`

```tsx
export default function RelationsTab() {
  // Static mock graph for now; Phase 3 makes it interactive
  const characters = [
    { name: "主角", x: 20, y: 80, cls: "border-blue-500" },
    { name: "对手", x: 140, y: 20, cls: "border-red-500" },
    { name: "盟友", x: 140, y: 140, cls: "border-green-500" },
  ]

  return (
    <div className="space-y-4">
      <div className="relative w-full h-[200px] bg-gray-950 rounded-xl border border-gray-800 overflow-hidden">
        {characters.map((c) => (
          <div key={c.name} key={undefined} className={`absolute bg-gray-800 border-2 ${c.cls} rounded-2xl px-3 py-1.5 text-[10px] font-semibold text-gray-200 shadow-sm`}
            style={{ left: c.x, top: c.y }}>
            {c.name}
          </div>
        ))}
        <div className="absolute left-[60px] top-[55px] w-px h-10 bg-gray-700 origin-left rotate-[30deg]" />
        <div className="absolute left-[60px] top-[100px] w-px h-10 bg-gray-700 origin-left -rotate-[30deg]" />
      </div>
      <div className="flex gap-3 text-[10px] text-gray-500">
        <span><span className="inline-block w-2 h-2 rounded-full bg-blue-500 mr-1" /> 主角</span>
        <span><span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1" /> 对手</span>
        <span><span className="inline-block w-2 h-2 rounded-full bg-green-500 mr-1" /> 盟友</span>
      </div>
    </div>
  )
}
```

### Task 7: HeatmapTab

**Create:** `frontend/src/pages/editor/panel/HeatmapTab.tsx`

```tsx
export default function HeatmapTab() {
  const chapters = Array.from({ length: 20 }, (_, i) => ({
    num: i + 1,
    intensity: [0.65, 0.55, 0.70, 0.80, 0.60, 0.72, 0.95, 0.75, 0.85, 0.50, 0.62, 0.78, 0.35, 0.40, 0.92, 0.82, 0.88, 0.90, 0.94, 0.98][i] || 0.5
  }))

  return (
    <div className="space-y-3">
      <div className="text-xs font-semibold text-gray-300">全剧冲突强度分布</div>
      <div className="space-y-1.5">
        {chapters.map((ch) => {
          const hue = Math.round(220 - ch.intensity * 220)
          return (
            <div key={ch.num} className="flex items-center gap-2">
              <span className="w-8 text-right text-[10px] text-gray-500 shrink-0">第{ch.num}章</span>
              <div className="flex-1 h-2.5 bg-gray-800 rounded overflow-hidden">
                <div className="h-full rounded transition-all" style={{ width: `${ch.intensity * 100}%`, background: `hsl(${hue}, 70%, 45%)` }} />
              </div>
            </div>
          )
        })}
      </div>
      <p className="text-[10px] text-gray-500 leading-relaxed">🔵 铺垫/文戏 → 🔴 高冲突/反转</p>
    </div>
  )
}
```

### Task 8: ForeshadowTab

**Create:** `frontend/src/pages/editor/panel/ForeshadowTab.tsx`

```tsx
export default function ForeshadowTab() {
  const items = [
    { id: "FS-01", content: "主角隐藏的过去", planted: "第2章", resolved: "第18章", status: "planned" as const },
    { id: "FS-02", content: "神秘人的真实身份", planted: "第4章", resolved: "第16章", status: "planned" as const },
    { id: "FS-03", content: "关键道具的来历", planted: "第1章", resolved: "第20章", status: "planned" as const },
    { id: "FS-04", content: "预言中的转折", planted: "第6章", resolved: "—", status: "pending" as const },
  ]

  return (
    <table className="w-full text-[10.5px] border-collapse">
      <thead>
        <tr className="text-gray-500 text-[9px] font-semibold">
          <th className="text-left py-2 pr-1 border-b border-gray-800">ID</th>
          <th className="text-left py-2 pr-1 border-b border-gray-800">伏笔</th>
          <th className="text-left py-2 pr-1 border-b border-gray-800">埋</th>
          <th className="text-left py-2 pr-1 border-b border-gray-800">收</th>
          <th className="text-left py-2 border-b border-gray-800">状态</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id} className="border-b border-gray-800/50">
            <td className="py-2 pr-1 text-gray-500">{item.id}</td>
            <td className="py-2 pr-1 text-gray-300">{item.content}</td>
            <td className="py-2 pr-1 text-gray-500">{item.planted}</td>
            <td className="py-2 pr-1 text-gray-500">{item.resolved}</td>
            <td className="py-2">
              <span className={`inline-block px-1.5 py-0.5 rounded-full text-[8px] font-semibold ${item.status === "planned" ? "bg-green-900 text-green-300" : "bg-yellow-900 text-yellow-300"}`}>
                {item.status === "planned" ? "已计划" : "待回收"}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
```

### Task 9: AgentButton

**Create:** `frontend/src/pages/editor/AgentButton.tsx`

```tsx
import { useState, useRef, useEffect } from "react"

const SUGGESTIONS = ["@校验 逻辑审查", "@情节 生成钩子", "@命题 补全缺陷", "@结构 调整篇幅"]

export default function AgentButton() {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState("")
  const dialogRef = useRef<HTMLDivElement>(null)
  const btnRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (open && !dialogRef.current?.contains(e.target as Node) && !btnRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [open])

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (open && e.key === "Escape") setOpen(false)
    }
    document.addEventListener("keydown", handleKey)
    return () => document.removeEventListener("keydown", handleKey)
  }, [open])

  return (
    <>
      <button ref={btnRef} onClick={() => setOpen(!open)} className="fixed bottom-6 z-50 w-11 h-11 bg-blue-600 text-white rounded-full shadow-lg shadow-blue-600/40 flex items-center justify-center text-lg cursor-pointer border-none font-inherit hover:scale-105 hover:shadow-blue-600/60 transition-all" style={{ right: "360px" }}>
        💬
      </button>
      {open && (
        <div ref={dialogRef} className="fixed bottom-20 z-50 w-72 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl p-3.5" style={{ right: "360px" }}>
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="@校验Agent 检查第3-5章冲突升级..." className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-100 placeholder-gray-500 outline-none focus:border-blue-500 font-inherit" />
          <div className="flex gap-1.5 mt-2 flex-wrap">
            {SUGGESTIONS.map((s) => (
              <span key={s} onClick={() => setInput(s + " ")} className="text-[9px] text-gray-400 bg-blue-500/10 px-2 py-1 rounded-full cursor-pointer hover:bg-blue-500/20 hover:text-blue-300 transition-colors">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
    </>
  )
}
```

### Task 10: editor/index.tsx composition + routing + cleanup

**Create:** `frontend/src/pages/editor/index.tsx`

```tsx
import { useState } from "react"
import { useParams } from "react-router-dom"
import EditorNavbar from "./EditorNavbar"
import ActBar from "./ActBar"
import CanvasViewport from "./canvas/CanvasViewport"
import EditorPanel from "./panel/EditorPanel"
import AgentButton from "./AgentButton"
import { DEFAULT_ACTS } from "./types"
import type { ActConfig } from "./types"

export default function ProjectPage() {
  const { id } = useParams()
  const [acts, setActs] = useState<ActConfig[]>(DEFAULT_ACTS)
  const [activeAct, setActiveAct] = useState<string | null>(null)
  const [zoom, setZoom] = useState(0.65)
  // Canvas ref for zoom/fit control (set by CanvasViewport via callback)

  const projectTitle = "正在加载..."

  return (
    <div className="h-screen flex flex-col bg-gray-950 text-gray-100 overflow-hidden select-none">
      <EditorNavbar
        title={projectTitle}
        zoom={zoom}
        onZoomIn={() => setZoom((z) => Math.min(2.0, z + 0.1))}
        onZoomOut={() => setZoom((z) => Math.max(0.25, z - 0.1))}
        onFit={() => {}}
        onSave={() => {}}
        onExport={() => {}}
        onValidate={() => {}}
      />
      <ActBar acts={acts} activeAct={activeAct} onActClick={setActiveAct} />
      <div className="flex-1 relative overflow-hidden">
        <CanvasViewport
          chapters={[]}
          acts={acts}
          activeAct={activeAct}
          onChapterClick={() => {}}
        />
        <EditorPanel />
        <AgentButton />
      </div>
    </div>
  )
}
```

**Modify:** `frontend/src/App.tsx`

Change import from `./pages/ProjectPage` to `./pages/editor`

**Delete:** All files listed in the deleted section above.

---

## Phase 2: Canvas

### Task 11: CanvasViewport

**Create:** `frontend/src/pages/editor/canvas/CanvasViewport.tsx`

```tsx
import { useRef, useState, useCallback, useEffect } from "react"
import type { Chapter, ActConfig } from "../types"

interface CanvasViewportProps {
  chapters: Chapter[]
  acts: ActConfig[]
  activeAct: string | null
  onChapterClick: (chapter: Chapter) => void
}

export default function CanvasViewport({ chapters, acts, activeAct, onChapterClick }: CanvasViewportProps) {
  const vpRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(0.65)
  const [tx, setTx] = useState(40)
  const [ty, setTy] = useState(40)
  const [dragging, setDragging] = useState(false)
  const dragRef = useRef({ startX: 0, startY: 0, startTx: 0, startTy: 0 })

  const apply = useCallback((s: number, x: number, y: number) => {
    const layer = vpRef.current?.querySelector(".canvas-layer") as HTMLElement
    if (layer) layer.style.transform = `translate(${x}px, ${y}px) scale(${s})`
  }, [])

  // Mouse drag
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0 || (e.target as HTMLElement).closest(".chapter-node")) return
    setDragging(true)
    dragRef.current = { startX: e.clientX, startY: e.clientY, startTx: tx, startTy: ty }
  }, [tx, ty])

  useEffect(() => {
    if (!dragging) return
    const handleMove = (e: MouseEvent) => {
      setTx(dragRef.current.startTx + e.clientX - dragRef.current.startX)
      setTy(dragRef.current.startTy + e.clientY - dragRef.current.startY)
    }
    const handleUp = () => setDragging(false)
    window.addEventListener("mousemove", handleMove)
    window.addEventListener("mouseup", handleUp)
    return () => { window.removeEventListener("mousemove", handleMove); window.removeEventListener("mouseup", handleUp) }
  }, [dragging])

  // Scroll zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const rect = vpRef.current!.getBoundingClientRect()
    const mx = e.clientX - rect.left, my = e.clientY - rect.top
    const cx = (mx - tx) / scale, cy = (my - ty) / scale
    const ns = Math.max(0.25, Math.min(2.0, scale - e.deltaY * 0.001))
    setTx(mx - cx * ns)
    setTy(my - cy * ns)
    setScale(ns)
  }, [scale, tx, ty])

  // Apply transform
  useEffect(() => { apply(scale, tx, ty) }, [scale, tx, ty, apply])

  const totalWidth = 2000
  const totalHeight = 1500

  return (
    <div
      ref={vpRef}
      className={`w-full h-full ${dragging ? "cursor-grabbing" : "cursor-grab"}`}
      style={{
        backgroundImage: "radial-gradient(circle, #374151 1px, transparent 1px)",
        backgroundSize: "24px 24px"
      }}
      onMouseDown={handleMouseDown}
      onWheel={handleWheel}
    >
      <div className="canvas-layer absolute top-0 left-0" style={{ width: totalWidth, height: totalHeight, transformOrigin: "0 0" }}>
        <svg className="absolute top-0 left-0 pointer-events-none z-0" width={totalWidth} height={totalHeight}>
          {/* Act group backgrounds as SVG rects */}
          {acts.map((act, i) => {
            const colors: Record<string, string> = { act1: "rgba(139,124,246,0.07)", act2a: "rgba(91,156,245,0.07)", act2b: "rgba(236,107,140,0.07)", act3: "rgba(240,180,67,0.08)" }
            const x = i * 480 + 20
            return <rect key={act.id} x={x} y={25} width={450} height={600} rx={14} fill={colors[act.id] || "rgba(255,255,255,0.03)"} stroke="rgba(255,255,255,0.06)" strokeWidth={1} strokeDasharray="6,4" />
          })}
          {/* Connection lines */}
          {chapters.length > 1 && chapters.slice(0, -1).map((_, i) => (
            <line key={i} x1={0} y1={0} x2={0} y2={0} stroke="#4a5568" strokeWidth={2} markerEnd="url(#arrow)" />
          ))}
          <defs>
            <marker id="arrow" markerWidth={8} markerHeight={6} refX={8} refY={3} orient="auto">
              <polygon points="0 0,8 3,0 6" fill="#6b7280" />
            </marker>
          </defs>
        </svg>
        {/* Chapter nodes rendered by ChapterNode component */}
      </div>
    </div>
  )
}
```

### Task 12-17

(ChapterNode, ActGroupBackground, TurningPointMarker, ConnectionLines, useLayout, useCanvas hooks)

These follow the same pattern: take the reference's JS logic, convert to React components with dark theme class names. The layout calculation, fly-to-node animation, and keyboard shortcuts mirror the reference's vanilla JS logic exactly but as React hooks.

---

## Phase 3 & 4

(MaterialTab logic, RelationsTab interactive graph, HeatmapTab real data, ForeshadowTab editable, ChapterEditForm, Save/load API, orchestrator calls, agent API)

Omitted from this plan to keep it manageable — will be detailed when Phases 1-2 are implemented.

---

## Execution

After writing all files and deleting old ones, run:
```bash
cd /home/yannick/StoryCAD/frontend && npx tsc --noEmit
docker compose build frontend && docker compose up -d frontend
```

Then verify at `http://localhost:5173/` that the editor loads with the new layout (Phase 1: navbar + actbar + panel + agent button; Phase 2: canvas with dot-grid).
