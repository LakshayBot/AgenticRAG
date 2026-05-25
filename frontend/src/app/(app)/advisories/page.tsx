'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Advisory, AdvisorySummary } from '@/lib/types'
import { formatDistanceToNow } from 'date-fns'
import { cn } from '@/lib/utils'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface AdvisoryListResponse {
  total: number
  page: number
  pageSize: number
  advisories: AdvisorySummary[]
}

const SEV_CLASSES: Record<string, string> = {
  critical: 'bg-[#ffdad7] text-[#b02500] dark:bg-[rgba(176,37,0,0.25)] dark:text-[#ffb3ac]',
  high:     'bg-[#ffe8d1] text-[#9e4d00] dark:bg-[rgba(158,77,0,0.25)]  dark:text-[#ffb77a]',
  medium:   'bg-[#fff9c4] text-[#6a5b00] dark:bg-[rgba(106,91,0,0.25)]  dark:text-[#d4c84a]',
  low:      'bg-[#e8f5e9] text-[#1a6430] dark:bg-[rgba(26,100,48,0.25)] dark:text-[#6fcf97]',
}

function SeverityBadge({ severity }: { severity: string }) {
  const s = severity?.toLowerCase() ?? 'low'
  return (
    <span className={cn(
      'inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide',
      SEV_CLASSES[s] ?? SEV_CLASSES.low
    )}>
      {severity}
    </span>
  )
}

function AdvisoryCard({
  adv,
  selected,
  onClick,
}: {
  adv: AdvisorySummary
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left p-4 rounded-2xl transition-colors flex flex-col gap-1.5',
        selected
          ? 'bg-md-primary/10 ring-1 ring-md-primary/30'
          : 'bg-surface-container-lowest hover:bg-surface-container'
      )}
    >
      <div className="flex items-center gap-2">
        <SeverityBadge severity={adv.severity} />
        <span className="text-[11px] text-on-surface-variant font-numbers ml-auto">
          {adv.publishedAt
            ? formatDistanceToNow(new Date(adv.publishedAt)) + ' ago'
            : ''}
        </span>
      </div>
      <p className="text-[13px] font-medium text-on-surface leading-snug line-clamp-2">
        {adv.summary}
      </p>
      <p className="text-[11px] text-on-surface-variant font-numbers">{adv.ghsaId}</p>
    </button>
  )
}

function AdvisoryDetailPanel({ ghsaId }: { ghsaId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['advisory', ghsaId],
    queryFn: () => api.get<Advisory>(`/api/advisories/${ghsaId}`),
    staleTime: 300_000,
  })

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center text-on-surface-variant">
        <span className="material-symbols-outlined text-3xl animate-spin">progress_activity</span>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-5">
      <div className="space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          <SeverityBadge severity={data.severity} />
          {data.cveId && (
            <span className="text-[11px] font-numbers bg-surface-container px-2 py-0.5 rounded-full text-on-surface-variant">
              {data.cveId}
            </span>
          )}
          {data.cvssScore != null && (
            <span className="text-[11px] font-numbers bg-surface-container px-2 py-0.5 rounded-full text-on-surface-variant">
              CVSS {data.cvssScore.toFixed(1)}
            </span>
          )}
        </div>
        <h2 className="font-display text-[20px] text-on-surface">{data.summary}</h2>
        <p className="text-[12px] text-on-surface-variant font-numbers">{data.ghsaId}</p>
      </div>

      {data.description && (
        <div className="prose-rag text-[13px]">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.description}</ReactMarkdown>
        </div>
      )}

      {data.affectedPackages && data.affectedPackages.length > 0 && (
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-on-surface-variant mb-2">
            Affected Packages
          </p>
          <div className="flex flex-wrap gap-1.5">
            {data.affectedPackages.map((pkg) => (
              <span
                key={pkg}
                className="text-[12px] font-numbers px-2.5 py-1 rounded-xl bg-surface-container text-on-surface-variant"
              >
                {pkg}
              </span>
            ))}
          </div>
        </div>
      )}

      {data.referenceUrls && data.referenceUrls.length > 0 && (
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-on-surface-variant mb-2">
            References
          </p>
          <ul className="space-y-1">
            {data.referenceUrls.slice(0, 5).map((url) => (
              <li key={url}>
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[12px] text-md-primary hover:opacity-80 transition-opacity truncate block"
                >
                  {url}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function AdvisoriesPage() {
  const [selected, setSelected] = useState<AdvisorySummary | null>(null)
  const [search, setSearch] = useState('')
  const [sevFilter, setSevFilter] = useState<string>('all')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  // Debounce search input — 300 ms
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(t)
  }, [search])

  // Full paginated list with server-side severity + search filtering
  const { data: listData, isLoading, isError } = useQuery({
    queryKey: ['advisory-list', sevFilter, debouncedSearch],
    queryFn: () => {
      const params = new URLSearchParams({ pageSize: '100' })
      if (sevFilter !== 'all') params.set('severity', sevFilter)
      if (debouncedSearch) params.set('search', debouncedSearch)
      return api.get<AdvisoryListResponse>(`/api/advisories?${params}`)
    },
    staleTime: 30_000,
    retry: 1,
  })

  const filtered = listData?.advisories ?? []

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left panel — list */}
      <div className="w-[360px] shrink-0 flex flex-col border-r border-outline-variant h-full">
        <div className="p-4 border-b border-outline-variant space-y-3">
          <h1 className="font-display text-[20px] text-on-surface">Threat Intelligence</h1>

          {/* Search */}
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant">
              search
            </span>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search advisories..."
              className="w-full pl-9 pr-3 py-2 bg-surface-container rounded-2xl text-[13px] text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-md-primary/40"
            />
          </div>

          {/* Severity filter */}
          <div className="flex gap-1.5 flex-wrap">
            {['all', 'critical', 'high', 'medium', 'low'].map((sev) => (
              <button
                key={sev}
                onClick={() => setSevFilter(sev)}
                className={cn(
                  'px-3 py-1 rounded-full text-[11px] font-medium capitalize transition-colors',
                  sevFilter === sev
                    ? 'bg-md-primary text-md-on-primary dark:bg-md-primary dark:text-md-on-primary'
                    : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
                )}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {isLoading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-20 rounded-2xl animate-skeleton" />
            ))
          ) : isError ? (
            <div className="text-center py-12 text-on-surface-variant">
              <span className="material-symbols-outlined text-4xl block mb-2">error_outline</span>
              <p className="text-[13px]">Failed to load advisories</p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-12 text-on-surface-variant">
              <span className="material-symbols-outlined text-4xl block mb-2">search_off</span>
              <p className="text-[13px]">No advisories found</p>
            </div>
          ) : (
            filtered.map((adv) => (
              <AdvisoryCard
                key={adv.ghsaId}
                adv={adv}
                selected={selected?.ghsaId === adv.ghsaId}
                onClick={() => setSelected(adv)}
              />
            ))
          )}
        </div>
      </div>

      {/* Right panel — detail */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {selected ? (
          <AdvisoryDetailPanel ghsaId={selected.ghsaId} />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-on-surface-variant gap-3">
            <span className="material-symbols-outlined text-5xl opacity-30">security</span>
            <p className="text-[14px]">Select an advisory to view details</p>
          </div>
        )}
      </div>
    </div>
  )
}
