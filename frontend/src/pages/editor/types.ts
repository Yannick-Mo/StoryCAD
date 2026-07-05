// View system
export type Pillar = 'world' | 'narrative'

export interface ViewDef {
  id: string
  label: string
  pillar: Pillar
  type: 'canvas' | 'info'
}

export const VIEWS: ViewDef[] = [
  // World
  { id: 'world-map', label: '🗺️ 地图与势力', pillar: 'world', type: 'info' },
  { id: 'world-rules', label: '⚛️ 规则体系', pillar: 'world', type: 'info' },
  { id: 'world-history', label: '📜 历史年表', pillar: 'world', type: 'info' },
  // Narrative
  { id: 'narrative-plot', label: '🎬 情节幕布', pillar: 'narrative', type: 'canvas' },
  { id: 'narrative-char', label: '👥 人物幕布', pillar: 'narrative', type: 'canvas' },
  { id: 'narrative-rhythm', label: '📈 节奏幕布', pillar: 'narrative', type: 'canvas' },
  { id: 'narrative-theme', label: '🎭 主题幕布', pillar: 'narrative', type: 'canvas' },
]

export const PILLAR_VIEWS: Record<Pillar, ViewDef[]> = {
  world: VIEWS.filter(v => v.pillar === 'world'),
  narrative: VIEWS.filter(v => v.pillar === 'narrative'),
}

// Edge types
export type EdgeType = 'timeline' | 'causal' | 'foreshadow' | 'character' | 'theme'

export interface ChapterEdge {
  id: string
  sourceId: string
  targetId: string
  type: EdgeType
  label?: string
  sourceHandle?: string
  targetHandle?: string
}

export interface SelectionState {
  type: 'act' | 'chapter' | 'edge' | null
  id: string | null
}

export interface Toast {
  id: string
  message: string
  type: 'info' | 'warning' | 'error' | 'success'
  duration?: number
}

export interface EdgeResult {
  edge: ChapterEdge | null
  cycle?: boolean
}

// Mock data types
export interface Act {
  id: string
  name: string
  order: number
  color: string
  width?: number
  height?: number
}

export interface Scene {
  id: string
  title: string
  povCharacter: string
  setting: string
  time: string
  summary: string
  content: string
  wordCount: number
}

export interface Chapter {
  id: string
  actId: string
  title: string
  goal: string
  wordCount: number
  status: 'draft' | 'revising' | 'final'
  scenes: Scene[]
}

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

export interface Causality {
  id: string
  cause: string
  effect: string
}

export interface RhythmPoint {
  chapterIndex: number
  intensity: number
  label: string
  action: number
  suspense: number
  emotion: number
  humor: number
}

export interface ThemeItem {
  name: string
  color: string
  proposition: string
  chapterIndices: number[]
  connections: string[]
}

export interface WorldInfo {
  name: string
  regions: string[]
}

export interface EditorMockData {
  projectTitle: string
  acts: Act[]
  chapters: Chapter[]
  edges: ChapterEdge[]
  characters: Character[]
  causalities: Causality[]
  rhythms: RhythmPoint[]
  themes: ThemeItem[]
  world: WorldInfo
  rules: string[]
  history: string[]
}

// React Flow node data types
export interface ChapterNodeData {
  actId: string
  actColor: string
  title: string
  goal: string
  wordCount: number
  status: 'draft' | 'revising' | 'final'
  sceneCount: number
  orderBadge?: string | number
}

export interface CharacterNodeData {
  name: string
  role: string
  relations: CharacterRelation[]
}

export interface ThemeNodeData {
  name: string
  color: string
  connections: string[]
}
