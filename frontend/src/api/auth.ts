const BASE = "/api/auth"

export function getToken(): string | null {
  return localStorage.getItem("storycad_token")
}

export function setToken(token: string) {
  localStorage.setItem("storycad_token", token)
}

export function clearToken() {
  localStorage.removeItem("storycad_token")
}

export function isLoggedIn(): boolean {
  return !!getToken()
}

async function authRequest<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options)
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(text ? JSON.parse(text).detail : `Auth error: ${res.status}`)
  }
  return res.json()
}

export async function apiGet<T>(url: string): Promise<T> {
  const token = getToken()
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    if (res.status === 401) { clearToken(); window.location.href = "/login" }
    const text = await res.text().catch(() => "")
    throw new Error(text ? JSON.parse(text).detail : `API error: ${res.status}`)
  }
  return res.json()
}

export async function apiPost<T>(url: string, body?: unknown): Promise<T> {
  const token = getToken()
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    if (res.status === 401) { clearToken(); window.location.href = "/login" }
    const text = await res.text().catch(() => "")
    throw new Error(text ? JSON.parse(text).detail : `API error: ${res.status}`)
  }
  return res.json()
}

export async function apiPut<T>(url: string, body: unknown): Promise<T> {
  const token = getToken()
  const res = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    if (res.status === 401) { clearToken(); window.location.href = "/login" }
    const text = await res.text().catch(() => "")
    throw new Error(text ? JSON.parse(text).detail : `API error: ${res.status}`)
  }
  return res.json()
}

export async function apiPatch<T>(url: string, body: unknown): Promise<T> {
  const token = getToken()
  const res = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    if (res.status === 401) { clearToken(); window.location.href = "/login" }
    const text = await res.text().catch(() => "")
    throw new Error(text ? JSON.parse(text).detail : `API error: ${res.status}`)
  }
  return res.json()
}

export async function apiDelete<T = { ok: boolean }>(url: string): Promise<T> {
  const token = getToken()
  const res = await fetch(url, {
    method: "DELETE",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    if (res.status === 401) { clearToken(); window.location.href = "/login" }
    const text = await res.text().catch(() => "")
    throw new Error(text ? JSON.parse(text).detail : `API error: ${res.status}`)
  }
  return res.json()
}

export interface AuthUser {
  id: string
  username: string
  email: string
  display_name: string
}

export interface AuthResponse {
  token: string
  user: AuthUser
}

export async function register(username: string, email: string, password: string): Promise<AuthResponse> {
  return authRequest(`${BASE}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password }),
  })
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  return authRequest(`${BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
}

export async function getMe(): Promise<AuthUser> {
  return apiGet(`${BASE}/me`)
}

export async function updateProfile(payload: { display_name?: string; password?: string }): Promise<AuthUser> {
  return apiPatch(`${BASE}/me`, payload)
}

// Project CRUD
const BASE_PROJECTS = "/api/projects"

export async function listProjects(page = 1, size = 20): Promise<{ id: string; title: string; status: string; created_at: string }[]> {
  return apiGet(`${BASE_PROJECTS}?page=${page}&size=${size}`)
}

export async function createProject(title: string, description?: string): Promise<{ id: string }> {
  return apiPost(`${BASE_PROJECTS}`, { title, description: description || "" })
}

export async function deleteProject(id: string): Promise<void> {
  await apiDelete(`${BASE_PROJECTS}/${id}`)
}
