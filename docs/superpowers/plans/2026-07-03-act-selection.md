# Act Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make act group nodes selectable in the plot canvas, showing a collapsible chapter/scene overview in the right panel.

**Architecture:** Add `selectedActId: string | null` state to `EditorShell`, dispatch from `PlotCanvas` via new `onActClick` prop, render new `ActDetail` component in the right panel when an act is selected. `ActDetail` shows chapters as collapsible rows with inline scene editing.

**Tech Stack:** React, TypeScript, React Flow v11, Tailwind CSS

---

### Task 1: Add state and act click handler to EditorShell

**Files:**
- Modify: `frontend/src/pages/editor/layout/EditorShell.tsx`

- [ ] **Step 1: Add `selectedActId` state and condition**

Replace:
```typescript
const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null)
```
With:
```typescript
const [selectedActId, setSelectedActId] = useState<string | null>(null)
const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null)
```

- [ ] **Step 2: Add `handleActClick` callback**

Add after `handleChapterClick`:
```typescript
const handleActClick = useCallback((actId: string) => {
  setSelectedActId(actId)
  setSelectedChapter(null)
}, [])
```

- [ ] **Step 3: Update `handleChapterClick` to clear act selection**

```typescript
const handleChapterClick = useCallback((chapterId: string) => {
  setSelectedChapter(data.chapters.find(c => c.id === chapterId) ?? null)
  setSelectedActId(null)
}, [])
```

- [ ] **Step 4: Pass `onActClick` to PlotCanvas**

Change:
```tsx
<PlotCanvas chapters={data.chapters} acts={data.acts} onChapterClick={handleChapterClick} />
```
To:
```tsx
<PlotCanvas chapters={data.chapters} acts={data.acts} onChapterClick={handleChapterClick} onActClick={handleActClick} />
```

- [ ] **Step 5: Replace ChapterDetail rendering with dual-mode panel**

Replace:
```tsx
{views.activeViewId === 'narrative-plot' && selectedChapter && (
  <ChapterDetail ... />
)}
```
With:
```tsx
{views.activeViewId === 'narrative-plot' && (
  selectedActId ? (
    <ActDetail
      act={data.acts.find(a => a.id === selectedActId)!}
      chapters={data.chapters.filter(c => c.actId === selectedActId)}
      onClose={() => setSelectedActId(null)}
      onSelectChapter={(chId) => {
        setSelectedActId(null)
        setSelectedChapter(data.chapters.find(c => c.id === chId) ?? null)
      }}
      onSceneSave={handleSceneSave}
      onOpenSceneEditor={(scene) => setEditingScene(scene)}
    />
  ) : selectedChapter ? (
    <ChapterDetail
      chapter={selectedChapter}
      onClose={() => setSelectedChapter(null)}
      onSceneSave={handleSceneSave}
      onChapterSave={handleChapterGoalSave}
      onOpenSceneEditor={(scene) => setEditingScene(scene)}
    />
  ) : null
)}
```

- [ ] **Step 6: Import ActDetail**

Add import:
```typescript
import ActDetail from '../views/plot/ActDetail'
```

---

### Task 2: Add onActClick prop to PlotCanvas

**Files:**
- Modify: `frontend/src/pages/editor/views/plot/PlotCanvas.tsx`

- [ ] **Step 1: Update interface**

```typescript
interface PlotCanvasProps {
  chapters: Chapter[]
  acts: Act[]
  onChapterClick?: (chapterId: string) => void
  onActClick?: (actId: string) => void
}
```

- [ ] **Step 2: Update function signature**

```typescript
export default function PlotCanvas({ chapters, acts, onChapterClick, onActClick }: PlotCanvasProps) {
```

- [ ] **Step 3: Add actGroup handling to handleNodeClick**

```typescript
const handleNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
  if (node.type === 'chapter') onChapterClick?.(node.id)
  if (node.type === 'actGroup') onActClick?.(node.id.replace('act-', ''))
}, [onChapterClick, onActClick])
```

- [ ] **Step 4: Add onPaneClick to ReactFlow**

Add `onPaneClick` to `ReactFlow` component (clear selection):
```tsx
onPaneClick={useCallback(() => {
  onActClick?.('')
}, [onActClick])}
```

- [ ] **Step 5: Handle empty actId in onActClick**

In `EditorShell`, update `handleActClick` to handle empty string:
```typescript
const handleActClick = useCallback((actId: string) => {
  if (!actId) { setSelectedActId(null); return }
  setSelectedActId(actId)
  setSelectedChapter(null)
}, [])
```

---

### Task 3: Create ActDetail component

**Files:**
- Create: `frontend/src/pages/editor/views/plot/ActDetail.tsx`

- [ ] **Step 1: Write the component**

```typescript
import { useState } from 'react'
import type { Act, Chapter, Scene } from '../../types'

interface ActDetailProps {
  act: Act
  chapters: Chapter[]
  onClose: () => void
  onSelectChapter: (chapterId: string) => void
  onSceneSave: (chapterId: string, sceneId: string, content: string) => void
  onOpenSceneEditor?: (scene: Scene) => void
}

const STATUS_OPTIONS = [
  { value: 'draft' as const, label: '草稿' },
  { value: 'revising' as const, label: '修改' },
  { value: 'final' as const, label: '定稿' },
]

export default function ActDetail({ act, chapters, onClose, onSelectChapter, onSceneSave, onOpenSceneEditor }: ActDetailProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [editSceneId, setEditSceneId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')

  const totalWords = chapters.reduce((s, c) => s + c.wordCount, 0)
  const totalScenes = chapters.reduce((s, c) => s + c.scenes.length, 0)

  const toggleExpand = (chId: string) => {
    setExpandedId(expandedId === chId ? null : chId)
    setEditSceneId(null)
  }

  const startEdit = (scene: Scene) => {
    setEditSceneId(scene.id)
    setEditContent(scene.content)
  }

  const saveScene = (chapterId: string) => {
    if (editSceneId) {
      onSceneSave(chapterId, editSceneId, editContent)
      setEditSceneId(null)
    }
  }

  return (
    <div className="absolute right-0 top-0 h-full w-96 bg-gray-900/95 backdrop-blur-xl border-l border-gray-800 z-20 flex flex-col shadow-2xl">
      {/* Header */}
      <div className="p-4 border-b border-gray-800" style={{ borderLeft: `3px solid ${act.color}` }}>
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-medium text-amber-100">{act.name}</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-lg leading-none">✕</button>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>{chapters.length} 章</span>
          <span>{totalScenes} 场</span>
          <span>{totalWords > 0 ? `${totalWords} 字` : '未开始'}</span>
          <span className="text-gray-600">
            {chapters.filter(c => c.status === 'final').length}/{chapters.length} 完成
          </span>
        </div>
      </div>

      {/* Chapter list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
        {chapters.map(ch => {
          const isExpanded = expandedId === ch.id
          return (
            <div key={ch.id} className="bg-gray-800/40 border border-gray-700/40 rounded-xl overflow-hidden">
              {/* Chapter header row */}
              <button
                onClick={() => toggleExpand(ch.id)}
                className="w-full flex items-center gap-2 px-3 py-2.5 hover:bg-gray-700/30 transition-colors text-left"
              >
                <span className="text-xs text-gray-500 w-4 shrink-0">{isExpanded ? '▾' : '▸'}</span>
                <span className="text-sm font-medium text-gray-200 flex-1 truncate">{ch.title}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                  ch.status === 'final' ? 'bg-green-900/30 text-green-400' :
                  ch.status === 'revising' ? 'bg-amber-900/30 text-amber-400' :
                  'bg-gray-800 text-gray-500'
                }`}>{STATUS_OPTIONS.find(s => s.value === ch.status)?.label}</span>
                <span className="text-[10px] text-gray-600 w-10 text-right">{ch.wordCount > 0 ? `${ch.wordCount}w` : '-'}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); onSelectChapter(ch.id) }}
                  className="text-[10px] text-gray-600 hover:text-amber-400 transition-colors px-1"
                  title="聚焦到本章"
                >🔍</button>
              </button>

              {/* Expanded scene list */}
              {isExpanded && (
                <div className="px-3 pb-3 space-y-2 border-t border-gray-700/30 pt-2">
                  {ch.scenes.map(scene => (
                    <div key={scene.id} className="bg-gray-800/60 border border-gray-700/40 rounded-lg p-2.5">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-gray-300">{scene.title}</span>
                        <span className="text-[10px] text-gray-600">{scene.wordCount > 0 ? `${scene.wordCount}字` : '空'}</span>
                      </div>
                      <div className="flex flex-wrap gap-x-2 gap-y-0.5 text-[10px] text-gray-600 mb-1.5">
                        <span>🎭 {scene.povCharacter}</span>
                        <span>📍 {scene.setting}</span>
                        <span>⏰ {scene.time}</span>
                      </div>
                      {editSceneId === scene.id ? (
                        <div className="space-y-1.5">
                          <textarea
                            value={editContent}
                            onChange={e => setEditContent(e.target.value)}
                            className="w-full h-28 bg-gray-950 border border-gray-700 rounded-lg p-2 text-xs text-gray-300 resize-none focus:outline-none focus:border-amber-600 font-mono leading-relaxed"
                            placeholder="写小说正文..."
                          />
                          <div className="flex gap-2">
                            <button onClick={() => saveScene(ch.id)} className="px-3 py-1 rounded-lg bg-amber-600 text-xs font-medium text-black hover:bg-amber-500 transition-colors">保存</button>
                            <button onClick={() => setEditSceneId(null)} className="px-3 py-1 rounded-lg bg-gray-700 text-xs text-gray-300 hover:bg-gray-600 transition-colors">取消</button>
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => startEdit(scene)}
                          className={`w-full text-left px-2.5 py-2 rounded-lg text-xs transition-colors ${
                            scene.content
                              ? 'bg-gray-950/50 text-gray-400 hover:bg-gray-800 border border-gray-800'
                              : 'bg-gray-800/30 text-gray-600 hover:bg-gray-700 border border-dashed border-gray-700'
                          }`}
                        >
                          {scene.content
                            ? <span className="line-clamp-2 font-mono leading-relaxed">{scene.content}</span>
                            : '✏️ 点击开始写作...'}
                        </button>
                      )}
                      {editSceneId !== scene.id && (
                        <button
                          onClick={(e) => { e.stopPropagation(); onOpenSceneEditor?.(scene) }}
                          className="w-full mt-1 px-2 py-1 rounded text-[10px] text-gray-600 hover:text-gray-400 hover:bg-gray-700/50 transition-colors text-center"
                        >
                          全屏编辑 ↗
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
        {chapters.length === 0 && (
          <div className="text-center text-gray-600 text-sm py-8">该幕暂无章节</div>
        )}
      </div>
    </div>
  )
}
```

---

### Task 4: Add selected visual feedback to ActGroupNode

**Files:**
- Modify: `frontend/src/pages/editor/views/plot/ActGroupNode.tsx`

- [ ] **Step 1: Apply selected highlight styling**

Change the outer div to apply a highlighted border when selected:
```tsx
<div
  ref={divRef}
  className={`w-full h-full rounded-xl border pointer-events-none transition-shadow ${selected ? 'shadow-[0_0_12px_2px_rgba(251,191,36,0.3)]' : ''}`}
  style={{
    backgroundColor: data.color + '0d',
    borderColor: selected ? '#fbbf24' : data.color + '25',
  }}
  ...
>
```

- [ ] **Step 2: Read `selected` from NodeProps**

The `selected` prop is available on `NodeProps` in React Flow v11. Use destructuring:
```typescript
function ActGroupNode({ id, data, selected }: NodeProps<ActGroupData>) {
```

---

### Task 5: Verify build

- [ ] **Step 1: Run tsc**

Run:
```bash
cd /home/yannick/StoryCAD && wsl docker exec storycad-frontend-1 sh -c 'cd /app && npx tsc --noEmit'
```
Expected: exit code 0, no errors

- [ ] **Step 2: Verify page loads**

Curl the editor route:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/projects/test
```
Expected: 200
