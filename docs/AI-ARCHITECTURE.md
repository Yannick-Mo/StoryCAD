# StoryCAD AI 系统架构设计 v2.0

> 设计日期：2026-07-07
> 覆盖范围：SuperAgent、MCP、RAG、Skills、Consistency Engine、Rhythm Dashboard、Co-Writer Mode

---

## 一、总体架构分层

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│  ┌──────────┐  ┌───────────┐  ┌────────────────────┐   │
│  │ AiChat    │  │ Legacy UI │  │ CreateFromMaterial │   │
│  │ (新对话UI)│  │ (保留不改)│  │ (保留不改)         │   │
│  └─────┬────┘  └───────────┘  └────────────────────┘   │
└────────┼────────────────────────────────────────────────┘
         │ SSE Streaming / REST
┌────────┼────────────────────────────────────────────────┐
│  Backend (FastAPI)                                      │
│  ┌──────┴────────────────────────────────────────────┐  │
│  │  API 层 (routes_ai_v2.py + 保留现有 routes_ai.py)  │  │
│  └──────┬────────────────────────────────────────────┘  │
│         │                                              │
│  ┌──────┴────────────────────────────────────────────┐  │
│  │  MCP Server (app/mcp/server.py)                   │  │
│  │  LLM ←→ Tools ←→ Backend CRUD                    │  │
│  └──────┬────────────────────────────────────────────┘  │
│         │                                              │
│  ┌──────┴────────────────────────────────────────────┐  │
│  │  SuperAgent (app/agent/super_agent.py)            │  │
│  │  LangGraph 对话图 — 意图识别 → 工具调用 → 生成    │  │
│  ├──────────────────────────────────────────────────┤  │
│  │  Tool Layer (app/agent/tools/)                    │  │
│  │  ├─ read_project / write_scene / ...             │  │
│  │  ├─ call_sub_agent (goal/outline/writing)         │  │
│  │  ├─ consistency_check / rhythm_analyze            │  │
│  │  └─ search_knowledge (RAG)                        │  │
│  ├──────────────────────────────────────────────────┤  │
│  │  Skill Engine (app/knowledge/skill_engine.py)     │  │
│  │  └─ skills/: web_novel, romance, mystery, ...     │  │
│  ├──────────────────────────────────────────────────┤  │
│  │  RAG Engine (app/knowledge/rag.py)                │  │
│  │  └─ pgvector: chunks → embed → retrieve          │  │
│  ├──────────────────────────────────────────────────┤  │
│  │  Consistency Engine (app/agent/consistency/)      │  │
│  └──────────────────────────────────────────────────┘  │
│                         │                              │
│  ┌──────────────────────┴────────────────────────────┐  │
│  │  LLM Infrastructure (app/llm/)                    │  │
│  │  ├─ client.py: 重试/流式/结构化输出/FC            │  │
│  │  ├─ registry.py: 多模型注册                       │  │
│  │  └─ tracker.py: token + 成本追踪                  │  │
│  └──────────────────────────────────────────────────┘  │
│                         │                              │
│  ┌──────────────────────┴────────────────────────────┐  │
│  │  Data Layer (已有模型 + 新增)                      │  │
│  │  ├─ projects / acts / chapters / scenes (已有)    │  │
│  │  ├─ knowledge_chunks (新增 pgvector)               │  │
│  │  ├─ skill_definitions (新增)                      │  │
│  │  ├─ ai_conversations (新增)                       │  │
│  │  └─ consistency_logs (新增)                       │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 二、模块详细设计

### 模块 1：`app/llm/` — LLM 基础设施层（核心底座）

**所有上层模块只依赖此层，不直接调 httpx。**

```
app/llm/
├── __init__.py
├── client.py          # LLMClient v2 — 重试 + 流式 + function calling
├── registry.py        # 模型注册表，每个模型独立配置
├── tracker.py         # Token & 成本追踪
└── types.py           # Message, ToolCall, ToolDef 等共享类型
```

#### `client.py` 核心接口

```python
class LLMClient:
    async def chat(
        messages: list[Message],
        model: str | None = None,          # 默认用 registry 的 default
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,              # 新增：流式支持
        tools: list[ToolDef] | None = None,    # 新增：Function Calling
        tool_choice: str = "auto",
        response_format: type | None = None,   # 新增：结构化输出
    ) -> ChatResult:
        # 1. 重试策略 (指数退避，最多3次)
        # 2. 区分 streaming / non-streaming
        # 3. 调用 tracker 记录用量
        # 4. 返回 ChatResult(content, tool_calls, usage)
```

需要支持的额外能力：
- **流式输出** — SuperAgent 对话需要实时打字效果
- **Function Calling** — MCP/SuperAgent 工具调用的基础
- **多模型切换** — 不同任务用不同模型（分析用便宜模型，写作用好模型）
- **重试** — 生产环境 LLM API 不稳定

#### `registry.py` 设计

```python
LLM_MODELS = {
    "deepseek-chat": ModelDef(
        api_key="sk-...",
        base_url="https://api.deepseek.com/v1",
        supports_streaming=True,
        supports_fc=True,
        max_tokens=8192,
        cost_per_1k_input=0.0001,
        cost_per_1k_output=0.0002,
    ),
    "deepseek-reasoner": ModelDef(...),  # 用于复杂推理
}
```

每个模型可以配置不同的 key/endpoint，方便对接不同供应商。

---

### 模块 2：`app/knowledge/` — 知识与技能层

投入产出比最高的模块。RAG + Skills 系统都在这里。

```
app/knowledge/
├── __init__.py
├── models.py              # 数据库模型：KnowledgeChunk, SkillDefinition
├── embeddings.py          # 文本嵌入（调用 LLM embedding API）
├── vector_store.py        # pgvector CRUD 封装
├── rag.py                 # RAG 编排器：检索 → 重排序 → 注入
├── skill_engine.py        # Skill 引擎：加载/组合/激活
└── skills/                # 技能定义目录
    ├── __init__.py
    ├── web_novel.yaml
    ├── romance.yaml
    ├── mystery.yaml
    └── realism.yaml
```

#### RAG 流程

```
用户创建/编辑项目 → 获取 project.genre
         │
         ▼
  Skill Engine 激活对应技能
         │
         ├── 1. 从 skills/ 加载 prompt override
         ├── 2. 从 pgvector 检索相关知识片段
         │       query = f"{genre} 写作技巧 {current_context}"
         │       WHERE project_id IS NULL OR project_id = :pid
         └── 3. 注入到 LLM 调用的 system prompt
```

#### 数据库表 `knowledge_chunks`

```sql
CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(1536),
    source_type VARCHAR(50),         -- 'genre_tips' | 'writing_technique' | 'style_guide'
    genre VARCHAR(100),              -- 关联类型
    tags TEXT[],                     -- 标签
    project_id UUID NULL,            -- NULL=全局知识, 非NULL=项目私有知识
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops);
```

#### Skill 定义示例 (`web_novel.yaml`)

```yaml
name: 网络爽文写作
genre: web_novel
description: 适用于网络连载爽文的写作辅助风格
prompt_overrides:
  persona: |
    你是一位资深网络小说编辑，精通爽文的节奏控制和爽点设计。
    核心原则：每500-1000字设置一个小爽点，每章至少有一个大爽点。
    打脸要干脆利落，升级要层层递进。
  goal: "...专门的goal prompt覆盖..."
  writing: "...专门的writing prompt覆盖..."
rag_tags:
  - web_novel
  - face_slapping
  - power_system
  - cliffhanger
tools_enabled:
  - create_cliffhanger
  - setup_payoff
  - escalate_tension
```

**关键设计决策：** Skill 可以**叠加**。如果用户同时启用"网络爽文"和"悬疑"，Skill Engine 会合并两者的 prompt override 和 RAG tag。

---

### 模块 3：`app/agent/` — 智能体系统（重构）

核心变化：从"按 mode 路由"变为"对话式 SuperAgent"。

```
app/agent/
├── __init__.py
├── super_agent.py         # LangGraph 对话图 — 核心编排器
├── graph.py               # 图定义（节点 + 边）
├── state.py               # AgentState TypedDict
├── memory/                # 记忆系统
│   ├── __init__.py
│   ├── conversation.py    # 对话历史管理 (Redis)
│   └── project.py         # 项目级持久记忆
├── tools/                 # 工具集（每个工具 = MCP tool + agent tool）
│   ├── __init__.py
│   ├── base.py            # BaseTool 定义
│   ├── project_tools.py   # read/write project, chapter, scene
│   ├── character_tools.py # CRUD characters + relations
│   ├── agent_tools.py     # 调用子智能体 (call_goal/call_outline/...)
│   ├── analysis_tools.py  # consistency_check, rhythm_analyze
│   └── knowledge_tools.py # search_knowledge (调 RAG)
├── consistency/           # 一致性引擎
│   ├── __init__.py
│   ├── checker.py         # 检查角色/时间线/世界观一致性
│   └── models.py          # ConsistencyReport
├── agents/                # 保留现有子智能体（扩展）
│   ├── base.py            # (升级 BaseAgent 支持 Skill 注入)
│   ├── goal_agent.py      # (保留)
│   ├── outline_agent.py   # (保留)
│   ├── writing_agent.py   # (保留)
│   ├── character_agent.py # 新增：角色深度设计
│   └── plot_doctor.py     # 新增：情节诊断
├── project_creator/       # (保留，不改)
├── prompts/               # (保留，扩展)
│   ├── persona.yaml       # (升级支持 Skill 变量)
│   ├── goal.yaml          # (保留)
│   ├── outline.yaml       # (保留)
│   ├── writing.yaml       # (保留)
│   └── character.yaml     # 新增
├── context.py             # (保留并扩展)
├── orchestrator.py        # (保留，兼容旧 API)
└── schema.py              # (保留并扩展)
```

#### SuperAgent 的 LangGraph 图设计

```
                    ┌──────────┐
                    │  START   │
                    └────┬─────┘
                         │ 用户消息
                    ┌────▼─────┐
                    │ classify │ ← 意图分类节点
                    │ _intent  │
                    └────┬─────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
   ┌──────▼──────┐ ┌─────▼──────┐ ┌────▼─────┐
   │ 直接生成     │ │ 工具调用   │ │ 多步推理  │
   │ (simple_q)  │ │ (tool_call)│ │ (complex) │
   └──────┬──────┘ └─────┬──────┘ └────┬─────┘
          │              │             │
          │        ┌─────▼──────┐      │
          │        │ execute    │      │
          │        │ _tool      │      │
          │        └─────┬──────┘      │
          │              │             │
          └──────┬───────┴──────┬──────┘
                 │              │
          ┌──────▼──────┐ ┌─────▼──────┐
          │ 需要更多?   │ │ 生成回复   │
          │ (loop back) │ │ (generate) │
          └─────────────┘ └─────┬──────┘
                               │
                          ┌────▼─────┐
                          │   END    │
                          └──────────┘
```

#### AgentState (LangGraph state)

```python
class AgentState(TypedDict):
    # 项目上下文（每次请求加载一次）
    project_id: str | None
    project_context: dict      # 由 ContextBuilder 加载

    # 对话状态
    messages: list[Message]    # 当前对话历史
    current_intent: str        # classify_intent 的输出

    # 工具调用
    tool_calls: list[ToolCall]
    tool_results: list[ToolResult]

    # RAG/Skill
    active_skills: list[str]   # 项目启用的技能
    rag_context: list[str]     # RAG 检索到的知识片段

    # 中间结果
    sub_agent_results: dict    # 子智能体返回
    pending_actions: list[str]
```

---

### 模块 4：`app/mcp/` — MCP 服务器

MCP 不是替代 API，而是 API 的"AI 原生接口"。

```
app/mcp/
├── __init__.py
├── server.py          # FastMCP 服务器，注册所有工具
└── tools/             # MCP 工具定义
    ├── __init__.py
    ├── project.py     # read_project, update_project, ...
    ├── story.py       # read_chapter, create_scene, ...
    ├── character.py   # create_character, update_relation, ...
    └── analysis.py    # check_consistency, analyze_rhythm, ...
```

#### MCP 工具示例

```python
@mcp.tool()
async def create_scene(
    project_id: str,
    chapter_id: str,
    title: str,
    pov_character: str = "",
    setting: str = "",
    summary: str = "",
) -> dict:
    """在指定章节下创建一个新场景"""
    repo = StoryCADRepository(db)
    result = await repo.create_entity(ENTITY_MAP["scenes"], {
        "project_id": project_id,
        "chapter_id": chapter_id,
        "title": title,
        "pov_character": pov_character,
        "setting": setting,
        "summary": summary,
    })
    return result
```

#### 双重用途设计

每个工具函数同时是：
- MCP tool（供外部 MCP 客户端调用）
- Agent tool（供 SuperAgent 内部调用 — 复用同一函数）

这样 SuperAgent 可以用**完全相同的工具集**独立运行，也可以通过 MCP 被外部 AI 客户端（如 Claude Desktop）调用。

---

### 模块 5：新增数据库表

```sql
-- 知识库
CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(1536),
    source_type VARCHAR(50) NOT NULL,   -- 'genre_tips'|'writing_technique'|'style_guide'|'user_note'
    genre VARCHAR(100),
    tags TEXT[] DEFAULT '{}',
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,  -- NULL = 全局
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,        -- NULL = 系统
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Skill 定义（存在文件系统，这里只是缓存/索引）
CREATE TABLE skill_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    genre VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    config JSONB NOT NULL DEFAULT '{}',  -- 技能完整配置
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 项目启用的 skill
CREATE TABLE project_skills (
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    skill_name VARCHAR(100) REFERENCES skill_definitions(name),
    config_override JSONB DEFAULT '{}',
    sort_order INT DEFAULT 0,
    PRIMARY KEY (project_id, skill_name)
);

-- AI 对话记录
CREATE TABLE ai_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) DEFAULT '',
    messages JSONB NOT NULL DEFAULT '[]',  -- 完整对话历史
    token_usage JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 一致性检查日志
CREATE TABLE consistency_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    check_type VARCHAR(50) NOT NULL,      -- 'character'|'timeline'|'world'
    severity VARCHAR(20) NOT NULL,        -- 'error'|'warning'|'info'
    entity_type VARCHAR(50),
    entity_id UUID,
    description TEXT NOT NULL,
    suggestion TEXT,
    is_resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

### 模块 6：前端新增

```
frontend/src/
├── api/
│   ├── ai_v2.ts          # 新增：流式对话 API + SSE
│   ├── ai.ts             # (保留)
│   └── mcp.ts            # 新增：通过后端 MCP 桥接调用工具
│
├── pages/editor/
│   ├── modals/
│   │   ├── AiAssistModal.tsx   # (保留)
│   │   └── AiChatPanel.tsx     # 新增：SuperAgent 对话面板
│   └── views/
│       └── plot/
│           └── ChapterDetail.tsx  # (保留，在 AI 按钮旁加"AI 对话"入口)
```

#### AiChatPanel 设计要点

- 侧边栏浮动面板，类似 Claude 的对话界面
- SSE 流式打字输出
- 支持上下文感知（自动带上当前章节/场景信息）
- 显示中间步骤（如"正在分析第三章节奏…"）
- 结果可直接 Apply 到编辑器

---

## 三、实施路线图

### 阶段 0 — 基础加固（预估 1-2 天）

目标：建立 LLM 基础设施层，所有后续工作依赖此层。

```
文件变更：
  ［新增］ backend/app/llm/__init__.py
  ［新增］ backend/app/llm/types.py        — Message, ToolCall, ToolDef, ChatResult
  ［新增］ backend/app/llm/client.py       — LLMClient v2 (重试/流式/FC)
  ［新增］ backend/app/llm/registry.py     — 多模型注册表
  ［新增］ backend/app/llm/tracker.py      — Token 用量追踪
  ［修改］ backend/app/agent/client.py     — 改为委托给 app/llm/client.py
  ［修改］ backend/app/config.py           — 增加 llm_models 配置
  ［修改］ backend/requirements.txt        — 增加 pgvector 依赖
  ［新增］ backend/alembic/...             — 数据库迁移脚本（新增表）
```

**验收标准：**
- 现有 Agent（goal/outline/writing）走新 LLMClient 正常工作
- 流式调用可用（SSE 返回打字效果）
- 模型切换生效

---

### 阶段 1 — RAG + Skills（预估 2-3 天）

目标：让 AI 输出具备类型感知和风格控制能力。

```
文件变更：
  ［新增］ backend/app/knowledge/__init__.py
  ［新增］ backend/app/knowledge/models.py       — SQLAlchemy 模型
  ［新增］ backend/app/knowledge/embeddings.py   — 文本嵌入
  ［新增］ backend/app/knowledge/vector_store.py — pgvector 封装
  ［新增］ backend/app/knowledge/rag.py          — RAG 编排器
  ［新增］ backend/app/knowledge/skill_engine.py — Skill 引擎
  ［新增］ backend/app/knowledge/skills/web_novel.yaml
  ［新增］ backend/app/knowledge/skills/romance.yaml
  ［新增］ backend/app/knowledge/skills/mystery.yaml
  ［新增］ backend/app/knowledge/skills/realism.yaml
  ［修改］ backend/app/agent/agents/base.py      — 注入 RAG context + Skill
  ［修改］ backend/app/agent/context.py          — 携带 genre/skill 信息
```

**验收标准：**
- 不同类型项目调用 AI 得到风格不同的输出
- 在没有 Skill/RAG 时 AI 正常工作，有则自动增强
- 用户可在项目设置中启用/禁用 Skill

---

### 阶段 2 — SuperAgent（预估 3-4 天）

目标：从"按钮式 AI"变为"对话式 AI 伙伴"。

```
文件变更：
  ［新增］ backend/app/agent/super_agent.py     — LangGraph 主图
  ［新增］ backend/app/agent/graph.py           — 图节点定义
  ［新增］ backend/app/agent/state.py           — AgentState
  ［新增］ backend/app/agent/memory/conversation.py
  ［新增］ backend/app/agent/memory/project.py
  ［新增］ backend/app/agent/tools/base.py
  ［新增］ backend/app/agent/tools/project_tools.py
  ［新增］ backend/app/agent/tools/character_tools.py
  ［新增］ backend/app/agent/tools/agent_tools.py
  ［新增］ backend/app/agent/tools/analysis_tools.py
  ［新增］ backend/app/agent/tools/knowledge_tools.py
  ［新增］ backend/app/agent/agents/character_agent.py
  ［新增］ backend/app/agent/agents/plot_doctor.py
  ［新增］ backend/app/api/routes_ai_v2.py      — 对话端点 + SSE
  ［新增］ frontend/src/api/ai_v2.ts            — 对话 API 客户端
  ［新增］ frontend/src/pages/editor/modals/AiChatPanel.tsx

兼容：
  app/agent/orchestrator.py — 保留，旧 API 仍可用
  app/api/routes_ai.py      — 保留，旧端点不变
  frontend/src/pages/editor/modals/AiAssistModal.tsx — 保留
```

**验收标准：**
- 用户输入"帮我看看第三章有什么问题" → SuperAgent 自动分析并建议
- 用户输入"给主角加个童年阴影并加一场闪回戏" → SuperAgent 多步执行
- 对话历史持久化，跨 session 可恢复

---

### 阶段 3 — MCP（预估 1-2 天）

目标：开放工具集给外部 AI 客户端，同时内部 SuperAgent 复用同一套工具。

```
文件变更：
  ［新增］ backend/app/mcp/__init__.py
  ［新增］ backend/app/mcp/server.py           — MCP 服务器
  ［新增］ backend/app/mcp/tools/__init__.py
  ［新增］ backend/app/mcp/tools/project.py
  ［新增］ backend/app/mcp/tools/story.py
  ［新增］ backend/app/mcp/tools/character.py
  ［新增］ backend/app/mcp/tools/analysis.py
  ［新增］ frontend/src/api/mcp.ts             — 前端桥接

设计要点：
  tools/ 下的每个工具定义同时导出为 MCP tool 和 Agent tool
  MCP 服务器可运行在独立端口或挂载在 FastAPI 路径下
```

**验收标准：**
- Claude Desktop 等外部工具可通过 MCP 连接并操作项目
- SuperAgent 内部的工具调用与 MCP 工具是同一份代码

---

### 阶段 4 — 高级功能（按需实施，每项 1-3 天）

#### 4a. Consistency Engine

```python
# backend/app/agent/consistency/checker.py
class ConsistencyChecker:
    async def check_character(self, project_id) -> list[ConsistencyIssue]:
        # 1. RAG 检索所有角色描述
        # 2. LLM 对比不同章节中的角色表现
        # 3. 返回矛盾列表
        pass

    async def check_timeline(self, project_id) -> list[ConsistencyIssue]:
        # 检查时间线逻辑
        pass

    async def check_world_rules(self, project_id) -> list[ConsistencyIssue]:
        # 检查世界观规则一致性
        pass
```

#### 4b. Rhythm Dashboard 增强

- AI 自动标注节奏异常章节
- 对比同类作品的节奏模式
- 可视化显示"情绪曲线"、"信息密度"、"对话/描写比例"

#### 4c. Co-Writer Mode

不是"AI 生成你修改"，而是协作式对话：

```
用户："女主角要在这章做出一个关键选择"
AI："考虑到她的背景（孤儿院长大，极度缺爱），
     我认为有两个合理方向：
     1. 选择安全感（接受求婚）—— 符合性格但不够成长
     2. 选择独立（拒绝求婚）—— 更有弧光，但需要铺垫
     建议你在前三节加一些铺垫，让第二个选择更有说服力。"
```

#### 4d. 灵感热启动

- 根据用户选定的类型/风格，生成多个故事起点
- 提供"创作挑战"模式（限定条件创作）

---

## 四、关键设计原则

| 原则 | 说明 |
|------|------|
| **向后兼容** | 现有 `routes_ai.py` + `AiAssistModal` 完全不动。新功能走新路由新组件 |
| **工具复用** | 一个工具函数 = MCP tool + Agent tool，一写两用 |
| **Skill 组合性** | 多个 Skill 可叠加，prompt 自动合并，RAG tag 取并集 |
| **渐进增强** | 没有 Skill/RAG 时 LLM 也正常工作，有则自动增强 |
| **可观测性** | 所有 LLM 调用记录 token 用量、模型、耗时 |

---

## 五、依赖清单

### Python 依赖（新增）

```
pgvector>=0.2.0         # 向量数据库支持
openai>=1.0.0           # 统一 OpenAI 客户端（用于 embedding 等）
mcp>=1.0.0              # MCP 服务器框架（如果独立发布）
```

### 数据库依赖

- PostgreSQL 15+ with pgvector extension
- Redis 7+（对话记忆缓存）

### Docker Compose 变更

```yaml
services:
  db:
    image: pgvector/pgvector:pg15  # 从 postgres:15 改为 pgvector 镜像
    # ... 其余不变
```

---

## 六、文件变更汇总

```
全部文件变更清单：

backend/
├── app/
│   ├── llm/                          # ［新增］LLM 基础设施
│   │   ├── __init__.py
│   │   ├── types.py
│   │   ├── client.py
│   │   ├── registry.py
│   │   └── tracker.py
│   ├── knowledge/                    # ［新增］知识 + Skill 引擎
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   ├── rag.py
│   │   ├── skill_engine.py
│   │   └── skills/
│   │       ├── web_novel.yaml
│   │       ├── romance.yaml
│   │       ├── mystery.yaml
│   │       └── realism.yaml
│   ├── mcp/                          # ［新增］MCP 服务器
│   │   ├── __init__.py
│   │   ├── server.py
│   │   └── tools/
│   │       ├── project.py
│   │       ├── story.py
│   │       ├── character.py
│   │       └── analysis.py
│   ├── agent/
│   │   ├── super_agent.py            # ［新增］
│   │   ├── graph.py                  # ［新增］
│   │   ├── state.py                  # ［新增］
│   │   ├── memory/                   # ［新增］
│   │   │   ├── conversation.py
│   │   │   └── project.py
│   │   ├── tools/                    # ［新增］
│   │   │   ├── base.py
│   │   │   ├── project_tools.py
│   │   │   ├── character_tools.py
│   │   │   ├── agent_tools.py
│   │   │   ├── analysis_tools.py
│   │   │   └── knowledge_tools.py
│   │   ├── consistency/             # ［新增］
│   │   │   ├── checker.py
│   │   │   └── models.py
│   │   ├── agents/
│   │   │   ├── base.py              # ［修改］Skill 注入
│   │   │   ├── character_agent.py   # ［新增］
│   │   │   └── plot_doctor.py       # ［新增］
│   │   ├── client.py                # ［修改］委托 LLMClient v2
│   │   └── context.py               # ［修改］携带 genre/skill
│   ├── api/
│   │   ├── routes_ai_v2.py          # ［新增］对话端点
│   │   └── routes_ai.py             # ［保留］
│   └── config.py                    # ［修改］新增 llm_models 配置
├── alembic/                         # ［新增］迁移脚本
└── requirements.txt                 # ［修改］新增依赖

frontend/src/
├── api/
│   ├── ai_v2.ts                     # ［新增］
│   └── mcp.ts                       # ［新增］
└── pages/editor/modals/
    ├── AiAssistModal.tsx            # ［保留］
    └── AiChatPanel.tsx             # ［新增］

docker-compose.yml                   # ［修改］pgvector 镜像
```
