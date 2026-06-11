'use client'

import { useState, useRef, useEffect, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useStream } from '@/hooks/useStream'
import { conversationsApi } from '@/lib/api'
import type { SourceDocument } from '@/lib/types'
import { cn } from '@/lib/utils'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import ThinkingDog from '@/components/ThinkingDog'
const IS_DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === 'true'

const SUGGESTIONS = [
  'What are the most critical vulnerabilities this week?',
  'Summarize recent npm ecosystem advisories',
  'Which packages have remote code execution vulnerabilities?',
  'Are there any critical CVEs affecting Python packages?',
]

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: SourceDocument[]
  responseTime?: number
}

function AdvisoryContextBadge({
  title,
  sourceId,
  onDismiss,
}: {
  title: string
  sourceId: string
  onDismiss: () => void
}) {
  return (
    <div className="mx-6 mt-4 flex items-start gap-3 rounded-2xl bg-md-primary/10 dark:bg-md-primary/20 border border-md-primary/20 px-4 py-3">
      <span
        className="material-symbols-outlined text-[18px] text-md-primary shrink-0 mt-0.5"
        style={{ fontVariationSettings: "'FILL' 1" }}
      >
        security
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-md-primary mb-0.5">
          Advisory context
        </p>
        <p className="text-[13px] font-medium text-on-surface leading-snug line-clamp-2">
          {title}
        </p>
        {sourceId && (
          <p className="text-[11px] text-on-surface-variant font-numbers mt-0.5">{sourceId}</p>
        )}
      </div>
      <button
        onClick={onDismiss}
        className="shrink-0 text-on-surface-variant hover:text-on-surface transition-colors"
        aria-label="Dismiss advisory context"
      >
        <span className="material-symbols-outlined text-[18px]">close</span>
      </button>
    </div>
  )
}

function ChatContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

  const [advisorySourceId, setAdvisorySourceId] = useState<string | null>(
    searchParams.get('sourceId')
  )
  const [advisoryTitle, setAdvisoryTitle] = useState<string | null>(
    searchParams.get('title')
  )

  const conversationId = searchParams.get('c')
  const lazyCreatedRef = useRef(false)

  const [messages, setMessages] = useState<Message[]>([])
  const [messagesLoaded, setMessagesLoaded] = useState(!conversationId)
  const [input, setInput] = useState('')
  const [useAgentic, setUseAgentic] = useState(false)
  const [searchMode, setSearchMode] = useState<'hybrid' | 'bm25' | 'vector'>('hybrid')
  const [topK, setTopK] = useState(5)
  const [showSources, setShowSources] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const autoSentRef = useRef(false)
  const sendTimeRef = useRef<number>(0)

  const { answer, sources, isStreaming, error, stream, reset } = useStream({
    onDone: (finalAnswer) => {
      const elapsed = Date.now() - sendTimeRef.current
      setMessages((prev) => {
        const last = prev[prev.length - 1]
        if (last?.role === 'assistant') {
          return [...prev.slice(0, -1), { ...last, content: finalAnswer, sources, responseTime: elapsed }]
        }
        return prev
      })
    },
  })

  useEffect(() => {
    if (isStreaming && answer) {
      setMessages((prev) => {
        const last = prev[prev.length - 1]
        if (last?.role === 'assistant') {
          return [...prev.slice(0, -1), { ...last, content: answer }]
        }
        return prev
      })
    }
  }, [answer, isStreaming])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, answer])

  useEffect(() => {
    if (advisoryTitle && !autoSentRef.current) {
      setInput(`Tell me about the advisory: ${advisoryTitle}`)
    }
  }, [advisoryTitle])

  useEffect(() => {
    if (!conversationId || lazyCreatedRef.current) {
      lazyCreatedRef.current = false
      return
    }
    conversationsApi.get(conversationId)
      .then((detail) => {
        const mapped: Message[] = detail.messages.map((m) => ({
          role: m.role as 'user' | 'assistant',
          content: m.content,
          sources: m.sources as unknown as SourceDocument[] | undefined,
          responseTime: m.responseTimeMs ?? undefined,
        }))
        setMessages(mapped)
        setMessagesLoaded(true)
      })
      .catch(() => {
        setMessagesLoaded(true)
      })
  }, [conversationId])

  async function handleSend(text?: string) {
    const question = (text ?? input).trim()
    if (!question || isStreaming) return

    let currentConversationId = conversationId

    if (!currentConversationId) {
      try {
        const conv = await conversationsApi.create()
        currentConversationId = conv.id
        lazyCreatedRef.current = true
        router.replace(`/ask?c=${conv.id}`)
      } catch {
        // proceed without conversation — backend still handles the query
      }
    }

    sendTimeRef.current = Date.now()
    setInput('')
    reset()
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: question },
      { role: 'assistant', content: '' },
    ])

    const conversationHistory = messages.slice(-6).map((m) => ({
      role: m.role,
      content: m.content,
    }))

    await stream('/api/rag/ask-stream', {
      question,
      topK,
      useHybrid: searchMode === 'hybrid',
      useAgentic,
      conversationId: currentConversationId ?? undefined,
      conversationHistory: conversationHistory.length > 0 ? conversationHistory : undefined,
      ...(advisorySourceId ? { advisoryId: advisorySourceId } : {}),
    })
  }

  function handleDismissContext() {
    setAdvisorySourceId(null)
    setAdvisoryTitle(null)
    setInput('')
    router.replace(`/ask${conversationId ? `?c=${conversationId}` : ''}`)
  }

  const hasMessages = messages.length > 0
  const hasContext = !!advisoryTitle

  if (!messagesLoaded) {
    return (
      <div className="flex h-full overflow-hidden">
        <div className="flex-1 flex items-center justify-center">
          <span className="material-symbols-outlined text-3xl text-on-surface-variant animate-spin">
            progress_activity
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full overflow-hidden">
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* Header */}
        <div className="px-6 py-4 border-b border-outline-variant flex items-center justify-between">
          <div>
            <h1 className="font-display text-[20px] text-on-surface">AI Query</h1>
              <p className="text-[12px] text-on-surface-variant">
                Ask questions about security advisories and threat intelligence
              </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex rounded-2xl bg-surface-container p-0.5 text-[12px] border border-outline-variant">
              {(['standard', 'agentic'] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setUseAgentic(mode === 'agentic')}
                  className={cn(
                    'px-3 py-1.5 rounded-xl capitalize transition-colors font-medium',
                    (mode === 'agentic') === useAgentic
                      ? 'bg-md-primary text-md-on-primary shadow-sm'
                      : 'text-on-surface-variant hover:text-on-surface'
                  )}
                >
                  {mode}
                </button>
              ))}
            </div>

            {sources.length > 0 && (
              <button
                onClick={() => setShowSources((v) => !v)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-2xl bg-surface-container border border-outline-variant text-[12px] text-on-surface-variant hover:bg-surface-container-high transition-colors"
              >
                <span className="material-symbols-outlined text-[16px]">library_books</span>
                {sources.length} sources
              </button>
            )}
          </div>
        </div>

        {/* Advisory context badge */}
        {hasContext && (
          <AdvisoryContextBadge
            title={advisoryTitle!}
            sourceId={advisorySourceId!}
            onDismiss={handleDismissContext}
          />
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {!hasMessages && (
            <div className="flex flex-col items-center justify-center h-full gap-6 pb-16">
              <div className="w-14 h-14 rounded-3xl bg-md-primary/15 dark:bg-md-primary/20 flex items-center justify-center">
                <span
                  className="material-symbols-outlined text-3xl text-md-primary"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  psychology
                </span>
              </div>
              <div className="text-center">
                {hasContext ? (
                  <>
                    <h2 className="font-display text-[22px] text-on-surface">
                      Ask about this advisory
                    </h2>
                    <p className="text-[13px] text-on-surface-variant mt-1">
                      Your questions will be answered using this advisory as context
                    </p>
                  </>
                ) : (
                  <>
                    <h2 className="font-display text-[22px] text-on-surface">
                      What would you like to know?
                    </h2>
                    <p className="text-[13px] text-on-surface-variant mt-1">
                      Ask about CVEs, vulnerabilities, affected packages, or threat trends
                    </p>
                  </>
                )}
              </div>
              {!hasContext && (
                <div className="grid grid-cols-2 gap-2 max-w-lg w-full">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => !IS_DEMO && handleSend(s)}
                      disabled={IS_DEMO}
                      className={cn(
                        'text-left p-3 rounded-2xl border text-[12px] transition-colors',
                        IS_DEMO
                          ? 'bg-surface-container border-outline-variant text-on-surface-variant opacity-40 cursor-not-allowed'
                          : 'bg-surface-container border-outline-variant text-on-surface-variant hover:bg-surface-container-high hover:border-md-primary/40 hover:text-on-surface'
                      )}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={cn(
                'flex gap-3 animate-msg-enter',
                msg.role === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              {msg.role === 'assistant' && (
                <div className="w-7 h-7 rounded-xl bg-md-primary/15 dark:bg-md-primary/20 flex items-center justify-center shrink-0 mt-0.5">
                  <span
                    className="material-symbols-outlined text-[14px] text-md-primary"
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    psychology
                  </span>
                </div>
              )}
              <div
                className={cn(
                  'max-w-[80%] rounded-3xl px-4 py-3 text-[14px]',
                  msg.role === 'user'
                    ? 'bg-md-primary text-md-on-primary'
                    : 'bg-surface-container border border-outline-variant text-on-surface min-w-[320px]'
                )}
              >
                {msg.role === 'assistant' ? (
                  msg.content ? (
                    <div className="prose-rag">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                      {isStreaming && i === messages.length - 1 && (
                        <span className="inline-block w-0.5 h-4 bg-on-surface ml-0.5 animate-caret-blink" />
                      )}
                      {!isStreaming && msg.responseTime !== undefined && (
                        <p className="mt-2 text-[11px] text-on-surface-variant/60 font-numbers flex items-center gap-1">
                          <span className="material-symbols-outlined text-[12px]">timer</span>
                          {msg.responseTime < 1000
                            ? `${msg.responseTime}ms`
                            : `${(msg.responseTime / 1000).toFixed(1)}s`}
                        </p>
                      )}
                    </div>
                  ) : isStreaming && i === messages.length - 1 ? (
                    <ThinkingDog />
                  ) : null
                ) : (
                  msg.content
                )}
              </div>
            </div>
          ))}

          {error && (
            <div className="flex items-center gap-2 text-error text-[13px] bg-error-container rounded-2xl px-4 py-3">
              <span className="material-symbols-outlined text-[18px]">error</span>
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <div className="px-6 pb-6 pt-3 border-t border-outline-variant">
          {IS_DEMO && (
            <div className="flex items-center gap-2 mb-2 px-1">
              <span
                className="material-symbols-outlined text-[14px] text-[#b45309] dark:text-[#ffb74d] shrink-0"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                lock
              </span>
              <p className="text-[11px] text-[#b45309] dark:text-[#ffb74d]">
                AI Query is disabled in this demo — clone the repo to use this feature locally.
              </p>
            </div>
          )}
          {hasContext && (
            <div className="flex items-center gap-1.5 mb-2">
              <span className="material-symbols-outlined text-[13px] text-md-primary">link</span>
              <span className="text-[11px] text-md-primary font-medium truncate max-w-xs">
                Scoped to: {advisoryTitle}
              </span>
              <button
                onClick={handleDismissContext}
                className="ml-auto text-[11px] text-on-surface-variant hover:text-on-surface transition-colors shrink-0"
              >
                Clear scope
              </button>
            </div>
          )}
          <div className={cn(
            'flex items-end gap-3 bg-surface-container rounded-3xl px-4 py-3',
            'border border-outline-variant',
            'focus-within:border-md-primary/60 focus-within:ring-1 focus-within:ring-md-primary/20 transition-all',
            IS_DEMO && 'opacity-50'
          )}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  if (!IS_DEMO) handleSend()
                }
              }}
              disabled={IS_DEMO}
              placeholder={
                IS_DEMO
                  ? 'AI Query disabled in demo mode'
                  : hasContext
                  ? `Ask anything about ${advisoryTitle}...`
                  : 'Ask about threats, CVEs, affected packages...'
              }
              rows={1}
              className="flex-1 resize-none bg-transparent text-[14px] text-on-surface placeholder:text-on-surface-variant focus:outline-none max-h-32 disabled:cursor-not-allowed"
            />
            <div className="flex items-center gap-2">
              <select
                value={searchMode}
                onChange={(e) => setSearchMode(e.target.value as 'hybrid' | 'bm25' | 'vector')}
                disabled={IS_DEMO}
                className="text-[11px] bg-surface-container-high rounded-xl px-2 py-1 text-on-surface-variant border border-outline-variant focus:outline-none disabled:cursor-not-allowed"
              >
                <option value="hybrid">Hybrid</option>
                <option value="bm25">BM25</option>
                <option value="vector">Vector</option>
              </select>

              <button
                onClick={() => handleSend()}
                disabled={IS_DEMO || !input.trim() || isStreaming}
                className="w-8 h-8 rounded-2xl bg-md-primary flex items-center justify-center text-md-on-primary disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 transition-opacity shrink-0"
              >
                <span
                  className="material-symbols-outlined text-[18px]"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  send
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Sources panel */}
      {showSources && sources.length > 0 && (
        <div className="w-72 shrink-0 border-l border-outline-variant flex flex-col overflow-hidden">
          <div className="p-4 border-b border-outline-variant flex items-center justify-between">
            <p className="text-[13px] font-semibold text-on-surface">Sources ({sources.length})</p>
            <button
              onClick={() => setShowSources(false)}
              className="text-on-surface-variant hover:text-on-surface"
            >
              <span className="material-symbols-outlined text-[20px]">close</span>
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {sources.map((src, i) => (
              <div key={i} className="p-3 rounded-2xl bg-surface-container border border-outline-variant space-y-1">
                <p className="text-[12px] font-medium text-on-surface line-clamp-2">{src.title}</p>
                <p className="text-[11px] text-on-surface-variant font-numbers">
                  Score: {src.score.toFixed(3)}
                </p>
                {src.chunkText && (
                  <p className="text-[11px] text-on-surface-variant line-clamp-3">{src.chunkText}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function AskPage() {
  return (
    <Suspense>
      <ChatContent />
    </Suspense>
  )
}
