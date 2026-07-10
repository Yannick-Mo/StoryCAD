import { getToken } from './auth'

const API_BASE = ''

interface McpResponse<T = unknown> {
  result?: T
  error?: string
}

async function callTool<T = unknown>(toolName: string, args: Record<string, unknown>): Promise<T> {
  const token = getToken()
  const resp = await fetch(`${API_BASE}/mcp/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: crypto.randomUUID(),
      method: 'tools/call',
      params: { name: toolName, arguments: args },
    }),
  })
  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    throw new Error(text || `HTTP ${resp.status}`)
  }
  const data: McpResponse<T> = await resp.json()
  if (data.error) throw new Error(data.error)
  return data.result as T
}

export const mcp = {
  // === Project ===
  readProject: (projectId: string) =>
    callTool<Record<string, unknown>>('read_project', { project_id: projectId }),

  updateProject: (projectId: string, fields: {
    title?: string; description?: string; genre?: string; status?: string; global_settings?: string
  }) =>
    callTool<Record<string, unknown>>('update_project', { project_id: projectId, ...fields }),

  listChapters: (projectId: string) =>
    callTool<Record<string, unknown>[]>('list_chapters', { project_id: projectId }),

  // === Story ===
  readChapter: (chapterId: string) =>
    callTool<Record<string, unknown>>('read_chapter', { chapter_id: chapterId }),

  readScene: (sceneId: string) =>
    callTool<Record<string, unknown>>('read_scene', { scene_id: sceneId }),

  createScene: (projectId: string, chapterId: string, title: string, opts?: {
    summary?: string; content?: string; pov_character?: string; setting?: string; scene_time?: string; sort_order?: number
  }) =>
    callTool<Record<string, unknown>>('create_scene', { project_id: projectId, chapter_id: chapterId, title, ...opts }),

  updateScene: (sceneId: string, fields: {
    title?: string; summary?: string; content?: string; pov_character?: string; setting?: string; scene_time?: string
  }) =>
    callTool<Record<string, unknown>>('update_scene', { scene_id: sceneId, ...fields }),

  // === Character ===
  listCharacters: (projectId: string) =>
    callTool<{ characters: Record<string, unknown>[]; relations: Record<string, unknown>[] }>('list_characters', { project_id: projectId }),

  createCharacter: (projectId: string, name: string, opts?: {
    role?: string; personality?: string; appearance?: string; background?: string; motivation?: string
  }) =>
    callTool<Record<string, unknown>>('create_character', { project_id: projectId, name, ...opts }),

  updateCharacter: (characterId: string, fields: {
    name?: string; role?: string; personality?: string; appearance?: string; background?: string; motivation?: string
  }) =>
    callTool<Record<string, unknown>>('update_character', { character_id: characterId, ...fields }),

  updateRelation: (projectId: string, characterId: string, targetId: string, opts?: {
    rel_type?: string; label?: string; description?: string; trust?: number; threat?: number; attraction?: number; relation_id?: string
  }) =>
    callTool<Record<string, unknown>>('update_relation', { project_id: projectId, character_id: characterId, target_id: targetId, ...opts }),

  // === Analysis ===
  checkConsistency: (projectId: string) =>
    callTool<Record<string, unknown>>('check_consistency', { project_id: projectId }),

  analyzeRhythm: (projectId: string) =>
    callTool<Record<string, unknown>>('analyze_rhythm', { project_id: projectId }),
}
