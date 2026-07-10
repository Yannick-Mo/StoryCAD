import { getToken } from './auth'

const API_BASE = '/api'

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
  const resp = await fetch(`${API_BASE}/consistency/projects/${projectId}/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  })
  if (!resp.ok) {
    const text = await resp.text();
    let detail = `API error: ${resp.status}`;
    try { detail = JSON.parse(text).detail || detail; } catch {}
    throw new Error(detail);
  }
  return resp.json()
}
