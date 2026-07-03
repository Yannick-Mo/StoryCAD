# 情节幕布交互系统设计

## 概述

在情节幕布视图中引入完整的 CAD 式节点/边编辑交互：创建幕、章节、两种类型的边（时序/关系），删除/重连边并自动更新内容顺序。

## 边类型系统

### 两种边

| 类型 | 视觉 | 语义 | 影响内容顺序？ |
|------|------|------|:---:|
| 时序边 | 琥珀色粗线 3px + 箭头 | 阅读/播放顺序 | ✅ |
| 关系边 | 灰色虚线 1.5px + 类型标签 | 因果/照应/人物/主题 | ❌ |

### 创建方式

- **默认时序边**：拖拽手柄创建
- **关系边**：创建后点击边 → 右侧面板修改类型
- 右键边 → 「修改类型」快捷操作

### 数据模型

```typescript
interface ChapterEdge {
  id: string
  sourceId: string
  targetId: string
  type: 'timeline' | 'causal' | 'foreshadow' | 'character' | 'theme'
  label?: string
}
```

## 内容顺序

- 导出/预览按时序边拓扑排序
- 游离节点（无时序边）排在末尾，按幕内原始顺序
- 时序边形成环路时弹警告并阻止操作
- 重连后顺序即时更新 + 序号 badge 动画

## 操作交互

### 添加

| 操作 | 方式 |
|------|------|
| 添加幕 | 右键画布空白 → 添加幕 / 工具栏 ＋幕 |
| 添加章节 | 右键幕内部 → 添加章节 / 工具栏 ＋章（需选中幕） |
| 创建时序边 | 节点手柄拖拽到目标节点 |

### 删除

| 操作 | 方式 |
|------|------|
| 删除节点/边 | 选中 → Delete 键 / 右键 → 删除 |
| 删除章节 | 同时删除关联边 |
| 删除幕 | 同时删除幕内所有章节和边 |

### 修改

| 操作 | 方式 |
|------|------|
| 重连时序边 | 拖拽边端手柄到另一节点 |
| 修改边类型 | 选中 → 右侧面板下拉菜单 / 右键 → 修改类型 |
| 重命名幕/章 | 双击标题（后续扩展） |
| 修改幕颜色 | 右键 → 修改颜色 |

### 时序边约束

- 一个章节最多一条入边（单前驱）
- 时序边不允许成环
- 关系边无约束

## 工具栏

画布顶部浮动栏：

```
[＋幕] [＋章] [✕删除] [——连线筛选] [◉ 重新布局] [☰ 导出]
```

状态依赖：
- ＋章：仅当选中幕时可用
- ✕删除：仅当选中节点/边时可用
- ——连线：筛选显示全部/仅时序/仅关系
- ◉ 重新布局：Dagre 自动排列

## 右键菜单

| 位置 | 菜单项 |
|------|--------|
| 画布空白 | 添加幕 / 重新布局 |
| 幕组 | 添加章节 / 重命名 / 删除幕 / 修改颜色 |
| 章节节点 | 编辑内容 / 删除 |
| 边 | 修改类型 / 删除 |

## 数据层

```typescript
interface EditorActions {
  addAct(name?: string): Act
  addChapter(actId: string): Chapter
  deleteAct(actId: string): void
  deleteChapter(chapterId: string): void
  addEdge(sourceId: string, targetId: string, type: EdgeType): ChapterEdge | null
  deleteEdge(edgeId: string): void
  changeEdgeType(edgeId: string, newType: EdgeType): void
  reconnectEdge(edgeId: string, newSource?: string, newTarget?: string): void
}
```

当前直接操作 `MOCK_DATA`，后续接 API 时替换实现，接口签名不变。

## 不涉及

- 其他 canvas 视图（人物/因果/节奏/主题幕布）
- 导出格式（已有 TXT 导出）
- 后端 API
