# StoryCAD AI Writing Assistant — Design Spec

**Status**: approved
**Date**: 2026-07-07
**LLM Provider**: DeepSeek (`deepseek-chat`)
**API Key**: sk-8b751f27971a44a481fbc21679b9c992

---

## 1. Overview

A 3-feature AI writing assistant embedded in the editor's chapter detail panel:

1. **Generate Chapter Goal** — reason about where a chapter sits in the narrative and propose a goal
2. **Generate Scene Outlines** — given a chapter's goal, suggest scenes with POV, setting, summary
3. **Assisted Writing** — open-ended generation given full story context

The system is built as an extensible multi-agent framework so future AI capabilities (logic validation, arc analysis, pacing suggestions) can be added by writing new agents and prompts without changing the core infrastructure.

---

## 2. Architecture

```
┌──────────────────────────────────────────────┐
│                Frontend (React)               │
│  ┌────────────────────────────────────────┐  │
│  │  AiAssistModal                         │  │
│  │  mode: 'goal' | 'outline' | 'write'    │  │
│  │  projectId, chapterId, scenes[]        │  │
│  │  → user prompt → API → display result  │  │
│  └───────────────┬────────────────────────┘  │
│                  │ POST /api/projects/{id}/ai │
└──────────────────┼───────────────────────────┘
                   │
┌──────────────────┼───────────────────────────┐
│                  ▼             Backend        │
│  ┌────────────────────────────────────────┐  │
│  │  routes_ai.py                          │  │
│  │  POST /api/projects/{id}/ai/generate   │  │
│  └───────────────┬────────────────────────┘  │
│                  │                            │
│  ┌───────────────▼────────────────────────┐  │
│  │  AgentOrchestrator                     │  │
│  │  .generate(mode, context, user_prompt) │  │
│  │    → select agent                      │  │
│  │    → build context                     │  │
│  │    → execute agent.run()               │  │
│  │    → validate & return                 │  │
│  └──────┬──────────┬──────────┬───────────┘  │
│         │          │          │               │
│    ┌────▼───┐ ┌───▼────┐ ┌──▼──────┐        │
│    │GoalAgent│ │Outline │ │Writing  │        │
│    │        │ │Agent   │ │Agent    │        │
│    └────┬───┘ └───┬────┘ └──┬──────┘        │
│         │         │         │                │
│    ┌────┴─────────┴─────────┴────┐           │
│    │     Shared Infrastructure    │           │
│    │  ContextBuilder  PromptReg.  │           │
│    │  SchemaValidator LLMClient   │           │
│    └─────────────────────────────┘           │
└──────────────────────────────────────────────┘
```

---

## 3. Backend Components

### 3.1 File Structure

```
backend/app/agent/
├── __init__.py
├── orchestrator.py
├── client.py
├── context.py
├── schema.py
├── agents/
│   ├── __init__.py
│   ├── base.py
│   ├── goal_agent.py
│   ├── outline_agent.py
│   └── writing_agent.py
├── prompts/
│   ├── persona.yaml
│   ├── goal.yaml
│   ├── outline.yaml
│   └── writing.yaml
└── __init__.py
```

### 3.2 LLM Client (`client.py`)

OpenAI-compatible HTTP client targeting DeepSeek:

```python
class LLMClient:
    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"  # V3, cost-effective
        self.reasoner_model = "deepseek-reasoner"  # R1, for later use

    async def chat(self, messages: list[dict], schema: dict | None = None) -> dict:
        """Single-turn with optional structured output"""
        ...

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str]:
        """Streaming mode for long generation"""
        ...
```

Add to `config.py`:
```python
deepseek_api_key: str = ""
```

### 3.3 Context Builder (`context.py`)

Selectively assembles project data into a context dict for the LLM. Strategy per agent:

| Data        | Goal | Outline | Writing |
|-------------|------|---------|---------|
| Project     | ✔    | ✔       | ✔       |
| Target Act  | ✔    | ✔       | ✔       |
| Chapters    | ✔±2  | ✔ target | ✔ all   |
| Scenes      | ✗    | ✗       | ✔ all   |
| Content     | ✗    | ✗       | ✔       |
| Characters  | ✔    | ✔       | ✔       |
| Relations   | ✗    | ✔       | ✔       |
| Themes      | ✔    | ✔       | ✔       |

The builder fetches from the StoryCADRepository using the same pattern as `get_editor_data()`.

### 3.4 Agent Base (`agents/base.py`)

```python
class BaseAgent:
    prompt_name: str  # references prompts/<name>.yaml
    output_schema: type[BaseModel]

    def build_messages(self, context: dict, user_prompt: str) -> list[dict]:
        """Load YAML prompt, fill slots with context, return messages"""
        ...

    async def run(self, client: LLMClient, context: dict, user_prompt: str) -> BaseModel:
        messages = self.build_messages(context, user_prompt)
        raw = await client.chat(messages, self.output_schema.model_json_schema())
        return self.output_schema.model_validate(raw)
```

### 3.5 Three Agents

**GoalAgent** — Generates a chapter goal with reasoning:

```python
class GoalOutput(BaseModel):
    goal: str          # The chapter goal in Chinese
    reasoning: str     # Why this goal — narrative reasoning

class GoalAgent(BaseAgent):
    prompt_name = "goal"
    output_schema = GoalOutput
```

**OutlineAgent** — Generates scene outlines:

```python
class SceneOutline(BaseModel):
    title: str
    pov_character: str
    setting: str
    scene_time: str
    summary: str

class OutlineOutput(BaseModel):
    planning: str              # Why this structure
    scenes: list[SceneOutline]

class OutlineAgent(BaseAgent):
    prompt_name = "outline"
    output_schema = OutlineOutput
```

**WritingAgent** — Open-ended assisted writing:

```python
class WritingOutput(BaseModel):
    content: str
    note: str | None

class WritingAgent(BaseAgent):
    prompt_name = "writing"
    output_schema = WritingOutput
```

### 3.6 Prompt Templates (YAML)

**`persona.yaml`** — Shared across all agents:
```yaml
system: |
  你是一位资深中文小说编辑与写作导师，专精于长篇小说结构设计和角色驱动叙事。
  你的指导原则：
  1. 故事以角色驱动，情节服务于角色成长
  2. 每次输出前先分析当前叙事位置和上下文
  3. 提供具体、可执行的建议，而非泛泛而谈
  4. 理解用户的写作风格，不强行改变
```

**`goal.yaml`**:
```yaml
system: |
  {persona}

  当前项目：《{project_title}》（{genre}）
  当前幕：{act_name}
  目标章节：{chapter_title}

  相邻章节：
  {adjacent_chapters}

  可用角色：
  {characters}

  主题：{themes}

  请分析这个章节在叙事弧中的位置，然后为它写一个具体、可执行的目标。
  输出格式：先推理（reasoning），再给出目标（goal）。
```

**`outline.yaml`**:
```yaml
system: |
  {persona}

  当前项目：《{project_title}》（目标{total_words}字）
  当前章节：{chapter_title}
  章节目标：{chapter_goal}

  可用角色：{characters}
  角色关系：{relations}
  主题：{themes}

  请为这一章规划具体场景。考虑：
  1. 场景数量应匹配目标字数
  2. 每个场景有明确的 POV、地点、时间和目的
  3. 场景之间应有情绪起伏和推进感
```

**`writing.yaml`**:
```yaml
system: |
  {persona}

  当前项目：《{project_title}》（{genre}）
  当前章节：{chapter_title}
  章节目标：{chapter_goal}

  所有场景内容：
  {all_scenes}

  角色：{characters}
  角色关系：{relations}
  主题：{themes}

  用户需求：{user_prompt}
  
  请根据上下文谨慎回应。
```

### 3.7 Orchestrator (`orchestrator.py`)

```python
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

    async def generate(self, project_id, chapter_id, mode, user_prompt) -> dict:
        agent = self.agents[mode]
        context = await self.context_builder.build(mode, project_id, chapter_id)
        result = await agent.run(self.client, context, user_prompt)
        return result.model_dump()
```

### 3.8 API Route (`routes_ai.py`)

```python
router = APIRouter(prefix="/api/projects/{project_id}", tags=["ai"])

@router.post("/ai/generate")
async def ai_generate(
    project_id: uuid.UUID,
    payload: AiGenerateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _check_project_owner(project_id, current_user, db)
    orchestrator = AgentOrchestrator(db)
    result = await orchestrator.generate(
        project_id,
        uuid.UUID(payload.chapter_id),
        payload.mode,   # "goal" | "outline" | "writing"
        payload.prompt,
    )
    return result
```

Register in `main.py`:
```python
from app.api.routes_ai import router as ai_router
app.include_router(ai_router)
```

---

## 4. Frontend Changes

### 4.1 New API Module (`frontend/src/api/ai.ts`)

```typescript
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

export interface SceneOutline {
  title: string
  pov_character: string
  setting: string
  scene_time: string
  summary: string
}

export interface OutlineResult {
  planning: string
  scenes: SceneOutline[]
}

export interface WritingResult {
  content: string
  note: string | null
}

export type AiResult = GoalResult | OutlineResult | WritingResult

export async function generateAI(
  projectId: string,
  request: AiGenerateRequest
): Promise<AiResult> {
  return apiPost<AiResult>(
    `/api/projects/${projectId}/ai/generate`,
    request
  )
}
```

### 4.2 New Component (`frontend/src/pages/editor/modals/AiAssistModal.tsx`)

Props:

| Prop | Type | Purpose |
|------|------|---------|
| `mode` | `'goal' \| 'outline' \| 'writing'` | Which agent to call |
| `projectId` | `string` | Project ID for API |
| `chapter` | `Chapter` | Current chapter with all scenes |
| `onClose` | `() => void` | Close modal |
| `onApplyGoal` | `(goal: string) => void` | Apply generated goal |
| `onApplyOutlines` | `(outlines: SceneOutline[]) => void` | Apply scene outlines |

UI Layout:
```
┌─────────────────────────────────┐
│ 🤖 AI 辅助写作           [✕]    │
│ mode-specific title              │
│ ─────────────────────────────── │
│                                 │
│ 上下文预览（可折叠）             │
│ ┌─────────────────────────────┐ │
│ │ 当前章节：xxx               │ │
│ │ 关联人物：4人               │ │
│ │ 关联主题：2个               │ │
│ └─────────────────────────────┘ │
│                                 │
│ 给 AI 的指令                    │
│ ┌─────────────────────────────┐ │
│ │ [textarea]                  │ │
│ └─────────────────────────────┘ │
│                                 │
│ [✕ 取消]  [✨ 生成中.../生成]   │
│                                 │
│ ─────────── 结果 ───────────── │
│ ┌─────────────────────────────┐ │
│ │ 生成的文本 / 大纲列表       │ │
│ │ [应用到章节]                │ │
│ └─────────────────────────────┘ │
└─────────────────────────────────┘
```

### 4.3 ChapterDetail Changes

- Remove the inline ghost AI modal (lines 246-276)
- The 3 AI buttons (lines 220-243) now each open `AiAssistModal` with the corresponding `mode`
- Pass `onApplyGoal` and `onApplyOutlines` as callbacks from the parent

---

## 5. Data Flow

```
User clicks "生成章节目标"
  → ChapterDetail sets showAIModal(true) with mode='goal'
  → AiAssistModal renders with mode='goal'
  → User types optional instruction, hits "生成"
  → POST /api/projects/{id}/ai/generate { chapter_id, mode:"goal", prompt }
  → routes_ai.py validates auth + project ownership
  → AgentOrchestrator.generate("goal", ...)
    → ContextBuilder.build("goal") fetches: project, target chapter, ±2 chapters, characters, themes
    → GoalAgent.build_messages() loads goal.yaml, fills {slots} with context
    → LLMClient.chat() sends to DeepSeek
    → GoalOutput validated via Pydantic
  → Response: { goal: "...", reasoning: "..." }
  → AiAssistModal displays result
  → User clicks "应用到章节"
  → AiAssistModal calls onApplyGoal(result.goal)
  → ChapterDetail updates chapter goal via existing update flow
```

---

## 6. Implementation Plan

### Phase 1: Agent Backend (6 parts)
1. `app/config.py` — add `deepseek_api_key` setting
2. `app/agent/client.py` — LLMClient (OpenAI-compatible HTTP, no extra deps)
3. `app/agent/schema.py` — Pydantic output models
4. `app/agent/prompts/*.yaml` — 4 prompt templates
5. `app/agent/context.py` — ContextBuilder
6. `app/agent/agents/` — BaseAgent + 3 agents
7. `app/agent/orchestrator.py` — AgentOrchestrator
8. `app/api/routes_ai.py` — API endpoint
9. `main.py` — register router

### Phase 2: Frontend
1. `src/api/ai.ts` — API client
2. `src/pages/editor/modals/AiAssistModal.tsx` — AI modal component
3. `src/pages/editor/views/plot/ChapterDetail.tsx` — wire buttons to modal

### Phase 3: Verify
1. Start containers, test `/api/projects/{id}/ai/generate`
2. Test full flow: register → create project → add chapter → AI generate goal → apply

---

## 7. Security & Rate Limiting

- AI endpoint requires JWT auth (same as all other endpoints)
- Add `deepseek_` rate limiting to prevent API key abuse
- User prompt sanitization: strip control characters, enforce max 2000 chars
- Response size cap: 16K tokens

---

## 8. Future Extensibility

Adding a new AI capability (e.g., "弧光分析") requires:
1. New prompt YAML in `prompts/`
2. New agent class in `agents/` (extends BaseAgent)
3. New output schema in `schema.py`
4. Register in `AgentOrchestrator.__init__`
5. New mode on the frontend

No changes to client, context builder, or orchestrator core needed.
