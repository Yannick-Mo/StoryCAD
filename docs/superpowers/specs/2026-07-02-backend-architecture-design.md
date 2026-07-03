# StoryCAD 后端架构完整设计

基于 [设计.md](../../../../../../../C:/Users/GodPrograms/Desktop/设计.md) 的设计书，后端全面重写，采用 DDD 限界上下文架构。

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                   │
│  /projects  /analysis  /story  /characters  /validation  │
│  /export  + WebSocket 事件推送                            │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│               Orchestrator (总控调度)                     │
│  状态机驱动工作流 · Agent 调度 · 用户交互管理             │
│  每个阶段可中断，等待用户确认后再继续                      │
└────┬──────┬──────┬──────┬──────┬──────┬─────────────────┘
     │      │      │      │      │      │
┌────▼──┐┌─▼───┐┌─▼───┐┌─▼───┐┌─▼───┐┌▼──────────┐
│Analysis││Story││Char ││World││Valid││Export      │
│Bounded ││Bound││Boun ││Boun ││Boun ││Bounded     │
│Context ││Ctx  ││Ctx  ││Ctx  ││Ctx  ││Context     │
└────┬───┘└──┬──┘└──┬──┘└──┬──┘└──┬──┘└─────┬──────┘
     │       │      │      │      │         │
┌────▼───────▼──────▼──────▼──────▼─────────▼──────────┐
│            Storage Layer                               │
│  PostgreSQL (projects/versions/configs)                │
│  + Neo4j (knowledge graph: entities+relationships)     │
│  + Redis (task queue, cache, event pub/sub)            │
└────────────────────────────────────────────────────────┘
```

### 技术栈

| 层次 | 选型 |
|------|------|
| Web 框架 | FastAPI + uvicorn |
| 数据库 | PostgreSQL 15 + asyncpg |
| 知识图谱 | Neo4j 5 + python neo4j driver |
| 缓存/队列 | Redis 7 |
| AI 编排 | LangGraph + LangChain |
| LLM | 可配置（默认 DeepSeek，支持 GPT-4o/Claude 等 OpenAI 兼容 API）|
| 校验 | Pydantic v2 |
| 容器化 | Docker Compose |

---

## 二、限界上下文 (Bounded Contexts)

### 上下文清单

| 上下文 | 核心职责 | 核心数据 | 依赖 |
|--------|---------|---------|------|
| **project** | 项目 CRUD、状态、版本管理、配置 | Project, ProjectVersion, ProjectConfig | — |
| **analysis** | 输入解析、六维信息提取、缺失诊断 | CreativeDoc, NarrativeMetadata | knowledge_graph |
| **story** | 宏观结构（幕/转折点）、情节编排（章节/节拍）、伏笔/分支 | ActStructure, ChapterPlan, Foreshadow | knowledge_graph, character |
| **character** | 角色设计、欲望拓扑、人物弧光、关系矩阵 | CharacterProfile, Relationship | knowledge_graph |
| **world** | 世界观规则、历史、禁止事件 | WorldRules | knowledge_graph |
| **validation** | 三遍校验（逻辑/人物/节奏）、自动修复、联动修改 | ValidationReport, Issue | knowledge_graph, all |
| **export** | JSON/MD/Word/可视化数据导出 | — | story, character, world |
| **knowledge_graph** | Neo4j 实体关系管理、图谱查询、一致性检测 | Entity, Relation | — |
| **orchestrator** | 工作流状态机、Agent 调度、用户交互循环 | WorkflowState | all |

### 跨上下文通信规则

- 每个上下文只通过 Repository 接口访问数据
- 上下文之间通过 Orchestrator 调度协作，不直接调用
- 共享数据模型定义在 `shared/` 层
- 依赖方向：下层不依赖上层

---

## 三、数据模型

### 3.1 PostgreSQL 模型

```
┌──────────────────────┐       ┌────────────────────────────┐
│       projects       │       │    project_versions        │
├──────────────────────┤       ├────────────────────────────┤
│ id            UUID   │──┐    │ id           UUID          │
│ title         str    │  │    │ project_id   UUID (FK)     │
│ description   text   │  │    │ version      int           │
│ genre         str    │  │    │ snapshot     JSONB         │
│ status        str    │  │    │ created_at   timestamptz   │
│ workflow_stage str   │  │    │ message      str           │
│ created_at    ts     │  ├────│                              │
│ updated_at    ts     │  │    └────────────────────────────┘
└──────────────────────┘  │
                          │    ┌────────────────────────────┐
                          │    │    project_configs         │
                          │    ├────────────────────────────┤
                          └────│ project_id   UUID (FK)     │
                               │ total_words  int           │
                               │ template_type str          │
                               │ target_audience str        │
                               │ created_at   timestamptz   │
                               └────────────────────────────┘
```

### 3.2 Neo4j 知识图谱模型

**节点标签:**

| 标签 | 属性 |
|------|------|
| `:Character` | `id`, `name`, `desire_topology` (JSON), `bottom_line`, `vulnerability`, `language_genes` ([]), `growth_arc`, `project_id` |
| `:Event` | `id`, `description`, `emotion_value` (0-100), `act`, `chapter`, `act_type` (plot_point/inciting_incident/midpoint/dark_night/climax), `project_id` |
| `:Chapter` | `id`, `number`, `title`, `core_event`, `hook`, `word_count`, `project_id` |
| `:Act` | `id`, `number`, `name`, `word_count`, `end_chapter`, `key_event`, `project_id` |
| `:Foreshadow` | `id`, `content`, `status` (pending/recycled/abandoned), `planted_at`, `planned_recycle_interval`, `project_id` |
| `:Theme` | `id`, `name`, `description`, `project_id` |
| `:Setting` | `id`, `name`, `description`, `rules` (JSON), `history`, `forbidden_events` ([]), `project_id` |

**关系类型:**

| 关系 | 起点 | 终点 | 属性 |
|------|------|------|------|
| `[:ACTED_IN]` | Character | Event | `role`: protagonist/antagonist/supporting |
| `[:CAUSES]` | Event | Event | `type`: necessary/possible/indirect |
| `[:HAS_FORESHAW]` | Event | Foreshadow | — |
| `[:RESOLVED_AT]` | Foreshadow | Event | — |
| `[:RELATES_TO]` | Character | Character | `trust`: 0-100, `threat`: 0-100, `attraction`: 0-100 |
| `[:BELONGS_TO]` | Event | Chapter | — |
| `[:PART_OF]` | Chapter | Act | — |
| `[:THEMATIZES]` | Event | Theme | — |
| `[:SET_IN]` | Event/Character | Setting | — |

### 3.3 核心数据结构

```python
# 六维叙事元数据 (analysis 上下文产出)
class NarrativeMetadata(BaseModel):
    # 一级：刚性锚点
    core_high_concept: str          # 核心高概念
    protagonist_identity: str       # 主角身份与核心执念
    core_conflict: str              # 主线目标+核心阻碍
    non_negotiable_events: list[str] # 用户明确"必须保留"的事件
    tone_and_length: str            # 作品调性与篇幅
    # 二级：骨架信息
    world_genre: str                # 世界观基础规则
    main_characters: list[dict]     # 主要人物身份/立场/动机
    core_relationships: list[dict]  # 人物间核心关系
    # 三级：填充信息
    landmark_scenes: list[str]      # 标志性名场面
    subplot_hints: list[str]        # 支线线索
    style_details: str              # 风格细节
    # 诊断
    missing_diagnosis: list[dict]   # 缺失项诊断 [{field, severity, suggestion}]

# 宏观结构 (story 上下文产出)
class ActStructure(BaseModel):
    acts: list[Act]                 # 四幕
    turning_points: dict            # 四大转折点位置
    word_count_distribution: dict   # 字数分配

class ChapterPlan(BaseModel):
    chapters: list[Chapter]         # 分章节拍表
    suspense_chain: list[Hook]      # 悬念钩子链

# 校验报告
class ValidationReport(BaseModel):
    round: int                      # 第几轮校验
    logic_issues: list[Issue]       # 逻辑问题
    character_issues: list[Issue]   # 人物问题
    pacing_issues: list[Issue]      # 节奏问题
    affected_entities: list[str]    # 联动修改影响的实体 ID
```

---

## 四、Agent 体系

### 4.1 Orchestrator 工作流状态机

设计文档的 6 阶段流程映射为状态机：

```
INIT → ANALYSIS → CONFIRM_CORE → STRUCTURE → PLOT → VALIDATE → EXPORT
  │                    │            │         │       │
  └──→ [用户输入]      │            │         │       └──→ [有问题] ──→ REPAIR
                       │            │         │                 │
                       └──→ [用户确认基石卡]   │                 └──→ [用户决策]
                                              │
                                  ┌───────────┘
                                  │
                      ┌───────────▼───────────┐
                      │  Agent                 │
                      │  LangGraph 管线        │
                      │  (生成骨架)            │
                      └───────────────────────┘
```

状态定义：

```python
class WorkflowStage(str, Enum):
    INIT = "init"
    ANALYSIS = "analysis"
    CONFIRM_CORE = "confirm_core"    # 等待用户确认基石卡
    STRUCTURE = "structure"          # 等待用户确认结构
    PLOT = "plot"                    # 等待用户确认章节
    VALIDATE = "validate"            # 等待用户处理校验报告
    REPAIR = "repair"                # 联动修改中
    EXPORT = "export"
    COMPLETED = "completed"
    FAILED = "failed"
```

每个阶段可暂停等待用户确认，Orchestrator 维护完整 `WorkflowState`：

```python
class WorkflowState(BaseModel):
    project_id: uuid.UUID
    stage: WorkflowStage
    data: dict                      # 跨阶段共享数据
    pending_confirmations: list[str] # 待用户确认的事项
    error_log: list[dict]           # 错误日志
```

### 4.2 统一 Agent 接口

```python
class AgentContext(BaseModel):
    project_id: uuid.UUID
    input_data: dict                # Agent 输入
    workflow_state: WorkflowState   # 当前工作流状态
    knowledge_graph: KnowledgeGraphService

class AgentResult(BaseModel):
    success: bool
    output_data: dict
    pending_confirmations: list[str]  # 需要用户确认的问题
    affected_entities: list[str]      # 被修改的图谱实体

class BaseAgent(ABC):
    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResult: ...
```

### 4.3 Agent 列表

| Agent | 职责 | 输入 | 输出 | 方法论文内化 |
|-------|------|------|------|------------|
| **Analysis** | 六维信息提取 + 缺失诊断 | 用户原始输入 | NarrativeMetadata | 六维信息提取模型 |
| **Soul Architect** | 生成故事脊椎/核心命题/人物弧光 | NarrativeMetadata | Logline, Theme, CharacterProfiles | 创意补全师方法论 |
| **Structure Designer** | 四幕结构/字数分配/转折点 | NarrativeMetadata, Characters | ActStructure | 参数化结构分配 |
| **Plot Planner** | 分节拍表/悬念链/伏笔 | ActStructure, Characters | ChapterPlan, Foreshadows | 反向追问法 + 悬念链设计 |
| **Validator** | 三轮校验/联动修改 | 完整骨架 | ValidationReport | 逻辑/人物/节奏三轮校验 |
| **Knowledge Keeper** | 模板/规则管理（非生成类） | — | — | — |

### 4.4 LangGraph 管线

纯 AI 生成步骤采用 LangGraph 编排：

```
analysis → soul_architect → structure → plot_planner → validate
                                                              │
                    ┌─────────────────────────────────────────┘
                    ▼ (有 high 级问题)
              repair_router → 路由到对应 Agent 修复
                    │
                    ▼ (通过)
                  export
```

其中 LangGraph 的 `StateGraph` 状态传递与 Orchestrator 的 `WorkflowState` 打通：Orchestrator 生成初始状态 → LangGraph 执行 → 结果写回 Orchestrator。

---

## 五、API 接口

按限界上下文分组的 RESTful API：

### Projects
```
POST   /api/projects                           # 创建项目
GET    /api/projects?page=&size=               # 项目列表
GET    /api/projects/{id}                      # 项目详情 + 当前状态 + 工作流阶段
PATCH  /api/projects/{id}                      # 更新配置
DELETE /api/projects/{id}                      # 删除项目
GET    /api/projects/{id}/versions             # 版本历史
GET    /api/projects/{id}/versions/{v}         # 特定版本
```

### Analysis
```
POST   /api/projects/{id}/analysis             # 提交输入，触发六维解析
GET    /api/projects/{id}/analysis             # 获取解析结果 + 缺失诊断
POST   /api/projects/{id}/analysis/confirm     # 确认基石卡
```

### Story Structure
```
GET    /api/projects/{id}/structure            # 获取幕结构
PUT    /api/projects/{id}/structure            # 手动调整幕结构
POST   /api/projects/{id}/structure/generate   # AI 生成宏观结构
GET    /api/projects/{id}/chapters             # 获取全章节拍表
PUT    /api/projects/{id}/chapters/{ch}        # 编辑单章
POST   /api/projects/{id}/chapters/generate    # AI 生成章节拍表
```

### Characters
```
GET    /api/projects/{id}/characters           # 角色列表
POST   /api/projects/{id}/characters           # 添加角色
GET    /api/projects/{id}/characters/{name}    # 角色详情
PUT    /api/projects/{id}/characters/{name}    # 编辑角色
DELETE /api/projects/{id}/characters/{name}    # 删除角色
PUT    /api/projects/{id}/characters/{name}/relationships  # 关系矩阵
```

### World
```
GET    /api/projects/{id}/world                # 世界观规则
PUT    /api/projects/{id}/world                # 更新规则
POST   /api/projects/{id}/world/generate       # AI 生成世界观
```

### Knowledge Graph
```
GET    /api/projects/{id}/graph/entities       # 查询实体列表
GET    /api/projects/{id}/graph/entities/{eid} # 实体详情 + 关系
GET    /api/projects/{id}/graph/relationships  # 查询关系
POST   /api/projects/{id}/graph/query          # 图谱查询
```

### Validation
```
POST   /api/projects/{id}/validate             # 触发全局校验
GET    /api/projects/{id}/validate/report      # 最新校验报告
POST   /api/projects/{id}/validate/repair      # 联动修改
```

### Export
```
GET    /api/projects/{id}/export/json          # JSON
GET    /api/projects/{id}/export/markdown      # Markdown
GET    /api/projects/{id}/export/word          # Word (.docx)
GET    /api/projects/{id}/export/visual        # 可视化数据
```

### Orchestration
```
GET    /api/projects/{id}/workflow             # 工作流状态
POST   /api/projects/{id}/workflow/next        # 推进到下一步
POST   /api/projects/{id}/workflow/pause       # 暂停
POST   /api/projects/{id}/workflow/resume      # 恢复
POST   /api/projects/{id}/workflow/skip        # 跳过阶段
```

---

## 六、项目文件结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 入口
│   ├── config.py                  # 全局配置
│   ├── database.py                # PostgreSQL + Neo4j + Redis 连接
│   │
│   ├── api/                       # API 路由定义
│   │   ├── __init__.py
│   │   ├── deps.py                # 依赖注入（session, kg, etc.）
│   │   ├── routes_project.py
│   │   ├── routes_analysis.py
│   │   ├── routes_story.py
│   │   ├── routes_character.py
│   │   ├── routes_world.py
│   │   ├── routes_knowledge_graph.py
│   │   ├── routes_validation.py
│   │   ├── routes_export.py
│   │   └── routes_orchestrator.py
│   │
│   ├── shared/                    # 共享层
│   │   ├── __init__.py
│   │   ├── models.py              # 跨上下文的通用模型
│   │   ├── errors.py              # 自定义错误类型
│   │   └── utils.py
│   │
│   ├── project/                   # project 限界上下文
│   │   ├── __init__.py
│   │   ├── models.py              # ORM 模型
│   │   ├── repository.py          # 数据访问
│   │   └── service.py             # 业务逻辑
│   │
│   ├── analysis/                  # analysis 限界上下文
│   │   ├── __init__.py
│   │   ├── models.py              # 六维元数据模型
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── agent.py               # Analysis Agent
│   │
│   ├── story/                     # story 限界上下文
│   │   ├── __init__.py
│   │   ├── models.py              # ActStructure, ChapterPlan, Foreshadow
│   │   ├── repository.py
│   │   ├── service.py
│   │   ├── agent_structure.py     # Structure Designer Agent
│   │   └── agent_plot.py          # Plot Planner Agent
│   │
│   ├── character/                 # character 限界上下文
│   │   ├── __init__.py
│   │   ├── models.py              # CharacterProfile, Relationship
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── agent.py               # Soul Architect Agent (角色部分)
│   │
│   ├── world/                     # world 限界上下文
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── agent.py               # World Builder Agent
│   │
│   ├── validation/                # validation 限界上下文
│   │   ├── __init__.py
│   │   ├── models.py              # ValidationReport, Issue
│   │   ├── repository.py
│   │   ├── service.py             # 校验 + 联动修改
│   │   └── agent.py               # Validator Agent
│   │
│   ├── export/                    # export 限界上下文
│   │   ├── __init__.py
│   │   ├── service.py
│   │   └── templates/             # 导出模板
│   │
│   ├── knowledge_graph/           # knowledge_graph 限界上下文
│   │   ├── __init__.py
│   │   ├── models.py              # 实体/关系 Python 模型
│   │   ├── repository.py          # Neo4j 数据访问
│   │   └── service.py             # 图谱查询/操作
│   │
│   ├── orchestrator/              # 总控调度
│   │   ├── __init__.py
│   │   ├── models.py              # WorkflowState
│   │   ├── state_machine.py       # 状态机
│   │   ├── dispatcher.py          # Agent 调度
│   │   └── langgraph_pipeline.py  # LangGraph 管线定义
│   │
│   └── agents/                    # Agent 基类 + 工具
│       ├── __init__.py
│       ├── base.py                # BaseAgent, AgentContext, AgentResult
│       ├── llm.py                 # LLM 工厂（多 Provider）
│       └── prompts/               # Prompt 模板目录
│           ├── analysis.txt
│           ├── soul_architect.txt
│           ├── structure.txt
│           ├── plot_planner.txt
│           └── validator.txt
│
├── tests/
│   ├── conftest.py
│   ├── test_project/
│   ├── test_analysis/
│   ├── test_story/
│   ├── test_character/
│   ├── test_world/
│   ├── test_validation/
│   ├── test_knowledge_graph/
│   ├── test_orchestrator/
│   └── test_api/
│
├── Dockerfile
├── docker-compose.yml              # 扩展: +neo4j, +redis
├── requirements.txt
└── pyproject.toml
```

---

## 七、错误处理

| 错误类型 | 处理方式 | HTTP 状态码 |
|---------|---------|------------|
| LLM 调用失败 | 重试 2 次，日志记录，workflow 标记 failed | — |
| JSON 解析失败 | 重试 1 次，不同 temperature | — |
| Neo4j 不可用 | 降级：缓存查询结果；写操作报 503 | 503 |
| PostgreSQL 连接失败 | 重试 3 次，指数退避 | 500 |
| 输入验证失败 | 返回详细字段错误 | 422 |
| 项目不存在 | — | 404 |
| 工作流冲突 | 返回当前阶段，提示用户 | 409 |

所有 Agent 错误汇总到 `WorkflowState.error_log`，前端可通过 GET /workflow 查看。

---

## 八、docker-compose 扩展

```yaml
services:
  db:       # PostgreSQL (已有)
  redis:    # Redis (已有)
  neo4j:    # 新增
    image: neo4j:5
    ports:
      - "7687:7687"   # Bolt
      - "7474:7474"   # Browser
    environment:
      NEO4J_AUTH: neo4j/password
    volumes:
      - neo4j_data:/data
  backend:  # FastAPI (已有，扩展依赖)
  frontend: # Vite (已有)
```

---

## 九、不包含的范围（后续阶段）

- 用户认证/多租户
- WebSocket 实时协作
- PDF 导出
- 骨架差异对比视图
- 推演沙盘
- 叙事节奏热力图前端组件
- 无限画布交互
