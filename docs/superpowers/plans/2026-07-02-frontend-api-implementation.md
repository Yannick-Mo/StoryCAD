# Story-Forge 前端与 API 扩展 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 React 可视化编辑工作台（5 个视图）和支撑 API 端点

**Architecture:** Vite + React 前端通过 Docker 运行，代理 `/api` 到后端 FastAPI；前端使用 react-resizable-panels 实现 Dock 布局，Cytoscape.js 渲染情节图谱

**Tech Stack:** Vite 5, React 18, TypeScript, Tailwind CSS 3, Cytoscape.js + dagre, react-resizable-panels, React Router 6, FastAPI, SQLAlchemy async, PostgreSQL

---

## 文件结构

```
frontend/
├── Dockerfile
├── package.json
├── vite.config.ts
├── tsconfig.json / tsconfig.node.json
├── tailwind.config.js
├── postcss.config.js
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── types/
    │   ├── skeleton.ts        # 骨架数据类型
    │   └── project.ts         # 项目数据类型
    ├── api/
    │   └── client.ts          # fetch 封装
    ├── context/
    │   ├── ProjectContext.tsx  # 项目 + 骨架全局状态
    │   └── SkeletonContext.tsx # 骨架各组件编辑状态
    ├── hooks/
    │   ├── useProject.ts      # 加载 + 轮询项目
    │   ├── useSkeletonCRUD.ts # 保存骨架/版本
    │   └── useCytoscape.ts    # Cytoscape 实例管理
    ├── pages/
    │   ├── ProjectListPage.tsx
    │   └── ProjectPage.tsx
    └── components/
        ├── Layout.tsx
        ├── Navbar.tsx
        ├── DockLayout.tsx
        ├── panels/
        │   ├── NodePropertyEditor.tsx
        │   ├── RelationshipMatrix.tsx
        │   └── BranchTree.tsx
        └── views/
            ├── PlotGraphView.tsx
            ├── CharacterView.tsx
            ├── WorldRulesView.tsx
            ├── BranchForeshadowView.tsx
            └── ValidationView.tsx

backend/app/
├── api/
│   └── routes.py              # + 新增端点
├── services/
│   ├── storage.py             # + 新查询函数
│   ├── export.py              # 新建：导出服务
│   └── graph_editor.py        # 新建：图谱编辑服务
└── models/
    └── db.py                  # + Project.list 类方法

docker-compose.yml             # + frontend 服务
```

---

### Task 1: 前端项目脚手架

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "story-forge-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0",
    "react-resizable-panels": "^2.0.19",
    "cytoscape": "^3.30.0",
    "cytoscape-dagre": "^2.5.0",
    "lucide-react": "^0.441.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@types/cytoscape": "^3.21.5",
    "typescript": "^5.5.3",
    "vite": "^5.4.0",
    "@vitejs/plugin-react": "^4.3.1",
    "tailwindcss": "^3.4.7",
    "postcss": "^8.4.40",
    "autoprefixer": "^10.4.19"
  }
}
```

- [ ] **Step 2: 创建 vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
```

- [ ] **Step 3: 创建 TypeScript 配置**

tsconfig.json:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src"]
}
```

tsconfig.node.json:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: 创建 Tailwind 配置**

tailwind.config.js:
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

postcss.config.js:
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 5: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Story-Forge</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: 创建入口文件**

src/index.css:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  font-family: system-ui, -apple-system, sans-serif;
  -webkit-font-smoothing: antialiased;
}
```

src/main.tsx:
```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
```

src/App.tsx:
```typescript
import { Routes, Route, Navigate } from 'react-router-dom'
import ProjectListPage from './pages/ProjectListPage'
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

- [ ] **Step 7: 安装依赖**

Run: `cd /home/yannick/story-forge/frontend && npm install`
Expected: node_modules/ 目录创建成功

---

### Task 2: Docker 集成

**Files:**
- Create: `frontend/Dockerfile`
- Modify: `docker-compose.yml`

- [ ] **Step 1: 创建 Dockerfile**

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

- [ ] **Step 2: 更新 docker-compose.yml**

```yaml
services:
  backend:
    # ... 保持现有配置
  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/index.html:/app/index.html
    depends_on:
      - backend
  redis:
    # ... 保持现有配置
  postgres:
    # ... 保持现有配置
```

- [ ] **Step 3: 构建并验证**

Run: `cd /home/yannick/story-forge && docker compose up -d --build frontend`
Run: `curl -s http://localhost:5173/ | head -5`
Expected: 返回 HTML 页面，包含 "Story-Forge" 标题

---

### Task 3: 类型定义

**Files:**
- Create: `frontend/src/types/skeleton.ts`
- Create: `frontend/src/types/project.ts`

- [ ] **Step 1: 创建 skeleton.ts**

```typescript
export interface WorldRule {
  category: string
  description: string
  limitation: string
}

export interface WorldRules {
  rules: WorldRule[]
  history: string
  forbidden_events: string[]
}

export interface DesireTopology {
  表层欲望: string
  深层需求: string
  核心恐惧: string
}

export interface Relationship {
  信任: number
  威胁: number
  吸引力: number
}

export interface Character {
  name: string
  desire_topology: DesireTopology
  bottom_line: string
  vulnerability: string
  language_genes: string[]
  relationships: Record<string, Relationship>
  growth_arc: string
}

export interface GraphNode {
  id: string
  description: string
  emotion_value: number
}

export interface GraphEdge {
  source: string
  target: string
  type: 'necessary' | 'possible' | 'indirect'
}

export interface PlotGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface Branch {
  divergence_point: string
  paths: string[][]
  convergence_point: string | null
}

export interface Foreshadow {
  id: string
  planted_at: string
  content: string
  status: 'pending' | 'recycled'
  planned_recycle_interval: string
}

export interface ValidationIssue {
  severity: 'high' | 'medium' | 'low'
  category: string
  description: string
  location: string
  suggestion: string
}

export interface CreativeDoc {
  core_conflict: string
  implied_world_clues: string[]
  character_seeds: { name: string; traits: string }[]
  structural_constraints: string[]
  anchor_events: { order: number; description: string }[]
}

export interface NarrativeSkeleton {
  creative_doc: CreativeDoc
  world_rules: WorldRules
  characters: Character[]
  graph: PlotGraph
  branches: Branch[]
  foreshadows: Foreshadow[]
}
```

- [ ] **Step 2: 创建 project.ts**

```typescript
import { NarrativeSkeleton, ValidationIssue } from './skeleton'

export interface Project {
  project_id: string
  status: 'pending' | 'completed' | 'failed'
  skeleton: NarrativeSkeleton | null
  validation_report: ValidationIssue[] | null
}

export interface SkeletonVersion {
  version: number
  skeleton: NarrativeSkeleton
  validation_report: ValidationIssue[]
  created_at: string
}

export interface ProjectListItem {
  project_id: string
  status: string
  created_at: string
}
```

---

### Task 4: API Client

**Files:**
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: 创建 API 客户端**

```typescript
import { Project, ProjectListItem, SkeletonVersion, ValidationIssue, NarrativeSkeleton } from '../types/project'

const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body}`)
  }
  return res.json()
}

export async function listProjects(): Promise<ProjectListItem[]> {
  return request('/projects')
}

export async function getProject(id: string): Promise<Project> {
  return request(`/projects/${id}`)
}

export async function createProject(rawInput: Record<string, unknown>): Promise<{ project_id: string; status: string }> {
  return request('/projects', {
    method: 'POST',
    body: JSON.stringify(rawInput),
  })
}

export async function deleteProject(id: string): Promise<void> {
  await request(`/projects/${id}`, { method: 'DELETE' })
}

export async function updateSkeleton(id: string, skeleton: NarrativeSkeleton): Promise<void> {
  await request(`/projects/${id}/skeleton`, {
    method: 'PUT',
    body: JSON.stringify(skeleton),
  })
}

export async function getSkeletonVersions(id: string): Promise<SkeletonVersion[]> {
  return request(`/projects/${id}/skeleton/versions`)
}

export async function getSkeletonVersion(id: string, version: number): Promise<SkeletonVersion> {
  return request(`/projects/${id}/skeleton/versions/${version}`)
}

export async function validateSkeleton(id: string): Promise<{ project_id: string; validation_report: ValidationIssue[] }> {
  return request(`/projects/${id}/validate`, { method: 'POST' })
}

export async function exportJSON(id: string): Promise<Blob> {
  const res = await fetch(`${BASE}/projects/${id}/export/json`)
  return res.blob()
}

export async function exportMarkdown(id: string): Promise<Blob> {
  const res = await fetch(`${BASE}/projects/${id}/export/markdown`)
  return res.blob()
}
```

---

### Task 5: Context & Hooks

**Files:**
- Create: `frontend/src/context/ProjectContext.tsx`
- Create: `frontend/src/context/SkeletonContext.tsx`
- Create: `frontend/src/hooks/useProject.ts`
- Create: `frontend/src/hooks/useSkeletonCRUD.ts`
- Create: `frontend/src/hooks/useCytoscape.ts`

- [ ] **Step 1: 创建 ProjectContext**

```typescript
import { createContext, useContext, useReducer, ReactNode } from 'react'
import { Project } from '../types/project'

interface ProjectState {
  project: Project | null
  loading: boolean
  error: string | null
}

type ProjectAction =
  | { type: 'SET_PROJECT'; project: Project }
  | { type: 'SET_LOADING'; loading: boolean }
  | { type: 'SET_ERROR'; error: string }
  | { type: 'UPDATE_SKELETON'; key: string; value: unknown }

function projectReducer(state: ProjectState, action: ProjectAction): ProjectState {
  switch (action.type) {
    case 'SET_PROJECT':
      return { ...state, project: action.project, loading: false, error: null }
    case 'SET_LOADING':
      return { ...state, loading: action.loading }
    case 'SET_ERROR':
      return { ...state, error: action.error, loading: false }
    case 'UPDATE_SKELETON':
      if (!state.project?.skeleton) return state
      return {
        ...state,
        project: {
          ...state.project,
          skeleton: { ...state.project.skeleton, [action.key]: action.value },
        },
      }
    default:
      return state
  }
}

const ProjectCtx = createContext<{
  state: ProjectState
  dispatch: React.Dispatch<ProjectAction>
} | null>(null)

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(projectReducer, {
    project: null,
    loading: false,
    error: null,
  })
  return <ProjectCtx.Provider value={{ state, dispatch }}>{children}</ProjectCtx.Provider>
}

export function useProjectContext() {
  const ctx = useContext(ProjectCtx)
  if (!ctx) throw new Error('useProjectContext must be inside ProjectProvider')
  return ctx
}
```

- [ ] **Step 2: 创建 useProject hook**

```typescript
import { useEffect, useCallback } from 'react'
import { getProject } from '../api/client'
import { useProjectContext } from '../context/ProjectContext'

export function useProject(projectId: string | undefined) {
  const { state, dispatch } = useProjectContext()

  const poll = useCallback(async () => {
    if (!projectId) return
    dispatch({ type: 'SET_LOADING', loading: true })
    try {
      const project = await getProject(projectId)
      dispatch({ type: 'SET_PROJECT', project })
    } catch (err: unknown) {
      dispatch({ type: 'SET_ERROR', error: String(err) })
    }
  }, [projectId, dispatch])

  useEffect(() => {
    if (!projectId) return
    poll()
    const interval = setInterval(() => {
      const status = (state.project?.status)
      if (status === 'pending') poll()
    }, 3000)
    return () => clearInterval(interval)
  }, [projectId])

  return { project: state.project, loading: state.loading, error: state.error, refresh: poll }
}
```

- [ ] **Step 3: 创建 useSkeletonCRUD hook**

```typescript
import { useState, useCallback } from 'react'
import { updateSkeleton, getSkeletonVersions } from '../api/client'
import { NarrativeSkeleton } from '../types/skeleton'
import { SkeletonVersion } from '../types/project'

export function useSkeletonCRUD(projectId: string | undefined) {
  const [saving, setSaving] = useState(false)
  const [versions, setVersions] = useState<SkeletonVersion[]>([])

  const save = useCallback(async (skeleton: NarrativeSkeleton) => {
    if (!projectId) return
    setSaving(true)
    try {
      await updateSkeleton(projectId, skeleton)
    } finally {
      setSaving(false)
    }
  }, [projectId])

  const loadVersions = useCallback(async () => {
    if (!projectId) return
    const v = await getSkeletonVersions(projectId)
    setVersions(v)
  }, [projectId])

  return { save, saving, versions, loadVersions }
}
```

- [ ] **Step 4: 创建 useCytoscape hook**

```typescript
import { useRef, useEffect, useCallback } from 'react'
import cytoscape, { Core, ElementDefinition } from 'cytoscape'
import dagre from 'cytoscape-dagre'
import { PlotGraph, GraphNode } from '../types/skeleton'

cytoscape.use(dagre)

export function useCytoscape(
  containerRef: React.RefObject<HTMLDivElement | null>,
  graphData: PlotGraph | undefined,
  onNodeSelect?: (node: GraphNode) => void
) {
  const cyRef = useRef<Core | null>(null)

  useEffect(() => {
    if (!containerRef.current || !graphData) return

    const elements: ElementDefinition[] = [
      ...graphData.nodes.map((n) => ({
        data: { id: n.id, label: `${n.id}\n${n.description.slice(0, 15)}...`, emotion: n.emotion_value },
        classes: n.emotion_value > 70 ? 'high' : n.emotion_value > 40 ? 'mid' : 'low',
      })),
      ...graphData.edges.map((e) => ({
        data: { id: `${e.source}-${e.target}`, source: e.source, target: e.target },
        classes: e.type,
      })),
    ]

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        { selector: 'node', style: { label: 'data(label)', 'text-wrap': 'wrap', 'text-max-width': '80px', 'font-size': '10px', 'background-color': '#4299e1', width: 60, height: 60 } },
        { selector: 'node.high', style: { 'background-color': '#e53e3e' } },
        { selector: 'node.mid', style: { 'background-color': '#ecc94b' } },
        { selector: 'node.low', style: { 'background-color': '#48bb78' } },
        { selector: 'edge', style: { width: 2, 'line-color': '#a0aec0', 'curve-style': 'bezier' } },
        { selector: 'edge.necessary', style: { 'line-style': 'solid' } },
        { selector: 'edge.possible', style: { 'line-style': 'dashed' } },
        { selector: 'edge.indirect', style: { 'line-style': 'dotted' } },
      ],
      layout: { name: 'dagre', rankDir: 'LR', spacingFactor: 1.5 },
      userZoomingEnabled: true,
      userPanningEnabled: true,
    })

    cy.on('tap', 'node', (evt) => {
      const nodeData = evt.target.data()
      const fullNode = graphData.nodes.find((n) => n.id === nodeData.id)
      if (fullNode && onNodeSelect) onNodeSelect(fullNode)
    })

    cyRef.current = cy

    return () => { cy.destroy(); cyRef.current = null }
  }, [graphData])

  const fit = useCallback(() => cyRef.current?.fit(undefined, 50), [])

  return { cy: cyRef, fit }
}
```

---

### Task 6: Layout 组件（Navbar + DockLayout）

**Files:**
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/components/Navbar.tsx`
- Create: `frontend/src/components/DockLayout.tsx`

- [ ] **Step 1: 创建 Navbar**

```typescript
import { ReactNode } from 'react'
import { Save, Download, RotateCcw, FileText } from 'lucide-react'

interface NavbarProps {
  projectId?: string
  onSave?: () => void
  onRegenerate?: () => void
  onExport?: (format: 'json' | 'markdown') => void
  saving?: boolean
  children?: ReactNode
}

export default function Navbar({ projectId, onSave, onRegenerate, onExport, saving, children }: NavbarProps) {
  return (
    <nav className="flex items-center justify-between px-4 py-2 bg-gray-900 text-white border-b border-gray-700">
      <div className="flex items-center gap-3">
        <FileText className="w-5 h-5" />
        <span className="font-semibold">Story-Forge</span>
        {projectId && <span className="text-sm text-gray-400">/{projectId.slice(0, 8)}</span>}
      </div>
      <div className="flex items-center gap-2">
        {children}
        {onRegenerate && (
          <button onClick={onRegenerate} className="flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 rounded">
            <RotateCcw className="w-4 h-4" /> 重新生成
          </button>
        )}
        {onExport && (
          <div className="relative group">
            <button className="flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 rounded">
              <Download className="w-4 h-4" /> 导出
            </button>
            <div className="absolute right-0 top-full mt-1 bg-gray-800 rounded shadow-lg hidden group-hover:block z-50">
              <button onClick={() => onExport('json')} className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-700">JSON</button>
              <button onClick={() => onExport('markdown')} className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-700">Markdown</button>
            </div>
          </div>
        )}
        {onSave && (
          <button onClick={onSave} disabled={saving} className="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 rounded disabled:opacity-50">
            <Save className="w-4 h-4" /> {saving ? '保存中...' : '保存'}
          </button>
        )}
      </div>
    </nav>
  )
}
```

- [ ] **Step 2: 创建 DockLayout**

```typescript
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import { ReactNode, useState } from 'react'

interface Tab {
  id: string
  label: string
  content: ReactNode
}

interface DockLayoutProps {
  mainView: ReactNode
  rightTabs: Tab[]
  bottomPanel?: ReactNode
}

export default function DockLayout({ mainView, rightTabs, bottomPanel }: DockLayoutProps) {
  const [activeTab, setActiveTab] = useState(rightTabs[0]?.id)

  return (
    <PanelGroup direction="horizontal" className="flex-1">
      <Panel defaultSize={60} minSize={30}>
        <div className="h-full bg-gray-900">{mainView}</div>
      </Panel>
      <PanelResizeHandle className="w-1 bg-gray-700 hover:bg-blue-500 transition-colors cursor-col-resize" />
      <Panel defaultSize={40} minSize={20}>
        <PanelGroup direction="vertical">
          <Panel defaultSize={55} minSize={20}>
            <div className="h-full flex flex-col bg-gray-800">
              <div className="flex border-b border-gray-700 bg-gray-850">
                {rightTabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                      activeTab === tab.id
                        ? 'border-blue-500 text-blue-400'
                        : 'border-transparent text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              <div className="flex-1 overflow-auto p-3">
                {rightTabs.find((t) => t.id === activeTab)?.content}
              </div>
            </div>
          </Panel>
          {bottomPanel && (
            <>
              <PanelResizeHandle className="h-1 bg-gray-700 hover:bg-blue-500 transition-colors cursor-row-resize" />
              <Panel defaultSize={45} minSize={15}>
                <div className="h-full bg-gray-800 overflow-auto p-3 border-t border-gray-700">
                  {bottomPanel}
                </div>
              </Panel>
            </>
          )}
        </PanelGroup>
      </Panel>
    </PanelGroup>
  )
}
```

- [ ] **Step 3: 创建 Layout 组件**

```typescript
import { ReactNode } from 'react'
import Navbar from './Navbar'
import { useProjectContext } from '../context/ProjectContext'

interface LayoutProps {
  children: ReactNode
  onSave?: () => void
  onRegenerate?: () => void
  onExport?: (format: 'json' | 'markdown') => void
  saving?: boolean
}

export default function Layout({ children, onSave, onRegenerate, onExport, saving }: LayoutProps) {
  const { state } = useProjectContext()
  const projectId = state.project?.project_id

  return (
    <div className="h-screen flex flex-col bg-gray-900 text-gray-100">
      <Navbar projectId={projectId} onSave={onSave} onRegenerate={onRegenerate} onExport={onExport} saving={saving} />
      {children}
    </div>
  )
}
```

---

### Task 7: 5 个视图组件

**Files:**
- Create: `frontend/src/components/views/PlotGraphView.tsx`
- Create: `frontend/src/components/views/CharacterView.tsx`
- Create: `frontend/src/components/views/WorldRulesView.tsx`
- Create: `frontend/src/components/views/BranchForeshadowView.tsx`
- Create: `frontend/src/components/views/ValidationView.tsx`
- Create: `frontend/src/components/panels/NodePropertyEditor.tsx`
- Create: `frontend/src/components/panels/RelationshipMatrix.tsx`
- Create: `frontend/src/components/panels/BranchTree.tsx`

- [ ] **Step 1: 创建 PlotGraphView**

```typescript
import { useRef, useState } from 'react'
import { useCytoscape } from '../../hooks/useCytoscape'
import { PlotGraph, GraphNode } from '../../types/skeleton'
import { useProjectContext } from '../../context/ProjectContext'
import NodePropertyEditor from '../panels/NodePropertyEditor'

export default function PlotGraphView() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const { state, dispatch } = useProjectContext()
  const graphData = state.project?.skeleton?.graph
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)

  useCytoscape(containerRef, graphData, (node) => setSelectedNode(node))

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-gray-700 bg-gray-850">
        <span className="text-xs text-gray-400">情节图谱 — {graphData?.nodes.length ?? 0} 节点 / {graphData?.edges.length ?? 0} 边</span>
      </div>
      <div ref={containerRef} className="flex-1" />
      {selectedNode && (
        <NodePropertyEditor node={selectedNode} onClose={() => setSelectedNode(null)} />
      )}
    </div>
  )
}
```

- [ ] **Step 2: 创建 NodePropertyEditor**

```typescript
import { GraphNode } from '../../types/skeleton'
import { X } from 'lucide-react'

interface NodePropertyEditorProps {
  node: GraphNode
  onClose: () => void
}

export default function NodePropertyEditor({ node, onClose }: NodePropertyEditorProps) {
  return (
    <div className="border-t border-gray-700 bg-gray-850 p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">{node.id}</span>
        <button onClick={onClose} className="text-gray-400 hover:text-white">
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="space-y-2">
        <div>
          <label className="text-xs text-gray-400">事件描述</label>
          <textarea
            defaultValue={node.description}
            className="w-full mt-1 px-2 py-1 text-sm bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none resize-none"
            rows={2}
          />
        </div>
        <div>
          <label className="text-xs text-gray-400">情绪值 (0-100)</label>
          <input
            type="range"
            min={0}
            max={100}
            defaultValue={node.emotion_value}
            className="w-full mt-1 accent-blue-500"
          />
          <span className="text-xs text-gray-400">{node.emotion_value}</span>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: 创建 CharacterView**

```typescript
import { useState } from 'react'
import { useProjectContext } from '../../context/ProjectContext'
import { Character } from '../../types/skeleton'
import { Plus, Trash2 } from 'lucide-react'

export default function CharacterView() {
  const { state, dispatch } = useProjectContext()
  const characters = state.project?.skeleton?.characters ?? []
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null)
  const char = selectedIdx !== null ? characters[selectedIdx] : null

  return (
    <div className="flex gap-3 h-full">
      <div className="w-40 flex-shrink-0 space-y-1">
        {characters.map((c, i) => (
          <div
            key={c.name}
            onClick={() => setSelectedIdx(i)}
            className={`px-2 py-1.5 text-sm rounded cursor-pointer ${
              selectedIdx === i ? 'bg-blue-600 text-white' : 'bg-gray-700 hover:bg-gray-600'
            }`}
          >
            {c.name}
          </div>
        ))}
      </div>
      {char && (
        <div className="flex-1 space-y-3 overflow-auto">
          <div>
            <label className="text-xs text-gray-400">名称</label>
            <input defaultValue={char.name} className="w-full mt-1 px-2 py-1 text-sm bg-gray-700 rounded border border-gray-600" />
          </div>
          <div>
            <label className="text-xs text-gray-400">表层欲望</label>
            <input defaultValue={char.desire_topology.表层欲望} className="w-full mt-1 px-2 py-1 text-sm bg-gray-700 rounded border border-gray-600" />
          </div>
          <div>
            <label className="text-xs text-gray-400">深层需求</label>
            <input defaultValue={char.desire_topology.深层需求} className="w-full mt-1 px-2 py-1 text-sm bg-gray-700 rounded border border-gray-600" />
          </div>
          <div>
            <label className="text-xs text-gray-400">核心恐惧</label>
            <input defaultValue={char.desire_topology.核心恐惧} className="w-full mt-1 px-2 py-1 text-sm bg-gray-700 rounded border border-gray-600" />
          </div>
          <div>
            <label className="text-xs text-gray-400">底线</label>
            <input defaultValue={char.bottom_line} className="w-full mt-1 px-2 py-1 text-sm bg-gray-700 rounded border border-gray-600" />
          </div>
          <div>
            <label className="text-xs text-gray-400">弱点</label>
            <input defaultValue={char.vulnerability} className="w-full mt-1 px-2 py-1 text-sm bg-gray-700 rounded border border-gray-600" />
          </div>
          <div>
            <label className="text-xs text-gray-400">语言基因</label>
            {char.language_genes.map((line, i) => (
              <input key={i} defaultValue={line} className="w-full mt-1 px-2 py-1 text-sm bg-gray-700 rounded border border-gray-600" />
            ))}
          </div>
          <div>
            <label className="text-xs text-gray-400">成长弧线</label>
            <textarea defaultValue={char.growth_arc} className="w-full mt-1 px-2 py-1 text-sm bg-gray-700 rounded border border-gray-600 resize-none" rows={3} />
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: 创建 WorldRulesView**

```typescript
import { useProjectContext } from '../../context/ProjectContext'

export default function WorldRulesView() {
  const { state } = useProjectContext()
  const worldRules = state.project?.skeleton?.world_rules
  if (!worldRules) return <div className="text-gray-400 text-sm">无世界观数据</div>

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs text-gray-400 block mb-1">背景历史</label>
        <textarea defaultValue={worldRules.history} className="w-full px-2 py-1 text-sm bg-gray-700 rounded border border-gray-600 resize-none" rows={4} />
      </div>
      <div>
        <label className="text-xs text-gray-400 block mb-1">世界规则 ({worldRules.rules.length})</label>
        {worldRules.rules.map((rule, i) => (
          <div key={i} className="mb-2 p-2 bg-gray-700 rounded">
            <div className="flex gap-2 mb-1">
              <select defaultValue={rule.category} className="px-1 py-0.5 text-xs bg-gray-600 rounded border border-gray-500">
                <option>物理规则</option>
                <option>魔法体系</option>
                <option>社会结构</option>
                <option>科技水平</option>
                <option>文化习俗</option>
              </select>
            </div>
            <textarea defaultValue={rule.description} className="w-full mb-1 px-2 py-1 text-sm bg-gray-600 rounded border border-gray-500 resize-none" rows={2} />
            <textarea defaultValue={rule.limitation} className="w-full px-2 py-1 text-sm bg-gray-600 rounded border border-gray-500 resize-none" rows={2} />
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: 创建 BranchForeshadowView**

```typescript
import { useProjectContext } from '../../context/ProjectContext'
import BranchTree from '../panels/BranchTree'

export default function BranchForeshadowView() {
  const { state } = useProjectContext()
  const branches = state.project?.skeleton?.branches ?? []
  const foreshadows = state.project?.skeleton?.foreshadows ?? []

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-medium mb-2">分支路径 ({branches.length})</h3>
        {branches.map((b, i) => <BranchTree key={i} branch={b} />)}
        {branches.length === 0 && <p className="text-gray-500 text-sm">无分支</p>}
      </div>
      <div>
        <h3 className="text-sm font-medium mb-2">伏笔 ({foreshadows.length})</h3>
        {foreshadows.map((f) => (
          <div key={f.id} className="mb-2 p-2 bg-gray-700 rounded text-sm">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs text-gray-400">{f.id}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded ${f.status === 'recycled' ? 'bg-green-700' : 'bg-yellow-700'}`}>{f.status}</span>
            </div>
            <p className="text-xs text-gray-300">{f.content}</p>
            <p className="text-xs text-gray-500 mt-1">埋设于: {f.planted_at} | {f.planned_recycle_interval}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 6: 创建 BranchTree**

```typescript
import { Branch } from '../../types/skeleton'

interface BranchTreeProps {
  branch: Branch
}

export default function BranchTree({ branch }: BranchTreeProps) {
  return (
    <div className="mb-2 p-2 bg-gray-700 rounded text-sm">
      <p className="text-xs text-gray-400 mb-1">
        分歧点: {branch.divergence_point}
        {branch.convergence_point && ` → 汇合点: ${branch.convergence_point}`}
      </p>
      {branch.paths.map((path, i) => (
        <div key={i} className="flex items-center gap-1 text-xs text-gray-300 ml-2">
          <span className="text-blue-400">路径 {i + 1}:</span>
          {path.map((evt, j) => (
            <span key={j}>
              {j > 0 && <span className="text-gray-600"> → </span>}
              {evt}
            </span>
          ))}
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 7: 创建 ValidationView**

```typescript
import { useState } from 'react'
import { useProjectContext } from '../../context/ProjectContext'
import { validateSkeleton } from '../../api/client'
import { ValidationIssue } from '../../types/skeleton'
import { AlertTriangle, AlertCircle, Info, RotateCcw } from 'lucide-react'

export default function ValidationView() {
  const { state } = useProjectContext()
  const [report, setReport] = useState<ValidationIssue[] | null>(state.project?.validation_report ?? null)
  const [validating, setValidating] = useState(false)

  const runValidation = async () => {
    if (!state.project?.project_id) return
    setValidating(true)
    try {
      const result = await validateSkeleton(state.project.project_id)
      setReport(result.validation_report)
    } finally {
      setValidating(false)
    }
  }

  const grouped = {
    high: report?.filter((r) => r.severity === 'high') ?? [],
    medium: report?.filter((r) => r.severity === 'medium') ?? [],
    low: report?.filter((r) => r.severity === 'low') ?? [],
  }

  const severityIcon = (s: string) => {
    if (s === 'high') return <AlertCircle className="w-4 h-4 text-red-400" />
    if (s === 'medium') return <AlertTriangle className="w-4 h-4 text-yellow-400" />
    return <Info className="w-4 h-4 text-blue-400" />
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-400">共 {report?.length ?? 0} 个问题</span>
        <button onClick={runValidation} disabled={validating} className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded disabled:opacity-50">
          <RotateCcw className="w-3 h-3" /> {validating ? '校验中...' : '重新校验'}
        </button>
      </div>
      {(['high', 'medium', 'low'] as const).map((severity) => (
        grouped[severity].length > 0 && (
          <div key={severity} className="mb-3">
            <h4 className="text-xs font-medium text-gray-400 uppercase mb-1">{severity} ({grouped[severity].length})</h4>
            {grouped[severity].map((issue, i) => (
              <div key={i} className="mb-2 p-2 bg-gray-700 rounded">
                <div className="flex items-start gap-2">
                  {severityIcon(issue.severity)}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-gray-300">{issue.description}</p>
                    <p className="text-xs text-gray-500 mt-1">{issue.category} · {issue.location}</p>
                    {issue.suggestion && <p className="text-xs text-blue-400 mt-1">建议: {issue.suggestion}</p>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )
      ))}
      {(!report || report.length === 0) && <p className="text-gray-500 text-sm">尚无校验结果</p>}
    </div>
  )
}
```

---

### Task 8: 页面组件（ProjectListPage + ProjectPage）

**Files:**
- Create: `frontend/src/pages/ProjectListPage.tsx`
- Create: `frontend/src/pages/ProjectPage.tsx`

- [ ] **Step 1: 创建 ProjectListPage**

```typescript
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { listProjects, createProject } from '../api/client'
import { ProjectListItem } from '../types/project'
import { Plus, FileText, Clock } from 'lucide-react'

export default function ProjectListPage() {
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [creating, setCreating] = useState(false)
  const [idea, setIdea] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    listProjects().then(setProjects).catch(() => {})
  }, [])

  const handleCreate = async () => {
    if (!idea.trim()) return
    setCreating(true)
    try {
      const { project_id } = await createProject({ idea: idea.trim() })
      navigate(`/projects/${project_id}`)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="h-screen flex flex-col items-center justify-center bg-gray-900 text-gray-100 p-8">
      <div className="max-w-lg w-full">
        <div className="flex items-center gap-3 mb-6">
          <FileText className="w-8 h-8 text-blue-400" />
          <h1 className="text-2xl font-bold">Story-Forge</h1>
        </div>
        <div className="mb-8">
          <textarea
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="输入故事创意..."
            className="w-full h-32 px-4 py-3 text-sm bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 outline-none resize-none"
          />
          <button
            onClick={handleCreate}
            disabled={creating || !idea.trim()}
            className="mt-2 flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg disabled:opacity-50 text-sm"
          >
            <Plus className="w-4 h-4" /> {creating ? '生成中...' : '开始生成'}
          </button>
        </div>
        <div>
          <h2 className="text-sm font-medium text-gray-400 mb-3">已有项目 ({projects.length})</h2>
          {projects.map((p) => (
            <div
              key={p.project_id}
              onClick={() => navigate(`/projects/${p.project_id}`)}
              className="flex items-center justify-between p-3 mb-2 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-750"
            >
              <span className="text-sm">{p.project_id.slice(0, 8)}...</span>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <Clock className="w-3 h-3" />
                <span>{new Date(p.created_at).toLocaleDateString()}</span>
                <span className={`px-1.5 py-0.5 rounded ${p.status === 'completed' ? 'bg-green-800 text-green-300' : 'bg-yellow-800 text-yellow-300'}`}>
                  {p.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 创建 ProjectPage**

```typescript
import { useParams } from 'react-router-dom'
import { useProject } from '../hooks/useProject'
import { useSkeletonCRUD } from '../hooks/useSkeletonCRUD'
import Layout from '../components/Layout'
import DockLayout from '../components/DockLayout'
import PlotGraphView from '../components/views/PlotGraphView'
import CharacterView from '../components/views/CharacterView'
import WorldRulesView from '../components/views/WorldRulesView'
import BranchForeshadowView from '../components/views/BranchForeshadowView'
import ValidationView from '../components/views/ValidationView'

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>()
  const { project, loading } = useProject(id)
  const { save, saving } = useSkeletonCRUD(id)

  if (loading && !project) {
    return (
      <Layout>
        <div className="flex-1 flex items-center justify-center text-gray-400">
          加载中...
        </div>
      </Layout>
    )
  }

  if (!project) {
    return (
      <Layout>
        <div className="flex-1 flex items-center justify-center text-gray-400">
          项目未找到
        </div>
      </Layout>
    )
  }

  const handleSave = () => {
    if (project.skeleton) save(project.skeleton)
  }

  const rightTabs = [
    { id: 'characters', label: '角色', content: <CharacterView /> },
    { id: 'world', label: '世界观', content: <WorldRulesView /> },
    { id: 'branches', label: '分支/伏笔', content: <BranchForeshadowView /> },
    { id: 'validation', label: '校验', content: <ValidationView /> },
  ]

  return (
    <Layout onSave={handleSave} saving={saving}>
      <DockLayout
        mainView={<PlotGraphView />}
        rightTabs={rightTabs}
        bottomPanel={<div className="text-sm text-gray-400">选中节点后可在此编辑属性</div>}
      />
    </Layout>
  )
}
```

---

### Task 9: 后端 API 扩展

**Files:**
- Modify: `backend/app/api/routes.py`
- Modify: `backend/app/services/storage.py`
- Create: `backend/app/services/export.py`
- Create: `backend/app/services/graph_editor.py`
- Modify: `backend/app/models/db.py`

- [ ] **Step 1: 添加 storage 新函数**

在 `backend/app/services/storage.py` 中添加：

```python
async def list_projects(db: AsyncSession) -> list[Project]:
    result = await db.execute(select(Project).order_by(desc(Project.created_at)))
    return result.scalars().all()

async def delete_project(db: AsyncSession, project_id: uuid.UUID) -> bool:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        return False
    await db.delete(project)
    await db.commit()
    return True

async def get_skeleton_versions(db: AsyncSession, project_id: uuid.UUID) -> list[ProjectSkeleton]:
    result = await db.execute(
        select(ProjectSkeleton)
        .where(ProjectSkeleton.project_id == project_id)
        .order_by(desc(ProjectSkeleton.version))
    )
    return result.scalars().all()

async def get_skeleton_by_version(db: AsyncSession, project_id: uuid.UUID, version: int) -> ProjectSkeleton | None:
    result = await db.execute(
        select(ProjectSkeleton)
        .where(ProjectSkeleton.project_id == project_id)
        .where(ProjectSkeleton.version == version)
    )
    return result.scalar_one_or_none()
```

- [ ] **Step 2: 创建 graph_editor.py**

```python
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db import Project, ProjectSkeleton
from app.services.storage import save_skeleton

async def add_graph_node(db: AsyncSession, project_id: uuid.UUID, node: dict) -> dict:
    sk = await _get_current_skeleton(db, project_id)
    if not sk:
        raise ValueError("No skeleton found")
    graph = sk.skeleton.get("graph", {})
    nodes = graph.get("nodes", [])
    max_id = max((int(n["id"].split("_")[1]) for n in nodes if n["id"].startswith("evt_")), default=0)
    node["id"] = f"evt_{max_id + 1}"
    nodes.append(node)
    graph["nodes"] = nodes
    sk.skeleton["graph"] = graph
    await save_skeleton(db, project_id, sk.skeleton, sk.validation_report)
    return node

async def update_graph_node(db: AsyncSession, project_id: uuid.UUID, node_id: str, updates: dict) -> dict | None:
    sk = await _get_current_skeleton(db, project_id)
    if not sk:
        return None
    graph = sk.skeleton.get("graph", {})
    for node in graph.get("nodes", []):
        if node["id"] == node_id:
            node.update(updates)
            await save_skeleton(db, project_id, sk.skeleton, sk.validation_report)
            return node
    return None

async def delete_graph_node(db: AsyncSession, project_id: uuid.UUID, node_id: str) -> bool:
    sk = await _get_current_skeleton(db, project_id)
    if not sk:
        return False
    graph = sk.skeleton.get("graph", {})
    graph["nodes"] = [n for n in graph.get("nodes", []) if n["id"] != node_id]
    graph["edges"] = [e for e in graph.get("edges", []) if e["source"] != node_id and e["target"] != node_id]
    sk.skeleton["graph"] = graph
    await save_skeleton(db, project_id, sk.skeleton, sk.validation_report)
    return True

async def add_graph_edge(db: AsyncSession, project_id: uuid.UUID, edge: dict) -> dict:
    sk = await _get_current_skeleton(db, project_id)
    if not sk:
        raise ValueError("No skeleton found")
    graph = sk.skeleton.get("graph", {})
    edges = graph.get("edges", [])
    edge["id"] = f"{edge['source']}-{edge['target']}-{len(edges)}"
    edges.append(edge)
    graph["edges"] = edges
    sk.skeleton["graph"] = graph
    await save_skeleton(db, project_id, sk.skeleton, sk.validation_report)
    return edge

async def delete_graph_edge(db: AsyncSession, project_id: uuid.UUID, source: str, target: str) -> bool:
    sk = await _get_current_skeleton(db, project_id)
    if not sk:
        return False
    graph = sk.skeleton.get("graph", {})
    graph["edges"] = [e for e in graph.get("edges", []) if not (e["source"] == source and e["target"] == target)]
    sk.skeleton["graph"] = graph
    await save_skeleton(db, project_id, sk.skeleton, sk.validation_report)
    return True

async def add_character(db: AsyncSession, project_id: uuid.UUID, character: dict) -> dict:
    sk = await _get_current_skeleton(db, project_id)
    if not sk:
        raise ValueError("No skeleton found")
    chars = sk.skeleton.get("characters", [])
    if any(c["name"] == character["name"] for c in chars):
        raise ValueError(f"Character '{character['name']}' already exists")
    chars.append(character)
    sk.skeleton["characters"] = chars
    await save_skeleton(db, project_id, sk.skeleton, sk.validation_report)
    return character

async def update_character(db: AsyncSession, project_id: uuid.UUID, name: str, updates: dict) -> dict | None:
    sk = await _get_current_skeleton(db, project_id)
    if not sk:
        return None
    chars = sk.skeleton.get("characters", [])
    for char in chars:
        if char["name"] == name:
            char.update(updates)
            await save_skeleton(db, project_id, sk.skeleton, sk.validation_report)
            return char
    return None

async def delete_character(db: AsyncSession, project_id: uuid.UUID, name: str) -> bool:
    sk = await _get_current_skeleton(db, project_id)
    if not sk:
        return False
    original_len = len(sk.skeleton.get("characters", []))
    sk.skeleton["characters"] = [c for c in sk.skeleton.get("characters", []) if c["name"] != name]
    if len(sk.skeleton["characters"]) < original_len:
        await save_skeleton(db, project_id, sk.skeleton, sk.validation_report)
        return True
    return False

async def _get_current_skeleton(db: AsyncSession, project_id: uuid.UUID) -> ProjectSkeleton | None:
    from app.services.storage import get_latest_skeleton
    return await get_latest_skeleton(db, project_id)
```

- [ ] **Step 3: 创建 export.py**

```python
import json
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db import Project, ProjectSkeleton
from app.services.storage import get_latest_skeleton


def _to_markdown(skeleton: dict) -> str:
    lines = []
    doc = skeleton.get("creative_doc", {})
    wr = skeleton.get("world_rules", {})
    chars = skeleton.get("characters", [])
    graph = skeleton.get("graph", {})
    branches = skeleton.get("branches", [])
    foreshadows = skeleton.get("foreshadows", [])

    lines.append("# 叙事骨架\n")

    lines.append("## 核心冲突\n")
    lines.append(f"{doc.get('core_conflict', 'N/A')}\n")

    lines.append("## 世界观规则\n")
    for rule in wr.get("rules", []):
        lines.append(f"- **{rule.get('category')}**: {rule.get('description')}")
        lines.append(f"  - 限制: {rule.get('limitation')}\n")

    lines.append("## 角色\n")
    for c in chars:
        lines.append(f"### {c.get('name')}\n")
        lines.append(f"- 表层欲望: {c.get('desire_topology', {}).get('表层欲望', 'N/A')}")
        lines.append(f"- 深层需求: {c.get('desire_topology', {}).get('深层需求', 'N/A')}")
        lines.append(f"- 核心恐惧: {c.get('desire_topology', {}).get('核心恐惧', 'N/A')}")
        lines.append(f"- 底线: {c.get('bottom_line', 'N/A')}")
        lines.append(f"- 成长弧线: {c.get('growth_arc', 'N/A')}\n")

    lines.append("## 情节图谱\n")
    for n in graph.get("nodes", []):
        lines.append(f"- [{n.get('id')}] {n.get('description')} (情绪: {n.get('emotion_value')})")
    lines.append("")
    for e in graph.get("edges", []):
        lines.append(f"  {e.get('source')} -[{e.get('type')}]-> {e.get('target')}")

    lines.append("\n## 分支\n")
    for b in branches:
        lines.append(f"- 分歧点: {b.get('divergence_point')} → 汇合点: {b.get('convergence_point', '无')}")
        for i, path in enumerate(b.get("paths", [])):
            lines.append(f"  - 路径 {i+1}: {' → '.join(path)}")

    lines.append("\n## 伏笔\n")
    for f in foreshadows:
        lines.append(f"- [{f.get('status')}] {f.get('content')}")
        lines.append(f"  埋设: {f.get('planted_at')}, {f.get('planned_recycle_interval')}")

    return "\n".join(lines)


async def export_json(db: AsyncSession, project_id: uuid.UUID) -> str | None:
    sk = await get_latest_skeleton(db, project_id)
    if not sk or not sk.skeleton:
        return None
    return json.dumps(sk.skeleton, ensure_ascii=False, indent=2)


async def export_markdown(db: AsyncSession, project_id: uuid.UUID) -> str | None:
    sk = await get_latest_skeleton(db, project_id)
    if not sk or not sk.skeleton:
        return None
    return _to_markdown(sk.skeleton)
```

- [ ] **Step 4: 添加新路由**

在 `backend/app/api/routes.py` 末尾添加：

```python
from fastapi.responses import PlainTextResponse

@router.get("/projects")
async def list_projects_route(db: AsyncSession = Depends(get_db)):
    projects = await list_projects(db)
    return [
        {"project_id": str(p.id), "status": p.status, "created_at": p.created_at.isoformat()}
        for p in projects
    ]

@router.delete("/projects/{project_id}")
async def delete_project_route(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    ok = await delete_project(db, project_id)
    if not ok:
        return {"error": "Project not found"}
    return {"ok": True}

@router.put("/projects/{project_id}/skeleton")
async def update_skeleton_route(project_id: uuid.UUID, skeleton: dict, db: AsyncSession = Depends(get_db)):
    from app.services.storage import save_skeleton as save_sk
    sk = await get_latest_skeleton(db, project_id)
    report = sk.validation_report if sk else []
    await save_sk(db, project_id, skeleton, report)
    return {"ok": True}

@router.get("/projects/{project_id}/skeleton/versions")
async def skeleton_versions_route(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    versions = await get_skeleton_versions(db, project_id)
    return [
        {"version": v.version, "created_at": v.created_at.isoformat()}
        for v in versions
    ]

@router.get("/projects/{project_id}/skeleton/versions/{version}")
async def skeleton_version_route(project_id: uuid.UUID, version: int, db: AsyncSession = Depends(get_db)):
    sk = await get_skeleton_by_version(db, project_id, version)
    if not sk:
        return {"error": "Version not found"}
    return {"version": sk.version, "skeleton": sk.skeleton, "validation_report": sk.validation_report}

@router.post("/projects/{project_id}/graph/nodes")
async def add_node_route(project_id: uuid.UUID, node: dict, db: AsyncSession = Depends(get_db)):
    result = await add_graph_node(db, project_id, node)
    return result

@router.put("/projects/{project_id}/graph/nodes/{node_id}")
async def update_node_route(project_id: uuid.UUID, node_id: str, updates: dict, db: AsyncSession = Depends(get_db)):
    result = await update_graph_node(db, project_id, node_id, updates)
    if not result:
        return {"error": "Node not found"}
    return result

@router.delete("/projects/{project_id}/graph/nodes/{node_id}")
async def delete_node_route(project_id: uuid.UUID, node_id: str, db: AsyncSession = Depends(get_db)):
    ok = await delete_graph_node(db, project_id, node_id)
    if not ok:
        return {"error": "Node not found"}
    return {"ok": True}

@router.post("/projects/{project_id}/graph/edges")
async def add_edge_route(project_id: uuid.UUID, edge: dict, db: AsyncSession = Depends(get_db)):
    result = await add_graph_edge(db, project_id, edge)
    return result

@router.delete("/projects/{project_id}/graph/edges")
async def delete_edge_route(project_id: uuid.UUID, source: str, target: str, db: AsyncSession = Depends(get_db)):
    ok = await delete_graph_edge(db, project_id, source, target)
    if not ok:
        return {"error": "Edge not found"}
    return {"ok": True}

@router.post("/projects/{project_id}/characters")
async def add_character_route(project_id: uuid.UUID, character: dict, db: AsyncSession = Depends(get_db)):
    try:
        result = await add_character(db, project_id, character)
        return result
    except ValueError as e:
        return {"error": str(e)}

@router.put("/projects/{project_id}/characters/{name}")
async def update_character_route(project_id: uuid.UUID, name: str, updates: dict, db: AsyncSession = Depends(get_db)):
    result = await update_character(db, project_id, name, updates)
    if not result:
        return {"error": "Character not found"}
    return result

@router.delete("/projects/{project_id}/characters/{name}")
async def delete_character_route(project_id: uuid.UUID, name: str, db: AsyncSession = Depends(get_db)):
    ok = await delete_character(db, project_id, name)
    if not ok:
        return {"error": "Character not found"}
    return {"ok": True}

@router.get("/projects/{project_id}/export/json")
async def export_json_route(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await export_json(db, project_id)
    if not result:
        return {"error": "No skeleton found"}
    return PlainTextResponse(result, media_type="application/json", headers={"Content-Disposition": f"attachment; filename=skeleton-{project_id}.json"})

@router.get("/projects/{project_id}/export/markdown")
async def export_markdown_route(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await export_markdown(db, project_id)
    if not result:
        return {"error": "No skeleton found"}
    return PlainTextResponse(result, media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename=skeleton-{project_id}.md"})
```

- [ ] **Step 5: 更新 routes.py import**

在 routes.py 顶部添加：
```python
from app.services.storage import list_projects, delete_project, get_skeleton_versions, get_skeleton_by_version
from app.services.graph_editor import add_graph_node, update_graph_node, delete_graph_node, add_graph_edge, delete_graph_edge, add_character, update_character, delete_character
from app.services.export import export_json, export_markdown
```

---

### Task 10: 验证

- [ ] **Step 1: 重启并验证后端扩展**

Run: `cd /home/yannick/story-forge && docker compose restart backend && sleep 3`

Run: `curl -s http://localhost:8000/projects | python3 -m json.tool`
Expected: 返回项目列表数组

- [ ] **Step 2: 构建并验证前端**

Run: `cd /home/yannick/story-forge && docker compose up -d --build frontend`

Run: `curl -s http://localhost:5173/ | head -5`
Expected: 返回 HTML

- [ ] **Step 3: 端到端验证**

Run: `curl -s -X POST http://localhost:8000/projects -H 'Content-Type: application/json' -d '{"idea":"test"}'`
Expected: 返回 `{"project_id":"...","status":"pending"}`

Run: 等待生成完成，在浏览器打开 http://localhost:5173 确认 5 个视图正确渲染
