# StoryCAD Create-from-Material AI System — Design Spec

**Status**: approved
**Date**: 2026-07-07
**LLM Provider**: DeepSeek (`deepseek-chat`)
**Framework**: LangGraph (stateful multi-node workflow)

---

## 1. Overview

Replace the disabled "从素材创建" ghost button in `CreateProjectDialog` with a working AI-powered project scaffolding system. The user pastes raw material (story idea, outline, character notes), and the AI generates a complete project framework via a LangGraph state machine.

## 2. LangGraph Workflow

### Node Pipeline

```
START → analyze_material → plan_structure → generate_scenes (parallel via Send) → design_characters → build_settings → validate → END
```

### State Schema

```python
class MaterialState(TypedDict):
    material: str                      # user input
    # analyze_material output
    genre: str
    tone: str
    characters_raw: list[dict]
    plot_summary: str
    world_elements: str
    # plan_structure output
    acts: list[ActDef]                 # [{name, order, chapters: [{title, goal}]}]
    estimated_words: int               # e.g. 80000
    # generate_scenes output (reducer: append)
    scenes: list[SceneDef]             # [{chapter_idx, title, pov, setting, time, summary}]
    # design_characters output
    characters: list[CharDef]          # [{name, role, personality, appearance, background, motivation}]
    relations: list[RelationDef]       # [{char_idx, target_idx, type, description}]
    # build_settings output
    global_settings: str
    # final
    project_title: str
    errors: list[str]
```

### Node Descriptions

| Node | LLM | Input | Output |
|------|-----|-------|--------|
| `analyze_material` | ✅ | `material` | genre, tone, characters_raw, plot_summary, world_elements |
| `plan_structure` | ✅ | genre, tone, plot_summary, world_elements | acts[] with nested chapters |
| `generate_scenes` | ✅ | chapter goal, characters_raw, world_elements | scene outlines (parallel per chapter via Send API) |
| `design_characters` | ✅ | characters_raw, plot_summary, tone | characters[] + relations[] |
| `build_settings` | ✅ | world_elements, plot_summary, genre | global_settings string |
| `validate` | ❌ | all outputs | validated/trimmed state, errors[] |

## 3. API

**Endpoint**: `POST /api/projects/create-from-material`

Request:
```json
{
  "title": "未命名项目",
  "material": "一个退隐杀手收到养女被绑架的消息..."
}
```

Response: **Server-Sent Events (SSE)**, streaming progress:
```
data: {"step":"analyze","status":"running"}
data: {"step":"analyze","status":"done","preview":"类型：都市/动作\n基调：悬疑黑暗..."}
data: {"step":"plan_structure","status":"running"}
data: {"step":"plan_structure","status":"done","preview":"3幕12章结构..."}
data: {"step":"generate_scenes","status":"running","progress":"0/12"}
data: {"step":"generate_scenes","status":"running","progress":"3/12"}
...
data: {"step":"generate_scenes","status":"done","preview":"12章共28个场景"}
data: {"step":"design_characters","status":"running"}
data: {"step":"design_characters","status":"done","preview":"5个角色已创建"}
data: {"step":"build_settings","status":"running"}
data: {"step":"build_settings","status":"done"}
data: {"step":"validate","status":"done"}
data: {"step":"done","project_id":"abc-123"}
```

## 4. Prompt Templates

All stored as YAML under `agent/project_creator/prompts/`, consistent with existing format.

### 4.1 material_analyze.yaml
- Persona: 资深小说编辑，擅长从碎片素材中提取叙事要素
- Constraints: 输出 JSON，字段见 State 中的 analyze 段
- Temperature: 0.3 (deterministic analysis)

### 4.2 material_structure.yaml  
- Input: genre, tone, plot_summary, world_elements, total_words
- Output: acts[] with nested chapters, each chapter has title + goal
- Constraint: 3-5 幕, 每幕 2-5 章, 章目标具体可执行

### 4.3 material_scenes.yaml
- Input: chapter_title, chapter_goal, characters_raw, world_elements
- Output: 1-3 scene outlines per chapter (title, POV, setting, time, summary)
- Designed for Send API: one invocation per chapter, runs in parallel

### 4.4 material_characters.yaml
- Input: characters_raw, plot_summary, tone
- Output: named characters with full profiles + inter-character relations
- Constraint: 2-8 characters, each with distinct role

### 4.5 material_settings.yaml
- Input: world_elements, genre, plot_summary
- Output: 2-5 paragraphs of world-building notes (setting, rules, history, atmosphere)

## 5. File Structure

```
backend/app/agent/project_creator/
├── __init__.py
├── graph.py               # build_graph() → compiled StateGraph
├── state.py               # MaterialState TypedDict + Pydantic models
├── nodes/
│   ├── __init__.py
│   ├── analyze.py
│   ├── plan.py
│   ├── scenes.py           # uses Send API for parallelism
│   ├── characters.py
│   ├── settings.py
│   └── validate.py
└── prompts/
    ├── material_analyze.yaml
    ├── material_structure.yaml
    ├── material_scenes.yaml
    ├── material_characters.yaml
    └── material_settings.yaml

backend/app/api/
└── routes_ai.py            # ADD: POST /create-from-material endpoint

backend/requirements.txt    # ADD: langgraph>=0.2.0
```

## 6. Frontend Changes

**CreateProjectDialog.tsx**:
- Remove `disabled` and `即将推出` from "从素材创建" button
- Click opens material input mode:
  - Title input (pre-filled or auto-generated from material)
  - Large textarea for material (100-5000 chars)
  - "AI 分析与生成" button
- During generation: SSE progress bar with 7 steps, showing current step + preview text
- On completion: auto-navigate to `/projects/{id}`

**New**: `frontend/src/api/ai.ts` — add `createFromMaterial()` function using `EventSource` (SSE).

## 7. Write-to-DB Strategy

After LangGraph completes successfully, the API endpoint:
1. Calls `ProjectService.create_project()` to create the project row
2. Creates `ProjectConfig` with total_words from analysis
3. Batch-creates acts via `createEntity(project_id, 'acts', ...)`
4. Batch-creates chapters with act_id references
5. Batch-creates scenes with chapter_id references
6. Batch-creates characters with relations
7. Sets global_settings via project update
8. Returns `project_id` to frontend

All wrapped in a single DB transaction (commit on success, rollback on error).

## 8. Error Handling

- Each LLM node has retry (max 2) on parse failure
- `validate` node checks: act count ≤ 5, scene count per chapter ≤ 5, character count ≤ 10
- Validation failures → trimmed without re-running LLM
- If a critical node fails after retries → SSE emits error + partial results so far
- Rate limiting: 2 material creations per user per hour (to prevent abuse)
