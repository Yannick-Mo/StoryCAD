# Character Canvas Enhancement Plan

> **For agentic workers:** Implement inline in this session.

**Goal:** Transform the read-only character canvas into a full interactive canvas matching the plot canvas patterns: draggable nodes, selectable nodes/edges, right-side detail panels, and context menus.

**Tech Stack:** React 18, TypeScript, React Flow 11, Tailwind CSS.

---

### Task 1: Expand Character Model and Mock Data

**Files:**
- Modify: `frontend/src/pages/editor/types.ts`
- Modify: `frontend/src/pages/editor/data/mockData.ts`

- [ ] **Step 1: Add fields to Character and Relation types**

In `types.ts`, update Character:
```ts
export interface CharacterRelation {
  id: string
  targetId: string
  type: string
  description: string
}

export interface Character {
  id: string
  name: string
  role: string
  personality: string
  appearance: string
  background: string
  motivation: string
  relations: CharacterRelation[]
}
```

- [ ] **Step 2: Update mockData with rich character info and relation IDs/descriptions**

- [ ] **Step 3: Verify `tsc --noEmit`**
- [ ] **Step 4: Commit**

---

### Task 2: Update CharacterNode for Selection

**Files:**
- Modify: `frontend/src/pages/editor/views/character/CharacterNode.tsx`

- [ ] Add `selected` to destructured props, add blue ring + glow on selected
- [ ] Enlarge handles for easier connection
- [ ] Commit

---

### Task 3: Add Character and Relation Detail Panels

**Files:**
- Create: `frontend/src/pages/editor/views/character/CharacterDetail.tsx`
- Create: `frontend/src/pages/editor/views/character/CharacterEdgeDetail.tsx`

- [ ] **CharacterDetail**: right panel showing name, role, personality, appearance, background, motivation
- [ ] **CharacterEdgeDetail**: right panel showing source→target character cards + relation type + description
- [ ] Verify `tsc --noEmit`
- [ ] Commit

---

### Task 4: Rewrite CharCanvas

**Files:**
- Modify: `frontend/src/pages/editor/views/character/CharCanvas.tsx`

- [ ] Add `useNodesState`/`useEdgesState` for drag persistence
- [ ] Enable `onConnect` for new relations
- [ ] Add `onNodeClick` for selection callback
- [ ] Add `onEdgeClick` for relation selection
- [ ] Add context menus (right-click node → delete/new; right-click edge → delete)
- [ ] Pass selection state for visual highlighting
- [ ] No handle occupancy checks (multiple edges per handle allowed)
- [ ] Verify `tsc --noEmit`
- [ ] Commit

---

### Task 5: Wire EditorShell

**Files:**
- Modify: `frontend/src/pages/editor/layout/EditorShell.tsx`
- Modify: `frontend/src/pages/editor/data/editorStore.ts`

- [ ] Add `selectedCharacterId` and `selectedRelationId` state to EditorShell
- [ ] Add store methods: `addCharacter`, `deleteCharacter`, `addRelation`, `deleteRelation`
- [ ] Render CharacterDetail / CharacterEdgeDetail when character canvas is active
- [ ] Pass new props to CharCanvas
- [ ] Verify `tsc --noEmit`
- [ ] Commit

---

### Task 6: Manual Verification

- [ ] Drag character nodes
- [ ] Click character → right panel opens with details
- [ ] Click relation edge → right panel opens with relation info
- [ ] Right-click node → context menu (new/delete)
- [ ] Right-click edge → delete
- [ ] Connect new relation between characters
- [ ] `tsc --noEmit` passes
