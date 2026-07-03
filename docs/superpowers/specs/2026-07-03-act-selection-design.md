# 幕组选择 + 右侧面板设计

## 概述

在情节幕布视图选中幕（Act）组节点时，右侧面板展示该幕下的所有章节（可折叠展开场景列表），与现有选中章节展示详情的行为形成层级导航。

## 选型

**A（采纳）**：幕概览模式 — 右侧面板显示幕内章节折叠列表，点击展开场景。

## 状态管理

`EditorShell` 中：
- `selectedActId: string | null` — 当前选中的幕 ID
- `selectedChapter: Chapter | null` — 当前选中的章节对象
- 两者互斥，一个为 `null` 时另一个可为有效值
- 点击画布空白处（`onPaneClick`）/关闭面板时两个均置 `null`

## 组件树

### PlotCanvas 改动
- 幕组节点 `selectable` 从 `false` 改为 `true`
- 新增 `onActClick: (actId: string) => void` prop
- `onNodeClick` 中按节点类型分发：`actGroup` → `onActClick`，`chapter` → `onChapterClick`
- `onPaneClick`（点击画布空白）→ 关闭面板

### ActDetail（新组件）
右侧面板的幕概览视图。

**Props**:
- `act: Act`
- `chapters: Chapter[]`（以 `actId` 过滤）
- `onClose: () => void`
- `onSelectChapter: (chapterId: string) => void` — 切换到该章的 ChapterDetail
- `onSceneSave`, `onOpenSceneEditor`

**内部状态**：
- `expandedChapterId: string | null` — 当前展开的章节 ID

**布局**：
- Header: 幕名称 + 颜色条 + 统计信息（章节数、总字数、各状态分布）
- Body: 可折叠章节列表
  - 每章行：`[▸/▾] 标题 · 状态标签 · 字数`
  - 点击行标题 → 折叠/展开该章的场景列表
  - 场景列表渲染同 `ChapterDetail`（可内联编辑 + 全屏入口）
  - 场景行右侧有 `🔍 聚焦` 按钮 → 调 `onSelectChapter`

### EditorShell 右侧面板渲染逻辑

```tsx
{views.activeViewId === 'narrative-plot' && (
  selectedActId ? (
    <ActDetail
      act={...}
      chapters={chapters.filter(c => c.actId === selectedActId)}
      onClose={() => setSelectedActId(null)}
      onSelectChapter={(chId) => {
        setSelectedActId(null)
        setSelectedChapter(chapters.find(c => c.id === chId) ?? null)
      }}
      onSceneSave={handleSceneSave}
      onOpenSceneEditor={...}
    />
  ) : selectedChapter ? (
    <ChapterDetail chapter={selectedChapter} ... />
  ) : null
)}
```

### 视觉反馈
- 选中幕组时高亮边框（`border-amber-400`），通过 React Flow 原生 `selected` prop 控制
- 在 `ActGroupNode` 中读取 `selected` prop 并应用 CSS 类

## 修改范围

| 文件 | 改动 |
|------|------|
| `EditorShell.tsx` | 替换 `selectedChapter` 为双状态，增加条件渲染分支 |
| `PlotCanvas.tsx` | 新增 `onActClick`，移除 `selectable: false`，空白点击关闭 |
| `ActDetail.tsx` | 新建（约 100 行） |
| `ActGroupNode.tsx` | 读取 `selected` prop，增加高亮样式 |
| `ChapterDetail.tsx` | 无需改动 |

## 不涉及
- 其他 canvas 视图
- Backend API
- Mock data 结构
- 导出逻辑
