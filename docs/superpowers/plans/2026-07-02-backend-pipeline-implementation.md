# Story-Forge Backend Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the backend multi-agent LLM pipeline for narrative skeleton generation with database persistence.

**Architecture:** 6 LangGraph agents (idea_parser done, 5 to implement) connected in a linear pipeline with a validation-triggered repair loop. PostgreSQL replaces in-memory storage.

**Tech Stack:** FastAPI, LangGraph, LangChain ChatOpenAI, SQLAlchemy 2.0 async, asyncpg, Pydantic

---

## File Structure

```
backend/app/
├── agents/
│   ├── __init__.py
│   ├── idea_parser.py         # EXISTING - keep as-is
│   ├── world_builder.py       # REWRITE - WorldRules from creative_doc
│   ├── character_designer.py  # REWRITE - CharacterProfiles from creative_doc + world_rules
│   ├── plot_graph.py          # REWRITE - EventNodes + CausalityEdges
│   ├── branch_foreshadow.py   # REWRITE - Branches + Foreshadows
│   └── validator.py           # REWRITE - consistency checks on full skeleton
├── graph/
│   ├── __init__.py
│   └── story_graph.py         # REWRITE - full pipeline with conditional edges + repair loop
├── models/
│   ├── __init__.py
│   ├── domain.py              # EXISTING - keep as-is
│   └── db.py                  # REWRITE - SQLAlchemy async models
├── services/
│   ├── __init__.py
│   ├── generation.py          # REWRITE - use DB instead of in-memory dict
│   └── storage.py             # REWRITE - async DB CRUD operations
├── api/
│   ├── __init__.py
│   └── routes.py              # ENHANCE - add validation endpoint
├── config.py                  # EXISTING - keep as-is
├── main.py                    # EXISTING - already includes router
```

---

### Task 1: Database Models

**Files:**
- Rewrite: `backend/app/models/db.py`

- [ ] **Step 1: Write the async SQLAlchemy models**

```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs

class Base(AsyncAttrs, DeclarativeBase):
    pass

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(20), default="pending")
    raw_input = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    skeletons = relationship("ProjectSkeleton", back_populates="project", order_by="ProjectSkeleton.version.desc()")

class ProjectSkeleton(Base):
    __tablename__ = "project_skeletons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    version = Column(Integer, default=1)
    skeleton = Column(JSONB, nullable=True)
    validation_report = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    project = relationship("Project", back_populates="skeletons")
```

- [ ] **Step 2: Add async engine setup to config.py**

```python
# Add to app/config.py
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/storyforge")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
```

- [ ] **Step 3: Create `app/database.py` for engine/session**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session

async def init_db():
    from app.models.db import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

---

### Task 2: Storage Service

**Files:**
- Rewrite: `backend/app/services/storage.py`

- [ ] **Step 1: Implement async CRUD operations**

```python
import uuid
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db import Project, ProjectSkeleton

async def create_project(db: AsyncSession, raw_input: dict) -> Project:
    project = Project(id=uuid.uuid4(), raw_input=raw_input, status="pending")
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project

async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Project | None:
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()

async def update_project_status(db: AsyncSession, project_id: uuid.UUID, status: str):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project:
        project.status = status
        await db.commit()

async def save_skeleton(db: AsyncSession, project_id: uuid.UUID, skeleton: dict, validation_report: list | None = None):
    # get current max version
    result = await db.execute(
        select(ProjectSkeleton)
        .where(ProjectSkeleton.project_id == project_id)
        .order_by(desc(ProjectSkeleton.version))
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    version = (latest.version + 1) if latest else 1

    sk = ProjectSkeleton(
        project_id=project_id,
        version=version,
        skeleton=skeleton,
        validation_report=validation_report
    )
    db.add(sk)
    await db.commit()

async def get_latest_skeleton(db: AsyncSession, project_id: uuid.UUID) -> ProjectSkeleton | None:
    result = await db.execute(
        select(ProjectSkeleton)
        .where(ProjectSkeleton.project_id == project_id)
        .order_by(desc(ProjectSkeleton.version))
        .limit(1)
    )
    return result.scalar_one_or_none()
```

---

### Task 3: World Builder Agent

**Files:**
- Rewrite: `backend/app/agents/world_builder.py`

- [ ] **Step 1: Implement world builder agent with LLM**

```python
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL_NAME

llm = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    model=MODEL_NAME,
    temperature=0.3,
    model_kwargs={"response_format": {"type": "json_object"}}
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个世界观架构师。根据创意解析文档，构建世界规则体系。

输出严格JSON：
{{
  "rules": [
    {{
      "category": "物理规则/魔法体系/社会结构/科技水平/文化习俗",
      "description": "规则的具体描述",
      "limitation": "规则的边界或限制条件"
    }}
  ],
  "history": "世界背景历史概要（100-200字）",
  "forbidden_events": ["在这个世界中不可能发生的事件1", "不可能发生的事件2"]
}}

要求：
1. 从创意文档的 implied_world_clues 推断世界观
2. 每个规则必须有明确的 limitation（不能空泛）
3. forbidden_events 必须覆盖约束中提到的限制
4. 输出 3-5 条核心规则
5. 只输出JSON，不要解释"""),
    ("user", """创意文档：{creative_doc}""")
])

def run(state: dict) -> dict:
    chain = prompt | llm
    response = chain.invoke({"creative_doc": json.dumps(state["creative_doc"], ensure_ascii=False)})
    world_rules = json.loads(response.content)
    return {"world_rules": world_rules}
```

---

### Task 4: Character Designer Agent

**Files:**
- Rewrite: `backend/app/agents/character_designer.py`

- [ ] **Step 1: Implement character designer agent with LLM**

```python
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL_NAME

llm = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    model=MODEL_NAME,
    temperature=0.4,
    model_kwargs={"response_format": {"type": "json_object"}}
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个角色设计师。根据创意文档和世界观规则，设计角色全息档案。

输出严格JSON，是一个数组：
[
  {{
    "name": "角色名",
    "desire_topology": {{
      "表层欲望": "角色表面追求的目标",
      "深层需求": "角色真正需要的心理需求",
      "核心恐惧": "角色最害怕发生的事"
    }},
    "bottom_line": "角色绝不会越过的底线",
    "vulnerability": "可以被对手利用的弱点",
    "language_genes": ["典型台词1", "典型台词2", "典型台词3"],
    "relationships": {{
      "其他角色名": {{"信任": 0-100, "威胁": 0-100, "吸引力": 0-100}}
    }},
    "growth_arc": "角色在故事中的成长弧线描述"
  }}
]

要求：
1. 如有 character_seeds，必须包含这些角色，并丰富其档案
2. 如无角色种子，根据核心冲突自动创建 2-3 个角色
3. 关系矩阵中的数值需合理：对立角色威胁高、信任低
4. 语言基因要符合角色身份
5. 只输出JSON，不要解释"""),
    ("user", """创意文档：{creative_doc}
世界观规则：{world_rules}""")
])

def run(state: dict) -> dict:
    chain = prompt | llm
    response = chain.invoke({
        "creative_doc": json.dumps(state["creative_doc"], ensure_ascii=False),
        "world_rules": json.dumps(state["world_rules"], ensure_ascii=False)
    })
    characters = json.loads(response.content)
    if isinstance(characters, dict) and "characters" in characters:
        characters = characters["characters"]
    return {"characters": characters}
```

---

### Task 5: Plot Graph Agent

**Files:**
- Rewrite: `backend/app/agents/plot_graph.py`

- [ ] **Step 1: Implement plot graph agent with LLM**

```python
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL_NAME

llm = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    model=MODEL_NAME,
    temperature=0.4,
    model_kwargs={"response_format": {"type": "json_object"}}
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个情节架构师。根据世界观、角色档案和创意文档，生成因果事件图谱。

输出严格JSON：
{{
  "nodes": [
    {{"id": "evt_1", "description": "事件描述（15-30字）", "emotion_value": 0-100}}
  ],
  "edges": [
    {{"source": "evt_1", "target": "evt_2", "type": "necessary/possible/indirect"}}
  ]
}}

要求：
1. 必须包含创意文档中的所有 anchor_events
2. 因果关系类型：necessary(必然导致), possible(可能导致), indirect(间接影响)
3. 节点 8-15 个，形成完整的故事弧线
4. emotion_value 要有起伏：开场中等(50-70)→上升→高潮(80-100)→下降→结局(40-60)
5. 边必须闭合：每个节点至少有一条入边和一条出边（开头和结尾节点除外）
6. 事件描述要具体，不要泛泛而谈
7. 只输出JSON，不要解释"""),
    ("user", """创意文档：{creative_doc}
世界观规则：{world_rules}
角色档案：{characters}""")
])

def run(state: dict) -> dict:
    chain = prompt | llm
    response = chain.invoke({
        "creative_doc": json.dumps(state["creative_doc"], ensure_ascii=False),
        "world_rules": json.dumps(state["world_rules"], ensure_ascii=False),
        "characters": json.dumps(state["characters"], ensure_ascii=False)
    })
    graph_data = json.loads(response.content)
    return {"graph_data": graph_data}
```

---

### Task 6: Branch & Foreshadow Agent

**Files:**
- Rewrite: `backend/app/agents/branch_foreshadow.py`

- [ ] **Step 1: Implement branch and foreshadow agent with LLM**

```python
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL_NAME

llm = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    model=MODEL_NAME,
    temperature=0.4,
    model_kwargs={"response_format": {"type": "json_object"}}
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个分支叙事设计师。根据因果图谱和角色档案，设计分支路线和伏笔系统。

输出严格JSON：
{{
  "branches": [
    {{
      "divergence_point": "evt_X（分歧发生的节点ID）",
      "paths": [
        ["分支路径上的事件ID列表"],
        ["另一条路径的事件ID列表"]
      ],
      "convergence_point": "evt_Y（汇合节点ID，可以为null）"
    }}
  ],
  "foreshadows": [
    {{
      "id": "fs_1",
      "planted_at": "evt_X（埋设节点ID）",
      "content": "伏笔的具体内容",
      "status": "pending",
      "planned_recycle_interval": "预期在evt_Y到evt_Z之间回收"
    }}
  ]
}}

要求：
1. 在情感值高或角色决策点处设置分歧点
2. 分支路径需有不同情感走向
3. 伏笔内容要具体，不要空泛
4. 每个伏笔都要有预期的回收区间
5. 如果图谱较小可以没有分支，返回空数组
6. 只输出JSON，不要解释"""),
    ("user", """因果图谱：{graph_data}
角色档案：{characters}""")
])

def run(state: dict) -> dict:
    chain = prompt | llm
    response = chain.invoke({
        "graph_data": json.dumps(state["graph_data"], ensure_ascii=False),
        "characters": json.dumps(state["characters"], ensure_ascii=False)
    })
    result = json.loads(response.content)
    return {
        "branches": result.get("branches", []),
        "foreshadows": result.get("foreshadows", [])
    }
```

---

### Task 7: Validator Agent

**Files:**
- Rewrite: `backend/app/agents/validator.py`

- [ ] **Step 1: Implement validator agent with LLM**

```python
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL_NAME

llm = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    model=MODEL_NAME,
    temperature=0.2,
    model_kwargs={"response_format": {"type": "json_object"}}
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个叙事逻辑审查官。审查完整骨架，找出逻辑问题。

输出严格JSON，是一个问题数组，如无问题则返回空数组：
[
  {{
    "severity": "high/medium/low",
    "category": "因果断裂/OOC/伏笔悬空/规则违反/锚点缺失",
    "description": "问题的具体描述",
    "location": "涉及的事件ID或角色名",
    "suggestion": "修复建议"
  }}
]

审查维度：
1. 因果断裂：事件链是否有孤立节点？是否有节点只有入边没有出边（末端除外）？
2. OOC：角色行为是否和其 desire_topology/bottom_line 冲突？
3. 伏笔悬空：是否有伏笔没有对应的回收事件？
4. 规则违反：事件是否和世界规则的禁止项冲突？
5. 锚点缺失：用户指定的锚点事件是否都在图谱中？

注意：
- 只有明确的问题才报告，不要过度审查
- low 级别的问题可以忽略（轻微不一致）
- 只输出JSON数组，不要解释"""),
    ("user", """完整骨架数据：
{full_skeleton}""")
])

def run(state: dict) -> dict:
    full_skeleton = {
        "creative_doc": state["creative_doc"],
        "world_rules": state["world_rules"],
        "characters": state["characters"],
        "graph": state["graph_data"],
        "branches": state["branches"],
        "foreshadows": state["foreshadows"]
    }
    chain = prompt | llm
    response = chain.invoke({"full_skeleton": json.dumps(full_skeleton, ensure_ascii=False)})
    report = json.loads(response.content)
    if isinstance(report, dict) and "issues" in report:
        report = report["issues"]
    return {"validation_report": report}
```

---

### Task 8: NarrativeTool - Shared LLM Utilities

**Files:**
- Create: `backend/app/agents/base.py`

- [ ] **Step 1: Create shared agent helper to reduce boilerplate**

```python
import json
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL_NAME

_default_llm = None

def get_llm(temperature: float = 0.3) -> ChatOpenAI:
    global _default_llm
    if _default_llm is None:
        _default_llm = ChatOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            model=MODEL_NAME,
            temperature=temperature,
            model_kwargs={"response_format": {"type": "json_object"}}
        )
    return _default_llm

def run_agent(state: dict, prompt_template: ChatPromptTemplate, inputs: dict[str, Any], temperature: float = 0.3) -> dict:
    llm = get_llm(temperature)
    chain = prompt_template | llm
    response = chain.invoke(inputs)
    return json.loads(response.content)
```

---

### Task 9: Story Graph - Full Pipeline with Repair Loop

**Files:**
- Rewrite: `backend/app/graph/story_graph.py`

- [ ] **Step 1: Implement full graph with conditional edges**

```python
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

class StoryState(TypedDict):
    raw_input: dict
    creative_doc: dict
    world_rules: dict
    characters: List[dict]
    graph_data: dict
    branches: List[dict]
    foreshadows: List[dict]
    validation_report: List[dict]
    iteration: int

def build_story_graph():
    from app.agents.idea_parser import parse as parse_idea
    from app.agents.world_builder import run as build_world
    from app.agents.character_designer import run as build_characters
    from app.agents.plot_graph import run as build_plot
    from app.agents.branch_foreshadow import run as build_branches
    from app.agents.validator import run as validate

    workflow = StateGraph(StoryState)

    workflow.add_node("parse_idea", parse_idea)
    workflow.add_node("build_world", build_world)
    workflow.add_node("build_characters", build_characters)
    workflow.add_node("build_plot", build_plot)
    workflow.add_node("build_branches", build_branches)
    workflow.add_node("validate", validate)

    workflow.set_entry_point("parse_idea")
    workflow.add_edge("parse_idea", "build_world")
    workflow.add_edge("build_world", "build_characters")
    workflow.add_edge("build_characters", "build_plot")
    workflow.add_edge("build_plot", "build_branches")
    workflow.add_edge("build_branches", "validate")

    # Conditional: after validate, decide next step
    workflow.add_conditional_edges(
        "validate",
        router,
        {
            "end": END,
            "repair_world": "build_world",
            "repair_characters": "build_characters",
            "repair_plot": "build_plot",
        }
    )

    return workflow.compile()

def router(state: StoryState) -> str:
    if state["iteration"] >= 3:
        return "end"
    if not state["validation_report"] or len(state["validation_report"]) == 0:
        return "end"

    # Route to the most relevant agent based on first issue's category
    first = state["validation_report"][0]
    category = first.get("category", "")
    if "OOC" in category:
        return "repair_characters"
    elif "因果" in category or "情节" in category or "锚点" in category:
        return "repair_plot"
    elif "规则" in category or "世界观" in category:
        return "repair_world"
    else:
        return "repair_plot"
```

---

### Task 10: Generation Service - DB Persistence

**Files:**
- Rewrite: `backend/app/services/generation.py`

- [ ] **Step 1: Rewrite generation service to use DB**

```python
import logging
import json
from app.graph.story_graph import build_story_graph
from app.services.storage import (
    create_project, update_project_status, save_skeleton
)

logger = logging.getLogger(__name__)

async def run_generation(project_id: str, raw_input: dict, db_session_factory):
    try:
        async with db_session_factory() as db:
            graph = build_story_graph()
            initial_state = {
                "raw_input": raw_input,
                "creative_doc": {},
                "world_rules": {},
                "characters": [],
                "graph_data": {},
                "branches": [],
                "foreshadows": [],
                "validation_report": [],
                "iteration": 0
            }
            final_state = await graph.ainvoke(initial_state)

            skeleton = {
                "creative_doc": final_state.get("creative_doc"),
                "world_rules": final_state.get("world_rules"),
                "characters": final_state.get("characters"),
                "graph": final_state.get("graph_data"),
                "branches": final_state.get("branches"),
                "foreshadows": final_state.get("foreshadows")
            }
            validation_report = final_state.get("validation_report", [])

            await save_skeleton(db, project_id, skeleton, validation_report)
            await update_project_status(db, project_id, "completed")

            logger.info(f"Project {project_id} generated successfully. Issues: {len(validation_report)}")
    except Exception as e:
        logger.error(f"Generation failed for {project_id}: {str(e)}")
        try:
            async with db_session_factory() as db:
                await update_project_status(db, project_id, "failed")
        except Exception:
            pass
```

---

### Task 11: Routes - DB Integration and Validation Endpoint

**Files:**
- Modify: `backend/app/api/routes.py`

- [ ] **Step 1: Update routes to use DB instead of in-memory dict**

```python
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.generation import run_generation
from app.services.storage import create_project, get_project, get_latest_skeleton

router = APIRouter()

@router.post("/projects")
async def create_project_route(
    background_tasks: BackgroundTasks,
    raw_input: dict,
    db: AsyncSession = Depends(get_db)
):
    project = await create_project(db, raw_input)
    background_tasks.add_task(run_generation, project.id, raw_input, db.session_factory)
    return {
        "project_id": str(project.id),
        "status": project.status
    }

@router.get("/projects/{project_id}")
async def get_project_route(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    project = await get_project(db, project_id)
    if not project:
        return {"error": "Project not found"}
    sk = await get_latest_skeleton(db, project_id)
    return {
        "project_id": str(project.id),
        "status": project.status,
        "skeleton": sk.skeleton if sk else None,
        "validation_report": sk.validation_report if sk else None
    }

@router.get("/projects/{project_id}/skeleton")
async def get_skeleton_route(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    sk = await get_latest_skeleton(db, project_id)
    if not sk:
        return {"error": "No skeleton found"}
    return {
        "version": sk.version,
        "skeleton": sk.skeleton,
        "validation_report": sk.validation_report
    }
```

---

### Task 12: Main.py - Database Initialization on Startup

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add lifecycle event for DB init**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import router
from app.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Story Forge", version="0.1.0", lifespan=lifespan)
app.include_router(router)

@app.get("/")
async def root():
    return {"message": "Story Forge API is running"}
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|---|---|
| World Builder Agent (world_rules) | Task 3 |
| Character Designer Agent (characters) | Task 4 |
| Plot Graph Agent (graph_data) | Task 5 |
| Branch & Foreshadow Agent (branches, foreshadows) | Task 6 |
| Validator Agent (validation_report) | Task 7 |
| Conditional repair loop (max 3 iterations) | Task 9 |
| PostgreSQL persistence | Tasks 1, 2, 10 |
| API endpoints (POST/GET projects, GET skeleton) | Task 11 |
| Error handling | Task 10 |
| DB init on startup | Task 12 |
| Shared LLM utilities | Task 8 |

No gaps found.
