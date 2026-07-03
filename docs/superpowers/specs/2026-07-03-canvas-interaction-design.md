# StoryCAD 画布交互系统设计

## 概述

设计一套完整的画布交互系统，支持用户创建/编辑节点、连线、排序，并通过锁定机制保护已写内容。

## 核心原则

1. **右键优先** - 所有操作通过右键菜单触发，降低记忆负担
2. **锁定保护** - 有内容的章节自动锁定时序连线，防止误操作
3. **上下文感知** - 工具栏根据选中对象动态显示可用操作
4. **多入口覆盖** - 同一操作可通过右键、拖拽、工具栏等多种方式触发

## 数据模型

### 节点类型

```typescript
// 幕节点（容器）
interface Act {
  id: string
  name: string
  order: number
  color: string
}

// 章节节点（内容单元）
interface Chapter {
  id: string
  actId: string
  title: string
  goal: string
  wordCount: number  // 锁定判断依据
  status: 'draft' | 'revising' | 'final'
  scenes: Scene[]
}
```

### 连线类型

```typescript
type EdgeType = 'timeline' | 'causal' | 'foreshadow' | 'character' | 'theme'

interface ChapterEdge {
  id: string
  sourceId: string  // 章节 ID
  targetId: string  // 章节 ID
  type: EdgeType
  label?: string
}
```

### 选中状态

```typescript
interface SelectionState {
  type: 'act' | 'chapter' | 'edge' | null
  id: string | null
}
```

## 交互设计

### 1. 节点操作

| 操作 | 触发方式 | 效果 |
|------|----------|------|
| 选中 | 单击节点 | 高亮边框 + 工具栏显示对应操作 |
| 编辑标题 | 双击节点标题 | 内联编辑输入框 |
| 创建连线 | 从 Handle 拖拽到另一节点 | 创建时序主线（默认） |
| 自由拖拽 | 拖拽节点本体 | 在幕内移动位置 |
| 右键菜单 | 右键节点 | 弹出操作菜单 |

### 2. 连线操作

| 操作 | 触发方式 | 效果 |
|------|----------|------|
| 选中 | 单击连线 | 高亮 + 工具栏显示操作 |
| 重新连接 | 拖拽连线端点到新节点 | 更新连线（带锁定检查） |
| 删除 | 选中 + Delete 键 / 右键删除 | 直接删除（无确认） |
| 改类型 | 右键 → 类型菜单 / 属性面板下拉 | 切换时序/关系类型 |

### 3. 右键菜单

| 对象 | 菜单项 | 说明 |
|------|--------|------|
| 画布空白处 | 新建幕 | 在画布底部创建新幕 |
| 幕节点 | 新建章 | 在当前幕内创建新章节 |
| 幕节点 | 重命名 | 幕名称变为内联编辑输入框 |
| 幕节点 | 删除幕 | 弹窗确认后级联删除所有章节 |
| 章节节点 | 编辑目标 | 章节目标变为内联编辑输入框 |
| 章节节点 | 删除章 | 直接删除（无确认） |
| 章节节点 | 断开时序线 | 移除该章节的所有 incoming timeline edges |
| 连线 | 删除连线 | 直接删除（无确认） |
| 连线 | 改为时序 | 切换为 timeline 类型 |
| 连线 | 改为关系 | 切换为当前选中的关系类型 |

### 4. 工具栏动态响应

| 选中对象 | 工具栏显示 |
|----------|------------|
| 无选中 | ＋幕 / ＋章(禁用) / 布局 / 导出 |
| 选中幕 | ＋章 / 重命名 / 删除幕 / 布局 / 导出 |
| 选中章节 | 删除章 / 断开连线 / 布局 / 导出 |
| 选中连线 | 删除连线 / 改类型 / 布局 / 导出 |

## 锁定机制

### 规则

- `wordCount > 0` 的章节，其 **incoming timeline edges** 被锁定
- 锁定时的行为：
  - 连线端点不可拖拽重新连接
  - 右键菜单禁用"断开时序线"选项
  - 工具栏禁用"断开连线"按钮
- 关系线（causal/foreshadow/character/theme）不受锁定限制
- outgoing timeline edges 不受锁定限制（可以修改章节的下游连接）

### 锁定判断函数

```typescript
function isEdgeLocked(edge: ChapterEdge, chapters: Chapter[]): boolean {
  if (edge.type !== 'timeline') return false
  const target = chapters.find(c => c.id === edge.targetId)
  return target ? target.wordCount > 0 : false
}
```

### 视觉反馈

- 锁定连线显示 🔒 图标（连线中点）
- 锁定连线样式变为虚线 + 灰色
- 违反锁定时显示 toast 提示："该章节已有内容，时序已锁定"

### Toast 通知系统

```typescript
interface Toast {
  id: string
  message: string
  type: 'info' | 'warning' | 'error' | 'success'
  duration?: number  // 默认 3000ms
}
```

| 场景 | Toast 类型 | 消息 |
|------|------------|------|
| 锁定连线被修改 | warning | "该章节已有内容，时序已锁定" |
| 创建环路边 | error | "不能创建环路，操作已取消" |
| 删除幕成功 | success | "幕已删除" |
| 连线类型切换 | info | "已切换为关系线" |

### 导出顺序

- 按拓扑排序结果排列章节内容
- 锁定章节的顺序优先保证

## 状态管理

### Store 结构

```typescript
interface EditorState {
  data: EditorMockData
  selection: SelectionState

  // 节点操作
  addAct: (name?: string) => Act
  addChapter: (actId: string) => Chapter
  deleteAct: (actId: string) => void
  deleteChapter: (chapterId: string) => void

  // 选择操作
  selectNode: (type: 'act' | 'chapter', id: string) => void
  selectEdge: (edgeId: string) => void
  clearSelection: () => void

  // 连线操作（带锁定检查）
  addEdge: (sourceId: string, targetId: string, type?: EdgeType) => EdgeResult
  deleteEdge: (edgeId: string) => void
  reconnectEdge: (edgeId: string, newSource?: string, newTarget?: string) => void
  changeEdgeType: (edgeId: string, newType: EdgeType) => void
}
```

### 关键修复

1. **Stale 闭包** - 所有回调依赖完整
2. **State 变异** - 更新返回新对象，不直接变异
3. **节点同步** - `useEffect` 监听 data 变化，同步 React Flow 节点

## 视觉设计

### 选中状态

| 状态 | 视觉效果 |
|------|----------|
| 幕选中 | 琥珀色边框 + 发光阴影 |
| 章节选中 | 蓝色边框 + 发光阴影 |
| 连线选中 | 线条加粗 + 高亮颜色 |
| 连线锁定 | 🔒 图标 + 虚线样式 |

### 右键菜单样式

- 深色毛玻璃面板（`bg-gray-900/90 backdrop-blur-lg`）
- 圆角 + 阴影
- 图标 + 文字组合
- 分割线分组

### 拖拽反馈

- 半透明预览节点
- 智能对齐线（幕边界对齐）
- 目标节点高亮提示

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| 创建环路边 | alert 提示 + 操作取消 |
| 修改锁定连线 | toast 提示 + 操作忽略 |
| 删除幕 | 弹窗确认（级联删除所有章节） |
| 删除章节 | 直接删除（无确认） |
| 删除连线 | 直接删除（无确认） |

## 待实现功能

- [ ] 自动布局算法（Dagre）
- [ ] 撤销/重做
- [ ] 多选操作
- [ ] 复制/粘贴
- [ ] 连线标签编辑
- [ ] 节点分组嵌套
