const BASE = "/api"

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options)
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`API error: ${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`)
  }
  return res.json()
}

export async function listProjects(): Promise<{ id: string; title: string; status: string; created_at: string }[]> {
  return request(`${BASE}/projects`)
}

export async function getProject(id: string): Promise<any> {
  return request(`${BASE}/projects/${id}`)
}

export async function createProject(title: string, description?: string): Promise<{ id: string }> {
  return request(`${BASE}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, description: description || "" }),
  })
}

export async function deleteProject(id: string): Promise<void> {
  await fetch(`${BASE}/projects/${id}`, { method: "DELETE" })
}

export async function updateProject(id: string, payload: Record<string, unknown>): Promise<void> {
  await request(`${BASE}/projects/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
}

// Story endpoints
export async function getStory(projectId: string): Promise<any> {
  return request(`${BASE}/projects/${projectId}/story`)
}

export async function generateStory(projectId: string): Promise<any> {
  return request(`${BASE}/projects/${projectId}/story/generate`, { method: "POST" })
}

export async function generatePlots(projectId: string): Promise<any> {
  return request(`${BASE}/projects/${projectId}/story/plots`, { method: "POST" })
}

// Character endpoints
export async function getCharacters(projectId: string): Promise<any[]> {
  return request(`${BASE}/projects/${projectId}/characters`)
}

export async function generateCharacters(projectId: string): Promise<any> {
  return request(`${BASE}/projects/${projectId}/characters/generate`, { method: "POST" })
}

export async function updateCharacter(projectId: string, name: string, updates: Record<string, unknown>): Promise<void> {
  await request(`${BASE}/projects/${projectId}/characters/${encodeURIComponent(name)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  })
}

export async function deleteCharacter(projectId: string, name: string): Promise<void> {
  await fetch(`${BASE}/projects/${projectId}/characters/${encodeURIComponent(name)}`, { method: "DELETE" })
}

// Analysis
export async function analyzeProject(projectId: string, input: Record<string, unknown>): Promise<any> {
  return request(`${BASE}/projects/${projectId}/analysis`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  })
}

export async function getAnalysis(projectId: string): Promise<any> {
  return request(`${BASE}/projects/${projectId}/analysis`)
}

// Workflow (Orchestrator)
export async function startWorkflow(projectId: string, input: Record<string, unknown>): Promise<any> {
  return request(`${BASE}/projects/${projectId}/workflow/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  })
}

export async function getWorkflowState(projectId: string): Promise<any> {
  return request(`${BASE}/projects/${projectId}/workflow/state`)
}

// Export
export async function exportStory(projectId: string, format: string = "json"): Promise<Blob> {
  const res = await fetch(`${BASE}/projects/${projectId}/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ format }),
  })
  if (!res.ok) throw new Error(`Export error: ${res.status}`)
  return res.blob()
}

// Versions (save/load)
export async function getVersions(projectId: string): Promise<{ version: number; created_at: string }[]> {
  return request(`${BASE}/projects/${projectId}/versions`)
}

export async function saveVersion(projectId: string, snapshot: Record<string, unknown>): Promise<{ version: number; created_at: string }> {
  return request(`${BASE}/projects/${projectId}/versions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ snapshot }),
  })
}

export async function getLatestVersion(projectId: string): Promise<{ version: number; snapshot: any; created_at: string }> {
  return request(`${BASE}/projects/${projectId}/versions/latest`)
}

export async function getVersion(projectId: string, version: number): Promise<{ version: number; snapshot: any; created_at: string }> {
  return request(`${BASE}/projects/${projectId}/versions/${version}`)
}
