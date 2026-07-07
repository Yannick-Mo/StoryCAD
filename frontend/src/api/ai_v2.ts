import { getToken } from './auth'

const API_BASE = 'http://localhost:8000'

export interface Conversation {
  id: string
  title: string
  created_at: string
  message_count?: number
}

export interface ChatEvent {
  type: 'conv_id' | 'step' | 'token' | 'done'
  data: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface ConversationDetail {
  id: string
  title: string
  created_at: string
  messages: Message[]
}

export function sendMessage(
  projectId: string,
  message: string,
  conversationId: string | null,
  onEvent: (event: ChatEvent) => void,
  onError: (error: Error) => void,
  onComplete: () => void,
  mode: string = 'chat',
): AbortController {
  const controller = new AbortController()
  const token = getToken()

  fetch(`${API_BASE}/api/v2/projects/${projectId}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, conversation_id: conversationId, mode }),
    signal: controller.signal,
  })
    .then(async (resp) => {
      if (!resp.ok) {
        const text = await resp.text().catch(() => '')
        throw new Error(text ? JSON.parse(text).detail || text : `HTTP ${resp.status}`)
      }

      const reader = resp.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let currentEvent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            const rawData = line.slice(6).trim()
            if (currentEvent === 'conv_id') {
              onEvent({ type: 'conv_id', data: rawData })
            } else if (currentEvent === 'step') {
              onEvent({ type: 'step', data: rawData })
            } else if (currentEvent === 'token') {
              onEvent({ type: 'token', data: rawData })
            } else if (currentEvent === 'done') {
              onEvent({ type: 'done', data: rawData })
            }
          }
        }
      }

      onComplete()
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError(err)
    })

  return controller
}

export async function getConversations(projectId: string): Promise<Conversation[]> {
  const token = getToken()
  const resp = await fetch(`${API_BASE}/api/v2/projects/${projectId}/conversations`, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.json()
}

export async function getConversation(projectId: string, convId: string): Promise<ConversationDetail> {
  const token = getToken()
  const resp = await fetch(`${API_BASE}/api/v2/projects/${projectId}/conversations/${convId}`, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.json()
}

export async function deleteConversation(projectId: string, convId: string): Promise<void> {
  const token = getToken()
  const resp = await fetch(`${API_BASE}/api/v2/projects/${projectId}/conversations/${convId}`, {
    method: 'DELETE',
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
}
