'use client'

import { useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { SearchResponse, SearchResult } from '@/lib/types'
import { cn } from '@/lib/utils'
import DOMPurify from 'dompurify'
import { SidebarTrigger } from '@/components/ui/sidebar'

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.min(score * 100, 100)
  const color =
    pct >= 70 ? 'var(--sev-low)' : pct >= 40 ? 'var(--sev-medium)' : 'var(--sev-high)'
  return (
    <span
      className="inline-block px-2 py-0.5 rounded-full text-[10px] font-numbers font-semibold"
      style={{ background: `${color}20`, color }}
    >
      {pct.toFixed(0)}%
    </span>
  )
}

function ResultCard({ result, onAsk }: { result: SearchResult; onAsk: (id: string, title: string) => void }) {
  const [expanded, setExpanded] = useState(false)
  const snippet = result.snippet ?? result.chunkText ?? ''
  const cleanSnippet =
    typeof window !== 'undefined' ? DOMPurify.sanitize(snippet) : snippet

  return (
    <div className="rounded-2xl bg-surface-container border border-outline-variant/40 p-4 space-y-2 animate-card-enter">
      <div className="flex items-start justify-between gap-2">
        <p className="text-[14px] font-semibold text-on-surface leading-snug flex-1">
          {result.title}
        </p>
        <ScoreBadge score={result.score} />
      </div>

      {result.authors && (
        <p className="text-[11px] text-on-surface-variant">{result.authors}</p>
      )}

      {cleanSnippet && (
        <div>
          <div
            className={cn(
              'text-[13px] text-on-surface-variant leading-relaxed overflow-hidden transition-all',
              expanded ? 'max-h-none' : 'max-h-20'
            )}
            dangerouslySetInnerHTML={{ __html: cleanSnippet }}
          />
          {cleanSnippet.length > 200 && (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="text-[12px] text-md-primary hover:opacity-80 mt-1"
            >
              {expanded ? 'Show less' : 'Show more'}
            </button>
          )}
        </div>
      )}

      <div className="flex items-center gap-2 pt-1">
        {result.publishedDate && (
          <span className="text-[11px] font-numbers text-on-surface-variant bg-surface-container px-2 py-0.5 rounded-full">
            {result.publishedDate.split('T')[0]}
          </span>
        )}
        <button
          onClick={() => onAsk(result.sourceId || result.id, result.title)}
          className="ml-auto flex items-center gap-1.5 text-[12px] text-md-primary hover:opacity-80 transition-opacity"
        >
          <span className="material-symbols-outlined text-[16px]">psychology</span>
          Ask about this
        </button>
      </div>
    </div>
  )
}

function SearchContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') ?? '')
  const [searchType, setSearchType] = useState<'hybrid' | 'bm25' | 'vector'>('hybrid')
  const [topK, setTopK] = useState(10)
  const [submitted, setSubmitted] = useState(searchParams.get('q') ?? '')

  const { data, isLoading } = useQuery({
    queryKey: ['search', submitted, searchType, topK],
    queryFn: () =>
      api.post<SearchResponse>(`/api/search/${searchType}`, {
        query: submitted,
        topK,
      }),
    enabled: !!submitted,
    staleTime: 30_000,
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const q = query.trim()
    if (!q) return
    setSubmitted(q)
    router.push(`/search?q=${encodeURIComponent(q)}`)
  }

  function handleAsk(sourceId: string, title: string) {
    const params = new URLSearchParams({ sourceId, title })
    router.push(`/ask?${params}`)
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-6 flex items-center gap-3">
        <SidebarTrigger className="-ml-2" />
        <div>
          <h1 className="font-display text-[26px] text-on-surface">Incident Logs</h1>
          <p className="text-[13px] text-on-surface-variant mt-0.5">
            Search across indexed security advisories and documents
          </p>
        </div>
      </div>

      {/* Search form */}
      <form onSubmit={handleSubmit} className="space-y-3 mb-6">
        <div className="relative">
          <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-[20px] text-on-surface-variant">
            search
          </span>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search for vulnerabilities, packages, CVEs..."
            className="w-full pl-12 pr-4 py-3 bg-surface-container border border-outline-variant rounded-3xl text-[14px] text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-md-primary/30 shadow-sm"
          />
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Search type */}
          <div className="flex rounded-2xl bg-surface-container p-0.5 text-[12px]">
            {(['hybrid', 'bm25', 'vector'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setSearchType(mode)}
                className={cn(
                  'px-3 py-1.5 rounded-xl uppercase tracking-wide transition-colors font-numbers',
                  searchType === mode
                    ? 'bg-md-primary text-md-on-primary'
                    : 'text-on-surface-variant hover:text-on-surface'
                )}
              >
                {mode}
              </button>
            ))}
          </div>

          {/* TopK */}
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-[12px] text-on-surface-variant">Top</span>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="text-[12px] bg-surface-container rounded-xl px-2 py-1.5 text-on-surface border-none focus:outline-none"
            >
              {[5, 10, 20, 50].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            disabled={!query.trim()}
            className="px-5 py-2 rounded-full bg-md-primary text-md-on-primary text-[13px] font-semibold disabled:opacity-40 hover:opacity-90 transition-opacity"
          >
            Search
          </button>
        </div>
      </form>

      {/* Results */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-28 rounded-2xl animate-skeleton bg-surface-container" />
          ))}
        </div>
      )}

      {!isLoading && !data && !submitted && (
        <div className="text-center py-20 text-on-surface-variant">
          <span className="material-symbols-outlined text-5xl block mb-3 opacity-25">manage_search</span>
          <p className="text-[14px] font-medium text-on-surface-variant">Search for CVEs, packages, or advisories</p>
          <p className="text-[12px] mt-1 opacity-60">Supports BM25 keyword, vector semantic, and hybrid search</p>
        </div>
      )}

      {data && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <p className="text-[13px] text-on-surface-variant">
              {data.totalResults} results
              <span className="ml-1 font-numbers text-outline">· {data.queryTimeMs.toFixed(0)}ms</span>
            </p>
            <span className="text-[11px] bg-surface-container px-2 py-0.5 rounded-full text-on-surface-variant uppercase tracking-wide ml-auto">
              {data.searchType}
            </span>
          </div>

          <div className="space-y-3">
            {data.results.map((r) => (
              <ResultCard key={r.id} result={r} onAsk={handleAsk} />
            ))}
          </div>

          {data.results.length === 0 && (
            <div className="text-center py-16 text-on-surface-variant">
              <span className="material-symbols-outlined text-5xl block mb-3 opacity-30">search_off</span>
              <p className="text-[14px]">No results found for &quot;{submitted}&quot;</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function SearchPage() {
  return (
    <Suspense>
      <SearchContent />
    </Suspense>
  )
}
