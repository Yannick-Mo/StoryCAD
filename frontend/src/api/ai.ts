// frontend/src/api/ai.ts
import { apiPost } from './auth'

export interface AiGenerateRequest {
  chapter_id: string
  mode: 'goal' | 'outline' | 'writing'
  prompt: string
}

export interface GoalResult {
  goal: string
  reasoning: string
}

export interface SceneOutlineItem {
  title: string
  pov_character: string
  setting: string
  scene_time: string
  summary: string
}

export interface OutlineResult {
  planning: string
  scenes: SceneOutlineItem[]
}

export interface WritingResult {
  content: string
  note: string | null
}

export type AiResult = GoalResult | OutlineResult | WritingResult

export async function generateAI(
  projectId: string,
  request: AiGenerateRequest,
): Promise<AiResult> {
  return apiPost<AiResult>(
    `/api/projects/${projectId}/ai/generate`,
    request,
  )
}
