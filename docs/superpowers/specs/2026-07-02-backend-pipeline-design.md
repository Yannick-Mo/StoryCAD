# Story-Forge 后端核心管线设计

## 定位

接收用户创意输入，通过多 Agent LLM 流水线生成结构化叙事骨架 JSON。

---

## 一、整体架构

```
用户输入 → POST /projects → BackgroundTasks → LangGraph 图 → 存储到 PostgreSQL → 返回 project_id
                                                                       ↓
                                                              前端轮询 GET /projects/{id}
```

### 技术栈

| 层次 | 选型 |
|------|------|
| Agent 编排 | LangGraph (StateGraph + 条件边) |
| LLM 调用 | LangChain ChatOpenAI + JSON mode |
| 主力模型 | deepseek-v4-flash (可配置) |
| 异步框架 | FastAPI + asyncio |
| 数据库 | PostgreSQL + asyncpg + SQLAlchemy 2.0 async |
| 缓存 | Redis (可选，暂不依赖) |

---

## 二、状态定义 (StoryState)

```python
class StoryState(TypedDict):
    raw_input: dict              # 原始用户输入
    creative_doc: dict           # 创意解析结果
    world_rules: dict            # 世界规则
    characters: List[dict]       # 角色档案列表
    graph_data: dict             # 事件节点 + 因果边
    branches: List[dict]         # 分支树
    foreshadows: List[dict]      # 伏笔列表
    validation_report: List[str] # 校验问题列表
    iteration: int               # 反思循环次数
```

---

## 三、Agent 设计

### 3.1 创意解析 Agent (已完成)

**文件**: `app/agents/idea_parser.py`
**输入**: `raw_input`
**输出**: `creative_doc` (core_conflict, implied_world_clues, character_seeds, structural_constraints, anchor_events)
**模型**: ChatOpenAI + JSON mode, temperature=0.3

### 3.2 世界观构建 Agent

**文件**: `app/agents/world_builder.py`
**输入**: `creative_doc`
**输出**: `world_rules` — 格式匹配 `domain.py` 的 `WorldRules`:
```json
{
  "rules": [{"category": "物理/魔法/社会", "description": "...", "limitation": "..."}],
  "history": "背景历史概要",
  "forbidden_events": ["禁止发生的事件列表"]
}
```
**设计要点**:
- 从 creative_doc 的 `implied_world_clues` 和 `structural_constraints` 推导世界规则
- 规则必须有明确的约束边界（limitation），不能空泛

### 3.3 角色全息 Agent

**文件**: `app/agents/character_designer.py`
**输入**: `creative_doc` + `world_rules`
**输出**: `characters` — 每个角色匹配 `domain.py` 的 `CharacterProfile`:
```json
[{
  "name": "...",
  "desire_topology": {"表层欲望": "...", "深层需求": "...", "核心恐惧": "..."},
  "bottom_line": "不可逾越的底线",
  "vulnerability": "可以被利用的弱点",
  "language_genes": ["典型台词1", "典型台词2", ...],
  "relationships": {"角色B": {"信任": 30, "威胁": 70, "吸引力": 20}},
  "growth_arc": "成长弧线描述"
}]
```
**设计要点**:
- creative_doc 的 `character_seeds` 作为角色核心输入
- 如果无角色种子，根据核心冲突自动生成 2-3 个角色
- 关系矩阵是双向的（A 对 B 和 B 对 A 可能不同）

### 3.4 情节图谱 Agent

**文件**: `app/agents/plot_graph.py`
**输入**: `world_rules` + `characters` + `creative_doc`
**输出**: `graph_data` — 匹配 `domain.py` 的 `PlotGraph`:
```json
{
  "nodes": [{"id": "evt_1", "description": "事件描述", "emotion_value": 75}],
  "edges": [{"source": "evt_1", "target": "evt_2", "type": "necessary"}]
}
```
**设计要点**:
- 必须嵌入 `anchor_events`（creative_doc 里的关键锚点）
- 因果类型: `necessary`(实线) / `possible`(虚线) / `indirect`(点线)
- 节点数控制在 8-15 个（MVP 规模）
- 情绪曲线要有起伏，不要平铺直叙

### 3.5 分支与伏笔 Agent

**文件**: `app/agents/branch_foreshadow.py`
**输入**: `graph_data` + `characters`
**输出**: `branches` + `foreshadows`
```json
{
  "branches": [{"divergence_point": "evt_3", "paths": [...], "convergence_point": "evt_8"}],
  "foreshadows": [{"id": "fs_1", "planted_at": "evt_2", "content": "...", "status": "pending"}]
}
```

### 3.6 一致性校验 Agent

**文件**: `app/agents/validator.py`
**输入**: 完整骨架（world_rules + characters + graph_data + branches + foreshadows）
**输出**: `validation_report` — 字符串列表，每个字符串描述一个问题
**校验维度**:
1. 因果断裂: 事件链是否有孤立节点或断裂
2. OOC: 角色行为是否违背其欲望/底线
3. 伏笔悬空: 是否有未设置回收点的伏笔
4. 规则违反: 事件是否违反世界规则的 forbidden_events
5. 锚点缺失: 用户指定的锚点是否都在图中

---

## 四、LangGraph 图流程

```python
parse_idea → build_world
           ↘ build_characters (可并行，但角色依赖世界观，实际串行)
                    ↓
              build_plot
                    ↓
         build_branches_foreshadows
                    ↓
              validate
                    ↓
           ┌─ [有问题?] ─→ repair_router ─→ (路由到对应 Agent) ─→ validate(iteration+1)
           │
           END (iteration >= 3 或无问题)
```

### 条件边逻辑

```
def should_validate(state):
    if state["iteration"] >= 3:
        return "end"
    if len(state["validation_report"]) == 0:
        return "end"
    return "repair"

def repair_router(state):
    # 从 validation_report 推断问题类型
    # 返回对应的 agent 节点名: "build_world" / "build_characters" / "build_plot"
```

---

## 五、数据库设计

### 表结构

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    raw_input JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE project_skeletons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    version INT DEFAULT 1,
    skeleton JSONB,
    validation_report JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### SQLAlchemy 异步模型

- `app/models/db.py`: 扩展 Base 为实际模型
- `app/services/storage.py`: 实现 save_skeleton / get_skeleton / create_project

---

## 六、API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | /projects | 创建项目 + 触发生成 |
| GET | /projects/{id} | 查询项目状态和最新骨架 |
| GET | /projects/{id}/skeleton | 获取最新骨架（和 /projects/{id} 一致） |
| POST | /projects/{id}/validate | 单独触发校验 |

---

## 七、文件结构变更

```
backend/app/
├── agents/
│   ├── idea_parser.py        # 已有 ✓
│   ├── world_builder.py      # 重写
│   ├── character_designer.py # 重写
│   ├── plot_graph.py         # 重写
│   ├── branch_foreshadow.py  # 重写
│   └── validator.py          # 重写
├── graph/
│   └── story_graph.py        # 重构为完整图
├── models/
│   ├── domain.py             # 已有 ✓
│   └── db.py                 # 重写为完整模型
├── services/
│   ├── generation.py         # 重构
│   └── storage.py            # 重写为真实DB操作
├── api/
│   └── routes.py             # 完善
├── config.py                 # 已有 ✓
└── main.py                   # 已有 ✓
```

---

## 八、错误处理

- Agent LLM 调用失败 → 记日志，在 validation_report 添加错误信息，不阻塞整条流水线
- JSON 解析失败 → 重试一次，再失败则标记为解析错误
- 数据库连接失败 → 抛出 500，前端显示 "生成失败，请重试"

---

## 九、不包含的范围（阶段二/三处理）

- 前端五个视图
- WebSocket 实时协作
- PDF 导出
- RAG 知识库增强
- 单个节点的编辑操作 API
- 推演沙盘
