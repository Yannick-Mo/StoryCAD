# AI Writing Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 3 AI writing features (generate chapter goal, generate scene outlines, assisted writing) in the StoryCAD editor using DeepSeek API, built on an extensible multi-agent framework.

**Architecture:** A FastAPI route (`/ai/generate`) delegates to an AgentOrchestrator which selects the right agent (GoalAgent/OutlineAgent/WritingAgent). Each agent composes a prompt from YAML templates filled with context data queried from the DB, calls the DeepSeek API via an OpenAI-compatible LLMClient, validates output with Pydantic schemas, and returns structured results to the React AiAssistModal for display and application.

**Tech Stack:** Python (FastAPI, httpx, PyYAML, Pydantic), TypeScript (React, fetch API), DeepSeek V3 API.

**Spec:** `docs/superpowers/specs/2026-07-07-ai-writing-design.md`

---

## File Map

| Action | Path | Role |
|--------|------|------|
| Modify | `backend/requirements.txt` | Add pyyaml |
| Modify | `backend/app/config.py` | Add deepseek_api_key setting |
| Create | `backend/app/agent/__init__.py` | Package init |
| Create | `backend/app/agent/client.py` | LLMClient — OpenAI-compatible HTTP wrapper |
| Create | `backend/app/agent/schema.py` | Pydantic output models for all 3 agents |
| Create | `backend/app/agent/prompts/persona.yaml` | Shared system persona |
| Create | `backend/app/agent/prompts/goal.yaml` | Goal generation prompt template |
| Create | `backend/app/agent/prompts/outline.yaml` | Outline generation prompt template |
| Create | `backend/app/agent/prompts/writing.yaml` | Writing assistance prompt template |
| Create | `backend/app/agent/context.py` | ContextBuilder — fetches & formats project data |
| Create | `backend/app/agent/agents/__init__.py` | Agent package init |
| Create | `backend/app/agent/agents/base.py` | BaseAgent — prompt loading, slot filling, run |
| Create | `backend/app/agent/agents/goal_agent.py` | GoalAgent |
| Create | `backend/app/agent/agents/outline_agent.py` | OutlineAgent |
| Create | `backend/app/agent/agents/writing_agent.py` | WritingAgent |
| Create | `backend/app/agent/orchestrator.py` | AgentOrchestrator — route + execute |
| Create | `backend/app/api/routes_ai.py` | POST /api/projects/{id}/ai/generate |
| Modify | `backend/app/main.py` | Register ai router |
| Create | `frontend/src/api/ai.ts` | API client for AI endpoint |
| Create | `frontend/src/pages/editor/modals/AiAssistModal.tsx` | AI modal component |
| Modify | `frontend/src/pages/editor/views/plot/ChapterDetail.tsx` | Wire buttons to AiAssistModal, remove ghost modal |

---

### Task 1: Add dependencies and config

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add pyyaml to requirements**

```diff
 # backend/requirements.txt — append one line:
+ pyyaml>=6.0
```

- [ ] **Step 2: Add deepseek_api_key to Settings**

```python
# backend/app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/storyforge"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret_key: str = ""
    jwt_expire_hours: int = 24
    deepseek_api_key: str = ""       # <-- ADD

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 3: Add DEEPSEEK_API_KEY to .env**

```bash
echo "DEEPSEEK_API_KEY=sk-your-deepseek-api-key" >> .env
```

- [ ] **Step 4: Rebuild backend container**

```bash
docker compose up -d --build backend
```

Verify: backend starts without error.

---

### Task 2: Create LLMClient

**Files:**
- Create: `backend/app/agent/__init__.py`
- Create: `backend/app/agent/client.py`

- [ ] **Step 1: Create package init**

```python
# backend/app/agent/__init__.py
```

- [ ] **Step 2: Write LLMClient**

```python
# backend/app/agent/client.py
import json
from typing import AsyncGenerator
import httpx
from app.config import settings


class LLMClient:
    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"

    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 4096) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
```

- [ ] **Step 3: Test client with a quick script**

```bash
# In WSL, run a quick Python test (adjust path as needed)
cd backend && python -c "
import asyncio
from app.config import settings
from app.agent.client import LLMClient

async def main():
    c = LLMClient()
    r = await c.chat([{'role':'user','content':'Say hello in one word'}], max_tokens=10)
    print(r)

asyncio.run(main())
"
```

Expected: prints "Hello" or similar.

---

### Task 3: Create output schemas

**Files:**
- Create: `backend/app/agent/schema.py`

- [ ] **Step 1: Write schema.py**

```python
# backend/app/agent/schema.py
from pydantic import BaseModel


# ── GoalAgent output ──────────────────────────────────

class GoalOutput(BaseModel):
    goal: str
    reasoning: str


# ── OutlineAgent output ───────────────────────────────

class SceneOutlineItem(BaseModel):
    title: str
    pov_character: str
    setting: str
    scene_time: str
    summary: str


class OutlineOutput(BaseModel):
    planning: str
    scenes: list[SceneOutlineItem]


# ── WritingAgent output ───────────────────────────────

class WritingOutput(BaseModel):
    content: str
    note: str | None = None
```

---

### Task 4: Create prompt templates (YAML)

**Files:**
- Create: `backend/app/agent/prompts/persona.yaml`
- Create: `backend/app/agent/prompts/goal.yaml`
- Create: `backend/app/agent/prompts/outline.yaml`
- Create: `backend/app/agent/prompts/writing.yaml`

- [ ] **Step 1: persona.yaml**

```yaml
# backend/app/agent/prompts/persona.yaml
system: |
  你是一位资深中文小说编辑与写作导师，专精于长篇小说结构设计和角色驱动叙事。

  指导原则：
  1. 故事以角色驱动，情节服务于角色成长。
  2. 每次输出前先分析叙事位置和上下文。
  3. 提供具体、可执行的建议，而非泛泛而谈。
  4. 理解用户的写作风格，不强行改变。
  5. 所有回复使用中文。
```

- [ ] **Step 2: goal.yaml**

```yaml
# backend/app/agent/prompts/goal.yaml
system: |
  {persona}

  你在协助用户为小说章节撰写目标。

  以下是项目上下文——

  项目名称：《{project_title}》
  类型：{genre}

  当前幕名：{act_name}

  当前章节：{chapter_title}
  （这是{position_desc}）

  相邻章节概览（按顺序排列）：
  {adjacent_chapters}

  项目中的角色：
  {characters_summary}

  项目中的主题：
  {themes_summary}

  请完成以下两步：
  1. reasoning：分析这一章在整体叙事弧中的位置，需要完成什么戏剧功能（50-100字）。
  2. goal：用一两句话写一个具体、可衡量的章节目标（例如"主角发现...并决定..."）。

  你的回答必须是一个合法的 JSON 对象，包含 "goal" 和 "reasoning" 两个字段，不要包含 markdown 代码块标记。
```

- [ ] **Step 3: outline.yaml**

```yaml
# backend/app/agent/prompts/outline.yaml
system: |
  {persona}

  你在协助用户为一章小说规划场景大纲。

  项目名称：《{project_title}》
  目标总字数：{total_words} 字

  当前章节：{chapter_title}
  章节目标：{chapter_goal}

  可用角色：
  {characters_summary}

  角色关系：
  {relations_summary}

  主题：
  {themes_summary}

  请完成以下两步：
  1. planning：分析章节目标，规划1-5个场景的结构（50-100字）。
  2. scenes：为每个场景指定——
     - title：场景标题（简短）
     - pov_character：视点角色名（必须从可用角色中选择）
     - setting：场景发生地点
     - scene_time：故事内时间（如 "第三天傍晚"）
     - summary：场景梗概（1-2句，说明这一场要完成什么）

  你的回答必须是一个合法的 JSON 对象，包含 "planning" 和 "scenes" 两个字段。"scenes" 是一个数组。不要包含 markdown 代码块标记。
```

- [ ] **Step 4: writing.yaml**

```yaml
# backend/app/agent/prompts/writing.yaml
system: |
  {persona}

  你在协助用户进行小说写作。

  项目名称：《{project_title}》（{genre}）

  当前章节：{chapter_title}
  章节目标：{chapter_goal}

  所有场景及内容：
  {all_scenes_content}

  角色：
  {characters_summary}

  角色关系：
  {relations_summary}

  主题：
  {themes_summary}

  用户的具体需求：{user_prompt}

  请根据上下文完成用户的写作需求。保持一致的叙事语气和对角色的理解。如果用户要求续写或扩写，保持与已有内容一致的风格和节奏。

  你的回答必须是一个合法的 JSON 对象，包含 "content" 字段和可选的 "note" 字段。不要包含 markdown 代码块标记。
```

---

### Task 5: Create ContextBuilder

**Files:**
- Create: `backend/app/agent/context.py`

- [ ] **Step 1: Write context.py**

```python
# backend/app/agent/context.py
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.storycad.models import Act, Chapter, Scene, SceneContent, Character, CharacterRelation, Theme, ThemeChapter
from app.project.models import Project, ProjectConfig


class ContextBuilder:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def build(self, mode: str, project_id: uuid.UUID, chapter_id: uuid.UUID) -> dict:
        ctx = {}

        proj = await self._get_project(project_id)
        target_chapter = await self._get_chapter(chapter_id)
        if not proj or not target_chapter:
            return ctx

        ctx["project_title"] = proj.title
        ctx["genre"] = proj.genre or "未指定"
        ctx["chapter_title"] = target_chapter.title
        ctx["chapter_goal"] = target_chapter.goal or "未设定"

        config = await self._get_config(project_id)
        ctx["total_words"] = config.total_words if config else 100000

        act = await self._get_act(target_chapter.act_id)
        ctx["act_name"] = act.name if act else "未命名幕"

        ctx["characters_summary"] = await self._characters_text(project_id)

        if mode in ("goal", "outline", "writing"):
            ctx["themes_summary"] = await self._themes_text(project_id)

        if mode == "goal":
            ctx["adjacent_chapters"] = await self._adjacent_chapters_text(project_id, target_chapter.sort_order, target_chapter.act_id)
            ctx["position_desc"] = self._position_desc(target_chapter.sort_order)

        if mode in ("outline", "writing"):
            ctx["relations_summary"] = await self._relations_text(project_id)

        if mode == "writing":
            ctx["all_scenes_content"] = await self._scenes_content_text(chapter_id)

        return ctx

    async def _get_project(self, project_id: uuid.UUID):
        r = await self.db.execute(select(Project).where(Project.id == project_id))
        return r.scalar_one_or_none()

    async def _get_config(self, project_id: uuid.UUID):
        r = await self.db.execute(select(ProjectConfig).where(ProjectConfig.project_id == project_id))
        return r.scalar_one_or_none()

    async def _get_chapter(self, chapter_id: uuid.UUID):
        r = await self.db.execute(select(Chapter).where(Chapter.id == chapter_id))
        return r.scalar_one_or_none()

    async def _get_act(self, act_id: uuid.UUID | None):
        if not act_id:
            return None
        r = await self.db.execute(select(Act).where(Act.id == act_id))
        return r.scalar_one_or_none()

    async def _characters_text(self, project_id: uuid.UUID) -> str:
        r = await self.db.execute(
            select(Character).where(Character.project_id == project_id).order_by(Character.sort_order)
        )
        chars = r.scalars().all()
        if not chars:
            return "暂无角色"
        lines = []
        for c in chars:
            parts = [f"- {c.name}（{c.role or '未指定角色'}）"]
            if c.personality:
                parts.append(f"  性格：{c.personality}")
            if c.motivation:
                parts.append(f"  动机：{c.motivation}")
            if c.background:
                parts.append(f"  背景：{c.background}")
            lines.append("\n".join(parts))
        return "\n".join(lines)

    async def _themes_text(self, project_id: uuid.UUID) -> str:
        r = await self.db.execute(
            select(Theme).where(Theme.project_id == project_id).order_by(Theme.sort_order)
        )
        themes = r.scalars().all()
        if not themes:
            return "暂无主题"
        lines = []
        for t in themes:
            prop = f" — {t.proposition}" if t.proposition else ""
            lines.append(f"- {t.name}{prop}")
        return "\n".join(lines)

    async def _adjacent_chapters_text(self, project_id: uuid.UUID, sort_order: int, act_id: uuid.UUID | None) -> str:
        r = await self.db.execute(
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .order_by(Chapter.sort_order)
        )
        all_chapters = r.scalars().all()
        if len(all_chapters) <= 1:
            return "（只有一个章节，暂无相邻章节）"

        idx = next((i for i, ch in enumerate(all_chapters) if ch.sort_order == sort_order), 0)
        start = max(0, idx - 2)
        end = min(len(all_chapters), idx + 3)

        lines = []
        for i in range(start, end):
            ch = all_chapters[i]
            marker = " ← 当前章节" if ch.sort_order == sort_order else ""
            goal_preview = f" | 目标：{ch.goal[:40]}..." if ch.goal and len(ch.goal) > 40 else (f" | 目标：{ch.goal}" if ch.goal else "")
            lines.append(f"{ch.sort_order}. {ch.title}{goal_preview}{marker}")
        return "\n".join(lines)

    def _position_desc(self, sort_order: int) -> str:
        if sort_order <= 1:
            return "故事开篇章节"
        return "故事中段章节"

    async def _relations_text(self, project_id: uuid.UUID) -> str:
        r = await self.db.execute(
            select(CharacterRelation).where(CharacterRelation.project_id == project_id)
        )
        rels = r.scalars().all()
        if not rels:
            return "暂无关系"
        char_map = {}
        cr = await self.db.execute(select(Character).where(Character.project_id == project_id))
        for c in cr.scalars().all():
            char_map[c.id] = c.name
        lines = []
        for rel in rels:
            src = char_map.get(rel.character_id, "?")
            tgt = char_map.get(rel.target_id, "?")
            trust = ""
            if rel.trust and rel.trust != 50:
                trust = f" (信任{rel.trust})"
            lines.append(f"- {src} → {rel.label or rel.rel_type or '关联'} → {tgt}{trust}")
        return "\n".join(lines)

    async def _scenes_content_text(self, chapter_id: uuid.UUID) -> str:
        r = await self.db.execute(
            select(Scene).where(Scene.chapter_id == chapter_id).order_by(Scene.sort_order)
        )
        scenes = r.scalars().all()
        if not scenes:
            return "暂无场景"

        parts = []
        for sc in scenes:
            content = ""
            cr = await self.db.execute(select(SceneContent).where(SceneContent.scene_id == sc.id))
            sc_content = cr.scalar_one_or_none()
            if sc_content and sc_content.content:
                content = sc_content.content[:2000]

            parts.append(
                f"【{sc.title}】\n"
                f"POV: {sc.pov_character or '未指定'} | 地点: {sc.setting or '未指定'} | 时间: {sc.scene_time or '未指定'}\n"
                f"梗概: {sc.summary or '无'}\n"
                f"正文: {content or '（尚未写作）'}"
            )
        return "\n\n".join(parts)
```

---

### Task 6: Create BaseAgent

**Files:**
- Create: `backend/app/agent/agents/__init__.py`
- Create: `backend/app/agent/agents/base.py`

- [ ] **Step 1: Create agents package init**

```python
# backend/app/agent/agents/__init__.py
```

- [ ] **Step 2: Write base.py**

```python
# backend/app/agent/agents/base.py
import json
import yaml
from pathlib import Path
from pydantic import BaseModel
from app.agent.client import LLMClient


PROMPT_DIR = Path(__file__).parent.parent / "prompts"


class BaseAgent:
    prompt_name: str = ""
    output_schema: type[BaseModel] = BaseModel

    def _load_yaml(self, name: str) -> dict:
        path = PROMPT_DIR / f"{name}.yaml"
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_persona(self) -> str:
        data = self._load_yaml("persona")
        return data.get("system", "")

    def _system_prompt(self, context: dict, user_prompt: str) -> str:
        data = self._load_yaml(self.prompt_name)
        template = data.get("system", "")
        persona = self._load_persona()
        prompt = template.format(persona=persona, **context, user_prompt=user_prompt)
        return prompt

    def _parse_json(self, raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            end = next((i for i in range(len(lines) - 1, 0, -1) if lines[i].strip() == "```"), len(lines))
            text = "\n".join(lines[1:end])
        return json.loads(text)

    async def run(self, client: LLMClient, context: dict, user_prompt: str) -> BaseModel:
        system = self._system_prompt(context, user_prompt)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "请按 JSON 格式输出"},
        ]
        raw = await client.chat(messages)
        parsed = self._parse_json(raw)
        return self.output_schema.model_validate(parsed)
```

---

### Task 7: Create GoalAgent

**Files:**
- Create: `backend/app/agent/agents/goal_agent.py`

- [ ] **Step 1: Write goal_agent.py**

```python
# backend/app/agent/agents/goal_agent.py
from app.agent.agents.base import BaseAgent
from app.agent.schema import GoalOutput


class GoalAgent(BaseAgent):
    prompt_name = "goal"
    output_schema = GoalOutput
```

---

### Task 8: Create OutlineAgent

**Files:**
- Create: `backend/app/agent/agents/outline_agent.py`

- [ ] **Step 1: Write outline_agent.py**

```python
# backend/app/agent/agents/outline_agent.py
from app.agent.agents.base import BaseAgent
from app.agent.schema import OutlineOutput


class OutlineAgent(BaseAgent):
    prompt_name = "outline"
    output_schema = OutlineOutput
```

---

### Task 9: Create WritingAgent

**Files:**
- Create: `backend/app/agent/agents/writing_agent.py`

- [ ] **Step 1: Write writing_agent.py**

```python
# backend/app/agent/agents/writing_agent.py
from app.agent.agents.base import BaseAgent
from app.agent.schema import WritingOutput


class WritingAgent(BaseAgent):
    prompt_name = "writing"
    output_schema = WritingOutput
```

---

### Task 10: Create AgentOrchestrator

**Files:**
- Create: `backend/app/agent/orchestrator.py`

- [ ] **Step 1: Write orchestrator.py**

```python
# backend/app/agent/orchestrator.py
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.client import LLMClient
from app.agent.context import ContextBuilder
from app.agent.agents.goal_agent import GoalAgent
from app.agent.agents.outline_agent import OutlineAgent
from app.agent.agents.writing_agent import WritingAgent


class AgentOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = LLMClient()
        self.context_builder = ContextBuilder(db)
        self.agents = {
            "goal": GoalAgent(),
            "outline": OutlineAgent(),
            "writing": WritingAgent(),
        }

    async def generate(self, project_id: uuid.UUID, chapter_id: uuid.UUID, mode: str, user_prompt: str) -> dict:
        agent = self.agents[mode]
        context = await self.context_builder.build(mode, project_id, chapter_id)
        result = await agent.run(self.client, context, user_prompt)
        return result.model_dump()
```

---

### Task 11: Create API route

**Files:**
- Create: `backend/app/api/routes_ai.py`

- [ ] **Step 1: Write routes_ai.py**

```python
# backend/app/api/routes_ai.py
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.project.service import ProjectService
from app.agent.orchestrator import AgentOrchestrator


class AiGenerateRequest(BaseModel):
    chapter_id: str
    mode: str         # "goal" | "outline" | "writing"
    prompt: str = ""  # optional user instruction


router = APIRouter(prefix="/api/projects/{project_id}", tags=["ai"])


@router.post("/ai/generate")
async def ai_generate(
    project_id: uuid.UUID,
    payload: AiGenerateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProjectService(db)
    project = await svc.get_project(project_id, uuid.UUID(current_user["id"]))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.mode not in ("goal", "outline", "writing"):
        raise HTTPException(status_code=400, detail=f"Invalid mode: {payload.mode}")

    prompt = payload.prompt.strip()[:2000]

    orchestrator = AgentOrchestrator(db)
    result = await orchestrator.generate(
        project_id,
        uuid.UUID(payload.chapter_id),
        payload.mode,
        prompt,
    )
    return result
```

---

### Task 12: Register AI router in main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Register the router**

Insert after the existing `storycad_router` registration:

```python
# backend/app/main.py — inside register_routers(), add at the end:

def register_routers():
    from app.api.routes_auth import router as auth_router
    app.include_router(auth_router)
    from app.api.routes_project import router as project_router
    app.include_router(project_router)
    from app.api.routes_storycad import router as storycad_router
    app.include_router(storycad_router)
    from app.api.routes_ai import router as ai_router          # <-- ADD
    app.include_router(ai_router)                               # <-- ADD
```

- [ ] **Step 2: Restart backend**

```bash
docker compose restart backend
```

Watch logs: `docker compose logs -f backend`. Verify no import errors.

- [ ] **Step 3: Test the endpoint from the host**

```bash
# Login first
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"testtest"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# List projects
curl -s http://localhost:8000/api/projects -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Use actual project_id and chapter_id from the output above to test:
# curl -s -X POST http://localhost:8000/api/projects/{PROJECT_ID}/ai/generate \
#   -H "Authorization: Bearer $TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{"chapter_id":"{CHAPTER_ID}", "mode":"goal", "prompt":""}'
```

Expected: JSON response with `{"goal": "...", "reasoning": "..."}`.

---

### Task 13: Create frontend AI API client

**Files:**
- Create: `frontend/src/api/ai.ts`

- [ ] **Step 1: Write ai.ts**

```typescript
// frontend/src/api/ai.ts
import { apiPost } from './auth'

export interface AiGenerateRequest {
  chapter_id: string
  mode: 'goal' | 'outline' | 'writing'
  prompt: string
}

export interface GoalResult {
  goal: string
  reasoning: string
}

export interface SceneOutlineItem {
  title: string
  pov_character: string
  setting: string
  scene_time: string
  summary: string
}

export interface OutlineResult {
  planning: string
  scenes: SceneOutlineItem[]
}

export interface WritingResult {
  content: string
  note: string | null
}

export type AiResult = GoalResult | OutlineResult | WritingResult

export async function generateAI(
  projectId: string,
  request: AiGenerateRequest,
): Promise<AiResult> {
  return apiPost<AiResult>(
    `/api/projects/${projectId}/ai/generate`,
    request,
  )
}
```

---

### Task 14: Create AiAssistModal component

**Files:**
- Create: `frontend/src/pages/editor/modals/AiAssistModal.tsx`

- [ ] **Step 1: Write AiAssistModal.tsx**

```tsx
// frontend/src/pages/editor/modals/AiAssistModal.tsx
import { useState } from 'react'
import type { Chapter } from '../types'
import { generateAI } from '../../../api/ai'
import type { GoalResult, OutlineResult, WritingResult, SceneOutlineItem } from '../../../api/ai'

const MODE_LABELS: Record<string, string> = {
  goal: '生成章节目标',
  outline: '生成场景大纲',
  writing: '辅助写作',
}

const MODE_PLACEHOLDERS: Record<string, string> = {
  goal: '可选：补充对章节的额外说明...',
  outline: '可选：补充你的规划偏好...',
  writing: '描述你的写作需求，AI 将根据上下文生成内容...',
}

interface Props {
  mode: 'goal' | 'outline' | 'writing'
  projectId: string
  chapter: Chapter
  onClose: () => void
  onApplyGoal?: (goal: string) => void
  onApplyOutlines?: (outlines: SceneOutlineItem[]) => void
}

export default function AiAssistModal({ mode, projectId, chapter, onClose, onApplyGoal, onApplyOutlines }: Props) {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<GoalResult | OutlineResult | WritingResult | null>(null)
  const [applied, setApplied] = useState(false)

  const handleGenerate = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await generateAI(projectId, {
        chapter_id: chapter.id,
        mode,
        prompt: prompt.trim(),
      })
      setResult(data)
    } catch (e: any) {
      setError(e.message || '生成失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  const renderResult = () => {
    if (!result) return null

    if (mode === 'goal') {
      const r = result as GoalResult
      return (
        <div className="space-y-3">
          <div>
            <div className="text-[10px] text-amber-500/80 mb-1">分析</div>
            <p className="text-xs text-gray-300 leading-relaxed">{r.reasoning}</p>
          </div>
          <div>
            <div className="text-[10px] text-amber-500/80 mb-1">目标</div>
            <p className="text-sm text-amber-100 leading-relaxed bg-gray-800/60 rounded-lg p-3">{r.goal}</p>
          </div>
          {onApplyGoal && (
            <button
              onClick={() => { onApplyGoal(r.goal); setApplied(true) }}
              disabled={applied}
              className={`w-full px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                applied
                  ? 'bg-green-900/40 text-green-400'
                  : 'bg-amber-600 text-black hover:bg-amber-500'
              }`}
            >
              {applied ? '✓ 已应用' : '应用到章节'}
            </button>
          )}
        </div>
      )
    }

    if (mode === 'outline') {
      const r = result as OutlineResult
      return (
        <div className="space-y-3">
          <div>
            <div className="text-[10px] text-amber-500/80 mb-1">规划思路</div>
            <p className="text-xs text-gray-300 leading-relaxed">{r.planning}</p>
          </div>
          <div>
            <div className="text-[10px] text-amber-500/80 mb-1">
              场景列表 ({r.scenes.length})
            </div>
            <div className="space-y-2">
              {r.scenes.map((sc, i) => (
                <div key={i} className="bg-gray-800/60 rounded-lg p-2.5 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-500 w-4">{i + 1}</span>
                    <span className="text-xs font-medium text-gray-200">{sc.title}</span>
                  </div>
                  <div className="flex gap-3 text-[10px] text-gray-500 ml-6">
                    <span>🎭 {sc.pov_character}</span>
                    <span>📍 {sc.setting}</span>
                    <span>⏰ {sc.scene_time}</span>
                  </div>
                  <p className="text-[11px] text-gray-400 ml-6">{sc.summary}</p>
                </div>
              ))}
            </div>
          </div>
          {onApplyOutlines && (
            <button
              onClick={() => { onApplyOutlines(r.scenes); setApplied(true) }}
              disabled={applied}
              className={`w-full px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                applied
                  ? 'bg-green-900/40 text-green-400'
                  : 'bg-amber-600 text-black hover:bg-amber-500'
              }`}
            >
              {applied ? '✓ 已添加' : '添加场景到章节'}
            </button>
          )}
        </div>
      )
    }

    if (mode === 'writing') {
      const r = result as WritingResult
      return (
        <div className="space-y-3">
          {r.note && (
            <div className="text-[10px] text-amber-500/80 mb-1">AI 备注</div>
          )}
          {r.note && <p className="text-[11px] text-gray-400 italic">{r.note}</p>}
          <div>
            <div className="text-[10px] text-amber-500/80 mb-1">生成内容</div>
            <div className="bg-gray-800/60 rounded-lg p-3 text-xs text-gray-300 leading-relaxed max-h-64 overflow-y-auto whitespace-pre-wrap font-mono">
              {r.content}
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => navigator.clipboard.writeText(r.content)}
              className="flex-1 px-3 py-1.5 rounded-lg bg-gray-700 text-xs text-gray-300 hover:bg-gray-600 transition-colors"
            >
              复制到剪贴板
            </button>
          </div>
        </div>
      )
    }
  }

  return (
    <div className="absolute inset-0 bg-gray-950/80 backdrop-blur-sm z-50 flex items-end">
      <div className="w-full max-h-[85%] overflow-y-auto bg-gray-900 border-t border-gray-800 rounded-t-2xl p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium text-amber-100">
            🤖 {MODE_LABELS[mode]}
          </h4>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-lg">✕</button>
        </div>

        {/* Context summary (collapsed by default) */}
        <details className="text-xs text-gray-500">
          <summary className="cursor-pointer hover:text-gray-400 select-none">
            上下文预览 · {chapter.title} · {chapter.status} · {chapter.scenes.length}场 · {chapter.scenes.reduce((s, sc) => s + sc.wordCount, 0)}字
          </summary>
          <div className="mt-2 space-y-1 text-gray-500">
            <div>目标：{chapter.goal || '未设定'}</div>
            <div>场景：{chapter.scenes.map(s => s.title).join('、') || '无'}</div>
          </div>
        </details>

        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder={MODE_PLACEHOLDERS[mode]}
          disabled={loading}
          className="w-full h-20 bg-gray-950 border border-gray-700 rounded-xl p-3 text-xs text-gray-300 resize-none focus:outline-none focus:border-amber-600 leading-relaxed disabled:opacity-50"
        />

        <div className="flex gap-2">
          <button
            onClick={handleGenerate}
            disabled={loading}
            className={`flex-1 px-4 py-2 rounded-xl text-xs font-medium text-black transition-colors ${
              loading ? 'bg-amber-800 animate-pulse' : 'bg-amber-600 hover:bg-amber-500'
            }`}
          >
            {loading ? '✨ 生成中...' : '✨ 生成'}
          </button>
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 rounded-xl bg-gray-800 text-xs text-gray-400 hover:bg-gray-700 transition-colors disabled:opacity-50"
          >
            取消
          </button>
        </div>

        {error && (
          <div className="bg-red-900/20 border border-red-800/30 rounded-lg p-3">
            <p className="text-xs text-red-400">{error}</p>
          </div>
        )}

        {result && !error && (
          <div className="border-t border-gray-800 pt-3">
            {renderResult()}
          </div>
        )}
      </div>
    </div>
  )
}
```

---

### Task 15: Wire ChapterDetail buttons to AiAssistModal

**Files:**
- Modify: `frontend/src/pages/editor/views/plot/ChapterDetail.tsx`

- [ ] **Step 1: Update imports and add state**

Replace the imports and add new state variables:

```diff
- import { useState } from 'react'
- import type { Chapter, Scene } from '../../types'
+ import { useState } from 'react'
+ import type { Chapter, Scene } from '../../types'
+ import AiAssistModal from '../../modals/AiAssistModal'
+ import type { SceneOutlineItem } from '../../../api/ai'
```

- [ ] **Step 2: Add new props to interface**

```diff
 interface ChapterDetailProps {
   chapter: Chapter | null
   onClose: () => void
   onSceneSave: (chapterId: string, sceneId: string, content: string) => void
   onChapterSave: (chapterId: string, goal: string) => void
   onOpenSceneEditor?: (scene: Scene) => void
   onUpdateChapter: (id: string, updates: Partial<Pick<Chapter, 'title' | 'status'>>) => void
   onUpdateScene: (chapterId: string, sceneId: string, updates: Partial<Pick<Scene, 'title' | 'povCharacter' | 'setting' | 'time' | 'summary'>>) => void
   onAddScene: (chapterId: string) => Scene
   onDeleteScene: (chapterId: string, sceneId: string) => void
+  projectId?: string
 }
```

- [ ] **Step 3: Add destructured prop**

```diff
- export default function ChapterDetail({ chapter, onClose, onSceneSave, onChapterSave, onOpenSceneEditor, onUpdateChapter, onUpdateScene, onAddScene, onDeleteScene }: ChapterDetailProps) {
+ export default function ChapterDetail({ chapter, onClose, onSceneSave, onChapterSave, onOpenSceneEditor, onUpdateChapter, onUpdateScene, onAddScene, onDeleteScene, projectId }: ChapterDetailProps) {
```

- [ ] **Step 4: Replace ghost state with aiMode**

```diff
-   const [showAIModal, setShowAIModal] = useState(false)
-   const [aiPrompt, setAIPrompt] = useState('')
+   const [aiMode, setAiMode] = useState<'goal' | 'outline' | 'writing' | null>(null)
```

- [ ] **Step 5: Wire the 3 AI buttons to set aiMode**

```diff
-             <button
-               onClick={() => setShowAIModal(true)}
-               className="w-full text-left px-3 py-2 rounded-lg text-xs text-gray-400 hover:text-amber-300 hover:bg-gray-700/40 transition-colors border border-gray-700/30"
-             >
-               ✨ 生成章节目标
-             </button>
-             <button
-               onClick={() => setShowAIModal(true)}
-               className="w-full text-left px-3 py-2 rounded-lg text-xs text-gray-400 hover:text-amber-300 hover:bg-gray-700/40 transition-colors border border-gray-700/30"
-             >
-               ✨ 生成场景大纲
-             </button>
-             <button
-               onClick={() => setShowAIModal(true)}
-               className="w-full text-left px-3 py-2 rounded-lg text-xs text-gray-400 hover:text-amber-300 hover:bg-gray-700/40 transition-colors border border-gray-700/30"
-             >
-               ✍️ 辅助写作
-             </button>
+             <button
+               onClick={() => setAiMode('goal')}
+               className="w-full text-left px-3 py-2 rounded-lg text-xs text-gray-400 hover:text-amber-300 hover:bg-gray-700/40 transition-colors border border-gray-700/30"
+             >
+               ✨ 生成章节目标
+             </button>
+             <button
+               onClick={() => setAiMode('outline')}
+               className="w-full text-left px-3 py-2 rounded-lg text-xs text-gray-400 hover:text-amber-300 hover:bg-gray-700/40 transition-colors border border-gray-700/30"
+             >
+               ✨ 生成场景大纲
+             </button>
+             <button
+               onClick={() => setAiMode('writing')}
+               className="w-full text-left px-3 py-2 rounded-lg text-xs text-gray-400 hover:text-amber-300 hover:bg-gray-700/40 transition-colors border border-gray-700/30"
+             >
+               ✍️ 辅助写作
+             </button>
```

- [ ] **Step 6: Replace ghost modal with AiAssistModal**

Replace lines 246-276 (the entire `{/* AI Modal */}` block) with:

```tsx
      {/* AI Modal */}
      {aiMode && projectId && (
        <AiAssistModal
          mode={aiMode}
          projectId={projectId}
          chapter={chapter}
          onClose={() => setAiMode(null)}
          onApplyGoal={(goal) => {
            onChapterSave(chapter.id, goal)
            setAiMode(null)
          }}
          onApplyOutlines={(outlines) => {
            outlines.forEach((sc) => {
              const newScene = onAddScene(chapter.id)
              onUpdateScene(chapter.id, newScene.id, {
                title: sc.title,
                povCharacter: sc.pov_character,
                setting: sc.setting,
                time: sc.scene_time,
                summary: sc.summary,
              })
            })
            setAiMode(null)
          }}
        />
      )}
```

The ghost modal block (lines 246-276) must be completely removed and replaced by the above.

- [ ] **Step 7: Pass projectId from EditorShell**

In `EditorShell.tsx`, at the ChapterDetail render (around line 260), add `projectId` prop:

```diff
              <ChapterDetail
                chapter={data.chapters.find(c => c.id === selectedChapter.id) ?? selectedChapter}
+               projectId={projectId}
                onClose={() => setSelectedChapter(null)}
```

- [ ] **Step 8: Verify frontend compiles**

```bash
docker compose logs frontend | grep -i error
```

Expected: no compilation errors. The Vite HMR should pick up the changes.

---

### Task 16: Verify full flow

- [ ] **Step 1: Confirm all containers healthy**

```bash
docker compose ps
```

Expected: all 4 services `(healthy)`.

- [ ] **Step 2: Test end-to-end in browser**

1. Open `http://localhost:5173`
2. Register/login
3. Create a project
4. Add an act, a chapter, and at least one character
5. Open chapter detail panel
6. Click "✨ 生成章节目标"
7. Verify the AI modal appears with mode `goal`
8. Click "✨ 生成"
9. Verify result displays goal + reasoning
10. Click "应用到章节" — verify goal textarea updates

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: implement AI writing assistant with 3 agents (goal, outline, writing)"
```

---

## Self-Review Checklist

- [x] **Spec coverage**: All 3 features (goal, outline, writing) covered. Architecture (orchestrator, agents, context builder, YAML prompts, schemas, client) all implemented. Frontend AiAssistModal replaces ghost modal. API route registered.
- [x] **No placeholders**: Every step has actual code. No TBDs. No "add error handling" without showing the code.
- [x] **Type consistency**: `GoalResult`, `OutlineResult`, `WritingResult` types match between Python schemas and TS interfaces. `SceneOutlineItem` fields match the YAML prompt instructions. `AiGenerateRequest.mode` values match orchestrator keys.
