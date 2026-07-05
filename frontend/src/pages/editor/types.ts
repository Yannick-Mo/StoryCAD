// View system
export type Pillar = 'world' | 'narrative' | 'experience' | 'creation'

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
  // Experience
  { id: 'experience-info', label: '👁️ 信息释放', pillar: 'experience', type: 'info' },
  { id: 'experience-pov', label: '🎯 POV策略', pillar: 'experience', type: 'info' },
  // Creation
  { id: 'creation-inspo', label: '💡 灵感碎片', pillar: 'creation', type: 'info' },
  { id: 'creation-kanban', label: '📋 进度看板', pillar: 'creation', type: 'info' },
  { id: 'creation-log', label: '📓 版本日志', pillar: 'creation', type: 'info' },
]

export const PILLAR_VIEWS: Record<Pillar, ViewDef[]> = {
  world: VIEWS.filter(v => v.pillar === 'world'),
  narrative: VIEWS.filter(v => v.pillar === 'narrative'),
  experience: VIEWS.filter(v => v.pillar === 'experience'),
  creation: VIEWS.filter(v => v.pillar === 'creation'),
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

export interface Character {
  id: string
  name: string
  role: string
  relations: { targetId: string; type: string }[]
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
}

export interface ThemeItem {
  name: string
  color: string
  connections: string[]
}

export interface WorldInfo {
  name: string
  regions: string[]
}

export interface InfoControl {
  topic: string
  revealed: boolean
}

export interface PovInfo {
  character: string
  percentage: number
}

export interface KanbanItem {
  stage: string
  count: number
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
  infoControls: InfoControl[]
  pov: PovInfo[]
  inspirations: string[]
  kanban: KanbanItem[]
  changelog: string[]
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
  relations: { targetId: string; type: string }[]
}

export interface CauseNodeData {
  label: string
}

export interface EffectNodeData {
  label: string
}

export interface RhythmNodeData {
  label: string
  intensity: number
  chapterIndex: number
}

export interface ThemeNodeData {
  name: string
  color: string
}
