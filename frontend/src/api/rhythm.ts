import { getToken } from './auth'

const API_BASE = 'http://localhost:8000'

export interface RhythmAnalysis {
  chapters: RhythmChapter[]
  genre_comparison: Record<string, unknown>
  overall_assessment: string
  emotion_curve: [number, number][]
  info_density: [number, number][]
  dialogue_ratio: [number, number][]
}

export interface RhythmChapter {
  chapter_id: string
  title: string
  metrics: { action: number; suspense: number; emotion: number; humor: number; intensity: number }
  word_count: number
  anomaly_score: number
  anomaly_label: string | null
  ai_note: string | null
}

export async function analyzeRhythm(projectId: string): Promise<RhythmAnalysis> {
  const token = getToken()
  const resp = await fetch(`${API_BASE}/api/rhythm/projects/${projectId}/analyze`, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.json()
}
