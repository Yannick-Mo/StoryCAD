export interface ProjectListItem {
  id: string
  title: string
  genre?: string
  status: string
  template_type?: string
  total_words?: number
  total_chapters?: number
  total_scenes?: number
  created_at: string
  updated_at?: string
}

export interface HomeProject extends ProjectListItem {
  coverClass: string
  coverChar: string
  stage: string
  stageType: string
  progress: number
  progressClass: string
}

export const COVER_GRADIENTS = ["grad-purple", "grad-blue", "grad-pink", "grad-gold", "grad-green", "grad-teal"] as const
export const PROGRESS_CLASSES = ["purple", "blue", "pink", "gold", "green"] as const
