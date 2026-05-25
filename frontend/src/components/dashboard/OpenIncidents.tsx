'use client'

import type { AdvisoryStats } from '@/lib/types'

export function OpenIncidents({ stats }: { stats: AdvisoryStats }) {
  const bd = stats.severityBreakdown
  const critical = bd['critical'] ?? 0
  const warning  = (bd['high'] ?? 0) + (bd['medium'] ?? 0)
  const info     = bd['low'] ?? 0
  const total    = stats.totalAdvisories || 1

  const categories = [
    { label: 'Critical', count: critical, pct: (critical / total) * 100, dotColor: 'bg-md-primary',           barColor: 'bg-md-primary' },
    { label: 'Warning',  count: warning,  pct: (warning  / total) * 100, dotColor: 'bg-[#d97706] dark:bg-[#ffb77a]', barColor: 'bg-[#d97706] dark:bg-[#ffb77a]' },
    { label: 'Info',     count: info,     pct: (info     / total) * 100, dotColor: 'bg-[#ca8a04] dark:bg-[#d4c84a]', barColor: 'bg-[#ca8a04] dark:bg-[#d4c84a]' },
  ]

  return (
    <div className="bg-surface-container-low rounded-[24px] p-6 shadow-sm relative overflow-hidden">
      {/* Decorative corner */}
      <div className="absolute top-0 right-0 w-24 h-24 bg-surface-variant/50 rounded-bl-full -z-10" />

      <h3 className="font-headline font-semibold text-on-surface mb-4">Open Incidents</h3>

      <div className="space-y-4">
        {categories.map(({ label, count, pct, dotColor, barColor }) => (
          <div key={label}>
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${dotColor}`} />
                <span className="font-body text-sm text-on-surface">{label}</span>
              </div>
              <span className="font-headline font-bold text-on-surface">{count}</span>
            </div>
            <div className="w-full bg-surface-container-highest rounded-full h-1.5">
              <div className={`${barColor} h-1.5 rounded-full`} style={{ width: `${Math.max(pct, 2)}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
