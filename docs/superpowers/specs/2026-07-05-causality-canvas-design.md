# 因果幕布设计

## 概述

因果幕布（Causality Canvas）是一个只读分析工具，帮助作者理解故事中因果关系的结构。它结合两种因果数据——章节间的因果连线（`ChapterEdge.type='causal'`）和文本因果对（`Causality[]`）——以力导向图可视化呈现。

## 布局

主区域：力导向图 + 右侧因果文本卡片面板。

```
┌─────────────────────────────────┬──────────┐
│                                 │  因→果    │
│    力导向图                      │          │
│    ┌─┐     ┌─┐                 │ 密信被截  │
│    │章1│───→│章2│                │  →盟友猜忌 │
│    └─┘     └─┘    ┌─┐          │          │
│               ┌──→│章4│          │ 玉牌现世  │
│               │   └─┘          │  →灭门案重查│
│              ┌┘                │          │
│    ┌─┐     ┌─┐                 │ 内鬼泄密  │
│    │章3│───→│章5│                │  →行动失败 │
│    └─┘     └─┘                 │          │
│                                 │          │
└─────────────────────────────────┴──────────┘
```

## 数据源

### 章节节点

来源：`EditorMockData.chapters[]` 和 `acts[]`。

每个节点显示：
- 章节标题
- 所属幕的颜色标识（小圆点）
- 状态标识（草稿/修改中/已定稿）

### 因果连线

来源：`EditorMockData.edges[]` 中 `type === 'causal'` 的边。

视觉：
- 暖色实线（琥珀色 `#d4a373`），2px 粗
- 箭头指向效果端
- 可显示因果标签（如"因果"）

### 时序参考线

来源：`type === 'timeline'` 的边。

视觉：
- 浅灰色虚线 `#555`，1px 粗
- 低透明度（0.3）
- 提供故事时间顺序的参考背景

### 文本因果对

来源：`EditorMockData.causalities[]`

展示在右侧面板，每格一张卡片：
- `因：<cause>` → `果：<effect>`
- 灰色背景卡片，无交互

## 力导向布局

初始化时使用 d3-force 计算节点位置：

- `forceManyBody()`：节点间斥力，避免重叠
- `forceLink()`：因果连线牵引力，将相连节点拉近
- `forceLink(timeline)`：时序线弱牵引力，保持时间顺序的大致结构
- `forceCenter()`：将整个图保持在画布中心

仿真收敛后固定位置，后续用户可平移/缩放。

## 交互

| 操作 | 行为 |
|------|------|
| 平移 | 鼠标拖拽空白区域 |
| 缩放 | 滚轮缩放 |
| 点击章节节点 | 选中该章节，高亮其因果连线 |
| 右侧面板卡片 | 纯展示，悬停无交互 |

## 组件结构

```
CausalityCanvas (main)
├── ReactFlow
│   ├── CausalNode (custom node)
│   └── edges (causal + timeline)
├── CausalSidebar
│   └── CausalCard × N
```

## 集成

### Props 变更

当前：
```tsx
<CausalityCanvas causalities={data.causalities} />
```

变更为：
```tsx
<CausalityCanvas
  chapters={data.chapters}
  acts={data.acts}
  edges={data.edges}
  causalities={data.causalities}
  onChapterClick={handleChapterClick}
/>
```

### 节点复用

使用简化版章节节点 `CausalNode`，复用 PlotCanvas 中 `ChapterNode` 的部分样式。

## 限制（v1 不做）

- 不编辑因果连线
- 不将文本因果对链接到具体章节（将来可扩展 `Causality.sourceChapterId` / `targetChapterId`）
- 不支持搜索/筛选
- 不保存布局位置（每次刷新重新计算）
