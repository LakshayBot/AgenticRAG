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
  const recent = stats.recentAdvisories.slice(1, 6)

  return (
    <>
      {/* Live Feed Card */}
      <div className="bg-surface-container-lowest rounded-[24px] p-5 shadow-lg border border-outline-variant/10 relative flex flex-col gap-4 min-h-[320px]">
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
        <a
          href="https://ko-fi.com/lakshaybot"
          target="_blank"
          rel="noopener noreferrer"
          className="bg-surface-container-lowest hover:bg-surface-container-low text-on-surface p-4 rounded-xl flex flex-col items-center justify-center gap-2 transition-colors border border-outline-variant/10 shadow-sm group"
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            className="text-[#FF5E5B] group-hover:scale-110 transition-transform"
          >
            <path
              d="M17 8h1a4 4 0 0 1 0 8h-1M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V8Z"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M6 2v3M10 2v3M14 2v3"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="text-xs font-medium text-center">Support</span>
        </a>
        <a
          href="https://github.com/LakshayBot/AgenticRAG"
          target="_blank"
          rel="noopener noreferrer"
          className="bg-surface-container-lowest hover:bg-surface-container-low text-on-surface p-4 rounded-xl flex flex-col items-center justify-center gap-2 transition-colors border border-outline-variant/10 shadow-sm group"
        >
          <svg
            width="22"
            height="22"
            viewBox="0 0 98 96"
            className="text-on-surface group-hover:scale-110 transition-transform"
          >
            <path
              fill="currentColor"
              fillRule="evenodd"
              clipRule="evenodd"
              d="M48.854 0C21.839 0 0 22 0 49.217c0 21.756 13.993 40.172 33.405 46.69 2.427.49 3.316-1.059 3.316-2.362 0-1.141-.08-5.052-.08-9.127-13.59 2.934-16.42-5.867-16.42-5.867-2.184-5.704-5.42-7.17-5.42-7.17-4.448-3.015.324-3.015.324-3.015 4.934.326 7.523 5.052 7.523 5.052 4.367 7.496 11.404 5.378 14.235 4.074.404-3.178 1.699-5.378 3.074-6.6-10.839-1.141-22.243-5.378-22.243-24.283 0-5.378 1.94-9.778 5.014-13.2-.485-1.222-2.184-6.275.486-13.038 0 0 4.125-1.304 13.426 5.052a46.97 46.97 0 0 1 12.214-1.63c4.125 0 8.33.571 12.213 1.63 9.302-6.356 13.427-5.052 13.427-5.052 2.67 6.763.97 11.816.485 13.038 3.155 3.422 5.015 7.822 5.015 13.2 0 18.905-11.404 23.06-22.324 24.283 1.78 1.548 3.316 4.481 3.316 9.126 0 6.6-.08 11.897-.08 13.526 0 1.304.89 2.853 3.316 2.362 19.412-6.518 33.405-24.934 33.405-46.691C97.707 22 75.788 0 48.854 0z"
            />
          </svg>
          <span className="text-xs font-medium text-center">Open Source</span>
        </a>
      </div>
    </>
  )
}
