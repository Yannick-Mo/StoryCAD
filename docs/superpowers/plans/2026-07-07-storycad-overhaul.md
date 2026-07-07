# StoryCAD 全面改造实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复安全漏洞、补全损坏功能、提升代码质量、补充缺失 API，使 StoryCAD 达到生产可用水平。

**Architecture:** 四梯队按优先级顺序实施。后端 FastAPI + SQLAlchemy async + Alembic，前端 React + TypeScript。每个梯队验证后再进入下一梯队。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, React 18, TypeScript, React Flow, LangGraph, DeepSeek API

---

## 文件结构

### 新建文件
| 文件 | 用途 |
|------|------|
| `backend/app/agent/project_creator/utils.py` | `_parse_json()`、`_load_prompt()` 共享函数 |
| `frontend/src/pages/editor/views/rhythm/RhythmEditPanel.tsx` | 节奏编辑滑块面板 |

### 新增 Migration
| 文件 | 用途 |
|------|------|
| `backend/alembic/versions/0008_add_chapter_rhythms.py` | 创建 chapter_rhythms 表 |

### 修改文件
| 文件 | 修改内容 |
|------|---------|
| **P0 安全** | |
| `backend/app/main.py:9-12` | 启动时检查 JWT 密钥非空 |
| `backend/app/api/routes_auth.py:11-25` | RegisterRequest Pydantic model + 输入校验 |
| `backend/app/api/routes_storycad.py:129-187` | get/put/delete entity 加归属校验 |
| **P1 功能** | |
| `backend/app/storycad/models.py` | 新增 ChapterRhythm model |
| `backend/app/storycad/entity_map.py` | 注册 rhythms -> ChapterRhythm |
| `backend/app/storycad/repository.py:81-103` | sync_editor_data 支持 rhythms |
| `backend/app/api/routes_project.py` | 增加统计字段 + 搜索参数 |
| `backend/app/project/service.py` | 查询字数/章节数统计 |
| `frontend/src/api/editor.ts:71` | normalizeApiData 映射 rhythms |
| `frontend/src/pages/editor/views/rhythm/RhythmView.tsx` | 点击立柱弹出面板、intensity 折线 |
| `frontend/src/pages/editor/views/theme/ThemeView.tsx` | 添加主题按钮、卡片操作 |
| `frontend/src/pages/editor/views/theme/ThemeDetail.tsx` | 笔记保存调 API |
| `frontend/src/pages/editor/EditorShell.tsx:236` | onLayout 实现、onSaveNote 实现 |
| `frontend/src/pages/editor/components/PlotToolbar.tsx:13` | 布局按钮功能 |
| `frontend/src/pages/home/ProjectGrid.tsx:15-29` | 真实数据展示 |
| `frontend/src/pages/home/index.tsx` | 传递真实统计数据 |
| **P2 代码质量** | |
| `backend/app/user/repository.py:76-78` | 删除死代码 |
| `backend/app/agent/project_creator/nodes/*.py` | 改用共享 utils |
| `backend/app/database.py:9-12` | 移除 create_all |
| `backend/app/storycad/repository.py:100-103` | 版本快照优化 |
| `backend/app/agent/project_creator/nodes/scenes.py:109` | asyncio.Semaphore(5) |
| `backend/requirements.txt` | 删除 passlib |
| `frontend/src/api/auth.ts:132-134` | 删除 unused updateProfile |
| `frontend/src/api/editor.ts:47-65` | 删除 unused CRUD 函数 |
| **P3 API** | |
| `backend/app/api/routes_project.py` | + GET/PUT config, + search params |
| `backend/app/project/service.py` | + config CRUD, + search logic |

---

## 任务清单

### P0 安全修复

---

### Task 1: JWT 密钥强制配置

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/config.py`

- [ ] **Step 1: 在 main.py 启动时检查 JWT 密钥**

打开 `backend/app/main.py`，在 `create_app()` 函数开头添加：

```python
from app.config import settings as app_settings

def create_app() -> FastAPI:
    if not app_settings.jwt_secret_key:
        raise ValueError(
            "JWT_SECRET_KEY is not configured. "
            "Set it in .env file or JWT_SECRET_KEY environment variable."
        )
    # ... rest of the function
```

- [ ] **Step 2: 重启验证**

```bash
cd /home/yannick/StoryCAD
docker compose restart backend
# 等 3 秒看日志
docker logs storycad-backend-1 --tail 5
```

Expected: 容器正常启动（JWT 密钥已通过 `.env` 配置）

- [ ] **Step 3: 提交**

```bash
git add backend/app/main.py
git commit -m "fix: enforce JWT_SECRET_KEY at startup, fail fast if empty"
```

---

### Task 2: 实体归属交叉校验

**Files:**
- Modify: `backend/app/api/routes_storycad.py:129-187`

- [ ] **Step 1: 在 get_entity 函数中加归属校验**

```python
@router.get("/{entity_type}/{entity_id}")
async def get_entity(project_id: UUID, entity_type: str, entity_id: UUID, ...):
    entity = await repo.get(entity_type, entity_id)
    if not entity:
        raise HTTPException(status_code=404)
    if getattr(entity, "project_id", None) != project_id:
        raise HTTPException(status_code=404)
    # ... rest
```

- [ ] **Step 2: 在 put_entity 函数中加归属校验**

同样的校验逻辑，在更新之前检查 `entity.project_id == project_id`。

- [ ] **Step 3: 在 delete_entity 函数中加归属校验**

同样的校验逻辑，在删除之前检查 `entity.project_id == project_id`。

- [ ] **Step 4: 提交**

```bash
git add backend/app/api/routes_storycad.py
git commit -m "fix: verify entity.project_id == project_id in generic CRUD"
```

---

### Task 3: 注册输入校验

**Files:**
- Modify: `backend/app/api/routes_auth.py:11-25`

- [ ] **Step 1: 添加 RegisterRequest Pydantic model**

```python
from pydantic import BaseModel, EmailStr, Field, validator
import re

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    email: str = Field(...)
    password: str = Field(..., min_length=8)

    @validator("username")
    def validate_username(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username must be alphanumeric with underscores only")
        return v

    @validator("email")
    def validate_email(cls, v):
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email format")
        return v
```

- [ ] **Step 2: 替换 register 路由中的 payload 类型**

将 `payload: dict` 改为 `payload: RegisterRequest`，去掉手动校验代码。

```python
@router.post("/register", status_code=201)
async def register(payload: RegisterRequest, ...):
    existing = await repo.get_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    existing = await repo.get_by_username(payload.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    user = await repo.create(payload.username, payload.email, payload.password)
    token = create_access_token(str(user.id))
    return {"token": token, "user": {"id": str(user.id), "username": user.username, "email": user.email}}
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/routes_auth.py
git commit -m "fix: add input validation for register endpoint"
```

---

### P1 功能修复

---

### Task 4: Rhythm 数据模型 + Migration

**Files:**
- Modify: `backend/app/storycad/models.py`
- Create: `backend/alembic/versions/0008_add_chapter_rhythms.py`

- [ ] **Step 1: 在 models.py 添加 ChapterRhythm**

```python
class ChapterRhythm(Base):
    __tablename__ = "chapter_rhythms"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, unique=True)
    action: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    suspense: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    emotion: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    humor: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    intensity: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

同时在文件顶部 imports 中加上 `from sqlalchemy import UniqueConstraint`，并在 `ChapterRhythm` 中加约束确保章节唯一。

- [ ] **Step 2: 生成 migration**

```bash
cd /home/yannick/StoryCAD
wsl.exe bash -c "cd /home/yannick/StoryCAD && docker compose exec backend alembic revision --autogenerate -m 'add chapter_rhythms' 2>&1"
```

如果 autogenerate 不工作，手动编写 migration 文件 0008。

- [ ] **Step 3: 手动编写 migration 0008**

创建 `backend/alembic/versions/0008_add_chapter_rhythms.py`：

```python
"""add chapter_rhythms

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0008"
down_revision = "0007"

def upgrade():
    op.create_table(
        "chapter_rhythms",
        sa.Column("id", UUID, primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("chapter_id", UUID, sa.ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("action", sa.Integer, nullable=False, server_default="5"),
        sa.Column("suspense", sa.Integer, nullable=False, server_default="5"),
        sa.Column("emotion", sa.Integer, nullable=False, server_default="5"),
        sa.Column("humor", sa.Integer, nullable=False, server_default="5"),
        sa.Column("intensity", sa.Integer, nullable=False, server_default="5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table("chapter_rhythms")
```

- [ ] **Step 4: 运行 migration**

```bash
wsl.exe bash -c "cd /home/yannick/StoryCAD && docker compose exec backend alembic upgrade head 2>&1"
```

Expected: `INFO  [alembic.runtime.migration] Running upgrade 0007 -> 0008`

- [ ] **Step 5: 注册到 entity_map.py**

在 `backend/app/storycad/entity_map.py` 的 ENTITY_MAP 中添加：
```python
"rhythms": ChapterRhythm,
```

导入添加：
```python
from app.storycad.models import ChapterRhythm
```

- [ ] **Step 6: 更新 sync_editor_data 支持 rhythms**

在 `backend/app/storycad/repository.py` 的 `sync_editor_data` 方法中，确保 `chapter_rhythms` 被处理。当前的同步逻辑已经循环所有 entity_type，所以只需确保 `rhythms` 表有正确的关系映射（entity_map 已注册即可）。

- [ ] **Step 7: 更新 normalizeApiData**

在 `frontend/src/api/editor.ts` 的 `normalizeApiData` 中添加：
```typescript
rhythms: (data.rhythms || []).map((r: any) => ({
  id: r.id,
  chapterId: r.chapter_id,
  action: r.action,
  suspense: r.suspense,
  emotion: r.emotion,
  humor: r.humor,
  intensity: r.intensity,
})),
```

- [ ] **Step 8: 提交**

```bash
git add backend/app/storycad/models.py backend/app/storycad/entity_map.py backend/alembic/versions/0008_add_chapter_rhythms.py frontend/src/api/editor.ts
git commit -m "feat: add ChapterRhythm model, migration, entity map, and frontend normalization"
```

---

### Task 5: Rhythm 前端编辑 UI

**Files:**
- Create: `frontend/src/pages/editor/views/rhythm/RhythmEditPanel.tsx`
- Modify: `frontend/src/pages/editor/views/rhythm/RhythmView.tsx`
- Modify: `frontend/src/pages/editor/EditorShell.tsx`

- [ ] **Step 1: 创建 RhythmEditPanel 组件**

```tsx
// frontend/src/pages/editor/views/rhythm/RhythmEditPanel.tsx
import { useState, useEffect } from "react"

interface RhythmEditPanelProps {
  chapterId: string
  chapterTitle: string
  initialValues: { action: number; suspense: number; emotion: number; humor: number; intensity: number }
  onSave: (values: { action: number; suspense: number; emotion: number; humor: number; intensity: number }) => void
  onClose: () => void
}

export function RhythmEditPanel({ chapterId, chapterTitle, initialValues, onSave, onClose }: RhythmEditPanelProps) {
  const [action, setAction] = useState(initialValues.action)
  const [suspense, setSuspense] = useState(initialValues.suspense)
  const [emotion, setEmotion] = useState(initialValues.emotion)
  const [humor, setHumor] = useState(initialValues.humor)
  const intensity = Math.round((action + suspense + emotion + humor) / 4)

  const handleSave = () => {
    onSave({ action, suspense, emotion, humor, intensity })
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-80" onClick={e => e.stopPropagation()}>
        <h3 className="text-white font-semibold mb-1">{chapterTitle}</h3>
        <p className="text-gray-400 text-sm mb-4">节奏维度编辑</p>

        <div className="space-y-3">
          <div>
            <label className="flex justify-between text-sm"><span style={{ color: "#f97316" }}>动作</span><span>{action}</span></label>
            <input type="range" min="0" max="10" value={action} onChange={e => setAction(Number(e.target.value))}
              className="w-full accent-orange-500" />
          </div>
          <div>
            <label className="flex justify-between text-sm"><span style={{ color: "#3b82f6" }}>悬疑</span><span>{suspense}</span></label>
            <input type="range" min="0" max="10" value={suspense} onChange={e => setSuspense(Number(e.target.value))}
              className="w-full accent-blue-500" />
          </div>
          <div>
            <label className="flex justify-between text-sm"><span style={{ color: "#ec4899" }}>情感</span><span>{emotion}</span></label>
            <input type="range" min="0" max="10" value={emotion} onChange={e => setEmotion(Number(e.target.value))}
              className="w-full accent-pink-500" />
          </div>
          <div>
            <label className="flex justify-between text-sm"><span style={{ color: "#22c55e" }}>幽默</span><span>{humor}</span></label>
            <input type="range" min="0" max="10" value={humor} onChange={e => setHumor(Number(e.target.value))}
              className="w-full accent-green-500" />
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-gray-700">
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">强度指数</span>
            <span className="text-white font-bold">{intensity}/10</span>
          </div>
          <div className="h-2 bg-gray-700 rounded mt-1 overflow-hidden">
            <div className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded transition-all"
              style={{ width: `${intensity * 10}%` }} />
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          <button onClick={onClose} className="flex-1 px-3 py-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600">取消</button>
          <button onClick={handleSave} className="flex-1 px-3 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-500">保存</button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 修改 RhythmView 使立柱可点击**

在 `frontend/src/pages/editor/views/rhythm/RhythmView.tsx` 中找到渲染柱状图的代码，为每个立柱的容器添加 `onClick` 处理，打开 RhythmEditPanel。

在 RhythmView 中添加状态：
```tsx
const [editChapter, setEditChapter] = useState<{ id: string; title: string } | null>(null)
```

渲染 RhythmEditPanel：
```tsx
{editChapter && (
  <RhythmEditPanel
    chapterId={editChapter.id}
    chapterTitle={editChapter.title}
    initialValues={getRhythmForChapter(editChapter.id)}
    onSave={(values) => {
      store.enqueueChange("rhythms", editChapter.id, { ...values, chapterId: editChapter.id })
    }}
    onClose={() => setEditChapter(null)}
  />
)}
```

同时在柱状图上方添加 intensity 折线覆盖层。使用 SVG 或 canvas 在柱状图区域绘制连接各章 intensity 值的折线。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/editor/views/rhythm/
git commit -m "feat: add rhythm edit panel with sliders and intensity curve overlay"
```

---

### Task 6: Theme 前端 CRUD

**Files:**
- Modify: `frontend/src/pages/editor/views/theme/ThemeView.tsx`
- Modify: `frontend/src/pages/editor/views/theme/ThemeDetail.tsx`
- Modify: `frontend/src/pages/editor/EditorShell.tsx`

- [ ] **Step 1: ThemeView 添加 Create 按钮**

在 `ThemeView.tsx` 中添加「添加主题」按钮和创建对话框：

```tsx
// 在组件中添加状态
const [showCreate, setShowCreate] = useState(false)

// 添加按钮（在主题卡片网格上方）
<button onClick={() => setShowCreate(true)}
  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500">
  + 添加主题
</button>

// 创建对话框
{showCreate && (
  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-96">
      <h3 className="text-white font-semibold mb-4">新建主题</h3>
      <div className="space-y-3">
        <div>
          <label className="text-sm text-gray-400">名称</label>
          <input className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white mt-1" />
        </div>
        <div>
          <label className="text-sm text-gray-400">颜色</label>
          <div className="flex gap-2 mt-1">
            {["#d4a373","#6b7280","#ef4444","#3b82f6","#22c55e","#a855f7"].map(c => (
              <div key={c} className="w-8 h-8 rounded-full cursor-pointer border-2 border-transparent hover:border-white"
                style={{ backgroundColor: c }} />
            ))}
          </div>
        </div>
        <div>
          <label className="text-sm text-gray-400">命题</label>
          <textarea className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white mt-1" rows={3} />
        </div>
      </div>
      <div className="flex gap-2 mt-4">
        <button onClick={() => setShowCreate(false)} className="flex-1 px-3 py-2 rounded bg-gray-700 text-gray-300">取消</button>
        <button onClick={handleCreateTheme} className="flex-1 px-3 py-2 rounded bg-blue-600 text-white">确定</button>
      </div>
    </div>
  </div>
)}
```

`handleCreateTheme` 调用 `store.enqueueChange("themes", crypto.randomUUID(), { name, color, proposition })`。

- [ ] **Step 2: Theme 卡片悬停显示操作按钮**

在 ThemeView 的主题卡片渲染中添加悬停操作：
```tsx
<div className="group relative">
  {/* existing theme card content */}
  <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
    <button onClick={() => setEditTheme(theme)} className="p-1 bg-gray-800 rounded hover:bg-gray-700"
      title="编辑">✎</button>
    <button onClick={() => setDeleteTheme(theme)} className="p-1 bg-gray-800 rounded hover:bg-red-700"
      title="删除">✕</button>
  </div>
</div>
```

添加删除确认弹窗，确认后调用 `store.enqueueChange("themes", theme.id, null)`（null 表示删除）。

- [ ] **Step 3: ThemeDetail 笔记保存**

在 `ThemeDetail.tsx` 中找到笔记（note）的保存逻辑，将 `onSaveNote` 从空函数改为实际调用：

```tsx
// 在组件中添加 effect
const { selectedTheme } = store

// 当笔记内容变化且 blur 时，调用保存
const [note, setNote] = useState("")

useEffect(() => {
  if (selectedTheme) setNote(selectedTheme.note || "")
}, [selectedTheme])

const handleBlur = () => {
  if (selectedTheme) {
    store.enqueueChange("themes", selectedTheme.id, { note })
  }
}
```

在 `EditorShell.tsx` 中将 `onSaveNote={() => {}}` 替换为实际处理函数（通过 store 同步）。

- [ ] **Step 4: 提交**

```bash
git add frontend/src/pages/editor/views/theme/ frontend/src/pages/editor/EditorShell.tsx
git commit -m "feat: add theme CRUD UI (create, edit, delete, note save)"
```

---

### Task 7: Layout 按钮实现

**Files:**
- Modify: `frontend/src/pages/editor/EditorShell.tsx:236`
- Modify: `frontend/src/pages/editor/components/PlotToolbar.tsx:13`

- [ ] **Step 1: 在 EditorShell 中实现 onLayout**

导入 dagre 布局库，或在 `PlotCanvas` 已有的拓扑排序基础上实现简单布局。

如果在 PlotCanvas 中已有拓扑排序逻辑，布局按钮可以触发重排：
```tsx
const handleLayout = () => {
  // 使用已知的拓扑排序结果重新分配节点位置
  const { chapters, acts } = store.data
  const layout = autoLayout(chapters, acts) // 基于拓扑排序 + 层分配
  store.setNodePositions(layout)
}
```

在 EditorShell 中替换：
```tsx
onLayout={handleLayout}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/pages/editor/EditorShell.tsx frontend/src/pages/editor/components/PlotToolbar.tsx
git commit -m "feat: implement auto-layout button using topological sort"
```

---

### Task 8: 项目列表真实数据

**Files:**
- Modify: `backend/app/api/routes_project.py`
- Modify: `backend/app/project/service.py`
- Modify: `frontend/src/pages/home/ProjectGrid.tsx`
- Modify: `frontend/src/pages/home/index.tsx`

- [ ] **Step 1: 后端查询统计字段**

在 `backend/app/project/service.py` 的 `list_projects` 方法中，对每个项目查询统计：

```python
async def list_projects(self, owner_id: uuid.UUID, page: int, size: int, search: str = "", status: str = ""):
    query = select(Project).where(Project.owner_id == owner_id)
    if search:
        query = query.where(Project.title.ilike(f"%{search}%"))
    if status:
        query = query.where(Project.status == status)
    query = query.order_by(Project.updated_at.desc())
    
    result = await self.db.execute(query.offset((page - 1) * size).limit(size))
    projects = result.scalars().all()

    items = []
    for p in projects:
        # 查询统计
        ch_count_q = select(func.count()).select_from(Chapter).where(Chapter.project_id == p.id)
        sc_count_q = select(func.count()).select_from(Scene).where(Scene.project_id == p.id)
        words_q = select(func.coalesce(func.sum(Chapter.total_words), 0)).where(Chapter.project_id == p.id)
        
        ch_count = (await self.db.execute(ch_count_q)).scalar() or 0
        sc_count = (await self.db.execute(sc_count_q)).scalar() or 0
        words = (await self.db.execute(words_q)).scalar() or 0

        # 查询 config
        config_q = select(ProjectConfig).where(ProjectConfig.project_id == p.id)
        config = (await self.db.execute(config_q)).scalar_one_or_none()

        items.append({
            "id": str(p.id),
            "title": p.title,
            "status": p.status,
            "genre": p.genre,
            "template_type": config.template_type if config else "",
            "total_words": words,
            "total_chapters": ch_count,
            "total_scenes": sc_count,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat(),
        })

    # 总数查询
    count_q = select(func.count()).select_from(Project).where(Project.owner_id == owner_id)
    total = (await self.db.execute(count_q)).scalar() or 0

    return {"items": items, "total": total, "page": page, "size": size}
```

- [ ] **Step 2: 更新路由参数**

在 `backend/app/api/routes_project.py` 的 `GET /api/projects` 中添加查询参数：
```python
@router.get("")
async def list_projects(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    status: str = Query(""),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    result = await service.list_projects(uuid.UUID(current_user["id"]), page, size, search, status)
    return result
```

- [ ] **Step 3: 更新前端 ProjectGrid 展示真实数据**

删除 `enrichProject()` 中的假数据生成逻辑，直接从 API 响应中读取真实字段：

```typescript
// 替换 enrichProject 函数
interface ProjectCardData {
  id: string
  title: string
  status: string
  genre: string
  template_type: string
  total_words: number
  total_chapters: number
  total_scenes: number
  created_at: string
  updated_at: string
}
```

卡片渲染使用真实数据：
```tsx
<div className="project-card">
  <div className="font-semibold text-white">{project.title}</div>
  <div className="flex gap-3 text-sm text-gray-400 my-2">
    <span>{project.total_words.toLocaleString()} 字</span>
    <span>{project.total_chapters} 章 / {project.total_scenes} 场景</span>
  </div>
  <div className="h-1 bg-gray-700 rounded overflow-hidden">
    <div className="h-full bg-gradient-to-r from-blue-500 to-green-500 rounded"
      style={{ width: `${Math.min((project.total_words / 100000) * 100, 100)}%` }} />
  </div>
  <div className="flex gap-2 mt-2">
    {project.genre && <span className="px-2 py-0.5 bg-gray-700 rounded text-xs">{project.genre}</span>}
    {project.template_type && <span className="px-2 py-0.5 bg-gray-700 rounded text-xs">{project.template_type}</span>}
    <span className="px-2 py-0.5 bg-gray-700 rounded text-xs">{statusLabel(project.status)}</span>
  </div>
</div>
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/api/routes_project.py backend/app/project/service.py frontend/src/pages/home/ProjectGrid.tsx frontend/src/pages/home/index.tsx
git commit -m "feat: real project stats from backend, redesigned project cards"
```

---

### P2 代码质量

---

### Task 9: 提取共享工具函数

**Files:**
- Create: `backend/app/agent/project_creator/utils.py`
- Modify: `backend/app/agent/project_creator/nodes/analyze.py`
- Modify: `backend/app/agent/project_creator/nodes/plan.py`
- Modify: `backend/app/agent/project_creator/nodes/characters.py`
- Modify: `backend/app/agent/project_creator/nodes/settings.py`
- Modify: `backend/app/agent/project_creator/nodes/scenes.py`

- [ ] **Step 1: 创建 utils.py**

```python
# backend/app/agent/project_creator/utils.py
import json
import yaml
from pathlib import Path

PROMPT_DIR = Path(__file__).parent / "prompts"

def load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("system", "")

def parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        end = next((i for i in range(len(lines) - 1, 0, -1) if lines[i].strip() == "```"), len(lines))
        text = "\n".join(lines[1:end])
    return json.loads(text)
```

- [ ] **Step 2: 替换 5 个节点文件中的重复代码**

每个节点文件删除本地的 `_load()` 和 `_parse_json()` 函数，改为：
```python
from app.agent.project_creator.utils import load_prompt, parse_json
```

将原有的 `_load("xxx")` 调用替换为 `load_prompt("xxx")`，`_parse_json(raw)` 替换为 `parse_json(raw)`。

- [ ] **Step 3: 提交**

```bash
git add backend/app/agent/project_creator/utils.py backend/app/agent/project_creator/nodes/
git commit -m "refactor: extract shared _parse_json and _load into utils.py"
```

---

### Task 10: 删除死代码

**Files:**
- Modify: `backend/app/user/repository.py:76-78`
- Modify: `backend/app/agent/project_creator/nodes/scenes.py:74-95`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 删除 user/repository.py 死代码**

打开 `backend/app/user/repository.py`，找到 `delete` 方法末尾的：

```python
        return True

        await self.db.delete(user)   # line 76
        await self.db.commit()       # line 77
        return True                  # line 78
```

删除不可达的 76-78 行。

- [ ] **Step 2: 删除 scenes.py 死函数**

删除 `backend/app/project_creator/nodes/scenes.py` 中的 `generate_scene_chapter()` 函数（74-95 行），只保留 `generate_all_scenes()`。

- [ ] **Step 3: 从 requirements.txt 删除 passlib**

编辑 `backend/requirements.txt`，删除 `passlib[bcrypt]>=1.7.4` 这一行。

- [ ] **Step 4: 提交**

```bash
git add backend/app/user/repository.py backend/app/agent/project_creator/nodes/scenes.py backend/requirements.txt
git commit -m "refactor: remove dead code (unreachable lines, unused function, passlib dep)"
```

---

### Task 11: 版本快照优化

**Files:**
- Modify: `backend/app/storycad/repository.py:100-103`

- [ ] **Step 1: 给 sync_editor_data 添加变更检测**

在创建 `ProjectVersion` 之前，先检查是否有实际数据变更。简单方案：比较输入数据的内存表示是否有变化。

```python
# 在 sync_editor_data 末尾，创建版本之前
# 如果没有任何实体被实际创建/更新/删除，跳过版本创建
if not any([inserts, updates, deletes]):
    return {"success": True, "version": current_version}
```

更精确的方案：对比每个 entity 的当前 DB 值与输入值是否一致。

- [ ] **Step 2: 提交**

```bash
git add backend/app/storycad/repository.py
git commit -m "perf: skip version snapshot when no data changes in sync"
```

---

### Task 12: asyncio.gather 节流

**Files:**
- Modify: `backend/app/agent/project_creator/nodes/scenes.py:109`

- [ ] **Step 1: 添加 Semaphore**

在 `generate_all_scenes` 函数中：

```python
import asyncio

async def generate_all_scenes(state: MaterialState) -> dict:
    sem = asyncio.Semaphore(5)  # 最大并发 5

    async def _generate_one(act_idx, chap_idx, act_name, chapter_title, chapter_goal):
        async with sem:
            return await _generate_one_chapter(...)

    tasks = []
    for act_idx, act in enumerate(state.get("acts", [])):
        for chap_idx, chapter in enumerate(act.get("chapters", [])):
            tasks.append(_generate_one(...))

    results = await asyncio.gather(*tasks)
    # ...rest
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/agent/project_creator/nodes/scenes.py
git commit -m "perf: limit LLM concurrency to 5 in generate_all_scenes"
```

---

### Task 13: 移除 create_all

**Files:**
- Modify: `backend/app/database.py:9-12`

- [ ] **Step 1: 删除 init_db 中的 create_all**

```python
async def init_db():
    # 删除以下两行：
    # import app.project.models  # noqa
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    pass  # 或直接删除函数体，只保留 pass
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/database.py
git commit -m "refactor: remove create_all on startup, rely on migrations only"
```

---

### P3 缺失 API

---

### Task 14: Project Config API

**Files:**
- Modify: `backend/app/api/routes_project.py`
- Modify: `backend/app/project/service.py`

- [ ] **Step 1: 添加 GET/PUT config 路由**

```python
@router.get("/{project_id}/config")
async def get_project_config(
    project_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    config = await service.get_config(uuid.UUID(current_user["id"]), project_id)
    if not config:
        raise HTTPException(status_code=404)
    return {
        "id": str(config.id),
        "project_id": str(config.project_id),
        "total_words": config.total_words,
        "template_type": config.template_type,
        "target_audience": config.target_audience,
    }

@router.put("/{project_id}/config")
async def update_project_config(
    project_id: UUID,
    payload: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    config = await service.update_config(uuid.UUID(current_user["id"]), project_id, payload)
    return {"success": True}
```

- [ ] **Step 2: 在 service.py 中添加 config 方法**

```python
async def get_config(self, owner_id: uuid.UUID, project_id: uuid.UUID):
    # 验证所有权
    project = await self._get_project(owner_id, project_id)
    if not project:
        return None
    q = select(ProjectConfig).where(ProjectConfig.project_id == project_id)
    result = await self.db.execute(q)
    return result.scalar_one_or_none()

async def update_config(self, owner_id: uuid.UUID, project_id: uuid.UUID, data: dict):
    project = await self._get_project(owner_id, project_id)
    if not project:
        raise HTTPException(status_code=404)
    config = await self.get_config(owner_id, project_id)
    if not config:
        config = ProjectConfig(project_id=project_id)
        self.db.add(config)
    for key in ["total_words", "template_type", "target_audience"]:
        if key in data:
            setattr(config, key, data[key])
    await self.db.commit()
    return config
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/routes_project.py backend/app/project/service.py
git commit -m "feat: add GET/PUT /api/projects/{id}/config endpoint"
```

---

### Task 15: 服务端搜索

**Files:**
- Modify: `backend/app/api/routes_project.py` (已含搜索参数)
- Modify: `backend/app/project/service.py` (已实现搜索逻辑)

- [ ] **Step 1: 确认搜索功能已实现**

Task 8 中已实现 `search` 和 `status` 参数以及 SQL `ILIKE` 过滤。验证：
- `GET /api/projects?search=暗夜` → 返回标题含"暗夜"的项目
- `GET /api/projects?status=draft` → 返回状态为 draft 的项目
- `GET /api/projects?search=星&status=init` → 组合过滤

- [ ] **Step 2: 更新前端搜索调用**

在 `frontend/src/pages/home/ProjectGrid.tsx` 中，修改 `searchProjects` 函数将查询参数传给 API：

```typescript
const fetchProjects = async (search?: string) => {
  const params = new URLSearchParams({ page: "1", size: "50" })
  if (search) params.set("search", search)
  if (statusFilter) params.set("status", statusFilter)
  const res = await apiGet(`/api/projects?${params}`)
  setProjects(res.items || [])
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/home/ProjectGrid.tsx
git commit -m "feat: server-side project search with ILIKE filter"
```

---

## 执行顺序

```
Task 1 (JWT) ────────────────────┐
Task 2 (Entity check) ───────────┤ P0 安全（并行）
Task 3 (Register validate) ──────┘
         │
         ▼
Task 4 (Rhythm model+API) ───────┐
Task 5 (Rhythm edit UI) ─────────┤
Task 6 (Theme CRUD) ─────────────┤ P1 功能（部分可并行）
Task 7 (Layout button) ──────────┤
Task 8 (Project stats) ──────────┘
         │
         ▼
Task 9 (Utils) ──────────────────┐
Task 10 (Dead code) ─────────────┤ P2 代码质量（可并行）
Task 11 (Version snapshot) ──────┤
Task 12 (Semaphore) ─────────────┤
Task 13 (create_all) ────────────┘
         │
         ▼
Task 14 (Config API) ────────────┐ P3 API（并行）
Task 15 (Search) ────────────────┘
```
