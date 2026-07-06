# Create-from-Material AI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the disabled "从素材创建" button with a LangGraph-powered AI system that analyzes user material and generates a complete project framework (acts, chapters, scenes, characters, global settings) in ~7 pipeline steps with SSE streaming.

**Architecture:** LangGraph `StateGraph` with 7 nodes: analyze → plan → fan-out generate_scenes (Send API per chapter) → design_characters → build_settings → validate. A new SSE endpoint streams progress. On completion, entities are batch-written to DB via existing `createEntity`.

**Tech Stack:** Python (FastAPI, LangGraph, httpx, PyYAML, Pydantic), TypeScript (React, EventSource SSE). DeepSeek V3 for all LLM calls.

**Spec:** `docs/superpowers/specs/2026-07-07-create-from-material-design.md`

---

## File Map

| Action | Path | Role |
|--------|------|------|
| Modify | `backend/requirements.txt` | Add langgraph |
| Modify | `backend/app/config.py` | No changes needed (deepseek_api_key already present) |
| Create | `backend/app/agent/project_creator/__init__.py` | Package init |
| Create | `backend/app/agent/project_creator/state.py` | MaterialState TypedDict + Pydantic sub-models |
| Create | `backend/app/agent/project_creator/graph.py` | `build_graph()` → compiled StateGraph |
| Create | `backend/app/agent/project_creator/nodes/__init__.py` | Nodes package |
| Create | `backend/app/agent/project_creator/nodes/analyze.py` | analyze_material node |
| Create | `backend/app/agent/project_creator/nodes/plan.py` | plan_structure node |
| Create | `backend/app/agent/project_creator/nodes/scenes.py` | generate_scene_chapter node (used by Send) |
| Create | `backend/app/agent/project_creator/nodes/characters.py` | design_characters node |
| Create | `backend/app/agent/project_creator/nodes/settings.py` | build_settings node |
| Create | `backend/app/agent/project_creator/nodes/validate.py` | validate node |
| Create | `backend/app/agent/project_creator/prompts/material_analyze.yaml` | Analyze prompt |
| Create | `backend/app/agent/project_creator/prompts/material_structure.yaml` | Structure prompt |
| Create | `backend/app/agent/project_creator/prompts/material_scenes.yaml` | Scene generation prompt |
| Create | `backend/app/agent/project_creator/prompts/material_characters.yaml` | Character design prompt |
| Create | `backend/app/agent/project_creator/prompts/material_settings.yaml` | Settings prompt |
| Modify | `backend/app/api/routes_ai.py` | Add SSE endpoint + write-to-DB |
| Modify | `frontend/src/api/ai.ts` | Add createFromMaterial() with EventSource |
| Modify | `frontend/src/pages/home/CreateProjectDialog.tsx` | Wire "从素材创建" button to new flow |

---

### Task 1: Install langgraph + create package structure

- [ ] **Step 1: Add langgraph to requirements**

Append to `backend/requirements.txt`:
```
langgraph>=0.2.0
langgraph-checkpoint>=2.0.0
```

- [ ] **Step 2: Install in running container**

```bash
docker exec storycad-backend-1 pip install langgraph langgraph-checkpoint
```

- [ ] **Step 3: Create directories**

```bash
mkdir -p backend/app/agent/project_creator/nodes
mkdir -p backend/app/agent/project_creator/prompts
```

- [ ] **Step 4: Create empty __init__.py files**

Create `backend/app/agent/project_creator/__init__.py` (empty)
Create `backend/app/agent/project_creator/nodes/__init__.py` (empty)

---

### Task 2: Create state.py

**Files:** Create `backend/app/agent/project_creator/state.py`

- [ ] **Step 1: Write state.py**

```python
# backend/app/agent/project_creator/state.py
import operator
from typing import Annotated, TypedDict


class ChapterDef(TypedDict):
    title: str
    goal: str


class ActDef(TypedDict):
    name: str
    order: int
    color: str
    chapters: list[ChapterDef]


class SceneDef(TypedDict):
    act_idx: int
    chapter_idx: int
    title: str
    pov_character: str
    setting: str
    scene_time: str
    summary: str


class RawCharacter(TypedDict):
    name: str
    description: str


class CharacterDef(TypedDict):
    name: str
    role: str
    personality: str
    appearance: str
    background: str
    motivation: str


class RelationDef(TypedDict):
    char_name: str
    target_name: str
    rel_type: str
    label: str
    description: str


class MaterialState(TypedDict):
    material: str
    project_title: str
    # analyze_material output
    genre: str
    tone: str
    characters_raw: list[RawCharacter]
    plot_summary: str
    world_elements: str
    # plan_structure output
    acts: list[ActDef]
    estimated_words: int
    # generate_scene_chapter output (reducer: append)
    scenes: Annotated[list[SceneDef], operator.add]
    # design_characters output
    characters: list[CharacterDef]
    relations: list[RelationDef]
    # build_settings output
    global_settings: str
    # validate output
    errors: list[str]
```

The `scenes` field uses `Annotated[list, operator.add]` so that when LangGraph's `Send` API runs `generate_scene_chapter` in parallel for multiple chapters, each branch's returned scenes are automatically concatenated.

---

### Task 3: Create YAML prompts (5 files)

- [ ] **Step 1: material_analyze.yaml**

```yaml
# backend/app/agent/project_creator/prompts/material_analyze.yaml
system: |
  你是一位资深中文小说编辑，专精于从碎片素材中提取完整的叙事要素。

  用户提供了一段创作素材。请仔细分析，提取以下信息并返回 JSON：

  1. genre：故事类型（如 都市、玄幻、科幻、悬疑、爱情 等，1-3个关键词）
  2. tone：故事基调（如 黑暗深沉、轻松幽默、热血励志 等，1-3个关键词）
  3. plot_summary：用200-300字概括素材蕴含的核心情节线
  4. characters_raw：素材中出现的或可推断的角色，每个包含 name 和 description（20字简述）
  5. world_elements：素材中或由其暗示的世界观要素、设定细节（100-200字）

  如果素材中缺失某个维度，基于素材合理推断补充。保持克制不过度发挥。

  返回一个合法的 JSON 对象，不要包含 markdown 代码块标记。
```

- [ ] **Step 2: material_structure.yaml**

```yaml
# backend/app/agent/project_creator/prompts/material_structure.yaml
system: |
  你是一位资深小说结构设计师。

  根据以下分析结果，为一个长篇故事规划完整的幕-章结构。

  类型：{genre}
  基调：{tone}
  情节概要：{plot_summary}
  世界观要素：{world_elements}

  要求：
  1. 规划3-5幕，每幕有名称（如 "开端"、"发展"、"高潮"、"结局"）
  2. 每幕包含2-5章，每章有标题和具体目标
  3. 章目标应该是可执行的叙述指令（如 "主角在拍卖会上发现宿敌现身，被迫做出抉择"）
  4. 总计12-25章，估算总字数（每章约3000-5000字）

  返回 JSON 格式：
  {{
    "estimated_words": 80000,
    "acts": [
      {{
        "name": "第一幕：开端",
        "order": 1,
        "color": "#8b5cf6",
        "chapters": [
          {{"title": "归乡之人", "goal": "退休杀手回到故乡小镇，发现一切都不像表面那样平静"}}
        ]
      }}
    ]
  }}

  返回合法的 JSON，不要 markdown 代码块。
```

- [ ] **Step 3: material_scenes.yaml**

```yaml
# backend/app/agent/project_creator/prompts/material_scenes.yaml
system: |
  你是一位小说场景规划师。

  为一章规划1-3个具体场景。

  幕名：{act_name}
  章标题：{chapter_title}
  章目标：{chapter_goal}

  可用角色：{characters_raw_text}
  世界观：{world_elements}

  要求：
  1. 每个场景有标题、POV角色、地点、故事内时间、梗概
  2. 场景之间有起承转合
  3. POV角色从可用角色中选择

  返回 JSON：
  {{
    "scenes": [
      {{
        "title": "酒吧偶遇",
        "pov_character": "老陈",
        "setting": "镇中心老酒馆",
        "scene_time": "傍晚",
        "summary": "老陈在酒馆遇到多年未见的战友，战友暗示有人要杀他"
      }}
    ]
  }}

  返回合法的 JSON，不要 markdown 代码块。
```

- [ ] **Step 4: material_characters.yaml**

```yaml
# backend/app/agent/project_creator/prompts/material_characters.yaml
system: |
  你是一位小说角色设计师。

  根据故事背景，设计2-8个有深度的角色。

  类型：{genre}
  基调：{tone}
  情节概要：{plot_summary}
  素材中的角色线索：{characters_raw_text}

  要求：
  1. 每个角色包含：name、role（主角 protagonist / 反派 antagonist / 盟友 ally / 支持 supporting / 导师 mentor）、personality（30字）、appearance（30字）、background（50字）、motivation（30字）
  2. 确保正反角色平衡
  3. 角色之间要有内在冲突或张力

  返回 JSON：
  {{
    "characters": [
      {{
        "name": "老陈",
        "role": "protagonist",
        "personality": "沉默寡言但内心重情义，行动果断",
        "appearance": "五十多岁，花白短发，双手布满老茧，眼神犀利",
        "background": "曾是特种部队的王牌狙击手，十年前因任务失败退役，隐居小镇",
        "motivation": "保护唯一的女儿，弥补过去的亏欠"
      }}
    ],
    "relations": [
      {{
        "char_name": "老陈",
        "target_name": "赵敏",
        "rel_type": "关联",
        "label": "父亲-女儿",
        "description": "老陈对女儿过度保护，女儿不知父亲真实身份"
      }}
    ]
  }}

  返回合法的 JSON，不要 markdown 代码块。
```

- [ ] **Step 5: material_settings.yaml**

```yaml
# backend/app/agent/project_creator/prompts/material_settings.yaml
system: |
  你是一位世界构建师。

  为故事写一份全局世界观设定文档（2-5段）。

  类型：{genre}
  基调：{tone}
  情节概要：{plot_summary}
  世界观素材：{world_elements}

  要求：
  1. 涵盖：时代背景、核心规则（如魔法/科技体系）、社会结构、氛围基调
  2. 用连贯的段落，而非要点列表
  3. 300-600字

  返回 JSON：
  {{"global_settings": "故事发生在一个名为..."}}

  返回合法的 JSON，不要 markdown 代码块。
```

---

### Task 4: Create analyze.py node

**Files:** Create `backend/app/agent/project_creator/nodes/analyze.py`

- [ ] **Step 1: Write analyze.py**

```python
# backend/app/agent/project_creator/nodes/analyze.py
import json
import yaml
from pathlib import Path
from app.agent.client import LLMClient
from app.agent.project_creator.state import MaterialState

PROMPT_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("system", "")


async def analyze_material(state: MaterialState) -> dict:
    client = LLMClient()
    system_prompt = _load_prompt("material_analyze")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"素材内容：\n\n{state['material']}"},
    ]

    raw = await client.chat(messages, temperature=0.3)
    parsed = _parse_json(raw)

    return {
        "genre": parsed.get("genre", ""),
        "tone": parsed.get("tone", ""),
        "characters_raw": parsed.get("characters_raw", []),
        "plot_summary": parsed.get("plot_summary", ""),
        "world_elements": parsed.get("world_elements", ""),
    }


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        end = next((i for i in range(len(lines) - 1, 0, -1) if lines[i].strip() == "```"), len(lines))
        text = "\n".join(lines[1:end])
    return json.loads(text)
```

---

### Task 5: Create plan.py node

**Files:** Create `backend/app/agent/project_creator/nodes/plan.py`

- [ ] **Step 1: Write plan.py**

```python
# backend/app/agent/project_creator/nodes/plan.py
import json
import yaml
from pathlib import Path
from app.agent.client import LLMClient
from app.agent.project_creator.state import MaterialState

PROMPT_DIR = Path(__file__).parent.parent / "prompts"

COLORS = ["#f97316", "#8b5cf6", "#06b6d4", "#ec4899", "#10b981"]


def _load(name: str) -> str:
    path = PROMPT_DIR / f"{name}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("system", "")


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        end = next((i for i in range(len(lines) - 1, 0, -1) if lines[i].strip() == "```"), len(lines))
        text = "\n".join(lines[1:end])
    return json.loads(text)


async def plan_structure(state: MaterialState) -> dict:
    client = LLMClient()
    system = _load("material_structure").format(
        genre=state.get("genre", ""),
        tone=state.get("tone", ""),
        plot_summary=state.get("plot_summary", ""),
        world_elements=state.get("world_elements", ""),
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "请规划完整的幕-章结构"},
    ]

    raw = await client.chat(messages, temperature=0.5, max_tokens=4096)
    parsed = _parse_json(raw)

    acts = parsed.get("acts", [])
    for i, act in enumerate(acts):
        if "color" not in act:
            act["color"] = COLORS[i % len(COLORS)]
        for ch in act.get("chapters", []):
            if "goal" not in ch:
                ch["goal"] = ""

    return {
        "acts": acts,
        "estimated_words": parsed.get("estimated_words", 50000),
    }
```

---

### Task 6: Create scenes.py node

**Files:** Create `backend/app/agent/project_creator/nodes/scenes.py`

- [ ] **Step 1: Write scenes.py**

This node is used by LangGraph's `Send` API. Each parallel invocation gets `act_idx` and `chapter_idx` from the `Send` override, plus the rest of the state.

```python
# backend/app/agent/project_creator/nodes/scenes.py
import json
import yaml
from pathlib import Path
from app.agent.client import LLMClient
from app.agent.project_creator.state import MaterialState, SceneDef

PROMPT_DIR = Path(__file__).parent.parent / "prompts"


def _load(name: str) -> str:
    path = PROMPT_DIR / f"{name}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("system", "")


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        end = next((i for i in range(len(lines) - 1, 0, -1) if lines[i].strip() == "```"), len(lines))
        text = "\n".join(lines[1:end])
    return json.loads(text)


def _raw_chars_text(raw_chars: list[dict]) -> str:
    if not raw_chars:
        return "暂无角色"
    return "\n".join(f"- {c['name']}: {c.get('description', '')}" for c in raw_chars)


async def generate_scene_chapter(state: MaterialState) -> dict:
    act_idx = state.get("_fanout_act_idx", 0)
    chap_idx = state.get("_fanout_chap_idx", 0)
    acts = state.get("acts", [])

    if act_idx >= len(acts):
        return {"scenes": []}
    act = acts[act_idx]
    chapters = act.get("chapters", [])
    if chap_idx >= len(chapters):
        return {"scenes": []}

    chapter = chapters[chap_idx]
    client = LLMClient()

    system = _load("material_scenes").format(
        act_name=act.get("name", ""),
        chapter_title=chapter.get("title", ""),
        chapter_goal=chapter.get("goal", ""),
        characters_raw_text=_raw_chars_text(state.get("characters_raw", [])),
        world_elements=state.get("world_elements", ""),
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "请为这一章规划场景"},
    ]

    raw = await client.chat(messages, temperature=0.6, max_tokens=2048)
    parsed = _parse_json(raw)

    scene_dicts = parsed.get("scenes", [])
    scenes: list[SceneDef] = []
    for sc in scene_dicts:
        scenes.append(SceneDef(
            act_idx=act_idx,
            chapter_idx=chap_idx,
            title=sc.get("title", ""),
            pov_character=sc.get("pov_character", ""),
            setting=sc.get("setting", ""),
            scene_time=sc.get("scene_time", ""),
            summary=sc.get("summary", ""),
        ))

    return {"scenes": scenes}
```

---

### Task 7: Create characters.py node

**Files:** Create `backend/app/agent/project_creator/nodes/characters.py`

- [ ] **Step 1: Write characters.py**

```python
# backend/app/agent/project_creator/nodes/characters.py
import json
import yaml
from pathlib import Path
from app.agent.client import LLMClient
from app.agent.project_creator.state import MaterialState

PROMPT_DIR = Path(__file__).parent.parent / "prompts"


def _load(name: str) -> str:
    path = PROMPT_DIR / f"{name}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("system", "")


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        end = next((i for i in range(len(lines) - 1, 0, -1) if lines[i].strip() == "```"), len(lines))
        text = "\n".join(lines[1:end])
    return json.loads(text)


def _raw_chars_text(raw_chars: list[dict]) -> str:
    if not raw_chars:
        return "素材中未明确提及角色"
    return "\n".join(f"- {c['name']}: {c.get('description', '')}" for c in raw_chars)


async def design_characters(state: MaterialState) -> dict:
    client = LLMClient()
    system = _load("material_characters").format(
        genre=state.get("genre", ""),
        tone=state.get("tone", ""),
        plot_summary=state.get("plot_summary", ""),
        characters_raw_text=_raw_chars_text(state.get("characters_raw", [])),
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "请设计角色"},
    ]

    raw = await client.chat(messages, temperature=0.7, max_tokens=4096)
    parsed = _parse_json(raw)

    characters = parsed.get("characters", [])
    for c in characters:
        c.setdefault("role", "supporting")
        c.setdefault("personality", "")
        c.setdefault("appearance", "")
        c.setdefault("background", "")
        c.setdefault("motivation", "")

    relations = parsed.get("relations", [])
    for r in relations:
        r.setdefault("rel_type", "关联")
        r.setdefault("label", "")
        r.setdefault("description", "")

    return {"characters": characters, "relations": relations}
```

---

### Task 8: Create settings.py node

**Files:** Create `backend/app/agent/project_creator/nodes/settings.py`

- [ ] **Step 1: Write settings.py**

```python
# backend/app/agent/project_creator/nodes/settings.py
import json
import yaml
from pathlib import Path
from app.agent.client import LLMClient
from app.agent.project_creator.state import MaterialState

PROMPT_DIR = Path(__file__).parent.parent / "prompts"


def _load(name: str) -> str:
    path = PROMPT_DIR / f"{name}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("system", "")


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        end = next((i for i in range(len(lines) - 1, 0, -1) if lines[i].strip() == "```"), len(lines))
        text = "\n".join(lines[1:end])
    return json.loads(text)


async def build_settings(state: MaterialState) -> dict:
    client = LLMClient()
    system = _load("material_settings").format(
        genre=state.get("genre", ""),
        tone=state.get("tone", ""),
        plot_summary=state.get("plot_summary", ""),
        world_elements=state.get("world_elements", ""),
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "请生成世界观设定"},
    ]

    raw = await client.chat(messages, temperature=0.5, max_tokens=2048)
    parsed = _parse_json(raw)

    return {"global_settings": parsed.get("global_settings", "")}
```

---

### Task 9: Create validate.py node

**Files:** Create `backend/app/agent/project_creator/nodes/validate.py`

- [ ] **Step 1: Write validate.py**

```python
# backend/app/agent/project_creator/nodes/validate.py
from app.agent.project_creator.state import MaterialState

MAX_ACTS = 5
MAX_CHAPTERS_PER_ACT = 5
MAX_SCENES_PER_CHAPTER = 5
MAX_CHARACTERS = 10


async def validate(state: MaterialState) -> dict:
    errors: list[str] = []
    acts = state.get("acts", [])

    if len(acts) > MAX_ACTS:
        errors.append(f"幕数 {len(acts)} 超过上限 {MAX_ACTS}")
        state["acts"] = acts[:MAX_ACTS]

    for act in acts:
        chapters = act.get("chapters", [])
        if len(chapters) > MAX_CHAPTERS_PER_ACT:
            errors.append(f"幕 '{act.get('name', '')}' 的章数 {len(chapters)} 超过上限 {MAX_CHAPTERS_PER_ACT}")
            act["chapters"] = chapters[:MAX_CHAPTERS_PER_ACT]

    if len(state.get("characters", [])) > MAX_CHARACTERS:
        errors.append(f"角色数超过上限 {MAX_CHARACTERS}")
        state["characters"] = state["characters"][:MAX_CHARACTERS]

    scenes = state.get("scenes", [])
    chapter_scene_counts: dict[str, int] = {}
    trimmed_scenes = []
    for sc in scenes:
        key = f"{sc['act_idx']}-{sc['chapter_idx']}"
        count = chapter_scene_counts.get(key, 0)
        if count < MAX_SCENES_PER_CHAPTER:
            chapter_scene_counts[key] = count + 1
            trimmed_scenes.append(sc)
        else:
            errors.append(f"章节 {key} 的场景数超过上限")

    return {"scenes": trimmed_scenes, "errors": errors}
```

---

### Task 10: Create graph.py (StateGraph assembly)

**Files:** Create `backend/app/agent/project_creator/graph.py`

- [ ] **Step 1: Write graph.py**

```python
# backend/app/agent/project_creator/graph.py
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.memory import MemorySaver
from app.agent.project_creator.state import MaterialState
from app.agent.project_creator.nodes.analyze import analyze_material
from app.agent.project_creator.nodes.plan import plan_structure
from app.agent.project_creator.nodes.scenes import generate_scene_chapter
from app.agent.project_creator.nodes.characters import design_characters
from app.agent.project_creator.nodes.settings import build_settings
from app.agent.project_creator.nodes.validate import validate


def _fanout_scenes(state: MaterialState):
    sends = []
    for act_idx, act in enumerate(state.get("acts", [])):
        for chap_idx in range(len(act.get("chapters", []))):
            sends.append(Send("generate_scene_chapter", {
                "_fanout_act_idx": act_idx,
                "_fanout_chap_idx": chap_idx,
            }))
    return sends


def build_graph():
    builder = StateGraph(state_schema=MaterialState)

    builder.add_node("analyze_material", analyze_material)
    builder.add_node("plan_structure", plan_structure)
    builder.add_node("generate_scene_chapter", generate_scene_chapter)
    builder.add_node("design_characters", design_characters)
    builder.add_node("build_settings", build_settings)
    builder.add_node("validate", validate)

    builder.add_edge(START, "analyze_material")
    builder.add_edge("analyze_material", "plan_structure")
    builder.add_conditional_edges("plan_structure", _fanout_scenes)
    builder.add_edge("generate_scene_chapter", "design_characters")
    builder.add_edge("design_characters", "build_settings")
    builder.add_edge("build_settings", "validate")
    builder.add_edge("validate", END)

    return builder.compile(checkpointer=MemorySaver())
```

---

### Task 11: Create SSE API endpoint + write-to-DB

**Files:** Modify `backend/app/api/routes_ai.py`

- [ ] **Step 1: Add imports at top of routes_ai.py**

```python
# Add these imports to the existing routes_ai.py file:
import asyncio
import json as json_mod
from fastapi.responses import StreamingResponse
from app.agent.project_creator.graph import build_graph
from app.agent.project_creator.state import MaterialState
from app.storycad.entity_map import ENTITY_MAP
from app.storycad.repository import StoryCADRepository
```

- [ ] **Step 2: Add Pydantic model**

```python
# Add after existing AiGenerateRequest:
class CreateFromMaterialRequest(BaseModel):
    title: str = "未命名项目"
    material: str
```

- [ ] **Step 3: Add SSE endpoint**

Append to routes_ai.py:

```python
@router.post("/create-from-material")
async def create_from_material(
    payload: CreateFromMaterialRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not payload.material.strip():
        raise HTTPException(status_code=400, detail="素材不能为空")
    if len(payload.material) > 5000:
        raise HTTPException(status_code=400, detail="素材不能超过5000字")

    async def event_stream():
        graph = build_graph()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        initial_state: MaterialState = {
            "material": payload.material.strip(),
            "project_title": payload.title.strip() or "未命名项目",
            "genre": "", "tone": "", "characters_raw": [],
            "plot_summary": "", "world_elements": "",
            "acts": [], "estimated_words": 0, "scenes": [],
            "characters": [], "relations": [],
            "global_settings": "", "errors": [],
        }

        try:
            async for event in graph.astream(initial_state, config):
                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        preview = _make_preview(node_name, node_output)
                        yield f"data: {json_mod.dumps({'step': node_name, 'status': 'done', 'preview': preview})}\n\n"
        except Exception as e:
            yield f"data: {json_mod.dumps({'step': 'error', 'message': str(e)})}\n\n"
            return

        # Get final state and write to DB
        final_state = graph.get_state(config).values
        try:
            project_id = await _write_project_to_db(db, final_state, uuid.UUID(current_user["id"]))
            yield f"data: {json_mod.dumps({'step': 'done', 'project_id': str(project_id)})}\n\n"
        except Exception as e:
            yield f"data: {json_mod.dumps({'step': 'error', 'message': f'数据库写入失败: {str(e)}'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _make_preview(node_name: str, output: dict) -> str:
    if node_name == "analyze_material":
        return f"类型：{output.get('genre', '')}\n基调：{output.get('tone', '')}"
    elif node_name == "plan_structure":
        acts = output.get("acts", [])
        total_ch = sum(len(a.get("chapters", [])) for a in acts)
        return f"{len(acts)}幕{total_ch}章 · 预估{output.get('estimated_words', 0)}字"
    elif node_name == "generate_scene_chapter":
        sc = output.get("scenes", [])
        return f"+{len(sc)}个场景"
    elif node_name == "design_characters":
        return f"{len(output.get('characters', []))}个角色已创建"
    elif node_name == "build_settings":
        gs = output.get("global_settings", "")
        return gs[:80] + ("..." if len(gs) > 80 else "")
    elif node_name == "validate":
        return "校验通过" if not output.get("errors") else f"修正了{len(output.get('errors', []))}个问题"
    return ""


async def _write_project_to_db(db: AsyncSession, state: dict, owner_id: uuid.UUID) -> uuid.UUID:
    from app.project.service import ProjectService
    from app.storycad.entity_map import ENTITY_MAP

    svc = ProjectService(db)
    repo = StoryCADRepository(db)

    project = await svc.create_project(state.get("project_title", "未命名"), "", owner_id)
    project_id = uuid.UUID(project["id"])
    await db.commit()

    # Create acts
    act_id_map = {}
    for act in state.get("acts", []):
        result = await repo.create_entity(
            ENTITY_MAP["acts"],
            {
                "project_id": str(project_id),
                "name": act.get("name", ""),
                "sort_order": act.get("order", 1),
                "color": act.get("color", "#8b5cf6"),
            },
        )
        act_id_map[act.get("order", 1)] = result["id"]

    # Create chapters + scenes
    chapter_sort = 0
    scene_sort_total = 0
    scenes = state.get("scenes", [])
    chap_id_map = {}
    for act_idx, act in enumerate(state.get("acts", [])):
        for ch_idx, ch in enumerate(act.get("chapters", [])):
            chapter_sort += 1
            chapter_sort_local = ch_idx
            act_id = act_id_map.get(act.get("order", act_idx + 1), "")
            chapter_result = await repo.create_entity(
                ENTITY_MAP["chapters"],
                {
                    "project_id": str(project_id),
                    "act_id": str(act_id),
                    "title": ch.get("title", ""),
                    "goal": ch.get("goal", ""),
                    "sort_order": chapter_sort,
                    "status": "draft",
                },
            )
            chap_id_map[(act_idx, ch_idx)] = chapter_result["id"]

    # Create scenes under chapters
    for sc in sorted(scenes, key=lambda s: (s["act_idx"], s["chapter_idx"])):
        cid = chap_id_map.get((sc["act_idx"], sc["chapter_idx"]))
        if cid:
            scene_sort_total += 1
            await repo.create_entity(
                ENTITY_MAP["scenes"],
                {
                    "project_id": str(project_id),
                    "chapter_id": str(cid),
                    "title": sc["title"],
                    "pov_character": sc.get("pov_character", ""),
                    "setting": sc.get("setting", ""),
                    "scene_time": sc.get("scene_time", ""),
                    "summary": sc.get("summary", ""),
                    "sort_order": scene_sort_total,
                },
            )

    # Create characters
    char_name_to_id: dict[str, str] = {}
    for char in state.get("characters", []):
        result = await repo.create_entity(
            ENTITY_MAP["characters"],
            {
                "project_id": str(project_id),
                "name": char["name"],
                "role": char.get("role", "supporting"),
                "personality": char.get("personality", ""),
                "appearance": char.get("appearance", ""),
                "background": char.get("background", ""),
                "motivation": char.get("motivation", ""),
                "sort_order": len(char_name_to_id),
            },
        )
        char_name_to_id[char["name"]] = result["id"]

    # Create relations
    for rel in state.get("relations", []):
        src_id = char_name_to_id.get(rel.get("char_name", ""))
        tgt_id = char_name_to_id.get(rel.get("target_name", ""))
        if src_id and tgt_id:
            await repo.create_entity(
                ENTITY_MAP["character_relations"],
                {
                    "project_id": str(project_id),
                    "character_id": str(src_id),
                    "target_id": str(tgt_id),
                    "rel_type": rel.get("rel_type", "关联"),
                    "label": rel.get("label", ""),
                    "description": rel.get("description", ""),
                },
            )

    # Create ProjectConfig
    from app.project.models import ProjectConfig
    config = ProjectConfig(
        project_id=project_id,
        total_words=state.get("estimated_words", 50000),
        template_type="custom",
    )
    db.add(config)

    # Save global settings
    gs = state.get("global_settings", "")
    if gs:
        from app.project.models import Project
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        proj = result.scalar_one_or_none()
        if proj:
            proj.global_settings = gs

    await db.commit()
    return project_id
```

Note: The `_write_project_to_db` function also needs this import at the file level:
```python
from sqlalchemy import select
from app.project.models import Project, ProjectConfig
```

---

### Task 12: Frontend API client

**Files:** Modify `frontend/src/api/ai.ts`

- [ ] **Step 1: Add createFromMaterial function**

Append to `frontend/src/api/ai.ts`:

```typescript
export interface CreateMaterialRequest {
  title: string
  material: string
}

export interface ProgressEvent {
  step: string
  status: 'running' | 'done'
  preview?: string
  progress?: string
  project_id?: string
  message?: string
}

export function createFromMaterial(
  request: CreateMaterialRequest,
  onProgress: (event: ProgressEvent) => void,
  onDone: (projectId: string) => void,
  onError: (message: string) => void,
): () => void {
  const token = localStorage.getItem('storycad_token')
  const url = `/api/projects/create-from-material`
  const controller = new AbortController()

  fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(request),
    signal: controller.signal,
  }).then(async (response) => {
    if (!response.ok) {
      const text = await response.text()
      try {
        const err = JSON.parse(text)
        onError(err.detail || '请求失败')
      } catch {
        onError(text || '请求失败')
      }
      return
    }

    const reader = response.body?.getReader()
    if (!reader) { onError('无法读取响应流'); return }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data: ProgressEvent = JSON.parse(line.slice(6))
            onProgress(data)
            if (data.step === 'done' && data.project_id) {
              onDone(data.project_id)
            }
            if (data.step === 'error') {
              onError(data.message || '生成失败')
            }
          } catch {}
        }
      }
    }
  }).catch((err) => {
    if (err.name !== 'AbortError') {
      onError(err.message || '网络错误')
    }
  })

  return () => controller.abort()
}
```

---

### Task 13: Wire CreateProjectDialog

**Files:** Modify `frontend/src/pages/home/CreateProjectDialog.tsx`

- [ ] **Step 1: Add imports**

```typescript
// Add to existing imports:
import { createFromMaterial, type ProgressEvent } from "../../api/ai"
```

- [ ] **Step 2: Add state for material mode**

```typescript
// Add these state variables inside the component, after existing useState lines:
const [materialText, setMaterialText] = useState("")
const [aiSteps, setAiSteps] = useState<ProgressEvent[]>([])
const [aiGenerating, setAiGenerating] = useState(false)
```

- [ ] **Step 3: Add material creation handler**

```typescript
// Add this function inside the component:
function handleCreateFromMaterial() {
  if (!materialText.trim() || !title.trim()) return
  setAiGenerating(true)
  setAiSteps([])
  const events: ProgressEvent[] = []
  createFromMaterial(
    { title: title.trim(), material: materialText.trim() },
    (evt) => {
      events.push(evt)
      setAiSteps([...events])
    },
    (projectId) => {
      navigate(`/projects/${projectId}`)
    },
    (msg) => {
      alert(msg)
      setAiGenerating(false)
    },
  )
}

function handleStartMaterial() {
  setMode("material" as any)
  setTitle("")
  setMaterialText("")
  setAiSteps([])
  setAiGenerating(false)
}
```

- [ ] **Step 4: Enable the "从素材创建" button**

Change the disabled button (lines 62-74):
```tsx
<button
  onClick={handleStartMaterial}
  className="w-full flex items-center gap-5 p-5 rounded-xl bg-gray-800 border border-gray-700 hover:border-yellow-500/50 hover:bg-gray-800/80 transition-all text-left group"
>
  <div className="w-12 h-12 rounded-full bg-yellow-500/10 text-yellow-400 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
    <FolderUp className="w-6 h-6" />
  </div>
  <div className="flex-1">
    <div className="font-bold text-gray-100 mb-0.5">从素材创建</div>
    <div className="text-sm text-gray-500">粘贴故事创意，AI 自动搭建项目框架</div>
  </div>
</button>
```

- [ ] **Step 5: Add "material" mode UI**

After the "empty" mode block (line 114, after `)}`), add:

```tsx
        {mode === "material" && !aiGenerating && aiSteps.length === 0 && (
          <>
            <div className="flex items-center gap-3 mb-6">
              <button onClick={() => setMode("pick")} className="text-gray-500 hover:text-gray-300 transition-colors">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
              </button>
              <h2 className="text-xl font-bold text-gray-100">从素材创建</h2>
            </div>
            <div className="mb-4">
              <label className="block text-sm text-gray-400 mb-2">项目名称</label>
              <input
                autoFocus
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="输入项目名称..."
                className="w-full px-4 py-3 rounded-xl bg-gray-800 border border-gray-700 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-yellow-500/50 transition-colors"
              />
            </div>
            <div className="mb-6">
              <label className="block text-sm text-gray-400 mb-2">
                创作素材 <span className="text-gray-600">（粘贴你的故事创意、角色设定、情节大纲...）</span>
              </label>
              <textarea
                value={materialText}
                onChange={e => setMaterialText(e.target.value)}
                placeholder="例如：一个退隐杀手在边境小镇收到养女被绑架的消息，被迫重出江湖。小镇上所有人都藏着秘密，而他必须在三天内找到女儿..."
                className="w-full h-40 px-4 py-3 rounded-xl bg-gray-800 border border-gray-700 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-yellow-500/50 transition-colors resize-none"
                maxLength={5000}
              />
              <div className="text-right text-[10px] text-gray-600 mt-1">{materialText.length}/5000</div>
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setMode("pick")} className="px-5 py-2.5 rounded-xl text-gray-400 hover:text-gray-200 transition-colors">返回</button>
              <button
                onClick={handleCreateFromMaterial}
                disabled={!title.trim() || !materialText.trim()}
                className="px-6 py-2.5 rounded-xl bg-yellow-600 text-white font-bold hover:bg-yellow-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                AI 分析与生成
              </button>
            </div>
          </>
        )}

        {mode === "material" && (aiGenerating || aiSteps.length > 0) && (
          <>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-100">AI 正在生成项目框架...</h2>
              <button onClick={() => navigate("/")} className="text-gray-500 hover:text-white text-lg">✕</button>
            </div>
            <div className="space-y-2 mb-6">
              {["analyze_material", "plan_structure", "design_characters", "build_settings", "validate"].map(step => {
                const evt = aiSteps.find(e => e.step === step)
                const labels: Record<string, string> = {
                  analyze_material: "分析素材",
                  plan_structure: "规划结构",
                  design_characters: "设计角色",
                  build_settings: "生成世界观",
                  validate: "校验结果",
                }
                const icon = evt ? "✓" : aiSteps.length > 0 && aiSteps[aiSteps.length - 1].step === step ? "⏳" : "○"
                const active = !!evt
                return (
                  <div key={step} className={`flex items-start gap-3 p-2 rounded-lg ${active ? 'bg-gray-800/60' : ''}`}>
                    <span className={`text-sm w-5 ${active ? 'text-green-400' : 'text-gray-600'}`}>{icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className={`text-sm ${active ? 'text-gray-200' : 'text-gray-600'}`}>{labels[step]}</div>
                      {evt?.preview && <div className="text-xs text-gray-500 mt-0.5 whitespace-pre-wrap">{evt.preview}</div>}
                    </div>
                  </div>
                )
              })}
            </div>
            {!aiSteps.find(e => e.step === "done") && !aiSteps.find(e => e.step === "error") && (
              <div className="text-center text-sm text-gray-500 animate-pulse">
                {aiSteps.length >= 5 ? "正在写入项目数据..." : "AI 思考中..."}
              </div>
            )}
            {aiSteps.find(e => e.step === "done") && (
              <div className="text-center text-sm text-green-400">项目创建完成！正在跳转...</div>
            )}
          </>
        )}
```

The `mode` state type needs updating from `"pick" | "empty"` to `"pick" | "empty" | "material"`:
```typescript
const [mode, setMode] = useState<"pick" | "empty" | "material">("pick")
```

---

### Task 14: Verify + commit

- [ ] **Step 1: Install langgraph in container**

```bash
docker exec storycad-backend-1 pip install langgraph langgraph-checkpoint
```

Verify: `docker exec storycad-backend-1 python -c "import langgraph; print(langgraph.__version__)"`

- [ ] **Step 2: Restart backend and check logs**

```bash
docker compose restart backend
docker logs storycad-backend-1 --tail 10
```

No import errors expected.

- [ ] **Step 3: Test endpoint via curl**

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"email":"test@test.com","password":"testtest"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -N -X POST http://localhost:8000/api/projects/create-from-material \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"测试项目","material":"一个年轻的魔法学徒发现自己是上古龙族的后裔"}'
```

Expected: SSE stream with progress events, ending with `{"step":"done","project_id":"..."}`.

- [ ] **Step 4: Verify frontend compiles**

Check `docker logs storycad-frontend-1 --tail 5` for no errors.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: implement create-from-material AI system with LangGraph pipeline"
```
