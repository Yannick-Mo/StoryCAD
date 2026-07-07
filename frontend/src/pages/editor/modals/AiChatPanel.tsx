import { useState, useRef, useEffect, useCallback } from 'react'
import { sendMessage, getConversations } from '../../../api/ai_v2'
import type { ChatEvent, Conversation } from '../../../api/ai_v2'

interface AiChatPanelProps {
  projectId: string
  onClose: () => void
  onApply?: (content: string) => void
}

interface DisplayMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export default function AiChatPanel({ projectId, onClose, onApply }: AiChatPanelProps) {
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const abortRef = useRef<AbortController | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getConversations(projectId).then(setConversations).catch(() => {})
  }, [projectId])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, step])

  const handleSend = useCallback(() => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    setError(null)
    setStep(null)

    const userMsg: DisplayMessage = { id: Date.now().toString(), role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])

    let currentConvId = conversationId
    let assistantMsg = ''

    const controller = sendMessage(
      projectId,
      text,
      currentConvId,
      (event: ChatEvent) => {
        if (event.type === 'conv_id') {
          currentConvId = event.data
          setConversationId(currentConvId)
        } else if (event.type === 'step') {
          setStep(event.data)
        } else if (event.type === 'token') {
          assistantMsg += event.data
          setMessages(prev => {
            const next = [...prev]
            const last = next[next.length - 1]
            if (last && last.role === 'assistant') {
              next[next.length - 1] = { ...last, content: assistantMsg }
            } else {
              next.push({ id: Date.now().toString(), role: 'assistant', content: assistantMsg })
            }
            return next
          })
        } else if (event.type === 'done') {
          setStep(null)
        }
      },
      (err: Error) => {
        setError(err.message)
        setLoading(false)
        setStep(null)
      },
      () => {
        setLoading(false)
        setStep(null)
      },
    )

    abortRef.current = controller
    setLoading(true)
  }, [input, loading, projectId, conversationId])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleStop = () => {
    abortRef.current?.abort()
    setLoading(false)
    setStep(null)
  }

  const handleNewChat = () => {
    setConversationId(null)
    setMessages([])
    setError(null)
    setStep(null)
  }

  return (
    <div className="fixed right-0 top-0 h-full w-[380px] z-50 flex flex-col bg-gray-900 border-l border-gray-800 shadow-2xl">
      <div className="flex items-center justify-between px-4 h-12 border-b border-gray-800 shrink-0 bg-gray-950/80">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-amber-100">AI 助手</h3>
          {conversationId && (
            <button
              onClick={handleNewChat}
              className="text-[10px] px-2 py-0.5 rounded bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition-colors"
            >
              新对话
            </button>
          )}
        </div>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-white text-lg leading-none"
        >
          x
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && !loading && (
          <div className="text-center text-gray-500 text-xs mt-8">
            向 AI 助手提问，获得创作建议和灵感
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-xl px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-amber-600 text-black rounded-br-sm'
                  : 'bg-gray-800 text-gray-200 rounded-bl-sm'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {step && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-xl px-3 py-2 text-xs text-amber-500/70 bg-gray-800/60 rounded-bl-sm">
              {step}
            </div>
          </div>
        )}

        {loading && !step && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-xl px-3 py-2 text-xs text-gray-500 bg-gray-800/60 rounded-bl-sm">
              <span className="inline-block animate-pulse">思考中...</span>
            </div>
          </div>
        )}

        {messages.some(m => m.role === 'assistant' && m.content) && onApply && (
          <div className="flex justify-start">
            <button
              onClick={() => {
                const last = messages.filter(m => m.role === 'assistant').pop()
                if (last) onApply(last.content)
              }}
              className="text-[10px] px-2 py-1 rounded bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition-colors"
            >
              应用建议
            </button>
          </div>
        )}

        {error && (
          <div className="bg-red-900/20 border border-red-800/30 rounded-lg p-3">
            <p className="text-xs text-red-400">{error}</p>
          </div>
        )}
      </div>

      <div className="p-3 border-t border-gray-800 shrink-0 bg-gray-950/80">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你的问题..."
            disabled={loading}
            rows={2}
            className="flex-1 bg-gray-950 border border-gray-700 rounded-xl px-3 py-2 text-xs text-gray-300 resize-none focus:outline-none focus:border-amber-600 leading-relaxed disabled:opacity-50"
          />
          {loading ? (
            <button
              onClick={handleStop}
              className="px-3 py-2 rounded-xl bg-red-600 text-white text-xs font-medium hover:bg-red-500 transition-colors shrink-0 self-end"
            >
              停止
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="px-3 py-2 rounded-xl bg-amber-600 text-black text-xs font-medium hover:bg-amber-500 transition-colors disabled:opacity-30 disabled:cursor-default shrink-0 self-end"
            >
              发送
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
