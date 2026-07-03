# 时序线单链重构与已完成内容

## 目标
1. 移除节点锁定机制（wordCount > 0 不再限制时序线操作）
2. 时序线强制执行单链约束（链表结构：每节点最多 1 入 + 1 出）
3. 完成内容 = 从头节点沿时序线的最长无断链
4. 选中连线视觉反馈

## 改动清单

### 一、移除锁定

| 文件 | 改动 |
|------|------|
| `types.ts` | `EdgeResult.locked?` 移除 |
| `orderUtils.ts` | 删除 `isEdgeLocked()` 函数 |
| `editorStore.ts` | 删除 `addEdge`/`changeEdgeType`/`reconnectEdge` 中的 `wordCount > 0` 检查 |
| `EdgePropertyPanel.tsx` | 删除 `isEdgeLocked` 导入、🔒、禁用下拉、警告条 |
| `PlotCanvas.tsx` | 删除 `isEdgeLocked` 导入、`locked` 样式变量、锁定 toast、`wordCount > 0` 边更新检查 |
| `PlotToolbar.tsx` | 无需改动（无锁定相关逻辑） |
| `ContextMenu.tsx` | 无需改动（`disabled` 由调用方控制） |

### 二、时序线单链约束

`editorStore.ts` 中的改动：

- **`addEdge`** (timeline): 
  - 依然替换目标已有入线
  - **新增**：替换源节点已有出线（A→B 时若 A 已有 A→C，删除 A→C）
  - 无环检测保持不变

- **`changeEdgeType`**: 
  - 改为非timeline→timeline 时：检查源节点是否已有出线、目标节点是否已有入线
  - 如果有则返回 `false`（调用方 toast 提示）

- **`reconnectEdge`**:
  - 改为非timeline→timeline 时（新source/target）：同样检查单链约束
  - 如果有冲突则静默返回

### 三、已完成内容链

新增 `orderUtils.ts` 函数：

```ts
function getCompletedChain(chapters, edges, acts): Chapter[]
```

算法：
1. `acts` 按 `order` 排序，取第一幕
2. 第一幕中所有章节，按 `topologicalSort` 排，取首个为头节点
3. 维护 `outgoingMap: Map<string, ChapterEdge>`（每个源最多一条时序出线）
4. 从头节点开始：`current = head; while (current) { result.push(current); edge = outgoingMap.get(current.id); if (!edge) break; current = chapters.find(edge.targetId) }`
5. 返回 `result`

`EditorShell.tsx` 改动：
- `handleExport`: 只导出 `getCompletedChain` 返回的章节
- `PreviewModal`: 传入 `getCompletedChain` 的结果而非全部章节

### 四、选中连线变色

`PlotCanvas.tsx` 中 `rfEdges` 映射：
- 选中状态下：时序线 → `#fbbf24`（亮金），关系线 → `#60a5fa`（亮蓝）
- 取消 `selected` 自带的 React Flow 蓝色描边

### 五、Mock 数据

`mockData.ts`：
- 添加 `e6: ch3→ch4 (timeline)` 使链连续
- 保留 `e5: ch2→ch4 (causal)` 不变
- 为 ch4-ch6 添加场景内容

## 边界情况
- **无时序边**：`getCompletedChain` 返回 `[head]`（仅头节点）
- **头节点无内容**：仍纳入链中（空内容不显示）
- **循环**：`topologicalSort`/`wouldCreateCycle` 不变
- **删边导致断链**：`getCompletedChain` 自动适应
