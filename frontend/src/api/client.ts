const BASE = "/api"

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options)
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

export async function listProjects(): Promise<{ project_id: string; status: string; created_at: string }[]> {
  return request(`${BASE}/projects`)
}

export async function getProject(id: string): Promise<any> {
  return request(`${BASE}/projects/${id}`)
}

export async function createProject(rawInput: string): Promise<{ project_id: string }> {
  return request(`${BASE}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_input: rawInput }),
  })
}

export async function deleteProject(id: string): Promise<void> {
  await fetch(`${BASE}/projects/${id}`, { method: "DELETE" })
}

export async function updateSkeleton(id: string, skeleton: any): Promise<void> {
  await request(`${BASE}/projects/${id}/skeleton`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(skeleton),
  })
}

export async function getSkeletonVersions(id: string): Promise<any[]> {
  return request(`${BASE}/projects/${id}/skeleton/versions`)
}

export async function getSkeletonVersion(id: string, version: number): Promise<any> {
  return request(`${BASE}/projects/${id}/skeleton/versions/${version}`)
}

export async function validateSkeleton(id: string): Promise<any> {
  return request(`${BASE}/projects/${id}/validate`, { method: "POST" })
}

export async function exportJSON(id: string): Promise<Blob> {
  const res = await fetch(`${BASE}/projects/${id}/export/json`)
  if (!res.ok) throw new Error(`Export error: ${res.status}`)
  return res.blob()
}

export async function exportMarkdown(id: string): Promise<Blob> {
  const res = await fetch(`${BASE}/projects/${id}/export/markdown`)
  if (!res.ok) throw new Error(`Export error: ${res.status}`)
  return res.blob()
}
