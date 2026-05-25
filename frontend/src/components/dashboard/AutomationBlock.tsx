'use client'

import type { SystemStatsResponse, JobsStatusResponse } from '@/lib/types'

interface AutomationBlockProps {
  systemStats?: SystemStatsResponse
  jobsStatus?: JobsStatusResponse
}

type ItemStatus = 'Active' | 'In Progress' | 'Pending' | 'Running' | 'Error'

interface AutomationItem {
  label: string
  status: ItemStatus
  active: boolean
}

function getItems(systemStats?: SystemStatsResponse, jobsStatus?: JobsStatusResponse): AutomationItem[] {
  if (systemStats) {
    const pyServices = Object.entries(systemStats.services.pythonServices).slice(0, 2)
    return [
      ...pyServices.map(([name, svc]) => ({
        label: name.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
        status: (svc.healthy ? 'Active' : 'Error') as ItemStatus,
        active: svc.healthy,
      })),
      {
        label: 'Threat Intel',
        status: (jobsStatus?.processing ? 'Running' : 'Pending') as ItemStatus,
        active: false,
      },
    ]
  }
  return [
    { label: 'Auto-Patching', status: 'In Progress', active: true  },
    { label: 'Monitoring',    status: 'Active',       active: true  },
    { label: 'Threat Intel',  status: 'Pending',      active: false },
  ]
}

// Per-status colour tokens — all visible in both light and dark mode
const STATUS_STYLES: Record<ItemStatus, { badge: string; icon: string; iconFill: string }> = {
  'Active':      { badge: 'bg-emerald-500/15 text-emerald-600 dark:bg-emerald-400/20 dark:text-emerald-400', icon: 'check_circle',    iconFill: '1' },
  'In Progress': { badge: 'bg-amber-500/15 text-amber-600 dark:bg-amber-400/20 dark:text-amber-400',         icon: 'autorenew',       iconFill: '0' },
  'Pending':     { badge: 'bg-zinc-400/20 text-zinc-500 dark:bg-zinc-500/25 dark:text-zinc-400',             icon: 'pending',         iconFill: '0' },
  'Running':     { badge: 'bg-blue-500/15 text-blue-600 dark:bg-blue-400/20 dark:text-blue-400',             icon: 'sync',            iconFill: '0' },
  'Error':       { badge: 'bg-red-500/15 text-red-600 dark:bg-red-400/20 dark:text-red-400',                 icon: 'error',           iconFill: '1' },
}

export function AutomationBlock({ systemStats, jobsStatus }: AutomationBlockProps) {
  const items = getItems(systemStats, jobsStatus)

  return (
    <div className="bg-secondary-container rounded-[24px] p-4 sm:p-6 flex-1 flex flex-col min-w-0 overflow-hidden">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="font-headline font-semibold text-lg text-on-secondary-container opacity-90">
          Automation
        </h2>
        <span className="material-symbols-outlined text-on-secondary-container opacity-70">bolt</span>
      </div>

      {/* Service rows */}
      <div className="flex flex-col gap-4 flex-1">
        {items.map(({ label, status, active }) => {
          const styles = STATUS_STYLES[status] ?? STATUS_STYLES['Pending']
          return (
            <div key={label} className="flex items-center gap-2 min-w-0">
              {/* Icon */}
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${styles.badge}`}>
                <span
                  className="material-symbols-outlined"
                  style={{
                    fontSize: '18px',
                    fontVariationSettings: `'FILL' ${styles.iconFill}`,
                  }}
                >
                  {styles.icon}
                </span>
              </div>

              {/* Label */}
              <span
                className={`font-body text-sm font-medium text-on-secondary-container flex-1 truncate min-w-0 ${
                  !active ? 'opacity-60' : ''
                }`}
                title={label}
              >
                {label}
              </span>

              {/* Status badge */}
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-md shrink-0 whitespace-nowrap ${styles.badge}`}>
                {status}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
