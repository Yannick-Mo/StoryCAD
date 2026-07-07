import { getToken } from './auth'

const API_BASE = 'http://localhost:8000'

export interface ConsistencyIssue {
  check_type: string
  severity: string
  entity_type: string
  entity_id: string | null
  description: string
  suggestion: string | null
  chapter_id: string | null
  scene_id: string | null
}

export interface ConsistencyReport {
  project_id: string
  issues: ConsistencyIssue[]
  summary: string
  timestamp: string | null
}

export async function checkConsistency(projectId: string): Promise<ConsistencyReport> {
  const token = getToken()
  const resp = await fetch(`${API_BASE}/api/consistency/projects/${projectId}/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: '{}',
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.json()
}
