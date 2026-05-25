import { useState, useRef, useCallback } from 'react'
import { apiStream } from '@/lib/api'
import type { SourceDocument } from '@/lib/types'

export interface UseStreamOptions {
  onSources?: (sources: SourceDocument[], meta: { chunksUsed: number; searchMode: string }) => void
  onChunk?: (partial: string) => void
  onDone?: (answer: string) => void
  onError?: (error: string) => void
}

export interface UseStreamResult {
  answer: string
  sources: SourceDocument[]
  searchMeta: { chunksUsed: number; searchMode: string } | null
  isStreaming: boolean
  error: string | null
  stream: (path: string, body: unknown) => Promise<void>
  reset: () => void
  abort: () => void
}

/** Returns true only when value is a plain, non-null object — safe to use 'in' on */
function isPlainObject(val: unknown): val is Record<string, unknown> {
  return typeof val === 'object' && val !== null && !Array.isArray(val)
}

export function useStream(opts: UseStreamOptions = {}): UseStreamResult {
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState<SourceDocument[]>([])
  const [searchMeta, setSearchMeta] = useState<{ chunksUsed: number; searchMode: string } | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Keep opts in a ref so the stream callback never needs to list them as deps
  const optsRef = useRef(opts)
  optsRef.current = opts

  const reset = useCallback(() => {
    setAnswer('')
    setSources([])
    setSearchMeta(null)
    setError(null)
    setIsStreaming(false)
  }, [])

  const abort = useCallback(() => {
    abortRef.current?.abort()
    setIsStreaming(false)
  }, [])

  const stream = useCallback(
    async (path: string, body: unknown) => {
      abort()
      reset()
      setIsStreaming(true)

      const controller = new AbortController()
      abortRef.current = controller

      try {
        const res = await apiStream(path, body)
        const reader = res.body?.getReader()
        if (!reader) throw new Error('No response body')

        const decoder = new TextDecoder()
        let accumulated = ''
        let buffer = ''

        while (true) {
          if (controller.signal.aborted) break
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? '' // keep incomplete last line

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            const raw = line.slice(6).trim()

            if (raw === '[DONE]') {
              setIsStreaming(false)
              optsRef.current.onDone?.(accumulated)
              return
            }

            // Skip empty data lines
            if (!raw) continue

            let event: unknown
            try {
              event = JSON.parse(raw)
            } catch {
              continue
            }

            // Guard: must be a plain object before we can use 'in'
            if (!isPlainObject(event)) continue

            if ('error' in event) {
              const msg = String(event.error)
              setError(msg)
              optsRef.current.onError?.(msg)
              setIsStreaming(false)
              return
            }

            if ('sources' in event) {
              const srcs = (event.sources as SourceDocument[]) ?? []
              const meta = {
                chunksUsed: (event.chunksUsed as number) ?? 0,
                searchMode: (event.searchMode as string) ?? 'hybrid',
              }
              setSources(srcs)
              setSearchMeta(meta)
              optsRef.current.onSources?.(srcs, meta)
            } else if ('chunk' in event) {
              accumulated += String(event.chunk)
              setAnswer(accumulated)
              optsRef.current.onChunk?.(accumulated)
            } else if ('done' in event && event.done) {
              const final = String(event.answer ?? accumulated)
              setAnswer(final)
              setIsStreaming(false)
              optsRef.current.onDone?.(final)
              return
            }
          }
        }

        setIsStreaming(false)
        if (accumulated) optsRef.current.onDone?.(accumulated)
      } catch (err) {
        if (controller.signal.aborted) return
        const msg = err instanceof Error ? err.message : 'Stream failed'
        setError(msg)
        optsRef.current.onError?.(msg)
        setIsStreaming(false)
      }
    },
    [abort, reset]
  )

  return { answer, sources, searchMeta, isStreaming, error, stream, reset, abort }
}
