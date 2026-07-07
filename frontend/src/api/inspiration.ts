import { getToken } from './auth'

const API_BASE = 'http://localhost:8000'

export interface StoryStarter {
  title: string
  hook: string
  premise: string
  protagonist: string
  opening_scene: string
  themes: string[]
  tags: string[]
}

export interface CreativeChallenge {
  title: string
  description: string
  constraints: string[]
  genre: string
  difficulty: string
}

export async function generateStarter(genre: string, style?: string, constraints?: string[]): Promise<StoryStarter> {
  const token = getToken()
  const resp = await fetch(`${API_BASE}/api/inspiration/starter`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify({ genre, style, constraints }),
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.json()
}

export async function batchGenerate(genres: string[], count?: number): Promise<StoryStarter[]> {
  const token = getToken()
  const resp = await fetch(`${API_BASE}/api/inspiration/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify({ genres, count }),
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.json()
}

export async function getChallenges(difficulty?: string, genre?: string): Promise<CreativeChallenge[]> {
  const token = getToken()
  const params = new URLSearchParams()
  if (difficulty) params.set('difficulty', difficulty)
  if (genre) params.set('genre', genre)
  const qs = params.toString()
  const resp = await fetch(`${API_BASE}/api/inspiration/challenges${qs ? `?${qs}` : ''}`, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.json()
}

export async function getRandomChallenge(): Promise<CreativeChallenge> {
  const token = getToken()
  const resp = await fetch(`${API_BASE}/api/inspiration/challenges/random`, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.json()
}
