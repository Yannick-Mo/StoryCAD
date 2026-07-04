# Homepage Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the minimal ProjectListPage with a rich dashboard homepage imitating 首页.html, adapted to dark theme.

**Architecture:** Modular components under `src/pages/home/`, composed in `index.tsx`. Real API data for project list, mock data for stats/templates. `App.tsx` import changes from `./pages/ProjectListPage` to `./pages/home`.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, lucide-react, react-router-dom v6

---

## Files

### Modified
- `frontend/src/types/project.ts` — update types for new backend API
- `frontend/src/api/client.ts` — update to match new backend contract; add `createProjectByTitle`
- `frontend/src/App.tsx` — change import path
- `frontend/src/pages/ProjectListPage.tsx` — delete after migration

### Created
- `frontend/src/pages/home/index.tsx` — composes all dashboard sections
- `frontend/src/pages/home/HomeNavbar.tsx` — sticky navbar with logo/search/btn/avatar
- `frontend/src/pages/home/AnnouncementBanner.tsx` — dismissable banner
- `frontend/src/pages/home/HeroSection.tsx` — time-based greeting
- `frontend/src/pages/home/StatsRow.tsx` — 4 stat cards
- `frontend/src/pages/home/ProjectGrid.tsx` — project cards with search/filter
- `frontend/src/pages/home/CreateCards.tsx` — 3 create entry cards
- `frontend/src/pages/home/TemplateGrid.tsx` — 5 template recommendations
- `frontend/src/pages/home/Footer.tsx` — site footer

---

### Task 1: Update types and API client

**Files:**
- Modify: `frontend/src/types/project.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Update types**

Update `frontend/src/types/project.ts` to match new backend API:

```typescript
export interface ProjectListItem {
  id: string
  title: string
  status: string
  created_at: string
}

// For homepage display — extends API data with mock fields
export interface HomeProject extends ProjectListItem {
  coverClass: string
  coverChar: string
  words: string
  template: string
  time: string
  stage: string
  stageType: string
  progress: number
  progressClass: string
  updated: Date
}

export const COVER_GRADIENTS = ["grad-purple", "grad-blue", "grad-pink", "grad-gold", "grad-green", "grad-teal"] as const
export const PROGRESS_CLASSES = ["purple", "blue", "pink", "gold", "green"] as const
```

- [ ] **Step 2: Update API client**

Replace `frontend/src/api/client.ts` content:

```typescript
const BASE = "/api"

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options)
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

export async function listProjects(): Promise<{ id: string; title: string; status: string; created_at: string }[]> {
  return request(`${BASE}/projects`)
}

export async function getProject(id: string): Promise<any> {
  return request(`${BASE}/projects/${id}`)
}

export async function createProject(title: string, description?: string): Promise<{ id: string }> {
  return request(`${BASE}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, description: description || "" }),
  })
}

export async function deleteProject(id: string): Promise<void> {
  await fetch(`${BASE}/projects/${id}`, { method: "DELETE" })
}

export async function updateSkeleton(id: string, skeleton: any): Promise<void> {
  await request(`${BASE}/projects/${id}/skeleton`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(skeleton),
  })
}

export async function getSkeletonVersions(id: string): Promise<any[]> {
  return request(`${BASE}/projects/${id}/skeleton/versions`)
}

export async function getSkeletonVersion(id: string, version: number): Promise<any> {
  return request(`${BASE}/projects/${id}/skeleton/versions/${version}`)
}

export async function validateSkeleton(id: string): Promise<any> {
  return request(`${BASE}/projects/${id}/validate`, { method: "POST" })
}

export async function exportJSON(id: string): Promise<Blob> {
  const res = await fetch(`${BASE}/projects/${id}/export/json`)
  if (!res.ok) throw new Error(`Export error: ${res.status}`)
  return res.blob()
}

export async function exportMarkdown(id: string): Promise<Blob> {
  const res = await fetch(`${BASE}/projects/${id}/export/markdown`)
  if (!res.ok) throw new Error(`Export error: ${res.status}`)
  return res.blob()
}
```

---

### Task 2: Create HomeNavbar

**Files:**
- Create: `frontend/src/pages/home/HomeNavbar.tsx`

- [ ] **Step: Write HomeNavbar**

```tsx
import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Search, Plus } from "lucide-react"
import { createProject } from "../../api/client"

interface HomeNavbarProps {
  searchQuery: string
  onSearchChange: (val: string) => void
}

export default function HomeNavbar({ searchQuery, onSearchChange }: HomeNavbarProps) {
  const [creating, setCreating] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey && e.key === "k") || (e.key === "/" && !["INPUT", "TEXTAREA"].includes((e.target as HTMLElement).tagName))) {
        e.preventDefault()
        document.getElementById("homeSearch")?.focus()
      }
    }
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [])

  async function handleCreate() {
    if (creating) return
    const title = prompt("请输入项目名称：")
    if (!title?.trim()) return
    setCreating(true)
    try {
      const result = await createProject(title.trim())
      navigate(`/projects/${result.id}`)
    } catch {
      setCreating(false)
    }
  }

  return (
    <nav className="sticky top-0 z-50 bg-gray-900/80 backdrop-blur-xl border-b border-gray-800 px-6 h-14 flex items-center gap-4">
      <a href="/" className="flex items-center gap-2 text-blue-400 font-bold text-lg no-underline shrink-0 hover:opacity-85 transition-opacity">
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
          <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5zm0 2.18l7 3.5v6.72c0 4.17-2.69 8.08-7 9.08-4.31-1-7-4.91-7-9.08V7.68l7-3.5z"/>
        </svg>
        StoryCAD
      </a>
      <div className="relative flex-1 max-w-xs ml-auto">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
        <input
          id="homeSearch"
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="搜索项目..."
          className="w-full pl-9 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-full text-sm text-gray-100 placeholder-gray-500 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
        />
      </div>
      <button
        onClick={handleCreate}
        disabled={creating}
        className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold rounded-full transition-all hover:shadow-lg hover:shadow-blue-600/30 active:scale-95"
      >
        <Plus className="w-4 h-4" />
        新建项目
      </button>
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center text-white text-xs font-bold shrink-0 cursor-pointer hover:scale-105 transition-transform border-2 border-transparent hover:border-blue-400">
        柳
      </div>
    </nav>
  )
}
```

---

### Task 3: Create AnnouncementBanner

**Files:**
- Create: `frontend/src/pages/home/AnnouncementBanner.tsx`

- [ ] **Step: Write AnnouncementBanner**

```tsx
import { useState } from "react"
import { X } from "lucide-react"

export default function AnnouncementBanner() {
  const [dismissed, setDismissed] = useState(() => {
    try { return sessionStorage.getItem("storycad_ann_dismissed") === "1" } catch { return false }
  })

  if (dismissed) return null

  function handleDismiss() {
    setDismissed(true)
    try { sessionStorage.setItem("storycad_ann_dismissed", "1") } catch {}
  }

  return (
    <div className="bg-gradient-to-r from-blue-900/40 via-purple-900/30 to-blue-900/40 border-b border-blue-800/30 px-6 py-2.5 flex items-center justify-center gap-2 text-sm text-blue-300 relative">
      <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse shrink-0" />
      <span>
        🎉 <strong>新功能上线：</strong>AI 智能校验已全面升级，试试在编辑器中一键检查逻辑漏洞吧～
      </span>
      <button onClick={handleDismiss} className="absolute right-4 text-blue-400 hover:text-blue-200 transition-colors">
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}
```

---

### Task 4: Create HeroSection

**Files:**
- Create: `frontend/src/pages/home/HeroSection.tsx`

- [ ] **Step: Write HeroSection**

```tsx
export default function HeroSection() {
  const hour = new Date().getHours()
  const greeting = hour < 12 ? "上午好" : hour < 18 ? "下午好" : "晚上好"

  return (
    <section className="pt-8 pb-4">
      <h1 className="text-2xl font-bold text-gray-100 flex items-center gap-2">
        {greeting}，StoryCAD 用户
        <span className="inline-block animate-wave text-2xl origin-[70%_70%]">👋</span>
      </h1>
      <p className="text-sm text-gray-400 mt-0.5">你的故事结构设计中心——让每一个灵感，都变成坚实的长篇蓝图。</p>
      <style>{`
        @keyframes wave { 0%,100%{transform:rotate(0deg)} 20%{transform:rotate(18deg)} 40%{transform:rotate(-10deg)} 60%{transform:rotate(14deg)} 80%{transform:rotate(-6deg)} }
        .animate-wave { animation: wave 1.5s ease-in-out infinite; }
      `}</style>
    </section>
  )
}
```

---

### Task 5: Create StatsRow

**Files:**
- Create: `frontend/src/pages/home/StatsRow.tsx`

- [ ] **Step: Write StatsRow**

```tsx
import { FolderOpen, FileText, LayoutList, Link2 } from "lucide-react"

interface StatsRowProps {
  projectCount: number
}

export default function StatsRow({ projectCount }: StatsRowProps) {
  const stats = [
    { icon: FolderOpen, color: "bg-blue-500/10 text-blue-400", label: "进行中项目", value: projectCount.toString() },
    { icon: FileText, color: "bg-yellow-500/10 text-yellow-400", label: "总规划字数", value: `${projectCount * 17}万字` },
    { icon: LayoutList, color: "bg-green-500/10 text-green-400", label: "已规划章节", value: Math.round(projectCount * 17 * 10000 / 4000).toString() },
    { icon: Link2, color: "bg-pink-500/10 text-pink-400", label: "追踪伏笔", value: Math.round(projectCount * 17 * 0.44).toString() },
  ]

  return (
    <div className="flex gap-4 flex-wrap mt-6 mb-2">
      {stats.map((s) => (
        <div key={s.label} className="flex-1 min-w-[140px] bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-3 hover:shadow-lg hover:-translate-y-0.5 transition-all cursor-default">
          <div className={`w-11 h-11 rounded-lg flex items-center justify-center shrink-0 ${s.color}`}>
            <s.icon className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xl font-bold text-gray-100">{s.value}</div>
            <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
```

---

### Task 6: Create ProjectGrid

**Files:**
- Create: `frontend/src/pages/home/ProjectGrid.tsx`

- [ ] **Step: Write ProjectGrid**

```tsx
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { listProjects } from "../../api/client"
import type { ProjectListItem, HomeProject } from "../../types/project"
import { COVER_GRADIENTS, PROGRESS_CLASSES } from "../../types/project"

const STAGES = [
  { label: "结构设计中", type: "progress" },
  { label: "人物构建中", type: "progress" },
  { label: "情节填充中", type: "progress" },
  { label: "校验中", type: "progress" },
  { label: "已完成", type: "done" },
]

const TEMPLATES = ["三幕式", "四幕结构", "英雄之旅", "救猫咪", "网文爽文节奏"]

function enrichProject(p: ProjectListItem, index: number): HomeProject {
  const stage = STAGES[index % STAGES.length]
  return {
    ...p,
    coverClass: COVER_GRADIENTS[index % COVER_GRADIENTS.length],
    coverChar: p.title.charAt(0),
    words: `${Math.floor(Math.random() * 25 + 5)}万字`,
    template: TEMPLATES[index % TEMPLATES.length],
    time: index === 0 ? "刚刚" : `${index + 1}天前`,
    stage: stage.label,
    stageType: stage.type,
    progress: Math.min(100, 30 + index * 12 + Math.floor(Math.random() * 20)),
    progressClass: PROGRESS_CLASSES[index % PROGRESS_CLASSES.length],
    updated: new Date(Date.now() - index * 24 * 60 * 60 * 1000),
  }
}

interface ProjectGridProps {
  projects: ProjectListItem[]
  searchQuery: string
  loading: boolean
}

export default function ProjectGrid({ projects, searchQuery, loading }: ProjectGridProps) {
  const [activeFilter, setActiveFilter] = useState("all")
  const navigate = useNavigate()

  const enriched = projects.map((p, i) => enrichProject(p, i))

  const filtered = enriched.filter((p) => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      if (!p.title.toLowerCase().includes(q) && !p.template.toLowerCase().includes(q) && !p.stage.toLowerCase().includes(q)) return false
    }
    if (activeFilter === "progress") return p.stageType === "progress"
    if (activeFilter === "done") return p.stageType === "done"
    if (activeFilter === "recent") {
      const diff = Date.now() - p.updated.getTime()
      return diff / (1000 * 60 * 60 * 24) <= 7
    }
    return true
  })

  const filters = [
    { key: "all", label: "全部" },
    { key: "progress", label: "进行中" },
    { key: "done", label: "已完成" },
    { key: "recent", label: "最近一周" },
  ]

  return (
    <section>
      <div className="flex items-center justify-between flex-wrap gap-3 mt-8 mb-4">
        <h2 className="text-lg font-bold text-gray-100 flex items-center gap-2">
          <span>📂</span> 继续创作
        </h2>
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            {filters.map((f) => (
              <button
                key={f.key}
                onClick={() => setActiveFilter(f.key)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-medium border transition-all ${
                  activeFilter === f.key
                    ? "bg-blue-600 border-blue-600 text-white"
                    : "bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600 hover:text-gray-200"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <a href="/projects" className="text-xs text-blue-400 hover:opacity-75 transition-opacity no-underline ml-2">
            全部项目 →
          </a>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">加载中...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 bg-gray-900 rounded-2xl border-2 border-dashed border-gray-800">
          <div className="text-4xl mb-2 opacity-70">📭</div>
          <div className="text-sm text-gray-400 font-medium">没有找到匹配的项目</div>
          <div className="text-xs text-gray-500 mt-1">试试调整搜索词或筛选条件</div>
        </div>
      ) : (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(270px,1fr))] gap-4">
          {filtered.map((proj, i) => (
            <div
              key={proj.id}
              onClick={() => navigate(`/projects/${proj.id}`)}
              className="bg-gray-900 border border-gray-800 rounded-2xl cursor-pointer overflow-hidden transition-all hover:shadow-xl hover:-translate-y-1 active:scale-[0.98]"
              style={{ animation: `fadeInUp 0.5s ease ${i * 0.06}s forwards`, opacity: 0 }}
            >
              <div className={`h-24 flex items-center justify-center text-white text-3xl font-bold relative overflow-hidden ${proj.coverClass}`}>
                {proj.coverChar}
                <span className={`absolute top-3 right-3 text-[10px] font-semibold px-2 py-0.5 rounded-full backdrop-blur-sm ${
                  proj.stageType === "done" ? "bg-green-500/80" : "bg-blue-500/80"
                }`}>
                  {proj.stage}
                </span>
              </div>
              <div className="p-4 flex flex-col gap-1.5">
                <div className="font-bold text-sm text-gray-100">《{proj.title}》</div>
                <div className="flex gap-3 text-xs text-gray-500">
                  <span>📏 {proj.words}</span>
                  <span>📐 {proj.template}</span>
                  <span>🕐 {proj.time}</span>
                </div>
                <div className="h-1 bg-gray-800 rounded-full mt-1 overflow-hidden">
                  <div className={`h-full rounded-full transition-all duration-500 ${proj.progressClass === "purple" ? "bg-purple-400" : proj.progressClass === "blue" ? "bg-blue-400" : proj.progressClass === "pink" ? "bg-pink-400" : proj.progressClass === "gold" ? "bg-yellow-400" : "bg-green-400"}`}
                    style={{ width: `${proj.progress}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      <style>{`
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
    </section>
  )
}
```

---

### Task 7: Create CreateCards

**Files:**
- Create: `frontend/src/pages/home/CreateCards.tsx`

- [ ] **Step: Write CreateCards**

```tsx
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Lightbulb, FileText, Upload } from "lucide-react"
import { createProject } from "../../api/client"

const CARDS = [
  { icon: Lightbulb, label: "从脑洞开始", desc: "把零碎的灵感倒进来，AI 帮你梳理成清晰的故事骨架", mode: "brainstorm", primary: true },
  { icon: FileText, label: "从模板开始", desc: "选择经典叙事结构模板，快速搭建专业框架", mode: "template", primary: false },
  { icon: Upload, label: "导入文档", desc: "上传已有大纲或文稿，自动提取关键信息", mode: "import", primary: false },
]

export default function CreateCards() {
  const [creating, setCreating] = useState(false)
  const navigate = useNavigate()

  async function handleClick(mode: string) {
    if (creating) return
    if (mode === "brainstorm") {
      const title = prompt("请输入项目名称：")
      if (!title?.trim()) return
      setCreating(true)
      try {
        const result = await createProject(title.trim())
        navigate(`/projects/${result.id}`)
      } catch {
        setCreating(false)
      }
    } else {
      const title = prompt(`请输入项目名称（${mode === "template" ? "模板模式" : "导入模式"}）：`)
      if (!title?.trim()) return
      setCreating(true)
      try {
        const result = await createProject(title.trim())
        navigate(`/projects/${result.id}`)
      } catch {
        setCreating(false)
      }
    }
  }

  return (
    <section>
      <div className="flex items-center gap-2 mt-8 mb-4">
        <h2 className="text-lg font-bold text-gray-100 flex items-center gap-2">
          <span>✨</span> 开始新创作
        </h2>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {CARDS.map((c) => (
          <div
            key={c.mode}
            onClick={() => handleClick(c.mode)}
            className={`rounded-2xl p-6 text-center cursor-pointer transition-all hover:-translate-y-1 active:scale-[0.97] ${
              c.primary
                ? "bg-gradient-to-b from-gray-800 to-gray-900 border-2 border-blue-800/40 hover:border-blue-500/60"
                : "bg-gray-900 border-2 border-dashed border-gray-800 hover:border-gray-600"
            }`}
          >
            <div className={`w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-3 transition-transform group-hover:scale-105 ${
              c.mode === "brainstorm" ? "bg-blue-500/10 text-blue-400" :
              c.mode === "template" ? "bg-yellow-500/10 text-yellow-400" :
              "bg-green-500/10 text-green-400"
            }`}>
              <c.icon className="w-7 h-7" />
            </div>
            <div className="font-bold text-sm text-gray-100 mb-1">{c.label}</div>
            <div className="text-xs text-gray-500 leading-relaxed">{c.desc}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
```

---

### Task 8: Create TemplateGrid

**Files:**
- Create: `frontend/src/pages/home/TemplateGrid.tsx`

- [ ] **Step: Write TemplateGrid**

```tsx
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { createProject } from "../../api/client"

const TEMPLATES = [
  { icon: "🐱", name: "救猫咪节拍表", desc: "15 个节拍，适合商业类型片与强情节小说", color: "bg-pink-500/10 text-pink-400" },
  { icon: "⚔️", name: "英雄之旅", desc: "12 阶段经典模型，适合冒险成长类故事", color: "bg-blue-500/10 text-blue-400" },
  { icon: "🏛️", name: "四幕结构", desc: "经典叙事框架，适合 10 万字以上长篇小说", color: "bg-yellow-500/10 text-yellow-400" },
  { icon: "🎬", name: "三幕式", desc: "简洁高效，适合中短篇及剧本创作", color: "bg-green-500/10 text-green-400" },
  { icon: "🔥", name: "网文爽文节奏", desc: "高密度爽点设计，适合网络连载小说", color: "bg-purple-500/10 text-purple-400" },
]

export default function TemplateGrid() {
  const [creating, setCreating] = useState(false)
  const navigate = useNavigate()

  async function handleClick(template: string) {
    if (creating) return
    const title = prompt(`请输入项目名称（${template}）：`)
    if (!title?.trim()) return
    setCreating(true)
    try {
      const result = await createProject(title.trim())
      navigate(`/projects/${result.id}`)
    } catch {
      setCreating(false)
    }
  }

  return (
    <section>
      <div className="flex items-center justify-between flex-wrap gap-3 mt-8 mb-4">
        <h2 className="text-lg font-bold text-gray-100 flex items-center gap-2">
          <span>📚</span> 推荐叙事模板
        </h2>
        <a href="/templates" className="text-xs text-blue-400 hover:opacity-75 transition-opacity no-underline">
          浏览全部模板 →
        </a>
      </div>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-3">
        {TEMPLATES.map((t) => (
          <div
            key={t.name}
            onClick={() => handleClick(t.name)}
            className="bg-gray-900 border border-gray-800 rounded-xl p-4 cursor-pointer flex gap-3 hover:border-gray-600 hover:shadow-lg hover:-translate-y-0.5 transition-all active:scale-[0.97]"
          >
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg shrink-0 ${t.color}`}>
              {t.icon}
            </div>
            <div className="min-w-0">
              <div className="font-semibold text-sm text-gray-100">{t.name}</div>
              <div className="text-xs text-gray-500 mt-0.5 leading-relaxed">{t.desc}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
```

---

### Task 9: Create Footer

**Files:**
- Create: `frontend/src/pages/home/Footer.tsx`

- [ ] **Step: Write Footer**

```tsx
export default function Footer() {
  return (
    <footer className="text-center py-6 mt-8 text-xs text-gray-600 border-t border-gray-800">
      <strong className="text-gray-500">StoryCAD</strong> — AI 写作辅助设计系统 · 让每一个灵感都变成坚实的长篇蓝图
      &nbsp;|&nbsp;
      <a href="/docs" className="text-blue-400 hover:underline no-underline">使用文档</a>
      &nbsp;·&nbsp;
      <a href="/changelog" className="text-blue-400 hover:underline no-underline">更新日志</a>
      &nbsp;·&nbsp;
      <a href="/feedback" className="text-blue-400 hover:underline no-underline">反馈建议</a>
    </footer>
  )
}
```

---

### Task 10: Create home/index.tsx composition

**Files:**
- Create: `frontend/src/pages/home/index.tsx`

- [ ] **Step: Write the composed page**

```tsx
import { useState, useEffect } from "react"
import HomeNavbar from "./HomeNavbar"
import AnnouncementBanner from "./AnnouncementBanner"
import HeroSection from "./HeroSection"
import StatsRow from "./StatsRow"
import ProjectGrid from "./ProjectGrid"
import CreateCards from "./CreateCards"
import TemplateGrid from "./TemplateGrid"
import Footer from "./Footer"
import { listProjects } from "../../api/client"
import type { ProjectListItem } from "../../types/project"

export default function ProjectListPage() {
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState("")

  useEffect(() => {
    listProjects()
      .then((data) => setProjects(data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <HomeNavbar searchQuery={searchQuery} onSearchChange={setSearchQuery} />
      <AnnouncementBanner />
      <div className="max-w-5xl mx-auto px-6 pb-12">
        <HeroSection />
        <StatsRow projectCount={projects.length} />
        <ProjectGrid projects={projects} searchQuery={searchQuery} loading={loading} />
        <CreateCards />
        <TemplateGrid />
        <Footer />
      </div>
    </div>
  )
}
```

---

### Task 11: Update App.tsx and cleanup

**Files:**
- Modify: `frontend/src/App.tsx`
- Delete: `frontend/src/pages/ProjectListPage.tsx`

- [ ] **Step: Update App.tsx import**

```tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import ProjectListPage from './pages/home'
import ProjectPage from './pages/ProjectPage'
import { ProjectProvider } from './context/ProjectContext'

export default function App() {
  return (
    <ProjectProvider>
      <Routes>
        <Route path="/" element={<ProjectListPage />} />
        <Route path="/projects/:id" element={<ProjectPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ProjectProvider>
  )
}
```

- [ ] **Step: Build check**

Run: `cd /home/yannick/StoryCAD/frontend && npx tsc --noEmit`
Expected: No type errors (or only pre-existing errors unrelated to our changes)

- [ ] **Step: Delete old ProjectListPage**

Delete `frontend/src/pages/ProjectListPage.tsx`
