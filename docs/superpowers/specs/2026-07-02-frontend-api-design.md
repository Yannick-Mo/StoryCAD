# Story-Forge 前端与 API 扩展设计

## 定位

为 Phase 1 生成的故事骨架提供可视化编辑工作台，以及支持增量编辑的 API 端点。

---

## 一、整体架构

```
                     Vite Dev Server (:5173)
                           │
                    ┌──────┴──────┐
                    │  React App  │
                    │  Dock View  │
                    └──────┬──────┘
                           │ fetch /api
                    ┌──────┴──────┐
                    │  FastAPI    │
                    │  (:8000)    │
                    └──────┬──────┘
                    ┌──────┴──────┐
                    │ PostgreSQL  │
                    └─────────────┘
```

- 前端 Vite dev server 通过 docker 运行，代理 `/api` 到后端
- 后端复用现有 FastAPI 容器，新增端点
- 无 WebSocket（阶段三），前端轮询 GET /projects/{id}

---

## 二、布局方案：Dock Layout

采用类似 VSCode 的可拖拽面板布局。

### 默认布局

```
┌──────────────────────────────────────────────┐
│  导航栏: 项目名称 │ 保存 │ 重新生成 │ 导出    │
├──────────────────┬───────────────────────────┤
│                  │                           │
│  情节图谱视图    │  右上面板 (标签切换)      │
│  (Cytoscape.js)  │  ┌───┬───┬───┬───┐      │
│                  │  │角 │世 │分 │校 │      │
│  画布            │  │色 │界 │支 │验 │      │
│  可拖拽/缩放     │  └───┴───┴───┴───┘      │
│                  │                           │
│  左侧（主区域）  │  右下面板 (属性编辑)      │
│                  │  选中节点的属性编辑表单    │
│  占 60% 宽度     │                           │
└──────────────────┴───────────────────────────┘
```

### 交互规则

- 面板可拖拽调整大小（react-resizable-panels）
- 右键面板可折叠/展开
- 每个面板可拖拽到其他位置
- 默认布局为预设，可重置
- 布局状态 localStorage 持久化

---

## 三、5 个视图详细设计

### 3.1 情节图谱视图 (PlotGraphView)

**组件:** `PlotGraphCanvas.tsx`, `GraphNodeForm.tsx`, `GraphEdgeForm.tsx`

- Cytoscape.js 画布，渲染事件节点和因果边
- 节点显示: 事件 ID、描述（截断）、情绪值（颜色渐变）
- 边类型: 实线(necessary)、虚线(possible)、点线(indirect)
- 交互：拖拽节点、点击选中、双击编辑
- 右键菜单：添加节点、添加边、删除

### 3.2 角色档案视图 (CharacterView)

**组件:** `CharacterList.tsx`, `CharacterEditor.tsx`, `RelationshipMatrix.tsx`

- 左侧角色列表（可增删）
- 右侧编辑表单：
  - 名称、成长弧线（textarea）
  - 欲望拓扑（三层：表层欲望/深层需求/核心恐惧）
  - 底线、弱点
  - 语言基因（可增删列表）
  - 关系矩阵（表格：每个维度 0-100 滑块）

### 3.3 世界观规则视图 (WorldRulesView)

**组件:** `WorldRulesList.tsx`, `RuleEditor.tsx`

- 规则列表，按分类分组
- 每条规则编辑：分类选择、描述、限制条件
- 背景历史（textarea）
- 禁止事件列表（可增删）

### 3.4 分支与伏笔视图 (BranchForeshadowView)

**组件:** `BranchTree.tsx`, `ForeshadowList.tsx`

- 分支路径可视化（树状/流程图）
- 每个分支显示分歧点 → 路径 → 汇合点
- 伏笔列表：ID、埋设点、内容、状态(pending/recycled)、计划回收区间

### 3.5 校验报告视图 (ValidationView)

**组件:** `ValidationReport.tsx`, `IssueCard.tsx`

- 按严重程度分组（high/medium/low 折叠组）
- 每个问题卡片：分类、描述、位置、建议
- "重新校验" 按钮 → 调用 POST /projects/{id}/validate

---

## 四、技术栈明细

| 层 | 选型 |
|----|------|
| 构建 | Vite 5 |
| 框架 | React 18 |
| 语言 | TypeScript |
| 样式 | Tailwind CSS 3 |
| 图谱 | Cytoscape.js + cytoscape-dagre |
| Dock 面板 | react-resizable-panels |
| 路由 | React Router 6 |
| HTTP | fetch (原生，无 axios) |
| 图标 | lucide-react |

---

## 五、组件树

```
App
├── Layout
│   ├── Navbar
│   │   ├── ProjectTitle
│   │   ├── SaveButton
│   │   ├── RegenerateButton
│   │   └── ExportMenu (JSON / Markdown)
│   └── DockLayout (react-resizable-panels)
│       ├── PlotGraphPanel (左, 60%)
│       │   └── PlotGraphCanvas (Cytoscape.js)
│       ├── RightTopPanel (右, 40%)
│       │   └── TabView
│       │       ├── CharacterTab
│       │       │   ├── CharacterList
│       │       │   └── CharacterEditor
│       │       │       └── RelationshipMatrix
│       │       ├── WorldRulesTab
│       │       │   └── WorldRulesEditor
│       │       ├── BranchForeshadowTab
│       │       │   ├── BranchTree
│       │       │   └── ForeshadowList
│       │       └── ValidationTab
│       │           └── ValidationReport
│       └── RightBottomPanel (属性编辑)
│           └── NodePropertyEditor
│
├── Pages
│   ├── ProjectListPage (主页, 列出已有项目)
│   └── ProjectPage (DockLayout 所在页)
│
└── Hooks
    ├── useProject (加载/轮询项目)
    ├── useSkeletonCRUD (保存骨架)
    └── useGraphInteractions (Cytoscape 事件)
```

---

## 六、API 扩展

### 新端点

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /projects | 列出所有项目（id, status, created_at） |
| DELETE | /projects/{id} | 删除项目 |
| PUT | /projects/{id}/skeleton | 全量更新骨架 |
| GET | /projects/{id}/skeleton/versions | 历史版本列表 |
| GET | /projects/{id}/skeleton/versions/{version} | 获取特定版本 |
| POST | /projects/{id}/graph/nodes | 添加事件节点 |
| PUT | /projects/{id}/graph/nodes/{node_id} | 编辑事件节点 |
| DELETE | /projects/{id}/graph/nodes/{node_id} | 删除事件节点 |
| POST | /projects/{id}/graph/edges | 添加因果边 |
| PUT | /projects/{id}/graph/edges/{edge_id} | 编辑因果边 |
| DELETE | /projects/{id}/graph/edges/{edge_id} | 删除因果边 |
| POST | /projects/{id}/characters | 添加角色 |
| PUT | /projects/{id}/characters/{name} | 编辑角色 |
| DELETE | /projects/{id}/characters/{name} | 删除角色 |
| GET | /projects/{id}/export/json | 导出 JSON |
| GET | /projects/{id}/export/markdown | 导出 Markdown 大纲 |

### 数据模型变化

骨架的节点/边需要可寻址 ID，现有 `evt_1` 格式保留，新增端点生成 `evt_N+1`。

### 版本管理

每次 PUT /skeleton 创建新版本。GET versions 返回 `{version, created_at}` 列表。

---

## 七、前端数据流

```
1. 路由 /projects/{id} → useProject 启动
2. useProject 轮询 GET /projects/{id} 直到 status === "completed"
3. 收到 skeleton JSON → 分发给各视图
4. 用户编辑 → 本地状态更新（乐观 UI）
5. 用户点击保存 → PUT /projects/{id}/skeleton → 创建新版本
6. 图谱视图的交互 → useGraphInteractions 同步本地 graph_data
```

### 状态管理

无 Redux，使用 React Context + useReducer：
- `ProjectContext` — 当前项目数据、加载状态
- `SkeletonContext` — 骨架 JSON 拆解为各视图可编辑的结构
- 每个视图独立管理自己的编辑状态，保存时合并提交

---

## 八、错误处理

- 后端 4xx → 显示 toast 错误消息
- 后端 5xx → 显示 "服务异常，请重试"，保留本地编辑不丢失
- 网络离线 → 检测 navigator.onLine，显示离线提示
- Cytoscape 渲染异常 → 降级显示 JSON 文本视图

---

## 九、不包含的范围（阶段三）

- WebSocket 实时协作
- PDF 导出
- RAG 知识库增强
- 推演沙盘
- 用户认证/多租户
- 骨架比较（diff 视图）
