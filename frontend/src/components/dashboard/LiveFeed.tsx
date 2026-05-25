'use client'

import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'
import type { AdvisoryStats } from '@/lib/types'

const SEV_COLOR: Record<string, string> = {
  critical: 'var(--primary)',
  high:     '#d97706',
  medium:   '#ca8a04',
  low:      'var(--secondary)',
}

export function LiveFeed({ stats }: { stats: AdvisoryStats }) {
  const latest = stats.recentAdvisories[0]
  const recent = stats.recentAdvisories.slice(1, 4)

  return (
    <>
      {/* Live Feed Card */}
      <div className="bg-surface-container-lowest rounded-[24px] p-5 shadow-lg border border-outline-variant/10 relative flex flex-col gap-3">
        {/* Pulse error badge */}
        <div className="absolute -top-3 -right-3 w-6 h-6 bg-error text-on-error rounded-full flex items-center justify-center shadow-sm animate-pulse z-10">
          <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>priority_high</span>
        </div>

        {latest ? (
          <div className="flex items-start gap-4">
            {/* Source badge */}
            <div className="w-10 h-10 rounded-xl bg-surface-container flex items-center justify-center shrink-0 border border-outline-variant/20">
              <span className="font-headline font-bold text-[#007DC1] text-[10px] tracking-tighter">
                {latest.ghsaId?.slice(5, 9).toUpperCase() ?? 'GHSA'}
              </span>
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1 gap-2">
                <h4 className="font-body font-semibold text-sm text-on-surface">Live Feed Alert</h4>
                {latest.publishedAt && (
                  <span className="text-[10px] text-on-surface-variant uppercase font-medium shrink-0">
                    {formatDistanceToNow(new Date(latest.publishedAt))} ago
                  </span>
                )}
              </div>

              {/* Severity badge */}
              <span
                className="inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide text-white mb-2"
                style={{ background: SEV_COLOR[latest.severity?.toLowerCase()] ?? SEV_COLOR.low }}
              >
                {latest.severity}
              </span>

              <p className="font-body text-xs text-on-surface-variant leading-relaxed line-clamp-3">
                {latest.summary}
              </p>
              <p className="text-[10px] text-on-surface-variant/60 font-numbers mt-1">{latest.ghsaId}</p>

              <Link
                href={`/advisories?id=${latest.ghsaId}`}
                className="mt-2 inline-block text-xs font-semibold text-primary hover:opacity-80 transition-opacity uppercase tracking-wider"
              >
                Investigate →
              </Link>
            </div>
          </div>
        ) : (
          <p className="text-sm text-on-surface-variant">No recent advisories.</p>
        )}

        {/* Recent list */}
        {recent.length > 0 && (
          <ul className="space-y-1.5 border-t border-outline-variant/10 pt-3">
            {recent.map((adv) => (
              <li key={adv.ghsaId} className="flex items-start gap-2">
                <span
                  className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0"
                  style={{ background: SEV_COLOR[adv.severity?.toLowerCase()] ?? SEV_COLOR.low }}
                />
                <p className="text-[11px] text-on-surface-variant line-clamp-1 flex-1">{adv.summary}</p>
              </li>
            ))}
          </ul>
        )}

        <Link
          href="/advisories"
          className="text-[11px] text-secondary font-medium hover:opacity-80 transition-opacity flex items-center gap-1"
        >
          View all advisories
          <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
        </Link>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 gap-3 w-full">
        <Link
          href="/ask"
          className="bg-surface-container-lowest hover:bg-surface-container-low text-on-surface p-4 rounded-xl flex flex-col items-center justify-center gap-2 transition-colors border border-outline-variant/10 shadow-sm group"
        >
          <span className="material-symbols-outlined text-md-primary group-hover:scale-110 transition-transform">vpn_key</span>
          <span className="text-xs font-medium text-center">Query AI</span>
        </Link>
        <Link
          href="/search"
          className="bg-surface-container-lowest hover:bg-surface-container-low text-on-surface p-4 rounded-xl flex flex-col items-center justify-center gap-2 transition-colors border border-outline-variant/10 shadow-sm group"
        >
          <span className="material-symbols-outlined text-[#ca8a04] dark:text-[#d4c84a] group-hover:scale-110 transition-transform">manage_search</span>
          <span className="text-xs font-medium text-center">Search Logs</span>
        </Link>
      </div>
    </>
  )
}
