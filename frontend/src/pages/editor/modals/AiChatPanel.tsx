import { useState, useRef, useEffect, useCallback } from 'react'
import { useResizePanel } from '../../../hooks/useResizePanel'
import { sendMessage, getConversations } from '../../../api/ai_v2'
import type { Conversation } from '../../../api/ai_v2'

function generateId(): string {
  return Math.random().toString(36).slice(2, 11)
}

const UI_TEXT = {
  placeholder: '输入你的创作需求...',
  send: '发送',
  stop: '停止',
  loading: '思考中...',
  cowriter: '协作',
  chat: '对话',
  newConversation: '新对话',
}

interface AiPanelProps {
  projectId: string
  onClose: () => void
  onProjectUpdated?: () => void
  contextView?: string
  contextId?: string
}

interface DisplayMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

interface OptionItem {
  id: string
  label: string
  description: string
  pros: string[]
  cons: string[]
}

interface ToolResult {
  tool: string
  success: boolean
  data?: any
  error?: string
}

function useAiChat(projectId: string, contextView: string, contextId?: string) {
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [mode, setMode] = useState<'chat' | 'cowriter'>('chat')
  const [currentOptions, setCurrentOptions] = useState<OptionItem[]>([])
  const [toolResults, setToolResults] = useState<ToolResult[]>([])
  const abortRef = useRef<AbortController | null>(null)
  const loadingRef = useRef(false)
  const convIdRef = useRef<string | null>(null)
  const modeRef = useRef(mode)

  useEffect(() => { modeRef.current = mode }, [mode])

  useEffect(() => {
    getConversations(projectId).then(data => setConversations(data.conversations)).catch(() => {})
  }, [projectId])

  const send = useCallback((text: string, onProjectUpdated?: () => void) => {
    if (!text.trim() || loadingRef.current) return

    loadingRef.current = true
    setLoading(true)
    setError(null)
    setStep(null)
    setCurrentOptions([])
    setToolResults([])

    const userMsg: DisplayMessage = { id: generateId(), role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])

    const currentConvId = convIdRef.current
    let assistantMsg = ''

    let throttleTimer: ReturnType<typeof requestAnimationFrame> | null = null
    const scheduleUpdate = () => {
      if (throttleTimer) return
      throttleTimer = requestAnimationFrame(() => {
        throttleTimer = null
        setMessages(prev => {
          const next = [...prev]
          const last = next[next.length - 1]
          if (last && last.role === 'assistant') {
            next[next.length - 1] = { ...last, content: assistantMsg }
          } else {
            next.push({ id: generateId(), role: 'assistant', content: assistantMsg })
          }
          return next
        })
      })
    }

    const controller = sendMessage({
      projectId,
      message: text,
      conversationId: currentConvId,
      onToken: (token: string) => {
        assistantMsg += token
        scheduleUpdate()
      },
      onStep: (step: string) => setStep(step),
      onToolStart: (data: string) => setStep(`执行: ${data}`),
      onToolDone: (data: string) => {
        try {
          const parsed = JSON.parse(data)
          setToolResults(prev => [...prev, parsed])
        } catch (e) {
          console.error('Failed to parse tool_done data:', data, e)
        }
      },
      onOption: (options: any[]) => setCurrentOptions(options),
      onConvId: (id: string) => {
        convIdRef.current = id
        setConversationId(id)
        setConversations(prev => {
          if (prev.some(c => c.id === id)) return prev
          return [{ id, title: text.slice(0, 50), created_at: new Date().toISOString() }, ...prev]
        })
      },
      onProjectUpdated: () => onProjectUpdated?.(),
      onDone: () => {
        if (throttleTimer) cancelAnimationFrame(throttleTimer)
        throttleTimer = null
        setMessages(prev => {
          const next = [...prev]
          const last = next[next.length - 1]
          if (last && last.role === 'assistant') {
            next[next.length - 1] = { ...last, content: assistantMsg }
          } else if (assistantMsg) {
            next.push({ id: generateId(), role: 'assistant', content: assistantMsg })
          }
          return next
        })
        setStep(null)
      },
      onError: (err: Error) => {
        if (throttleTimer) cancelAnimationFrame(throttleTimer)
        throttleTimer = null
        setError(err.message)
        loadingRef.current = false
        setLoading(false)
        setStep(null)
      },
      onComplete: () => {
        loadingRef.current = false
        setLoading(false)
        setStep(null)
      },
      mode: modeRef.current,
      contextView,
      contextId: contextId ?? null,
    })

    abortRef.current = controller
  }, [projectId, contextView, contextId])

  const abort = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setLoading(false)
    setStep(null)
  }, [])

  const clear = useCallback(() => {
    setConversationId(null)
    setMessages([])
    setError(null)
    setStep(null)
    setCurrentOptions([])
    setToolResults([])
  }, [])

  return {
    messages, setMessages,
    loading, setLoading,
    step, setStep,
    error, setError,
    conversationId, setConversationId,
    conversations, setConversations,
    mode, setMode,
    currentOptions, setCurrentOptions,
    toolResults, setToolResults,
    send,
    abort,
    clear,
  }
}

function MessageBubble({ msg }: { msg: DisplayMessage }) {
  return (
    <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
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
  )
}

function MessageList({ messages }: { messages: DisplayMessage[] }) {
  return (
    <>
      {messages.map((msg) => (
        <MessageBubble key={msg.id} msg={msg} />
      ))}
    </>
  )
}

function OptionCard({ option, idx, onSelect }: { option: OptionItem; idx: number; onSelect: (opt: OptionItem) => void }) {
  return (
    <div
      onClick={() => onSelect(option)}
      className="border border-gray-700 rounded-lg p-3 cursor-pointer hover:border-amber-600 hover:bg-gray-800/50 transition-colors"
    >
      <div className="flex items-start gap-2">
        <span className="text-amber-500 font-mono text-xs mt-0.5">
          {['①', '②', '③', '④'][idx] || `#${idx + 1}`}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-amber-100 font-medium mb-1">{option.label}</p>
          <p className="text-xs text-gray-400 mb-1">{option.description}</p>
          {option.pros && option.pros.length > 0 && (
            <p className="text-xs text-green-500/70">✓ {option.pros.join(' · ')}</p>
          )}
          {option.cons && option.cons.length > 0 && (
            <p className="text-xs text-red-500/70">✗ {option.cons.join(' · ')}</p>
          )}
        </div>
      </div>
    </div>
  )
}

function ToolResultIndicator({ results }: { results: ToolResult[] }) {
  if (results.length === 0) return null
  return (
    <div className="space-y-1">
      {results.map((tr, i) => (
        <div key={i} className="text-xs text-gray-500 bg-gray-800/40 rounded px-2 py-1">
          {tr.success ? '✅' : '❌'} {tr.tool}
          {tr.error && <span className="text-red-400 ml-1">({tr.error})</span>}
        </div>
      ))}
    </div>
  )
}

function ChatInput({
  input, setInput, loading, onSend, onStop, onKeyDown
}: {
  input: string
  setInput: (v: string) => void
  loading: boolean
  onSend: () => void
  onStop: () => void
  onKeyDown: (e: React.KeyboardEvent) => void
}) {
  return (
    <div className="flex flex-col h-full gap-2">
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder={UI_TEXT.placeholder}
        disabled={loading}
        className="flex-1 bg-gray-950 border border-gray-700 rounded-xl px-3 py-2 text-xs text-gray-300 resize-none focus:outline-none focus:border-amber-600 leading-relaxed disabled:opacity-50"
      />
      {loading ? (
        <button
          onClick={onStop}
          className="px-3 py-2 rounded-xl bg-red-600 text-white text-xs font-medium hover:bg-red-500 transition-colors shrink-0 self-end"
        >
          {UI_TEXT.stop}
        </button>
      ) : (
        <button
          onClick={onSend}
          disabled={!input.trim()}
          className="px-3 py-2 rounded-xl bg-amber-600 text-black text-xs font-medium hover:bg-amber-500 transition-colors disabled:opacity-30 disabled:cursor-default shrink-0 self-end"
        >
          {UI_TEXT.send}
        </button>
      )}
    </div>
  )
}

export default function AiChatPanel({
  projectId, onClose, onProjectUpdated,
  contextView = 'chat', contextId
}: AiPanelProps) {
  const chat = useAiChat(projectId, contextView, contextId)
  const [input, setInput] = useState('')
  const inputRef = useRef(input)
  inputRef.current = input
  const scrollRef = useRef<HTMLDivElement>(null)

  const { size: width, handleMouseDown: panelResizeDown } = useResizePanel({ initial: 380, min: 300, max: 800, direction: 'horizontal' })
  const { size: inputHeight, handleMouseDown: inputResizeDown } = useResizePanel({ initial: 130, min: 120, max: 400, direction: 'vertical' })

  const contextLabel = contextView === 'scene' ? '场景写作'
    : contextView === 'chapter' ? '章节分析'
    : contextView === 'plot' ? '结构建议'
    : contextView === 'character' ? '角色分析'
    : contextView === 'analysis' ? '综合分析'
    : 'AI 助手'

  useEffect(() => {
    const raf = requestAnimationFrame(() => {
      const el = scrollRef.current
      if (!el) return
      const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 150
      if (isNearBottom) {
        el.scrollTop = el.scrollHeight
      }
    })
    return () => cancelAnimationFrame(raf)
  }, [chat.messages, chat.step, chat.currentOptions])

  const handleSend = useCallback(() => {
    const text = inputRef.current.trim()
    if (!text || chat.loading) return
    setInput('')
    chat.send(text, onProjectUpdated)
  }, [chat, onProjectUpdated])

  const handleOptionSelect = useCallback((option: OptionItem) => {
    setInput('')
    chat.setMessages(prev => [...prev, {
      id: generateId(),
      role: 'user',
      content: `[Select option: ${option.label}]`,
    }])
    chat.send(option.label, onProjectUpdated)
  }, [chat, onProjectUpdated])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleNewChat = () => {
    chat.clear()
  }

  return (
    <div className="fixed right-0 top-0 h-full z-50 flex flex-col bg-gray-900 border-l border-gray-800 shadow-2xl" style={{ width }}>
      {/* Resize handle (left edge) */}
      <div
        onMouseDown={panelResizeDown}
        className="absolute left-0 top-0 bottom-0 w-1 cursor-ew-resize hover:w-1.5 hover:bg-amber-500/50 active:bg-amber-500/70 transition-all z-10"
      />
      {/* Header */}
      <div className="flex items-center justify-between px-4 h-12 border-b border-gray-800 shrink-0 bg-gray-950/80">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-amber-100">{contextLabel}</h3>
          <button
            onClick={() => chat.setMode(chat.mode === 'chat' ? 'cowriter' : 'chat')}
            className={`text-[10px] px-2 py-0.5 rounded transition-colors flex items-center gap-1 ${
              chat.mode === 'cowriter'
                ? 'bg-amber-700 text-amber-100 hover:bg-amber-600'
                : 'bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700'
            }`}
            title={chat.mode === 'cowriter' ? '当前：协作模式' : '切换为协作写作模式'}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${chat.mode === 'cowriter' ? 'bg-green-400' : 'bg-gray-500'}`} />
            {chat.mode === 'cowriter' ? UI_TEXT.cowriter : UI_TEXT.chat}
          </button>
          {chat.conversationId && (
            <button
              onClick={handleNewChat}
              className="text-[10px] px-2 py-0.5 rounded bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition-colors"
            >
              {UI_TEXT.newConversation}
            </button>
          )}
        </div>
        <button onClick={onClose} className="text-gray-500 hover:text-white text-lg leading-none">x</button>
      </div>

      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {chat.messages.length === 0 && !chat.loading && (
          <div className="text-center text-gray-500 text-xs mt-8">
            {contextView === 'scene' ? '询问关于当前场景的写作建议'
              : contextView === 'chapter' ? '分析当前章节的结构和内容'
              : contextView === 'character' ? '分析角色弧线和一致性'
              : '向 AI 助手提问，获得创作建议和灵感'}
          </div>
        )}

        <MessageList messages={chat.messages} />

        {/* Options cards (cowriter mode) */}
        {chat.currentOptions.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-gray-500">选择方向：</p>
            {chat.currentOptions.map((opt, idx) => (
              <OptionCard key={opt.id} option={opt} idx={idx} onSelect={handleOptionSelect} />
            ))}
          </div>
        )}

        <ToolResultIndicator results={chat.toolResults} />

        {/* Step indicator */}
        {chat.step && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-xl px-3 py-2 text-xs text-amber-500/70 bg-gray-800/60 rounded-bl-sm">
              {chat.step}
            </div>
          </div>
        )}

        {chat.loading && !chat.step && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-xl px-3 py-2 text-xs text-gray-500 bg-gray-800/60 rounded-bl-sm">
              <span className="inline-block animate-pulse">{UI_TEXT.loading}</span>
            </div>
          </div>
        )}

        {/* Error */}
        {chat.error && (
          <div className="bg-red-900/20 border border-red-800/30 rounded-lg p-3">
            <p className="text-xs text-red-400">{chat.error}</p>
          </div>
        )}
      </div>

      {/* Resize handle (input top edge) */}
      <div
        onMouseDown={inputResizeDown}
        className="cursor-ns-resize h-1 hover:h-1.5 hover:bg-amber-500/50 active:bg-amber-500/70 transition-all shrink-0"
      />
      {/* Input */}
      <div className="p-3 border-t border-gray-800 shrink-0 bg-gray-950/80" style={{ height: inputHeight }}>
        <ChatInput
          input={input}
          setInput={setInput}
          loading={chat.loading}
          onSend={handleSend}
          onStop={chat.abort}
          onKeyDown={handleKeyDown}
        />
      </div>
    </div>
  )
}
