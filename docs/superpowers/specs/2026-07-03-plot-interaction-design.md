# 情节幕布交互设计：节点/边编辑 + 顺序管理

## 概述

为情节幕布（Plot Canvas）增加完整的节点和边编辑能力，支持创建/删除幕、章节、连线，以及基于时序边的章节自动排序。

## 边类型系统

### 两种边

| 类型 | 视觉 | 语义 | 影响内容顺序 |
|------|------|------|:---:|
| 时序边 | 琥珀色粗线 3px，箭头 | 阅读/播放顺序 | ✅ |
| 关系边 | 灰色虚线 1.5px，类型标签 | 因果/照应/人物/主题 | ❌ |

### 数据模型

```typescript
type EdgeType = 'timeline' | 'causal' | 'foreshadow' | 'character' | 'theme'

interface ChapterEdge {
  id: string
  sourceId: string
  targetId: string
  type: EdgeType
  label?: string
}
```

### 创建规则
- 默认从手柄拖拽创建时序边（琥珀色）
- 创建后可通过右键/边属性面板修改类型
- 时序边：每个章节最多一个前驱（入边），允许多个后继（出边）→ 分支，但当前导出只走主链
- 关系边：不限制入边/出边数量
- 时序边不能形成环路 → 操作时校验，弹警告阻止

### 章节排序规则
- 按时序边做拓扑排序确定线性顺序
- 游离节点（无时序边）排在末尾，按幕内原始顺序
- 重连/删除/创建时序边后即时重算
- 节点左上角显示序号 `① ② ③...`
- 导出/预览遵循时序边顺序

## 操作入口

### 工具栏（画布顶部浮动栏）

```
[＋幕] [＋章] [✕删除] [——连线筛选] [◉ 重新布局] [☰ 导出]
```

| 按钮 | 可用条件 |
|------|----------|
| ＋幕 | 始终可用 |
| ＋章 | 有幕被选中时 |
| ✕删除 | 有节点/边被选中时 |
| 连线筛选 | 始终可用（显示全部/仅时序/仅关系） |
| 重新布局 | 始终可用（Dagre 布局） |

### 右键菜单

| 位置 | 菜单项 |
|------|--------|
| 画布空白 | 添加幕 / 重新布局 |
| 幕组 | 添加章节 / 重命名 / 删除幕 / 修改颜色 |
| 章节节点 | 编辑内容 / 删除 |
| 边 | 修改类型 / 删除 |

### 快捷键
- `Delete` / `Backspace` → 删除选中节点/边
- 点击边 → 选中；拖拽手柄 → 重连

## 操作流程

### 创建幕
右键画布空白 →「添加幕」→ 在底部生成新 Act，自动命名"第 N 幕"，随机颜色

### 创建章节
右键幕内部 →「添加章节」→ 在该幕内生成新 Chapter，自动命名"第 N 章"
或：选中幕 → 工具栏「＋章」

### 创建时序边
从章节底部手柄拖出 → 连到目标章节 → 自动创建时序边
若目标已有入边 → 原入边被替换

### 创建关系边
默认拖拽创建的是时序边 → 点击边 → 右侧面板修改类型为关系类型

### 重连
点击时序边 → 两端出现手柄 → 拖拽到新目标/源 → 重连 → 顺序重算

### 删除
- 选中节点 → 按 Delete → 删除节点及其所有边
- 选中边 → 按 Delete → 仅删除边
- 删除幕 → 删除幕内所有章节和边

## 数据层设计

```typescript
interface EditorActions {
  addAct(name?: string): Act
  addChapter(actId: string, beforeChapterId?: string): Chapter
  deleteAct(actId: string): void
  deleteChapter(chapterId: string): void
  addEdge(sourceId: string, targetId: string, type: EdgeType): ChapterEdge | null
  deleteEdge(edgeId: string): void
  changeEdgeType(edgeId: string, newType: EdgeType): void
  reconnectEdge(edgeId: string, newSource?: string, newTarget?: string): void
}
```

当前直接操作 `MOCK_DATA`，接口签名与未来 API 调用一致。

## 不涉及
- 后端 API
- 其他 canvas 视图（人物/因果/节奏/主题）
- 全局设定
- 导出格式扩展（已有 TXT 导出）
