export interface WorldRule {
  category: string
  description: string
  limitation: string
}

export interface WorldRules {
  rules: WorldRule[]
  history: string
  forbidden_events: string[]
}

export interface DesireTopology {
  表层欲望: string
  深层需求: string
  核心恐惧: string
}

export interface Relationship {
  信任: number
  威胁: number
  吸引力: number
}

export interface Character {
  name: string
  desire_topology: DesireTopology
  bottom_line: string
  vulnerability: string
  language_genes: string[]
  relationships: Record<string, Relationship>
  growth_arc: string
}

export interface GraphNode {
  id: string
  description: string
  emotion_value: number
}

export interface GraphEdge {
  source: string
  target: string
  type: "necessary" | "possible" | "indirect"
}

export interface PlotGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface Branch {
  divergence_point: string
  paths: string[][]
  convergence_point: string | null
}

export interface Foreshadow {
  id: string
  planted_at: string
  content: string
  status: "pending" | "recycled"
  planned_recycle_interval: number
}

export interface ValidationIssue {
  severity: "high" | "medium" | "low"
  category: string
  description: string
  location: string
  suggestion: string
}

export interface CreativeDoc {
  core_conflict: string
  implied_world_clues: string[]
  character_seeds: string[]
  structural_constraints: string[]
  anchor_events: string[]
}

export interface NarrativeSkeleton {
  creative_doc: CreativeDoc
  world_rules: WorldRules
  characters: Character[]
  graph: PlotGraph
  branches: Branch[]
  foreshadows: Foreshadow[]
}