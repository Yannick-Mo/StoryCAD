export interface ProjectListItem {
  id: string
  title: string
  status: string
  created_at: string
}

// For homepage display — extends API data with mock fields
export interface HomeProject extends ProjectListItem {
  coverClass: string
  coverChar: string
  words: string
  template: string
  time: string
  stage: string
  stageType: string
  progress: number
  progressClass: string
  updated: Date
}

export const COVER_GRADIENTS = ["grad-purple", "grad-blue", "grad-pink", "grad-gold", "grad-green", "grad-teal"] as const
export const PROGRESS_CLASSES = ["purple", "blue", "pink", "gold", "green"] as const
