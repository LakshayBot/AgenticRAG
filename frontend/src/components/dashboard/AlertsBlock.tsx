'use client'

import type { AdvisoryStats } from '@/lib/types'

const SEV_ORDER = ['critical', 'high', 'medium', 'low'] as const

export function AlertsBlock({ stats }: { stats: AdvisoryStats }) {
  const bd = stats.severityBreakdown
  const maxVal = Math.max(...SEV_ORDER.map((s) => bd[s] ?? 0), 1)

  return (
    <div className="bg-primary text-on-primary rounded-[24px] p-6 shadow-lg relative overflow-hidden group hover:shadow-xl transition-shadow duration-300 flex flex-col justify-between flex-1">
      {/* Decorative glow */}
      <div className="absolute -right-12 -top-12 w-40 h-40 bg-white/10 rounded-full blur-2xl group-hover:bg-white/20 transition-colors pointer-events-none" />

      {/* Header */}
      <div className="flex justify-between items-start mb-4 relative z-10">
        <h2 className="font-headline font-semibold text-lg opacity-90">Alerts</h2>
        <button className="text-on-primary/70 hover:text-on-primary transition-colors">
          <span className="material-symbols-outlined">more_horiz</span>
        </button>
      </div>

      {/* Big number */}
      <div className="mb-6 relative z-10">
        <div className="font-headline font-light text-6xl tracking-tight leading-none mb-1">
          {stats.totalAdvisories}
        </div>
        <div className="font-body text-sm font-medium opacity-80 uppercase tracking-widest mt-2">
          Total Active
        </div>
      </div>

      {/* Severity bar chart — real data */}
      <div className="flex items-end gap-1.5 h-16 w-full relative z-10 opacity-80 mt-auto">
        {SEV_ORDER.map((sev, i) => {
          const count = bd[sev] ?? 0
          const pct = (count / maxVal) * 100
          // highlight the tallest bar (first non-zero) in full white
          const isHighlight = i === SEV_ORDER.findIndex((s) => (bd[s] ?? 0) === maxVal)
          return (
            <div key={sev} className="flex-1 flex flex-col items-center gap-1">
              <span className="text-[9px] font-medium opacity-70 tabular-nums">{count}</span>
              <div
                className={`w-full rounded-t-sm ${isHighlight ? 'bg-white' : 'bg-on-primary/25'}`}
                style={{ height: `${Math.max(pct, 8)}%` }}
              />
              <span className="text-[8px] uppercase tracking-wide opacity-60">{sev.slice(0, 4)}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
